"""Provider deltas and the safe fallback. No live network."""

import json

import httpx

from desk.assistant import AssistantMessage
from desk.text_ai import TextAssistant, TextConfig
from desk.text_providers import text_adapter
from desk.token_stream import extract_message

from test_agent_loop import _runtime
from test_reply_stream import _configured, _events


def _sse(lines):
    return httpx.Response(200, content=("".join(lines)).encode())


def test_extract_message_grows_across_partial_json():
    assert extract_message("") == ""
    assert extract_message("{") == ""
    assert extract_message('{"message":') == ""
    assert extract_message('{"message":"Hi') == "Hi"
    assert extract_message('{"message":"Hi\\') == "Hi"
    assert extract_message('{"message":"Hi\\nthere","tool":"none"') == "Hi\nthere"
    assert extract_message("not json") is None


def test_qwen_and_gemini_deltas_skip_thoughts_and_keep_usage(tmp_path):
    plan = '{"message":"Draft only.","tool":"none","arguments":{}}'
    qwen_body = (
        "data: "
        + json.dumps({"choices": [{"delta": {"content": plan[:18]}}]})
        + "\n\n"
        + "data: "
        + json.dumps(
            {
                "choices": [{"delta": {"content": plan[18:]}}],
                "usage": {"prompt_tokens": 4},
            }
        )
        + "\n\ndata: [DONE]\n\n"
    )
    gemini_body = (
        "data: "
        + json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"thought": True, "text": "hidden"}, {"text": plan[:10]}]
                        }
                    }
                ]
            }
        )
        + "\n\ndata: "
        + json.dumps(
            {
                "candidates": [{"content": {"parts": [{"text": plan[10:]}]}}],
                "usageMetadata": {"promptTokenCount": 4},
            }
        )
        + "\n\n"
    )

    def response(request):
        if request.url.host.endswith("aliyuncs.com"):
            assert json.loads(request.content)["stream"] is True
            return _sse([qwen_body])
        assert ":streamGenerateContent" in request.url.path
        return _sse([gemini_body])

    client = httpx.Client(transport=httpx.MockTransport(response))
    qwen = text_adapter("qwen")
    pieces, box = qwen.deltas(
        client,
        TextConfig(
            provider="qwen",
            model="qwen-test",
            endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            api_key="fixture-key",
        ),
        "system",
        "user",
    )
    assert "".join(pieces) == plan and box["prompt_tokens"] == 4
    gemini = text_adapter("gemini")
    pieces, box = gemini.deltas(
        client,
        TextConfig(provider="gemini", model="gemini-test", api_key="fixture-key"),
        "system",
        "user",
    )
    assert "".join(pieces) == plan and "hidden" not in "".join(pieces)
    assert box["promptTokenCount"] == 4
    assert tmp_path is not None


def test_stream_failure_falls_back_to_one_completion(tmp_path):
    runtime = _runtime(tmp_path)
    calls = []
    plan = json.dumps(
        {"message": "Tuesday morning is clear. Nothing was saved.", "tool": "none", "arguments": {}}
    )

    def response(request):
        body = json.loads(request.content)
        calls.append(body.get("stream"))
        if body.get("stream") is True:
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": plan}}], "usage": {"prompt_tokens": 2}}
        )

    service = TextAssistant(runtime, config=_configured(), transport=httpx.MockTransport(response))
    events = _events(service.event_stream(AssistantMessage(message="Hello"), "fallback-turn"))
    assert calls == [True, False]
    deltas = [event["text"] for event in events if event["type"] == "delta"]
    assert "".join(deltas) == events[-1]["reply"]["message"]
    assert events[-1]["reply"].get("saved") is not True
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM text_ai_usage").fetchone()[0] == 2


def test_fake_provider_stream_works_without_network(tmp_path):
    runtime = _runtime(tmp_path)

    def forbidden(request):
        raise AssertionError("Offline provider attempted network")

    service = TextAssistant(
        runtime, config=TextConfig(provider="fake"), transport=httpx.MockTransport(forbidden)
    )
    events = _events(service.event_stream(AssistantMessage(message="Hello"), "offline-stream"))
    assert events[-1]["type"] == "done"
    assert "offline" in events[-1]["reply"]["message"].lower()


def test_stream_fallback_cannot_exceed_daily_attempt_budget(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path)
    monkeypatch.setenv("DESK_TEXT_DAILY_CAP", "1")
    calls = []

    def response(request):
        calls.append(request)
        return httpx.Response(503)

    service = TextAssistant(runtime, config=_configured(), transport=httpx.MockTransport(response))
    events = _events(service.event_stream(AssistantMessage(message="Hello"), "bounded-fallback"))
    assert len(calls) == 1
    assert "daily limit" in events[-1]["reply"]["message"]
