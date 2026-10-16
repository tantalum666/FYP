import asyncio
import base64
import json
import time
from pathlib import Path

import pytest

from desk.app import create_app
from desk.store import DomainError
from desk.voice import QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, QwenOmniProtocol, VoiceConfig
from desk.voice_credentials import qwen_key
from desk.voice_media import jpeg_image
from test_tool_dispatch import FakeSocket
from test_voice_google import FakeProvider

JPEG = (Path(__file__).parent / "fixtures" / "qwen-vision.jpg").read_bytes()
IMAGE = base64.b64encode(JPEG).decode()
AUDIO = base64.b64encode(b"\x00" * 1280).decode()


def config():
    return VoiceConfig("qwen_omni", QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, "fixture_" * 4)


def test_explicit_private_key_loading_ignores_untrusted_endpoint_metadata(tmp_path, monkeypatch):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    path = directory / "qwen.env"
    key = "fixture_" * 4
    path.write_text(f"DASHSCOPE_API_KEY={key}\nFYP_QWEN_REALTIME_URL=wss://evil.invalid/realtime\n")
    path.chmod(0o600)
    for name in ("DESK_VOICE_MODEL", "DESK_VOICE_ENDPOINT", "DESK_VOICE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DESK_QWEN_CREDENTIAL_FILE", str(path))
    monkeypatch.setenv("DESK_VOICE_PROVIDER", "none")
    assert VoiceConfig.environment().api_key == ""
    monkeypatch.setenv("DESK_VOICE_PROVIDER", "qwen_omni")
    chosen = VoiceConfig.environment()
    assert chosen.valid() and chosen.endpoint == QWEN_OMNI_ENDPOINT
    assert chosen.api_key == key and key not in repr(chosen)
    path.chmod(0o644)
    assert not VoiceConfig.environment().valid()
    assert VoiceConfig.environment().configuration_error == "VOICE_CREDENTIALS_INVALID"


def test_key_loader_refuses_ancestor_links(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (private / "qwen.env").write_text("DASHSCOPE_API_KEY=" + "fixture_" * 4)
    (private / "qwen.env").chmod(0o600)
    (tmp_path / "alias").symlink_to(private, target_is_directory=True)
    with pytest.raises(OSError):
        qwen_key(str(tmp_path / "alias" / "qwen.env"))


@pytest.mark.parametrize(
    "endpoint",
    [
        "wss://evil.invalid/api-ws/v1/realtime",
        "wss://maas.qianwenaiapi.com:443/api-ws/v1/realtime",
        QWEN_OMNI_ENDPOINT + "?model=other",
        QWEN_OMNI_ENDPOINT + "#fragment",
        "wss://user@maas.qianwenaiapi.com/api-ws/v1/realtime",
        "https://maas.qianwenaiapi.com/compatible-mode/v1",
    ],
)
def test_omni_cannot_send_credentials_to_an_unapproved_endpoint(endpoint):
    chosen = config()
    chosen.endpoint = endpoint
    assert not chosen.valid()


def test_omni_setup_preserves_business_approval_and_uses_its_own_audio_contract():
    setup = QwenOmniProtocol().setup(config(), "Fixture instructions", allow_memory=False)[
        "session"
    ]
    assert setup["audio"]["input"]["format"]["sample_rate"] == 16000
    assert setup["audio"]["output"]["format"] == {"type": "pcm", "sample_rate": 24000}
    assert setup["audio"]["output"]["voice"] == "Tina"
    assert setup["turn_detection"]["type"] == "semantic_vad"
    assert not setup["enable_search"]
    assert "max_history_turns" not in setup and "input_audio_format" not in setup
    names = [x["function"]["name"] for x in setup["tools"]]
    assert "calendar_query" in names
    assert not any(name.startswith("memory_") or "confirm" in name for name in names)


def test_function_metadata_is_correlated_when_argument_event_omits_name_or_call_id():
    protocol = QwenOmniProtocol()
    item = {
        "id": "item-1",
        "type": "function_call",
        "call_id": "call-1",
        "name": "calendar_query",
        "arguments": "",
    }
    assert (
        protocol.events({"type": "response.output_item.added", "response_id": "r1", "item": item})
        == []
    )
    events = protocol.events(
        {
            "type": "response.function_call_arguments.done",
            "response_id": "r1",
            "item_id": "item-1",
            "arguments": "{}",
        }
    )
    assert events == [
        {
            "type": "tool",
            "id": "call-1",
            "name": "calendar_query",
            "arguments": "{}",
            "response_id": "r1",
        }
    ]
    assert (
        protocol.events(
            {
                "type": "response.output_item.done",
                "response_id": "r1",
                "item": {**item, "arguments": "{}"},
            }
        )
        == []
    )
    assert not any(
        e["type"] == "tool"
        for e in protocol.events(
            {
                "type": "response.done",
                "response": {"id": "r1", "output": [{**item, "arguments": "{}"}]},
            }
        )
    )


def test_completed_response_is_a_fallback_for_complete_function_calls():
    protocol = QwenOmniProtocol()
    item = {
        "id": "item-2",
        "type": "function_call",
        "call_id": "call-2",
        "name": "calendar_query",
        "arguments": "{}",
    }
    events = protocol.events(
        {
            "type": "response.done",
            "response": {"id": "r2", "output": [item]},
            "usage": {"input_tokens": 3},
        }
    )
    assert events[0]["id"] == "call-2" and protocol.response_idle.is_set()
    assert events[-1] == {"type": "usage", "usage": {"input_tokens": 3}}


def test_incomplete_function_metadata_cannot_grow_without_a_session_bound():
    protocol = QwenOmniProtocol()
    for number in range(129):
        events = protocol.events(
            {
                "type": "response.output_item.added",
                "response_id": "r1",
                "item": {"type": "function_call", "id": str(number)},
            }
        )
    assert events == [{"type": "error", "code": "VOICE_SESSION_ENDED"}]


def test_cancelled_response_cannot_inject_late_output_into_a_new_turn():
    protocol = QwenOmniProtocol()
    protocol.events({"type": "response.created", "response": {"id": "old"}})
    protocol.cancel()
    protocol.events({"type": "response.created", "response": {"id": "new"}})
    assert (
        protocol.events({"type": "response.audio.delta", "response_id": "old", "delta": AUDIO})
        == []
    )
    assert (
        protocol.events(
            {
                "type": "response.function_call_arguments.done",
                "response_id": "old",
                "call_id": "late",
                "name": "calendar_query",
                "arguments": "{}",
            }
        )
        == []
    )
    protocol.events({"type": "response.done", "response": {"id": "old"}})
    assert not protocol.response_idle.is_set()
    assert protocol.active_response == "new"


def test_cancel_before_response_created_also_discards_its_late_audio():
    protocol = QwenOmniProtocol()
    protocol.sent({"type": "response.create"})
    protocol.cancel()
    assert protocol.events({"type": "response.created", "response": {"id": "late-created"}}) == [
        {"type": "cancel_response"}
    ]
    assert (
        protocol.events(
            {"type": "response.audio.delta", "response_id": "late-created", "delta": AUDIO}
        )
        == []
    )


def test_pending_cancel_that_finishes_without_created_does_not_cancel_the_next_turn():
    protocol = QwenOmniProtocol()
    protocol.sent({"type": "response.create"})
    assert protocol.cancel() is None
    protocol.events({"type": "response.done", "response": {"id": "cancelled-before-created"}})
    events = protocol.events({"type": "response.created", "response": {"id": "next"}})
    assert events == [{"type": "state", "state": "thinking"}]


def test_omni_interrupt_drops_late_audio_and_tool_calls_and_usage_is_deduplicated():
    protocol = QwenOmniProtocol()
    assert protocol.cancel() is None
    protocol.events({"type": "response.created", "response": {"id": "r1"}})
    assert protocol.cancel() == {"type": "response.cancel"}
    assert protocol.cancel() is None
    assert protocol.events({"type": "response.audio.delta", "delta": AUDIO}) == []
    assert (
        protocol.events({"type": "response.function_call_arguments.done", "call_id": "late"}) == []
    )
    done = {
        "type": "response.done",
        "response": {
            "id": "r1",
            "status": "cancelled",
            "usage": {
                "input_tokens": 9,
                "input_tokens_details": {"audio_tokens": 4, "evil": "not-stored"},
            },
        },
    }
    usage = [e for e in protocol.events(done) if e["type"] == "usage"][0]["usage"]
    assert usage == {"input_tokens": 9, "input_audio_tokens": 4}
    assert not any(e["type"] == "usage" for e in protocol.events(done))
    assert protocol.response_idle.is_set()


def test_omni_text_and_audio_transcripts_do_not_duplicate_and_bad_audio_format_fails():
    protocol = QwenOmniProtocol()
    assert protocol.events({"type": "response.text.delta", "delta": "hello"}) == []
    assert (
        protocol.events({"type": "response.audio_transcript.delta", "delta": "hello"})[0]["text"]
        == "hello"
    )
    assert protocol.events({"type": "response.text.done", "text": "hello"}) == []
    assert protocol.events({"type": "response.audio_transcript.done", "transcript": "hello"})[0][
        "final"
    ]
    assert (
        protocol.events({"type": "session.updated", "session": {"output_audio_format": "wav"}})[0][
            "code"
        ]
        == "VOICE_AUDIO_FORMAT_UNSUPPORTED"
    )


@pytest.mark.parametrize(
    "value",
    [
        "not base64",
        "A" * (256 * 1024 + 1),
        base64.b64encode(b"PNG").decode(),
        base64.b64encode(JPEG[:-2]).decode(),
    ],
)
def test_image_boundary_rejects_invalid_or_unbounded_inputs(value):
    with pytest.raises(DomainError, match="INVALID_VOICE_IMAGE"):
        jpeg_image(value)


class QuietOmni(FakeProvider):
    async def send(self, raw):
        message = json.loads(raw)
        self.sent.append(message)
        if message["type"] == "session.update":
            await self.queue.put({"type": "session.updated"})


async def begin(runtime, provider, principal=None):
    voice = runtime.voice
    voice.config = config()
    voice.connector = lambda *args, **kwargs: provider
    voice.active, voice.started = True, time.monotonic()
    principal = principal or {
        "kind": "owner",
        "session": runtime.store.authenticate("owner", "fixture"),
    }
    socket = FakeSocket()
    task = asyncio.create_task(voice.run(socket, principal, "en"))
    assert (await asyncio.wait_for(socket.outgoing.get(), 2))["type"] == "ready"
    return voice, socket, task


def test_images_require_explicit_owner_consent_and_stop_blocks_later_frames(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime

    async def scenario():
        provider = QuietOmni()
        voice, socket, task = await begin(runtime, provider)
        try:
            await socket.incoming.put({"type": "audio", "audio": AUDIO})
            await socket.incoming.put({"type": "vision_start"})
            assert (await asyncio.wait_for(socket.outgoing.get(), 2))["active"]
            await socket.incoming.put({"type": "image", "image": IMAGE})
            assert (await asyncio.wait_for(socket.outgoing.get(), 2))["count"] == 1
            await socket.incoming.put({"type": "vision_stop"})
            assert not (await asyncio.wait_for(socket.outgoing.get(), 2))["active"]
            await socket.incoming.put({"type": "image", "image": IMAGE})
            assert (await asyncio.wait_for(socket.outgoing.get(), 2))[
                "code"
            ] == "VOICE_VISION_NOT_READY"
            await asyncio.wait_for(task, 2)
            assert len([m for m in provider.sent if m["type"] == "input_image_buffer.append"]) == 1
            assert not voice.active
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())
    assert jpeg_image(IMAGE) == JPEG


@pytest.mark.parametrize("initial", ["image", "vision_start"])
def test_unconsented_images_and_paired_screen_observation_are_rejected(tmp_path, initial):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime

    async def scenario():
        provider = QuietOmni()
        principal = {"kind": "controller", "id": "fixture"} if initial == "vision_start" else None
        _, socket, task = await begin(runtime, provider, principal)
        await socket.incoming.put({"type": initial, "image": IMAGE})
        event = await asyncio.wait_for(socket.outgoing.get(), 2)
        assert event["code"] in {"VOICE_VISION_NOT_ALLOWED", "VOICE_VISION_NOT_READY"}
        await asyncio.wait_for(task, 2)
        assert not any(m["type"] == "input_image_buffer.append" for m in provider.sent)

    asyncio.run(scenario())


def test_function_results_wait_for_response_end_and_resume_once_for_two_calls(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime

    async def scenario():
        provider = QuietOmni()
        _, socket, task = await begin(runtime, provider)
        try:
            await provider.queue.put({"type": "response.created", "response": {"id": "r-tools"}})
            for name in ("one", "two"):
                await provider.queue.put(
                    {
                        "type": "response.function_call_arguments.done",
                        "response_id": "r-tools",
                        "call_id": name,
                        "name": "calendar_query",
                        "arguments": json.dumps(
                            {
                                "start": "2026-10-19T00:00:00+08:00",
                                "end": "2026-10-26T00:00:00+08:00",
                            }
                        ),
                    }
                )
            await asyncio.sleep(0.1)
            assert not any(m["type"] == "conversation.item.create" for m in provider.sent)
            await provider.queue.put(
                {
                    "type": "response.done",
                    "response": {"id": "r-tools", "usage": {"input_tokens": 10}},
                }
            )
            for _ in range(100):
                if any(m["type"] == "response.create" for m in provider.sent):
                    break
                await asyncio.sleep(0.01)
            outputs = [m for m in provider.sent if m["type"] == "conversation.item.create"]
            assert len(outputs) == 2
            assert all("occurrences" in json.loads(m["item"]["output"]) for m in outputs)
            assert len([m for m in provider.sent if m["type"] == "response.create"]) == 1
            await socket.incoming.put({"type": "stop"})
            await asyncio.wait_for(task, 2)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())


def test_interrupt_drops_unsent_function_output_and_the_next_turn_can_resume(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime

    async def scenario():
        provider = QuietOmni()
        _, socket, task = await begin(runtime, provider)
        queried = asyncio.Event()
        loop = asyncio.get_running_loop()
        original = runtime.assistant.tool

        def read(*args, **kwargs):
            result = original(*args, **kwargs)
            loop.call_soon_threadsafe(queried.set)
            return result

        runtime.assistant.tool = read
        arguments = json.dumps(
            {"start": "2026-10-19T00:00:00+08:00", "end": "2026-10-26T00:00:00+08:00"}
        )

        async def call(response_id, call_id):
            await provider.queue.put({"type": "response.created", "response": {"id": response_id}})
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": response_id,
                    "call_id": call_id,
                    "name": "calendar_query",
                    "arguments": arguments,
                }
            )

        try:
            await call("old", "cancelled-call")
            await asyncio.wait_for(queried.wait(), 2)
            await socket.incoming.put({"type": "interrupt"})
            for _ in range(200):
                if any(m["type"] == "response.cancel" for m in provider.sent):
                    break
                await asyncio.sleep(0.01)
            assert any(m["type"] == "response.cancel" for m in provider.sent)
            await provider.queue.put({"type": "response.done", "response": {"id": "old"}})
            queried.clear()
            await call("next", "valid-call")
            await asyncio.wait_for(queried.wait(), 2)
            await provider.queue.put({"type": "response.done", "response": {"id": "next"}})
            for _ in range(200):
                if any(m["type"] == "response.create" for m in provider.sent):
                    break
                await asyncio.sleep(0.01)
            outputs = [m for m in provider.sent if m["type"] == "conversation.item.create"]
            assert [m["item"]["call_id"] for m in outputs] == ["valid-call"]
            assert len([m for m in provider.sent if m["type"] == "response.create"]) == 1
            await socket.incoming.put({"type": "stop"})
            await asyncio.wait_for(task, 2)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())
