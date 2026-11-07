"""Server-held credentials, bounded realtime sessions, replaceable wire protocols.

Audio is not stored. Owner text uses login/task-scoped bounded RAM continuity;
paired and local-agent sessions do not create a reusable owner history.
Duration and provider-reported usage are the only persisted session metrics.
Read/write tools share the same proposal service as the text UI.
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
from dataclasses import dataclass, field as dataclass_field
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

import websockets
from .openai_transport import model_proxy, validate_openai_proxy
from fastapi import APIRouter, Depends, WebSocket, Request
from starlette.websockets import WebSocketDisconnect

from .conversation import Conversations, draft_context, memory_context, task_context
from .store import DomainError
from .tool_dispatch import ToolDispatcher
from .voice_credentials import qwen_key, openai_key
from .voice_protocols import (
    flatten_schema as flatten_schema,
    QwenAudioProtocol as QwenAudioProtocol,
    QwenOmniProtocol,
    GeminiProtocol,
    RealtimeProtocol,
)
from .openai_live import OpenAILiveProtocol, OPENAI_LIVE_ENDPOINT
from .openai_voice import OpenAIRealtimeProtocol, OPENAI_REALTIME_ENDPOINT, OPENAI_REALTIME_MODELS
from .voice_media import MAX_IMAGE_BASE64, jpeg_image
from .voice_turns import VoiceTurns

from .context import voice_context_note
from .voice_work import VoiceWorkLedger, VoiceDraftFreeze
from .provider_policy import (
    ProviderWebSocketConnect,
    valid_api_key,
    valid_model,
    valid_provider_endpoint,
)

QWEN_OMNI_MODEL = "qwen3.8-omni-flash-realtime"
QWEN_OMNI_ENDPOINT = "wss://maas.qianwenaiapi.com/api-ws/v1/realtime"


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
    api_key: str = dataclass_field(default="", repr=False)
    voice: str = ""
    configuration_error: str = ""
    proxy_url: str = ""
    backend_model: str = "gpt-6.1-sol"

    @classmethod
    def environment(cls):
        config = cls(
            **{
                name.lower(): os.environ.get("DESK_VOICE_" + name, default)
                for name, default in [
                    ("PROVIDER", "openai_live"),
                    ("ENDPOINT", ""),
                    ("MODEL", ""),
                    ("API_KEY", ""),
                    ("VOICE", ""),
                ]
            }
        )
        if config.provider == "qwen_omni":
            config.model = config.model or QWEN_OMNI_MODEL
            config.endpoint = config.endpoint or QWEN_OMNI_ENDPOINT
            path = os.environ.get("DESK_QWEN_CREDENTIAL_FILE")
            if not config.api_key and path:
                try:
                    config.api_key = qwen_key(path)
                except (ValueError, OSError, UnicodeError):
                    config.configuration_error = "VOICE_CREDENTIALS_INVALID"
        if config.provider in {"openai_realtime", "openai_live"}:
            config.proxy_url = os.environ.get("DESK_OPENAI_PROXY_URL", "")
            try:
                validate_openai_proxy(config.proxy_url)
            except ValueError:
                config.configuration_error = "OPENAI_PROXY_INVALID"
            config.model = config.model or (
                "gpt-live-1" if config.provider == "openai_live" else "gpt-realtime-2.1"
            )
            config.backend_model = os.environ.get("DESK_LIVE_BACKEND_MODEL", "gpt-6.1-sol")
            config.endpoint = config.endpoint or (
                OPENAI_LIVE_ENDPOINT
                if config.provider == "openai_live"
                else OPENAI_REALTIME_ENDPOINT
            )
            path = os.environ.get("DESK_OPENAI_CREDENTIAL_FILE")
            if path:
                try:
                    config.api_key = openai_key(path)
                except (ValueError, OSError, UnicodeError):
                    config.api_key = ""
                    config.configuration_error = "VOICE_CREDENTIALS_INVALID"
            elif not config.api_key or "DESK_VOICE_PROVIDER" not in os.environ:
                config.api_key = os.environ.get("OPENAI_API_KEY", "")
            if os.environ.get("DESK_OPENAI_REGION_UNSUPPORTED") == "1":
                config.configuration_error = "OPENAI_REGION_UNSUPPORTED"
        return config

    def valid(self):
        try:
            model_proxy(self)
        except ValueError:
            return False
        if self.configuration_error or not valid_api_key(self.api_key):
            return False
        if self.provider == "openai_live":
            return (
                self.model == "gpt-live-1"
                and valid_model(self.backend_model)
                and valid_provider_endpoint(self.provider, self.endpoint, kind="voice")
            )
        if self.provider == "openai_realtime":
            return self.model in OPENAI_REALTIME_MODELS and valid_provider_endpoint(
                self.provider, self.endpoint, kind="voice"
            )
        if self.provider == "qwen_omni":
            endpoint = self.endpoint
            if not isinstance(endpoint, str) or self.model != QWEN_OMNI_MODEL:
                return False
            if endpoint == QWEN_OMNI_ENDPOINT:
                return True
            return valid_provider_endpoint("qwen_audio", endpoint, kind="voice")
        return valid_model(
            self.model, gemini_voice=self.provider == "gemini"
        ) and valid_provider_endpoint(self.provider, self.endpoint, kind="voice")


class VoiceService:
    def __init__(self, runtime, config=None):
        self.runtime, self.store = runtime, runtime.store
        self.work = VoiceWorkLedger(runtime)
        self.config = config or VoiceConfig.environment()
        self.tickets = {}
        self.lock = threading.Lock()
        self.forget_session = threading.Event()
        self.active = False
        self.state = "idle"
        self.started = None
        self.connector = ProviderWebSocketConnect
        self.turn_factory = VoiceTurns
        self.conversations = Conversations()

    def drop_live_session(self) -> bool:
        """Close an open provider socket so it stops using turns that included a forgotten fact.

        Returns False when no voice session is running. Logs the provider already
        stored on its own side are outside this desk.
        """
        if not self.active:
            self.forget_session.clear()
            return False
        self.forget_session.set()
        return True

    def snapshot(self):
        self.conversations.prune()
        return {
            "configured": self.config.valid(),
            "provider": self.config.provider,
            "model": self.config.model,
            "state": self.state if self.config.valid() else "not_configured",
            "active": self.active,
            "input_sample_rate": 16000,
            "output_sample_rate": 24000,
            "max_session_seconds": 600,
            "supports_images": self.config.provider in {"qwen_omni", "openai_realtime"},
            "supports_text": self.config.provider in {"qwen_omni", "openai_realtime"},
            "configuration_error": self.config.configuration_error,
            "config_revision": self.work.config_revision(),
            "wake_word": self.runtime.wake.snapshot()
            if hasattr(self.runtime, "wake")
            else {"available": False},
        }

    def ticket(self, principal):
        if not self.config.valid():
            raise DomainError("VOICE_NOT_CONFIGURED", 409)
        with self.lock:
            self.tickets = {k: v for k, v in self.tickets.items() if v[0] > time.monotonic()}
            if (
                self.active
                or getattr(getattr(self.runtime, "wake", None), "active", None) is not None
                or len(self.tickets) >= 10
            ):
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
            if (
                not item
                or item[0] <= time.monotonic()
                or self.active
                or getattr(getattr(self.runtime, "wake", None), "active", None) is not None
            ):
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

    async def run(
        self,
        socket,
        principal,
        language,
        mode="voice",
        conversation_id=None,
        prebuffer_ms=0,
        *,
        task_id=None,
        wake_triggered=False,
    ):
        if not self.config.valid():
            await socket.send_json({"type": "error", "code": "VOICE_NOT_CONFIGURED"})
            self.active, self.state, self.started = False, "idle", None
            await socket.close()
            return
        protocol = {
            "gemini": GeminiProtocol,
            "qwen_audio": QwenAudioProtocol,
            "qwen_omni": QwenOmniProtocol,
            "openai_realtime": OpenAIRealtimeProtocol,
            "openai_live": OpenAILiveProtocol,
        }[self.config.provider]()
        endpoint = (
            self.config.endpoint
            or "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
        )
        headers = (
            {"x-goog-api-key": self.config.api_key}
            if self.config.provider == "gemini"
            else {"Authorization": "Bearer " + self.config.api_key}
        )
        if self.config.provider in {"qwen_audio", "qwen_omni", "openai_realtime"}:
            endpoint += "?" + urlencode({"model": self.config.model})
        with self.store.connection() as conn:
            zone = self.store.settings(conn)["timezone"]
        from .style import render_prompt

        instructions = render_prompt(
            self.runtime.persona.current()["body"],
            self.runtime.data.preferences(),
            language,
            channel="voice",
            now_iso=self.store.clock().astimezone(ZoneInfo(zone)).isoformat(),
            zone=zone,
        )
        session_id = uuid4().hex
        drafts, usage = {}, {}
        tool_failures = {}
        grounding_retries = set()
        turns = self.turn_factory()
        allow_memory = principal["kind"] in {"owner", "agent"}
        revision, facts = memory_context(self.runtime, allow_memory)
        instructions += facts
        instructions += draft_context(self.runtime, principal["kind"] == "owner")
        instructions += self.runtime.permissions.instructions(principal)
        conversation = None
        work_session_ref = None
        assistant_text = ""
        live_user_text = ""
        restored = False
        greeted = False
        if isinstance(protocol, RealtimeProtocol):
            protocol.mode = mode
            protocol.language = language
        dispatcher = ToolDispatcher(
            self.runtime,
            session_id,
            allow_memory=allow_memory,
            language=language,
            principal=principal,
            task_id=task_id,
        )
        ready = asyncio.Event()
        send_lock = asyncio.Lock()
        provider_send_lock = asyncio.Lock()
        last_activity = time.monotonic()
        input_bytes = 0
        vision_active, last_image_at, image_count = False, None, 0

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
            if isinstance(protocol, OpenAILiveProtocol) and mode != "voice":
                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
            if mode not in {"text", "voice"} or (
                mode == "text" and not isinstance(protocol, RealtimeProtocol)
            ):
                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
            work_session_ref = self.work.begin(principal)
            instructions += task_context(self.runtime, principal, task_id)
            conversation = self.conversations.open(
                principal, revision, conversation_id, task_id=task_id
            )
            if not isinstance(protocol, RealtimeProtocol):
                instructions += "\n" + voice_context_note(
                    self.runtime, allow_memory=allow_memory, conversation=conversation
                )
            if isinstance(protocol, OpenAILiveProtocol):
                protocol.wake_triggered = wake_triggered
                protocol.voice_style = self.runtime.persona.current()["body"]
                remaining = 6000
                for item in reversed(conversation.replay() if conversation else []):
                    message = item.get("item", {})
                    content = message.get("content", [])
                    text = content[0].get("text", "") if content else ""
                    size = len(text.encode())
                    if not text or size > remaining:
                        continue
                    remaining -= size
                    protocol.initial_items.insert(0, message)
            async with self.connector(
                endpoint,
                additional_headers=headers,
                open_timeout=12,
                close_timeout=2,
                max_size=2_000_000,
                max_queue=8,
                ping_interval=20,
                proxy=model_proxy(self.config),
            ) as provider:

                async def send_provider(value):
                    async with provider_send_lock:
                        if isinstance(protocol, RealtimeProtocol):
                            protocol.sent(value)
                        await asyncio.wait_for(
                            provider.send(json.dumps(value, ensure_ascii=False)), timeout=3
                        )

                async def send_tool_result(event, result):
                    # An interruption can arrive while the client notification or
                    # a prior provider send is blocked. Check at each send boundary
                    # and never restart a cancelled realtime response.
                    if isinstance(protocol, RealtimeProtocol):
                        # Waiting does not hold the send lock: audio, interrupt and
                        # provider response.done must remain able to make progress.
                        end = time.monotonic() + 5
                        while True:
                            await asyncio.wait_for(
                                protocol.response_idle.wait(),
                                timeout=max(0.01, end - time.monotonic()),
                            )
                            async with provider_send_lock:
                                if not protocol.response_idle.is_set():
                                    if time.monotonic() >= end:
                                        raise TimeoutError()
                                    continue
                                current = dispatcher.current_result(event, result)
                                if (
                                    current.get("error") == "TOOL_CANCELLED"
                                    or protocol.cancel_requested
                                ):
                                    protocol.delivered_group(event, current)
                                    return False
                                for response in protocol.result(event, current):
                                    await asyncio.wait_for(
                                        provider.send(json.dumps(response, ensure_ascii=False)),
                                        timeout=3,
                                    )
                                turns.delivered(event.get("_turn_id"), event["id"], current)
                                group = protocol.delivered_group(event, current)
                                eligible = any(
                                    dispatcher.current_result(call, value).get("error")
                                    != "TOOL_CANCELLED"
                                    for call, value in group
                                )
                                if eligible and not protocol.cancel_requested:
                                    response = {"type": "response.create"}
                                    protocol.sent(response)
                                    await asyncio.wait_for(
                                        provider.send(json.dumps(response)), timeout=3
                                    )
                                return True
                    async with provider_send_lock:
                        turns.delivered(event.get("_turn_id"), event["id"], result)
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
                    return True

                await send_provider(
                    protocol.setup(self.config, instructions, allow_memory=allow_memory)
                )

                async def refresh_context():
                    if not isinstance(protocol, RealtimeProtocol):
                        return True
                    current_revision, current_facts = memory_context(self.runtime, allow_memory)
                    if current_revision != revision:
                        if conversation:
                            conversation.items.clear()
                            conversation.revision = current_revision
                        await send_client({"type": "ended", "reason": "memory_changed"})
                        return False
                    with self.store.connection() as conn:
                        current_zone = self.store.settings(conn)["timezone"]
                    current = render_prompt(
                        self.runtime.persona.current()["body"],
                        self.runtime.data.preferences(),
                        language,
                        channel="voice",
                        now_iso=self.store.clock().astimezone(ZoneInfo(current_zone)).isoformat(),
                        zone=current_zone,
                    )
                    current += current_facts + draft_context(
                        self.runtime, principal["kind"] == "owner"
                    )
                    current += task_context(self.runtime, principal, task_id)
                    current += self.runtime.permissions.instructions(principal)
                    ready.clear()
                    await send_provider(protocol.instructions_update(current))
                    await asyncio.wait_for(ready.wait(), timeout=5)
                    return True

                async def receive_client():
                    nonlocal \
                        input_bytes, \
                        last_activity, \
                        vision_active, \
                        last_image_at, \
                        image_count, \
                        mode, \
                        assistant_text
                    await asyncio.wait_for(ready.wait(), timeout=15)
                    async for raw in socket.iter_text():
                        if len(raw) > MAX_IMAGE_BASE64 + 2000:
                            raise DomainError("VOICE_MESSAGE_TOO_LARGE", 422)
                        message = json.loads(raw)
                        if not isinstance(message, dict):
                            raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
                        if message.get("type") == "audio":
                            if mode != "voice":
                                raise DomainError("MICROPHONE_DISABLED", 409)
                            chunk = pcm_chunk(message.get("audio"))
                            input_bytes += len(chunk)
                            # Bound upload to 1.3x realtime plus one second of burst.
                            if (
                                input_bytes
                                > (time.monotonic() - self.started + 1 + prebuffer_ms / 1000)
                                * 32000
                                * 1.3
                            ):
                                raise DomainError("AUDIO_RATE_LIMIT", 429)
                            await send_provider(protocol.audio(message["audio"]))
                        elif message.get("type") in {"vision_start", "vision_stop", "image"}:
                            if isinstance(protocol, OpenAILiveProtocol):
                                raise DomainError("VOICE_VISION_NOT_ALLOWED", 403)
                            if (
                                not isinstance(protocol, RealtimeProtocol)
                                or principal["kind"] != "owner"
                                or not self.principal_valid(principal)
                            ):
                                raise DomainError("VOICE_VISION_NOT_ALLOWED", 403)
                            if message["type"] == "vision_start":
                                vision_active = True
                                await send_client({"type": "vision", "active": True})
                            elif message["type"] == "vision_stop":
                                vision_active = False
                                await send_client({"type": "vision", "active": False})
                            else:
                                if not vision_active or not input_bytes:
                                    raise DomainError("VOICE_VISION_NOT_READY", 409)
                                now = time.monotonic()
                                if last_image_at is not None and now - last_image_at < 0.9:
                                    raise DomainError("VOICE_IMAGE_RATE_LIMIT", 429)
                                jpeg_image(message.get("image"))
                                await send_provider(protocol.image(message["image"]))
                                last_image_at, last_activity = now, now
                                image_count += 1
                                await send_client({"type": "image_sent", "count": image_count})
                        elif message.get("type") == "text":
                            if isinstance(protocol, OpenAILiveProtocol):
                                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
                            value = message.get("text", "")
                            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 3000:
                                raise DomainError("INVALID_TEXT", 422)
                            if isinstance(protocol, RealtimeProtocol) and (
                                not protocol.response_idle.is_set()
                                or (turns.current and turns.current.pending)
                            ):
                                await send_client({"type": "rejected", "code": "CONVERSATION_BUSY"})
                                continue
                            assistant_text = ""
                            last_activity = time.monotonic()
                            turns.start()
                            turns.transcript(value, visual_context=image_count > 0)
                            await send_client({**turns.end(), "input_kind": "text"})
                            if not await refresh_context():
                                return
                            if conversation:
                                conversation.append("user", value)
                                conversation.touched = time.monotonic()
                            for item in protocol.text(value):
                                await send_provider(item)
                            await send_client(
                                {"type": "transcript", "role": "user", "text": value, "final": True}
                            )
                        elif (
                            message.get("type") == "context_refresh"
                            and principal["kind"] == "owner"
                        ):
                            if not await refresh_context():
                                return
                        elif message.get("type") == "mode" and isinstance(
                            protocol, RealtimeProtocol
                        ):
                            if isinstance(protocol, OpenAILiveProtocol):
                                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
                            next_mode = message.get("mode")
                            if next_mode not in {"text", "voice"}:
                                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
                            if not protocol.response_idle.is_set() or (
                                turns.current and turns.current.pending
                            ):
                                await cancel_drafts()
                            cancel = protocol.cancel()
                            if cancel:
                                await send_provider(cancel)
                            await asyncio.wait_for(protocol.response_idle.wait(), timeout=5)
                            turns.finish("mode_changed")
                            assistant_text = ""
                            mode = next_mode
                            await send_provider({"type": "input_audio_buffer.clear"})
                            await send_client({"type": "interrupted"})
                            await send_provider(protocol.mode_update(mode))
                        elif message.get("type") in {"stop", "mute"}:
                            return
                        elif message.get("type") == "interrupt":
                            if isinstance(protocol, OpenAILiveProtocol):
                                await cancel_drafts()
                                await send_client({"type": "ended", "reason": "stopped"})
                                return
                            assistant_text = ""
                            turns.finish("interrupted")
                            await cancel_drafts()
                            await send_client({"type": "interrupted"})
                            if isinstance(protocol, RealtimeProtocol):
                                cancel = protocol.cancel()
                                if cancel:
                                    await send_provider(cancel)
                            elif self.config.provider == "qwen_audio":
                                await send_provider({"type": "response.cancel"})
                            else:
                                for item in protocol.text(
                                    "Stop speaking. Wait for my next instruction."
                                ):
                                    await send_provider(item)
                        elif message.get("type") == "playback_started":
                            timing = turns.playback(message)
                            if timing:
                                await send_client(timing)
                        elif message.get("type") == "input_started" and isinstance(
                            protocol, OpenAILiveProtocol
                        ):
                            turns.start()
                            last_activity = time.monotonic()
                        elif message.get("type") == "input_ended":
                            end_ms = message.get("input_end_ms")
                            if end_ms is not None and (
                                isinstance(end_ms, bool)
                                or not isinstance(end_ms, (int, float))
                                or not 0 <= end_ms <= input_bytes / 32
                            ):
                                raise DomainError("INVALID_INPUT_BOUNDARY", 422)
                            # A local acoustic boundary protects against missing provider VAD.
                            # Later response.created / VAD events do not restart this timer.
                            if self.state != "speaking" and (
                                not turns.current or turns.current.ended is None
                            ):
                                await send_client(turns.end(end_ms))
                        elif message.get("type") == "playback_ended":
                            self.state = "listening"
                            current = turns.current
                            if (
                                current
                                and message.get("turn_id") == current.id
                                and current.progress_at is not None
                            ):
                                turns.finish("played")
                        else:
                            raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)

                async def receive_provider():
                    nonlocal last_activity, usage, restored, assistant_text, greeted, live_user_text
                    async for raw in provider:
                        data = json.loads(raw)
                        if not isinstance(data, dict):
                            raise DomainError("VOICE_PROVIDER_ERROR", 502)
                        for event in protocol.events(data):
                            kind = event["type"]
                            if kind == "ready":
                                if (
                                    conversation
                                    and not restored
                                    and isinstance(protocol, RealtimeProtocol)
                                    and not isinstance(protocol, OpenAILiveProtocol)
                                ):
                                    for item in conversation.replay():
                                        await send_provider(item)
                                    restored = True
                                if wake_triggered and not greeted:
                                    greeted = True
                                    for greeting in (
                                        protocol.greeting_events()
                                        if isinstance(protocol, OpenAILiveProtocol)
                                        else protocol.text("Alice")
                                    ):
                                        await send_provider(greeting)
                                ready.set()
                                self.state = "listening"
                                event = {
                                    **event,
                                    "mode": mode,
                                    "input_markers": isinstance(protocol, OpenAILiveProtocol),
                                    "conversation_id": conversation.id if conversation else None,
                                }
                            elif kind == "cancel_response":
                                await send_provider({"type": "response.cancel"})
                                continue
                            elif kind == "state":
                                if event.get("speech_ended"):
                                    await send_client(turns.end(event.get("input_end_ms")))
                                self.state = event["state"]
                                last_activity = time.monotonic()
                            elif kind in {"interrupted", "cancel_tools"}:
                                assistant_text = ""
                                if kind == "interrupted":
                                    turns.finish("interrupted")
                                    if event.get("speech_started"):
                                        turns.start()
                                await cancel_drafts(event.get("ids"))
                                self.state = "listening"
                                if isinstance(protocol, RealtimeProtocol):
                                    cancel = protocol.cancel()
                                    if cancel:
                                        await send_provider(cancel)
                            elif kind == "audio":
                                if mode == "text":
                                    raise DomainError("VOICE_OUTPUT_MODE_MISMATCH", 409)
                                pcm_chunk(event["audio"], maximum=1_000_000)
                                if (
                                    turns.current
                                    and turns.current.needs_tool
                                    and not turns.current.tool_delivered
                                ):
                                    continue  # Never play a schedule answer backed only by old chat.
                                if not turns.current or turns.current.ended is None:
                                    await send_client(turns.end())
                                event = {**event, **turns.audio()}
                                self.state = "speaking"
                                last_activity = time.monotonic()
                            elif kind == "transcript":
                                normalized = self.work.observe(work_session_ref, event)
                                if normalized is not None:
                                    await send_client(normalized)
                                event = {
                                    key: value
                                    for key, value in event.items()
                                    if key
                                    not in {
                                        "input_key",
                                        "input_operation",
                                        "input_sequence",
                                        "boundary",
                                    }
                                }
                                if event.get("role") == "user":
                                    if isinstance(protocol, OpenAILiveProtocol):
                                        live_user_text = (live_user_text + event.get("text", ""))[
                                            -8000:
                                        ]
                                    turns.transcript(
                                        event.get("text", ""), visual_context=image_count > 0
                                    )
                                    if conversation and event.get("final"):
                                        conversation.append("user", event.get("text", ""))
                                else:
                                    if (
                                        turns.current
                                        and turns.current.needs_tool
                                        and not turns.current.tool_delivered
                                    ):
                                        continue
                                    assistant_text = (
                                        event.get("text", "")
                                        if event.get("final")
                                        else assistant_text + event.get("text", "")
                                    )[:8000]
                                    if mode == "text":
                                        timing = turns.text(event.get("text", ""))
                                        if timing:
                                            await send_client(timing)
                                last_activity = time.monotonic()
                            elif kind == "tool":
                                self.state = "thinking"
                                last_activity = time.monotonic()
                                if not turns.current or turns.current.ended is None:
                                    await send_client(turns.end())
                                event = {**event, "_turn_id": turns.tool(event["id"])}
                                dispatcher.submit(event)
                                continue
                            elif kind == "usage":
                                if isinstance(protocol, RealtimeProtocol) and not isinstance(
                                    protocol, OpenAILiveProtocol
                                ):
                                    for key, value in event["usage"].items():
                                        usage[key] = usage.get(key, 0) + value
                                else:
                                    usage = event["usage"]
                                continue
                            elif kind == "turn_complete":
                                if turns.current and turns.current.pending:
                                    continue  # A function-call round is not the spoken answer.
                                if (
                                    turns.current
                                    and turns.current.needs_tool
                                    and not turns.current.tool_delivered
                                ):
                                    turn_id = turns.current.id
                                    if turn_id in grounding_retries or not isinstance(
                                        protocol, RealtimeProtocol
                                    ):
                                        await send_client(
                                            {
                                                "type": "error",
                                                "code": "VOICE_UNGROUNDED_RESPONSE",
                                            }
                                        )
                                        return
                                    grounding_retries.add(turn_id)
                                    assistant_text = ""
                                    # One bounded repair within the original deadline, never a cached answer.
                                    for message in protocol.text(
                                        "Application validation: no successful tool read was returned in this turn. "
                                        "Your ungrounded answer was not delivered. Call the relevant read tool now "
                                        "(calendar_query for schedules/counts), then answer from its current result. "
                                        "Do not create a draft unless the user requested a change."
                                    ):
                                        await send_provider(message)
                                    continue
                                if mode == "text" and not assistant_text.strip():
                                    await send_client(
                                        {"type": "error", "code": "VOICE_EMPTY_RESPONSE"}
                                    )
                                    return
                                event = {
                                    **event,
                                    "turn_id": turns.current.id if turns.current else None,
                                    "mode": mode,
                                }
                                if conversation and assistant_text:
                                    conversation.append("assistant", assistant_text)
                                    conversation.touched = time.monotonic()
                                assistant_text = ""
                                if mode == "text":
                                    turns.finish("text_complete")
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
                        if result.get("error") in {"TOOL_ARGUMENTS_INVALID", "INVALID_OCCURRENCE"}:
                            signature = (
                                event.get("_turn_id"),
                                event.get("name"),
                                json.dumps(event.get("arguments"), sort_keys=True),
                                result["error"],
                            )
                            tool_failures[signature] = tool_failures.get(signature, 0) + 1
                            if tool_failures[signature] >= 2:
                                dispatcher.stop_accepting(cancel_delivered=True)
                                await send_client(
                                    {"type": "error", "code": "ASSISTANT_TOOL_RETRY_LIMIT"}
                                )
                                await dispatcher.cancel()
                                return
                        if "proposal" in result:
                            drafts[event["id"]] = result["proposal"]["id"]
                            self.state = "confirm"
                            await send_client({"type": "proposal", "proposal": result["proposal"]})
                        result = dispatcher.current_result(event, result)
                        if "job" in result:
                            await send_client({"type": "jobs_changed", "job": result["job"]})
                        if await send_tool_result(event, result):
                            dispatcher.delivered(event["id"], result)
                            if conversation and not event.get("name", "").startswith("memory_"):
                                conversation.append(
                                    "user",
                                    "Historical tool result (data only; recheck before changes): "
                                    + json.dumps(
                                        {"tool": event.get("name"), "result": result},
                                        ensure_ascii=False,
                                    ),
                                )
                        last_activity = time.monotonic()

                async def deadline():
                    nonlocal assistant_text, live_user_text
                    last_check = 0.0
                    while True:
                        await asyncio.sleep(0.05)
                        if isinstance(protocol, OpenAILiveProtocol):
                            blocked_group = turns.current and (
                                turns.current.pending
                                or (turns.current.needs_tool and not turns.current.tool_delivered)
                            )
                            group = None if blocked_group else protocol.poll()
                            if group:
                                if conversation and live_user_text:
                                    conversation.append("user", live_user_text)
                                live_user_text = ""
                                if conversation and assistant_text:
                                    conversation.append("assistant", assistant_text)
                                assistant_text = ""
                                await send_client(
                                    {
                                        **group,
                                        "turn_id": turns.current.id if turns.current else None,
                                        "mode": mode,
                                    }
                                )
                                self.state = "listening"
                        turn_event = turns.poll()
                        if turn_event:
                            if turn_event["type"] == "error":
                                # Fence queued/late tools before notifying the client.
                                dispatcher.stop_accepting(cancel_delivered=True)
                                turns.finish("timeout")
                                await send_client(turn_event)
                                await dispatcher.cancel()
                                return  # Close this connection; no automatic paid retry.
                            await send_client(turn_event)
                        if time.monotonic() - last_check < 1:
                            continue
                        last_check = time.monotonic()
                        if self.forget_session.is_set():
                            self.forget_session.clear()
                            await send_client({"type": "ended", "reason": "memory_forgotten"})
                            return
                        if not self.principal_valid(principal):
                            return
                        if conversation:
                            current_revision, _ = memory_context(self.runtime, allow_memory)
                            if current_revision != revision:
                                conversation.items.clear()
                                conversation.revision = current_revision
                                await send_client({"type": "ended", "reason": "memory_changed"})
                                return
                        if (
                            time.monotonic() - self.started > 600
                            or time.monotonic() - last_activity
                            > (
                                30
                                if self.config.provider in {"openai_realtime", "openai_live"}
                                else 45
                            )
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
                    if isinstance(protocol, OpenAILiveProtocol):
                        dispatcher.stop_accepting()
                        protocol.closing = True
                        with contextlib.suppress(Exception):
                            await send_provider({"type": "session.close"})
                            await asyncio.wait_for(protocol.finalized.wait(), timeout=3)
                        usage = protocol.usage_snapshot()
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (
            DomainError,
            ValueError,
            TypeError,
            KeyError,
            ImportError,
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
            with contextlib.suppress(Exception):
                self.work.end(work_session_ref)
            dispatcher.stop_accepting()
            turns.finish("session_ended")
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
                            "prebuffer_allowance_ms": prebuffer_ms,
                            "image_frames": image_count,
                            "usage": safe_usage,
                            "turns": turns.history,
                        },
                    )
            finally:
                if conversation:
                    current_revision, _ = memory_context(self.runtime, allow_memory)
                    if current_revision != revision:
                        conversation.items.clear()
                        conversation.revision = current_revision
                    conversation.touched = time.monotonic()
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

    @router.delete("/voice/conversations/{conversation_id}")
    def forget(conversation_id: str, request: Request, principal=Depends(authenticated)):
        if principal["kind"] != "owner":
            raise DomainError("OWNER_REQUIRED", 403)
        runtime.voice.conversations.forget(
            {**principal, "session": request.cookies.get("desk_companion_session")}, conversation_id
        )
        return {"cleared": True}

    @router.post("/voice/work-drafts")
    def work_draft(payload: VoiceDraftFreeze, request: Request, principal=Depends(authenticated)):
        return runtime.voice.work.freeze(
            payload, {**principal, "session": request.cookies.get("desk_companion_session")}
        )

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
            prebuffer_ms = first.get("prebuffer_ms", 0)
            if type(prebuffer_ms) is not int or not 0 <= prebuffer_ms <= 5000:
                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
            if type(first.get("wake_triggered", False)) is not bool:
                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
            principal = runtime.voice.consume(first.get("ticket", ""))
        except (DomainError, ValueError, TimeoutError, WebSocketDisconnect):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
            return
        await runtime.voice.run(
            ws,
            principal,
            "zh" if first.get("language") == "zh" else "en",
            first.get("mode", "voice"),
            first.get("conversation_id"),
            prebuffer_ms,
            task_id=first.get("task_id"),
            wake_triggered=first.get("wake_triggered", False),
        )

    return router
