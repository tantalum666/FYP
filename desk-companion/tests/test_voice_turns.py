"""Owner voice transcripts join the text turn budget. Paired sessions do not."""

import asyncio
import json
from base64 import b64encode

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.context import pack_conversation, voice_context_note
from desk.store import encode
from desk.turns import VoiceTranscript, apply_voice_event, remember_exchange, voice_turn_log
from desk.voice import VoiceConfig

from test_agent_loop import _runtime


def test_deltas_and_a_final_user_line_land_in_the_budget(tmp_path):
    runtime = _runtime(tmp_path)
    log = voice_turn_log(runtime, "voice-1", {"kind": "owner"})
    apply_voice_event(
        log, {"type": "transcript", "role": "user", "text": "partial", "final": False}
    )
    apply_voice_event(
        log,
        {"type": "transcript", "role": "user", "text": "What time is it?", "final": True},
    )
    apply_voice_event(
        log, {"type": "transcript", "role": "assistant", "text": "It is ", "final": False}
    )
    apply_voice_event(
        log, {"type": "transcript", "role": "assistant", "text": "Tuesday.", "final": False}
    )
    apply_voice_event(log, {"type": "turn_complete"})
    bodies = [row["body"] for row in pack_conversation(runtime)["turns"]]
    assert bodies[0] == "It is Tuesday."
    assert "What time is it?" in bodies
    assert "partial" not in "".join(bodies)
    note = voice_context_note(runtime)
    assert "User: What time is it?" in note
    assert "Assistant: It is Tuesday." in note
    assert note.index("User:") < note.index("Assistant:")


def test_paired_and_disabled_logs_write_nothing(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.memory.create("Private owner fact", "fact")
    paired = voice_turn_log(runtime, "paired", {"kind": "display"})
    paired.add_typed("the paired phrase")
    apply_voice_event(
        paired, {"type": "transcript", "role": "assistant", "text": "hello", "final": False}
    )
    apply_voice_event(paired, {"type": "turn_complete"})
    assert pack_conversation(runtime)["turns"] == []
    disabled = VoiceTranscript(runtime, "off", enabled=False)
    disabled.add("user", "still hidden", final=True)
    disabled.commit()
    assert pack_conversation(runtime)["turns"] == []
    note = voice_context_note(runtime)
    assert "Private owner fact" in note
    assert "still hidden" not in note
    assert voice_context_note(runtime, allow_memory=False) == ""


def test_local_desk_worker_is_stored_and_a_pending_draft_survives(tmp_path):
    runtime = _runtime(tmp_path)
    draft = runtime.assistant.tool(
        "memory_save_draft", {"body": "Keep this approval"}, "voice-draft"
    )
    log = voice_turn_log(runtime, "desk", {"kind": "agent"})
    for index in range(6):
        log.add_typed(f"turn {index} " + ("noise " * 40))
        log.add("assistant", f"reply {index}", final=True)
        log.commit()
    packed = pack_conversation(runtime, budget=1)
    assert packed["pending_approvals"][0]["id"] == draft["proposal"]["id"]
    assert packed["pending_approvals"][0]["saved"] is False
    note = voice_context_note(runtime)
    assert draft["proposal"]["id"] in note
    assert "saved=false" in note


def _stamp(runtime, memory_id, updated_at):
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE owner_memories SET updated_at=? WHERE id=?",
            (updated_at, memory_id),
        )


def test_owner_voice_prompt_ranks_memory_and_keeps_the_pending_draft(tmp_path):
    runtime = _runtime(tmp_path)
    older = runtime.memory.create("晚上要带红灯笼。", "lantern")["memory"]
    newer = runtime.memory.create("苹果" * 40, "apple")["memory"]
    _stamp(runtime, older["id"], "2026-10-01T00:00:00+00:00")
    _stamp(runtime, newer["id"], "2026-10-20T00:00:00+00:00")
    draft = runtime.assistant.tool(
        "memory_save_draft", {"body": "Keep this approval"}, "voice-memory-draft"
    )
    remember_exchange(runtime, "said-lantern", "灯笼", "好")
    packed = pack_conversation(runtime, user_message="灯笼", budget=100000)
    without_apple = dict(packed)
    without_apple["memory"] = [row for row in packed["memory"] if "苹果" not in row["body"]]
    tight = voice_context_note(runtime, budget=len(encode(without_apple)))
    assert "晚上要带红灯笼。" in tight
    assert newer["body"] not in tight
    assert tight.index("saved=false") < tight.index("晚上要带红灯笼。")
    assert draft["proposal"]["id"] in tight
    runtime.memory.delete(older["id"], older["version"], "delete-lantern")
    assert "红灯笼" not in voice_context_note(runtime, user_message="灯笼")
    assert voice_context_note(runtime, allow_memory=False, user_message="灯笼") == ""


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


def test_live_voice_socket_stores_text_and_not_audio(tmp_path):
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
    with client.websocket_connect("/api/voice/ws", headers={"Origin": "http://testserver"}) as socket:
        socket.send_json({"ticket": ticket, "language": "en"})
        assert socket.receive_json()["type"] == "ready"
        socket.send_json({"type": "text", "text": "What time is it?"})
        seen = []
        for _ in range(6):
            message = socket.receive_json()
            seen.append(message["type"])
            if message["type"] == "turn_complete":
                break
        socket.send_json({"type": "stop"})
    assert "turn_complete" in seen
    bodies = [row["body"] for row in pack_conversation(app.state.runtime)["turns"]]
    assert "What time is it?" in bodies
    assert "Tuesday morning." in bodies
    assert audio not in "".join(bodies)
    with app.state.store.connection() as conn:
        blob = " ".join(row["body"] for row in conn.execute("SELECT body FROM assistant_turns"))
    assert audio not in blob
