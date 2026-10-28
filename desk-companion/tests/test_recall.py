"""Cited recall stays local. Forget-that is a draft until the owner confirms."""

from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.conversation import memory_context
from desk.store import DomainError
from desk.text_ai import TextAssistant, TextConfig

ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


def _runtime(tmp_path):
    app = create_app(
        tmp_path,
        password="fixture-only",
        scheduler=False,
        clock=lambda: datetime(2026, 10, 3, 2, tzinfo=UTC),
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


def test_a_recalled_fact_names_the_day_and_forget_that_waits_for_confirm(tmp_path):
    app, _client = _runtime(tmp_path)
    runtime = app.state.runtime
    runtime.memory.create("I prefer tea", "save-tea")
    runtime.memory.create("我更喜欢茶", "save-zh")
    runtime.memory.create("The desk lamp preset is calm", "save-lamp")
    reply = runtime.assistant.local_message(
        AssistantMessage(message="What do you remember about tea?"),
        "ask",
    )
    assert "more than one fact" in reply["message"]
    assert "I prefer tea" in reply["message"] and "我更喜欢茶" in reply["message"]
    zh = runtime.assistant.local_message(
        AssistantMessage(message="你还记得茶吗", language="zh"),
        "ask-zh",
    )
    assert "I prefer tea" in zh["message"] and "我更喜欢茶" in zh["message"]
    conversation = runtime.voice.conversations.open(
        {"kind": "owner", "session": "fixture"}, memory_context(runtime, True)[0]
    )
    lamp = runtime.assistant.local_message(
        AssistantMessage(message="what do you remember about the lamp"),
        "ask-lamp",
        conversation=conversation,
    )
    assert lamp["message"] == "You told me on 3 Oct 2026: The desk lamp preset is calm"
    draft = runtime.assistant.local_message(
        AssistantMessage(message="forget that"), "forget", conversation=conversation
    )
    assert draft["kind"] == "draft" and draft["saved"] is False
    bodies = {row["body"] for row in runtime.memory.for_model()}
    assert "The desk lamp preset is calm" in bodies
    runtime.assistant.decide(draft["proposal"]["id"], "confirm", "confirm-forget")
    assert "The desk lamp preset is calm" not in {row["body"] for row in runtime.memory.for_model()}
    again = runtime.assistant.local_message(
        AssistantMessage(message="忘掉那个", language="zh"), "again", conversation=conversation
    )
    assert again["kind"] == "clarify"


def test_several_matches_do_not_pick_a_fact_to_forget(tmp_path):
    app, _client = _runtime(tmp_path)
    runtime = app.state.runtime
    runtime.memory.create("I prefer tea", "one")
    runtime.memory.create("The tea shop is nearby", "two")
    reply = runtime.assistant.local_message(
        AssistantMessage(message="what do you remember about tea"),
        "both",
    )
    assert "more than one fact" in reply["message"]
    assert "I prefer tea" in reply["message"] and "tea shop" in reply["message"]
    clarify = runtime.assistant.local_message(AssistantMessage(message="forget that"), "which")
    assert clarify["kind"] == "clarify"
    assert len(runtime.memory.for_model()) == 2


def test_a_configured_provider_is_not_called_for_recall_or_forget_that(tmp_path):
    app, _client = _runtime(tmp_path)
    runtime = app.state.runtime
    runtime.memory.create("I prefer tea", "save")
    calls = []

    def response(_request):
        calls.append(1)
        return httpx.Response(500)

    service = TextAssistant(
        runtime,
        TextConfig("qwen", "test-model", ENDPOINT, "fixture-key"),
        httpx.MockTransport(response),
    )
    principal = {"kind": "owner", "session": "fixture"}
    reply = service.message(
        AssistantMessage(message="do you remember tea"), "paid-recall", principal=principal
    )
    assert calls == []
    assert "3 Oct 2026" in reply["message"]
    forgotten = service.message(
        AssistantMessage(message="forget it", conversation_id=reply["conversation_id"]),
        "paid-forget",
        principal=principal,
    )
    assert calls == [] and forgotten["kind"] == "draft"


def test_a_paired_display_cannot_recall_a_fact(tmp_path):
    app, owner = _runtime(tmp_path)
    app.state.runtime.memory.create("I prefer tea", "save")
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    response = display.post(
        "/api/assistant/messages",
        json={"message": "What do you remember about tea?", "language": "en"},
        headers={"X-Operation-Id": "display-recall"},
    )
    assert response.status_code == 403
    assert "I prefer tea" not in response.text
    with pytest.raises(DomainError) as caught:
        app.state.runtime.assistant.local_message(
            AssistantMessage(message="forget that"),
            "display-forget",
            allow_memory=False,
        )
    assert caught.value.code == "OWNER_SIGN_IN_REQUIRED"
