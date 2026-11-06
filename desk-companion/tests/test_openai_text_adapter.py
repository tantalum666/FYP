"""Responses wire/config tests; all HTTP is a local MockTransport."""

import json

import httpx
import pytest

from desk.app import create_app
from desk.provider_policy import OPENAI_TEXT_ENDPOINT, valid_provider_endpoint
from desk.store import DomainError
from desk.text_ai import TextConfig, TextPlan
from desk.voice import VoiceConfig


def test_openai_defaults_are_inert_without_a_key_and_none_is_still_explicit(monkeypatch):
    for name in [
        "OPENAI_API_KEY",
        "DESK_OPENAI_CREDENTIAL_FILE",
        "DESK_TEXT_API_KEY",
        "DESK_TEXT_PROVIDER",
        "DESK_VOICE_PROVIDER",
        "DESK_VOICE_API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)
    text, voice = TextConfig.environment(), VoiceConfig.environment()
    assert (text.provider, text.model, text.endpoint) == (
        "openai",
        "gpt-6.1-sol",
        OPENAI_TEXT_ENDPOINT,
    )
    assert (voice.provider, voice.model) == ("openai_realtime", "gpt-realtime-2.1")
    assert not text.valid() and not voice.valid() and not text.background
    monkeypatch.setenv("DESK_TEXT_PROVIDER", "none")
    monkeypatch.setenv("DESK_VOICE_PROVIDER", "none")
    assert TextConfig.environment().provider == VoiceConfig.environment().provider == "none"


def test_confirmed_project_file_wins_over_stale_vendor_keys(tmp_path, monkeypatch):
    path = (tmp_path / "openai.env").resolve()
    path.write_text("OPENAI_API_KEY=sk-fake-project-key-for-offline-test\n")
    path.chmod(0o600)
    monkeypatch.setenv("DESK_OPENAI_CREDENTIAL_FILE", str(path))
    monkeypatch.setenv("DESK_TEXT_PROVIDER", "openai")
    monkeypatch.setenv("DESK_VOICE_PROVIDER", "openai_realtime")
    for name in ["OPENAI_API_KEY", "DESK_TEXT_API_KEY", "DESK_VOICE_API_KEY"]:
        monkeypatch.setenv(name, "stale-vendor-value")
    for config in [TextConfig.environment(), VoiceConfig.environment()]:
        assert config.api_key == "sk-fake-project-key-for-offline-test" and config.valid()
        assert config.api_key not in repr(config)
    path.chmod(0o644)
    assert not TextConfig.environment().valid() and not VoiceConfig.environment().valid()


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com.evil.test/v1/responses",
        "https://api.openai.com:443/v1/responses",
        "https://owner@api.openai.com/v1/responses",
        "https://api.openai.com/v1/responses?x=1",
        "https://api.openai.com/v1/chat/completions",
        "http://api.openai.com/v1/responses",
    ],
)
def test_openai_credential_target_is_exact(url):
    assert not valid_provider_endpoint("openai", url, kind="text")


@pytest.mark.parametrize("status", ["completed", "incomplete"])
def test_work_uses_responses_and_never_accepts_an_incomplete_answer(tmp_path, status):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.text_ai.config = TextConfig("openai", "gpt-6.1-sol", OPENAI_TEXT_ENDPOINT, "fake-only")
    runtime.text_ai.config.proxy_url = "http://127.0.0.1:17891"
    calls, checks = [], []

    def transport(request):
        body = json.loads(request.content)
        calls.append(body)
        assert str(request.url) == OPENAI_TEXT_ENDPOINT
        assert request.headers["authorization"] == "Bearer fake-only"
        assert body["store"] is False and body["reasoning"]["effort"] == "low"
        assert body["max_output_tokens"] == 1600
        return httpx.Response(
            200,
            json={
                "status": status,
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"message":"Observed","tool":"none","arguments":{}}',
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 8},
            },
        )

    runtime.text_ai.transport = httpx.MockTransport(transport)

    def generate():
        return runtime.text_ai.generate_guarded(
            "Return the requested JSON",
            {"fictional": True},
            TextPlan,
            "agent_run_decision",
            checkpoint=lambda: checks.append(True),
        )

    if status == "completed":
        assert generate().message == "Observed"
    else:
        with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
            generate()
    assert len(calls) == 1 and len(checks) >= 2
    with runtime.store.connection() as conn:
        rows = conn.execute("SELECT provider,usage FROM text_ai_usage").fetchall()
        assert len(rows) == 1 and rows[0]["provider"] == "openai"
        if status == "completed":
            assert json.loads(rows[0]["usage"])["input_tokens"] == 10


def test_openai_redirect_cannot_forward_credentials(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.text_ai.config = TextConfig("openai", "gpt-6.1-sol", OPENAI_TEXT_ENDPOINT, "fake-only")
    requests = []

    def transport(request):
        requests.append(str(request.url))
        return httpx.Response(307, headers={"location": "https://other.example/collect"})

    runtime.text_ai.transport = httpx.MockTransport(transport)
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        runtime.text_ai.generate("JSON", {}, TextPlan, "conversation")
    assert requests == [OPENAI_TEXT_ENDPOINT]


def test_known_region_refusal_keeps_openai_selected_but_disables_dispatch(monkeypatch):
    monkeypatch.setenv("DESK_OPENAI_REGION_UNSUPPORTED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-only")
    monkeypatch.delenv("DESK_OPENAI_CREDENTIAL_FILE", raising=False)
    for config in [TextConfig.environment(), VoiceConfig.environment()]:
        assert config.provider.startswith("openai")
        assert config.configuration_error == "OPENAI_REGION_UNSUPPORTED"
        assert not config.valid()


def test_new_defaults_do_not_relabel_legacy_vendor_keys_as_openai(monkeypatch):
    for name in ["DESK_TEXT_PROVIDER", "DESK_VOICE_PROVIDER", "OPENAI_API_KEY", "DESK_OPENAI_CREDENTIAL_FILE", "DESK_OPENAI_REGION_UNSUPPORTED"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DESK_TEXT_API_KEY", "legacy-non-openai-key")
    monkeypatch.setenv("DESK_VOICE_API_KEY", "legacy-non-openai-key")
    for config in [TextConfig.environment(), VoiceConfig.environment()]:
        assert config.provider.startswith("openai")
        assert config.api_key == "" and not config.valid()
