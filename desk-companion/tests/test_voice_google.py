import asyncio
import base64
import json
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.exchange import ImportApply, ShareInput
from desk.google_calendar import GoogleCalendar, SCOPE
from desk.store import DomainError
from desk.voice import GeminiProtocol, QwenAudioProtocol, VoiceConfig, pcm_chunk


class FakeProvider:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.sent = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        return json.dumps(await self.queue.get())

    async def send(self, raw):
        message = json.loads(raw)
        self.sent.append(message)
        if message.get("type") == "session.update":
            await self.queue.put({"type": "session.updated"})
        elif message.get("type") == "input_audio_buffer.append":
            await self.queue.put({"type": "input_audio_buffer.speech_started"})
            await self.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "call_id": "call-fixture",
                    "name": "calendar_create_draft",
                    "arguments": json.dumps(
                        {
                            "event": {
                                "title": "Voice fixture",
                                "start_local": "2026-10-03T15:00",
                                "end_local": "2026-10-03T16:00",
                            }
                        }
                    ),
                }
            )
        elif message.get("type") == "response.create":
            await self.queue.put(
                {"type": "response.done", "response": {"usage": {"input_tokens": 12}}}
            )


def test_realtime_transport_creates_only_a_draft_and_interrupt_cancels_it(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    voice = app.state.runtime.voice
    voice.config = VoiceConfig(
        provider="qwen_audio",
        endpoint="wss://fixture.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime",
        model="fixture",
        api_key="fixture-not-a-key",
    )
    fake = FakeProvider()
    voice.connector = lambda *args, **kwargs: fake
    client = TestClient(app)
    headers = {"X-Desk-Request": "1"}
    client.post(
        "/api/session", json={"username": "owner", "password": "fixture-only"}, headers=headers
    )
    ticket = client.post("/api/voice/tickets", headers=headers).json()["ticket"]
    with client.websocket_connect(
        "/api/voice/ws", headers={"Origin": "http://testserver"}
    ) as socket:
        socket.send_json({"ticket": ticket, "language": "en"})
        assert socket.receive_json()["type"] == "ready"
        socket.send_json({"type": "audio", "audio": base64.b64encode(b"\x00" * 1280).decode()})
        for _ in range(10):
            message = socket.receive_json()
            if message["type"] == "proposal":
                break
        assert message["type"] == "proposal"
        with app.state.store.connection() as conn:
            assert not app.state.store.data(conn)[0]
        socket.send_json({"type": "interrupt"})
        for _ in range(8):
            message = socket.receive_json()
            if message["type"] == "interrupted":
                break
        assert not app.state.runtime.assistant.proposals()
        socket.send_json({"type": "stop"})
    assert not voice.active
    with pytest.raises(DomainError):
        voice.consume(ticket)


def test_gemini_all_parts_and_function_cancellation_are_preserved():
    protocol = GeminiProtocol()
    events = protocol.events(
        {
            "serverContent": {
                "modelTurn": {
                    "parts": [
                        {"inlineData": {"mimeType": "audio/pcm;rate=24000", "data": "AAA="}},
                        {"inlineData": {"mimeType": "audio/pcm;rate=24000", "data": "AAA="}},
                    ]
                },
                "inputTranscription": {"text": "test"},
                "turnComplete": True,
            },
            "toolCall": {"functionCalls": [{"id": "one", "name": "posture_status", "args": {}}]},
            "toolCallCancellation": {"ids": ["one"]},
        }
    )
    assert len([e for e in events if e["type"] == "audio"]) == 2
    assert any(e["type"] == "cancel_tools" for e in events)
    setup = protocol.setup(VoiceConfig(model="fixture"), "Instructions")
    assert all(
        "confirm" not in tool["name"] for tool in setup["setup"]["tools"][0]["functionDeclarations"]
    )
    assert QwenAudioProtocol().audio("AAA=")["type"] == "input_audio_buffer.append"
    with pytest.raises(DomainError):
        pcm_chunk("bad base64")
    with pytest.raises(DomainError):
        pcm_chunk(base64.b64encode(b"x").decode())


def test_google_oauth_is_bound_single_use_encrypted_and_read_only(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    runtime = app.state.runtime
    store = app.state.store
    token = store.authenticate("owner", "fixture-only")
    calls = []

    def mock(request):
        calls.append(request)
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "fixture-access",
                    "refresh_token": "fixture-refresh",
                    "expires_in": 3600,
                    "scope": SCOPE,
                },
            )
        if request.url.path == "/revoke":
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "event-1",
                        "summary": "Remote fixture",
                        "start": {"dateTime": "2026-10-03T15:00:00+08:00"},
                        "end": {"dateTime": "2026-10-03T16:00:00+08:00"},
                    }
                ]
            },
        )

    google = GoogleCalendar(
        runtime,
        transport=httpx.MockTransport(mock),
        config={
            "client_id": "fixture",
            "client_secret": "fixture-secret",
            "redirect_uri": "http://localhost:8832/api/google/callback",
        },
    )
    issued = google.begin(token)
    query = parse_qs(urlsplit(issued["url"]).query)
    assert query["scope"] == [SCOPE] and query["code_challenge_method"] == ["S256"]
    with pytest.raises(DomainError):
        google.callback("wrong-state", "code")
    google.callback(query["state"][0], "fixture-code")
    with pytest.raises(DomainError):
        google.callback(query["state"][0], "fixture-code")
    with store.connection() as conn:
        assert (
            "fixture-refresh"
            not in conn.execute("SELECT encrypted_tokens FROM google_connection").fetchone()[0]
        )
    preview = google.preview(
        ShareInput(start=date(2026, 10, 1), end=date(2026, 10, 15)), uuid4().hex
    )
    assert preview["rows"][0]["event"]["start_local"] == "2026-10-03T07:00:00"
    assert runtime.exchange.apply(preview["preview_id"], ImportApply(), "import")["created"] == 1
    assert all(r.method == "GET" for r in calls if "/calendar/v3/" in r.url.path)
    assert google.disconnect()["provider_revocation_confirmed"]
    assert not google.snapshot()["connected"]


def test_google_callback_fails_after_owner_signout(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    google = GoogleCalendar(
        app.state.runtime,
        config={
            "client_id": "fixture",
            "client_secret": "fixture",
            "redirect_uri": "http://localhost:8832/api/google/callback",
        },
    )
    token = app.state.store.authenticate("owner", "fixture-only")
    issued = google.begin(token)
    app.state.store.logout(token)
    with pytest.raises(DomainError, match="OAUTH_EXPIRED"):
        google.callback(parse_qs(urlsplit(issued["url"]).query)["state"][0], "code")


def test_announcement_claim_has_one_destination_and_obeys_quiet_hours(tmp_path):
    clock = [datetime(2026, 10, 2, 0, 0, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture-only", scheduler=False, clock=lambda: clock[0])
    data = app.state.runtime.data
    from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

    data.update(
        PreferencesUpdate(
            expected_version=1, preferences=WorkspacePreferences(daily_brief_enabled=True)
        ),
        "enable",
    )
    assert data.claim_announcement("display-one")["announcement"]["kind"] == "brief"
    assert data.claim_announcement("display-two")["announcement"] is None
    clock[0] += timedelta(hours=15)
    assert data.claim_announcement("display-one")["quiet"]
