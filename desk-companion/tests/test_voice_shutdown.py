import asyncio
import json

from desk.openai_live import OpenAILiveProtocol
from desk.voice_shutdown import finalize_live


def test_final_receipts_are_drained_after_client_reader_has_failed():
    async def run():
        protocol = OpenAILiveProtocol()
        protocol.events(
            {
                "type": "response.event",
                "event": {"type": "response.created", "response": {"id": "backend"}},
            }
        )
        protocol.closing = True
        sent = []

        class Provider:
            def __aiter__(self):
                async def receive():
                    yield json.dumps(
                        {
                            "type": "response.event",
                            "event": {
                                "type": "response.completed",
                                "response": {
                                    "id": "backend",
                                    "status": "completed",
                                    "output": [],
                                    "usage": {"input_tokens": 14, "output_tokens": 3},
                                },
                            },
                        }
                    )
                    yield json.dumps({"type": "session.closed", "usage": {"seconds": 7}})

                return receive()

        async def stopped():
            raise RuntimeError("client is already disconnected")

        reader = asyncio.create_task(stopped())
        await asyncio.gather(reader, return_exceptions=True)

        async def send(value):
            sent.append(value)

        result = await finalize_live(Provider(), protocol, reader, send, timeout=0.2)
        assert sent == [{"type": "session.close"}]
        assert result["voice_seconds"] == 7 and result["finalization_confirmed"] == 1
        assert result["backend_receipts_complete"] == 1 and result["backend_input_tokens"] == 14

    asyncio.run(run())


def test_running_receiver_keeps_ownership_while_final_usage_arrives():
    async def run():
        protocol = OpenAILiveProtocol()
        protocol.closing = True
        closed = asyncio.Event()

        async def reader_loop():
            await closed.wait()
            protocol.events({"type": "session.closed", "usage": {"seconds": 2}})

        reader = asyncio.create_task(reader_loop())

        class Provider:
            def __aiter__(self):
                raise AssertionError("a second receiver must not race the first")

        async def send(_):
            closed.set()

        result = await finalize_live(Provider(), protocol, reader, send, timeout=0.2)
        await reader
        assert result["finalization_confirmed"] == 1

    asyncio.run(run())
