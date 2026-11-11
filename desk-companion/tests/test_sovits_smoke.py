import argparse
import importlib.util
import io
from pathlib import Path
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.error

import pytest

spec = importlib.util.spec_from_file_location(
    "sovits_smoke", Path(__file__).parents[1] / "scripts/sovits_smoke.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.example",
        "http://127.0.0.1@cloud.example",
        "file:///tmp/audio",
        "http://127.0.0.1/?token=private",
    ],
)
def test_reference_audio_probe_refuses_remote_or_credential_destinations(url):
    with pytest.raises(argparse.ArgumentTypeError):
        probe.local_endpoint(url)


def test_probe_rejects_truncated_or_silent_audio():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(32000)
        writer.writeframes(b"\xe8\x03" * 16000)
    data = buffer.getvalue()
    assert probe.inspect_wave(data)["duration_seconds"] == 0.5
    with pytest.raises(ValueError):
        probe.inspect_wave(data[:-100])
    with pytest.raises(ValueError):
        probe.inspect_wave(data[:44] + bytes(len(data) - 44))


def test_probe_does_not_redirect_reference_payload(tmp_path):
    paths = []

    class Redirect(BaseHTTPRequestHandler):
        def do_POST(self):
            paths.append(self.path)
            self.send_response(307)
            self.send_header("Location", "/unexpected")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Redirect)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with pytest.raises(urllib.error.HTTPError):
            probe.request_audio(
                f"http://127.0.0.1:{server.server_port}/tts",
                {"ref_audio_path": "/fictional/reference.wav"},
                tmp_path / "result.wav",
                timeout=2,
            )
        assert paths == ["/tts"] and not (tmp_path / "result.wav").exists()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
