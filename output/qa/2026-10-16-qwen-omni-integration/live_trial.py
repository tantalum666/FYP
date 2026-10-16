"""Bounded live production VoiceService trial with synthetic audio and an isolated calendar."""

import asyncio
import base64
import json
import sys
import tempfile
import time
import wave
from array import array
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desk-companion/backend"))
import websockets
from desk.app import create_app
from desk.schemas import CreateEvents, EventInput
from desk.store import DomainError
from desk.voice import QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, QwenOmniProtocol, VoiceConfig
from desk.voice_credentials import qwen_key

QA = Path(__file__).parent
from trial_budget import reserve
MEETINGS = [
    ("Planning sync", "2026-10-19T10:00", "2026-10-19T10:30"),
    ("Design review", "2026-10-21T15:00", "2026-10-21T16:00"),
    ("Demo rehearsal", "2026-10-23T11:00", "2026-10-23T12:00"),
]


class TrialSocket:
    def __init__(self):
        self.incoming, self.outgoing = asyncio.Queue(), asyncio.Queue()

    async def iter_text(self):
        while True:
            yield json.dumps(await self.incoming.get())

    async def send_json(self, value):
        await self.outgoing.put(value)

    async def close(self):
        pass


async def main():
    mode = "vision" if "--vision" in sys.argv else "calendar"
    attempt = reserve(mode + "_voice")
    result = {"authorization_cny": 5, "inputs": "synthetic speech and fictional calendar only", "real_mic_or_screen_capture": False, "model": QWEN_OMNI_MODEL, "live_requests_in_this_trial": 1, "tool_queries": [], "wire_events": [], "usage": {}, "response_limit": 4, "wall_timeout_seconds": 45}
    key = qwen_key(str(Path.home() / ".config/desk-companion/qwen.env"))
    with wave.open(str(QA / ("vision-request.wav" if mode == "vision" else "calendar-request.wav")), "rb") as file:
        assert (file.getframerate(), file.getnchannels(), file.getsampwidth()) == (16000, 1, 2)
        pcm = file.readframes(file.getnframes())
    samples = array("h", pcm)
    last_signal = max(i for i, sample in enumerate(samples) if abs(sample) > 128) / 16000
    pcm += b"\x00" * 32000 * 2
    result["synthetic_audio_seconds"] = round(len(pcm) / 32000, 3)
    grounded_sent = [None]
    usage_parser = QwenOmniProtocol()
    audio = bytearray()
    transcript = []
    started = time.monotonic()
    send_started = [None]

    with tempfile.TemporaryDirectory(prefix="fyp-qwen-live-fixture-") as directory:
        app = create_app(Path(directory), password="fixture-only", scheduler=False, clock=lambda: datetime(2026, 10, 16, 4, tzinfo=UTC))
        runtime = app.state.runtime
        for index, (title, start, end) in enumerate(MEETINGS):
            runtime.store.create(CreateEvents(event=EventInput(title=title, start_local=start, end_local=end, timezone="Asia/Hong_Kong")), f"seed-{index}")
        original_tool = runtime.assistant.tool

        def read_only_tool(name, arguments, *args, **kwargs):
            if name != "calendar_query":
                raise DomainError("TRIAL_READ_ONLY", 403)
            value = original_tool(name, arguments, *args, **kwargs)
            result["tool_queries"].append({"arguments": arguments, "returned_titles": [o.get("title") for o in value.get("occurrences", [])]})
            return value

        runtime.assistant.tool = read_only_tool
        runtime.voice.config = VoiceConfig("qwen_omni", QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, key)

        class Wire:
            def __init__(self, provider):
                self.provider = provider

            def __aiter__(self):
                return self

            async def __anext__(self):
                raw = await self.provider.recv()
                event = json.loads(raw)
                kind = event.get("type", "unknown")
                if kind not in {"response.audio.delta", "response.audio_transcript.delta"}:
                    result["wire_events"].append(kind)
                if kind == "error":
                    error = event.get("error", {})
                    result["provider_error"] = str(error.get("code", error.get("type", "error"))).replace(key, "[redacted]")[:100]
                    result["provider_param"] = str(error.get("param", "")).replace(key, "[redacted]")[:100]
                if kind in {"response.function_call_arguments.done", "response.output_item.added", "response.output_item.done"}:
                    item = event.get("item", {})
                    if kind == "response.function_call_arguments.done" or item.get("type") == "function_call":
                        result.setdefault("function_envelopes", []).append({
                            "type": kind,
                            "fields": list(event),
                            "metadata": {k: event.get(k) for k in ("call_id", "name", "item_id", "response_id")},
                            "item_metadata": {k: item.get(k) for k in ("id", "call_id", "name", "type")},
                        })
                if kind == "response.done":
                    result.setdefault("done_shapes", []).append({"fields": list(event), "response_fields": list(event.get("response", {})), "usage_fields": list((event.get("response", {}).get("usage") or event.get("usage") or {}))})
                    for normalized in usage_parser.events(event):
                        if normalized["type"] == "usage":
                            for name, value in normalized["usage"].items():
                                result["usage"][name] = result["usage"].get(name, 0) + value
                    if result["wire_events"].count("response.done") > 4:
                        raise DomainError("TRIAL_RESPONSE_LIMIT", 429)
                return raw

            async def send(self, raw):
                event = json.loads(raw)
                if event.get("type") == "session.update":
                    event["session"]["tools"] = [] if mode == "vision" else [t for t in event["session"]["tools"] if t["function"]["name"] == "calendar_query"]
                    event["session"]["max_tokens"] = 512
                    # Worst-case planning reserve: byte-count token upper estimate,
                    # image-free audio and four responses at the highest model rate.
                    reserve = ((len(json.dumps(event).encode()) + 12000) * 4 + 4 * 512) * 12 / 1_000_000
                    result["conservative_trial_reserve_cny"] = round(reserve, 6)
                    assert reserve <= 1, "Trial would exceed its allocated reserve"
                    raw = json.dumps(event)
                await self.provider.send(raw)
                if event.get("type") == "conversation.item.create" and event.get("item", {}).get("type") == "function_call_output":
                    grounded_sent[0] = time.monotonic()

        @asynccontextmanager
        async def connector(*args, **kwargs):
            kwargs["close_timeout"] = 3
            async with websockets.connect(*args, **kwargs) as provider:
                yield Wire(provider)

        runtime.voice.connector = connector
        principal = {"kind": "owner", "session": runtime.store.authenticate("owner", "fixture-only")}
        ticket = runtime.voice.ticket(principal)["ticket"]
        principal = runtime.voice.consume(ticket)
        socket = TrialSocket()
        task = asyncio.create_task(runtime.voice.run(socket, principal, "en"))
        feeder = None

        async def feed():
            send_started[0] = time.monotonic()
            for offset in range(0, len(pcm), 1280):
                await socket.incoming.put({"type": "audio", "audio": base64.b64encode(pcm[offset:offset + 1280]).decode()})
                if mode == "vision" and offset == 0:
                    image = base64.b64encode((ROOT / "desk-companion/tests/fixtures/qwen-vision.jpg").read_bytes()).decode()
                    await socket.incoming.put({"type": "vision_start"})
                    await socket.incoming.put({"type": "image", "image": image})
                    grounded_sent[0] = time.monotonic()
                await asyncio.sleep(max(0, send_started[0] + (offset + 1280) / 32000 - time.monotonic()))

        try:
            async with asyncio.timeout(45):
                while True:
                    event = await socket.outgoing.get()
                    kind = event["type"]
                    if kind == "ready":
                        result["ready_seconds"] = round(time.monotonic() - started, 3)
                        feeder = asyncio.create_task(feed())
                    elif kind == "transcript":
                        if event.get("role") == "user":
                            result["recognized_request"] = event.get("text", "")
                        elif event.get("final"):
                            transcript = [event.get("text", "")]
                        else:
                            transcript.append(event.get("text", ""))
                    elif kind == "image_sent":
                        result["image_frames_accepted"] = event["count"]
                    elif kind == "audio":
                        if grounded_sent[0] and "grounded_audio_received_seconds" not in result:
                            result["grounded_audio_received_seconds"] = round(time.monotonic() - (send_started[0] + last_signal), 3)
                        audio.extend(base64.b64decode(event["audio"]))
                        if len(audio) > 2_000_000:
                            raise DomainError("TRIAL_OUTPUT_LIMIT", 429)
                    elif kind == "turn_complete" and grounded_sent[0] and audio:
                        result["grounded_answer_completed"] = True
                        break
                    elif kind in {"error", "ended"}:
                        result["client_error"] = event.get("code", event.get("reason", kind))
                        break
        except Exception as error:
            result["failure_class"] = type(error).__name__
        finally:
            if feeder:
                feeder.cancel()
                await asyncio.gather(feeder, return_exceptions=True)
            await socket.incoming.put({"type": "stop"})
            try:
                await asyncio.wait_for(task, 8)
            except (TimeoutError, Exception):
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    result["answer_transcript"] = "".join(transcript).replace(key, "[redacted]")
    result["audio_bytes_received"] = len(audio)
    result["expected_titles"] = [m[0] for m in MEETINGS]
    result["all_meetings_mentioned"] = all(title.lower() in result["answer_transcript"].lower() for title in result["expected_titles"])
    result["conservative_usage_estimate_cny"] = round(result["usage"]["total_tokens"] * 12 / 1_000_000, 6) if "total_tokens" in result["usage"] else None
    result["billing_confirmed"] = False
    result["latency_scope"] = "Synthetic last non-silent sample to grounded audio receipt; no browser playback or Pi measurement"
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    if audio:
        with wave.open(str(QA / f"qwen-{mode}-answer.wav"), "wb") as file:
            file.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            file.writeframes(audio)
    key = ""
    result["trial_mode"] = mode
    result["budget_request_number"] = attempt
    if mode == "vision":
        result["vision_answer_correct"] = "blue" in result["answer_transcript"].lower()
        result["inputs"] = "Synthetic speech and one generated blue JPEG; no calendar data requested"
    (QA / f"live-{mode}-trial.json").write_text(json.dumps(result, indent=2) + "\n")
    (QA / f"live-{mode}-attempt{attempt}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
