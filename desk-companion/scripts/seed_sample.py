"""Explicit sample-calendar seed. Does not clear existing records."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.schemas import CreateEvents, EventInput  # noqa: E402
from desk.store import Store  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--week", default="2026-09-28")
parser.add_argument("--runtime", default=str(Path(__file__).resolve().parents[1] / ".runtime"))
args = parser.parse_args()
store = Store(args.runtime)
monday = datetime.fromisoformat(args.week)
samples = [
    (0, 9, 60, "Weekly planning", "study", "lavender"),
    (1, 10, 60, "Project discussion", "study", "lavender"),
    (1, 14, 90, "Design review", "personal", "blue"),
    (2, 9, 60, "Study session", "study", "sage"),
    (3, 11, 60, "Team check-in", "study", "lavender"),
    (4, 15, 60, "Reading", "personal", "peach"),
    (5, 0, 1440, "Mum's birthday", "personal", "peach"),
]
for day, hour, minutes, title, calendar, color in samples:
    start = monday + timedelta(days=day, hours=hour)
    event = EventInput(
        title=title,
        start_local=start,
        end_local=start + timedelta(minutes=minutes),
        calendar=calendar,
        color=color,
        all_day=minutes == 1440,
        reminder_minutes=[],
    )
    store.create(CreateEvents(event=event), f"sample/{args.week}/{day}/{hour}", origin="sample")
print("Example calendar seeded without replacing existing records.")
