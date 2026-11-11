import asyncio
import base64
import json
import pytest
from types import SimpleNamespace

from desk.openai_live import OpenAILiveProtocol, OPENAI_LIVE_ENDPOINT
from desk.persona import voice_instructions
from desk.voice import VoiceConfig
from desk.app import create_app
from desk.voice_settings import VoiceRegistration, VoiceSelection


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


def test_live_voice_receipt_confirms_custom_voice_and_refuses_silent_substitution():
    custom = config()
    custom.voice = "voice_original"
    protocol = OpenAILiveProtocol()
    protocol.setup(custom, "Fixture")

    def started(voice):
        return {"type": "session.started", "session": {"audio": {"output": {"voice": voice}}}}

    assert protocol.events(started({"id": "voice_original"}))[0]["type"] == "ready"
    assert protocol.voice_confirmed is True
    assert protocol.events(started("marin"))[0]["code"] == "VOICE_SELECTION_MISMATCH"
    assert protocol.voice_confirmed is False
    unconfirmed = OpenAILiveProtocol()
    unconfirmed.setup(custom, "Fixture")
    assert unconfirmed.events({"type": "session.started"})[0]["type"] == "ready"
    assert unconfirmed.voice_confirmed is None


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


def test_client_lost_before_ready_still_finalizes_the_provider(tmp_path):
    async def run():
        from starlette import websockets as starlette_websockets

        runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
        service = runtime.voice
        service.config = config()

        class Client:
            async def send_json(self, _):
                raise getattr(starlette_websockets, "WebSocketDisconnected", RuntimeError)(
                    "client closed"
                )

            async def iter_text(self):
                await asyncio.Event().wait()
                yield ""

            async def close(self):
                pass

        class Provider:
            def __init__(self):
                self.queue = asyncio.Queue()
                self.sent = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                pass

            def __aiter__(self):
                async def receive():
                    while True:
                        value = await self.queue.get()
                        yield json.dumps(value)
                        if value["type"] == "session.closed":
                            return

                return receive()

            async def send(self, raw):
                value = json.loads(raw)
                self.sent.append(value)
                if value["type"] == "session.start":
                    await self.queue.put({"type": "session.started"})
                elif value["type"] == "session.close":
                    await self.queue.put({"type": "session.closed", "usage": {"seconds": 2}})

        provider = Provider()
        service.connector = lambda *a, **k: provider
        owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
        principal = service.consume(service.ticket(owner)["ticket"])
        await asyncio.wait_for(
            service.run(Client(), principal, "en", wake_triggered=True), timeout=4
        )
        assert not service.active
        assert [value["type"] for value in provider.sent] == ["session.start", "session.close"]
        with runtime.store.connection() as db:
            receipt = json.loads(
                db.execute("select details from records where action='voice_session'").fetchone()[0]
            )
        assert receipt["usage"]["finalization_confirmed"] == 1
        assert receipt["failure"] == {"code": "VOICE_CLIENT_DISCONNECTED", "phase": "startup"}

    asyncio.run(run())


def test_live_configuration_error_keeps_only_safe_diagnostic_identifiers():
    protocol = OpenAILiveProtocol()
    events = protocol.events(
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "code": "invalid_function_parameters",
                "param": "session.delegation.responses.tools[2].parameters",
                "message": "PRIVATE_OWNER_INPUT must not be recorded",
            },
        }
    )
    assert events == [{"type": "error", "code": "VOICE_CONFIGURATION_REJECTED"}]
    assert protocol.failure["code"] == "invalid_function_parameters"
    assert "message" not in protocol.failure
    protocol.events({"type": "error", "error": {"param": "private content with spaces"}})
    assert protocol.failure == {}


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


@pytest.mark.parametrize("finish", ["stop", "idle", "ungrounded"])
def test_live_service_drains_final_usage_before_releasing_slot(tmp_path, monkeypatch, finish):
    async def run():
        runtime = create_app(tmp_path, password="fictional", scheduler=False).state.runtime
        service = runtime.voice
        service.config = config()
        if finish == "stop":
            service.settings.register(
                VoiceRegistration(
                    expected_version=1,
                    id="voice_fixture",
                    name="Original Alice",
                    description="A clear original adult voice.",
                ),
                "voice-register",
            )
            service.settings.select(
                VoiceSelection(
                    expected_version=2,
                    voice="voice_fixture",
                    delivery="Natural connected Mandarin and Cantonese.",
                ),
                "voice-select",
            )
        client_ready = asyncio.Event()
        transcript_processed = asyncio.Event()
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
                    if finish == "ungrounded":
                        await transcript_processed.wait()
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
                        if event["type"] == "session.output_transcript.delta":
                            transcript_processed.set()
                        if event["type"] == "session.closed":
                            return

                return receive()

            async def send(self, body):
                value = json.loads(body)
                self.sent.append(value)
                if value["type"] == "session.start":
                    await self.queue.put({"type": "session.started"})
                    await self.queue.put({"type": "session.usage.updated", "usage": {"seconds": 1}})
                    if finish == "ungrounded":
                        await self.queue.put(
                            {
                                "type": "session.input_transcript.delta",
                                "delta": "How many meetings are scheduled tomorrow?",
                                "start_ms": 100,
                                "end_ms": 900,
                            }
                        )
                        await self.queue.put(
                            {
                                "type": "session.output_transcript.delta",
                                "delta": "Your calendar is empty.",
                                "start_ms": 1000,
                                "end_ms": 1500,
                            }
                        )
                elif value["type"] == "session.close":
                    await self.queue.put({"type": "session.closed", "usage": {"seconds": 2}})

        provider = Provider()
        service.connector = lambda *_args, **_kwargs: provider
        owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
        principal = service.consume(service.ticket(owner)["ticket"])
        await asyncio.wait_for(service.run(Client(), principal, "en"), timeout=5)
        assert not service.active and provider.sent[-1]["type"] == "session.close"
        setup = provider.sent[0]["session"]
        assert setup["audio"]["output"]["voice"] == (
            {"id": "voice_fixture"} if finish == "stop" else "marin"
        )
        assert len(setup["delegation"]["responses"]["tools"]) == 30
        if finish == "stop":
            assert "A clear original adult voice." in setup["instructions"]
            assert "Natural connected Mandarin and Cantonese." in setup["instructions"]
        assert service.config.voice == "marin"  # The default provider configuration stays intact.
        if finish == "ungrounded":
            history = next(iter(service.conversations.entries.values())).items
            assert [item["role"] for item in history] == ["user"]
            assert not any(event.get("text") == "Your calendar is empty." for event in Client.sent)
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
