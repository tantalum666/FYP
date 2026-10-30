"""Small editable owner-confirmed facts. Never an authority store."""

from typing import Literal

from pydantic import Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError


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


class PersonalMemoryAdapter:
    """Retained-context projection of the current canonical owner fact service."""

    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection() as conn:
            if conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_memories'"
            ).fetchone():
                raise DomainError("PERSONAL_MEMORY_MIGRATION_REQUIRED")

    @staticmethod
    def view(row):
        return {
            "id": row["id"],
            "content": row["body"],
            "category": "fact",
            "version": row["version"],
            "source": row["source"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def rows(self, conn):
        return [
            self.view(row)
            for row in conn.execute(
                "SELECT * FROM owner_memories WHERE state='active' "
                "AND (expires_at IS NULL OR expires_at>?) ORDER BY updated_at DESC,id",
                (iso(self.store.clock()),),
            )
        ]

    def get(self, conn, memory_id):
        return next((row for row in self.rows(conn) if row["id"] == memory_id), None)

    def listing(self, conn=None):
        if conn is None:
            with self.store.connection() as owned:
                return self.listing(owned)
        return {"memories": self.rows(conn)}

    def _result(self, result):
        memory_id = result.get("memory_id") or result.get("memory", {}).get("id")
        with self.store.connection() as conn:
            memory = self.get(conn, memory_id)
        # Fresh projection prevents a retry from resurrecting forgotten text.
        return {**result, "memory_id": memory_id, "memory": memory}

    def create(self, payload, key):
        return self._result(self.runtime.memory.create(payload.content, key))

    def action(self, memory_id, payload, key):
        if payload.action == "forget":
            result = self.runtime.memory.delete(memory_id, payload.expected_version, key)
            return {**self._result(result), "forgotten": True}
        if not payload.content or not payload.content.strip():
            raise DomainError("MEMORY_CONTENT_REQUIRED", 422)
        return self._result(
            self.runtime.memory.replace(memory_id, payload.content, payload.expected_version, key)
        )

    def draft(self, kind, arguments, key):
        schema, tool = {
            "memory_create": (MemoryInput, "memory_save_draft"),
            "memory_update": (MemoryUpdate, "memory_replace_draft"),
            "memory_forget": (MemoryForget, "memory_delete_draft"),
        }[kind]
        data = schema.model_validate(arguments).model_dump()
        data.pop("category", None)
        if "content" in data:
            data["body"] = data.pop("content")
        result = self.runtime.assistant.tool(tool, data, key, allow_memory=True)
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM assistant_proposals WHERE id=?", (result["proposal"]["id"],)
            ).fetchone()
            return {**result, "proposal": self.runtime.assistant._view(row)}

    def expire(self):
        self.runtime.memory.expire_due()
        personal = self.runtime.personal_context
        with personal.lock, self.store.connection(write=True) as conn:
            changed = conn.execute(
                "UPDATE assistant_proposals SET data='{}',state=CASE WHEN state='pending' THEN 'expired' ELSE state END "
                "WHERE kind LIKE 'memory_%' AND data!='{}' AND "
                "(state IN ('cancelled','expired') OR (state='pending' AND expires_at<=?))",
                (iso(self.store.clock()),),
            )
            if changed.rowcount:
                personal.invalidate(conn, exclude_history=False, scrub_drafts=False)
