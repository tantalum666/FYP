"""Optional live conversation eval. Refuses to run unless every gate is explicit.

This file is not imported by pytest and must not be wired into CI.
A run needs DESK_CONVERSATION_EVAL=1, a configured text provider, and
DESK_CONVERSATION_EVAL_CAP set to an integer from 1 to 24. The cap counts
provider completions and is checked before each call. Each case uses a fresh
temporary runtime, not the owner's desk database.
"""

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from desk.conversation_eval import live_enabled, parse_cap, run_capped

    enabled, reason = live_enabled(os.environ)
    if not enabled:
        print(f"Refusing: {reason}", flush=True)
        return 2
    cap = parse_cap(os.environ.get("DESK_CONVERSATION_EVAL_CAP"))
    from desk.app import create_app
    from desk.model_provider import HostedTextProvider

    def new_runtime():
        directory = tempfile.mkdtemp(prefix="desk-conversation-")
        app = create_app(directory, password="eval-only", scheduler=False)
        return app.state.runtime

    def bind(runtime):
        provider = HostedTextProvider(runtime.text_ai.generate)
        return provider.complete

    results, used = run_capped(new_runtime, bind, cap)
    print(f"conversation eval: used {used}/{cap} provider calls", flush=True)
    failed = 0
    for result in results:
        label = "pass" if result.passed and not result.detail else result.detail or "pass"
        if not result.passed:
            failed += 1
            label = "fail: " + result.detail
        print(f"{result.name}: {label}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
