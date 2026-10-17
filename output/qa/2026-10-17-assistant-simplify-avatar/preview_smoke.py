"""Read-only loopback smoke check. Never prints credentials or cookies."""
import hashlib
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
base = "http://localhost:8832"
credentials = json.loads(
    (ROOT / "desk-companion/.runtime/a1-review-20261017/credentials.json").read_text()
)
with httpx.Client(base_url=base, timeout=15, trust_env=False) as client:
    authenticated = client.post(
        "/api/session",
        json=credentials,
        headers={"X-Desk-Request": "1", "Origin": base},
    )
    assert authenticated.status_code == 200, "Preview authentication failed"
    response = client.get("/api/workspace")
    assert response.status_code == 200, "Preview workspace unavailable"
    workspace = response.json()
    assert workspace["voice"]["provider"] == "none"
    assert not workspace["voice"]["configured"]
    assert workspace["text_ai"]["provider"] == "none"
    asset = client.get("/companion/a1-v2.glb")
    assert asset.status_code == 200
    expected = json.loads(
        (ROOT / "desk-companion/frontend/public/companion/source.json").read_text()
    )["stats"]
    assert hashlib.sha256(asset.content).hexdigest() == expected["sha256"]
    result = {
        "owner_authentication": True,
        "voice_provider": workspace["voice"]["provider"],
        "voice_configured": workspace["voice"]["configured"],
        "text_provider": workspace["text_ai"]["provider"],
        "html": client.get("/").status_code,
        "device_html": client.get("/?surface=device").status_code,
        "avatar_html": client.get("/?surface=avatar").status_code,
        "model_bytes": len(asset.content),
        "model_matches_final_source": True,
    }
    assert result["html"] == result["device_html"] == result["avatar_html"] == 200
    (Path(__file__).parent / "preview-smoke.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))
