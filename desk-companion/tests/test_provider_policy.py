"""Synthetic policy regressions; no real provider, credential or network calls."""

import asyncio
import json
import time

import httpx
import pytest
from websockets.datastructures import Headers
from websockets.exceptions import InvalidStatus
from websockets.http11 import Response

from desk.app import create_app
from desk.provider_policy import (
    GEMINI_TEXT_ENDPOINT,
    GEMINI_VOICE_ENDPOINT,
    ProviderWebSocketConnect,
    valid_provider_endpoint,
)
from desk.store import DomainError
from desk.text_ai import FollowUpAdvice, TextAssistant, TextConfig
from desk.voice import VoiceConfig

QT = "https://fixture.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
QV = "wss://fixture.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime"


@pytest.mark.parametrize(
    "kind,endpoint",
    [("text", ""), ("voice", ""), ("text", GEMINI_TEXT_ENDPOINT), ("voice", GEMINI_VOICE_ENDPOINT)],
)
def test_pinned_gemini_destinations(kind, endpoint):
    assert valid_provider_endpoint("gemini", endpoint, kind=kind)


@pytest.mark.parametrize(
    "region",
    ["cn-beijing", "ap-southeast-1", "ap-northeast-1", "eu-central-1", "us-east-1", "cn-hongkong"],
)
def test_published_qwen_text_workspace_regions(region):
    assert TextConfig("qwen", "fixture", QT.replace("cn-beijing", region), "synthetic-key").valid()


@pytest.mark.parametrize(
    "host",
    [
        "fixture.cn-beijing.maas.aliyuncs.com",
        "fixture.ap-southeast-1.maas.aliyuncs.com",
        "dashscope.aliyuncs.com",
        "dashscope-intl.aliyuncs.com",
    ],
)
def test_published_qwen_voice_hosts(host):
    assert VoiceConfig(
        "qwen_audio", f"wss://{host}/api-ws/v1/realtime", "fixture", "synthetic-key"
    ).valid()


@pytest.mark.parametrize(
    "host", ["dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com"]
)
def test_existing_qwen_shared_text_hosts(host):
    assert TextConfig(
        "qwen", "fixture", f"https://{host}/compatible-mode/v1/chat/completions", "synthetic-key"
    ).valid()


@pytest.mark.parametrize(
    "endpoint",
    [
        "wss://unapproved.example.invalid/api-ws/v1/realtime",
        "wss://127.0.0.1/api-ws/v1/realtime",
        "wss://[::1]/api-ws/v1/realtime",
        "wss://[broken",
        QV.replace("wss://", "ws://"),
        QV.replace("wss://", "https://"),
        QV.replace("wss://", "wss://name:secret@"),
        QV.replace("wss://", "wss://@"),
        QV.replace(".com/", ".com:invalid/"),
        QV.replace(".com/", ".com:443/"),
        QV.replace(".com/", ".com:/"),
        QV.replace(".com/", ".com:65536/"),
        QV.replace(".com/", ".com.evil.invalid/"),
        QV.replace(".com/", ".com./"),
        QV.replace("fixture.", "nested.fixture."),
        QV.replace("fixture.", "-fixture."),
        QV.replace("fixture.", "%66ixture."),
        QV.replace("cn-beijing", "invented-region"),
        QV.replace("/api-ws", "/prefix/api-ws"),
        QV.replace("/api-ws", "/../api-ws"),
        QV + "/",
        QV + "?model=unreviewed",
        QV + "?",
        QV + "#fragment",
        QV + "#",
        " " + QV,
        QV + "\n",
        QV.replace("fixture", "fixt\ture"),
        QV.replace("fixture", "fíxture"),
        QV.replace("fixture", "fixture\\"),
        None,
        42,
        "",
    ],
)
def test_unreviewed_or_ambiguous_voice_targets_fail_closed(endpoint):
    assert not VoiceConfig("qwen_audio", endpoint, "fixture", "synthetic-key").valid()


@pytest.mark.parametrize(
    "endpoint",
    [
        QT.replace(".com/", ".com:invalid/"),
        QT.replace(".com/", ".com:443/"),
        QT.replace(".com/", ".com.evil.invalid/"),
        QT.replace("/compatible-mode", "/other/compatible-mode"),
        QT + "?",
        QT + "#",
        QT.replace("https://", "https://owner@"),
        "https://[broken",
        None,
    ],
)
def test_malformed_text_config_returns_false_not_exception(endpoint):
    assert not TextConfig("qwen", "fixture", endpoint, "synthetic-key").valid()


@pytest.mark.parametrize("kind", ["text", "voice"])
def test_provider_and_channel_binding(kind):
    qwen, gemini = (QT, GEMINI_TEXT_ENDPOINT) if kind == "text" else (QV, GEMINI_VOICE_ENDPOINT)
    assert not valid_provider_endpoint("gemini", qwen, kind=kind)
    assert not valid_provider_endpoint(
        "qwen" if kind == "text" else "qwen_audio", gemini, kind=kind
    )
    assert not valid_provider_endpoint("unsupported", gemini, kind=kind)
    assert not valid_provider_endpoint("unsupported", "", kind=kind)


@pytest.mark.parametrize("value", ["", "fixture\n", "fixture/../../", " ", None, True])
def test_invalid_models(value):
    assert not TextConfig("qwen", value, QT, "synthetic-key").valid()
    assert not VoiceConfig("qwen_audio", QV, value, "synthetic-key").valid()


@pytest.mark.parametrize("key", ["", " key", "key\r\nX-Other: value", "key\x00", None, True])
def test_invalid_header_values(key):
    assert not TextConfig("qwen", "fixture", QT, key).valid()
    assert not VoiceConfig("qwen_audio", QV, "fixture", key).valid()


def test_optional_gemini_model_resource_prefix():
    assert VoiceConfig("gemini", "", "models/fixture", "synthetic-key").valid()
    assert not VoiceConfig("gemini", "", "models/models/fixture", "synthetic-key").valid()


def test_rejected_text_destination_makes_no_request(tmp_path):
    runtime = create_app(tmp_path, password="fixture-only", scheduler=False).state.runtime
    called = []
    service = TextAssistant(
        runtime,
        TextConfig("qwen", "fixture", "https://unapproved.example.invalid", "synthetic-key"),
        httpx.MockTransport(lambda request: called.append(request)),
    )
    with pytest.raises(DomainError, match="TEXT_AI_NOT_CONFIGURED"):
        service.generate("Fixture", {}, FollowUpAdvice, "fixture")
    assert not called


def test_text_redirect_and_environment_proxy_are_disabled(tmp_path, monkeypatch):
    import desk.text_ai as module

    runtime = create_app(tmp_path, password="fixture-only", scheduler=False).state.runtime
    called, options = [], []
    original = httpx.Client

    def client(**kwargs):
        options.append(kwargs)
        return original(**kwargs)

    def response(request):
        called.append(request)
        return httpx.Response(302, headers={"Location": "https://unapproved.example.invalid"})

    monkeypatch.setattr(module.httpx, "Client", client)
    service = TextAssistant(
        runtime, TextConfig("qwen", "fixture", QT, "synthetic-key"), httpx.MockTransport(response)
    )
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        service.generate("Fixture", {}, FollowUpAdvice, "fixture")
    assert len(called) == 1 and str(called[0].url) == QT
    assert options[0]["trust_env"] is False and options[0]["follow_redirects"] is False


def test_websocket_redirect_never_reuses_headers():
    async def check():
        connector = ProviderWebSocketConnect(GEMINI_VOICE_ENDPOINT, proxy=None)
        for location in [GEMINI_VOICE_ENDPOINT, "wss://unapproved.example.invalid"]:
            error = InvalidStatus(Response(302, "Found", Headers({"Location": location})))
            assert connector.process_redirect(error) is error

    asyncio.run(check())


def test_voice_rechecks_config_after_ticket(tmp_path):
    runtime = create_app(tmp_path, password="fixture-only", scheduler=False).state.runtime
    voice = runtime.voice
    voice.config = VoiceConfig("qwen_audio", QV, "fixture", "synthetic-key")
    session = runtime.store.authenticate("owner", "fixture-only")
    ticket = voice.ticket({"kind": "owner", "id": "owner", "session": session})
    principal = voice.consume(ticket["ticket"])
    voice.config.endpoint = "wss://unapproved.example.invalid"
    called, messages = [], []

    def connector(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("Rejected destination reached transport")

    class Socket:
        async def send_json(self, value):
            messages.append(value)

        async def close(self):
            pass

    voice.connector = connector
    asyncio.run(voice.run(Socket(), principal, "en"))
    assert not called and not voice.active
    assert messages == [{"type": "error", "code": "VOICE_NOT_CONFIGURED"}]


def test_voice_explicitly_disables_ambient_proxy(tmp_path):
    runtime = create_app(tmp_path, password="fixture-only", scheduler=False).state.runtime
    voice = runtime.voice
    voice.config = VoiceConfig("qwen_audio", QV, "fixture", "synthetic-key")
    voice.started, voice.active = time.monotonic(), True
    options = []

    def connector(*args, **kwargs):
        options.append(kwargs)
        raise OSError("Synthetic connection failure")

    class Socket:
        async def send_json(self, value):
            assert "synthetic-key" not in json.dumps(value)

        async def close(self):
            pass

    voice.connector = connector
    asyncio.run(voice.run(Socket(), {"kind": "owner", "id": "owner"}, "en"))
    assert options[0]["proxy"] is None and not voice.active
