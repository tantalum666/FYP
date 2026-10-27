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
from .conversation import Conversations, draft_context, memory_context, task_context
from .persona import voice_instructions
from .store import DomainError
from .tool_dispatch import ToolDispatcher
from .voice_credentials import qwen_key
from .voice_media import MAX_IMAGE_BASE64, jpeg_image
from .voice_turns import VoiceTurns

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
        result = {k: resolve(v) for k, v in value.items() if k not in {"$defs", "title", "default"}}
        properties = result.get("properties", {})
        for name, item in properties.items():
            if name.endswith("_local"):
                for variant in item.get("anyOf", [item]):
                    if variant.get("format") == "date-time":
                        variant.pop("format")
                        variant["pattern"] = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:00)?$"
                item["description"] = (
                    "Local wall time YYYY-MM-DDTHH:MM, without Z or UTC offset. Use the separate timezone field."
                )
        if {"action", "expected_version", "scope", "occurrence_key"} <= properties.keys():
            result["required"] = list(dict.fromkeys([*result.get("required", []), "scope"]))
            properties["scope"]["description"] = (
                "occurrence: edit one instance using its exact occurrence_key from calendar_query; series: edit the entire event/series."
            )
            properties["occurrence_key"]["description"] = (
                "Required for scope=occurrence. Copy exactly from calendar_query, without a UTC offset."
            )
        return result

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
        # The public gateway may reject setup with a REST-shaped error on the
        # WebSocket (no event type). Never echo provider messages or request data.
        if (not kind and data.get("code")) or kind == "error":
            error = data.get("error", data)
            code = error.get("code") if isinstance(error, dict) else None
            return [
                {
                    "type": "error",
                    "code": "VOICE_MODEL_ACCESS_DENIED"
                    if code == "AccessDenied.Unpurchased"
                    else "VOICE_PROVIDER_ERROR",
                }
            ]
        if kind == "session.updated":
            return [{"type": "ready"}]
        if kind == "input_audio_buffer.speech_started":
            return [
                {"type": "interrupted", "speech_started": True},
                {"type": "state", "state": "listening"},
            ]
        if kind == "input_audio_buffer.speech_stopped":
            return [
                {
                    "type": "state",
                    "state": "thinking",
                    "speech_ended": True,
                    "input_end_ms": data.get("audio_end_ms"),
                }
            ]
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
        self.finished_responses = set()
        self.pending_cancel = False
        self.mode = "voice"

    def mode_update(self, mode):
        self.mode = mode
        return {
            "type": "session.update",
            "session": {
                "modalities": ["text"] if mode == "text" else ["text", "audio"],
                "turn_detection": None
                if mode == "text"
                else {
                    "type": "semantic_vad_ec",
                    "threshold": 0.5,
                    "silence_duration_ms": 700,
                },
            },
        }

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
                "modalities": ["text"] if self.mode == "text" else ["text", "audio"],
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
                "turn_detection": None
                if self.mode == "text"
                else {
                    "type": "semantic_vad_ec",
                    "threshold": 0.5,
                    "silence_duration_ms": 700,
                },
                "video": {"input": {"representation_compact": "none"}},
                "enable_search": False,
                "tools": tools,
                "max_tokens": 1024,
                "temperature": 0.2,
                "presence_penalty": 0,
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
            failed = response.get("status") in {"failed", "incomplete"}
            if response.get("status") == "cancelled" and response_id:
                self.cancelled_responses.add(response_id)
            if response_id in self.finished_responses:
                return []
            if response_id:
                self.finished_responses.add(response_id)
            current = not self.active_response or self.active_response in {"pending", response_id}
            if current:
                if self.pending_cancel:
                    if response_id:
                        self.cancelled_responses.add(response_id)
                    self.pending_cancel = False
                self.active_response = None
                self.response_idle.set()
            result = []
            for item in [] if failed else response.get("output", []):
                if isinstance(item, dict) and item.get("type") == "function_call":
                    result.extend(
                        self.tool_event(
                            {"item": item, "response_id": response_id}, response_complete=True
                        )
                    )
            if (
                current
                and not failed
                and response_id not in self.cancelled_responses
                and not self.cancel_requested
            ):
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
            return (
                result
                + [{"type": "usage", "usage": safe}]
                + ([{"type": "error", "code": "VOICE_PROVIDER_RESPONSE_FAILED"}] if failed else [])
            )
        if (
            self.cancel_requested
            or data.get("response_id") in self.cancelled_responses
            or data.get("response_id") in self.finished_responses
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
            if self.mode != "text":
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
        self.turn_factory = VoiceTurns
        self.conversations = Conversations()

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
            "supports_images": self.config.provider == "qwen_omni",
            "supports_text": self.config.provider == "qwen_omni",
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
    ):
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
        tool_failures = {}
        grounding_retries = set()
        turns = self.turn_factory()
        allow_memory = principal["kind"] in {"owner", "agent"}
        revision, facts = memory_context(self.runtime, allow_memory)
        instructions += facts
        instructions += draft_context(self.runtime, principal["kind"] == "owner")
        conversation = None
        assistant_text = ""
        restored = False
        if isinstance(protocol, QwenOmniProtocol):
            protocol.mode = mode
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
            if mode not in {"text", "voice"} or (
                mode == "text" and not isinstance(protocol, QwenOmniProtocol)
            ):
                raise DomainError("VOICE_MESSAGE_NOT_ALLOWED", 422)
            instructions += task_context(self.runtime, principal, task_id)
            if isinstance(protocol, QwenOmniProtocol):
                conversation = self.conversations.open(
                    principal, revision, conversation_id, task_id=task_id
                )
            async with self.connector(
                endpoint,
                additional_headers=headers,
                open_timeout=12,
                close_timeout=2,
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
                    if not isinstance(protocol, QwenOmniProtocol):
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
                    current = voice_instructions(
                        self.runtime.persona.current()["body"],
                        language,
                        self.store.clock().astimezone(ZoneInfo(current_zone)).isoformat(),
                        current_zone,
                    )
                    current += current_facts + draft_context(
                        self.runtime, principal["kind"] == "owner"
                    )
                    current += task_context(self.runtime, principal, task_id)
                    ready.clear()
                    await send_provider(
                        {"type": "session.update", "session": {"instructions": current}}
                    )
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
                            value = message.get("text", "")
                            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 3000:
                                raise DomainError("INVALID_TEXT", 422)
                            if isinstance(protocol, QwenOmniProtocol) and (
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
                            protocol, QwenOmniProtocol
                        ):
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
                            assistant_text = ""
                            turns.finish("interrupted")
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
                        elif message.get("type") == "playback_started":
                            timing = turns.playback(message)
                            if timing:
                                await send_client(timing)
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
                    nonlocal last_activity, usage, restored, assistant_text
                    async for raw in provider:
                        data = json.loads(raw)
                        if not isinstance(data, dict):
                            raise DomainError("VOICE_PROVIDER_ERROR", 502)
                        for event in protocol.events(data):
                            kind = event["type"]
                            if kind == "ready":
                                if conversation and not restored:
                                    for item in conversation.replay():
                                        await send_provider(item)
                                    restored = True
                                ready.set()
                                self.state = "listening"
                                event = {
                                    **event,
                                    "mode": mode,
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
                                if isinstance(protocol, QwenOmniProtocol):
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
                                if event.get("role") == "user":
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
                                if isinstance(protocol, QwenOmniProtocol):
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
                                        protocol, QwenOmniProtocol
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
                    last_check = 0.0
                    while True:
                        await asyncio.sleep(0.05)
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
        )

    return router
