"""In-memory protocol fixtures shared by voice Work acceptance tests."""

import asyncio
import json


class Provider:
    def __init__(self):
        self.sent = []
        self.queue = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        return json.dumps(await self.queue.get())

    async def send(self, raw):
        item = json.loads(raw)
        self.sent.append(item)
        if item.get("type") == "session.update":
            await self.queue.put({"type": "session.updated"})


class Socket:
    def __init__(self, when_ready=None, continue_text=False):
        self.messages = []
        self.queue = asyncio.Queue()
        self.when_ready = when_ready
        self.continue_text = continue_text
        self.closed = False

    async def send_json(self, item):
        self.messages.append(item)
        if item["type"] == "ready":
            if self.when_ready:
                self.when_ready()
                if self.continue_text:
                    await self.queue.put({"type": "text", "text": "Next turn"})
            else:
                await self.queue.put({"type": "stop"})

    async def iter_text(self):
        while True:
            yield json.dumps(await self.queue.get())

    async def close(self):
        self.closed = True
