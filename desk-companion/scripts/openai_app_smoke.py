"""Explicit, synthetic, bounded live test through the production VoiceService.

No retry loop, microphone, camera, external accounts or real owner data. Requires
--run-live. At most four named attempts share a fresh USD1 reservation ledger.
"""

import argparse
import asyncio
import base64
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.openai_voice import OPENAI_REALTIME_ENDPOINT
from desk.provider_policy import ProviderWebSocketConnect
from desk.voice import VoiceConfig
from desk.voice_credentials import openai_key
from voice_eval import budget as budget_module
from voice_eval.fixtures import Fixture, LINES, VOICES

MODEL = "gpt-realtime-2.1-mini"
MAX_SECONDS = 35
MAX_RESPONSES = 4


async def trial(runtime, pcm, evidence):
    incoming = asyncio.Queue()
    ready, closed = asyncio.Event(), asyncio.Event()
    output_hash = hashlib.sha256()
    audio_bytes = 0
    started = time.monotonic()

    class Client:
        async def iter_text(self):
            while True:
                item = await incoming.get()
                yield json.dumps(item)

        async def send_json(self, event):
            nonlocal audio_bytes
            kind = event.get("type")
            if kind == "ready":
                ready.set()
            if kind == "audio":
                chunk = base64.b64decode(event["audio"])
                audio_bytes += len(chunk)
                output_hash.update(chunk)
            elif kind == "transcript":
                evidence.setdefault("transcripts", []).append(
                    {k: event[k] for k in ("role", "text", "final") if k in event}
                )
            elif kind in {"error", "ended"}:
                evidence.setdefault("client_status", []).append(event)
            if kind == "turn_complete" and audio_bytes:
                await incoming.put({"type": "stop"})

        async def close(self, code=1000):
            closed.set()

    class Connection:
        def __init__(self, *args, **kwargs):
            self.context = ProviderWebSocketConnect(*args, **kwargs)

        async def __aenter__(self):
            self.ws = await self.context.__aenter__()
            return self

        async def __aexit__(self, *args):
            return await self.context.__aexit__(*args)

        async def send(self, raw):
            data = json.loads(raw)
            if (
                data.get("type") == "response.create"
                and evidence.get("responses_created", 0) >= MAX_RESPONSES
            ):
                await incoming.put({"type": "stop"})
                return
            item = data.get("item", {})
            if item.get("type") == "function_call_output":
                evidence.setdefault("tool_results", []).append(
                    {"call_id": item.get("call_id"), "result": json.loads(item.get("output", "{}"))}
                )
            await self.ws.send(raw)

        def __aiter__(self):
            return self.receive()

        async def receive(self):
            async for raw in self.ws:
                event = json.loads(raw)
                kind = event.get("type")
                if kind == "response.created":
                    evidence["responses_created"] = evidence.get("responses_created", 0) + 1
                    if evidence["responses_created"] > MAX_RESPONSES:
                        await incoming.put({"type": "stop"})
                        return
                if kind == "response.done":
                    response = event.get("response", {})
                    evidence.setdefault("usage", []).append(response.get("usage", {}))
                    evidence.setdefault("response_status", []).append(response.get("status"))
                if kind == "conversation.item.input_audio_transcription.completed":
                    evidence.setdefault("transcription_usage", []).append(event.get("usage", {}))
                if kind == "response.function_call_arguments.done":
                    evidence.setdefault("tools", []).append(
                        {
                            "name": event.get("name"),
                            "id": event.get("call_id"),
                            "arguments": event.get("arguments"),
                        }
                    )
                if kind == "error":
                    error = event.get("error", {})
                    evidence.setdefault("provider_errors", []).append(
                        {
                            "code": str(error.get("code", ""))[:100],
                            "param": str(error.get("param", ""))[:100],
                        }
                    )
                yield raw

    async def feed():
        await asyncio.wait_for(ready.wait(), timeout=18)
        origin = time.monotonic()
        offset = 0
        while not closed.is_set():
            block = pcm[offset : offset + 1280]
            offset += 1280
            await incoming.put(
                {"type": "audio", "audio": base64.b64encode(block.ljust(1280, b"\0")).decode()}
            )
            evidence["input_seconds"] = min(offset, len(pcm)) / 32000
            await asyncio.sleep(max(0, origin + offset / 32000 - time.monotonic()))
            if time.monotonic() - started > MAX_SECONDS:
                await incoming.put({"type": "stop"})
                return

    runtime.voice.connector = Connection
    owner = {"kind": "owner", "session": runtime.store.create_owner_session()}
    principal = runtime.voice.consume(runtime.voice.ticket(owner)["ticket"])
    sender = asyncio.create_task(feed())
    try:
        await asyncio.wait_for(
            runtime.voice.run(Client(), principal, "zh"), timeout=MAX_SECONDS + 5
        )
    except Exception as error:
        evidence["error_type"] = type(error).__name__
    finally:
        sender.cancel()
        with contextlib.suppress(asyncio.CancelledError, TimeoutError):
            await sender
    evidence.update(
        elapsed_seconds=round(time.monotonic() - started, 3),
        output_audio_seconds=round(audio_bytes / 48000, 3),
        output_audio_sha256=output_hash.hexdigest(),
        voice_slot_released=not runtime.voice.active,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--attempt", choices=["1", "2", "3", "4"], required=True)
    args = parser.parse_args()
    if not args.run_live:
        parser.error("Explicit --run-live required")
    for name in list(os.environ):
        if name.startswith("DESK_"):
            os.environ.pop(name)
    os.environ.update(
        DESK_TEXT_PROVIDER="none", DESK_VOICE_PROVIDER="none", DESK_COMPUTER_ENABLED="0"
    )
    args.runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    budget_module.CEILING_USD = 1.0
    ledger = budget_module.Budget(args.runtime / "budget.sqlite3")
    model = "gpt-realtime-2.1" if args.attempt == "4" else MODEL
    run_id = "production-adapter-" + args.attempt
    ledger.reserve(
        run_id, model, 0.4 if args.attempt == "4" else 0.25 if args.attempt == "3" else 0.5
    )
    evidence = {
        "model": model,
        "synthetic_input": True,
        "production_voice_service": True,
        "attempt": args.attempt,
    }
    try:
        key = openai_key(str(args.key_file))
        fixture = Fixture(args.runtime / ("fixture-" + args.attempt), "calendar-zh")
        fixture.runtime.voice.config = VoiceConfig(
            "openai_realtime", OPENAI_REALTIME_ENDPOINT, model, key
        )
        speech = args.runtime / "calendar-zh.wav"
        subprocess.run(
            [
                "say",
                "-v",
                VOICES["zh"],
                "--file-format=WAVE",
                "--data-format=LEI16@16000",
                "-o",
                str(speech),
                LINES["calendar-zh"][1],
            ],
            check=True,
        )
        with wave.open(str(speech)) as audio:
            assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (
                16000,
                1,
                2,
            )
            pcm = bytes(6400) + audio.readframes(audio.getnframes())
        if len(pcm) > 20 * 32000:
            raise ValueError("FIXTURE_TOO_LONG")
        asyncio.run(trial(fixture.runtime, pcm, evidence))
        estimate = sum(budget_module.token_cost(model, u) for u in evidence.get("usage", []) if u)
        # Charge ASR receipts at the higher Realtime rates as a conservative bound.
        estimate += sum(
            budget_module.token_cost(model, u)
            for u in evidence.get("transcription_usage", [])
            if u and "input_tokens" in u
        )
        if evidence.get("input_seconds") and not evidence.get("transcription_usage"):
            estimate += 0.01 * evidence["input_seconds"] / 60
        finalized = (
            evidence.get("responses_created", 0) == len(evidence.get("usage", []))
            and "error_type" not in evidence
        )
        evidence["estimated_usd_upper"] = estimate
        evidence["finalized"] = finalized
        ledger.finish(run_id, estimate=estimate, finalized=finalized, result=evidence)
    finally:
        (args.runtime / ("attempt-" + args.attempt + ".json")).write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        )
    print(
        json.dumps(
            {
                k: evidence.get(k)
                for k in [
                    "model",
                    "responses_created",
                    "tools",
                    "provider_errors",
                    "client_status",
                    "output_audio_seconds",
                    "estimated_usd_upper",
                    "finalized",
                    "voice_slot_released",
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
