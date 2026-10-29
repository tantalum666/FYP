"""Owner-selected authority for registered software actions, separate from the model.

Full access does not enable new executors, physical outputs, accounts or media.
Only a new authenticated owner request can capture an automatic grant. Cached
requests resolve existing receipts without applying an old pending action.
"""

import json
import threading
from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field

from .calendar import iso
from .jobs import JobApproval
from .schemas import StrictModel
from .store import DomainError

SOFTWARE_PROPOSALS = frozenset({
    "create", "change", "task_create", "task_change",
    "memory_save", "memory_replace", "memory_delete", "memory_consolidate",
})


class PermissionChange(StrictModel):
    mode: Literal["ask", "full"]
    expected_version: int = Field(ge=1, strict=True)


@dataclass(frozen=True)
class OwnerGrant:
    version: int
    session: str
    task_id: str | None
    proposal_sequence: int
    job_sequence: int


class PermissionService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.lock = threading.RLock()
        with self.store.connection(write=True) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS owner_permissions ("
                         "id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL, "
                         "version INTEGER NOT NULL, updated_at TEXT NOT NULL)")
            conn.execute("INSERT OR IGNORE INTO owner_permissions VALUES(1,'ask',1,?)",
                         (iso(self.store.clock()),))

    def snapshot(self, conn=None):
        if conn is not None:
            return dict(conn.execute(
                "SELECT mode,version,updated_at FROM owner_permissions WHERE id=1"
            ).fetchone())
        with self.store.connection() as owned:
            return self.snapshot(owned)

    def change(self, payload, key):
        def apply(conn):
            current = self.snapshot(conn)
            if (payload.expected_version > current["version"] or
                    (payload.mode == "full" and current["version"] != payload.expected_version)):
                raise DomainError("VERSION_CONFLICT", 409)
            # An explicit revocation is allowed from an older screen. Even an
            # already-Ask decision fences delayed Full requests and old grants.
            conn.execute("UPDATE owner_permissions SET mode=?,version=version+1,updated_at=? "
                         "WHERE id=1", (payload.mode, iso(self.store.clock())))
            self.store.record(conn, "permission_changed", details={
                "mode": payload.mode, "version": current["version"] + 1,
            })
            self.store.bump(conn)
            return {"saved": True}
        with self.lock:
            self.store.operation(key, {"type": "permission_change", **payload.model_dump()}, apply)
            return {"saved": True, "permissions": self.snapshot()}

    def capture(self, principal, task_id=None):
        if not principal or principal.get("kind") != "owner":
            return None
        session = principal.get("session")
        if not session or not self.store.session_valid(session):
            return None
        with self.store.connection() as conn:
            current = self.snapshot(conn)
            if current["mode"] != "full":
                return None
            proposal_sequence = conn.execute("SELECT COALESCE(MAX(rowid),0) FROM assistant_proposals").fetchone()[0]
            job_sequence = conn.execute("SELECT COALESCE(MAX(rowid),0) FROM computer_jobs").fetchone()[0]
        return OwnerGrant(current["version"], session, task_id, proposal_sequence, job_sequence)

    def current(self, version, conn=None):
        policy = self.snapshot(conn)
        return policy["mode"] == "full" and policy["version"] == version

    def instructions(self, principal):
        if not principal or principal.get("kind") != "owner":
            return ""
        mode = self.snapshot()["mode"]
        return (f"\nOwner software permission mode: {mode}. You still propose typed actions; "
                "the application independently applies the owner's permission policy. "
                "A tool result with saved=true is already applied; queued=true is still in progress. "
                "Do not ask the owner to confirm an action already applied or call it complete before verification. "
                "Permission changes are only available to the owner in Settings, never as a model tool. "
                "Full access does not add physical outputs, accounts, media capture or unavailable executors.")

    def apply_reply(self, reply, grant, *, language="en", cancelled=lambda: False):
        if grant is None:
            return reply
        with self.lock:
            if cancelled() or not self.current(grant.version) or not self.store.session_valid(grant.session):
                return reply
            proposal_id = (reply.get("proposal") or {}).get("id")
            job_id = (reply.get("job") or {}).get("id")
            if not proposal_id and not job_id:
                return reply
            try:
                if proposal_id:
                    with self.store.connection() as conn:
                        proposal = conn.execute(
                            "SELECT rowid AS sequence,kind,state,data FROM assistant_proposals WHERE id=?", (proposal_id,)
                        ).fetchone()
                    if not proposal or proposal["kind"] not in SOFTWARE_PROPOSALS:
                        return reply
                    if proposal["sequence"] <= grant.proposal_sequence:
                        return self.refresh_reply(reply, language=language)
                    if grant.task_id and proposal["kind"] == "task_change" and json.loads(proposal["data"])["task_id"] != grant.task_id:
                        return reply
                    if cancelled():
                        return reply
                    if proposal["state"] == "pending":
                        self.runtime.assistant.decide(
                            proposal_id, "confirm", "permission/" + proposal_id,
                            permission_version=grant.version,
                        )
                else:
                    with self.store.connection() as conn:
                        sequence = conn.execute("SELECT rowid FROM computer_jobs WHERE id=?", (job_id,)).fetchone()
                    if not sequence or sequence[0] <= grant.job_sequence:
                        return self.refresh_reply(reply, language=language)
                    job = self.runtime.jobs.detail(job_id, review=True)
                    if grant.task_id and grant.task_id != job["task_id"]:
                        return reply
                    if cancelled():
                        return reply
                    if job["state"] == "review":
                        self.runtime.jobs.approve(job_id, JobApproval(
                            expected_version=job["version"], intent_hash=job["intent_hash"],
                        ), "permission/" + job_id, permission_version=grant.version)
            except DomainError as error:
                return {**reply, "permission_error": error.code}
            return self.refresh_reply({**reply, "authorization": {
                "mode": "full", "version": grant.version,
            }}, language=language)

    def refresh_reply(self, reply, *, language="en"):
        """Read existing action state; never authorize a cached pending request."""
        zh = language == "zh"
        if job_id := (reply.get("job") or {}).get("id"):
            job = self.runtime.jobs.detail(job_id)
            state = job["state"]
            if state == "review":
                return {**reply, "job": job}
            messages = {
                "succeeded": ("The file action finished and its result was verified.", "文件操作已完成，结果已核验。"),
                "cancelled": ("The file action was cancelled before execution.", "文件操作已在执行前取消。"),
                "expired": ("This file action expired without execution.", "文件操作已到期，未执行。"),
                "failed": ("The file action could not run. Review its details.", "文件操作未能执行，请查看详情。"),
                "unknown": ("The result needs checking before another write.", "结果待核验，请先检查已有结果。"),
            }
            wording = messages.get(state, ("The file action is in progress.", "文件操作正在进行。"))
            return {**reply, "job": job, "saved": state == "succeeded",
                    "queued": state in {"queued", "running", "verifying"}, "message": wording[zh]}
        if proposal_id := (reply.get("proposal") or {}).get("id"):
            with self.store.connection() as conn:
                row = conn.execute("SELECT * FROM assistant_proposals WHERE id=?", (proposal_id,)).fetchone()
                applied = conn.execute("SELECT response FROM operations WHERE id=?", ("assistant-confirm/" + proposal_id,)).fetchone()
            if row and (row["state"] == "confirmed" or applied) and row["kind"] in SOFTWARE_PROPOSALS:
                result = json.loads(applied[0] if applied else row["result"])
                return {**reply, "proposal": None, "kind": "action", "saved": True,
                        "action": {"id": proposal_id, "kind": row["kind"], "state": "confirmed"},
                        "result": result,
                        "message": (("已按你的权限设置完成操作。" if zh else "Done using your permission setting.")
                                    if reply.get("authorization", {}).get("mode") == "full"
                                    else ("此操作已完成。" if zh else "This action was completed."))}
        return reply


def permission_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/permissions", dependencies=[Depends(owner)])

    @router.get("")
    def snapshot():
        return runtime.permissions.snapshot()

    @router.post("")
    def change(payload: PermissionChange, key=Depends(operation_id)):
        return runtime.permissions.change(payload, key)

    return router
