from dataclasses import dataclass
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    database_url: str
    device_key: str
    simulator_key: str
    development: bool = False
    session_hours: int = 8
    console_key: str = ""
    console_workspace_id: str = ""
    allowed_origins: tuple[str, ...] = ("http://localhost:5177", "http://127.0.0.1:5177",
                                       "http://localhost:8799", "http://127.0.0.1:8799")


def load_settings() -> Settings:
    path = Path(os.environ.get("SENPLATE_CONFIG", ROOT / ".runtime/config.json"))
    if not path.exists():
        raise RuntimeError("Run scripts/dev.py setup before starting the local API.")
    data = json.loads(path.read_text())
    return Settings(**{k: data[k] for k in Settings.__dataclass_fields__ if k in data})
