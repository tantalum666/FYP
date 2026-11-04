"""Ephemeral owner-authorized PCM channel for local Alice keyword detection.

No provider access, transcript, recording or business action exists here.
"""

import asyncio
import contextlib
import hashlib
import importlib.util
import json
import os
import secrets
import sys
import threading
import time
from array import array
from pathlib import Path

from fastapi import APIRouter, Depends, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from .agents.wake import WakeDetector
from .store import DomainError


class WakeListening:
    def __init__(self, runtime):
        self.runtime = runtime
        self.directory = Path(
            os.environ.get("DESK_WAKE_MODEL_DIR", runtime.store.directory / "models/wake")
        )
        self.enabled = os.environ.get("DESK_WAKE_ENABLED") == "1"
        self.lock = threading.Lock()
        self.tickets = {}
        self.active = None
        self.detector_factory = lambda: WakeDetector(self.directory, phrase="alice")

    def available(self):
        if not self.enabled or importlib.util.find_spec("sherpa_onnx") is None:
            return False
        manifest = Path(__file__).resolve().parents[2] / "config/wake-model.json"
        return all(
            (self.directory / name).is_file() for name in json.loads(manifest.read_text())["files"]
        )

    def snapshot(self):
        return {"available": self.available(), "word": "Alice", "active": self.active is not None}

    def ticket(self, principal):
        if principal.get("kind") != "owner":
            raise DomainError("OWNER_REQUIRED", 403)
        if not self.available():
            raise DomainError("WAKE_NOT_CONFIGURED", 409)
        with self.lock:
            self.tickets = {
                key: value for key, value in self.tickets.items() if value[0] > time.monotonic()
            }
            if self.active or self.runtime.voice.active or len(self.tickets) >= 10:
                raise DomainError("VOICE_BUSY", 409)
            value = secrets.token_urlsafe(32)
            self.tickets[hashlib.sha256(value.encode()).hexdigest()] = (
                time.monotonic() + 30,
                principal,
            )
        return {"ticket": value, "expires_in": 30}

    def consume(self, value):
        with self.lock:
            saved = self.tickets.pop(hashlib.sha256(str(value).encode()).hexdigest(), None)
            if (
                not saved
                or saved[0] <= time.monotonic()
                or self.active
                or self.runtime.voice.active
            ):
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            if not self.runtime.store.session_valid(saved[1].get("session")):
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            lease = secrets.token_hex(12)
            self.active = lease
            return lease, saved[1]

    async def listen(self, socket, lease, principal):
        started = time.monotonic()
        total = 0
        try:
            detector = await asyncio.to_thread(self.detector_factory)
            await socket.send_json({"type": "ready", "word": "Alice"})
            while self.runtime.store.session_valid(principal.get("session")):
                try:
                    message = await asyncio.wait_for(socket.receive(), timeout=1)
                except TimeoutError:
                    continue
                if message["type"] == "websocket.disconnect":
                    break
                chunk = message.get("bytes")
                if chunk is None:
                    if message.get("text") == '{"type":"stop"}':
                        break
                    raise DomainError("INVALID_AUDIO", 422)
                if not chunk or len(chunk) > 6400 or len(chunk) % 2:
                    raise DomainError("INVALID_AUDIO", 422)
                total += len(chunk)
                if total > (time.monotonic() - started + 1) * 32000 * 1.3:
                    raise DomainError("AUDIO_RATE_LIMIT", 429)
                values = array("h", chunk)
                if sys.byteorder != "little":
                    values.byteswap()
                word = await asyncio.to_thread(detector.accept, [value / 32768 for value in values])
                if word:
                    await socket.send_json({"type": "wake", "word": "Alice"})
                    break
        except (DomainError, ValueError, OSError, RuntimeError, ImportError, WebSocketDisconnect):
            with contextlib.suppress(Exception):
                await socket.send_json({"type": "error", "code": "WAKE_UNAVAILABLE"})
        finally:
            with self.lock:
                if self.active == lease:
                    self.active = None
            with contextlib.suppress(Exception):
                await socket.close()


def wake_routes(runtime, owner, allowed_origins):
    router = APIRouter(prefix="/api")

    @router.post("/wake/tickets")
    def ticket(request: Request, principal=Depends(owner)):
        return runtime.wake.ticket(
            {**principal, "session": request.cookies.get("desk_companion_session")}
        )

    @router.websocket("/wake/ws")
    async def socket(ws: WebSocket):
        if ws.headers.get("origin") not in allowed_origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=5)
            if len(raw) > 2000:
                raise ValueError()
            first = json.loads(raw)
            if not isinstance(first, dict):
                raise ValueError()
            lease, principal = runtime.wake.consume(first.get("ticket", ""))
        except (DomainError, ValueError, TimeoutError, WebSocketDisconnect):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
            return
        await runtime.wake.listen(ws, lease, principal)

    return router
