"""Conversation facts stay drafts until the owner confirms them."""

import json
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.store import DomainError
from desk.text_ai import TextAssistant, TextConfig

ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


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
    return app


def _say(runtime, message, key="turn", language="en"):
    return runtime.assistant.local_message(
        AssistantMessage(message=message, language=language), key
    )


def test_local_rules_draft_stable_statements_and_ignore_appointments(tmp_path):
    runtime = _owner(tmp_path).state.runtime
    preference = _say(runtime, "I prefer short answers")
    assert preference["proposal"]["kind"] == "memory_save"
    assert preference["proposal"]["data"]["note"] == "preference"
    runtime.assistant.decide(preference["proposal"]["id"], "cancel", "cancel-prefer")
    assert runtime.memory.for_model() == []
    name = _say(runtime, "My name is Yuan", "name")
    saved = runtime.assistant.decide(name["proposal"]["id"], "confirm", "confirm-name")
    fact = saved["result"]["memory"]
    assert fact["body"] == "My name is Yuan"
    assert fact["source"] == "conversation"
    assert fact["note"] == "identity"
    chinese = _say(runtime, "我更喜欢简短回答", "zh-prefer", "zh")
    assert chinese["proposal"]["data"]["body"] == "我更喜欢简短回答"
    for message in (
        "I prefer to meet tomorrow at 15:00",
        "I prefer tea?",
        "I want to finish the report",
    ):
        reply = _say(runtime, message, message)
        assert reply.get("proposal", {}).get("kind") != "memory_save"
    assert [row["body"] for row in runtime.memory.for_model()] == ["My name is Yuan"]
    remembered = _say(runtime, "Remember: tea without sugar", "remember")
    assert remembered["proposal"]["data"]["body"] == "tea without sugar"
    assert remembered["proposal"]["data"]["note"] == "explicit"


def test_display_cannot_extract_a_preference(tmp_path):
    runtime = _owner(tmp_path).state.runtime
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        runtime.assistant.local_message(
            AssistantMessage(message="I prefer tea"), "display", allow_memory=False
        )
    assert runtime.memory.for_model() == []


def _configured(runtime, response, cap):
    return TextAssistant(
        runtime,
        TextConfig(
            "qwen",
            "test-model",
            ENDPOINT,
            "fixture-key",
            extract_cap=cap,
        ),
        httpx.MockTransport(response),
    )


def _plan(content):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 3},
        },
    )


def test_hosted_extraction_is_off_without_a_cap_and_only_keeps_quoted_wording(tmp_path):
    runtime = _owner(tmp_path).state.runtime
    calls = []

    def response(request):
        prompt = json.loads(request.content)["messages"][0]["content"]
        kind = "extract" if "stable personal fact" in prompt else "chat"
        calls.append(kind)
        if kind == "extract":
            body = "tea without sugar" if calls.count("extract") == 1 else "lives in Paris"
            return _plan(json.dumps({"fact": {"body": body, "reason": "stated in the message"}}))
        return _plan(json.dumps({"message": "Noted.", "tool": "none", "arguments": {}}))

    quiet = _configured(runtime, response, 0)
    quiet.message(AssistantMessage(message="I drink tea without sugar"), "no-cap")
    assert calls == ["chat"]
    calls.clear()
    capped = _configured(runtime, response, 1)
    draft = capped.message(AssistantMessage(message="I drink tea without sugar"), "extract-one")
    assert calls == ["extract"]
    assert draft["proposal"]["kind"] == "memory_save"
    assert draft["proposal"]["data"]["body"] == "tea without sugar"
    runtime.assistant.decide(draft["proposal"]["id"], "cancel", "cancel-extract")
    assert runtime.memory.for_model() == []
    calls.clear()
    reply = capped.message(AssistantMessage(message="I drink tea without sugar daily"), "over-cap")
    assert calls == ["chat"]
    assert reply["kind"] == "reply"
    calls.clear()
    fresh = _configured(runtime, response, 1)
    # The previous successful extract already used today's only slot.
    missed = fresh.message(AssistantMessage(message="I drink tea without sugar"), "still-capped")
    assert calls == ["chat"] and missed["kind"] == "reply"


def test_a_model_fact_that_was_not_said_is_dropped_and_the_call_still_counts(tmp_path):
    clock = [datetime(2026, 10, 3, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture-only", scheduler=False, clock=lambda: clock[0])
    runtime = app.state.runtime
    calls = []

    def response(request):
        prompt = json.loads(request.content)["messages"][0]["content"]
        kind = "extract" if "stable personal fact" in prompt else "chat"
        calls.append(kind)
        if kind == "extract":
            return _plan(json.dumps({"fact": {"body": "lives in Paris", "reason": "guess"}}))
        return _plan(json.dumps({"message": "Noted.", "tool": "none", "arguments": {}}))

    service = _configured(runtime, response, 1)
    reply = service.message(AssistantMessage(message="I drink tea without sugar"), "reject")
    assert calls == ["extract", "chat"]
    assert reply["kind"] == "reply"
    assert runtime.memory.for_model() == []
    calls.clear()
    service.message(AssistantMessage(message="I drink tea without sugar still"), "second")
    assert calls == ["chat"]


def test_explicit_remember_does_not_call_the_hosted_model(tmp_path):
    runtime = _owner(tmp_path).state.runtime
    calls = []

    def response(request):
        calls.append(request)
        return _plan(json.dumps({"message": "Noted.", "tool": "none", "arguments": {}}))

    service = _configured(runtime, response, 5)
    draft = service.message(AssistantMessage(message="Remember: the desk faces the window"), "remember")
    assert calls == []
    assert draft["proposal"]["data"]["body"] == "the desk faces the window"
    assert draft["mode"] == "local_rules"
