"""Read-only diagnostics; deliberately excludes credentials and personal event data."""

import importlib.metadata
import json
import platform
import sys
from pathlib import Path


root = Path(__file__).resolve().parents[1]
versions = {}
for package in ["fastapi", "uvicorn", "mediapipe", "sherpa-onnx", "sherpa-onnx-core", "httpx"]:
    try:
        versions[package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        versions[package] = "not installed"
result = {
    "os": platform.system(),
    "architecture": platform.machine(),
    "python": sys.version.split()[0],
    "packages": versions,
    "frontend_built": (root / "frontend/dist/index.html").is_file(),
    "pose_model_present": (root / ".runtime/models/pose_landmarker_lite.task").is_file(),
    "wake_model_present": (root / ".runtime/models/wake/tokens.txt").is_file(),
    "runtime_present": (root / ".runtime/desk.sqlite3").is_file(),
    "credentials_printed": False,
    "camera_opened": False,
    "microphone_opened": False,
}
print(json.dumps(result, indent=2))
