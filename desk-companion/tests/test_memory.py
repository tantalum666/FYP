"""Owner memory: drafts do not write, deletion leaves the model context, display cannot read."""

from uuid import uuid4
import asyncio

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
    enrol = owner.post("/api/devices/enrol-display", json={"name": "Test display"}, headers=headers)
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


def test_paired_display_cannot_bypass_memory_owner_check_through_assistant(tmp_path):
    app, owner = _owner(tmp_path)
    runtime = app.state.runtime
    draft = runtime.assistant.tool("memory_save_draft", {"body": "Owner-only fact"}, "owner-draft")
    proposal_id = draft["proposal"]["id"]
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-memory"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/assistant/proposals").json()["proposals"] == []
    response = display.post(
        f"/api/assistant/proposals/{proposal_id}/decisions",
        json={"action": "confirm"},
        headers={"X-Operation-Id": "display-confirm"},
    )
    assert response.status_code == 403
    assert runtime.memory.for_model() == []
    response = display.post(
        "/api/assistant/messages",
        json={"message": "Remember: display supplied fact", "language": "en"},
        headers={"X-Operation-Id": "display-remember"},
    )
    assert response.status_code == 403
    assert runtime.memory.for_model() == []


def test_paired_text_context_and_cached_replies_cannot_reveal_owner_memory(tmp_path, monkeypatch):
    from desk.text_ai import TextPlan

    runtime = _owner(tmp_path)[0].state.runtime
    runtime.memory.create("Private owner fact", "private-fact")
    captured = []

    def generate(system, context, schema, purpose):
        captured.append(context)
        return TextPlan(message="Public reply", tool="none")

    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)
    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    payload = AssistantMessage(message="Hello")
    runtime.text_ai.message(payload, "owner-reply")
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        runtime.text_ai.message(payload, "owner-reply", allow_memory=False)
    runtime.text_ai.message(payload, "display-reply", allow_memory=False)
    assert captured[0]["memory"][0]["body"] == "Private owner fact"
    assert captured[1]["memory"] == []
    assert not any(t["name"].startswith("memory_") for t in captured[1]["tools"])
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        runtime.assistant.tool("memory_query", {}, "forced-tool", allow_memory=False)


def test_paired_voice_hides_memory_tools_and_rejects_unsolicited_calls(tmp_path):
    from desk.tool_dispatch import ToolDispatcher
    from desk.voice import GeminiProtocol, QwenAudioProtocol, VoiceConfig

    runtime = _owner(tmp_path)[0].state.runtime
    runtime.memory.create("Private voice fact", "voice-fact")
    qwen = QwenAudioProtocol().setup(VoiceConfig(), "Test", allow_memory=False)
    gemini = GeminiProtocol().setup(VoiceConfig(), "Test", allow_memory=False)
    assert not any(t["function"]["name"].startswith("memory_") for t in qwen["session"]["tools"])
    assert not any(
        t["name"].startswith("memory_") for t in gemini["setup"]["tools"][0]["functionDeclarations"]
    )

    async def run():
        dispatcher = ToolDispatcher(runtime, "paired-voice", allow_memory=False)
        dispatcher.submit({"id": "memory-read", "name": "memory_query", "arguments": {}})
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=2)
        assert result == {"error": "OWNER_SIGN_IN_REQUIRED", "saved": False}
        await dispatcher.close()

    asyncio.run(run())
