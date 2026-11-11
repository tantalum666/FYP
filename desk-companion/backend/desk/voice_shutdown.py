"""Drain final Live receipts even when the client-facing reader has stopped."""

import asyncio
import contextlib
import json


async def finalize_live(provider, protocol, reader, send, timeout=3):
    async def collect():
        closed = asyncio.create_task(protocol.finalized.wait())
        try:
            await asyncio.wait((reader, closed), return_when=asyncio.FIRST_COMPLETED)
            if protocol.finalized.is_set():
                return
            # Only one receiver may read the socket. The original reader has
            # finished, so this path consumes receipts without sending to UI.
            async for raw in provider:
                value = json.loads(raw)
                if isinstance(value, dict):
                    protocol.events(value)
                if protocol.finalized.is_set():
                    return
        finally:
            closed.cancel()
            await asyncio.gather(closed, return_exceptions=True)

    with contextlib.suppress(Exception):
        await send({"type": "session.close"})
        await asyncio.wait_for(collect(), timeout=timeout)
    return protocol.usage_snapshot()
