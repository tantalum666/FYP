"""Small editable owner-confirmed facts. Never an authority store."""

import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode


class MemoryInput(StrictModel):
    content: str = Field(min_length=1, max_length=1000)
    category: Literal["fact", "preference", "decision"] = "fact"


class MemoryAction(StrictModel):
    action: Literal["update", "forget"]
    expected_version: int = Field(ge=1)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: Literal["fact", "preference", "decision"] | None = None


class MemoryUpdate(MemoryInput):
    memory_id: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1)


class MemoryForget(StrictModel):
    memory_id: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1)


class MemoryService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.context = runtime.personal_context
        with self.store.connection(write=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS personal_memories(
                id TEXT PRIMARY KEY, content TEXT NOT NULL, category TEXT NOT NULL,
                version INTEGER NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, forgotten INTEGER NOT NULL DEFAULT 0)""")

    @staticmethod
    def view(row):
        return {
            k: row[k]
            for k in ("id", "content", "category", "version", "source", "created_at", "updated_at")
        }

    def listing(self, conn=None):
        if conn is None:
            with self.store.connection() as connection:
                return self.listing(connection)
        return {
            "memories": [
                self.view(r)
                for r in conn.execute(
                    "SELECT * FROM personal_memories WHERE forgotten=0 ORDER BY updated_at DESC,id LIMIT 100"
                )
            ]
        }

    def render(self, conn, receipt):
        row = conn.execute(
            "SELECT * FROM personal_memories WHERE id=? AND forgotten=0", (receipt["memory_id"],)
        ).fetchone()
        return {**receipt, "memory": self.view(row) if row else None}

    def _create(self, conn, payload, source):
        if (
            conn.execute("SELECT COUNT(*) FROM personal_memories WHERE forgotten=0").fetchone()[0]
            >= 100
        ):
            raise DomainError("MEMORY_LIMIT_REACHED", 422)
        memory_id, now = uuid4().hex, iso(self.store.clock())
        if not payload.content.strip():
            raise DomainError("MEMORY_CONTENT_REQUIRED", 422)
        conn.execute(
            "INSERT INTO personal_memories VALUES(?,?,?,1,?,?,?,0)",
            (memory_id, payload.content.strip(), payload.category, source, now, now),
        )
        self.context.invalidate(conn, exclude_history=False)
        return {"memory_id": memory_id, "saved": True}

    def create(self, payload, key):
        return self.context.operation(
            key,
            {"kind": "memory_create", **payload.model_dump()},
            lambda conn: self._create(conn, payload, "owner"),
            self.render,
        )

    def _action(self, conn, memory_id, payload, source=None):
        row = conn.execute(
            "SELECT * FROM personal_memories WHERE id=? AND forgotten=0", (memory_id,)
        ).fetchone()
        if not row:
            raise DomainError("MEMORY_NOT_FOUND", 404)
        if row["version"] != payload.expected_version:
            raise DomainError("VERSION_CONFLICT")
        if payload.action == "forget":
            conn.execute(
                "UPDATE personal_memories SET content='',forgotten=1,version=version+1,updated_at=? WHERE id=?",
                (iso(self.store.clock()), memory_id),
            )
        else:
            if not payload.content or not payload.content.strip():
                raise DomainError("MEMORY_CONTENT_REQUIRED", 422)
            conn.execute(
                "UPDATE personal_memories SET content=?,category=?,source=?,version=version+1,updated_at=? WHERE id=?",
                (
                    payload.content.strip(),
                    payload.category or row["category"],
                    source or "owner",
                    iso(self.store.clock()),
                    memory_id,
                ),
            )
        self.context.invalidate(conn)
        return {"memory_id": memory_id, "saved": True, "forgotten": payload.action == "forget"}

    def action(self, memory_id, payload, key):
        return self.context.operation(
            key,
            {"kind": "memory_action", "id": memory_id, **payload.model_dump()},
            lambda conn: self._action(conn, memory_id, payload),
            self.render,
        )

    def draft(self, kind, arguments, key):
        self.expire()
        schema = {
            "memory_create": MemoryInput,
            "memory_update": MemoryUpdate,
            "memory_forget": MemoryForget,
        }[kind]
        payload = schema.model_validate(arguments)

        def apply(conn):
            if kind != "memory_create":
                row = conn.execute(
                    "SELECT version FROM personal_memories WHERE id=? AND forgotten=0",
                    (payload.memory_id,),
                ).fetchone()
                if not row:
                    raise DomainError("MEMORY_NOT_FOUND", 404)
                if row["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT")
            active = conn.execute(
                "SELECT COUNT(*) FROM assistant_proposals WHERE state='pending' AND expires_at>?",
                (iso(self.store.clock()),),
            ).fetchone()[0]
            if active >= 20:
                raise DomainError("TOO_MANY_DRAFTS", 422)
            proposal_id = uuid4().hex
            conn.execute(
                "INSERT INTO assistant_proposals VALUES(?,?,?,'pending',?,?,NULL)",
                (
                    proposal_id,
                    kind,
                    encode(payload.model_dump()),
                    iso(self.store.clock() + timedelta(minutes=5)),
                    iso(self.store.clock()),
                ),
            )
            return {"proposal_id": proposal_id, "saved": False}

        def render(conn, receipt):
            row = conn.execute(
                "SELECT * FROM assistant_proposals WHERE id=?", (receipt["proposal_id"],)
            ).fetchone()
            return {**receipt, "proposal": self.runtime.assistant._view(row)}

        return self.context.operation(key, {"kind": kind, **payload.model_dump()}, apply, render)

    def decide(self, proposal_id, action, key):
        self.expire()

        def apply(conn):
            row = conn.execute(
                "SELECT * FROM assistant_proposals WHERE id=? AND kind LIKE 'memory_%'",
                (proposal_id,),
            ).fetchone()
            if not row:
                raise DomainError("DRAFT_NOT_FOUND", 404)
            if row["state"] == "confirmed":
                if action == "cancel":
                    raise DomainError("DRAFT_ALREADY_SAVED", 409)
                return json.loads(row["result"])
            if row["state"] == "cancelled" and action == "cancel":
                return {"state": "cancelled", "saved": False}
            if row["state"] != "pending" or row["expires_at"] <= iso(self.store.clock()):
                raise DomainError("DRAFT_EXPIRED", 410)
            payload = json.loads(row["data"])
            result = {"state": "cancelled", "saved": False, "kind": row["kind"]}
            if action == "confirm":
                if row["kind"] == "memory_create":
                    receipt = self._create(
                        conn, MemoryInput.model_validate(payload), "confirmed_assistant"
                    )
                else:
                    change = MemoryAction(
                        action="forget" if row["kind"] == "memory_forget" else "update",
                        **{k: v for k, v in payload.items() if k != "memory_id"},
                    )
                    receipt = self._action(
                        conn, payload["memory_id"], change, "confirmed_assistant"
                    )
                result |= receipt | {"state": "confirmed"}
            if action == "cancel":
                self.context.invalidate(conn, exclude_history=False, scrub_drafts=False)
            conn.execute(
                "UPDATE assistant_proposals SET state=?,data='{}',result=? WHERE id=?",
                (result["state"], encode(result), proposal_id),
            )
            return result

        return self.context.operation(
            key, {"kind": "memory_decision", "id": proposal_id, "action": action}, apply
        )

    def expire(self):
        with self.context.lock, self.store.connection(write=True) as conn:
            changed = conn.execute(
                "UPDATE assistant_proposals SET state='expired',data='{}' WHERE kind LIKE 'memory_%' AND state='pending' AND expires_at<=?",
                (iso(self.store.clock()),),
            )
            if changed.rowcount:
                self.context.invalidate(conn, exclude_history=False, scrub_drafts=False)
