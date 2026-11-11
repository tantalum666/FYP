import asyncio
import json
import threading

import pytest

from desk.app import create_app
from desk.voice_turns import VoiceTurns
from test_voice_omni import QuietOmni, begin


def test_delivered_review_card_waits_for_owner_without_claiming_spoken_success():
    now = [0.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.start()
    turns.end()
    turns.tool("status")
    turns.delivered(1, "status", {"connected": True})
    assert turns.review_waiting(1) is None
    turns.tool("draft")
    now[0] = 7
    turns.delivered(1, "draft", {"proposal": {"id": "actual-pending-draft"}, "sent": False})
    assert turns.review_waiting(1) == {"type": "turn_review", "turn_id": 1}
    now[0] = 12
    assert turns.poll() is None
    assert turns.summary("waiting")["first_played_ms"] is None
    assert not turns.summary("waiting")["response_started"]
    turns.start()
    turns.end()
    now[0] = 23
    assert turns.poll()["code"] == "VOICE_TURN_TIMEOUT"


@pytest.mark.parametrize(
    "has_image,question,requires_tool",
    [
        (True, "图片上的会议是几点？", False),
        (True, "What time is the meeting in this screenshot?", False),
        (False, "图片上的会议是几点？", True),
        (True, "下周有几场会议？", True),
        (False, "下個星期有幾多個會議？", True),
        (False, "Check my appointments next week", True),
        (False, "帮我创建一个会议", False),
        (False, "Create a meeting for me", False),
    ],
)
def test_visual_schedule_answers_do_not_require_unrelated_database_query(
    has_image, question, requires_tool
):
    now = [0.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.start()
    turns.transcript(question, visual_context=has_image)
    turns.end()
    issued = turns.audio()
    now[0] = 2
    result = turns.playback(
        {
            **issued,
            "elapsed_ms": 2000,
            "timing_source": "output_timestamp",
            "endpoint_source": "capture_energy",
        }
    )
    assert result["response_started"] is not requires_tool
    now[0] = 11
    assert (turns.poll() is not None) is requires_tool


def test_first_sound_does_not_satisfy_a_calendar_query_or_extend_deadline():
    now = [100.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.start()
    turns.transcript("下周有什么会议")
    turns.end(2400)
    first = turns.audio()
    now[0] = 102
    result = turns.playback(
        {
            "turn_id": 1,
            "audio_id": first["audio_id"],
            "elapsed_ms": 2000,
            "timing_source": "output_timestamp",
            "endpoint_source": "capture_energy",
        }
    )
    assert not result["response_started"] and not result["semantic_verified"]
    now[0] = 105
    assert turns.poll()["type"] == "turn_slow"
    assert turns.poll() is None
    turns.end(4000)  # repeated VAD / response events cannot extend the deadline
    now[0] = 110
    assert turns.poll()["code"] == "VOICE_TURN_TIMEOUT"


def test_all_tool_calls_must_return_and_audio_must_actually_play():
    now = [1.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.start()
    turns.end()
    turns.tool("a")
    turns.tool("b")
    turns.delivered(1, "a", {"occurrences": []})
    assert not turns.audio()["after_tool"]
    turns.delivered(1, "b", {"occurrences": []})
    audio = turns.audio()
    assert audio["after_tool"]
    now[0] = 6
    assert turns.poll()["type"] == "turn_slow"  # network receipt is not playback
    assert turns.playback({"turn_id": 1, "audio_id": 999, "elapsed_ms": 1}) is None
    result = turns.playback(
        {
            "turn_id": 1,
            "audio_id": audio["audio_id"],
            "elapsed_ms": 4900,
            "timing_source": "output_timestamp",
            "endpoint_source": "capture_energy",
        }
    )
    assert result["response_started"] and result["post_tool_played_ms"] == 4900
    now[0] = 12
    assert turns.poll() is None


def test_late_playback_cannot_clear_timeout_or_a_new_turn():
    now = [1.0]
    turns = VoiceTurns(clock=lambda: now[0])
    turns.end()
    audio = turns.audio()
    message = {
        "turn_id": 1,
        "audio_id": audio["audio_id"],
        "elapsed_ms": 10001,
        "timing_source": "output_timestamp",
        "endpoint_source": "capture_energy",
    }
    assert not turns.playback(message)["response_started"]
    now[0] = 12
    assert turns.poll()["code"] == "VOICE_TURN_TIMEOUT"
    turns.finish("timeout")
    turns.start()
    turns.end()
    assert turns.playback({**message, "elapsed_ms": 2}) is None
    assert turns.current.progress_at is None
    assert turns.history[0]["outcome"] == "timeout"


def test_zero_error_or_untrusted_timing_does_not_mark_success():
    turns = VoiceTurns()
    turns.end()
    turns.tool("x")
    turns.delivered(1, "x", {"error": "FAILED"})
    assert not turns.audio()["after_tool"]
    for value in [float("nan"), -1, True, "3"]:
        assert (
            turns.playback(
                {
                    "turn_id": 1,
                    "audio_id": 1,
                    "elapsed_ms": value,
                    "timing_source": "output_timestamp",
                    "endpoint_source": "capture_energy",
                }
            )
            is None
        )


@pytest.mark.parametrize("boundary", ["provider", "client"])
def test_silent_provider_times_out_without_waiting_for_session_idle(tmp_path, boundary):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.voice.turn_factory = lambda: VoiceTurns(target=0.03, cutoff=0.12)

    async def scenario():
        provider = QuietOmni()
        voice, socket, running = await begin(runtime, provider)
        if boundary == "provider":
            await provider.queue.put(
                {"type": "input_audio_buffer.speech_stopped", "audio_end_ms": 2400}
            )
        else:
            await socket.incoming.put({"type": "input_ended"})
        events = []
        while True:
            event = await asyncio.wait_for(socket.outgoing.get(), 2)
            events.append(event)
            if event["type"] == "error":
                break
        assert events[-1]["code"] == "VOICE_TURN_TIMEOUT"
        assert any(e["type"] == "turn_slow" for e in events)
        await asyncio.wait_for(running, 2)
        assert not voice.active
        with runtime.store.connection() as db:
            recorded = json.loads(
                db.execute(
                    "SELECT details FROM records WHERE action='voice_session' ORDER BY sequence DESC LIMIT 1"
                ).fetchone()[0]
            )
        assert recorded["failure"] == {"code": "VOICE_TURN_TIMEOUT", "phase": "active"}
        await provider.queue.put({"type": "response.audio.delta", "delta": "AAA="})
        assert socket.outgoing.empty()

    asyncio.run(scenario())


def test_timed_out_slow_draft_is_cancelled_after_its_thread_returns(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.voice.turn_factory = lambda: VoiceTurns(target=0.03, cutoff=0.12)
    entered, release = threading.Event(), threading.Event()
    original = runtime.assistant.tool

    def slow(*args, **kwargs):
        entered.set()
        release.wait(3)
        return original(*args, **kwargs)

    runtime.assistant.tool = slow

    async def scenario():
        provider = QuietOmni()
        _, socket, running = await begin(runtime, provider)
        try:
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": "r1",
                    "call_id": "draft",
                    "name": "calendar_create_draft",
                    "arguments": json.dumps(
                        {
                            "event": {
                                "title": "Synthetic late draft",
                                "start_local": "2026-10-24T15:00",
                                "end_local": "2026-10-24T16:00",
                            }
                        }
                    ),
                }
            )
            assert await asyncio.to_thread(entered.wait, 1)
            while (await asyncio.wait_for(socket.outgoing.get(), 2))["type"] != "error":
                pass
            await asyncio.wait_for(running, 2)
        finally:
            release.set()
        for _ in range(100):
            await asyncio.sleep(0.01)
            with runtime.store.connection() as conn:
                rows = conn.execute("SELECT state FROM assistant_proposals").fetchall()
            if rows and all(row["state"] == "cancelled" for row in rows):
                break
        assert rows and all(row["state"] == "cancelled" for row in rows)
        assert not any(m["type"] == "response.create" for m in provider.sent)

    asyncio.run(scenario())
