"""One next step when the calendar has a real gap, or one open loop when it does not.

A free slot is only unoccupied saved time. With no timed event in the next
30 to 180 minutes, one unanswered follow-up, a goal due within seven days,
or a task quiet for two days can be suggested. Dismissing the same kind
three times pauses that kind until the owner resets the list. Quiet hours
and a low or off proactivity setting produce nothing. No model call.
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
NEAR_HOURS = 24 * 7
STALE_DAYS = 2
_OPEN = {"todo", "in_progress", "waiting"}


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
        free_paused = sum(row["kind"] == "free_time" for row in rows) >= PAUSE_AFTER
        loops_paused = sum(row["kind"] == "open_loop" for row in rows) >= PAUSE_AFTER
        ctx = self._context()
        suggestion, gap = None, None
        if ctx is not None:
            now, gap = ctx
            suggestion = self._suggest(now, gap, dismissed, free_paused, loops_paused)
        paused = ctx is not None and suggestion is None and (
            (gap is not None and free_paused) or (gap is None and loops_paused)
        )
        if paused and gap is not None:
            reason = (
                "Free-time suggestions are paused after three dismissals. "
                "Reset to allow them again."
            )
            reason_zh = "空隙建议已因三次关闭而暂停。清空后才会再出现。"
        elif paused:
            reason = (
                "Open-loop suggestions are paused after three dismissals. "
                "Reset to allow them again."
            )
            reason_zh = "未完成事项的建议已因三次关闭而暂停。清空后才会再出现。"
        else:
            reason, reason_zh = "", ""
        return {
            "suggestion": suggestion,
            "dismissals": [dict(row) for row in rows],
            "paused": paused,
            "pause_reason_en": reason,
            "pause_reason_zh": reason_zh,
        }

    def _context(self):
        prefs = self.runtime.data.preferences()
        if prefs.get("proactivity") in {"off", "low"}:
            return None
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        now = self.store.clock().astimezone(zone)
        if is_quiet(prefs, now):
            return None
        window = self.store.snapshot(now, now + timedelta(hours=8))
        return now, free_gap(window["occurrences"], now)

    def _suggest(self, now, gap, dismissed, free_paused, loops_paused):
        if gap is not None:
            if free_paused:
                return None
            return self._free(now, gap, dismissed)
        if loops_paused:
            return None
        return self._loop(now, dismissed)

    def _free(self, now, gap, dismissed: set[str]) -> dict | None:
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

    def _loop(self, now, dismissed: set[str]) -> dict | None:
        day = now.date().isoformat()
        for subtype, target_id, title in self._open_loops(now):
            suggestion_id = f"loop-{day}-{subtype}-{target_id}"[:80]
            if suggestion_id in dismissed:
                continue
            why = {
                "followup": (
                    f"“{title}” still has an unanswered follow-up.",
                    f"「{title}」还有一条未回复的跟进。",
                ),
                "goal": (
                    f"“{title}” is due within seven days.",
                    f"「{title}」将在七天内到期。",
                ),
                "stale": (
                    f"“{title}” has not been updated for at least two days.",
                    f"「{title}」至少两天没有更新。",
                ),
            }[subtype]
            return {
                "id": suggestion_id,
                "kind": "open_loop",
                "target_id": target_id,
                "title": title,
                "minutes": None,
                "reason_en": (
                    f"{why[0]} No timed event falls in the next 30 to 180 minutes, "
                    "so this is one open loop, not a claim that you are free."
                ),
                "reason_zh": (
                    f"{why[1]}接下来 30 到 180 分钟内没有定时日程，"
                    "所以这只是一条未完成事项，不是说你现在有空。"
                ),
            }
        return None

    def _open_loops(self, now) -> list[tuple[str, str, str]]:
        tasks = self.runtime.tasks.listing()["tasks"]
        found = []
        for task in tasks:
            if task.get("followup") and task["status"] in _OPEN and task["title"]:
                found.append(("followup", task["id"], task["title"]))
        for goal in self.runtime.goals.listing()["goals"]:
            due = _aware(goal["due_at"]) if goal.get("due_at") else None
            if (
                goal["state"] != "closed"
                and goal["title"]
                and due is not None
                and timedelta(0) <= due - now <= timedelta(hours=NEAR_HOURS)
            ):
                found.append(("goal", goal["id"], goal["title"]))
        for task in tasks:
            updated = _aware(task.get("updated_at") or "")
            if (
                task["status"] in _OPEN
                and task["title"]
                and not task.get("followup")
                and updated is not None
                and now - updated >= timedelta(days=STALE_DAYS)
            ):
                found.append(("stale", task["id"], task["title"]))
        return found

    def dismiss(self, suggestion_id: str, key: str) -> dict:
        current = self.view()["suggestion"]
        if current is None or current["id"] != suggestion_id:
            raise DomainError("SUGGESTION_NOT_FOUND", 404)

        def apply(conn):
            conn.execute(
                "INSERT OR IGNORE INTO suggestion_dismissals VALUES(?,?,?,?)",
                (suggestion_id, current["kind"], current["target_id"], iso(self.store.clock())),
            )
            self.store.record(conn, "suggestion_dismissed", details={"kind": current["kind"]})
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
