"""Both historical fact stores converge on the current canonical data contract."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from desk.memory import MemoryService
from desk.memory_migration import migrate_personal_memories
from desk.personal_memory import MemoryAction
from desk.runtime import Runtime
from desk.store import DomainError, Store


def legacy_table(store, *, memory_id=None, body="Original PR5 preference", forgotten=0):
    memory_id = memory_id or uuid4().hex
    with store.connection(write=True) as conn:
        conn.execute("""CREATE TABLE personal_memories(
            id TEXT PRIMARY KEY, content TEXT NOT NULL, category TEXT NOT NULL,
            version INTEGER NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, forgotten INTEGER NOT NULL DEFAULT 0)""")
        conn.execute(
            "INSERT INTO personal_memories VALUES(?,?,?,2,?,?,?,?)",
            (
                memory_id,
                body,
                "preference",
                "confirmed_assistant",
                "2026-10-12T10:00:00.000000Z",
                "2026-10-13T10:00:00.000000Z",
                forgotten,
            ),
        )
    return memory_id


def test_current_facts_revisions_expiry_and_forgetting_share_one_store(tmp_path):
    now = [datetime(2026, 10, 31, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, clock=lambda: now[0], password="fixture-only"))
    fact = runtime.memory.create("Original current fact", "create")["memory"]
    runtime.memory.replace(fact["id"], "Corrected current fact", 1, "correct")
    runtime.memory.set_expiry(fact["id"], 2, (now[0] + timedelta(hours=1)).isoformat(), "expiry")
    current = runtime.memories.listing()["memories"][0]
    assert current["id"] == fact["id"] and current["version"] == 3
    assert current["content"] == "Corrected current fact"
    with runtime.store.connection() as conn:
        assert (
            conn.execute("SELECT body FROM memory_revisions").fetchone()[0]
            == "Original current fact"
        )
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='personal_memories'"
        ).fetchone()
    now[0] += timedelta(hours=2)
    assert runtime.memories.listing()["memories"] == []
    assert runtime.memory.listing()["expired"][0]["id"] == fact["id"]


def test_old_fact_conversion_is_explicit_restartable_and_preserves_identity(tmp_path):
    store = Store(tmp_path, password="fixture-only")
    memory_id = legacy_table(store)
    with pytest.raises(DomainError, match="PERSONAL_MEMORY_MIGRATION_OPT_IN_REQUIRED"):
        migrate_personal_memories(store)
    with pytest.raises(DomainError, match="PERSONAL_MEMORY_MIGRATION_REQUIRED"):
        Runtime(store)
    assert migrate_personal_memories(store, acknowledged=True)["migrated"] == 1
    assert migrate_personal_memories(store, acknowledged=True)["already_current"]
    runtime = Runtime(Store(tmp_path))
    fact = runtime.memory.listing()["memories"][0]
    assert fact["id"] == memory_id and fact["version"] == 2
    assert fact["body"] == "Original PR5 preference"
    assert fact["source"] == "assistant_confirmed"
    assert "preference" in fact["note"]
    assert runtime.memories.listing()["memories"][0]["id"] == memory_id
    runtime.memories.action(
        memory_id, MemoryAction(action="update", expected_version=2, content="New wording"), "edit"
    )
    assert runtime.memory.listing()["memories"][0]["version"] == 3
    runtime.memory.delete(memory_id, 3, "forget")
    assert Runtime(Store(tmp_path)).memories.listing()["memories"] == []


def test_conversion_conflict_rolls_back_and_preserves_both_originals(tmp_path):
    store = Store(tmp_path, password="fixture-only")
    service = MemoryService(SimpleNamespace(store=store))
    fact = service.create("Current authoritative wording", "current")["memory"]
    legacy_table(store, memory_id=fact["id"], body="Conflicting old wording")
    with pytest.raises(DomainError, match="PERSONAL_MEMORY_MIGRATION_CONFLICT"):
        migrate_personal_memories(store, acknowledged=True)
    with store.connection() as conn:
        assert (
            conn.execute("SELECT content FROM personal_memories").fetchone()[0]
            == "Conflicting old wording"
        )
        assert (
            conn.execute("SELECT body FROM owner_memories").fetchone()[0]
            == "Current authoritative wording"
        )


def test_forgotten_legacy_fact_cannot_become_visible_after_conversion(tmp_path):
    store = Store(tmp_path, password="fixture-only")
    legacy_table(store, body="", forgotten=1)
    migrate_personal_memories(store, acknowledged=True)
    runtime = Runtime(store)
    assert runtime.memory.listing()["memories"] == []
    assert runtime.memories.listing()["memories"] == []


def test_forget_scrubs_body_and_revisions_without_losing_retry_identity(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    first = runtime.memory.create("PR5-private-original-marker", "original")["memory"]
    runtime.memory.replace(first["id"], "PR5-private-corrected-marker", 1, "correction")
    runtime.memory.delete(first["id"], 2, "forget")
    with runtime.store.connection() as conn:
        dump = "\n".join(conn.iterdump())
    assert "PR5-private-original-marker" not in dump
    assert "PR5-private-corrected-marker" not in dump
    runtime.memory.create("PR5-private-original-marker", "original")
    assert runtime.memory.listing()["memories"] == []
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        runtime.memory.create("A different request", "original")
