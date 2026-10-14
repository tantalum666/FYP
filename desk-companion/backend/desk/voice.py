"""Server-held credentials, bounded realtime sessions, replaceable wire protocols.

No audio or transcript is persisted here. Only duration and provider-reported usage
are recorded. Read/write tools share the same proposal service as the text UI.
"""

import asyncio
import base64
import binascii
import contextlib
import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

import websockets
from fastapi import APIRouter, Depends, WebSocket, Request
from starlette.websockets import WebSocketDisconnect

from .assistant import TOOLS
from .persona import voice_instructions
from .store import DomainError
from .tool_dispatch import ToolDispatcher


def flatten_schema(schema):
    definitions = schema.get("$defs", {})

    def resolve(value):
        if isinstance(value, list):
            return [resolve(v) for v in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            return resolve(definitions[value["$ref"].split("/")[-1]])
        return {k: resolve(v) for k, v in value.items() if k not in {"$defs", "title", "default"}}

    return resolve(schema)


def pcm_chunk(value, maximum=6400):
    if not isinstance(value, str) or len(value) > maximum * 2:
        raise DomainError("INVALID_AUDIO", 422)
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise DomainError("INVALID_AUDIO", 422) from None
    if not result or len(result) > maximum or len(result) % 2:
        raise DomainError("INVALID_AUDIO", 422)
    return result


@dataclass
class VoiceConfig:
    provider: str = "none"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    voice: str = ""

    @classmethod
    def environment(cls):
        return cls(
            *(
                os.environ.get("DESK_VOICE_" + name, default)
                for name, default in [
                    ("PROVIDER", "none"),
                    ("ENDPOINT", ""),
                    ("MODEL", ""),
                    ("API_KEY", ""),
                    ("VOICE", ""),
                ]
            )
        )

    def valid(self):
        endpoint = self.endpoint or (
            "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            if self.provider == "gemini"
            else ""
        )
        parsed = urlsplit(endpoint)
        return bool(
            self.provider in {"qwen_audio", "gemini"}
            and self.model
            and self.api_key
            and parsed.scheme == "wss"
            and parsed.hostname
            and not parsed.username
            and not parsed.query
            and not parsed.fragment
        )


class QwenAudioProtocol:
    def setup(self, config, instructions):
        session = {
            "modalities": ["text", "audio"],
            "instructions": instructions,
            "input_audio_format": "pcm",
            "output_audio_format": "pcm",
            "turn_detection": {"type": "smart_turn"},
            "max_history_turns": 10,
            "tools": [
                {
                    "type": "function",
                    "function": {**tool, "parameters": flatten_schema(tool["parameters"])},
                }
                for tool in TOOLS
            ],
        }
        if config.voice:
            session["voice"] = config.voice
        return {"type": "session.update", "session": session}

    def audio(self, value):
        return {"type": "input_audio_buffer.append", "audio": value}

    def text(self, value):
        return [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": value}],
                },
            },
            {"type": "response.create"},
        ]

    def result(self, call, value):
        return [
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call["id"],
                    "output": json.dumps(value, ensure_ascii=False),
                },
            },
            {"type": "response.create"},
        ]

    def events(self, data):
        kind = data.get("type")
        if kind == "session.updated":
            return [{"type": "ready"}]
        if kind == "input_audio_buffer.speech_started":
            return [{"type": "interrupted"}, {"type": "state", "state": "listening"}]
        if kind == "input_audio_buffer.speech_stopped":
            return [{"type": "state", "state": "thinking"}]
        if kind in {"response.audio.delta", "response.output_audio.delta"}:
            return [{"type": "audio", "audio": data.get("delta", ""), "sample_rate": 24000}]
        if kind in {"response.audio_transcript.delta", "response.text.delta"}:
            return [
                {
                    "type": "transcript",
                    "role": "assistant",
                    "text": data.get("delta", ""),
                    "final": False,
                }
            ]
        if kind == "conversation.item.input_audio_transcription.completed":
            return [
                {
                    "type": "transcript",
                    "role": "user",
                    "text": data.get("transcript", ""),
                    "final": True,
                }
            ]
        if kind == "response.function_call_arguments.done":
            return [
                {
                    "type": "tool",
                    "id": data.get("call_id", ""),
                    "name": data.get("name", ""),
                    "arguments": data.get("arguments", "{}"),
                }
            ]
        if kind == "response.done":
            return [
                {"type": "turn_complete"},
                {"type": "usage", "usage": data.get("response", {}).get("usage", {})},
            ]
        if kind == "error":
            return [{"type": "error", "code": "VOICE_PROVIDER_ERROR"}]
        return []


class GeminiProtocol:
    def setup(self, config, instructions):
        generation = {"responseModalities": ["AUDIO"]}
        if config.voice:
            generation["speechConfig"] = {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": config.voice}}
            }
        declarations = [
            {
                "name": t["name"],
                "description": t["description"],
                "parametersJsonSchema": flatten_schema(t["parameters"]),
            }
            for t in TOOLS
        ]
        return {
            "setup": {
                "model": "models/" + config.model.removeprefix("models/"),
                "generationConfig": generation,
                "systemInstruction": {"parts": [{"text": instructions}]},
                "tools": [{"functionDeclarations": declarations}],
                "inputAudioTranscription": {},
                "outputAudioTranscription": {},
                "realtimeInputConfig": {
                    "automaticActivityDetection": {"disabled": False, "silenceDurationMs": 700},
                    "activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
                },
            }
        }

    def audio(self, value):
        return {"realtimeInput": {"audio": {"data": value, "mimeType": "audio/pcm;rate=16000"}}}

    def text(self, value):
        return [
            {
                "clientContent": {
                    "turns": [{"role": "user", "parts": [{"text": value}]}],
                    "turnComplete": True,
                }
            }
        ]

    def result(self, call, value):
        return [
            {
                "toolResponse": {
                    "functionResponses": [
                        {"id": call["id"], "name": call["name"], "response": value}
                    ]
                }
            }
        ]

    def events(self, data):
        out = []
        if "setupComplete" in data:
            out.append({"type": "ready"})
        content = data.get("serverContent", {})
        if content.get("interrupted"):
            out.append({"type": "interrupted"})
        for part in content.get("modelTurn", {}).get("parts", []):
            inline = part.get("inlineData", {})
            if inline.get("mimeType", "").startswith("audio/pcm"):
                out.append({"type": "audio", "audio": inline.get("data", ""), "sample_rate": 24000})
            if part.get("text") and not part.get("thought"):
                out.append(
                    {
                        "type": "transcript",
                        "role": "assistant",
                        "text": part["text"],
                        "final": False,
                    }
                )
        for field, role in [("inputTranscription", "user"), ("outputTranscription", "assistant")]:
            if content.get(field, {}).get("text"):
                out.append(
                    {
                        "type": "transcript",
                        "role": role,
                        "text": content[field]["text"],
                        "final": False,
                    }
                )
        if content.get("turnComplete"):
            out.append({"type": "turn_complete"})
        for call in data.get("toolCall", {}).get("functionCalls", []):
            out.append(
                {
                    "type": "tool",
                    "id": call.get("id", ""),
                    "name": call.get("name", ""),
                    "arguments": call.get("args", {}),
                }
            )
        if data.get("toolCallCancellation"):
            out.append({"type": "cancel_tools", "ids": data["toolCallCancellation"].get("ids", [])})
        if data.get("usageMetadata"):
            out.append({"type": "usage", "usage": data["usageMetadata"]})
        if "goAway" in data:
            out.append({"type": "error", "code": "VOICE_SESSION_ENDED"})
        if "error" in data:
            out.append({"type": "error", "code": "VOICE_PROVIDER_ERROR"})
        return out


class VoiceService:
    def __init__(self, runtime, config=None):
        self.runtime, self.store = runtime, runtime.store
        self.config = config or VoiceConfig.environment()
        self.tickets = {}
        self.lock = threading.Lock()
        self.active = False
        self.state = "idle"
        self.started = None
        self.connector = websockets.connect

    def snapshot(self):
        return {
            "configured": self.config.valid(),
            "provider": self.config.provider,
            "model": self.config.model,
            "state": self.state if self.config.valid() else "not_configured",
            "active": self.active,
            "input_sample_rate": 16000,
            "output_sample_rate": 24000,
            "max_session_seconds": 600,
        }

    def ticket(self, principal):
        if not self.config.valid():
            raise DomainError("VOICE_NOT_CONFIGURED", 409)
        with self.lock:
            self.tickets = {k: v for k, v in self.tickets.items() if v[0] > time.monotonic()}
            if self.active or len(self.tickets) >= 10:
                raise DomainError("VOICE_BUSY", 409)
            value = secrets.token_urlsafe(32)
            self.tickets[hashlib.sha256(value.encode()).hexdigest()] = (
                time.monotonic() + 30,
                principal,
            )
            return {"ticket": value, "expires_in": 30}

    def consume(self, value):
        with self.lock:
            item = self.tickets.pop(hashlib.sha256(str(value).encode()).hexdigest(), None)
            if not item or item[0] <= time.monotonic() or self.active:
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            if not self.principal_valid(item[1]):
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            self.active, self.state, self.started = True, "connecting", time.monotonic()
            return item[1]

    def principal_valid(self, principal):
        if principal["kind"] == "owner":
            return self.store.session_valid(principal.get("session"))
        if principal["kind"] == "agent":
            return self.runtime.data.preferences()["voice_enabled"]
        with self.store.connection() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM trusted_clients WHERE id=? AND revoked=0", (principal["id"],)
                ).fetchone()
            )

    async def run(self, socket, principal, language):
        protocol = GeminiProtocol() if self.config.provider == "gemini" else QwenAudioProtocol()
        endpoint = (
            self.config.endpoint
            or "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
        )
        headers = (
            {"x-goog-api-key": self.config.api_key}
            if self.config.provider == "gemini"
            else {"Authorization": "Bearer " + self.config.api_key}
        )
        if self.config.provider == "qwen_audio":
            endpoint += "?" + urlencode({"model": self.config.model})
        with self.store.connection() as conn:
            zone = self.store.settings(conn)["timezone"]
        instructions = voice_instructions(
            self.runtime.persona.current()["body"],
            language,
            self.store.clock().astimezone(ZoneInfo(zone)).isoformat(),
            zone,
        )
        session_id = uuid4().hex
        drafts, usage = {}, {}
        dispatcher = ToolDispatcher(self.runtime, session_id)
        ready = asyncio.Event()
        send_lock = asyncio.Lock()
        provider_send_lock = asyncio.Lock()
        last_activity = time.monotonic()
        input_bytes = 0

        async def send_client(value):
            async with send_lock:
                await asyncio.wait_for(socket.send_json(value), timeout=3)

        async def cancel_drafts(ids=None):
            await dispatcher.cancel(ids)
            for call_id in list(drafts):
                if ids is None or call_id in ids:
                    drafts.pop(call_id, None)
            await send_client({"type": "proposals_changed"})

        try:
            async with self.connector(
                endpoint,
                additional_headers=headers,
                open_timeout=12,
                max_size=2_000_000,
                max_queue=8,
                ping_interval=20,
            ) as provider:

                async def send_provider(value):
                    async with provider_send_lock:
                        await asyncio.wait_for(
                            provider.send(json.dumps(value, ensure_ascii=False)), timeout=3
                        )

                async def send_tool_result(event, result):
                    # An interruption can arrive while the client notification or
                    # a prior provider send is blocked. Check at each send boundary
                    # and never restart a cancelled Qwen response.
                    async with provider_send_lock:
                        responses = protocol.result(event, result)
                        for index in range(len(responses)):
                            current = dispatcher.current_result(event, result)
                            response = protocol.result(event, current)[index]
                            if (
                                current.get("error") == "TOOL_CANCELLED"
                                and response.get("type") == "response.create"
                            ):
                                continue
                            await asyncio.wait_for(
                                provider.send(json.dumps(response, ensure_ascii=False)), timeout=3
                            )

                await send_provider(protocol.setup(self.config, instructions))

                async def receive_client():
                    nonlocal input_bytes, last_activity
                    await asyncio.wait_for(ready.wait(), timeout=15)
                    async for raw in socket.iter_text():
                        if len(raw) > 20000:
                            raise DomainError("INVALID_AUDIO", 422)
                        message = json.loads(raw)
                        if not isinstance(message, dict):
                            raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
                        if message.get("type") == "audio":
                            chunk = pcm_chunk(message.get("audio"))
                            input_bytes += len(chunk)
                            # Bound upload to 1.3x realtime plus one second of burst.
                            if input_bytes > (time.monotonic() - self.started + 1) * 32000 * 1.3:
                                raise DomainError("AUDIO_RATE_LIMIT", 429)
                            await send_provider(protocol.audio(message["audio"]))
                        elif message.get("type") == "text":
                            value = str(message.get("text", ""))
                            if not 1 <= len(value) <= 3000:
                                raise DomainError("INVALID_TEXT", 422)
                            last_activity = time.monotonic()
                            for item in protocol.text(value):
                                await send_provider(item)
                        elif message.get("type") in {"stop", "mute"}:
                            return
                        elif message.get("type") == "interrupt":
                            await cancel_drafts()
                            await send_client({"type": "interrupted"})
                            if self.config.provider == "qwen_audio":
                                await send_provider({"type": "response.cancel"})
                            else:
                                for item in protocol.text(
                                    "Stop speaking. Wait for my next instruction."
                                ):
                                    await send_provider(item)
                        elif message.get("type") == "playback_ended":
                            self.state = "listening"
                        else:
                            raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)

                async def receive_provider():
                    nonlocal last_activity, usage
                    async for raw in provider:
                        for event in protocol.events(json.loads(raw)):
                            kind = event["type"]
                            if kind == "ready":
                                ready.set()
                                self.state = "listening"
                            elif kind == "state":
                                self.state = event["state"]
                                last_activity = time.monotonic()
                            elif kind in {"interrupted", "cancel_tools"}:
                                await cancel_drafts(event.get("ids"))
                                self.state = "listening"
                            elif kind == "audio":
                                pcm_chunk(event["audio"], maximum=1_000_000)
                                self.state = "speaking"
                                last_activity = time.monotonic()
                            elif kind == "transcript":
                                last_activity = time.monotonic()
                            elif kind == "tool":
                                self.state = "thinking"
                                last_activity = time.monotonic()
                                dispatcher.submit(event)
                                continue
                            elif kind == "usage":
                                usage = event["usage"]
                                continue
                            elif kind == "turn_complete":
                                self.state = "confirm" if drafts else "listening"
                            elif kind == "error":
                                await send_client(event)
                                return
                            await send_client(event)

                async def receive_tools():
                    nonlocal last_activity
                    while True:
                        event, result = await dispatcher.results.get()
                        result = dispatcher.current_result(event, result)
                        if "proposal" in result:
                            drafts[event["id"]] = result["proposal"]["id"]
                            self.state = "confirm"
                            await send_client({"type": "proposal", "proposal": result["proposal"]})
                        result = dispatcher.current_result(event, result)
                        if "job" in result:
                            await send_client({"type": "jobs_changed", "job": result["job"]})
                        await send_tool_result(event, result)
                        dispatcher.delivered(event["id"], result)
                        last_activity = time.monotonic()

                async def deadline():
                    while True:
                        await asyncio.sleep(1)
                        if not self.principal_valid(principal):
                            return
                        if (
                            time.monotonic() - self.started > 600
                            or time.monotonic() - last_activity > 45
                        ):
                            await send_client(
                                {
                                    "type": "ended",
                                    "reason": "session_limit"
                                    if time.monotonic() - self.started > 600
                                    else "idle",
                                }
                            )
                            return
                        if principal["kind"] != "owner" and principal["kind"] != "agent":
                            with self.store.connection() as conn:
                                alive = conn.execute(
                                    "SELECT 1 FROM trusted_clients WHERE id=? AND revoked=0",
                                    (principal["id"],),
                                ).fetchone()
                            if not alive:
                                return

                tasks = [
                    asyncio.create_task(fn())
                    for fn in (receive_client, receive_provider, receive_tools, deadline)
                ]
                try:
                    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        task.result()
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (
            DomainError,
            ValueError,
            TypeError,
            KeyError,
            OSError,
            TimeoutError,
            websockets.WebSocketException,
        ) as error:
            with contextlib.suppress(Exception):
                await send_client(
                    {
                        "type": "error",
                        "code": error.code
                        if isinstance(error, DomainError)
                        else "VOICE_CONNECTION_FAILED",
                    }
                )
        except WebSocketDisconnect:
            pass
        finally:
            dispatcher.stop_accepting()
            try:
                # Only numeric usage is evidence, not arbitrary provider response text.
                safe_usage = (
                    {
                        k: v
                        for k, v in usage.items()
                        if isinstance(v, (int, float)) and not isinstance(v, bool)
                    }
                    if isinstance(usage, dict)
                    else {}
                )
                with self.store.connection(write=True) as conn:
                    self.store.record(
                        conn,
                        "voice_session",
                        details={
                            "provider": self.config.provider,
                            "model": self.config.model,
                            "seconds": round(time.monotonic() - self.started, 1),
                            "input_audio_seconds": round(input_bytes / 32000, 1),
                            "usage": safe_usage,
                        },
                    )
            finally:
                # Do this before any await: disconnect cancellation must always
                # release the active slot, including when cleanup is interrupted.
                with self.lock:
                    self.active, self.state, self.started = False, "idle", None
            # Delivered drafts stay reviewable; in-flight/undelivered drafts are
            # invalidated even if their underlying thread returns after disconnect.
            await dispatcher.close()
            with contextlib.suppress(Exception):
                await socket.close()


def voice_routes(runtime, authenticated, agent, allowed_origins, limit):
    router = APIRouter(prefix="/api")

    @router.post("/voice/tickets")
    def ticket(request: Request, principal=Depends(authenticated)):
        return runtime.voice.ticket(
            {
                **principal,
                **(
                    {"session": request.cookies.get("desk_companion_session")}
                    if principal["kind"] == "owner"
                    else {}
                ),
            }
        )

    @router.post("/agent/voice/tickets", dependencies=[Depends(agent)])
    def agent_ticket():
        if not runtime.data.preferences().get("voice_enabled"):
            raise DomainError("VOICE_DISABLED", 409)
        return runtime.voice.ticket({"kind": "agent", "id": "local-voice", "name": "Local voice"})

    @router.websocket("/voice/ws")
    async def socket(ws: WebSocket):
        origin = ws.headers.get("origin")
        if origin and origin not in allowed_origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=5)
            if len(raw) > 2000:
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            first = json.loads(raw)
            if not isinstance(first, dict):
                raise DomainError("VOICE_TICKET_EXPIRED", 403)
            principal = runtime.voice.consume(first.get("ticket", ""))
        except (DomainError, ValueError, TimeoutError, WebSocketDisconnect):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
            return
        await runtime.voice.run(ws, principal, "zh" if first.get("language") == "zh" else "en")

    return router
