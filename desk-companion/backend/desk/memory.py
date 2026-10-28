"""Owner-reviewed personal facts. The model may read them and prepare drafts only.

Active facts are the assistant's long-term memory. A draft does not write.
Deletion hides a fact from every later model context. The owner edits directly;
a paired display does not.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError

MAX_ACTIVE = 200
MAX_MODEL = 40


class MemoryQuery(StrictModel):
    query: str | None = None

    @field_validator("query")
    @classmethod
    def compact_query(cls, value):
        if value is None:
            return None
        text = " ".join(value.split())
        if not text:
            raise ValueError("Memory query is empty")
        if len(text) > 80:
            raise ValueError("Memory query is too long")
        return text


class MemoryText(StrictModel):
    body: str = Field(min_length=1, max_length=500)

    @field_validator("body")
    @classmethod
    def readable(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Memory text is required")
        return value


class MemoryRevision(MemoryText):
    expected_version: int = Field(ge=1, strict=True)


class MemorySaveDraft(MemoryText):
    pass


class MemoryReplaceDraft(MemoryRevision):
    memory_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class MemoryVersion(StrictModel):
    expected_version: int = Field(ge=1, strict=True)


class MemoryDeleteDraft(MemoryVersion):
    memory_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class MemoryService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS owner_memories(
                    id TEXT PRIMARY KEY,
                    body TEXT NOT NULL,
                    source TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS owner_memories_active
                    ON owner_memories(state, updated_at);
                """
            )

    def _view(self, row):
        return {
            "id": row["id"],
            "body": row["body"],
            "source": row["source"],
            "state": row["state"],
            "version": row["version"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _active(self, conn, memory_id):
        row = conn.execute("SELECT * FROM owner_memories WHERE id=?", (memory_id,)).fetchone()
        if not row or row["state"] != "active":
            raise DomainError("MEMORY_NOT_FOUND", 404)
        return row

    def listing(self):
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM owner_memories WHERE state='active' ORDER BY updated_at DESC, id"
            ).fetchall()
        return {"memories": [self._view(row) for row in rows]}

    def for_model(self):
        """Facts the hosted model may see. Deleted rows are absent, not redacted in place."""
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id, version, body, updated_at FROM owner_memories "
                "WHERE state='active' ORDER BY updated_at DESC, id LIMIT ?",
                (MAX_MODEL,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, body, key, origin="owner"):
        text = MemoryText(body=body).body

        def apply(conn):
            active = conn.execute(
                "SELECT COUNT(*) FROM owner_memories WHERE state='active'"
            ).fetchone()[0]
            if active >= MAX_ACTIVE:
                raise DomainError("MEMORY_LIMIT", 422)
            now = iso(self.store.clock())
            memory_id = uuid4().hex
            conn.execute(
                "INSERT INTO owner_memories VALUES(?,?,?,'active',1,?,?,NULL)",
                (memory_id, text, origin, now, now),
            )
            self.store.record(conn, "memory_saved", details={"memory_id": memory_id})
            row = conn.execute("SELECT * FROM owner_memories WHERE id=?", (memory_id,)).fetchone()
            return {"memory": self._view(row), "saved": True}

        return self.store.operation(
            key, {"type": "memory_save", "body": text, "origin": origin}, apply
        )

    def replace(self, memory_id, body, expected_version, key, origin="owner"):
        text = MemoryText(body=body).body

        def apply(conn):
            row = self._active(conn, memory_id)
            if row["version"] != expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["body"] == text:
                return {"memory": self._view(row), "saved": True}
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE owner_memories SET body=?, source=?, version=version+1, updated_at=? "
                "WHERE id=?",
                (text, origin, now, memory_id),
            )
            self.store.record(
                conn,
                "memory_replaced",
                details={"memory_id": memory_id, "version": expected_version + 1},
            )
            updated = conn.execute("SELECT * FROM owner_memories WHERE id=?", (memory_id,)).fetchone()
            return {"memory": self._view(updated), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_replace",
                "memory_id": memory_id,
                "body": text,
                "expected_version": expected_version,
                "origin": origin,
            },
            apply,
        )

    def delete(self, memory_id, expected_version, key):
        def apply(conn):
            row = self._active(conn, memory_id)
            if row["version"] != expected_version:
                raise DomainError("VERSION_CONFLICT")
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE owner_memories SET state='deleted', version=version+1, "
                "updated_at=?, deleted_at=? WHERE id=?",
                (now, now, memory_id),
            )
            self.store.record(conn, "memory_deleted", details={"memory_id": memory_id})
            return {"memory_id": memory_id, "state": "deleted", "saved": True}

        return self.store.operation(
            key,
            {"type": "memory_delete", "memory_id": memory_id, "expected_version": expected_version},
            apply,
        )


def memory_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/memory", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.memory.listing()

    @router.post("")
    def create(payload: MemoryText, key=Depends(operation_id)):
        return runtime.memory.create(payload.body, key, origin="owner")

    @router.post("/{memory_id}/revisions")
    def replace(memory_id: str, payload: MemoryRevision, key=Depends(operation_id)):
        return runtime.memory.replace(
            memory_id, payload.body, payload.expected_version, key, origin="owner"
        )

    @router.post("/{memory_id}/deletions")
    def delete(memory_id: str, payload: MemoryVersion, key=Depends(operation_id)):
        return runtime.memory.delete(memory_id, payload.expected_version, key)

    return router
