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


def test_qwen_and_gemini_adapters_are_selected_by_config(desk):
    seen = []

    def response(request):
        seen.append(request)
        plan = {"message": "Draft only.", "tool": "none", "arguments": {}}
        if request.url.host == "dashscope-intl.aliyuncs.com":
            assert request.headers["authorization"] == "Bearer fixture-key"
            body = json.loads(request.content)
            assert body["model"] == "qwen-test" and body["response_format"]["type"] == "json_object"
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
