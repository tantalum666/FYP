"""Local keyword spotting. Audio stays local until a configured phrase is detected."""

import hashlib
import json
from pathlib import Path
import tempfile


class WakeDetector:
    def __init__(self, directory, manifest=None, *, phrase="desk"):
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
        if phrase not in {"desk", "alice"}:
            raise ValueError("Unknown local wake phrase")
        keyword_text = (
            "AE1 L AH0 S :1.5 #0.35 @ALICE\nài l ì s ī :1.5 #0.35 @ALICE\n"
            if phrase == "alice"
            else "HH EY1 D EH1 S K :1.5 #0.3 @HEY_DESK\nn ǐ h ǎo zh uō b àn :1.5 #0.3 @你好桌伴\n"
        )
        # Shipped weights can be root-owned/read-only. The pinned recognizer
        # loads its keyword file during construction; no runtime model mutation.
        with tempfile.TemporaryDirectory(prefix="desk-keywords-") as temporary:
            keywords = Path(temporary) / "keywords.txt"
            keywords.write_text(keyword_text)
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
        if phrase == "alice":
            # Seed feature context before announcing readiness; the first real
            # keyword should not have to supply its own leading silence.
            self.accept([0.0] * 6400)

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
