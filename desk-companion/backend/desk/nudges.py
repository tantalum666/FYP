"""Owner check-ins using the saved quiet hours and briefing preferences.

Morning briefing reuses ``daily_brief_enabled`` and ``daily_brief_time``.
The evening check-in is two more fields on that same preference record.
Task follow-ups stay in ``tasks.tick``. This module does not call a model.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from .calendar import iso
from .notify import Notice
from .store import DomainError, encode
from .workspace_data import is_quiet

WINDOW_SECONDS = 120
OPEN = {"todo", "in_progress", "waiting"}
_NUDGE_ID = re.compile(r"(?:morning_brief|evening_check)-\d{4}-\d{2}-\d{2}")


def due_kinds(prefs: dict, now_local: datetime) -> list[str]:
    """Kinds whose saved clock time is in the last two minutes, outside quiet hours."""
    if now_local.tzinfo is None or is_quiet(prefs, now_local):
        return []
    due = []
    for kind, flag, clock_key in (
        ("morning_brief", "daily_brief_enabled", "daily_brief_time"),
        ("evening_check", "evening_check_enabled", "evening_check_time"),
    ):
        clock = prefs.get(clock_key) or ""
        if not prefs.get(flag) or len(clock) != 5:
            continue
        start = now_local.replace(
            hour=int(clock[:2]), minute=int(clock[3:]), second=0, microsecond=0
        )
        elapsed = (now_local - start).total_seconds()
        if 0 <= elapsed < WINDOW_SECONDS:
            due.append(kind)
    return due


def explain(kind: str, when: str) -> dict[str, str]:
    """Why this check-in fired. The saved clock time is part of the sentence."""
    if kind == "morning_brief":
        return {
            "reason_en": (
                "Morning briefing fired because it is enabled, local time is within "
                f"two minutes of the saved briefing time {when}, and quiet hours are not in effect."
            ),
            "reason_zh": (
                "早晨简报已触发：已启用早晨简报，本地时间在已保存的简报时间 "
                f"{when} 之后的两分钟内，且当前不在安静时段。"
            ),
        }
    return {
        "reason_en": (
            "Evening check-in fired because it is enabled, local time is within "
            f"two minutes of the saved check-in time {when}, and quiet hours are not in effect."
        ),
        "reason_zh": (
            "晚间检查已触发：已启用晚间检查，本地时间在已保存的检查时间 "
            f"{when} 之后的两分钟内，且当前不在安静时段。"
        ),
    }


def _summary(kind: str, open_count: int, waiting: int, events: int) -> dict[str, str]:
    if kind == "morning_brief":
        return {
            "summary_en": (
                f"{events} calendar item(s) today. {open_count} open task(s) still followed up, "
                f"{waiting} waiting."
            ),
            "summary_zh": (
                f"今天有 {events} 项日程。仍在跟进的未完成事务 {open_count} 件，"
                f"其中等待中 {waiting} 件。"
            ),
        }
    return {
        "summary_en": (
            f"{open_count} open task(s) still followed up, {waiting} waiting. "
            "This is a check-in, not a new task reminder."
        ),
        "summary_zh": (
            f"仍在跟进的未完成事务 {open_count} 件，其中等待中 {waiting} 件。"
            "这是一次检查，不是一条新的事务提醒。"
        ),
    }


def _view(row) -> dict:
    import json

    return {
        "id": row["id"],
        "kind": row["kind"],
        "state": row["state"],
        "created_at": row["created_at"],
        **json.loads(row["content"]),
    }


class NudgeService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS owner_nudges(
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    content TEXT NOT NULL
                )"""
            )

    def tick(self) -> None:
        prefs = self.runtime.data.preferences()
        # Off stops both check-ins. Low keeps the morning briefing and skips the evening one.
        # Per-task follow-ups stay on their own switch.
        level = prefs.get("proactivity", "normal")
        if level == "off":
            return
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        now_local = self.store.clock().astimezone(zone)
        kinds = due_kinds(prefs, now_local)
        if level == "low":
            kinds = [kind for kind in kinds if kind != "evening_check"]
        if not kinds:
            return
        tasks = self.runtime.tasks.listing()["tasks"]
        open_tasks = [
            task
            for task in tasks
            if task["status"] in OPEN and task.get("follow_up_enabled", True) and not task["paused"]
        ]
        waiting = sum(task["status"] == "waiting" for task in open_tasks)
        events = 0
        if "morning_brief" in kinds:
            begin = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            events = len(self.store.snapshot(begin, begin + timedelta(days=1))["occurrences"])
        day = now_local.date().isoformat()
        pending = []
        with self.store.connection(write=True) as conn:
            wrote = False
            for kind in kinds:
                nudge_id = f"{kind}-{day}"
                if conn.execute("SELECT 1 FROM owner_nudges WHERE id=?", (nudge_id,)).fetchone():
                    continue
                when = prefs[
                    "daily_brief_time" if kind == "morning_brief" else "evening_check_time"
                ]
                content = {
                    **explain(kind, when),
                    **_summary(kind, len(open_tasks), waiting, events),
                }
                conn.execute(
                    "INSERT INTO owner_nudges VALUES(?,?,?,'open',?)",
                    (nudge_id, kind, iso(self.store.clock()), encode(content)),
                )
                self.store.record(conn, "nudge_opened", details={"kind": kind})
                title = (
                    ("Morning briefing", "早晨简报")
                    if kind == "morning_brief"
                    else ("Evening check-in", "晚间检查")
                )
                pending.append(
                    Notice(
                        nudge_id,
                        kind,
                        title[0],
                        title[1],
                        content["summary_en"],
                        content["summary_zh"],
                        content["reason_en"],
                        content["reason_zh"],
                    )
                )
                wrote = True
            if wrote:
                self.store.bump(conn)
        notifier = getattr(self.runtime, "notify", None)
        if notifier:
            for notice in pending:
                notifier.publish(notice, quiet=is_quiet(prefs, now_local))

    def listing(self) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM owner_nudges ORDER BY created_at DESC, id LIMIT 14"
            ).fetchall()
        return {"nudges": [_view(row) for row in rows]}

    def dismiss(self, nudge_id: str, key: str) -> dict:
        if not _NUDGE_ID.fullmatch(nudge_id):
            raise DomainError("NUDGE_NOT_FOUND", 404)

        def apply(conn):
            row = conn.execute("SELECT * FROM owner_nudges WHERE id=?", (nudge_id,)).fetchone()
            if not row:
                raise DomainError("NUDGE_NOT_FOUND", 404)
            if row["state"] == "dismissed":
                return {"nudge": _view(row), "saved": True}
            conn.execute("UPDATE owner_nudges SET state='dismissed' WHERE id=?", (nudge_id,))
            self.store.record(conn, "nudge_dismissed", details={"kind": row["kind"]})
            updated = conn.execute("SELECT * FROM owner_nudges WHERE id=?", (nudge_id,)).fetchone()
            return {"nudge": _view(updated), "saved": True}

        return self.store.operation(key, {"type": "nudge_dismiss", "id": nudge_id}, apply)


def nudge_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/nudges", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.nudges.listing()

    @router.post("/{nudge_id}/dismissals")
    def dismiss(nudge_id: str, key=Depends(operation_id)):
        return runtime.nudges.dismiss(nudge_id, key)

    return router
