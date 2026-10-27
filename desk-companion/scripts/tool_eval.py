"""Print a pass/fail table for every offline tool and conversation scenario.

Run from desk-companion/:

    .venv/bin/python scripts/tool_eval.py

No network. This does not call a hosted model and does not honor
DESK_CONVERSATION_EVAL. Exit 0 when every row passes, otherwise 1.
"""

import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from desk.eval_report import collect, format_table, summary
    from desk.runtime import Runtime
    from desk.store import Store

    root = Path(tempfile.mkdtemp(prefix="desk-tool-eval-"))

    def new_runtime():
        folder = root / uuid4().hex
        return Runtime(
            Store(
                folder,
                password="eval-only",
                clock=lambda: datetime(2026, 10, 27, tzinfo=UTC),
            )
        )

    rows = collect(new_runtime)
    print(format_table(rows), flush=True)
    print(summary(rows), flush=True)
    return 0 if all(row.passed for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
