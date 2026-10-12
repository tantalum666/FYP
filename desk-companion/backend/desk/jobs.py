"""Durable execution intents, owner approval and conservative crash recovery.

One local worker, no model calls. Claim/approval/cancellation are SQLite transactions.
A dispatched write is never retried. Unknown results have a read-only reconciliation
path; a late verified receipt remains truthful even after a cancellation request.
"""

import hashlib
import json
import os
import threading
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import Field, model_validator

from .calendar import iso
from .computer import ComputerExecutor, ExecutionRejected, LocalNotesExecutor
from .application_executor import ApplicationRecordsExecutor
from .executor_registry import ExecutorRegistry
from .schemas import StrictModel
from .store import DomainError, encode

TERMINAL = {"succeeded", "failed", "cancelled", "expired"}


class JobInput(StrictModel):
    action: Literal["save_note", "verify_note", "create_record", "verify_record"] = "save_note"
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=8000)
    source_job_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    task_id: str | None = Field(default=None, max_length=64)
    task_version: int | None = Field(default=None, ge=1, strict=True)

    @model_validator(mode="after")
    def intent(self):
        try:
            self.content.encode("utf-8")
            self.title.encode("utf-8")
        except UnicodeError:
            raise ValueError("Use valid Unicode text") from None
        if not self.title.strip() or (
            self.action in {"save_note", "create_record"} and not self.content.strip()
        ):
            raise ValueError("A title and note text are required")
        if (self.task_id is None) != (self.task_version is None):
            raise ValueError("Task ID and version must be supplied together")
        if self.action in {"save_note", "create_record"} and self.source_job_id is not None:
            raise ValueError("New notes cannot target an existing artifact")
        if self.action in {"verify_note", "verify_record"} and (
            not self.source_job_id or self.content
        ):
            raise ValueError("Verification requires a saved job, without replacement text")
        return self


class JobApproval(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class JobQuery(StrictModel):
    job_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class JobService:
    def __init__(self, runtime, executor: ComputerExecutor | None = None):
        self.runtime, self.store = runtime, runtime.store
        self.executor = executor or LocalNotesExecutor(self.store.directory)
        app_origin = os.environ.get("DESK_DEMO_APP_ORIGIN")
        self.registry = ExecutorRegistry(
            lambda: self.executor,
            ApplicationRecordsExecutor(app_origin) if app_origin else None,
        )
        self.enabled = os.environ.get("DESK_COMPUTER_ENABLED") == "1"
        self.run_lock = threading.Lock()
        self.stopping = False
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS computer_jobs(
                    id TEXT PRIMARY KEY, request TEXT NOT NULL, intent_hash TEXT NOT NULL,
                    state TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, expires_at TEXT NOT NULL, deadline TEXT,
                    approved_by TEXT, run_id TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    result TEXT, error TEXT);
                CREATE INDEX IF NOT EXISTS computer_jobs_state ON computer_jobs(state, created_at);
                CREATE TABLE IF NOT EXISTS computer_job_events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                    at TEXT NOT NULL, state TEXT NOT NULL, code TEXT);
            """)
            for row in conn.execute(
                "SELECT * FROM computer_jobs WHERE state IN ('running','verifying','cancel_requested')"
            ).fetchall():
                # Invalidate the old run token; an old process cannot bless a new run.
                conn.execute("UPDATE computer_jobs SET run_id=NULL WHERE id=?", (row["id"],))
                self._state(conn, row["id"], "unknown", "PROCESS_RESTARTED")

    def capabilities(self):
        return {
            "enabled": self.enabled,
            "executor": self.executor.identity,
            "scope": self.executor.scope,
            "actions": self.registry.actions() if self.enabled else [],
            "application": {
                "enabled": self.enabled and self.registry.application is not None,
                "executor": "demo_records_api_v1",
                "scope": "isolated_demo_records_only",
                "target_origin": self.registry.application.origin
                if self.registry.application
                else None,
                "interface": "application_api",
            },
        }

    @staticmethod
    def _row(conn, job_id):
        row = conn.execute("SELECT * FROM computer_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise DomainError("JOB_NOT_FOUND", 404)
        return row

    @staticmethod
    def _view(row, review=False):
        request = json.loads(row["request"])
        view = {
            k: row[k]
            for k in (
                "id",
                "state",
                "version",
                "created_at",
                "updated_at",
                "expires_at",
                "deadline",
                "error",
            )
        }
        view.update(
            action=request["action"],
            task_id=request["task_id"],
            cancel_requested=bool(row["cancel_requested"]),
            result=json.loads(row["result"]) if row["result"] else None,
        )
        if review:
            view.update(request=request, intent_hash=row["intent_hash"])
        return view

    def detail(self, job_id, review=False):
        with self.store.connection() as conn:
            view = self._view(self._row(conn, job_id), review)
            view["history"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT at,state,code FROM computer_job_events WHERE job_id=? ORDER BY sequence",
                    (job_id,),
                )
            ]
            return view

    def listing(self, task_id=None, review=False):
        with self.store.connection() as conn:
            # Filter before paging: an older task must not disappear behind
            # unrelated history. Unresolved outcomes take priority over history.
            rows = conn.execute(
                "SELECT * FROM computer_jobs "
                + ("WHERE json_extract(request, '$.task_id')=? " if task_id is not None else "")
                + "ORDER BY state IN ('succeeded','failed','cancelled','expired'), "
                "created_at DESC,rowid DESC LIMIT 200",
                (task_id,) if task_id is not None else (),
            )
            return [self._view(r, review) for r in rows]

    def _state(self, conn, job_id, state, code=None, result=None):
        now = iso(self.store.clock())
        conn.execute(
            "UPDATE computer_jobs SET state=?,version=version+1,updated_at=?,error=?,result=COALESCE(?,result) WHERE id=?",
            (state, now, code, encode(result) if result is not None else None, job_id),
        )
        conn.execute(
            "INSERT INTO computer_job_events(job_id,at,state,code) VALUES(?,?,?,?)",
            (job_id, now, state, code),
        )
        self.store.record(
            conn, "computer_job", details={"job_id": job_id, "state": state, "code": code}
        )
        self.store.bump(conn)

    def _task_current(self, conn, request):
        if request["task_id"]:
            task = self.runtime.tasks.get(conn, request["task_id"])
            if task["version"] != request["task_version"] or task["status"] in {
                "completed",
                "cancelled",
            }:
                raise DomainError("JOB_TASK_CHANGED", 409)

    def prepare(self, payload: JobInput, key):
        if not self.enabled:
            raise DomainError("COMPUTER_DISABLED", 409)

        def apply(conn):
            if conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0] >= 1000:
                raise DomainError("JOB_LIMIT", 429)
            if (
                conn.execute(
                    "SELECT COUNT(*) FROM computer_jobs WHERE state IN ('review','queued')"
                ).fetchone()[0]
                >= 20
            ):
                raise DomainError("TOO_MANY_DRAFTS", 422)
            request = payload.model_dump()
            self._task_current(conn, request)
            job_id = uuid4().hex
            request.update(artifact_id=job_id)
            self.registry.bind(request)
            if payload.action in {"verify_note", "verify_record"}:
                source = self._row(conn, payload.source_job_id)
                original = json.loads(source["request"])
                source_action = "save_note" if payload.action == "verify_note" else "create_record"
                if source["state"] != "succeeded" or original["action"] != source_action:
                    raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
                self.registry.validate(original)
                request.update(artifact_id=original["artifact_id"], content=original["content"])
                if payload.action == "verify_record":
                    if request["app_instance_id"] != original["app_instance_id"]:
                        raise DomainError("APPLICATION_INSTANCE_CHANGED", 409)
                    request.update(
                        {
                            name: original[name]
                            for name in (
                                "record_title",
                                "content_sha256",
                                "app_instance_id",
                                "target_origin",
                                "adapter_version",
                                "schema_version",
                            )
                        }
                    )
                    request["record_intent_hash"] = source["intent_hash"]
            fingerprint = hashlib.sha256(encode(request).encode()).hexdigest()
            now = iso(self.store.clock())
            conn.execute(
                "INSERT INTO computer_jobs(id,request,intent_hash,state,version,created_at,updated_at,expires_at) VALUES(?,?,?,'review',0,?,?,?)",
                (
                    job_id,
                    encode(request),
                    fingerprint,
                    now,
                    now,
                    iso(self.store.clock() + timedelta(minutes=5)),
                ),
            )
            self._state(conn, job_id, "review")
            return {"job": self._view(self._row(conn, job_id)), "saved": False}

        result = self.store.operation(
            key, {"type": "computer_prepare", **payload.model_dump()}, apply
        )
        # Return live state on retries; an old 'review' response is not current truth.
        return {**result, "job": self.detail(result["job"]["id"])}

    def approve(self, job_id, payload: JobApproval, key):
        def apply(conn):
            row = self._row(conn, job_id)
            if not self.enabled:
                raise DomainError("COMPUTER_DISABLED", 409)
            if row["state"] != "review" or row["expires_at"] <= iso(self.store.clock()):
                raise DomainError("JOB_NOT_REVIEWABLE", 409)
            if (
                row["version"] != payload.expected_version
                or row["intent_hash"] != payload.intent_hash
            ):
                raise DomainError("VERSION_CONFLICT", 409)
            request = json.loads(row["request"])
            self._task_current(conn, request)
            self._authorized_request(row, request)
            conn.execute(
                "UPDATE computer_jobs SET approved_by='owner',deadline=? WHERE id=?",
                (iso(self.store.clock() + timedelta(seconds=60)), job_id),
            )
            self._state(conn, job_id, "queued")
            return {"job_id": job_id}

        self.store.operation(
            key, {"type": "computer_approve", "id": job_id, **payload.model_dump()}, apply
        )
        return {"job": self.detail(job_id), "queued": True}

    def cancel(self, job_id, key, review_only=False):
        def apply(conn):
            row = self._row(conn, job_id)
            if review_only and row["state"] != "review":
                return {"job_id": job_id}
            if row["state"] not in TERMINAL and not row["cancel_requested"]:
                conn.execute("UPDATE computer_jobs SET cancel_requested=1 WHERE id=?", (job_id,))
                state = (
                    "cancelled"
                    if row["state"] in {"review", "queued"}
                    else ("unknown" if row["state"] == "unknown" else "cancel_requested")
                )
                self._state(conn, job_id, state, "USER_CANCELLED")
            return {"job_id": job_id}

        self.store.operation(
            key, {"type": "computer_cancel", "id": job_id, "review_only": review_only}, apply
        )
        return {"job": self.detail(job_id)}

    def expire(self):
        now = iso(self.store.clock())
        with self.store.connection(write=True) as conn:
            for row in conn.execute(
                "SELECT * FROM computer_jobs WHERE (state='review' AND expires_at<=?) OR (state='queued' AND deadline<=?) OR (state IN ('running','verifying','cancel_requested') AND deadline<=?)",
                (now, now, now),
            ).fetchall():
                state = "expired" if row["state"] in {"review", "queued"} else "unknown"
                self._state(conn, row["id"], state, "JOB_DEADLINE_EXCEEDED")

    def _authorized_request(self, row, request):
        if hashlib.sha256(encode(request).encode()).hexdigest() != row["intent_hash"]:
            raise DomainError("JOB_INTENT_CHANGED", 409)
        return self.registry.validate(request)

    def _verify(self, request):
        return self.registry.verify(request)

    def run_one(self):
        if not self.enabled or self.stopping or not self.run_lock.acquire(False):
            return
        try:
            self.expire()
            with self.store.connection(write=True) as conn:
                row = conn.execute(
                    "SELECT * FROM computer_jobs WHERE state='queued' ORDER BY created_at,rowid LIMIT 1"
                ).fetchone()
                if not row:
                    return
                job_id, request, run_id = row["id"], json.loads(row["request"]), uuid4().hex
                try:
                    self._task_current(conn, request)
                    if not row["approved_by"]:
                        raise DomainError("COMPUTER_SCOPE_CHANGED", 409)
                    executor = self._authorized_request(row, request)
                except DomainError as error:
                    self._state(conn, job_id, "failed", error.code)
                    return
                conn.execute("UPDATE computer_jobs SET run_id=? WHERE id=?", (run_id, job_id))
                self._state(conn, job_id, "running")

            def checkpoint():
                with self.store.connection() as conn:
                    current = self._row(conn, job_id)
                    if self.stopping or current["run_id"] != run_id or current["cancel_requested"]:
                        raise ExecutionRejected("JOB_CANCELLED_BEFORE_DISPATCH", 409)
                    if current["deadline"] <= iso(self.store.clock()):
                        raise ExecutionRejected("JOB_DEADLINE_EXCEEDED", 409)
                    try:
                        self._task_current(conn, request)
                    except DomainError as error:
                        raise ExecutionRejected(error.code, error.status) from None

            try:
                executor.execute(request, checkpoint)
            except ExecutionRejected as error:
                state = "cancelled" if error.code == "JOB_CANCELLED_BEFORE_DISPATCH" else "failed"
                code, receipt = error.code, None
            except Exception:
                # The adapter may already have written. Never repeat this intent.
                state, code, receipt = "unknown", "EXECUTOR_RESULT_UNKNOWN", None
            else:
                with self.store.connection(write=True) as conn:
                    if self._row(conn, job_id)["run_id"] != run_id:
                        return
                    self._state(conn, job_id, "verifying")
                try:
                    receipt = self._verify(request)
                    state, code = (
                        ("succeeded", None)
                        if receipt.get("verified")
                        else ("unknown", "JOB_VERIFICATION_FAILED")
                    )
                except Exception:
                    # Even an explicit verification rejection says nothing about
                    # the preceding write. Preserve read-only reconciliation.
                    state, code, receipt = "unknown", "JOB_VERIFICATION_FAILED", None
            with self.store.connection(write=True) as conn:
                if self._row(conn, job_id)["run_id"] == run_id:
                    self._state(conn, job_id, state, code, receipt)
        finally:
            self.run_lock.release()

    def shutdown(self):
        self.stopping = True
        with self.store.connection(write=True) as conn:
            for row in conn.execute(
                "SELECT id FROM computer_jobs WHERE state IN ('running','verifying','cancel_requested')"
            ).fetchall():
                conn.execute("UPDATE computer_jobs SET run_id=NULL WHERE id=?", (row["id"],))
                self._state(conn, row["id"], "unknown", "SERVICE_STOPPED")

    def reconcile(self, job_id):
        if not self.enabled:
            raise DomainError("COMPUTER_DISABLED", 409)
        if not self.run_lock.acquire(False):
            raise DomainError("JOB_STILL_RUNNING", 409)
        try:
            with self.store.connection() as conn:
                row = self._row(conn, job_id)
                if row["state"] != "unknown":
                    return {"job": self._view(row)}
                request = json.loads(row["request"])
                self._authorized_request(row, request)
            try:
                receipt = self._verify(request)
            except Exception:
                receipt = {"verified": False, "reason": "verification_unavailable"}
            with self.store.connection(write=True) as conn:
                self._state(
                    conn,
                    job_id,
                    "succeeded" if receipt.get("verified") else "unknown",
                    None if receipt.get("verified") else "JOB_VERIFICATION_FAILED",
                    receipt,
                )
            return {"job": self.detail(job_id)}
        finally:
            self.run_lock.release()


def job_routes(runtime, owner, operation_id):
    # Pairing and model tool access do not grant computer execution approval.
    router = APIRouter(prefix="/api/computer", dependencies=[Depends(owner)])

    def visible(principal=Depends(owner)):
        runtime.personal_context.require_visible(principal)
        return principal

    @router.get("/jobs")
    def listing(task_id: str | None = None, principal=Depends(owner)):
        return {
            **runtime.jobs.capabilities(),
            "jobs": runtime.jobs.listing(
                task_id, review=runtime.personal_context.visible(principal)
            ),
        }

    @router.post("/jobs", dependencies=[Depends(visible)])
    def prepare(payload: JobInput, key=Depends(operation_id)):
        return runtime.jobs.prepare(payload, key)

    @router.get("/jobs/{job_id}")
    def detail(job_id: str, principal=Depends(owner)):
        return {
            "job": runtime.jobs.detail(job_id, review=runtime.personal_context.visible(principal))
        }

    @router.post("/jobs/{job_id}/approve", dependencies=[Depends(visible)])
    def approve(job_id: str, payload: JobApproval, key=Depends(operation_id)):
        return runtime.jobs.approve(job_id, payload, key)

    @router.post("/jobs/{job_id}/cancel")
    def cancel(job_id: str, key=Depends(operation_id)):
        return runtime.jobs.cancel(job_id, key)

    @router.post("/jobs/{job_id}/reconcile")
    def reconcile(job_id: str):
        return runtime.jobs.reconcile(job_id)

    return router
