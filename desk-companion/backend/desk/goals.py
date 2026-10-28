"""Goals the owner stated. Confirming a draft tracks one; nothing closes itself.

A goal is a task with a saved promise. Follow-up uses the task check time.
Closing prepares the same completion draft the owner already confirms by hand.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from .calendar import iso
from .store import DomainError
from .tasks import TaskAction, TaskInput

_OPENING = re.compile(
    r"^(?:goal|promise|i will|i promise to|目标|承诺|我要)\s*[:：]?\s*(.+)$",
    re.I | re.S,
)
_BY_SUFFIX = re.compile(
    r"\s+(?:by|before)\s+([a-z]+|\d{4}-\d{2}-\d{2})\s*$",
    re.I,
)
_BY_PREFIX = re.compile(
    r"^(星期[一二三四五六日天]|周[一二三四五六日天]|\d{4}-\d{2}-\d{2})前\s*(.+)$"
)
_DONE = re.compile(r"^(?:done with|finished|完成了)\s*[:：]\s*(.+)$", re.I | re.S)
_DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "周一": 0,
    "周二": 1,
    "周三": 2,
    "周四": 3,
    "周五": 4,
    "周六": 5,
    "周日": 6,
    "星期天": 6,
    "星期日": 6,
    "星期一": 0,
    "星期二": 1,
    "星期三": 2,
    "星期四": 3,
    "星期五": 4,
    "星期六": 5,
}


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _due_on(day, now_local: datetime) -> datetime | None:
    due = now_local.replace(year=day.year, month=day.month, day=day.day, hour=18, minute=0, second=0, microsecond=0)
    return due if due > now_local else None


def _weekday_due(name: str, now_local: datetime) -> datetime | None:
    index = _DAYS.get(name.lower()) if name.isascii() else _DAYS.get(name)
    if index is None:
        return None
    ahead = (index - now_local.weekday()) % 7
    if ahead == 0 and now_local.hour >= 18:
        ahead = 7
    return _due_on(now_local.date() + timedelta(days=ahead), now_local)


def _date_due(text: str, now_local: datetime) -> datetime | None:
    try:
        day = datetime.fromisoformat(text).date()
    except ValueError:
        return None
    return _due_on(day, now_local)


def parse_goal(text: str, now_local: datetime) -> dict | None:
    """Pull a title and an optional local due time from one stated promise."""
    raw = text.strip()
    title, token = "", ""
    body = raw
    for lead in ("目标：", "目标:", "承诺：", "承诺:", "我要"):
        if body.startswith(lead):
            body = body[len(lead) :].strip()
            break
    prefixed = _BY_PREFIX.match(body) if body != raw else None
    if prefixed:
        token, title = prefixed.group(1), _collapse(prefixed.group(2))
    else:
        opened = _OPENING.match(raw)
        if not opened:
            return None
        title = _collapse(opened.group(1))
        suffix = _BY_SUFFIX.search(title)
        if suffix:
            token = suffix.group(1)
            title = _collapse(title[: suffix.start()])
    if not title or len(title) > 160:
        return None
    due = None
    if token:
        due = _date_due(token, now_local) if token[:4].isdigit() else _weekday_due(token, now_local)
    return {"title": title, "due_local": due}


def parse_done(text: str) -> str | None:
    matched = _DONE.match(text.strip())
    if not matched:
        return None
    title = _collapse(matched.group(1))
    return title if title and len(title) <= 160 else None


class GoalService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS owner_goals(
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    due_at TEXT,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )

    def _zone(self, conn):
        return ZoneInfo(self.store.settings(conn)["timezone"])

    def record(self, task_id: str, title: str, due_at: str | None) -> dict:
        now = iso(self.store.clock())
        with self.store.connection(write=True) as conn:
            if conn.execute("SELECT COUNT(*) FROM owner_goals").fetchone()[0] >= 100:
                raise DomainError("GOAL_LIMIT", 422)
            conn.execute(
                "INSERT OR IGNORE INTO owner_goals VALUES(?,?,?,?, 'open', ?)",
                (task_id, task_id, title, due_at, now),
            )
            self.store.record(conn, "goal_opened", details={"task_id": task_id})
        return self.listing()

    def close_for_task(self, task_id: str) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE owner_goals SET state='closed' WHERE task_id=? AND state!='closed'",
                (task_id,),
            )

    def listing(self) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM owner_goals ORDER BY created_at, id"
            ).fetchall()
        goals = []
        for row in rows:
            task = self.runtime.tasks.detail(row["task_id"])["task"]
            goals.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "due_at": row["due_at"],
                    "state": "closed" if task["status"] not in {"todo", "in_progress", "waiting"} else row["state"],
                    "task_id": row["task_id"],
                    "task_status": task["status"],
                }
            )
        return {"goals": goals}

    def turn(self, request, key, *, allow=True):
        """A reviewable task draft for a stated goal, or None when this is not one."""
        if not allow:
            return None
        text, zh = request.message.strip(), request.language == "zh"
        with self.store.connection() as conn:
            zone = self._zone(conn)
        now_local = self.store.clock().astimezone(zone)
        done = parse_done(text)
        if done:
            matches = [
                goal
                for goal in self.listing()["goals"]
                if goal["state"] != "closed" and goal["title"].casefold() == done.casefold()
            ]
            if len(matches) != 1:
                return {
                    "mode": "local_rules",
                    "kind": "clarify",
                    "message": "没有找到同名的未完成目标。" if zh else "No open goal has that exact title.",
                }
            return self.ask_close(matches[0]["id"], key, zh=zh)
        parsed = parse_goal(text, now_local)
        if not parsed:
            return None
        due = parsed["due_local"]
        check = None
        if due is not None:
            morning = due.replace(hour=9)
            if morning > now_local:
                check = morning.strftime("%Y-%m-%dT%H:%M")
        task = {
            "title": parsed["title"],
            "timezone": zone.key,
            "due_local": due.strftime("%Y-%m-%dT%H:%M") if due else None,
            "check_in_local": check,
            "follow_up_enabled": True,
            "visibility": "private",
        }
        TaskInput.model_validate(task)
        result = self.runtime.assistant.propose(
            "task_create",
            {
                "task": task,
                "goal": True,
                "goal_title": parsed["title"],
                "due_at": iso(due.astimezone(ZoneInfo("UTC"))) if due else None,
            },
            key,
        )
        when = task["due_local"] or ("无截止时间" if zh else "no deadline")
        return {
            "mode": "local_rules",
            "kind": "draft",
            **result,
            "message": (
                f"请确认后才会跟踪「{parsed['title']}」。截止 {when}。到期不会自动结束。"
                if zh
                else (
                    f"Confirm to track “{parsed['title']}”. Due {when}. "
                    "It will not close on its own."
                )
            ),
        }

    def ask_close(self, goal_id: str, key: str, *, zh=False) -> dict:
        goals = [goal for goal in self.listing()["goals"] if goal["id"] == goal_id]
        if len(goals) != 1 or goals[0]["state"] == "closed":
            raise DomainError("GOAL_NOT_FOUND", 404)
        goal = goals[0]
        task = self.runtime.tasks.detail(goal["task_id"])["task"]
        result = self.runtime.assistant.propose(
            "task_change",
            {
                "task_id": goal["task_id"],
                "goal": True,
                "change": TaskAction(
                    action="complete", expected_version=task["version"]
                ).model_dump(mode="json"),
            },
            key,
        )
        return {
            "mode": "local_rules",
            "kind": "draft",
            **result,
            "message": (
                "确认后才会结束这个目标。" if zh else "Confirm before this goal is closed."
            ),
        }

    def tick(self) -> None:
        """After a due time, ask once per local day. Never mark the goal done here."""
        now = self.store.clock()
        with self.store.connection() as conn:
            zone = self._zone(conn)
            rows = conn.execute(
                "SELECT * FROM owner_goals WHERE state='open' AND due_at IS NOT NULL AND due_at<=?",
                (iso(now),),
            ).fetchall()
        day = now.astimezone(zone).date().isoformat()
        for row in rows:
            try:
                self.ask_close(row["id"], f"goal-close-{row['id']}-{day}")
            except DomainError:
                continue


def goal_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/goals", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.goals.listing()

    @router.post("/{goal_id}/close-drafts")
    def close_draft(goal_id: str, key=Depends(operation_id)):
        return runtime.goals.ask_close(goal_id, key)

    return router
