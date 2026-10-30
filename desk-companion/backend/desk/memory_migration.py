"""Explicit conversion of PR5 facts into the current canonical fact store."""

import re

from .memory import MAX_ACTIVE, MemoryService
from .store import DomainError, _check_migration_identity, _migration_path_identity


def migrate_personal_memories(store, *, acknowledged=False):
    if acknowledged is not True:
        raise DomainError("PERSONAL_MEMORY_MIGRATION_OPT_IN_REQUIRED", 422)
    identity = _migration_path_identity(store.directory)
    with store.connection(write=True) as conn:
        _check_migration_identity(store.directory, identity)
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_memories'"
        ).fetchone():
            return {"migrated": 0, "already_current": True}
        rows = list(conn.execute("SELECT * FROM personal_memories LIMIT 101"))
        if len(rows) > 100:
            raise DomainError("PERSONAL_MEMORY_MIGRATION_INVALID")
        for row in rows:
            if (
                not re.fullmatch(r"[a-f0-9]{32}", row["id"])
                or not isinstance(row["content"], str)
                or len(row["content"]) > 1000
                or row["category"] not in {"fact", "preference", "decision"}
                or row["source"] not in {"owner", "confirmed_assistant"}
                or type(row["version"]) is not int
                or row["version"] < 1
                or row["forgotten"] not in (0, 1)
            ):
                raise DomainError("PERSONAL_MEMORY_MIGRATION_INVALID")
        MemoryService.initialize_schema(conn)
        migrated = 0
        for row in rows:
            prior = conn.execute("SELECT * FROM owner_memories WHERE id=?", (row["id"],)).fetchone()
            state = "deleted" if row["forgotten"] else "active"
            body = "" if row["forgotten"] else row["content"]
            if prior:
                if (
                    prior["body"] != body
                    or prior["state"] != state
                    or prior["version"] != row["version"]
                ):
                    raise DomainError("PERSONAL_MEMORY_MIGRATION_CONFLICT")
                continue
            conn.execute(
                "INSERT INTO owner_memories(id,body,source,state,version,created_at,updated_at,deleted_at,attribution) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    row["id"],
                    body,
                    "owner" if row["source"] == "owner" else "assistant_confirmed",
                    state,
                    row["version"],
                    row["created_at"],
                    row["updated_at"],
                    row["updated_at"] if row["forgotten"] else None,
                    "Imported PR5 category: " + row["category"] if not row["forgotten"] else "",
                ),
            )
            migrated += 1
        if (
            conn.execute("SELECT COUNT(*) FROM owner_memories WHERE state='active'").fetchone()[0]
            > MAX_ACTIVE
        ):
            raise DomainError("MEMORY_LIMIT", 422)
        # Old bindings have different memory hashes and must be selected again.
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='personal_settings'").fetchone():
            conn.execute("UPDATE personal_settings SET epoch=epoch+1")
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='conversation_messages'"
        ).fetchone():
            conn.execute("UPDATE conversation_messages SET context_allowed=0")
        conn.execute("DROP TABLE personal_memories")
        _check_migration_identity(store.directory, identity)
    return {"migrated": migrated, "already_current": False}
