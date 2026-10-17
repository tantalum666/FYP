"""Loopback UI fixture: synthetic provider only, never loads a real key or captures media."""

import asyncio
import base64
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desk-companion/backend"))
os.environ["DESK_VOICE_PROVIDER"] = "none"
os.environ["DESK_TEXT_PROVIDER"] = "none"
os.environ["DESK_TEXT_BACKGROUND"] = "0"
os.environ.pop("DESK_QWEN_CREDENTIAL_FILE", None)

import uvicorn
os.environ["DESK_COMPUTER_ENABLED"] = "1"
from desk.app import create_app
from desk.voice import QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, VoiceConfig


class Provider:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.greeted = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        return json.dumps(await self.queue.get())

    async def send(self, raw):
        message = json.loads(raw)
        if message["type"] == "session.update":
            await self.queue.put({"type": "session.updated"})
        elif message["type"] == "input_audio_buffer.append" and not self.greeted:
            self.greeted = True
            for event in [
                {"type": "input_audio_buffer.speech_started"},
                {"type": "conversation.item.input_audio_transcription.completed", "transcript": "Synthetic UI fixture request"},
                {"type": "response.created", "response": {"id": "fixture-response"}},
                {"type": "response.audio_transcript.delta", "delta": "Simulated provider ready. Select an image or screen to test sharing."},
                {"type": "response.audio.delta", "delta": base64.b64encode(b"\x00" * 4800).decode()},
                {"type": "response.done", "response": {"id": "fixture-response", "usage": {"input_tokens": 10, "output_tokens": 3}}},
            ]:
                await self.queue.put(event)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="fyp-omni-ui-fixture-") as directory:
        app = create_app(Path(directory), password="qa-fixture", scheduler=True, allow_replay=True)
        app.state.runtime.voice.config = VoiceConfig("qwen_omni", QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, "fixture_" * 4)
        app.state.runtime.voice.connector = lambda *args, **kwargs: Provider()
        uvicorn.run(app, host="127.0.0.1", port=5191, log_level="warning", access_log=False)
