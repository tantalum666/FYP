"""Streaming replies expose tool progress and do not write on their own."""

import json

from fastapi.testclient import TestClient

from desk.agent_loop import AgentLoop
from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.model_provider import ModelStep, ScriptedProvider
from desk.reply_stream import text_chunks
from desk.text_ai import TextAssistant, TextConfig

from test_agent_loop import _runtime


def _configured():
    return TextConfig(
        provider="qwen",
        model="qwen-test",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        api_key="test-key",
    )


def _events(chunks):
    body = "".join(chunks)
    events = []
    for block in body.split("\n\n"):
        data = "".join(
            line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
        )
        if data:
            events.append(json.loads(data))
    return events


def test_chunks_follow_characters_not_bytes():
    text = "确认" * 30
    parts = text_chunks(text)
    assert "".join(parts) == text
    assert len(parts) > 1
    assert all(len(part) <= 24 for part in parts)


def test_loop_reports_tool_progress_without_arguments(tmp_path):
    runtime = _runtime(tmp_path)
    provider = ScriptedProvider(
        [
            ModelStep("Checking the clock.", "owner_clock", {}),
            ModelStep("Tuesday morning is clear. Nothing was saved.", "none", {}),
        ]
    )
    seen = []
    reply = AgentLoop(runtime, provider).run(
        system="persona",
        context={},
        key="stream-clock",
        language="en",
        allow_memory=True,
        on_event=seen.append,
    )
    assert [event["phase"] for event in seen] == ["started", "finished"]
    assert seen[0]["tool"] == "owner_clock" and "arguments" not in seen[0]
    assert seen[1]["saved"] is False and seen[1]["outcome"] == "ok"
    assert reply["kind"] == "reply" and "Tuesday" in reply["message"]


def test_cached_stream_does_not_call_the_provider_again(tmp_path):
    runtime = _runtime(tmp_path)
    service = TextAssistant(runtime, config=_configured())
    calls = []

    def generate(_system, context, schema, _purpose):
        calls.append(context.get("user_message"))
        if "last_tool_result" not in context:
            return schema.model_validate(
                {"message": "Checking the clock.", "tool": "owner_clock", "arguments": {}}
            )
        return schema.model_validate(
            {
                "message": "Tuesday morning is clear. Nothing was saved.",
                "tool": "none",
                "arguments": {},
            }
        )

    service.generate = generate
    payload = AssistantMessage(message="What time is it?", language="en")
    first = _events(service.event_stream(payload, "clock-turn"))
    second = _events(service.event_stream(payload, "clock-turn"))
    assert len(calls) == 2
    tools = [event for event in first if event["type"] == "tool"]
    assert tools[0] == {"type": "tool", "phase": "started", "tool": "owner_clock"}
    assert tools[1]["phase"] == "finished" and tools[1]["saved"] is False
    assert "arguments" not in tools[1]
    deltas = [event["text"] for event in first if event["type"] == "delta"]
    assert first[-1]["type"] == "done"
    assert "".join(deltas) == first[-1]["reply"]["message"]
    assert len(first[-1]["reply"]["message"]) > 24
    assert deltas == text_chunks(first[-1]["reply"]["message"])
    assert [event["type"] for event in second] == ["delta", "delta", "done"]
    assert second[-1]["reply"]["message"] == first[-1]["reply"]["message"]


def test_missing_operation_is_an_event_and_makes_no_provider_call(tmp_path):
    runtime = _runtime(tmp_path)
    runtime = _runtime(tmp_path)
    service = TextAssistant(runtime, config=_configured())
    calls = []

    def generate(*_args):
        calls.append(1)

    service.generate = generate
    events = _events(service.event_stream(AssistantMessage(message="Hello"), ""))
    assert calls == []
    assert events == [{"type": "error", "code": "OPERATION_ID_REQUIRED", "status": 422}]


def test_http_stream_shows_a_local_draft_without_saving(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    client = TestClient(app)
    client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    response = client.post(
        "/api/assistant/messages/stream",
        json={"message": "Remember: the code is lantern", "language": "en"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "stream-remember"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events([response.text])
    tools = [event for event in events if event["type"] == "tool"]
    assert tools[0]["tool"] == "memory_save_draft" and tools[0]["phase"] == "started"
    assert tools[1]["phase"] == "finished" and tools[1]["saved"] is False
    assert all("arguments" not in event for event in tools)
    done = events[-1]
    deltas = [event["text"] for event in events if event["type"] == "delta"]
    assert done["type"] == "done" and done["reply"]["saved"] is False
    assert "".join(deltas) == done["reply"]["message"]
    assert "confirm" in done["reply"]["message"].lower()
    assert app.state.runtime.memory.for_model() == []
    plain = client.post(
        "/api/assistant/messages",
        json={"message": "Remember: another fact", "language": "en"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "json-remember"},
    )
    assert plain.status_code == 200 and plain.headers["content-type"].startswith("application/json")
    assert plain.json()["saved"] is False
