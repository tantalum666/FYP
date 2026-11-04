"""Provider wire formats and shared realtime response lifecycle; no transport or authority."""

import asyncio
import hashlib
import json

from .assistant import TOOLS
from .tool_policy import tool_visible


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


class RealtimeEvents:
    def __init__(self):
        self.input_sequence = 0

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
            transcript = data.get("transcript", "")
            if not isinstance(transcript, str):
                return []
            try:
                transcript.encode("utf-8")
            except UnicodeEncodeError:
                return []
            self.input_sequence += 1
            return [
                {
                    "type": "transcript",
                    "role": "user",
                    "text": data.get("transcript", ""),
                    "final": True,
                    "input_operation": "replace",
                    "boundary": "provider_final",
                    "input_sequence": self.input_sequence,
                    "input_key": str(
                        data.get("item_id")
                        or hashlib.sha256(str(data.get("transcript", "")).encode()).hexdigest()
                    ),
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


class RealtimeProtocol(RealtimeEvents):
    """Shared response, cancellation, grouped-tool and usage lifecycle."""

    def __init__(self):
        super().__init__()
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

    def instructions_update(self, instructions):
        return {"type": "session.update", "session": {"instructions": instructions}}

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


class QwenAudioProtocol(RealtimeEvents):
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
                if tool_visible(tool["name"], allow_memory)
            ],
        }
        if config.voice:
            session["voice"] = config.voice
        return {"type": "session.update", "session": session}


class QwenOmniProtocol(RealtimeProtocol):
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

    def setup(self, config, instructions, *, allow_memory=True):
        tools = QwenAudioProtocol.setup(self, config, instructions, allow_memory=allow_memory)[
            "session"
        ]["tools"]
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


class GeminiProtocol:
    def __init__(self):
        self.input_sequence = 0
        self.input_group = 0

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
            if tool_visible(t["name"], allow_memory)
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
            self.input_group += 1
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
                if role == "user":
                    self.input_sequence += 1
                out.append(
                    {
                        "type": "transcript",
                        "role": role,
                        "text": content[field]["text"],
                        "final": False,
                        **(
                            {
                                "input_operation": "append",
                                "boundary": "unfinalized",
                                "input_key": "gemini-" + str(self.input_group),
                                "input_sequence": self.input_sequence,
                            }
                            if role == "user"
                            else {}
                        ),
                    }
                )
        if content.get("turnComplete"):
            # This closes a local grouping, never proves final user speech.
            self.input_group += 1
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
