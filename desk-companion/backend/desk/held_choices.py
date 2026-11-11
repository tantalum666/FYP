"""A choice the owner is holding, and the assumption it rests on.

Preparing a choice does not make it current. Approving the exact wording does.
Replacing the assumption keeps the previous wording readable and leaves it
current until the owner approves the new wording. Nothing is mailed, bought,
or booked, and no task is completed.
"""

import hashlib
import json
import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator, model_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode

OWNER_COOKIE = "desk_companion_session"
_FIELDS = ("title", "assumption", "choice", "reason")
_LIMITS = {"title": 160, "assumption": 500, "choice": 500, "reason": 500}
_OPEN = ("pending", "current")
_MAX_LINEAGES = 100
_MAX_VERSIONS = 20
_EFFECTS = {"live_effect": False, "mailed": False, "purchased": False, "booked": False}


def _collapse(value: str, limit: int) -> str:
    collapsed = " ".join(value.split())
    if not collapsed or len(collapsed) > limit:
        raise ValueError("blank or too long")
    return collapsed


def _norm(parts: dict) -> str:
    return encode([parts[key].casefold() for key in _FIELDS])


class ChoiceDraft(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    assumption: str = Field(min_length=1, max_length=500)
    choice: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator(*_FIELDS)
    @classmethod
    def collapsed(cls, value, info):
        return _collapse(value, _LIMITS[info.field_name])


class ChoiceReplace(StrictModel):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=160)
    assumption: str | None = Field(default=None, max_length=500)
    choice: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def null_does_not_clear(cls, value):
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("null does not clear a field")
        return value

    @field_validator(*_FIELDS)
    @classmethod
    def collapsed(cls, value, info):
        if value is None:
            return None
        return _collapse(value, _LIMITS[info.field_name])


class ChoiceApproval(ChoiceDraft):
    expected_version: int = Field(ge=1)


class ChoiceWithdraw(StrictModel):
    target: str = Field(pattern="^(pending|current)$")
    expected_version: int = Field(ge=1)


class HeldChoiceService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.interrupt_after_intent = False
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS held_choices (
                    id TEXT PRIMARY KEY,
                    lineage_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    title TEXT NOT NULL,
                    assumption TEXT NOT NULL,
                    choice_text TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    norm TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(lineage_id, version)
                );
                CREATE INDEX IF NOT EXISTS held_choices_lineage ON held_choices(lineage_id, version);
                CREATE INDEX IF NOT EXISTS held_choices_open_norm ON held_choices(norm, state);
                CREATE TABLE IF NOT EXISTS held_choice_effects (
                    operation_id TEXT PRIMARY KEY,
                    request TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL
                );
                """
            )

    def listing(self, token):
        with self.store.connection() as conn:
            self._visible(conn, token)
            rows = conn.execute("SELECT * FROM held_choices ORDER BY version").fetchall()
        grouped: dict[str, list] = {}
        for row in rows:
            grouped.setdefault(row["lineage_id"], []).append(row)
        lines = [self._line(versions) for versions in grouped.values()]
        lines = [line for line in lines if line["current"] or line["pending"] or line["previous"]]
        lines.sort(key=lambda line: line["updated_at"], reverse=True)
        return {"choices": lines, **_EFFECTS}

    def prepare(self, draft: ChoiceDraft, key, token):
        parts = draft.model_dump()

        def plan(conn):
            norm = _norm(parts)
            open_row = self._open_with_norm(conn, norm)
            if open_row:
                return {
                    "action": "reuse",
                    "lineage_id": open_row["lineage_id"],
                    "version_id": open_row["id"],
                }
            count = conn.execute("SELECT COUNT(DISTINCT lineage_id) FROM held_choices").fetchone()[
                0
            ]
            if count >= _MAX_LINEAGES:
                raise DomainError("CHOICE_LIMIT", 422)
            return {
                "action": "create",
                "lineage_id": uuid4().hex,
                "version_id": uuid4().hex,
                "version": 1,
                **parts,
                "norm": norm,
            }

        return self._run(key, {"kind": "prepare", **parts}, token, "prepare", plan)

    def replace(self, lineage_id, patch: ChoiceReplace, key, token):
        provided = patch.model_dump(exclude_unset=True)
        text = {name: value for name, value in provided.items() if name in _FIELDS}

        def plan(conn):
            if not text:
                raise DomainError("CHOICE_UNCHANGED", 422)
            versions = self._versions(conn, lineage_id)
            current = self._one(versions, "current")
            if current["version"] != patch.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if self._one(versions, "pending", required=False):
                raise DomainError("CHOICE_REVISION_OPEN")
            merged = self._parts(current)
            merged.update(text)
            if merged == self._parts(current):
                raise DomainError("CHOICE_UNCHANGED", 422)
            version = max(row["version"] for row in versions) + 1
            if version > _MAX_VERSIONS:
                raise DomainError("CHOICE_LIMIT", 422)
            return {
                "action": "replace",
                "lineage_id": lineage_id,
                "version_id": uuid4().hex,
                "version": version,
                **merged,
                "norm": _norm(merged),
            }

        return self._run(
            key, {"kind": "replace", "id": lineage_id, **provided}, token, "replace", plan
        )

    def approve(self, lineage_id, approval: ChoiceApproval, key, token):
        parts = {name: approval.model_dump()[name] for name in _FIELDS}

        def plan(conn):
            versions = self._versions(conn, lineage_id)
            pending = self._one(versions, "pending")
            if pending["version"] != approval.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if self._parts(pending) != parts:
                raise DomainError("CHOICE_TEXT_MISMATCH")
            return {
                "action": "approve",
                "lineage_id": lineage_id,
                "version_id": pending["id"],
            }

        stored = {
            "kind": "approve",
            "id": lineage_id,
            "expected_version": approval.expected_version,
            **parts,
        }
        return self._run(key, stored, token, "approve", plan)

    def withdraw(self, lineage_id, payload: ChoiceWithdraw, key, token):
        def plan(conn):
            versions = self._versions(conn, lineage_id)
            if payload.target == "current" and self._one(versions, "pending", required=False):
                raise DomainError("CHOICE_REVISION_OPEN")
            target = self._one(versions, payload.target)
            if target["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            return {
                "action": "withdraw",
                "lineage_id": lineage_id,
                "version_id": target["id"],
                "target": payload.target,
            }

        stored = {
            "kind": "withdraw",
            "id": lineage_id,
            "target": payload.target,
            "expected_version": payload.expected_version,
        }
        return self._run(key, stored, token, "withdraw", plan)

    def _run(self, key, stored, token, kind, plan):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        request = encode(stored)
        created = False
        with self.store.connection() as conn:
            self._visible(conn, token)
            finished = self._finished(conn, key, request)
            if finished is not None:
                return finished
            effect = self._effect(conn, key, request)
        if effect is None:
            with self.store.connection(write=True) as conn:
                self._visible(conn, token)
                finished = self._finished(conn, key, request)
                if finished is not None:
                    return finished
                effect = self._effect(conn, key, request)
                if effect is None:
                    self._visible(conn, token)
                    body = plan(conn)
                    try:
                        conn.execute(
                            "INSERT INTO held_choice_effects VALUES(?,?,?,?,?)",
                            (key, request, "intent", kind, encode(body)),
                        )
                    except sqlite3.IntegrityError:
                        effect = self._effect(conn, key, request)
                        if effect is None:
                            raise
                    else:
                        created = True
        if created and self.interrupt_after_intent:
            self.interrupt_after_intent = False
            raise DomainError("INTERRUPTED", 409)

        def apply(conn):
            self._visible(conn, token)
            effect_row = self._effect(conn, key, request)
            if effect_row is None:
                raise DomainError("INTERRUPTED", 409)
            result = self._finish(conn, json.loads(effect_row["body"]))
            conn.execute(
                "UPDATE held_choice_effects SET phase='done' WHERE operation_id=?",
                (key,),
            )
            return result

        try:
            return self.store.operation(key, stored, apply)
        except sqlite3.IntegrityError:
            with self.store.connection() as conn:
                finished = self._finished(conn, key, request)
            if finished is not None:
                return finished
            raise

    def _finish(self, conn, body):
        action = body["action"]
        if action == "reuse":
            versions = self._versions(conn, body["lineage_id"])
            return self._response(versions, reused=True)
        if action == "create":
            existing = self._open_with_norm(conn, body["norm"])
            if existing:
                return self._response(self._versions(conn, existing["lineage_id"]), reused=True)
            self._insert(conn, body, "pending")
            return self._response(self._versions(conn, body["lineage_id"]), reused=False)
        if action == "replace":
            versions = self._versions(conn, body["lineage_id"])
            if self._one(versions, "pending", required=False):
                pending = self._one(versions, "pending")
                if pending["id"] == body["version_id"]:
                    return self._response(versions, reused=False)
                raise DomainError("CHOICE_REVISION_OPEN")
            self._insert(conn, body, "pending")
            return self._response(self._versions(conn, body["lineage_id"]), reused=False)
        if action == "approve":
            versions = self._versions(conn, body["lineage_id"])
            pending = self._one(versions, "pending", required=False)
            if pending is None or pending["id"] != body["version_id"]:
                current = self._one(versions, "current", required=False)
                if current and current["id"] == body["version_id"]:
                    return self._response(versions, reused=True)
                raise DomainError("CHOICE_TEXT_MISMATCH")
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE held_choices SET state='previous', updated_at=? WHERE lineage_id=? AND state='current'",
                (now, body["lineage_id"]),
            )
            updated = conn.execute(
                "UPDATE held_choices SET state='current', updated_at=? WHERE id=? AND state='pending'",
                (now, body["version_id"]),
            )
            if updated.rowcount != 1:
                raise DomainError("CHOICE_TEXT_MISMATCH")
            return self._response(self._versions(conn, body["lineage_id"]), reused=False)
        versions = self._versions(conn, body["lineage_id"])
        target = next((row for row in versions if row["id"] == body["version_id"]), None)
        if target is None:
            raise DomainError("CHOICE_NOT_FOUND", 404)
        if target["state"] == "withdrawn":
            return self._response(versions, reused=True)
        if target["state"] != body["target"]:
            raise DomainError("VERSION_CONFLICT")
        conn.execute(
            "UPDATE held_choices SET state='withdrawn', updated_at=? WHERE id=? AND state=?",
            (iso(self.store.clock()), body["version_id"], body["target"]),
        )
        return self._response(self._versions(conn, body["lineage_id"]), reused=False)

    def _insert(self, conn, body, state):
        now = iso(self.store.clock())
        conn.execute(
            "INSERT INTO held_choices VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                body["version_id"],
                body["lineage_id"],
                body["version"],
                state,
                body["title"],
                body["assumption"],
                body["choice"],
                body["reason"],
                body["norm"],
                now,
                now,
            ),
        )

    def _response(self, versions, *, reused):
        line = self._line(versions)
        return {**_EFFECTS, "reused": reused, "held": line["current"] is not None, "choice": line}

    def _line(self, versions):
        current = self._public(self._one(versions, "current", required=False))
        pending = self._public(self._one(versions, "pending", required=False))
        previous = [
            self._public(row)
            for row in sorted(versions, key=lambda row: row["version"], reverse=True)
            if row["state"] == "previous"
        ]
        updated = max(row["updated_at"] for row in versions)
        return {
            "id": versions[0]["lineage_id"],
            "current": current,
            "pending": pending,
            "previous": previous[:8],
            "held": current is not None,
            "updated_at": updated,
            **_EFFECTS,
        }

    @staticmethod
    def _public(row):
        if row is None:
            return None
        return {
            "id": row["id"],
            "version": row["version"],
            "state": row["state"],
            "title": row["title"],
            "assumption": row["assumption"],
            "choice": row["choice_text"],
            "reason": row["reason"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _parts(row):
        return {key: row["choice_text"] if key == "choice" else row[key] for key in _FIELDS}

    @staticmethod
    def _one(versions, state, required=True):
        found = [row for row in versions if row["state"] == state]
        if len(found) != 1:
            if required:
                raise DomainError("CHOICE_NOT_FOUND", 404)
            return None
        return found[0]

    def _versions(self, conn, lineage_id):
        if not isinstance(lineage_id, str) or len(lineage_id) != 32 or not lineage_id.isalnum():
            raise DomainError("CHOICE_NOT_FOUND", 404)
        rows = conn.execute(
            "SELECT * FROM held_choices WHERE lineage_id=? ORDER BY version",
            (lineage_id,),
        ).fetchall()
        if not rows:
            raise DomainError("CHOICE_NOT_FOUND", 404)
        return rows

    @staticmethod
    def _open_with_norm(conn, norm):
        return conn.execute(
            "SELECT * FROM held_choices WHERE norm=? AND state IN ('pending','current') LIMIT 1",
            (norm,),
        ).fetchone()

    def _visible(self, conn, token):
        if not token:
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (digest, iso(self.store.clock())),
        ).fetchone()
        if not row:
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if self.store.settings(conn).get("hide_private"):
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)

    @staticmethod
    def _effect(conn, key, request):
        row = conn.execute(
            "SELECT * FROM held_choice_effects WHERE operation_id=?",
            (key,),
        ).fetchone()
        if row and row["request"] != request:
            raise DomainError("OPERATION_ID_CONFLICT")
        return row

    def _finished(self, conn, key, request):
        row = conn.execute("SELECT request, response FROM operations WHERE id=?", (key,)).fetchone()
        if not row:
            return None
        if row["request"] != request:
            raise DomainError("OPERATION_ID_CONFLICT")
        return json.loads(row["response"])


def held_choice_routes(runtime, owner, operation_id):
    def visible_owner(principal=Depends(owner)):
        runtime.personal_context.require_visible(principal)

    router = APIRouter(prefix="/api/held-choices", dependencies=[Depends(visible_owner)])

    def token(request: Request) -> str | None:
        return request.cookies.get(OWNER_COOKIE)

    @router.get("")
    def listing(session=Depends(token)):
        return runtime.held_choices.listing(session)

    @router.post("")
    def prepare(payload: ChoiceDraft, session=Depends(token), key=Depends(operation_id)):
        return runtime.held_choices.prepare(payload, key, session)

    @router.post("/{lineage_id}/replacements")
    def replace(
        lineage_id: str, payload: ChoiceReplace, session=Depends(token), key=Depends(operation_id)
    ):
        return runtime.held_choices.replace(lineage_id, payload, key, session)

    @router.post("/{lineage_id}/approval")
    def approve(
        lineage_id: str, payload: ChoiceApproval, session=Depends(token), key=Depends(operation_id)
    ):
        return runtime.held_choices.approve(lineage_id, payload, key, session)

    @router.post("/{lineage_id}/withdrawal")
    def withdraw(
        lineage_id: str, payload: ChoiceWithdraw, session=Depends(token), key=Depends(operation_id)
    ):
        return runtime.held_choices.withdraw(lineage_id, payload, key, session)

    return router
