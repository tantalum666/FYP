import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from desk.agents.wake import WakeDetector


def test_keyword_setup_does_not_write_installed_model_directory(tmp_path, monkeypatch):
    models = tmp_path / "installed-models"
    models.mkdir()
    names = [
        "tokens.txt", "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
        "decoder-epoch-13-avg-2-chunk-8-left-64.onnx",
        "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
    ]
    manifest = {"files": {}}
    for name in names:
        (models / name).write_bytes(b"fixture-model")
        manifest["files"][name] = {"sha256": hashlib.sha256(b"fixture-model").hexdigest()}
    metadata = tmp_path / "manifest.json"
    metadata.write_text(json.dumps(manifest))
    seen = {}

    class Spotter:
        def __init__(self, **options):
            path = Path(options["keywords_file"])
            assert not path.is_relative_to(models)
            seen.update(path=path, keywords=path.read_text())

        def create_stream(self):
            return SimpleNamespace(accept_waveform=lambda *args: None)

        def is_ready(self, _stream):
            return False

    monkeypatch.setitem(sys.modules, "sherpa_onnx", SimpleNamespace(KeywordSpotter=Spotter))
    original_write = Path.write_text

    def protected_write(path, *args, **kwargs):
        if path.is_relative_to(models):
            raise PermissionError("Installed weights are read-only")
        return original_write(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", protected_write)
    detector = WakeDetector(models, metadata, phrase="alice")
    assert detector.accept([0.0] * 320) is None
    assert "@ALICE" in seen["keywords"]
    assert not seen["path"].exists()
    assert sorted(path.name for path in models.iterdir()) == sorted(names)


def test_bad_model_digest_fails_before_loading_runtime(tmp_path, monkeypatch):
    metadata = tmp_path / "manifest.json"
    metadata.write_text(json.dumps({"files": {"tokens.txt": {"sha256": "0" * 64}}}))
    monkeypatch.setitem(sys.modules, "sherpa_onnx", SimpleNamespace())
    with pytest.raises(ValueError, match="checksum mismatch"):
        WakeDetector(tmp_path, metadata, phrase="alice")
