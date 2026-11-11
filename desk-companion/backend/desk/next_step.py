"""One local answer when the owner asks Alice what to do next.

The question is read from the calendar, the selected task, and open goals.
It does not create a task, a draft, a notice, or a model call. Quiet hours and
a low proactivity setting still answer, because the owner asked.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .store import DomainError

_OPEN = {"todo", "in_progress", "waiting"}
_ASK = re.compile(
    r"^(?:please\s+|请问)?"
    r"(?:"
    r"what should i do(?: next)?"
    r"|what do i do next"
    r"|what(?:'s| is) (?:my |the )?next step"
    r"|what(?:'s| is) next"
    r"|next step"
    r"|接下来(?:做什么|呢)"
    r"|我(?:现在)?该做什么"
    r"|下一步(?:是什么|做什么)"
    r"|现在做什么"
    r")"
    r"\s*[.!?。！？]*$",
    re.IGNORECASE,
)


def asks_next_step(text: str) -> bool:
    """True only for the whole question, not a calendar or task command."""
    return bool(_ASK.match(text.strip()))


def answer_next_step(runtime, request, *, owner: bool = True):
    """A spoken next step, or None when this message is a different request."""
    if not asks_next_step(request.message):
        return None
    zh = request.language == "zh"
    step = _choose(runtime, getattr(request, "task_id", None), owner=owner)
    return {
        "mode": "local_rules",
        "kind": "next_step",
        "saved": False,
        "acted": False,
        "message": step["sentence_zh"] if zh else step["sentence_en"],
        "next_step": {
            "source": step["source"],
            "title": step["title"],
            "detail": step["detail"],
            "reason_en": step["reason_en"],
            "reason_zh": step["reason_zh"],
            "redacted": step["redacted"],
            "acted": False,
            **({"target_id": step["target_id"]} if step.get("target_id") else {}),
        },
    }


def _choose(runtime, task_id: str | None, *, owner: bool) -> dict:
    zone = _zone(runtime)
    now = _now(runtime)
    if task_id:
        selected = _selected(runtime, task_id, owner=owner)
        if selected is not None:
            return selected
    event = _event(runtime, now, zone, owner=owner)
    if event is not None:
        return event
    task = _open_task(runtime, owner=owner)
    if task is not None:
        return task
    goal = _goal(runtime, zone) if owner else None
    if goal is not None:
        return goal
    return _none()


def _selected(runtime, task_id: str, *, owner: bool):
    try:
        task = runtime.tasks.detail(task_id)["task"]
    except DomainError as error:
        if error.code == "PRIVATE_TASK_HIDDEN":
            return _private_task()
        raise
    if _task_hidden(task, owner):
        return _private_task()
    if task["status"] not in _OPEN:
        return None
    if (task.get("next_step") or "").strip():
        return _task_step(task)
    if (task.get("waiting_for") or "").strip():
        return _waiting(task)
    return None


def _event(runtime, now: datetime, zone: ZoneInfo, *, owner: bool):
    window = runtime.store.snapshot(now - timedelta(hours=6), now + timedelta(hours=24))
    chosen = None
    for item in window["occurrences"]:
        if item.get("all_day"):
            continue
        start, end = _aware(item.get("start") or ""), _aware(item.get("end") or "")
        if start is None or end is None or end <= now or start > now + timedelta(hours=24):
            continue
        hidden = _event_hidden(item, owner)
        if hidden and not owner:
            continue
        if chosen is None or start < chosen[0]:
            chosen = (start, item, hidden)
    if chosen is None:
        return None
    start, item, hidden = chosen
    clock = start.astimezone(zone).strftime("%H:%M")
    if hidden:
        return {
            "source": "calendar",
            "title": "",
            "detail": clock,
            "redacted": True,
            "target_id": "",
            "reason_en": ("It is the soonest timed event in the next day. The title stays hidden."),
            "reason_zh": "这是接下来一天里最近的定时日程。标题保持隐藏。",
            "sentence_en": (
                f"A private event is next at {clock}, because it is the soonest timed event "
                "in the next day, and I have not changed the calendar."
            ),
            "sentence_zh": (
                f"接下来一天里最近的是 {clock} 的一项私人日程，标题保持隐藏，我还没有改动日历。"
            ),
        }
    title = _plain(item.get("title") or "")
    return {
        "source": "calendar",
        "title": title,
        "detail": clock,
        "redacted": False,
        "target_id": item.get("id") or "",
        "reason_en": "It is the soonest timed event in the next day.",
        "reason_zh": "这是接下来一天里最近的定时日程。",
        "sentence_en": (
            f"The next timed event is {title} at {clock}, because it is the soonest "
            "event in the next day, and I have not changed the calendar."
        ),
        "sentence_zh": (f"接下来一天里最近的定时日程是 {clock} 的{title}，我还没有改动日历。"),
    }


def _open_task(runtime, *, owner: bool):
    for task in runtime.tasks.listing()["tasks"]:
        if _task_hidden(task, owner):
            continue
        if (task.get("next_step") or "").strip():
            return _task_step(task)
    for task in runtime.tasks.listing()["tasks"]:
        if _task_hidden(task, owner):
            continue
        if (task.get("waiting_for") or "").strip():
            return _waiting(task)
    return None


def _goal(runtime, zone: ZoneInfo):
    goals = [
        goal
        for goal in runtime.goals.listing()["goals"]
        if goal["state"] != "closed" and goal.get("due_at") and goal.get("title")
    ]
    if not goals:
        return None
    goal = min(goals, key=lambda item: (item["due_at"], item["id"]))
    due = _due_label(goal["due_at"], zone)
    title = _plain(goal["title"])
    return {
        "source": "goal",
        "title": title,
        "detail": due,
        "redacted": False,
        "target_id": goal["id"],
        "reason_en": "That due date is saved on the open goal.",
        "reason_zh": "这个到期日保存在未完成的目标上。",
        "sentence_en": (
            f"The open goal “{title}” is due on {due}, because that date is saved, "
            "and I have not closed it."
        ),
        "sentence_zh": (f"未完成的目标「{title}」的到期日是 {due}，我还没有把它标成完成。"),
    }


def _task_step(task: dict) -> dict:
    title, step = _plain(task["title"]), _plain(task["next_step"])
    return {
        "source": "task",
        "title": title,
        "detail": step,
        "redacted": False,
        "target_id": task["id"],
        "reason_en": "That step is saved on the task, and the task is still open.",
        "reason_zh": "这一步保存在事务上，而这件事务仍未完成。",
        "sentence_en": (
            f"The saved next step on “{title}” is {step}, because that task is still open, "
            "and I have not done it."
        ),
        "sentence_zh": (f"「{title}」上保存的下一步是{step}，因为这件事仍未完成，我还没有去做。"),
    }


def _waiting(task: dict) -> dict:
    title, who = _plain(task["title"]), _plain(task["waiting_for"])
    return {
        "source": "waiting",
        "title": title,
        "detail": who,
        "redacted": False,
        "target_id": task["id"],
        "reason_en": "That waiting reason is saved on the open task.",
        "reason_zh": "这个等待原因保存在未完成的事务上。",
        "sentence_en": (
            f"“{title}” is waiting on {who}, because that reason is saved, "
            "and I have not changed it."
        ),
        "sentence_zh": (f"「{title}」仍在等待{who}，因为这是已保存的等待原因，我还没有改动。"),
    }


def _private_task() -> dict:
    return {
        "source": "private",
        "title": "",
        "detail": "",
        "redacted": True,
        "reason_en": "The selected task is private, so the saved step stays hidden.",
        "reason_zh": "选中的事务是私人的，已保存的下一步保持隐藏。",
        "sentence_en": (
            "That task is private, so its next step stays hidden, and I have not read or done it."
        ),
        "sentence_zh": "这件事是私人的，下一步保持隐藏，我没有读取，也没有去做。",
    }


def _none() -> dict:
    return {
        "source": "none",
        "title": "",
        "detail": "",
        "redacted": False,
        "reason_en": "No timed event in the next day, and no open task has a saved next step.",
        "reason_zh": "接下来一天没有定时日程，也没有未完成事务保存了下一步。",
        "sentence_en": (
            "Nothing in the next day is on the calendar, and no open task has a saved next step, "
            "so I have not created one."
        ),
        "sentence_zh": (
            "接下来一天的日历上没有定时日程，也没有未完成事务保存了下一步，所以我没有新建任何事项。"
        ),
    }


def _task_hidden(task: dict, owner: bool) -> bool:
    if task.get("redacted"):
        return True
    return not owner and task.get("visibility") == "private"


def _event_hidden(item: dict, owner: bool) -> bool:
    if item.get("redacted"):
        return True
    return not owner and item.get("visibility") == "private"


def _zone(runtime) -> ZoneInfo:
    with runtime.store.connection() as conn:
        return ZoneInfo(runtime.store.settings(conn)["timezone"])


def _now(runtime) -> datetime:
    now = runtime.store.clock()
    if now.tzinfo is None:
        return now.replace(tzinfo=ZoneInfo("UTC"))
    return now


def _aware(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed


def _due_label(value: str, zone: ZoneInfo) -> str:
    parsed = _aware(value)
    if parsed is None:
        return value[:10]
    return parsed.astimezone(zone).date().isoformat()


def _plain(value: str) -> str:
    return " ".join(str(value).split())[:160]
