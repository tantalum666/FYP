"""Local keyword spotting. Audio stays local until a configured phrase is detected."""

import hashlib
import json
from pathlib import Path


class WakeDetector:
    def __init__(self, directory, manifest=None):
        import sherpa_onnx

        directory = Path(directory)
        manifest = (
            Path(manifest)
            if manifest
            else Path(__file__).resolve().parents[3] / "config" / "wake-model.json"
        )
        metadata = json.loads(manifest.read_text())
        for name, details in metadata["files"].items():
            path = directory / name
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != details["sha256"]
            ):
                raise ValueError(
                    "Wake model missing or checksum mismatch; run scripts/fetch_wake_model.py"
                )
        keywords = directory / "desk-keywords.txt"
        keywords.write_text(
            "HH EY1 D EH1 S K :1.5 #0.3 @HEY_DESK\nn ǐ h ǎo zh uō b àn :1.5 #0.3 @你好桌伴\n"
        )
        self.spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(directory / "tokens.txt"),
            encoder=str(directory / "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx"),
            decoder=str(directory / "decoder-epoch-13-avg-2-chunk-8-left-64.onnx"),
            joiner=str(directory / "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"),
            keywords_file=str(keywords),
            num_threads=2,
            provider="cpu",
        )
        self.stream = self.spotter.create_stream()

    def reset(self):
        self.spotter.reset_stream(self.stream)

    def accept(self, samples):
        self.stream.accept_waveform(16000, samples)
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            result = self.spotter.get_result(self.stream)
            if result:
                self.reset()
                return result
        return None
