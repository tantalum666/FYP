import json
from datetime import UTC, datetime

import httpx
import pytest

from desk.assistant import AssistantMessage
from desk.runtime import Runtime
from desk.store import DomainError, Store
from desk.text_ai import TextAssistant, TextConfig
from desk.text_providers import text_adapter


@pytest.fixture
def desk(tmp_path):
    clock = [datetime(2026, 10, 14, 2, tzinfo=UTC)]
    return Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))


def test_unknown_provider_is_rejected_before_a_request():
    with pytest.raises(DomainError, match="TEXT_AI_NOT_CONFIGURED"):
        text_adapter("none")


def _offline():
    return httpx.MockTransport(lambda request: (_ for _ in ()).throw(AssertionError("network")))


def test_fake_provider_is_valid_without_a_key_and_does_not_call_http(desk):
    assert TextConfig(provider="fake").valid() is True
    assert TextConfig().valid() is False
    assistant = TextAssistant(desk, TextConfig(provider="fake"), _offline())
    reply = assistant.message(AssistantMessage(message="What can this demo do?"), "fake-default")
    assert reply["mode"] == "ai" and reply["kind"] == "reply"
    assert "offline" in reply["message"]
    assert assistant.snapshot()["configured"] is True
    assert assistant.snapshot()["provider"] == "fake"


def test_fake_provider_prepares_a_memory_correction_without_saving_it(desk):
    desk.memory.create("The owner studies at CUHK.", "demo-memory")
    assistant = TextAssistant(desk, TextConfig(provider="fake"), _offline())
    reply = assistant.message(
        AssistantMessage(message="Please correct my memory: I study at CityU, not CUHK."),
        "fake-memory",
    )
    assert reply["kind"] == "draft"
    assert reply["proposal"]["kind"] == "memory_replace"
    assert reply["proposal"]["data"]["body"] == "The owner studies at CityU."
    assert reply["proposal"]["data"]["previous"] == "The owner studies at CUHK."
    assert desk.memory.listing()["memories"][0]["body"] == "The owner studies at CUHK."


def test_fake_provider_prepares_a_note_and_answers_quiet_hours(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    clock = [datetime(2026, 10, 14, 2, tzinfo=UTC)]
    desk = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    assistant = TextAssistant(desk, TextConfig(provider="fake"), _offline())
    job = assistant.message(AssistantMessage(message="Please save a demo note."), "fake-note")
    assert job["kind"] == "job" and job["job"]["state"] == "review"
    assert desk.jobs.detail(job["job"]["id"], review=True)["request"]["title"] == "FYP demo note"
    quiet = assistant.message(AssistantMessage(message="What do quiet hours do?"), "fake-quiet")
    assert quiet["kind"] == "reply" and "Quiet hours" in quiet["message"]
    assert desk.jobs.listing()[0]["state"] == "review"


def test_qwen_and_gemini_adapters_are_selected_by_config(desk):
    seen = []

    def response(request):
        seen.append(request)
        plan = {"message": "Draft only.", "tool": "none", "arguments": {}}
        if request.url.host == "dashscope-intl.aliyuncs.com":
            assert request.headers["authorization"] == "Bearer fixture-key"
            body = json.loads(request.content)
            assert body["model"] == "qwen-test" and body["response_format"]["type"] == "json_object"
            assert body["max_tokens"] == 1600
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": json.dumps(plan)}}],
                    "usage": {"prompt_tokens": 4},
                },
            )
        assert request.url.path.endswith("/models/gemini-test:generateContent")
        assert request.headers["x-goog-api-key"] == "fixture-key"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thought": True, "text": "hidden"},
                                {"text": json.dumps(plan)},
                            ]
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 4},
            },
        )

    transport = httpx.MockTransport(response)
    qwen = TextAssistant(
        desk,
        TextConfig(
            provider="qwen",
            model="qwen-test",
            endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            api_key="fixture-key",
        ),
        transport,
    )
    gemini = TextAssistant(
        desk,
        TextConfig(provider="gemini", model="gemini-test", api_key="fixture-key"),
        transport,
    )
    first = qwen.message(AssistantMessage(message="Track the report"), "qwen-one")
    second = gemini.message(AssistantMessage(message="Track the report"), "gemini-one")
    assert first["mode"] == "ai" and second["mode"] == "ai"
    assert first["message"] == "Draft only." and second["message"] == "Draft only."
    assert [item.url.host for item in seen] == [
        "dashscope-intl.aliyuncs.com",
        "generativelanguage.googleapis.com",
    ]
    assert not desk.tasks.listing()["tasks"]
