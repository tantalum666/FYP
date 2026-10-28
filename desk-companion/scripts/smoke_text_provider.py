"""One real Qwen or Gemini text call. Skipped unless explicitly armed.

Do not add this file to GitHub Actions or any default test command. With no
environment, it prints "smoke skipped" and exits 0 without opening a socket.
Voice providers are not covered here.

Arming requires every one of these:

- DESK_SMOKE_TEXT=1
- DESK_TEXT_PROVIDER=qwen or gemini
- DESK_TEXT_MODEL and DESK_TEXT_API_KEY
- DESK_TEXT_ENDPOINT for Qwen
- DESK_SMOKE_MAX_TOKENS as an integer from 1 through 64

A missing or larger cap skips. It does not fall back to the normal 1600-token call.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

CEILING = 64


def readiness(env):
    if env.get("DESK_SMOKE_TEXT") != "1":
        return None
    provider = env.get("DESK_TEXT_PROVIDER", "")
    if provider not in {"qwen", "gemini"}:
        return None
    if not env.get("DESK_TEXT_MODEL") or not env.get("DESK_TEXT_API_KEY"):
        return None
    if provider == "qwen" and not env.get("DESK_TEXT_ENDPOINT"):
        return None
    raw = env.get("DESK_SMOKE_MAX_TOKENS", "")
    if not str(raw).isdigit():
        return None
    cap = int(raw)
    if cap < 1 or cap > CEILING:
        return None
    return cap


def run(env, caller=None):
    cap = readiness(env)
    if cap is None:
        print("smoke skipped")
        return 0
    from desk.text_ai import TextConfig

    config = TextConfig(
        provider=env["DESK_TEXT_PROVIDER"],
        model=env["DESK_TEXT_MODEL"],
        endpoint=env.get("DESK_TEXT_ENDPOINT", ""),
        api_key=env["DESK_TEXT_API_KEY"],
    )
    if not config.valid():
        print("smoke skipped")
        return 0
    if caller is None:
        import httpx

        from desk.text_providers import text_adapter

        def caller(active, limit):
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                return text_adapter(active.provider).complete(
                    client,
                    active,
                    "Reply with a JSON object only.",
                    '{"ping":true}',
                    max_tokens=limit,
                )

    raw, _usage = caller(config, cap)
    if not isinstance(raw, str) or not raw.strip():
        print("smoke failed")
        return 1
    print("smoke ok")
    return 0


def main():
    import os

    return run(os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
