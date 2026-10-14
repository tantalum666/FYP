"""Owner memory: drafts do not write, deletion leaves the model context, display cannot read."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import TOOLS, AssistantMessage
from desk.context import pack_conversation
from desk.memory import MAX_ACTIVE
from desk.store import DomainError


def _owner(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
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


def test_draft_is_not_memory_until_the_owner_confirms_and_cancel_writes_nothing(tmp_path):
    app, client = _owner(tmp_path)
    runtime = app.state.runtime
    reply = runtime.assistant.local_message(
        AssistantMessage(message="记住：周五的报告还在等组员数据", language="zh"),
        "remember",
    )
    assert reply["saved"] is False
    assert runtime.memory.listing()["memories"] == []
    runtime.assistant.decide(reply["proposal"]["id"], "cancel", "cancel-memory")
    assert runtime.memory.for_model() == []
    saved = runtime.assistant.local_message(
        AssistantMessage(message="Remember: The desk lamp preset is calm", language="en"),
        "remember-en",
    )
    first = runtime.assistant.decide(saved["proposal"]["id"], "confirm", "confirm-memory")
    again = runtime.assistant.decide(saved["proposal"]["id"], "confirm", "confirm-memory-retry")
    assert first == again
    assert runtime.memory.for_model()[0]["body"] == "The desk lamp preset is calm"
    assert all("confirm" not in tool["name"] for tool in TOOLS)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": uuid4().hex}
    assert client.get("/api/memory", headers=headers).status_code == 200


def test_correction_conflict_and_deleted_fact_leave_the_packed_context(tmp_path):
    app, _client = _owner(tmp_path)
    runtime = app.state.runtime
    created = runtime.memory.create("Wait for the figures", "create-fact")
    fact = created["memory"]
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        runtime.memory.replace(fact["id"], "Figures arrived", 99, "bad-version")
    runtime.memory.replace(fact["id"], "Figures arrived", fact["version"], "good-version")
    packed = pack_conversation(runtime)
    assert packed["memory"][0]["body"] == "Figures arrived"
    assert "api_key" not in packed
    runtime.memory.delete(fact["id"], fact["version"] + 1, "delete-fact")
    assert pack_conversation(runtime)["memory"] == []
    with pytest.raises(DomainError, match="MEMORY_NOT_FOUND"):
        runtime.memory.replace(fact["id"], "Still here", fact["version"] + 2, "revive")


def test_display_cannot_read_memory_and_the_active_cap_holds(tmp_path, monkeypatch):
    app, owner = _owner(tmp_path)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": uuid4().hex}
    enrol = owner.post(
        "/api/devices/enrol-display", json={"name": "Test display"}, headers=headers
    )
    assert enrol.status_code == 200
    token = owner.cookies.get("desk_companion_device")
    display = TestClient(app)
    display.headers["Authorization"] = "Bearer " + token
    assert display.get("/api/memory", headers={"X-Desk-Request": "1"}).status_code == 403
    monkeypatch.setattr("desk.memory.MAX_ACTIVE", 1)
    runtime = app.state.runtime
    runtime.memory.create("Only one", "one")
    with pytest.raises(DomainError, match="MEMORY_LIMIT"):
        runtime.memory.create("Second", "two")
    assert MAX_ACTIVE >= 1
