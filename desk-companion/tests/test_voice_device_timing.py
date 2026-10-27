import sys
from types import SimpleNamespace

import pytest

from desk.agents.voice import AudioDevice


def test_native_capture_and_output_use_portaudio_clock_not_network_receipt(monkeypatch):
    callbacks = {}

    class Stream:
        def __init__(self, kind, **kwargs):
            callbacks[kind] = kwargs["callback"]

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            RawInputStream=lambda **kw: Stream("input", **kw),
            RawOutputStream=lambda **kw: Stream("output", **kw),
        ),
    )
    now = [500.0]
    monkeypatch.setattr("desk.agents.voice.time.monotonic", lambda: now[0])
    device = AudioDevice()
    device.start()
    timestamp = SimpleNamespace(currentTime=100, inputBufferAdcTime=99.9, outputBufferDacTime=100.2)
    callbacks["input"]((1000).to_bytes(2, "little", signed=True) * 640, 640, timestamp, None)
    assert device.last_voice_at == pytest.approx(499.94)
    block = b"\x00" * 480 + (1000).to_bytes(2, "little", signed=True) * 720
    device.output.put((block, {"turn_id": 1, "audio_id": 1, "after_tool": True}))
    output = bytearray(1920)
    callbacks["output"](output, 960, timestamp, None)
    assert bytes(output) == block
    mark = device.timings.get_nowait()
    assert mark["played_at"] == pytest.approx(500.21)
    assert not device.drained()
    now[0] = 501
    assert device.drained()
    device.output.put((block, {"turn_id": 1, "audio_id": 2}))
    device.silence()
    assert device.output.empty() and device.timings.empty()
    callbacks["output"](output, 960, timestamp, None)
    assert not any(output)
    device.close()
