import asyncio
import base64
import json
import pytest
from types import SimpleNamespace

from desk.openai_live import OpenAILiveProtocol, OPENAI_LIVE_ENDPOINT
from desk.persona import voice_instructions
from desk.voice import VoiceConfig
from desk.app import create_app


def config():
    return VoiceConfig("openai_live", OPENAI_LIVE_ENDPOINT, "gpt-live-1", "fictional-key", "marin")


def test_live_setup_separates_speech_and_backend_authority():
    protocol = OpenAILiveProtocol()
    protocol.language, protocol.wake_triggered = "zh", True
    instructions = voice_instructions(
        "Old saved Desk Companion persona.", "zh", "2026-11-07T12:00:00+08:00", "Asia/Hong_Kong"
    )
    session = protocol.setup(config(), instructions)["session"]
    assert (
        "Alice" in session["instructions"]
        and "Alice" in session["delegation"]["responses"]["instructions"]
    )
    assert "我在" in session["input"][-1]["content"][0]["text"]
    assert session["store"] is False and session["audio"]["format"]["rate"] == 24000
    assert session["delegation"]["responses"]["service_tier"] == "default"
    assert all(tool["type"] == "function" for tool in session["delegation"]["responses"]["tools"])
    assert not any(
        "confirm" in tool["name"] for tool in session["delegation"]["responses"]["tools"]
    )
    assert config().valid()


def test_live_backend_completion_never_claims_speech_completion_and_dedupes():
    now = [10.0]
    protocol = OpenAILiveProtocol(clock=lambda: now[0])

    def nested(event):
        return {"type": "response.event", "delegation_id": "one", "event": event}

    protocol.events(nested({"type": "response.created", "response": {"id": "r1"}}))
    call = {
        "type": "response.output_item.done",
        "item": {
            "id": "i1",
            "type": "function_call",
            "call_id": "c1",
            "name": "calendar_query",
            "arguments": "{}",
        },
    }
    first = protocol.events(nested(call))
    assert len(first) == 1 and first[0]["response_id"] == "r1"
    assert protocol.events(nested(call)) == []
    done = nested(
        {
            "type": "response.completed",
            "response": {
                "id": "r1",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 3},
            },
        }
    )
    protocol.last_output, protocol.caption_group_open = 8, True
    result = protocol.events(done)
    assert not any(e["type"] == "turn_complete" for e in result)
    now[0] = 15
    assert protocol.poll() is None  # Earlier acknowledgment is not a delivered answer.
    protocol.events(done)
    assert protocol.usage_snapshot()["backend_input_tokens"] == 10
    protocol.events({"type": "session.output_transcript.delta", "delta": "Two meetings."})
    now[0] = 17
    assert protocol.poll()["boundary"] == "local_caption_group"
    assert protocol.poll() is None
    output = protocol.result(first[0], {"saved": False})
    assert output[0]["type"] == "response.item.create"


def test_live_duration_snapshots_replace_and_finalization_is_explicit():
    protocol = OpenAILiveProtocol()
    for seconds in [12, 15, 12]:
        protocol.events({"type": "session.usage.updated", "usage": {"seconds": seconds}})
    assert protocol.usage_snapshot()["voice_seconds"] == 15
    assert protocol.usage_snapshot()["finalization_confirmed"] == 0
    protocol.events(
        {"type": "session.closed", "usage": {"seconds": 16}, "reason": "close_requested"}
    )
    assert protocol.usage_snapshot()["voice_seconds"] == 16
    assert protocol.usage_snapshot()["finalization_confirmed"] == 1


def test_live_silence_and_fragments_do_not_invent_a_provider_final():
    protocol = OpenAILiveProtocol()
    assert (
        protocol.events(
            {"type": "session.output_audio.delta", "delta": base64.b64encode(bytes(2400)).decode()}
        )
        == []
    )
    event = protocol.events({"type": "session.input_transcript.delta", "delta": "Alice"})[0]
    assert event["final"] is False and event["boundary"] == "unfinalized"
    protocol.closing = True
    assert protocol.events({"type": "session.input_transcript.delta", "delta": "late"}) == []


@pytest.mark.parametrize("finish", ["stop", "idle"])
def test_live_service_drains_final_usage_before_releasing_slot(tmp_path, monkeypatch, finish):
    async def run():
        runtime = create_app(tmp_path, password="fictional", scheduler=False).state.runtime
        service = runtime.voice
        service.config = config()
        client_ready = asyncio.Event()
        clock = [0.0]
        if finish == "idle":
            import desk.voice as voice_module

            monkeypatch.setattr(voice_module, "time", SimpleNamespace(monotonic=lambda: clock[0]))

        class Client:
            sent = []

            async def send_json(self, event):
                self.sent.append(event)
                if event["type"] == "ready":
                    client_ready.set()

            async def iter_text(self):
                await client_ready.wait()
                yield json.dumps({"type": "input_started"})
                if finish == "idle":
                    clock[0] = 31.0
                    await asyncio.Event().wait()
                else:
                    yield json.dumps({"type": "stop"})

            async def close(self):
                pass

        class Provider:
            def __init__(self):
                self.queue, self.sent = asyncio.Queue(), []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                pass

            def __aiter__(self):
                async def receive():
                    while True:
                        event = await self.queue.get()
                        yield json.dumps(event)
                        if event["type"] == "session.closed":
                            return

                return receive()

            async def send(self, body):
                value = json.loads(body)
                self.sent.append(value)
                if value["type"] == "session.start":
                    await self.queue.put({"type": "session.started"})
                    await self.queue.put({"type": "session.usage.updated", "usage": {"seconds": 1}})
                elif value["type"] == "session.close":
                    await self.queue.put({"type": "session.closed", "usage": {"seconds": 2}})

        provider = Provider()
        service.connector = lambda *_args, **_kwargs: provider
        owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
        principal = service.consume(service.ticket(owner)["ticket"])
        await asyncio.wait_for(service.run(Client(), principal, "en"), timeout=5)
        assert not service.active and provider.sent[-1]["type"] == "session.close"
        assert not any(x["type"] == "error" for x in Client.sent)
        if finish == "idle":
            assert any(x.get("reason") == "idle" for x in Client.sent)
        assert not any(x["type"] == "input_started" for x in provider.sent)
        with runtime.store.connection() as db:
            receipt = json.loads(
                db.execute("SELECT details FROM records WHERE action='voice_session'").fetchone()[0]
            )
        assert (
            receipt["usage"]["voice_seconds"] == 2
            and receipt["usage"]["finalization_confirmed"] == 1
        )

    asyncio.run(run())


def test_closed_without_final_duration_or_backend_usage_stays_unreconciled():
    protocol = OpenAILiveProtocol()
    protocol.events({"type": "session.usage.updated", "usage": {"seconds": 12}})
    protocol.events({"type": "session.closed"})
    assert protocol.finalized.is_set()
    assert protocol.usage_snapshot()["voice_seconds"] == 12
    assert protocol.usage_snapshot()["finalization_confirmed"] == 0
    protocol = OpenAILiveProtocol()
    protocol.events(
        {
            "type": "response.event",
            "delegation_id": "d",
            "event": {"type": "response.created", "response": {"id": "r"}},
        }
    )
    protocol.events(
        {
            "type": "response.event",
            "delegation_id": "d",
            "event": {
                "type": "response.completed",
                "response": {"id": "r", "status": "completed", "output": []},
            },
        }
    )
    assert protocol.usage_snapshot()["backend_receipts_complete"] == 0
