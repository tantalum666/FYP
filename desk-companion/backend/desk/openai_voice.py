"""OpenAI GA Realtime wire adapter; business authority stays in VoiceService."""

import base64
import copy
from array import array
import sys

from .assistant import TOOLS
from .tool_policy import tool_visible
from .voice_protocols import RealtimeProtocol, flatten_schema

OPENAI_REALTIME_ENDPOINT = "wss://api.openai.com/v1/realtime"
OPENAI_REALTIME_MODELS = {"gpt-realtime-2.1-mini", "gpt-realtime-2.1"}


class PCM16To24:
    """Streaming 16-to-24 kHz interpolation, preserving boundary phase/sample.

    Browser and existing local workers keep their public16k contract. Only the
    provider adapter changes wire rate; chunking cannot lose boundary samples.
    """

    def __init__(self):
        self.last = None
        self.offset = 0
        self.next_third = 0

    def convert(self, pcm):
        samples = array("h")
        samples.frombytes(pcm)
        if sys.byteorder != "little":
            samples.byteswap()
        if not samples:
            return b""
        if self.last is not None:
            samples.insert(0, self.last)
        out = array("h")
        while True:
            index, fraction = divmod(self.next_third, 3)
            local = index - self.offset
            if local >= len(samples) or (fraction and local + 1 >= len(samples)):
                break
            value = samples[local]
            if fraction:
                value = round((value * (3 - fraction) + samples[local + 1] * fraction) / 3)
            out.append(value)
            self.next_third += 2
        self.offset += len(samples) - 1
        self.last = samples[-1]
        if sys.byteorder != "little":
            out.byteswap()
        return out.tobytes()


class OpenAIRealtimeProtocol(RealtimeProtocol):
    def __init__(self):
        super().__init__()
        self.resampler = PCM16To24()
        self.language = "en"

    def _turn_detection(self):
        return (
            None
            if self.mode == "text"
            else {
                "type": "server_vad",
                "threshold": 0.6,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 700,
                "create_response": True,
                "interrupt_response": False,
            }
        )

    def setup(self, config, instructions, *, allow_memory=True):
        return {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": config.model,
                "instructions": instructions
                + "\nFor simple factual queries, answer only the requested facts in one short spoken sentence. Omit introductions, unrequested end times, offers and sign-offs. For relative dates such as today, tomorrow, or next week, first call owner_clock and use its date/timezone, not the model default date. calendar_query requires only start and end, both ISO8601 datetimes WITH UTC offset (for example +08:00) or Z. Do not pass a separate timezone key. Read meeting start times from start_local, never end_local; copy and double-check the exact hour and minute. The end is exclusive: for one day query its midnight through the next midnight.",
                "output_modalities": ["text"] if self.mode == "text" else ["audio"],
                "max_output_tokens": 1024,
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "transcription": {
                            "model": "gpt-4o-mini-transcribe",
                            "language": self.language,
                        },
                        "turn_detection": self._turn_detection(),
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "voice": config.voice or "marin",
                    },
                },
                "tools": [
                    {"type": "function", **tool, "parameters": flatten_schema(tool["parameters"])}
                    for tool in TOOLS
                    if tool_visible(tool["name"], allow_memory)
                ],
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "truncation": {
                    "type": "retention_ratio",
                    "retention_ratio": 0.8,
                    "token_limits": {"post_instructions": 4096},
                },
            },
        }

    def mode_update(self, mode):
        self.mode = mode
        self.resampler = PCM16To24()
        return {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "output_modalities": ["text"] if mode == "text" else ["audio"],
                "audio": {"input": {"turn_detection": self._turn_detection()}},
            },
        }

    def instructions_update(self, instructions):
        return {
            "type": "session.update",
            "session": {"type": "realtime", "instructions": instructions},
        }

    def audio(self, value):
        raw = self.resampler.convert(base64.b64decode(value, validate=True))
        return {"type": "input_audio_buffer.append", "audio": base64.b64encode(raw).decode()}

    def image(self, value):
        return {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": "data:image/jpeg;base64," + value}
                ],
            },
        }

    def events(self, incoming):
        data = copy.deepcopy(incoming)
        aliases = {
            "response.output_audio_transcript.delta": "response.audio_transcript.delta",
            "response.output_audio_transcript.done": "response.audio_transcript.done",
            "response.output_text.delta": "response.text.delta",
            "response.output_text.done": "response.text.done",
        }
        data["type"] = aliases.get(data.get("type"), data.get("type"))
        if data["type"] == "session.updated":
            audio = data.get("session", {}).get("audio", {})
            fmt = audio.get("output", {}).get("format", {})
            if fmt.get("type", "audio/pcm") != "audio/pcm" or fmt.get("rate", 24000) != 24000:
                return [{"type": "error", "code": "VOICE_AUDIO_FORMAT_UNSUPPORTED"}]
            audio.setdefault("output", {})["format"] = {"type": "pcm", "sample_rate": 24000}
        if data["type"] == "response.done":
            usage = data.get("response", {}).get("usage", {})
            for direction in ("input", "output"):
                usage[direction + "_tokens_details"] = usage.get(direction + "_token_details", {})
        return super().events(data)
