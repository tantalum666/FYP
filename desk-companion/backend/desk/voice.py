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
from dataclasses import dataclass, field as dataclass_field
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
from .voice_credentials import qwen_key
from .voice_media import MAX_IMAGE_BASE64, jpeg_image

QWEN_OMNI_MODEL = "qwen3.8-omni-flash-realtime"
QWEN_OMNI_ENDPOINT = "wss://maas.qianwenaiapi.com/api-ws/v1/realtime"


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
    api_key: str = dataclass_field(default="", repr=False)
    voice: str = ""
    configuration_error: str = ""

    @classmethod
    def environment(cls):
        config = cls(
            **{
                name.lower(): os.environ.get("DESK_VOICE_" + name, default)
                for name, default in [
                    ("PROVIDER", "none"),
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
        return config

    def valid(self):
        endpoint = self.endpoint or (
            "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            if self.provider == "gemini"
            else ""
        )
        parsed = urlsplit(endpoint)
        if self.provider == "qwen_omni":
            try:
                allowed = (
                    (
                        parsed.hostname == "maas.qianwenaiapi.com"
                        or bool(parsed.hostname and parsed.hostname.endswith(".maas.aliyuncs.com"))
                    )
                    and parsed.path == "/api-ws/v1/realtime"
                    and parsed.port is None
                )
            except ValueError:
                return False
            if not allowed or self.model != QWEN_OMNI_MODEL:
                return False
        return bool(
            self.provider in {"qwen_audio", "qwen_omni", "gemini"}
            and self.model
            and self.api_key
            and not self.configuration_error
            and parsed.scheme == "wss"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        )


class QwenAudioProtocol:
    def setup(self, config, instructions, *, allow_memory=True):
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
                if allow_memory or not tool["name"].startswith("memory_")
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


class QwenOmniProtocol(QwenAudioProtocol):
    """Qwen3.8 Omni's nested audio, VAD, images and response/tool lifecycle."""

    def __init__(self):
        self.response_idle = asyncio.Event()
        self.response_idle.set()
        self.active_response = None
        self.cancel_requested = False
        self.tool_calls = {}
        self.results = {}
        self.resumed = set()
        self.seen_usage = set()
        self.audio_transcript = False
        self.function_items = {}
        self.dispatched_calls = set()
        self.cancelled_responses = set()
        self.pending_cancel = False

    def tool_event(self, data, *, response_complete=False):
        item = data.get("item", {})
        item_id = data.get("item_id") or item.get("id")
        cached = self.function_items.get(item_id, {})
        merged = {
            **cached,
            **{key: value for key, value in item.items() if value is not None},
            **{
                key: data[key]
                for key in ("call_id", "name", "arguments", "response_id")
                if data.get(key) is not None
            },
        }
        if item_id:
            self.function_items[item_id] = merged
        call_id, name = merged.get("call_id"), merged.get("name")
        if (
            not call_id
            or not name
            or call_id in self.dispatched_calls
            or self.cancel_requested
            or merged.get("response_id") in self.cancelled_responses
        ):
            return []
        if "arguments" not in merged:
            return []
        group = merged.get("response_id") or data.get("response_id") or "unidentified"
        self.dispatched_calls.add(call_id)
        self.tool_calls.setdefault(group, set()).add(call_id)
        if (
            len(self.function_items) > 128
            or len(self.tool_calls) > 256
            or len(self.dispatched_calls) > 256
        ):
            return [{"type": "error", "code": "VOICE_SESSION_ENDED"}]
        if not response_complete and group != "unidentified":
            if self.active_response in {None, "pending", group}:
                self.active_response = group
                self.response_idle.clear()
        return [
            {
                "type": "tool",
                "id": call_id,
                "name": name,
                "arguments": merged["arguments"],
                "response_id": group,
            }
        ]

    def setup(self, config, instructions, *, allow_memory=True):
        tools = super().setup(config, instructions, allow_memory=allow_memory)["session"]["tools"]
        return {
            "type": "session.update",
            "session": {
                "model": config.model,
                "modalities": ["text", "audio"],
                "instructions": instructions
                + "\nCalendar ranges have an exclusive end. For a next-week query, start at next Monday 00:00 and end at the following Monday 00:00 in the user's timezone; do not use Sunday 23:59:59.",
                "audio": {
                    "input": {"format": {"type": "pcm", "sample_rate": 16000, "channels": 1}},
                    "output": {
                        "format": {"type": "pcm", "sample_rate": 24000},
                        "voice": config.voice or "Tina",
                    },
                },
                "input_audio_transcription": {"model": "qwen3-asr-flash-realtime"},
                "turn_detection": {
                    "type": "semantic_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 400,
                },
                "video": {"input": {"representation_compact": "none"}},
                "enable_search": False,
                "tools": tools,
                "max_tokens": 1024,
            },
        }

    def image(self, value):
        return {"type": "input_image_buffer.append", "image": value}

    def sent(self, message):
        if message.get("type") == "response.create":
            self.active_response = "pending"
            self.response_idle.clear()

    def cancel(self):
        if self.response_idle.is_set() or self.cancel_requested:
            return None
        self.cancel_requested = True
        if self.active_response == "pending":
            self.pending_cancel = True
            return None  # Cancel only after response.created confirms admission.
        elif self.active_response:
            self.cancelled_responses.add(self.active_response)
        return {"type": "response.cancel"}

    def result(self, call, value):
        # Resume only once all function outputs for this response are returned.
        return super().result(call, value)[:1]

    def delivered_group(self, call, value):
        group = call.get("response_id") or "unidentified"
        values = self.results.setdefault(group, {})
        values[call["id"]] = (call, value)
        expected = self.tool_calls.get(group, {call["id"]})
        if group in self.resumed or not expected.issubset(values):
            return []
        self.resumed.add(group)
        return list(values.values())

    def events(self, data):
        kind = data.get("type")
        if kind == "session.updated":
            session = data.get("session", {})
            output = session.get("audio", {}).get("output", {}).get("format", {})
            fmt = output.get("type", session.get("output_audio_format", "pcm"))
            if fmt not in {"pcm", "pcm16"} or output.get("sample_rate", 24000) != 24000:
                return [{"type": "error", "code": "VOICE_AUDIO_FORMAT_UNSUPPORTED"}]
        if kind == "response.created":
            self.active_response = data.get("response", {}).get("id") or "pending"
            self.response_idle.clear()
            if self.pending_cancel:
                self.cancelled_responses.add(self.active_response)
                self.pending_cancel = False
                self.cancel_requested = True
                return [{"type": "cancel_response"}]
            self.cancel_requested = self.active_response in self.cancelled_responses
            self.audio_transcript = False
            return [{"type": "state", "state": "thinking"}]
        if kind in {"response.output_item.added", "response.output_item.done"}:
            item = data.get("item", {})
            if item.get("type") != "function_call":
                return []
            if kind == "response.output_item.added":
                if item.get("id"):
                    self.function_items[item["id"]] = {
                        **item,
                        "response_id": data.get("response_id"),
                    }
                if len(self.function_items) > 128:
                    return [{"type": "error", "code": "VOICE_SESSION_ENDED"}]
                return []
            return self.tool_event(data)
        if kind == "response.function_call_arguments.done":
            return self.tool_event(data)
        if kind == "response.done":
            response = data.get("response", {})
            response_id = response.get("id")
            current = not self.active_response or self.active_response in {"pending", response_id}
            if current:
                if self.pending_cancel:
                    if response_id:
                        self.cancelled_responses.add(response_id)
                    self.pending_cancel = False
                self.active_response = None
                self.response_idle.set()
            result = []
            for item in response.get("output", []):
                if isinstance(item, dict) and item.get("type") == "function_call":
                    result.extend(
                        self.tool_event(
                            {"item": item, "response_id": response_id}, response_complete=True
                        )
                    )
            if current:
                result.append({"type": "turn_complete"})
            if response_id and response_id in self.seen_usage:
                return result
            if response_id:
                self.seen_usage.add(response_id)
            if len(self.seen_usage) > 256:
                return [{"type": "error", "code": "VOICE_SESSION_ENDED"}]
            usage = response.get("usage") or data.get("usage") or {}
            safe = {}
            if isinstance(usage, dict):
                for name in ("total_tokens", "input_tokens", "output_tokens"):
                    value = usage.get(name)
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                        safe[name] = value
                for direction in ("input", "output"):
                    details = usage.get(direction + "_tokens_details", {})
                    if isinstance(details, dict):
                        for modality in ("text", "audio", "image", "video", "cached"):
                            value = details.get(modality + "_tokens")
                            if (
                                isinstance(value, int)
                                and not isinstance(value, bool)
                                and value >= 0
                            ):
                                safe[f"{direction}_{modality}_tokens"] = value
            return result + [{"type": "usage", "usage": safe}]
        if (
            self.cancel_requested or data.get("response_id") in self.cancelled_responses
        ) and kind in {
            "response.audio.delta",
            "response.output_audio.delta",
            "response.audio_transcript.delta",
            "response.audio_transcript.done",
            "response.text.delta",
            "response.text.done",
        }:
            return []
        if kind == "response.audio_transcript.delta":
            self.audio_transcript = True
        if kind == "response.text.delta":
            return []  # Audio mode uses its transcript, avoiding duplicate text.
        if kind in {"response.audio_transcript.done", "response.text.done"}:
            if kind == "response.text.done" and self.audio_transcript:
                return []
            self.audio_transcript = kind == "response.audio_transcript.done"
            return [
                {
                    "type": "transcript",
                    "role": "assistant",
                    "text": data.get("transcript", data.get("text", "")),
                    "final": True,
                }
            ]
        return super().events(data)


class GeminiProtocol:
    def setup(self, config, instructions, *, allow_memory=True):
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
            if allow_memory or not t["name"].startswith("memory_")
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
            "supports_images": self.config.provider == "qwen_omni",
            "configuration_error": self.config.configuration_error,
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
        protocol = {
            "gemini": GeminiProtocol,
            "qwen_audio": QwenAudioProtocol,
            "qwen_omni": QwenOmniProtocol,
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
        if self.config.provider in {"qwen_audio", "qwen_omni"}:
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
        allow_memory = principal["kind"] in {"owner", "agent"}
        dispatcher = ToolDispatcher(self.runtime, session_id, allow_memory=allow_memory)
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
                        if isinstance(protocol, QwenOmniProtocol):
                            protocol.sent(value)
                        await asyncio.wait_for(
                            provider.send(json.dumps(value, ensure_ascii=False)), timeout=3
                        )

                async def send_tool_result(event, result):
                    # An interruption can arrive while the client notification or
                    # a prior provider send is blocked. Check at each send boundary
                    # and never restart a cancelled Qwen response.
                    if isinstance(protocol, QwenOmniProtocol):
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

                async def receive_client():
                    nonlocal input_bytes, last_activity, vision_active, last_image_at, image_count
                    await asyncio.wait_for(ready.wait(), timeout=15)
                    async for raw in socket.iter_text():
                        if len(raw) > MAX_IMAGE_BASE64 + 2000:
                            raise DomainError("VOICE_MESSAGE_TOO_LARGE", 422)
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
                        elif message.get("type") in {"vision_start", "vision_stop", "image"}:
                            if (
                                not isinstance(protocol, QwenOmniProtocol)
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
                            if isinstance(protocol, QwenOmniProtocol):
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
                        elif message.get("type") == "playback_ended":
                            self.state = "listening"
                        else:
                            raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)

                async def receive_provider():
                    nonlocal last_activity, usage
                    async for raw in provider:
                        data = json.loads(raw)
                        if not isinstance(data, dict):
                            raise DomainError("VOICE_PROVIDER_ERROR", 502)
                        for event in protocol.events(data):
                            kind = event["type"]
                            if kind == "ready":
                                ready.set()
                                self.state = "listening"
                            elif kind == "cancel_response":
                                await send_provider({"type": "response.cancel"})
                                continue
                            elif kind == "state":
                                self.state = event["state"]
                                last_activity = time.monotonic()
                            elif kind in {"interrupted", "cancel_tools"}:
                                await cancel_drafts(event.get("ids"))
                                self.state = "listening"
                                if isinstance(protocol, QwenOmniProtocol):
                                    cancel = protocol.cancel()
                                    if cancel:
                                        await send_provider(cancel)
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
                                if isinstance(protocol, QwenOmniProtocol):
                                    for key, value in event["usage"].items():
                                        usage[key] = usage.get(key, 0) + value
                                else:
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
                        if await send_tool_result(event, result):
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
                            "image_frames": image_count,
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
