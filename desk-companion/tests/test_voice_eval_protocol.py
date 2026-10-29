import asyncio
import json

from scripts.voice_eval.fixtures import Fixture
from scripts.voice_eval.session import Session, session_config


def test_only_registered_fixture_tools_can_execute_and_drafts_do_not_save(tmp_path):
    fixture = Fixture(tmp_path, "memory-en")
    raw = json.dumps({"body": "Fictional evaluation preference"})
    first = fixture.call("one", "memory_save_draft", raw)
    assert first["saved"] is False and first["proposal"]["id"]
    assert fixture.call("one", "memory_save_draft", raw) == first
    assert fixture.call("one", "memory_save_draft", "{}")["error"] == "TOOL_CALL_CONFLICT"
    assert fixture.call("two", "shell_exec", "{}")["error"] == "TOOL_NOT_ALLOWED"
    assert fixture.runtime.memory.for_model() == []
    assert len(fixture.runtime.assistant.proposals()) == 1


def test_live_calls_use_created_response_id_not_empty_completed_output(tmp_path):
    async def run():
        fixture = Fixture(tmp_path, "calendar-en")
        session = Session("gpt-live-1", fixture, bytes(2400))

        def nested(event):
            return {"type": "response.event", "delegation_id": "delegation-one", "event": event}

        done = nested(
            {
                "type": "response.completed",
                "response": {
                    "id": "response-one",
                    "output": [],
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                },
            }
        )
        events = [
            nested({"type": "response.created", "response": {"id": "response-one"}}),
            nested(
                {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "name": "calendar_query",
                        "call_id": "call-one",
                        "arguments": json.dumps(
                            {
                                "start": "2026-10-30T00:00:00+08:00",
                                "end": "2026-10-31T00:00:00+08:00",
                            }
                        ),
                    },
                }
            ),
            done,
            done,
            {"type": "session.usage.updated", "usage": {"seconds": 12}},
            {"type": "session.usage.updated", "usage": {"seconds": 15}},
            {"type": "session.closed", "usage": {"seconds": 16}, "reason": "close_requested"},
        ]

        class Socket:
            sent = []

            def __aiter__(self):
                async def stream():
                    for event in events:
                        yield json.dumps(event)

                return stream()

            async def send(self, payload):
                self.sent.append(json.loads(payload))

        socket = Socket()
        await session.receive(socket)
        assert len(fixture.calls) == 1 and len(session.usage) == 1
        assert [e["type"] for e in socket.sent] == ["response.item.create", "response.create"]
        result = json.loads(socket.sent[0]["item"]["output"])
        assert len(result["occurrences"]) == 3
        assert session.voice_seconds == 16 and session.finalized

    asyncio.run(run())


def test_configuration_has_no_hosted_tools_or_storage():
    fixture_tools = [
        {"type": "function", "name": "calendar_query", "parameters": {"type": "object"}}
    ]
    live = session_config("gpt-live-1", fixture_tools)["session"]
    assert live["store"] is False
    assert live["delegation"]["responses"]["max_output_tokens"] == 768
    assert all(t["type"] == "function" for t in live["delegation"]["responses"]["tools"])
    realtime = session_config("gpt-realtime-2.1", fixture_tools)["session"]
    assert realtime["max_output_tokens"] == 512
    assert realtime["audio"]["input"]["turn_detection"]["interrupt_response"] is True


def test_live_acknowledgment_pause_cannot_finish_before_backend_answer():
    session = Session("gpt-live-1", None, b"")
    session.input_end, session.last_voice = 6, 9
    session.transcripts = [{"at": 9, "text": "I am checking."}]
    session.last_backend_done = 11
    assert not session.can_finish(13)
    session.transcripts.append({"at": 12, "text": "Tomorrow has"})
    assert not session.can_finish(14)
    session.last_voice = 16
    session.transcripts.append({"at": 16, "text": "three meetings."})
    assert session.can_finish(20)
