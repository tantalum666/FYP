#!/usr/bin/env python3
"""Configure OpenAI using an already-approved private key file; no API request.

Writes provider settings only. It does not change context consent, permissions,
start services, create a key, or copy the key into the service environment.
"""

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.computer_use_network import local_browser_proxy
from desk.voice_credentials import openai_key


def configure(runtime, credentials, *, browser=None, browser_proxy="", region_unavailable=False):
    runtime, credentials = Path(runtime).absolute(), Path(credentials).absolute()
    # Loading checks ownership, size, permissions and every path component.
    openai_key(str(credentials))
    if runtime.resolve() != runtime or runtime.is_symlink():
        raise ValueError("Use the real owner runtime directory")
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    if runtime.stat().st_uid != os.getuid() or stat.S_IMODE(runtime.stat().st_mode) & 0o077:
        raise ValueError("Runtime must be private to its owner")
    target = runtime / "service.env"
    if target.is_symlink() or (
        target.exists()
        and (
            target.is_symlink()
            or not target.is_file()
            or target.stat().st_uid != os.getuid()
            or stat.S_IMODE(target.stat().st_mode) != 0o600
            or target.stat().st_size > 32000
        )
    ):
        raise ValueError("Use an owner-private service environment")
    settings = {
        "DESK_OPENAI_CREDENTIAL_FILE": str(credentials),
        "DESK_VOICE_PROVIDER": "openai_realtime",
        "DESK_VOICE_MODEL": "gpt-realtime-2.1",
        "DESK_VOICE_ENDPOINT": "wss://api.openai.com/v1/realtime",
        "DESK_VOICE_API_KEY": "",
        "DESK_VOICE_VOICE": "marin",
        "DESK_TEXT_PROVIDER": "openai",
        "DESK_TEXT_MODEL": "gpt-6.1-sol",
        "DESK_TEXT_ENDPOINT": "https://api.openai.com/v1/responses",
        "DESK_TEXT_API_KEY": "",
        "DESK_TEXT_BACKGROUND": "0",
        "DESK_MEMORY_EXTRACT": "0",
        "DESK_OPENAI_REGION_UNSUPPORTED": "1" if region_unavailable else "0",
    }
    if browser:
        binary = Path(browser).absolute()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError("Choose an installed browser executable")
        settings.update(
            DESK_COMPUTER_USE_ENABLED="1",
            DESK_BROWSER_EXECUTABLE=str(binary),
            DESK_BROWSER_PROXY_URL=local_browser_proxy(browser_proxy) or "",
        )
    before = target.read_text() if target.exists() else ""
    lines = [line for line in before.splitlines() if line.split("=", 1)[0] not in settings]
    lines.extend(
        name + "=" + json.dumps(value, ensure_ascii=False) for name, value in settings.items()
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".openai-settings-", dir=runtime)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write("\n".join(lines) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        descriptor = os.open(runtime, os.O_RDONLY)
        os.fsync(descriptor)
        os.close(descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {
        "configuration_only": True,
        "service_env": str(target),
        "provider": "openai",
        "text_model": settings["DESK_TEXT_MODEL"],
        "voice_model": settings["DESK_VOICE_MODEL"],
        "region_unavailable": region_unavailable,
        "model_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--browser-proxy", default="")
    parser.add_argument("--region-unavailable", action="store_true")
    args = parser.parse_args()
    try:
        result = configure(
            args.runtime,
            args.credentials,
            browser=args.browser,
            browser_proxy=args.browser_proxy,
            region_unavailable=args.region_unavailable,
        )
    except (ValueError, OSError):
        raise SystemExit(
            "OpenAI settings were not applied; check the private file/runtime paths."
        ) from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
