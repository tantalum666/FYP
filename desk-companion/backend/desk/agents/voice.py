"""Explicit local hands-free voice worker (16 kHz capture, 24 kHz playback).

Use an AEC-capable microphone/speaker path on the actual desk. No software-only
claim of acoustic echo cancellation is made by this sounddevice adapter.
"""

import argparse
import asyncio
import base64
import contextlib
import json
import queue
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import websockets

from .wake import WakeDetector


class AudioDevice:
    def __init__(self, input_device=None, output_device=None):
        import sounddevice as sd

        self.sd = sd
        self.input_device = input_device
        self.output_device = output_device
        self.input = queue.Queue(maxsize=25)
        self.output = queue.Queue(maxsize=750)
        self.playing = bytearray()
        self.play_lock = threading.Lock()
        self.marks = []
        self.timings = queue.Queue(maxsize=64)
        self.last_voice_at = None
        self.playback_end = 0.0
        self.stream_in = None
        self.stream_out = None

    def start(self):
        def capture(data, frames, timestamp, status):
            pcm = memoryview(bytes(data)).cast("h")
            voiced = next((i for i in range(len(pcm) - 1, -1, -1) if abs(pcm[i]) >= 328), None)
            if voiced is not None:
                self.last_voice_at = (
                    time.monotonic()
                    + timestamp.inputBufferAdcTime
                    - timestamp.currentTime
                    + (voiced + 1) / 16000
                )
            try:
                self.input.put_nowait(bytes(data))
            except queue.Full:
                # Drop stale capture rather than sending seconds-old speech.
                with contextlib.suppress(queue.Empty):
                    self.input.get_nowait()

        def playback(data, frames, timestamp, status):
            needed = frames * 2
            with self.play_lock:
                while len(self.playing) < needed:
                    try:
                        item = self.output.get_nowait()
                    except queue.Empty:
                        break
                    block, marker = item if isinstance(item, tuple) else (item, None)
                    if marker:
                        pcm = memoryview(block).cast("h")
                        first = next((i for i, value in enumerate(pcm) if abs(value) >= 33), None)
                        if first is not None:
                            self.marks.append((len(self.playing) + first * 2, marker))
                    self.playing.extend(block)
                payload = self.playing[:needed]
                del self.playing[:needed]
                at = time.monotonic() + timestamp.outputBufferDacTime - timestamp.currentTime
                remaining = []
                for offset, marker in self.marks:
                    if offset < len(payload):
                        with contextlib.suppress(queue.Full):
                            self.timings.put_nowait({**marker, "played_at": at + offset / 48000})
                    else:
                        remaining.append((offset - len(payload), marker))
                self.marks = remaining
                if payload:
                    self.playback_end = at + len(payload) / 48000
                data[:] = bytes(payload) + b"\x00" * (needed - len(payload))

        self.stream_in = self.sd.RawInputStream(
            device=self.input_device,
            samplerate=16000,
            blocksize=640,
            channels=1,
            dtype="int16",
            callback=capture,
        )
        self.stream_out = self.sd.RawOutputStream(
            device=self.output_device,
            samplerate=24000,
            blocksize=960,
            channels=1,
            dtype="int16",
            callback=playback,
        )
        self.stream_in.start()
        self.stream_out.start()

    def silence(self):
        with self.play_lock:
            self.playing.clear()
            self.marks.clear()
            self.playback_end = 0
            for items in (self.output, self.timings):
                while not items.empty():
                    with contextlib.suppress(queue.Empty):
                        items.get_nowait()

    def drained(self):
        with self.play_lock:
            return (
                not self.playing and self.output.empty() and time.monotonic() >= self.playback_end
            )

    def close(self):
        for stream in (self.stream_in, self.stream_out):
            if stream:
                stream.stop()
                stream.close()
        self.stream_in = self.stream_out = None
        self.silence()
        while not self.input.empty():
            with contextlib.suppress(queue.Empty):
                self.input.get_nowait()


async def conversation(api, headers, audio, language, allowed):
    with httpx.Client(trust_env=False, base_url=api, headers=headers, timeout=3) as client:
        response = client.post("/api/agent/voice/tickets", json={})
        response.raise_for_status()
        ticket = response.json()["ticket"]
    endpoint = api.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/api/voice/ws"
    async with websockets.connect(
        endpoint, proxy=None, open_timeout=5, max_size=2_000_000, max_queue=8
    ) as socket:
        await socket.send(json.dumps({"ticket": ticket, "language": language}))
        ready = asyncio.Event()
        timing = {
            "turn": None,
            "end": 0,
            "endpoint": "provider_event",
            "first": False,
            "post": False,
            "complete": False,
        }

        async def send():
            await asyncio.wait_for(ready.wait(), timeout=20)
            while allowed():
                try:
                    chunk = await asyncio.to_thread(audio.input.get, True, 0.2)
                except queue.Empty:
                    continue
                await asyncio.wait_for(
                    socket.send(
                        json.dumps({"type": "audio", "audio": base64.b64encode(chunk).decode()})
                    ),
                    timeout=2,
                )

        async def receive():
            async for raw in socket:
                event = json.loads(raw)
                if event["type"] == "ready":
                    # A ready cue should be added through a real speaker after AEC testing.
                    ready.set()
                elif event["type"] == "turn_waiting":
                    if timing["turn"] != event["turn_id"]:
                        now = time.monotonic()
                        valid = (
                            audio.last_voice_at is not None and 0 <= now - audio.last_voice_at < 15
                        )
                        timing.update(
                            turn=event["turn_id"],
                            end=audio.last_voice_at if valid else now,
                            endpoint="capture_energy" if valid else "provider_event",
                            first=False,
                            post=False,
                            complete=False,
                        )
                elif event["type"] == "turn_complete":
                    if event.get("turn_id") == timing["turn"]:
                        timing["complete"] = True
                elif event["type"] == "interrupted":
                    timing.update(turn=None, complete=False)
                    audio.silence()
                elif event["type"] == "audio":
                    from desk.voice import pcm_chunk

                    data = pcm_chunk(event["audio"], maximum=1_000_000)
                    # Match the browser's 30-second bound. A provider can generate
                    # a normal calendar answer much faster than the DAC plays it.
                    for i in range(0, len(data), 1920):
                        try:
                            audio.output.put_nowait(
                                (
                                    data[i : i + 1920],
                                    {
                                        "turn_id": event.get("turn_id"),
                                        "audio_id": event.get("audio_id"),
                                        "after_tool": event.get("after_tool", False),
                                    },
                                )
                            )
                        except queue.Full:
                            raise RuntimeError("Playback queue exceeded limit") from None
                elif event["type"] in {"error", "ended"}:
                    return

        async def report_playback():
            while allowed():
                try:
                    mark = audio.timings.get_nowait()
                except queue.Empty:
                    mark = None
                if (
                    mark
                    and mark["turn_id"] == timing["turn"]
                    and (not timing["first"] or (mark["after_tool"] and not timing["post"]))
                ):
                    await asyncio.sleep(max(0, mark["played_at"] - time.monotonic()))
                    if mark["turn_id"] != timing["turn"]:
                        continue
                    await socket.send(
                        json.dumps(
                            {
                                "type": "playback_started",
                                "turn_id": mark["turn_id"],
                                "audio_id": mark["audio_id"],
                                "elapsed_ms": max(0, (mark["played_at"] - timing["end"]) * 1000),
                                "timing_source": "portaudio_dac",
                                "endpoint_source": timing["endpoint"],
                            }
                        )
                    )
                    timing["first"] = True
                    timing["post"] = timing["post"] or mark["after_tool"]
                if timing["complete"] and audio.drained():
                    await socket.send(
                        json.dumps({"type": "playback_ended", "turn_id": timing["turn"]})
                    )
                    timing["complete"] = False
                await asyncio.sleep(0.02)

        tasks = [
            asyncio.create_task(send()),
            asyncio.create_task(receive()),
            asyncio.create_task(report_playback()),
        ]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            audio.silence()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8831")
    parser.add_argument("--runtime", type=Path, default=Path(".runtime"))
    parser.add_argument("--input-device", type=int)
    parser.add_argument("--output-device", type=int)
    parser.add_argument("--language", choices=["en", "zh"], default="en")
    args = parser.parse_args()
    url = urlsplit(args.api)
    if url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}
    ):
        parser.error("Use loopback HTTP or HTTPS")
    token = json.loads((args.runtime / "agent.json").read_text())["token"]
    headers = {"Authorization": "Bearer " + token, "X-Desk-Request": "1"}
    wake = WakeDetector(args.runtime / "models/wake")
    audio = AudioDevice(args.input_device, args.output_device)
    stop = threading.Event()
    state = {"enabled": False, "at": 0.0}

    def control():
        with httpx.Client(trust_env=False, base_url=args.api, headers=headers, timeout=2) as client:
            while not stop.is_set():
                try:
                    r = client.get("/api/agent/config")
                    r.raise_for_status()
                    state.update(enabled=r.json().get("voice_enabled", False), at=time.monotonic())
                except (httpx.HTTPError, ValueError):
                    state["enabled"] = False
                stop.wait(0.5)

    threading.Thread(target=control, daemon=True).start()

    def allowed():
        return state["enabled"] and time.monotonic() - state["at"] < 3

    try:
        import numpy as np

        while True:
            if not allowed():
                audio.close()
                wake.reset()
                time.sleep(0.25)
                continue
            if audio.stream_in is None:
                audio.start()
            try:
                chunk = audio.input.get(timeout=0.2)
            except queue.Empty:
                continue
            if wake.accept(np.frombuffer(chunk, dtype="<i2").astype("float32") / 32768):
                try:
                    asyncio.run(conversation(args.api, headers, audio, args.language, allowed))
                except (
                    httpx.HTTPError,
                    OSError,
                    TimeoutError,
                    ValueError,
                    RuntimeError,
                    websockets.WebSocketException,
                ):
                    print("Voice session unavailable; returning to local wake listening.")
                    time.sleep(1)
                wake.reset()
                audio.silence()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        audio.close()


if __name__ == "__main__":
    main()
