"""Voice transcript continuity shares the existing owner-scoped RAM buffer."""

import asyncio
import json
from base64 import b64encode
import pytest
from fastapi.testclient import TestClient
from desk.app import create_app
from desk.context import pack_conversation
from desk.conversation import memory_context
from desk.store import DomainError
from desk.voice import VoiceConfig


class _Speak:
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
        elif message.get("type") == "response.create":
            await self.queue.put(
                {"type": "response.audio_transcript.delta", "delta": "Tuesday morning."}
            )
            await self.queue.put(
                {"type": "response.done", "response": {"usage": {"output_tokens": 2}}}
            )


def test_voice_context_is_ram_only_and_bound_to_the_owner_login(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    voice = app.state.runtime.voice
    voice.config = VoiceConfig(
        provider="qwen_audio",
        endpoint="wss://fixture.invalid/realtime",
        model="fixture",
        api_key="fixture-not-a-key",
    )
    voice.connector = lambda *args, **kwargs: _Speak()
    client = TestClient(app)
    headers = {"X-Desk-Request": "1"}
    client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers=headers,
    )
    ticket = client.post("/api/voice/tickets", headers=headers).json()["ticket"]
    audio = b64encode(b"\x00" * 320).decode()
    with client.websocket_connect(
        "/api/voice/ws", headers={"Origin": "http://testserver"}
    ) as socket:
        socket.send_json({"ticket": ticket, "language": "en"})
        ready = socket.receive_json()
        assert ready["type"] == "ready"
        socket.send_json({"type": "text", "text": "What time is it?"})
        seen = []
        for _ in range(6):
            message = socket.receive_json()
            seen.append(message["type"])
            if message["type"] == "turn_complete":
                break
        socket.send_json({"type": "stop"})
    assert "turn_complete" in seen
    runtime = app.state.runtime
    principal = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    conversation = voice.conversations.open(
        principal, memory_context(runtime, True)[0], ready["conversation_id"]
    )
    bodies = [row["body"] for row in pack_conversation(runtime, conversation=conversation)["turns"]]
    assert "What time is it?" in bodies
    assert "Tuesday morning." in bodies
    assert audio not in "".join(bodies)
    with app.state.store.connection() as conn:
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name='assistant_turns'").fetchone()
            is None
        )
    assert pack_conversation(runtime)["turns"] == []
    with pytest.raises(DomainError, match="CONVERSATION_NOT_FOUND"):
        voice.conversations.open(
            {"kind": "owner", "session": "another-login"},
            memory_context(runtime, True)[0],
            ready["conversation_id"],
        )
    fresh = create_app(tmp_path, password="fixture-only", scheduler=False)
    assert fresh.state.runtime.voice.conversations.entries == {}
