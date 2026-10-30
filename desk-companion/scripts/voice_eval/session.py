"""Bounded WebSocket experiments for Realtime and Live, not a production adapter.

Only synthetic audio and the explicitly supplied isolated fixture can be sent.
No automatic retries/reconnects, microphone, hosted tools or background calls.
"""

import asyncio
import base64
import json
import math
import time
import wave
from array import array
from pathlib import Path

import websockets

from .budget import token_cost

RATE = 24000
CHUNK = 2400  # 50 ms, mono PCM16; continuously paced, including Live silence.
BACKEND_MODEL = "gpt-6-luna"
MAX_SECONDS = 45
MAX_RESPONSES = 6
INSTRUCTIONS = (
    "You are Desk Companion. This test uses fictional data. Today is 2026-10-29, "
    "10:00 Asia/Hong_Kong (UTC+08:00). Tomorrow is 2026-10-30. "
    "Reply briefly in the user's language (Cantonese for Cantonese). "
    "Always query calendar_query for current meetings; do not guess dates or counts. "
    "Call memory_save_draft only when asked to remember a fact. A draft is not saved; "
    "the owner must approve on screen. No confirmation tool exists. Do not claim success. "
    "Give the useful answer in one or two short sentences, with times when requested."
)


def load_key(path):
    import os
    import stat

    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as file:
        info = os.fstat(file.fileno())
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 8192:
            raise ValueError("PRIVATE_KEY_FILE_REQUIRED")
        values = [
            line.partition("=")[2].strip().strip("\"'")
            for line in file
            if line.startswith("OPENAI_API_KEY=")
        ]
    if len(values) != 1 or not values[0].startswith("sk-"):
        raise ValueError("OPENAI_KEY_MISSING")
    return values[0]


def rms(pcm):
    values = array("h", pcm)
    return math.sqrt(sum(v * v for v in values) / max(1, len(values)))


def session_config(model, tools, language="auto"):
    preference = {
        "en": " The selected spoken language is English. Reply entirely in English.",
        "zh": " The selected spoken language is Mandarin Chinese. Reply entirely in Mandarin Chinese.",
        "yue": " The selected spoken language is Hong Kong Cantonese. Reply in colloquial Cantonese, not Mandarin.",
        "auto": "",
    }[language]
    if model == "gpt-live-1":
        return {
            "type": "session.start",
            "event_id": "start",
            "session": {
                "model": model,
                "store": False,
                "instructions": "You are Desk Companion. Speak briefly in the user's language. "
                "Delegate calendar and memory requests to your backend; only it knows those facts. "
                "Never say a pending draft has been saved. For memory requests, acknowledge only that "
                "you will prepare a draft, not that you have remembered or noted it. Wait for the backend "
                "result and clearly state when screen approval is still needed. "
                "Listen to corrections and stop when asked." + preference,
                "audio": {
                    "format": {"type": "audio/pcm", "rate": RATE},
                    "output": {"voice": "marin"},
                },
                "delegation": {
                    "type": "responses",
                    "responses": {
                        "model": BACKEND_MODEL,
                        "instructions": INSTRUCTIONS + preference,
                        "max_output_tokens": 768,
                        "tools": [{**t, "strict": False} for t in tools],
                        "parallel_tool_calls": False,
                        "tool_choice": "auto",
                    },
                },
            },
        }
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "instructions": INSTRUCTIONS + preference,
            "output_modalities": ["audio"],
            "max_output_tokens": 512,
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": RATE},
                    "turn_detection": {
                        "type": "server_vad",
                        "silence_duration_ms": 600,
                        "create_response": True,
                        "interrupt_response": True,
                    },
                },
                "output": {"format": {"type": "audio/pcm", "rate": RATE}, "voice": "marin"},
            },
            "tools": tools,
            "tool_choice": "auto",
        },
    }


class Session:
    def __init__(self, model, fixture, pcm, stop_pcm=None, *, language="auto"):
        self.model, self.fixture, self.pcm, self.stop_pcm = model, fixture, pcm, stop_pcm
        self.live = model == "gpt-live-1"
        self.language = language
        self.started = time.monotonic()
        self.ready = asyncio.Event()
        self.finished = asyncio.Event()
        self.closed = asyncio.Event()
        self.send_lock = asyncio.Lock()
        self.events, self.usage, self.audio, self.transcripts = [], {}, [], []
        self.responses, self.completed = set(), set()
        self.pending_calls, self.handled_calls = {}, set()
        self.delegated_responses = {}
        self.last_voice = self.first_voice = self.input_end = self.interrupt_at = None
        self.last_input_end = None
        self.first_tool = None
        self.last_backend_done = 0
        self.backend_text_events = []
        self.voice_seconds = 0
        self.errors = []
        self.end_reason = "not_started"
        self.sending = False
        self.finalized = False

    def stamp(self):
        return round(time.monotonic() - self.started, 4)

    def can_finish(self, now):
        if not self.input_end or not self.last_voice or not self.transcripts:
            return False
        if self.responses - self.completed or self.pending_calls:
            return False
        if self.stop_pcm is not None and (
            not self.last_input_end or now - self.last_input_end <= 2
        ):
            return False
        if self.live:
            # A backend result can arrive before Live starts saying it. An
            # acknowledgment followed by silence is not a finished answer.
            last_activity = max(self.last_voice, self.transcripts[-1]["at"], self.last_backend_done)
            return self.last_voice > self.last_backend_done and now - last_activity > 3
        return now - self.last_voice > 1.5

    async def send(self, ws, event):
        async with self.send_lock:
            await ws.send(json.dumps(event, ensure_ascii=False))

    async def input_stream(self, ws):
        await self.ready.wait()
        self.sending = True
        source, offset = self.pcm, 0
        target = time.monotonic()
        while not self.finished.is_set():
            if (
                self.stop_pcm is not None
                and self.first_voice is not None
                and self.stamp() > self.first_voice + 0.8
                and self.interrupt_at is None
            ):
                source, offset = self.stop_pcm, 0
                self.interrupt_at = self.stamp()
                self.events.append({"type": "fixture.interruption", "at": self.interrupt_at})
            block = source[offset : offset + CHUNK]
            offset += len(block)
            if not block:
                if self.input_end is None:
                    self.input_end = self.stamp()
                    self.events.append({"type": "fixture.input_end", "at": self.input_end})
                if self.interrupt_at is not None and self.last_input_end is None:
                    self.last_input_end = self.stamp()
                block = bytes(CHUNK)
            else:
                block = block.ljust(CHUNK, b"\0")
            await self.send(
                ws,
                {
                    "type": "session.input_audio.append"
                    if self.live
                    else "input_audio_buffer.append",
                    "audio": base64.b64encode(block).decode(),
                },
            )
            target += 0.05
            await asyncio.sleep(max(0, target - time.monotonic()))
            if self.stamp() > MAX_SECONDS:
                self.end_reason = "session_deadline"
                self.finished.set()
                break
            if self.can_finish(self.stamp()):
                self.end_reason = "quiet_after_reply"
                self.finished.set()
        self.sending = False

    async def return_calls(self, ws, response_id):
        calls = self.pending_calls.pop(response_id, [])
        for item in calls:
            call_id = item["call_id"]
            if call_id in self.handled_calls:
                continue
            self.handled_calls.add(call_id)
            self.first_tool = self.first_tool or self.stamp()
            result = await asyncio.to_thread(
                self.fixture.call, call_id, item["name"], item["arguments"]
            )
            self.events.append(
                {
                    "type": "fixture.tool_result",
                    "name": item["name"],
                    "at": self.stamp(),
                    "saved": result.get("saved", False),
                }
            )
            body = json.dumps(result, ensure_ascii=False)
            if len(body.encode()) > 8000:
                raise ValueError("TOOL_RESULT_LIMIT")
            await self.send(
                ws,
                {
                    "type": "response.item.create" if self.live else "conversation.item.create",
                    "item": {"type": "function_call_output", "call_id": call_id, "output": body},
                },
            )
        if calls and len(self.responses) < MAX_RESPONSES:
            await self.send(ws, {"type": "response.create"})

    async def receive(self, ws):
        async for raw in ws:
            event = json.loads(raw)
            kind = event.get("type", "")
            at = self.stamp()
            if kind in {"response.output_audio.delta", "session.output_audio.delta"}:
                pcm = base64.b64decode(event["delta"])
                self.audio.append(pcm)
                if rms(pcm) > 100:
                    self.first_voice = self.first_voice if self.first_voice is not None else at
                    self.last_voice = at
                continue
            if kind in {
                "response.output_audio_transcript.delta",
                "session.output_transcript.delta",
            }:
                self.transcripts.append(
                    {
                        "at": at,
                        "text": event["delta"],
                        "response_id": event.get("response_id"),
                        "start_ms": event.get("start_ms"),
                        "end_ms": event.get("end_ms"),
                    }
                )
                continue
            if kind == "session.input_transcript.delta":
                self.events.append({"type": kind, "at": at, "text": event["delta"]})
                continue
            delegation_id = event.get("delegation_id")
            if kind == "response.event":
                event = event["event"]
                kind = event.get("type", "")
                if kind == "response.output_text.delta":
                    self.backend_text_events.append({"at": at, "text": event["delta"]})
            if kind == "error":
                self.errors.append(
                    {k: event.get("error", {}).get(k) for k in ("type", "code", "message", "param")}
                )
                self.end_reason = "provider_error"
                self.finished.set()
                continue
            if kind in {"session.updated", "session.started"}:
                self.events.append({"type": kind, "at": at})
                self.ready.set()
            if kind == "session.usage.updated":
                self.voice_seconds = max(
                    self.voice_seconds, event.get("usage", {}).get("seconds", 0)
                )
            if kind == "session.closed":
                self.voice_seconds = event.get("usage", {}).get("seconds", self.voice_seconds)
                self.finalized = True
                self.closed.set()
                self.events.append(
                    {
                        "type": kind,
                        "at": at,
                        "reason": event.get("reason"),
                        "usage": event.get("usage"),
                    }
                )
                return
            if kind == "response.created":
                rid = event["response"]["id"]
                self.responses.add(rid)
                if delegation_id:
                    self.delegated_responses[delegation_id] = rid
                self.events.append({"type": kind, "at": at, "id": rid})
                if len(self.responses) > MAX_RESPONSES:
                    self.end_reason = "response_limit"
                    self.finished.set()
            if (
                kind == "response.output_item.done"
                and event.get("item", {}).get("type") == "function_call"
            ):
                rid = event.get("response_id") or self.delegated_responses[delegation_id]
                self.pending_calls.setdefault(rid, []).append(event["item"])
            if kind in {
                "response.done",
                "response.completed",
                "response.failed",
                "response.incomplete",
                "response.cancelled",
            }:
                response = event["response"]
                rid = response["id"]
                self.completed.add(rid)
                self.last_backend_done = at
                if response.get("usage") is not None:
                    self.usage[rid] = response["usage"]
                self.events.append(
                    {
                        "type": kind,
                        "at": at,
                        "id": rid,
                        "status": response.get("status"),
                        "status_details": response.get("status_details"),
                    }
                )
                await self.return_calls(ws, rid)
            if kind.startswith("input_audio_buffer.speech") or kind == "session.delegation.created":
                self.events.append({"type": kind, "at": at})

    async def run(self, key):
        endpoint = (
            "wss://api.openai.com/v1/live/sessions"
            if self.live
            else "wss://api.openai.com/v1/realtime?model=" + self.model
        )
        try:
            async with websockets.connect(
                endpoint,
                additional_headers={"Authorization": "Bearer " + key},
                open_timeout=10,
                close_timeout=3,
                max_size=4 * 1024 * 1024,
            ) as ws:
                receiver = asyncio.create_task(self.receive(ws))
                sender = asyncio.create_task(self.input_stream(ws))
                try:
                    await self.send(
                        ws, session_config(self.model, self.fixture.tools, self.language)
                    )
                    await asyncio.wait_for(self.finished.wait(), MAX_SECONDS + 12)
                except TimeoutError:
                    self.end_reason = "outer_deadline"
                finally:
                    self.finished.set()
                    sender.cancel()
                    await asyncio.gather(sender, return_exceptions=True)
                    if self.live and self.ready.is_set() and not receiver.done():
                        await self.send(ws, {"type": "session.close"})
                        try:
                            await asyncio.wait_for(self.closed.wait(), 5)
                        except TimeoutError:
                            pass
                    await ws.close()
                    receiver.cancel()
                    outcomes = await asyncio.gather(receiver, return_exceptions=True)
                    for error in outcomes:
                        if isinstance(error, Exception) and not isinstance(
                            error, websockets.ConnectionClosedOK
                        ):
                            self.errors.append(
                                {
                                    "type": type(error).__name__,
                                    "message": str(error).replace(key, "[REDACTED]")[:300],
                                }
                            )
        except Exception as error:
            self.end_reason = "connection_error"
            self.errors.append(
                {
                    "type": type(error).__name__,
                    "message": str(error).replace(key, "[REDACTED]")[:300],
                }
            )
        backend = sum(
            token_cost(BACKEND_MODEL if self.live else self.model, u) for u in self.usage.values()
        )
        accounted = self.responses <= self.usage.keys()
        finalized = (
            self.finalized and accounted if self.live else bool(self.responses) and accounted
        )
        return {
            "model": self.model,
            "backend_model": BACKEND_MODEL if self.live else None,
            "language_mode": self.language,
            "harness_protocol": "v3-live-memory-ack",
            "ready": self.ready.is_set(),
            "end_reason": self.end_reason,
            "errors": self.errors,
            "elapsed_s": self.stamp(),
            "input_end_s": self.input_end,
            "first_non_silent_output_s": self.first_voice,
            "first_audio_after_input_s": None
            if self.input_end is None or self.first_voice is None
            else round(self.first_voice - self.input_end, 4),
            "interrupt_at_s": self.interrupt_at,
            "voice_usage_seconds": self.voice_seconds,
            "provider_usage": self.usage,
            "usage_finalized": finalized,
            "estimated_uncached_usd": backend + self.voice_seconds * 0.05 / 60,
            "transcript": "".join(t["text"] for t in self.transcripts),
            "transcript_events": self.transcripts,
            "events": self.events,
            "backend_text_events": self.backend_text_events,
            "business_evidence": self.fixture.evidence(),
            "measurement": "Paced synthetic PCM, network-received audio above RMS100; not DAC playback or human-use latency.",
        }

    def save_audio(self, path):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(b"".join(self.audio))
