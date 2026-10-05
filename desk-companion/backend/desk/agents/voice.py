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
        self.output = queue.Queue(maxsize=150)
        self.playing = bytearray()
        self.stream_in = None
        self.stream_out = None

    def start(self):
        def capture(data, frames, timestamp, status):
            try:
                self.input.put_nowait(bytes(data))
            except queue.Full:
                # Drop stale capture rather than sending seconds-old speech.
                with contextlib.suppress(queue.Empty):
                    self.input.get_nowait()

        def playback(data, frames, timestamp, status):
            needed = frames * 2
            while len(self.playing) < needed:
                try:
                    self.playing.extend(self.output.get_nowait())
                except queue.Empty:
                    break
            payload = self.playing[:needed]
            del self.playing[:needed]
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
        self.playing.clear()
        while not self.output.empty():
            with contextlib.suppress(queue.Empty):
                self.output.get_nowait()

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
                elif event["type"] == "interrupted":
                    audio.silence()
                elif event["type"] == "audio":
                    from desk.voice import pcm_chunk

                    data = pcm_chunk(event["audio"], maximum=1_000_000)
                    # Rechunk to bound output backlog to at most six seconds.
                    for i in range(0, len(data), 1920):
                        try:
                            audio.output.put_nowait(data[i : i + 1920])
                        except queue.Full:
                            raise RuntimeError("Playback queue exceeded limit") from None
                elif event["type"] in {"error", "ended"}:
                    return

        tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
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
