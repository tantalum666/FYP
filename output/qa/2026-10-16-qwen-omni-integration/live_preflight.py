"""One bounded authenticated Omni setup; no audio, image, user data or raw key output."""

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desk-companion/backend"))
import websockets
from desk.voice import QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, QwenOmniProtocol, VoiceConfig
from desk.voice_credentials import qwen_key

QA = Path(__file__).parent


async def main():
    result = {"authorization_cny": 5, "trial": "setup_only", "audio_sent": False, "images_sent": False, "account_eligibility": "unverified", "model": QWEN_OMNI_MODEL}
    key = qwen_key(str(Path.home() / ".config/desk-companion/qwen.env"))
    config = VoiceConfig("qwen_omni", QWEN_OMNI_ENDPOINT, QWEN_OMNI_MODEL, key)
    started = time.monotonic()
    try:
        async with websockets.connect(QWEN_OMNI_ENDPOINT + "?model=" + QWEN_OMNI_MODEL, additional_headers={"Authorization": "Bearer " + key}, open_timeout=12, close_timeout=3, max_size=2_000_000) as provider:
            result["websocket_connected"] = True
            setup = QwenOmniProtocol().setup(config, "Synthetic integration preflight. Do not generate a response unless asked.", allow_memory=False)
            setup["session"]["tools"] = [t for t in setup["session"]["tools"] if t["function"]["name"] == "calendar_query"]
            setup["session"]["max_tokens"] = 256
            await provider.send(json.dumps(setup))
            for _ in range(8):
                event = json.loads(await asyncio.wait_for(provider.recv(), timeout=8))
                if event.get("type") == "session.updated":
                    result["session_configured"] = True
                    result["account_eligibility"] = "setup_accepted"
                    break
                if event.get("type") == "error":
                    error = event.get("error", {})
                    result["provider_error"] = str(error.get("code", error.get("type", "provider_error"))).replace(key, "[redacted]")[:100]
                    result["provider_param"] = str(error.get("param", "")).replace(key, "[redacted]")[:100]
                    break
    except Exception as error:
        result["failure_class"] = type(error).__name__
        response = getattr(error, "response", None)
        if response is not None:
            result["http_status"] = getattr(response, "status_code", None)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["usage_observed"] = False
    result["billing_confirmed"] = False
    key = ""
    (QA / "live-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
