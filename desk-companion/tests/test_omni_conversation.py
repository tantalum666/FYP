"""Real application services, scripted provider events; no hosted model/real audio."""

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.conversation import Conversations
from desk.store import DomainError
from desk.voice import QwenOmniProtocol
from desk.voice_turns import VoiceTurns
from test_tool_dispatch import FakeSocket
from test_voice_omni import AUDIO, QuietOmni, config


async def until(socket, kind):
    while True:
        value = await asyncio.wait_for(socket.outgoing.get(), 2)
        if value["type"] == kind:
            return value


async def open_chat(runtime, principal, mode="text", conversation_id=None):
    provider, socket = QuietOmni(), FakeSocket()
    voice = runtime.voice
    voice.config = config()
    voice.connector = lambda *a, **k: provider
    voice.active, voice.started = True, time.monotonic()
    task = asyncio.create_task(voice.run(socket, principal, "zh", mode, conversation_id))
    ready = await until(socket, "ready")
    return provider, socket, task, ready["conversation_id"]


async def answer(provider, socket, response_id, text, voice=False):
    await provider.queue.put({"type": "response.created", "response": {"id": response_id}})
    kind = "response.audio_transcript" if voice else "response.text"
    await provider.queue.put({"type": kind + ".delta", "response_id": response_id, "delta": text})
    await provider.queue.put({"type": kind + ".done", "response_id": response_id, "text": text})
    await provider.queue.put({"type": "response.done", "response": {"id": response_id}})
    return await until(socket, "turn_complete")


@pytest.fixture
def owner(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    return runtime, {"kind": "owner", "session": runtime.store.authenticate("owner", "fixture")}


def test_text_voice_text_uses_one_provider_and_reconnect_replays_both(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, cid = await open_chat(runtime, principal)
        setup = provider.sent[0]["session"]
        assert setup["model"] == config().model
        assert setup["modalities"] == ["text"] and setup["turn_detection"] is None
        await socket.incoming.put({"type": "text", "text": "我正在准备项目报告"})
        await until(socket, "transcript")
        completed = await answer(provider, socket, "text-1", "可以先整理测试结果。")
        assert completed["mode"] == "text"
        assert runtime.voice.active
        await socket.incoming.put({"type": "mode", "mode": "voice"})
        assert (await until(socket, "ready"))["conversation_id"] == cid
        await socket.incoming.put({"type": "audio", "audio": AUDIO})
        await provider.queue.put({"type": "input_audio_buffer.speech_stopped"})
        await provider.queue.put(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "刚才说的报告先做哪一部分？",
            }
        )
        await answer(provider, socket, "voice-2", "先整理项目测试结果。", voice=True)
        await socket.incoming.put({"type": "mode", "mode": "text"})
        assert (await until(socket, "ready"))["mode"] == "text"
        assert len([m for m in provider.sent if m.get("session", {}).get("model")]) == 1
        await socket.incoming.put({"type": "stop"})
        await asyncio.wait_for(running, 2)
        second, sock2, run2, resumed_id = await open_chat(runtime, principal, conversation_id=cid)
        assert resumed_id == cid
        replay = [m["item"] for m in second.sent if m["type"] == "conversation.item.create"]
        assert [m["role"] for m in replay] == ["user", "assistant", "user", "assistant"]
        assert "刚才说的报告" in json.dumps(replay, ensure_ascii=False)
        await sock2.incoming.put({"type": "stop"})
        await asyncio.wait_for(run2, 2)
        with runtime.store.connection() as conn:
            records = " ".join(str(tuple(row)) for row in conn.execute("SELECT * FROM records"))
        assert "刚才说的报告" not in records

    asyncio.run(scenario())


def test_text_tool_draft_stays_unwritten_and_survives_mode_switch(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        await socket.incoming.put({"type": "text", "text": "记住我喜欢上午开会"})
        await until(socket, "transcript")
        await provider.queue.put({"type": "response.created", "response": {"id": "draft-r"}})
        await provider.queue.put(
            {
                "type": "response.function_call_arguments.done",
                "response_id": "draft-r",
                "call_id": "draft",
                "name": "memory_save_draft",
                "arguments": json.dumps({"body": "我喜欢上午开会"}),
            }
        )
        await provider.queue.put({"type": "response.done", "response": {"id": "draft-r"}})
        proposal = (await until(socket, "proposal"))["proposal"]
        for _ in range(100):
            if any(m.get("item", {}).get("call_id") == "draft" for m in provider.sent):
                break
            await asyncio.sleep(0.01)
        assert runtime.memory.for_model() == []
        await answer(provider, socket, "answer-r", "请确认这条记忆草稿。")
        await socket.incoming.put({"type": "mode", "mode": "voice"})
        await until(socket, "ready")
        # Switching input devices is not cancellation or permission to save.
        runtime.assistant.decide(proposal["id"], "confirm", "confirm-once")
        assert runtime.memory.for_model()[0]["body"] == "我喜欢上午开会"
        ended = await until(socket, "ended")
        assert ended["reason"] == "memory_changed"
        await asyncio.wait_for(running, 2)

    asyncio.run(scenario())


def test_memory_replacement_and_deletion_invalidate_old_replay(owner):
    runtime, principal = owner
    fact = runtime.memory.create("Old private preference", "create")["memory"]

    async def scenario():
        provider, socket, running, cid = await open_chat(runtime, principal)
        assert "Old private preference" in provider.sent[0]["session"]["instructions"]
        await socket.incoming.put({"type": "text", "text": "What do you remember?"})
        await until(socket, "transcript")
        await answer(provider, socket, "r", "Old private preference")
        runtime.memory.replace(fact["id"], "New preference", fact["version"], "change")
        assert (await until(socket, "ended"))["reason"] == "memory_changed"
        await asyncio.wait_for(running, 2)
        provider2, socket2, running2, _ = await open_chat(runtime, principal, conversation_id=cid)
        assert "New preference" in provider2.sent[0]["session"]["instructions"]
        assert "Old private preference" not in json.dumps(provider2.sent)
        runtime.memory.delete(fact["id"], 2, "forget")
        await until(socket2, "ended")
        await asyncio.wait_for(running2, 2)
        provider3, socket3, running3, _ = await open_chat(runtime, principal, conversation_id=cid)
        assert "New preference" not in json.dumps(provider3.sent)
        await socket3.incoming.put({"type": "stop"})
        await asyncio.wait_for(running3, 2)

    asyncio.run(scenario())


def test_context_is_owner_scoped_bounded_expires_and_new_chat_forgets():
    now = [0.0]
    cache = Conversations(lambda: now[0])
    first = {"kind": "owner", "session": "owner-session-one"}
    other = {"kind": "owner", "session": "owner-session-two"}
    entry = cache.open(first, "rev1")
    for _ in range(50):
        entry.append("user", "x" * 3000)
    assert len(entry.items) <= 40
    assert sum(len(i["text"]) for i in entry.items) <= 32000
    for principal in [other, {"kind": "controller", "id": "screen"}]:
        with pytest.raises(DomainError):
            cache.open(principal, "rev1", entry.id)
        with pytest.raises(DomainError):
            cache.forget(principal, entry.id)
    now[0] = 1801
    with pytest.raises(DomainError):
        cache.open(first, "rev1", entry.id)
    new = cache.open(first, "rev1")
    cache.forget(first, new.id)
    assert new.id not in cache.entries


def test_text_does_not_require_playback_but_filler_does_not_finish_tool_deadline():
    now = [0.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.start()
    turns.transcript("下周有什么会议？")
    turns.end()
    now[0] = 1
    assert not turns.text("让我查一下")["response_started"]
    turn_id = turns.tool("calendar")
    turns.delivered(turn_id, "calendar", {"occurrences": []})
    now[0] = 2
    result = turns.text("下周没有已保存的会议。")
    assert result["response_started"] and result["first_text_ms"] == 1000
    assert result["first_played_ms"] is None


def test_text_mode_refuses_audio_upload_and_does_not_make_it_to_provider(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        await socket.incoming.put({"type": "audio", "audio": AUDIO})
        assert (await until(socket, "error"))["code"] == "MICROPHONE_DISABLED"
        await asyncio.wait_for(running, 2)
        assert not any(m["type"] == "input_audio_buffer.append" for m in provider.sent)

    asyncio.run(scenario())


def test_cancelled_text_does_not_reappear_in_new_turn():
    protocol = QwenOmniProtocol()
    protocol.mode = "text"
    protocol.events({"type": "response.created", "response": {"id": "old"}})
    protocol.cancel()
    assert not protocol.events(
        {"type": "response.text.delta", "response_id": "old", "delta": "stale"}
    )
    ended = protocol.events({"type": "response.done", "response": {"id": "old"}})
    assert not any(e["type"] == "turn_complete" for e in ended)
    protocol.events({"type": "response.created", "response": {"id": "new"}})
    events = protocol.events(
        {"type": "response.text.delta", "response_id": "new", "delta": "current"}
    )
    assert events[0]["text"] == "current"


@pytest.mark.parametrize("status", ["failed", "incomplete"])
def test_failed_provider_response_keeps_usage_without_claiming_completion(status):
    protocol = QwenOmniProtocol()
    protocol.mode = "text"
    protocol.events({"type": "response.created", "response": {"id": "failed"}})
    events = protocol.events(
        {
            "type": "response.done",
            "response": {
                "id": "failed",
                "status": status,
                "usage": {"total_tokens": 12},
            },
        }
    )
    assert not any(e["type"] == "turn_complete" for e in events)
    assert any(e["type"] == "usage" and e["usage"]["total_tokens"] == 12 for e in events)
    assert events[-1]["code"] == "VOICE_PROVIDER_RESPONSE_FAILED"


def test_empty_text_response_is_an_error_not_a_success(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        await socket.incoming.put({"type": "text", "text": "Hello"})
        await until(socket, "transcript")
        await provider.queue.put({"type": "response.created", "response": {"id": "empty"}})
        await provider.queue.put({"type": "response.done", "response": {"id": "empty"}})
        assert (await until(socket, "error"))["code"] == "VOICE_EMPTY_RESPONSE"
        await asyncio.wait_for(running, 2)

    asyncio.run(scenario())


def test_forget_context_route_requires_owner_session(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    client = TestClient(app)
    headers = {"X-Desk-Request": "1"}
    response = client.delete("/api/voice/conversations/unknown", headers=headers)
    assert response.status_code == 401
    client.post("/api/session", json={"username": "owner", "password": "fixture"}, headers=headers)
    principal = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    cid = runtime.voice.conversations.open(principal, "rev").id
    another = TestClient(app)
    another.post("/api/session", json={"username": "owner", "password": "fixture"}, headers=headers)
    assert another.delete(f"/api/voice/conversations/{cid}", headers=headers).status_code == 404
    assert client.delete(f"/api/voice/conversations/{cid}", headers=headers).json() == {
        "cleared": True
    }
    assert cid not in runtime.voice.conversations.entries


def test_immediate_input_after_memory_change_never_uploads_stale_context(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        runtime.memory.create("New confirmed fact", "save")
        await socket.incoming.put({"type": "text", "text": "PRIVATE-NEW-INPUT"})
        assert (await until(socket, "ended"))["reason"] == "memory_changed"
        await asyncio.wait_for(running, 2)
        assert "PRIVATE-NEW-INPUT" not in json.dumps(provider.sent)
        assert not any(m["type"] == "response.create" for m in provider.sent)

    asyncio.run(scenario())


def test_identical_invalid_tool_retry_is_bounded_without_writing(owner):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        await socket.incoming.put({"type": "text", "text": "Create a calendar draft"})
        await until(socket, "transcript")
        for i in range(2):
            rid, cid = f"response-{i}", f"call-{i}"
            await provider.queue.put({"type": "response.created", "response": {"id": rid}})
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": rid,
                    "call_id": cid,
                    "name": "calendar_create_draft",
                    "arguments": "{}",
                }
            )
            await provider.queue.put({"type": "response.done", "response": {"id": rid}})
            if i == 0:
                for _ in range(100):
                    if any(m.get("item", {}).get("call_id") == cid for m in provider.sent):
                        break
                    await asyncio.sleep(0.01)
                else:
                    raise AssertionError("First rejection was not returned")
        assert (await until(socket, "error"))["code"] == "ASSISTANT_TOOL_RETRY_LIMIT"
        await asyncio.wait_for(running, 2)
        assert runtime.assistant.proposals() == []
        assert not runtime.voice.active

    asyncio.run(scenario())


@pytest.mark.parametrize("recover", [True, False])
def test_cached_schedule_answer_is_withheld_and_only_one_grounding_repair_is_allowed(
    owner, recover
):
    runtime, principal = owner

    async def scenario():
        provider, socket, running, _ = await open_chat(runtime, principal)
        await socket.incoming.put({"type": "text", "text": "下周有几场会议？"})
        await until(socket, "transcript")
        await provider.queue.put({"type": "response.created", "response": {"id": "ungrounded"}})
        await provider.queue.put(
            {"type": "response.text.done", "response_id": "ungrounded", "text": "STALE-3"}
        )
        await provider.queue.put({"type": "response.done", "response": {"id": "ungrounded"}})
        for _ in range(100):
            if "Application validation" in json.dumps(provider.sent):
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("No bounded grounding repair")
        assert "STALE-3" not in json.dumps(list(socket.outgoing._queue))
        if recover:
            await provider.queue.put({"type": "response.created", "response": {"id": "read"}})
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": "read",
                    "call_id": "fresh",
                    "name": "calendar_query",
                    "arguments": json.dumps(
                        {"start": "2026-10-26T00:00:00+08:00", "end": "2026-11-02T00:00:00+08:00"}
                    ),
                }
            )
            await provider.queue.put({"type": "response.done", "response": {"id": "read"}})
            for _ in range(100):
                if any(m.get("item", {}).get("call_id") == "fresh" for m in provider.sent):
                    break
                await asyncio.sleep(0.01)
            completed = await answer(provider, socket, "grounded", "0")
            assert completed["mode"] == "text"
            await socket.incoming.put({"type": "stop"})
        else:
            await provider.queue.put({"type": "response.created", "response": {"id": "again"}})
            await provider.queue.put(
                {"type": "response.text.done", "response_id": "again", "text": "STILL-STALE"}
            )
            await provider.queue.put({"type": "response.done", "response": {"id": "again"}})
            assert (await until(socket, "error"))["code"] == "VOICE_UNGROUNDED_RESPONSE"
        await asyncio.wait_for(running, 2)
        repairs = [
            m
            for m in provider.sent
            if m["type"] == "conversation.item.create" and "Application validation" in json.dumps(m)
        ]
        assert len(repairs) == 1
        assert not runtime.voice.active

    asyncio.run(scenario())


@pytest.mark.parametrize("value", [True, -1, 5001, "5000", 4.5])
def test_invalid_audio_prebuffer_does_not_consume_ticket_or_open_provider(tmp_path, value):
    from starlette.websockets import WebSocketDisconnect

    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    runtime.voice.config = config()
    client = TestClient(app)
    client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    )
    ticket = client.post("/api/voice/tickets", json={}, headers={"X-Desk-Request": "1"}).json()[
        "ticket"
    ]
    with client.websocket_connect("/api/voice/ws") as ws:
        ws.send_json({"ticket": ticket, "prebuffer_ms": value})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    assert not runtime.voice.active
    assert runtime.voice.consume(ticket)["kind"] == "owner"
    runtime.voice.active = False
