#!/usr/bin/env python3
"""Local CONNECT bridge to a fixed SSH forward. No TLS termination or key storage.

The SSH forward must map 127.0.0.1:18443 to api.openai.com:443 on the owned VPS.
Only CONNECT api.openai.com:443 is accepted. No ambient proxy/DNS changes.
"""

import asyncio
import contextlib

LISTEN_PORT = 17891
FORWARD_PORT = 18443
AUTHORITY = b"api.openai.com:443"
MAX_HEADER = 8192


async def read_connect(reader):
    data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
    if len(data) > MAX_HEADER:
        return 431
    lines = data[:-4].split(b"\r\n")
    if lines[0] not in {
        b"CONNECT " + AUTHORITY + b" HTTP/1.1",
        b"CONNECT " + AUTHORITY + b" HTTP/1.0",
    }:
        return 403
    for line in lines[1:]:
        if b":" not in line or line[:1] in (b" ", b"\t"):
            return 400
        name, value = line.split(b":", 1)
        if name.lower() in {b"content-length", b"transfer-encoding", b"proxy-authorization"}:
            return 400
        # HTTPX keeps :443; websockets omits the default TLS port in Host.
        # The CONNECT request target still pins the exact destination.
        if name.lower() == b"host" and value.strip() not in {AUTHORITY, b"api.openai.com"}:
            return 403
    return 200


async def pump(reader, writer):
    while chunk := await asyncio.wait_for(reader.read(65536), timeout=90):
        writer.write(chunk)
        await writer.drain()


class ConnectBridge:
    def __init__(self, upstream_port=FORWARD_PORT, limit=8):
        self.upstream_port = upstream_port
        self.limit = limit
        self.active = 0

    async def client(self, reader, writer):
        upstream = None
        tasks = []
        if self.active >= self.limit:
            writer.write(b"HTTP/1.1 503 Busy\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        self.active += 1
        try:
            code = await read_connect(reader)
            if code != 200:
                writer.write(f"HTTP/1.1 {code} Rejected\r\nConnection: close\r\n\r\n".encode())
                await writer.drain()
                return
            remote, upstream = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", self.upstream_port), timeout=5
            )
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            # TLS bytes pass unchanged; api.openai.com remains the client's SNI,
            # certificate identity and HTTP authority. Neither bridge stores keys.
            tasks = [
                asyncio.create_task(pump(reader, upstream)),
                asyncio.create_task(pump(remote, writer)),
            ]
            _, pending = await asyncio.wait(tasks, timeout=650, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
        except (
            OSError,
            asyncio.TimeoutError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ):
            pass
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            for stream in (upstream, writer):
                if stream:
                    stream.close()
                    with contextlib.suppress(OSError, asyncio.TimeoutError):
                        await asyncio.wait_for(stream.wait_closed(), timeout=1)
            self.active -= 1


async def main():
    bridge = ConnectBridge()
    server = await asyncio.start_server(bridge.client, "127.0.0.1", LISTEN_PORT, limit=MAX_HEADER)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
