"""Owner review of memory: one wording, a kept history, expiry, and duplicate retirement."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.runtime import Runtime
from desk.store import DomainError, Store


def _owner(tmp_path, clock=None):
    app = create_app(
        tmp_path, password="fixture-only", scheduler=False, clock=clock
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return app, client


def test_the_same_wording_is_stored_once_and_a_correction_keeps_the_previous_text(tmp_path):
    runtime = _owner(tmp_path)[0].state.runtime
    first = runtime.memory.create("The lamp preset is calm", "first")
    assert first["duplicate"] is False
    again = runtime.memory.create("  the   lamp preset is calm. ", "second")
    assert again["duplicate"] is True
    assert again["memory"]["id"] == first["memory"]["id"]
    assert len(runtime.memory.for_model()) == 1
    replaced = runtime.memory.replace(
        first["memory"]["id"], "The lamp preset is bright", first["memory"]["version"], "edit"
    )
    current = runtime.memory.listing()["memories"][0]
    assert current["body"] == "The lamp preset is bright"
    assert current["previous_body"] == "The lamp preset is calm"
    assert current["source"] == "owner"
    assert [row["body"] for row in runtime.memory.for_model()] == ["The lamp preset is bright"]
    other = runtime.memory.create("Coffee in the morning", "other")["memory"]
    with pytest.raises(DomainError, match="MEMORY_DUPLICATE"):
        runtime.memory.replace(other["id"], "the lamp preset is bright", other["version"], "clash")
    assert replaced["memory"]["version"] == 2


def test_duplicate_review_can_be_cancelled_and_confirmation_retires_the_older_copy(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = _owner(tmp_path, clock=lambda: clock[0])[0].state.runtime
    first = runtime.memory.create("Same fact", "first")["memory"]
    duplicate_id = uuid4().hex
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO owner_memories("
            "id, body, source, state, version, created_at, updated_at, attribution"
            ") VALUES(?,?,?,'active',1,?,?, '')",
            (duplicate_id, "same fact", "owner", "2026-10-02T00:00:00+00:00", "2026-10-02T02:00:00+00:00"),
        )
    suggestion = runtime.memory.listing()["suggestions"][0]
    assert suggestion["keep"]["id"] == duplicate_id
    retire_ids = [row["id"] for row in suggestion["retire"]]
    draft = runtime.memory.prepare_consolidation(suggestion["keep"]["id"], retire_ids, "review")
    runtime.assistant.decide(draft["proposal"]["id"], "cancel", "cancel-review")
    assert {row["id"] for row in runtime.memory.for_model()} == {first["id"], duplicate_id}
    draft = runtime.memory.prepare_consolidation(
        suggestion["keep"]["id"], retire_ids, "review-again"
    )
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE owner_memories SET version=version+1 WHERE id=?", (first["id"],))
    with pytest.raises(DomainError, match="MEMORY_REVIEW_STALE"):
        runtime.assistant.decide(draft["proposal"]["id"], "confirm", "stale-review")
    assert len(runtime.memory.for_model()) == 2
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE owner_memories SET version=1 WHERE id=?", (first["id"],))
    runtime.assistant.decide(draft["proposal"]["id"], "confirm", "confirm-review")
    visible = runtime.memory.for_model()
    assert [row["id"] for row in visible] == [duplicate_id]
    retired = runtime.memory.listing()["retired"]
    assert retired[0]["id"] == first["id"] and retired[0]["state"] == "superseded"
    assert runtime.memory.listing()["suggestions"] == []


def test_expired_facts_leave_the_model_and_can_still_be_forgotten(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = _owner(tmp_path, clock=lambda: clock[0])[0].state.runtime
    fact = runtime.memory.create("Visiting next month", "fact")["memory"]
    with pytest.raises(DomainError, match="INVALID_EXPIRY"):
        runtime.memory.set_expiry(fact["id"], fact["version"], "tomorrow", "bad-expiry")
    future = runtime.memory.set_expiry(
        fact["id"], fact["version"], "2099-01-01T00:00:00+00:00", "future"
    )["memory"]
    assert runtime.memory.for_model()[0]["id"] == fact["id"]
    runtime.memory.set_expiry(fact["id"], future["version"], None, "clear")
    assert runtime.memory.listing()["memories"][0]["expires_at"] is None
    current = runtime.memory.listing()["memories"][0]
    runtime.memory.set_expiry(
        fact["id"], current["version"], "2020-01-01T00:00:00+00:00", "past"
    )
    assert runtime.memory.for_model() == []
    assert runtime.memory.listing()["expired"][0]["body"] == "Visiting next month"
    runtime.memory.expire_due()
    expired = runtime.memory.listing()["expired"][0]
    assert expired["state"] == "expired"
    runtime.memory.delete(expired["id"], expired["version"], "forget")
    assert runtime.memory.listing()["expired"] == []
    assert runtime.memory.listing()["memories"] == []


def test_display_cannot_review_memory_and_an_old_table_still_opens(tmp_path):
    app, owner = _owner(tmp_path)
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-review"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    response = display.post(
        "/api/memory/consolidation",
        json={"keep_id": "a" * 32, "retire_ids": ["b" * 32]},
        headers={"X-Operation-Id": "display-review"},
    )
    assert response.status_code == 403
    store = Store(tmp_path / "legacy", password="fixture-only")
    with store.connection(write=True) as conn:
        conn.execute(
            """CREATE TABLE owner_memories(
                id TEXT PRIMARY KEY, body TEXT NOT NULL, source TEXT NOT NULL,
                state TEXT NOT NULL, version INTEGER NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT)"""
        )
        conn.execute(
            "INSERT INTO owner_memories VALUES(?,?,?,'active',1,?,?,NULL)",
            ("a" * 32, "Tea", "owner", "2026-10-02T00:00:00+00:00", "2026-10-02T00:00:00+00:00"),
        )
    opened = Runtime(store)
    fact = opened.memory.listing()["memories"][0]
    assert fact["body"] == "Tea" and fact["note"] == "" and fact["expires_at"] is None
    clock = opened.store.clock() + timedelta(days=1)
    assert clock > datetime(2026, 1, 1, tzinfo=UTC)
