"""Streaming replies expose tool progress and do not write on their own."""

import json

import httpx
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
    tools = [event for event in seen if event["type"] == "tool"]
    assert [event["phase"] for event in tools] == ["started", "finished"]
    assert tools[0]["tool"] == "owner_clock" and "arguments" not in tools[0]
    assert tools[1]["saved"] is False and tools[1]["outcome"] == "ok"
    assert any(event.get("type") == "preview" and event.get("text") == "" for event in seen)
    final = [event for event in seen if event.get("type") == "preview" and event.get("final")]
    assert final[-1]["text"] == reply["message"]
    assert reply["kind"] == "reply" and "Tuesday" in reply["message"]


def test_cached_stream_does_not_call_the_provider_again(tmp_path):
    runtime = _runtime(tmp_path)
    calls = []
    message = "Tuesday morning is clear. Nothing was saved."
    plan = json.dumps({"message": message, "tool": "none", "arguments": {}})
    pieces = [plan[:12], plan[12:28], plan[28:]]

    def response(request):
        calls.append(json.loads(request.content).get("stream"))
        if calls[-1] is True:
            lines = [
                "data: "
                + json.dumps({"choices": [{"delta": {"content": piece}}]})
                + "\n\n"
                for piece in pieces
            ]
            lines.append(
                'data: {"choices":[],"usage":{"prompt_tokens":3}}\n\ndata: [DONE]\n\n'
            )
            return httpx.Response(200, content="".join(lines).encode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": plan}}], "usage": {"prompt_tokens": 3}},
        )

    service = TextAssistant(runtime, config=_configured(), transport=httpx.MockTransport(response))
    payload = AssistantMessage(message="What time is it?", language="en")
    first = _events(service.event_stream(payload, "clock-turn"))
    second = _events(service.event_stream(payload, "clock-turn"))
    assert calls == [True]
    previews = [event["text"] for event in first if event["type"] == "preview"]
    assert previews[-1] == message
    assert not [event for event in first if event["type"] == "delta"]
    assert first[-1]["type"] == "done" and first[-1]["reply"]["message"] == message
    assert [event["type"] for event in second] == ["delta", "delta", "done"]
    assert "".join(event["text"] for event in second if event["type"] == "delta") == message


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
