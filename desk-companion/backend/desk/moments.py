"""One next step when the calendar has a real gap. No model call.

A free slot is only unoccupied saved time. Dismissing the same kind three
times pauses it until the owner resets the list. Quiet hours and a low or
off proactivity setting produce nothing.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError
from .workspace_data import is_quiet

PAUSE_AFTER = 3


def _aware(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo("UTC"))


def free_gap(occurrences: list[dict], now: datetime) -> dict | None:
    """Minutes until the next timed event, when that gap is 30 to 180 minutes."""
    upcoming = []
    for item in occurrences:
        if item.get("all_day"):
            continue
        start, end = _aware(item.get("start") or ""), _aware(item.get("end") or "")
        if start is None or end is None or end <= now:
            continue
        upcoming.append((start, item))
    if not upcoming:
        return None
    start, item = min(upcoming, key=lambda pair: pair[0])
    minutes = int((start - now).total_seconds() // 60)
    if minutes < 30 or minutes > 180:
        return None
    hidden = bool(item.get("redacted")) or not item.get("title")
    return {"minutes": minutes, "title": "" if hidden else item["title"], "hidden": hidden}


class DismissInput(StrictModel):
    id: str = Field(min_length=8, max_length=80)


class MomentService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS suggestion_dismissals(
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )

    def _dismissed(self, conn) -> set[str]:
        return {row["id"] for row in conn.execute("SELECT id FROM suggestion_dismissals")}

    def _targets(self) -> list[tuple[str, str]]:
        goals = [
            ("goal", goal["id"], goal["title"])
            for goal in self.runtime.goals.listing()["goals"]
            if goal["state"] != "closed" and goal["title"]
        ]
        if goals:
            return [(item[1], item[2]) for item in goals]
        tasks = [
            (task["id"], task["title"])
            for task in self.runtime.tasks.listing()["tasks"]
            if task["status"] in {"todo", "in_progress", "waiting"} and task["title"]
        ]
        return tasks

    def view(self) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id, kind, target_id, created_at FROM suggestion_dismissals ORDER BY created_at, id"
            ).fetchall()
            dismissed = {row["id"] for row in rows}
        pauses = sum(row["kind"] == "free_time" for row in rows)
        paused = pauses >= PAUSE_AFTER
        suggestion = None if paused else self._current(dismissed)
        reason = (
            "Free-time suggestions are paused after three dismissals. Reset to allow them again."
            if paused
            else ""
        )
        reason_zh = "空隙建议已因三次关闭而暂停。清空后才会再出现。" if paused else ""
        return {
            "suggestion": suggestion,
            "dismissals": [dict(row) for row in rows],
            "paused": paused,
            "pause_reason_en": reason,
            "pause_reason_zh": reason_zh,
        }

    def _current(self, dismissed: set[str]) -> dict | None:
        prefs = self.runtime.data.preferences()
        if prefs.get("proactivity") in {"off", "low"}:
            return None
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        now = self.store.clock().astimezone(zone)
        if is_quiet(prefs, now):
            return None
        window = self.store.snapshot(now, now + timedelta(hours=8))
        gap = free_gap(window["occurrences"], now)
        if gap is None:
            return None
        day = now.date().isoformat()
        for target_id, title in self._targets():
            suggestion_id = f"free-{day}-{target_id}"[:80]
            if suggestion_id in dismissed:
                continue
            event = "a private event" if gap["hidden"] else gap["title"]
            event_zh = "一项私人事项" if gap["hidden"] else gap["title"]
            return {
                "id": suggestion_id,
                "kind": "free_time",
                "target_id": target_id,
                "title": title,
                "minutes": gap["minutes"],
                "reason_en": (
                    f"You have {gap['minutes']} free minutes before {event}. "
                    f"The open item “{title}” could start then. "
                    "A free calendar slot is not proof you are actually free."
                ),
                "reason_zh": (
                    f"距离{event_zh}还有 {gap['minutes']} 分钟空档。"
                    f"未完成的「{title}」可以在这时开始。"
                    "日历上的空档不等于你真的有空。"
                ),
            }
        return None

    def dismiss(self, suggestion_id: str, key: str) -> dict:
        current = self.view()["suggestion"]
        if current is None or current["id"] != suggestion_id:
            raise DomainError("SUGGESTION_NOT_FOUND", 404)

        def apply(conn):
            conn.execute(
                "INSERT OR IGNORE INTO suggestion_dismissals VALUES(?,?,?,?)",
                (suggestion_id, "free_time", current["target_id"], iso(self.store.clock())),
            )
            self.store.record(conn, "suggestion_dismissed", details={"kind": "free_time"})
            return {"saved": True}

        self.store.operation(key, {"type": "suggestion_dismiss", "id": suggestion_id}, apply)
        return self.view()

    def reset(self, key: str) -> dict:
        def apply(conn):
            conn.execute("DELETE FROM suggestion_dismissals")
            self.store.record(conn, "suggestion_reset", details={})
            return {"saved": True}

        self.store.operation(key, {"type": "suggestion_reset"}, apply)
        return self.view()


def moment_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/moments", dependencies=[Depends(owner)])

    @router.get("")
    def view():
        return runtime.moments.view()

    @router.post("/dismissals")
    def dismiss(payload: DismissInput, key=Depends(operation_id)):
        return runtime.moments.dismiss(payload.id, key)

    @router.post("/reset")
    def reset(key=Depends(operation_id)):
        return runtime.moments.reset(key)

    return router
