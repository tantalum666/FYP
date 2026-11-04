import base64
from array import array
import pytest
from desk.openai_voice import OpenAIRealtimeProtocol, PCM16To24, OPENAI_REALTIME_ENDPOINT
from desk.voice import VoiceConfig
from desk.voice_credentials import openai_key, qwen_key


def config():
    return VoiceConfig(
        "openai_realtime", OPENAI_REALTIME_ENDPOINT, "gpt-realtime-2.1-mini", "fixture-key"
    )


@pytest.mark.parametrize("suffix", ["?model=other", "#x", ":443", "/extra"])
def test_openai_endpoint_scope_is_exact(suffix):
    c = config()
    c.endpoint += suffix
    assert not c.valid()


def test_openai_configuration_and_wire_shapes():
    c = config()
    assert c.valid()
    p = OpenAIRealtimeProtocol()
    p.language = "zh"
    setup = p.setup(c, "fixture instructions")["session"]
    assert setup["type"] == "realtime" and setup["output_modalities"] == ["audio"]
    assert setup["audio"]["input"]["format"]["rate"] == 24000
    assert 1 <= setup["max_output_tokens"] <= 1024
    assert all(
        t["type"] == "function" and "name" in t and "function" not in t for t in setup["tools"]
    )
    assert p.mode_update("text")["session"]["audio"]["input"]["turn_detection"] is None
    assert p.instructions_update("new")["session"]["type"] == "realtime"
    assert p.image("AA==")["item"]["content"][0]["image_url"] == "data:image/jpeg;base64,AA=="


def test_resampling_is_continuous_independent_of_chunk_boundaries():
    samples = array("h", [((n * 123) % 60000) - 30000 for n in range(16000)])
    expected = PCM16To24().convert(samples.tobytes())
    bridge = PCM16To24()
    actual = b"".join(bridge.convert(samples[n : n + 640].tobytes()) for n in range(0, 16000, 640))
    assert actual == expected and len(actual) == 47998
    p = OpenAIRealtimeProtocol()
    data = p.audio(base64.b64encode(samples[:640].tobytes()).decode())
    assert (
        data["type"] == "input_audio_buffer.append" and len(base64.b64decode(data["audio"])) == 1918
    )


def test_openai_event_aliases_keep_cancel_and_usage_deduplication():
    p = OpenAIRealtimeProtocol()
    assert p.events(
        {
            "type": "session.updated",
            "session": {"audio": {"output": {"format": {"type": "audio/pcm", "rate": 24000}}}},
        }
    ) == [{"type": "ready"}]
    p.events({"type": "response.created", "response": {"id": "r"}})
    p.events(
        {"type": "response.output_audio_transcript.delta", "response_id": "r", "delta": "hello"}
    )
    assert p.cancel() == {"type": "response.cancel"}
    assert (
        p.events(
            {"type": "response.output_audio_transcript.delta", "response_id": "r", "delta": "late"}
        )
        == []
    )
    done = {
        "type": "response.done",
        "response": {
            "id": "r",
            "status": "cancelled",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "input_token_details": {"audio_tokens": 4, "text_tokens": 6},
                "output_token_details": {"audio_tokens": 2},
            },
        },
    }
    events = p.events(done)
    assert events[0]["type"] == "usage" and events[0]["usage"]["input_audio_tokens"] == 4
    assert p.events(done) == []


def test_project_env_file_permissions_do_not_relax_qwen_private_directory(tmp_path):
    directory = tmp_path / "project"
    directory.mkdir()
    directory.chmod(0o755)
    path = directory / ".env.local"
    path.write_text("OPENAI_API_KEY=fixture_key_for_tests_only\n")
    path.chmod(0o600)
    assert openai_key(str(path)) == "fixture_key_for_tests_only"
    with pytest.raises(ValueError):
        qwen_key(str(path))
    path.chmod(0o644)
    with pytest.raises(ValueError):
        openai_key(str(path))


def test_openai_barge_in_uses_one_application_owned_cancel():
    p = OpenAIRealtimeProtocol()
    assert (
        p.setup(config(), "fixture")["session"]["audio"]["input"]["turn_detection"][
            "interrupt_response"
        ]
        is False
    )
    p.events({"type": "response.created", "response": {"id": "old"}})
    assert p.events({"type": "input_audio_buffer.speech_started"})[0]["type"] == "interrupted"
    assert p.cancel() == {"type": "response.cancel"}
    assert p.cancel() is None
    p.events({"type": "response.done", "response": {"id": "old", "status": "cancelled"}})
    p.events({"type": "response.created", "response": {"id": "new"}})
    assert not p.cancel_requested


def test_explicit_project_credential_file_wins_over_generic_environment(tmp_path, monkeypatch):
    path = tmp_path / ".env.local"
    path.write_text("OPENAI_API_KEY=project_fixture_key_123456789\n")
    path.chmod(0o600)
    monkeypatch.setenv("DESK_VOICE_PROVIDER", "openai_realtime")
    monkeypatch.setenv("DESK_OPENAI_CREDENTIAL_FILE", str(path))
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated_fixture_key_123456789")
    monkeypatch.delenv("DESK_VOICE_API_KEY", raising=False)
    assert VoiceConfig.environment().api_key == "project_fixture_key_123456789"
    path.chmod(0o644)
    assert not VoiceConfig.environment().valid()


def test_openai_quiet_session_closes_without_another_paid_response(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from desk.app import create_app
    from desk import voice as voice_module
    from test_voice_google import FakeProvider
    from test_tool_dispatch import FakeSocket

    clock = [100.0]
    monkeypatch.setattr(voice_module, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    runtime = create_app(tmp_path, scheduler=False).state.runtime
    service = runtime.voice
    service.config = config()
    owner = {"kind": "owner", "session": runtime.store.create_owner_session()}

    async def scenario():
        provider = FakeProvider()
        socket = FakeSocket()
        service.connector = lambda *a, **k: provider
        principal = service.consume(service.ticket(owner)["ticket"])
        task = asyncio.create_task(service.run(socket, principal, "en"))
        event = await asyncio.wait_for(socket.outgoing.get(), 1)
        assert event["type"] == "ready"
        clock[0] += 31
        await asyncio.wait_for(task, 2)
        events = []
        while not socket.outgoing.empty():
            events.append(socket.outgoing.get_nowait())
        assert any(e.get("type") == "ended" and e.get("reason") == "idle" for e in events)
        assert not service.active
        assert not any(e.get("type") == "response.create" for e in provider.sent)

    asyncio.run(scenario())
