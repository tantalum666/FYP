#!/usr/bin/env python3
"""Explicit USD1 /45s synthetic wake -> production GPT-Live acceptance.

No microphone, personal store, hosted tools, physical output or automatic retry.
Received audio is evidence of generated speech, not physical playback latency.
"""

import argparse
import asyncio
from array import array
import base64
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desk.app import create_app
from desk.agents.wake import WakeDetector
from desk.openai_live import OpenAILiveProtocol, OPENAI_LIVE_ENDPOINT
from desk.schemas import CreateEvents, EventInput
from desk.style import render_prompt
from desk.voice import VoiceConfig
from desk.voice_credentials import openai_key
from desk.voice_turns import VoiceTurns
from scripts.voice_eval.budget import Budget
import desk.voice as voice_module

ALLOWED = {"owner_clock", "calendar_query"}
RESERVE = 0.95


def pcm_file(path, text):
    subprocess.run(
        [
            "/usr/bin/say",
            "-v",
            "Samantha",
            "--file-format=WAVE",
            "--data-format=LEI16@16000",
            "-o",
            str(path),
            text,
        ],
        check=True,
        capture_output=True,
    )
    with wave.open(str(path), "rb") as file:
        assert (file.getnchannels(), file.getsampwidth(), file.getframerate()) == (1, 2, 16000)
        pcm = file.readframes(file.getnframes())
    assert len(pcm) <= 20 * 32000
    return pcm


def estimated(usage):
    return (
        usage.get("voice_seconds", 0) * 0.05 / 60
        + usage.get("backend_input_tokens", 0) * 5 / 1e6
        + usage.get("backend_output_tokens", 0) * 10 / 1e6
    ) * 1.1


async def evaluate(args, report, budget):
    speech = pcm_file(
        report / "request.wav",
        "What is your name? Please check how many meetings I have today and tell me their start times.",
    )
    wake_audio = pcm_file(report / "wake.wav", "Hey Alice")
    detector = WakeDetector(args.wake_models, phrase="alice")
    samples = [x / 32768 for x in array("h", wake_audio)] + [0.0] * 16000
    detected = any(detector.accept(samples[i : i + 800]) for i in range(0, len(samples), 800))
    if not detected:
        raise ValueError("Local wake did not trigger; no provider request made")
    runtime = create_app(
        report / "runtime",
        clock=lambda: datetime(2026, 11, 7, 2, tzinfo=UTC),
        password="synthetic-acceptance",
        scheduler=False,
    ).state.runtime
    for i, (start, end) in enumerate([("10:30", "11:00"), ("14:00", "14:30")]):
        runtime.store.create(
            CreateEvents(
                event=EventInput(
                    title=f"FYP synthetic meeting {i + 1}",
                    start_local=f"2026-11-07T{start}",
                    end_local=f"2026-11-07T{end}",
                    timezone="Asia/Hong_Kong",
                    reminder_minutes=[],
                )
            ),
            f"seed-{i}",
        )
    captured = {}

    class CheckedLive(OpenAILiveProtocol):
        def __init__(self):
            super().__init__()
            captured["protocol"] = self
            self.reads = []

        def setup(self, cfg, instructions, **kwargs):
            message = super().setup(cfg, instructions, **kwargs)
            backend = message["session"]["delegation"]["responses"]
            backend["tools"] = [tool for tool in backend["tools"] if tool["name"] in ALLOWED]
            backend["max_output_tokens"] = 512
            # UTF8 bytes upper-bound ordinary text tokens. Additional slack covers
            # bounded synthetic speech and up to three 4KiB tool results.
            bound = len(json.dumps(message).encode()) + 8192 + 3 * 4096
            quote = (4 * bound * 5 / 1e6 + 4 * 512 * 10 / 1e6 + 45 * 0.05 / 60) * 1.1
            if quote > RESERVE:
                raise ValueError("Conservative request bound exceeds reservation")
            captured["input_bound"], captured["quote"] = bound, quote
            return message

        def events(self, event):
            result = super().events(event)
            if len(self.started_responses) > 3 or estimated(self.usage_snapshot()) > 0.70:
                return [{"type": "error", "code": "EVALUATION_LIMIT"}]
            if any(x["type"] == "tool" and x["name"] not in ALLOWED for x in result):
                return [{"type": "error", "code": "EVALUATION_TOOL_DENIED"}]
            return result

        def result(self, call, value):
            if len(json.dumps(value).encode()) > 4096:
                raise ValueError("Tool result limit")
            self.reads.append({"name": call["name"], "result": value})
            return super().result(call, value)

    cfg = VoiceConfig(
        "openai_live",
        OPENAI_LIVE_ENDPOINT,
        "gpt-live-1",
        openai_key(args.credentials),
        "marin",
        proxy_url=args.proxy,
    )
    assert cfg.valid()
    runtime.voice.config = cfg
    # This is a receive-only evaluation client, not a physical speaker. Do not
    # fabricate a playback acknowledgment to satisfy the ordinary 10s SLO.
    runtime.voice.turn_factory = lambda: VoiceTurns(cutoff=45)
    voice_module.OpenAILiveProtocol = CheckedLive
    # Validate the request bound before reserving or opening a Live connection.
    preview = CheckedLive()
    preview.setup(
        cfg,
        render_prompt(
            runtime.persona.current()["body"],
            runtime.data.preferences(),
            "en",
            channel="voice",
            now_iso="2026-11-07T10:00:00+08:00",
            zone="Asia/Hong_Kong",
        ),
    )
    if args.prepare_only:
        return {
            "preflight_only": True,
            "local_wake_detected": detected,
            "quote_usd": captured["quote"],
            "input_byte_bound": captured["input_bound"],
            "model_calls": 0,
        }
    budget.reserve("live-identity-calendar", "gpt-live-1", RESERVE)
    ready, stop = asyncio.Event(), asyncio.Event()
    started = time.monotonic()

    class Receiver:
        def __init__(self):
            self.events, self.audio, self.text = [], [], []

        async def send_json(self, event):
            at = round(time.monotonic() - started, 3)
            if event["type"] == "ready":
                ready.set()
            if event["type"] == "audio":
                self.audio.append(base64.b64decode(event["audio"], validate=True))
                self.events.append({"type": "received_audio", "at": at})
            else:
                self.events.append({**event, "at": at})
            if event["type"] == "transcript" and event.get("role") == "assistant":
                self.text.append(event.get("text", ""))
            if event["type"] == "turn_complete":
                text = "".join(self.text).lower()
                if (
                    "alice" in text
                    and ("two" in text or "2" in text)
                    and captured["protocol"].reads
                ):
                    stop.set()
            if event["type"] in {"error", "ended"}:
                stop.set()

        async def iter_text(self):
            await ready.wait()
            source = bytes(16000) + speech
            offset = 0
            boundary = False
            target = time.monotonic()
            while time.monotonic() - started < 37 and not stop.is_set():
                block = source[offset : offset + 1600]
                offset += len(block)
                if not block:
                    if not boundary:
                        boundary = True
                        yield json.dumps({"type": "input_ended", "input_end_ms": len(source) / 32})
                    block = bytes(1600)
                yield json.dumps(
                    {"type": "audio", "audio": base64.b64encode(block.ljust(1600, b"\0")).decode()}
                )
                target += 0.05
                await asyncio.sleep(max(0, target - time.monotonic()))
            yield json.dumps({"type": "stop"})

        async def close(self):
            stop.set()

    receiver = Receiver()
    owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
    principal = runtime.voice.consume(runtime.voice.ticket(owner)["ticket"])
    failure = None
    try:
        await asyncio.wait_for(
            runtime.voice.run(receiver, principal, "en", wake_triggered=True), timeout=42
        )
    except Exception as error:
        failure = type(error).__name__
    protocol = captured["protocol"]
    usage = protocol.usage_snapshot()
    text = "".join(receiver.text)
    reads = [x for x in protocol.reads if x["name"] == "calendar_query"]
    with runtime.store.connection() as db:
        events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        proposals = db.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0]
    result = {
        "local_wake_detected": detected,
        "speech_transcript": text,
        "usage": usage,
        "backend_requests": len(protocol.started_responses),
        "completed_backend_requests": len(protocol.finished_responses),
        "tool_reads": protocol.reads,
        "events": receiver.events,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "failure_type": failure,
        "checks": {
            "alice_identity": "alice" in text.lower(),
            "two_meetings_spoken": "two" in text.lower() or "2" in text,
            "calendar_read": bool(reads) and len(reads[-1]["result"].get("occurrences", [])) == 2,
            "received_audio": bool(receiver.audio),
            "no_calendar_write": events == 2 and proposals == 0,
            "finalized": protocol.finalized.is_set(),
            "slot_released": not runtime.voice.active,
        },
        "quote_usd": captured["quote"],
        "billing_note": "Conservative duration/token estimate; not a provider invoice. No physical speaker claim.",
    }
    if receiver.audio:
        with wave.open(str(report / "received.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(b"".join(receiver.audio))
    finalized = bool(
        usage.get("finalization_confirmed") and usage.get("backend_receipts_complete")
    ) and protocol.started_responses.issubset(protocol.finished_responses)
    budget.finish(
        "live-identity-calendar",
        estimate=estimated(usage),
        finalized=finalized,
        result={"checks": result["checks"], "usage": usage},
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--wake-models", type=Path, required=True)
    parser.add_argument("--proxy", default="")
    args = parser.parse_args()
    if not (args.run_live or args.prepare_only) or args.report.exists():
        parser.error("Explicit live flag and a fresh report/ledger required")
    os.umask(0o077)
    args.report.mkdir(parents=True)
    budget = Budget(args.report / "budget.sqlite3", ceiling=1)
    result = {}
    try:
        result = asyncio.run(evaluate(args, args.report, budget))
    except Exception as error:
        result = {"failure_type": type(error).__name__}
    finally:
        budget.close()
        result["budget"] = budget.snapshot()
        (args.report / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(
            json.dumps(
                {
                    k: v
                    for k, v in result.items()
                    if k not in {"speech_transcript", "events", "tool_reads", "budget"}
                }
            )
        )
        print(json.dumps({k: v for k, v in result["budget"].items() if k != "runs"}))


if __name__ == "__main__":
    main()
