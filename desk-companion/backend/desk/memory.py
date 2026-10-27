"""Owner-reviewed personal facts. The model may read them and prepare drafts only.

Active facts are the assistant's long-term memory. A draft does not write.
The same wording is stored once. A correction keeps the previous wording.
Expired and superseded facts stay visible to the owner and leave the model context.
Deletion hides a fact from every later model context. A paired display does not read this.
"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError

MAX_ACTIVE = 200
MAX_MODEL = 40
ORIGINS = {"owner", "assistant_confirmed", "conversation"}
_EDGE = ".,;:。，；：!！"


def fact_key(body: str) -> str:
    """Identity used to notice the same fact. The stored wording is not rewritten."""
    collapsed = " ".join(body.casefold().split())
    trimmed = collapsed.strip(_EDGE)
    return trimmed or collapsed


def parse_expiry(value):
    """Timezone-aware instant, or None to clear. Past times expire on the next read."""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise DomainError("INVALID_EXPIRY", 422)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DomainError("INVALID_EXPIRY", 422) from None
    if parsed.tzinfo is None or not 2000 <= parsed.year <= 2100:
        raise DomainError("INVALID_EXPIRY", 422)
    return iso(parsed)


class MemoryText(StrictModel):
    body: str = Field(min_length=1, max_length=500)

    @field_validator("body")
    @classmethod
    def readable(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Memory text is required")
        return value


class MemoryCreate(MemoryText):
    expires_at: str | None = None


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


class MemoryExpiry(MemoryVersion):
    expires_at: str | None = None


class MemoryConsolidate(StrictModel):
    keep_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    retire_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("retire_ids")
    @classmethod
    def unique_ids(cls, value):
        for item in value:
            if len(item) != 32 or any(char not in "0123456789abcdef" for char in item):
                raise ValueError("Invalid memory id")
        if len(set(value)) != len(value):
            raise ValueError("Repeated memory id")
        return value


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
                    deleted_at TEXT,
                    attribution TEXT NOT NULL DEFAULT '',
                    expires_at TEXT,
                    supersedes_id TEXT,
                    superseded_by TEXT
                );
                CREATE INDEX IF NOT EXISTS owner_memories_active
                    ON owner_memories(state, updated_at);
                CREATE TABLE IF NOT EXISTS memory_revisions(
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            have = {row["name"] for row in conn.execute("PRAGMA table_info(owner_memories)")}
            for name, ddl in (
                ("attribution", "TEXT NOT NULL DEFAULT ''"),
                ("expires_at", "TEXT"),
                ("supersedes_id", "TEXT"),
                ("superseded_by", "TEXT"),
            ):
                if name not in have:
                    conn.execute(f"ALTER TABLE owner_memories ADD COLUMN {name} {ddl}")

    def _view(self, row, previous="", retired=0):
        return {
            "id": row["id"],
            "body": row["body"],
            "source": row["source"],
            "note": row["attribution"] or "",
            "state": row["state"],
            "version": row["version"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
            "supersedes_id": row["supersedes_id"],
            "superseded_by": row["superseded_by"],
            "previous_body": previous or None,
            "retired_duplicates": retired,
        }

    def _previous(self, conn, memory_id):
        found = conn.execute(
            "SELECT body FROM memory_revisions WHERE memory_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (memory_id,),
        ).fetchone()
        return found["body"] if found else ""

    def _retired_count(self, conn, memory_id):
        return conn.execute(
            "SELECT COUNT(*) FROM owner_memories WHERE superseded_by=?",
            (memory_id,),
        ).fetchone()[0]

    def _present(self, conn, memory_id):
        row = conn.execute("SELECT * FROM owner_memories WHERE id=?", (memory_id,)).fetchone()
        if not row or row["state"] == "deleted":
            raise DomainError("MEMORY_NOT_FOUND", 404)
        return row

    def _active(self, conn, memory_id):
        row = self._present(conn, memory_id)
        now = iso(self.store.clock())
        if row["state"] != "active" or (row["expires_at"] and row["expires_at"] <= now):
            raise DomainError("MEMORY_NOT_FOUND", 404)
        return row

    def _same_active(self, conn, text, ignore_id=None):
        now = iso(self.store.clock())
        key = fact_key(text)
        rows = conn.execute("SELECT * FROM owner_memories WHERE state='active'").fetchall()
        for row in rows:
            if row["id"] == ignore_id or (row["expires_at"] and row["expires_at"] <= now):
                continue
            if fact_key(row["body"]) == key:
                return row
        return None

    def _pack(self, conn, row):
        return self._view(
            row,
            previous=self._previous(conn, row["id"]),
            retired=self._retired_count(conn, row["id"]),
        )

    def listing(self):
        now = iso(self.store.clock())
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM owner_memories WHERE state!='deleted' ORDER BY updated_at DESC, id"
            ).fetchall()
            previous = {}
            for revision in conn.execute(
                "SELECT memory_id, body FROM memory_revisions ORDER BY created_at DESC, id DESC"
            ):
                previous.setdefault(revision["memory_id"], revision["body"])
            retired = {
                row["superseded_by"]: row["count"]
                for row in conn.execute(
                    "SELECT superseded_by, COUNT(*) AS count FROM owner_memories "
                    "WHERE state='superseded' AND superseded_by IS NOT NULL "
                    "GROUP BY superseded_by"
                )
            }
        active, expired, retired_rows = [], [], []
        for row in rows:
            view = self._view(
                row,
                previous=previous.get(row["id"], ""),
                retired=retired.get(row["id"], 0),
            )
            if row["state"] == "superseded":
                retired_rows.append(view)
            elif row["state"] == "expired" or (row["expires_at"] and row["expires_at"] <= now):
                expired.append(view)
            elif row["state"] == "active":
                active.append(view)
        return {
            "memories": active,
            "expired": expired,
            "retired": retired_rows[:20],
            "suggestions": suggestions_for(active),
        }

    def for_model(self):
        """Facts the hosted model may see. Deleted, expired, and superseded rows are absent."""
        now = iso(self.store.clock())
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id, version, body, updated_at, source FROM owner_memories "
                "WHERE state='active' AND (expires_at IS NULL OR expires_at>?) "
                "ORDER BY updated_at DESC, id LIMIT ?",
                (now, MAX_MODEL),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, body, key, origin="owner", note="", expires_at=None):
        text = MemoryText(body=body).body
        if origin not in ORIGINS:
            raise DomainError("TOOL_ARGUMENTS_INVALID", 422)
        expiry = parse_expiry(expires_at)
        attribution = " ".join(str(note).split())[:160]

        def apply(conn):
            match = self._same_active(conn, text)
            if match:
                return {"memory": self._pack(conn, match), "saved": True, "duplicate": True}
            active = conn.execute(
                "SELECT COUNT(*) FROM owner_memories WHERE state='active'"
            ).fetchone()[0]
            if active >= MAX_ACTIVE:
                raise DomainError("MEMORY_LIMIT", 422)
            now = iso(self.store.clock())
            memory_id = uuid4().hex
            conn.execute(
                "INSERT INTO owner_memories("
                "id, body, source, state, version, created_at, updated_at, deleted_at, "
                "attribution, expires_at, supersedes_id, superseded_by"
                ") VALUES(?,?,?,'active',1,?,?,NULL,?,?,NULL,NULL)",
                (memory_id, text, origin, now, now, attribution, expiry),
            )
            self.store.record(conn, "memory_saved", details={"memory_id": memory_id})
            row = conn.execute("SELECT * FROM owner_memories WHERE id=?", (memory_id,)).fetchone()
            return {"memory": self._pack(conn, row), "saved": True, "duplicate": False}

        return self.store.operation(
            key,
            {
                "type": "memory_save",
                "body": text,
                "origin": origin,
                "note": attribution,
                "expires_at": expiry,
            },
            apply,
        )

    def replace(self, memory_id, body, expected_version, key, origin="owner"):
        text = MemoryText(body=body).body
        if origin not in ORIGINS:
            raise DomainError("TOOL_ARGUMENTS_INVALID", 422)

        def apply(conn):
            row = self._active(conn, memory_id)
            if row["version"] != expected_version:
                raise DomainError("VERSION_CONFLICT")
            if self._same_active(conn, text, ignore_id=memory_id):
                raise DomainError("MEMORY_DUPLICATE", 409)
            if row["body"] == text:
                return {"memory": self._pack(conn, row), "saved": True}
            now = iso(self.store.clock())
            conn.execute(
                "INSERT INTO memory_revisions VALUES(?,?,?,?,?)",
                (uuid4().hex, memory_id, row["body"], row["source"], now),
            )
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
            updated = conn.execute(
                "SELECT * FROM owner_memories WHERE id=?", (memory_id,)
            ).fetchone()
            return {"memory": self._pack(conn, updated), "saved": True}

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

    def set_expiry(self, memory_id, expected_version, expires_at, key):
        expiry = parse_expiry(expires_at)

        def apply(conn):
            row = self._active(conn, memory_id)
            if row["version"] != expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["expires_at"] == expiry:
                return {"memory": self._pack(conn, row), "saved": True}
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE owner_memories SET expires_at=?, version=version+1, updated_at=? WHERE id=?",
                (expiry, now, memory_id),
            )
            self.store.record(conn, "memory_expiry", details={"memory_id": memory_id})
            updated = conn.execute(
                "SELECT * FROM owner_memories WHERE id=?", (memory_id,)
            ).fetchone()
            return {"memory": self._pack(conn, updated), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_expiry",
                "memory_id": memory_id,
                "expected_version": expected_version,
                "expires_at": expiry,
            },
            apply,
        )

    def delete(self, memory_id, expected_version, key):
        def apply(conn):
            row = self._present(conn, memory_id)
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

    def expire_due(self) -> None:
        """Mark active facts whose saved expiry has passed. Idempotent across ticks."""
        now = iso(self.store.clock())
        with self.store.connection(write=True) as conn:
            cursor = conn.execute(
                "UPDATE owner_memories SET state='expired', version=version+1, updated_at=? "
                "WHERE state='active' AND expires_at IS NOT NULL AND expires_at<=?",
                (now, now),
            )
            if cursor.rowcount:
                self.store.record(conn, "memory_expired", details={"count": cursor.rowcount})
                self.store.bump(conn)

    def prepare_consolidation(self, keep_id, retire_ids, key):
        """Draft that retires exact duplicate facts. Confirming uses the existing proposal path."""
        match = next(
            (
                item
                for item in self.listing()["suggestions"]
                if item["keep"]["id"] == keep_id
                and {row["id"] for row in item["retire"]} == set(retire_ids)
            ),
            None,
        )
        if not match:
            raise DomainError("MEMORY_REVIEW_STALE", 409)
        payload = {
            "keep_id": match["keep"]["id"],
            "keep_version": match["keep"]["version"],
            "keep_body": match["keep"]["body"],
            "retire": [
                {
                    "memory_id": row["id"],
                    "expected_version": row["version"],
                    "body": row["body"],
                }
                for row in match["retire"]
            ],
            "reason_en": match["reason_en"],
            "reason_zh": match["reason_zh"],
        }
        return self.runtime.assistant.propose("memory_consolidate", payload, key)

    def supersede(self, keep_id, keep_version, retire, key):
        def apply(conn):
            keep = self._active(conn, keep_id)
            if keep["version"] != keep_version or not retire:
                raise DomainError("VERSION_CONFLICT")
            rows = []
            for item in retire:
                row = self._active(conn, item["memory_id"])
                if (
                    row["version"] != item["expected_version"]
                    or row["id"] == keep_id
                    or fact_key(row["body"]) != fact_key(keep["body"])
                ):
                    raise DomainError("MEMORY_REVIEW_STALE", 409)
                rows.append(row)
            now = iso(self.store.clock())
            for row in rows:
                conn.execute(
                    "UPDATE owner_memories SET state='superseded', superseded_by=?, "
                    "version=version+1, updated_at=? WHERE id=?",
                    (keep_id, now, row["id"]),
                )
            supersedes = keep["supersedes_id"] or rows[0]["id"]
            conn.execute(
                "UPDATE owner_memories SET supersedes_id=?, version=version+1, updated_at=? "
                "WHERE id=?",
                (supersedes, now, keep_id),
            )
            self.store.record(
                conn,
                "memory_consolidated",
                details={"memory_id": keep_id, "retired": len(rows)},
            )
            updated = conn.execute(
                "SELECT * FROM owner_memories WHERE id=?", (keep_id,)
            ).fetchone()
            return {
                "memory": self._pack(conn, updated),
                "retired": [row["id"] for row in rows],
                "saved": True,
            }

        return self.store.operation(
            key,
            {
                "type": "memory_consolidate",
                "keep_id": keep_id,
                "keep_version": keep_version,
                "retire": retire,
            },
            apply,
        )


def suggestions_for(active):
    """Exact-wording groups. The newest fact is the one a review can keep."""
    groups = {}
    for fact in active:
        groups.setdefault(fact_key(fact["body"]), []).append(fact)
    suggestions = []
    for facts in groups.values():
        if len(facts) < 2:
            continue
        ordered = sorted(facts, key=lambda item: (item["updated_at"], item["id"]), reverse=True)
        suggestions.append(
            {
                "kind": "duplicate",
                "reason_en": (
                    "These facts use the same wording. You can keep the newest and retire the others."
                ),
                "reason_zh": "这些事实文字相同。可以保留最新的一条，并停用其余几条。",
                "keep": ordered[0],
                "retire": ordered[1:],
            }
        )
    return suggestions


def memory_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/memory", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.memory.listing()

    @router.post("")
    def create(payload: MemoryCreate, key=Depends(operation_id)):
        return runtime.memory.create(
            payload.body, key, origin="owner", expires_at=payload.expires_at
        )

    @router.post("/consolidation")
    def consolidate(payload: MemoryConsolidate, key=Depends(operation_id)):
        return runtime.memory.prepare_consolidation(payload.keep_id, payload.retire_ids, key)

    @router.post("/{memory_id}/revisions")
    def replace(memory_id: str, payload: MemoryRevision, key=Depends(operation_id)):
        return runtime.memory.replace(
            memory_id, payload.body, payload.expected_version, key, origin="owner"
        )

    @router.post("/{memory_id}/expiry")
    def expiry(memory_id: str, payload: MemoryExpiry, key=Depends(operation_id)):
        return runtime.memory.set_expiry(
            memory_id, payload.expected_version, payload.expires_at, key
        )

    @router.post("/{memory_id}/deletions")
    def delete(memory_id: str, payload: MemoryVersion, key=Depends(operation_id)):
        return runtime.memory.delete(memory_id, payload.expected_version, key)

    return router
