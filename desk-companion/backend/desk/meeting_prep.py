"""Answer one asked question about the next saved meeting.

The reply is read from the local calendar, one related open task, and one
cited memory. It does not create, move, book, or send anything, and it does
not call a model. Quiet hours still answer, because the owner asked.
"""

import re
from datetime import datetime, timedelta

from .recall import spoken_day, zone_of

_WINDOW = timedelta(hours=36)
_LOOKBACK = timedelta(hours=12)
_STOP = {
    "about",
    "before",
    "brief",
    "call",
    "from",
    "know",
    "meeting",
    "meetings",
    "need",
    "next",
    "please",
    "prep",
    "prepare",
    "sync",
    "that",
    "this",
    "today",
    "tomorrow",
    "what",
    "with",
    "your",
    "一下",
    "什么",
    "今天",
    "开会",
    "明天",
    "准备",
    "会议",
}
_TOMORROW = re.compile(
    r"^(?:please\s+|请问)?"
    r"(?:"
    r"prep(?:are)? me for tomorrow(?:'s|s)? meeting"
    r"|明天的会要准备什么"
    r"|明天的会议要准备什么"
    r")"
    r"\s*[.!?。！？]*$",
    re.IGNORECASE,
)
_NEXT = re.compile(
    r"^(?:please\s+|请问)?"
    r"(?:"
    r"prep(?:are)? me for my next meeting"
    r"|brief me (?:for|before) my next meeting"
    r"|what should i know before my next meeting"
    r"|what do i need before my next meeting"
    r"|下一场会议要准备什么"
    r"|下一场会要准备什么"
    r"|下一场会议我该知道什么"
    r"|开会前我要准备什么"
    r")"
    r"\s*[.!?。！？]*$",
    re.IGNORECASE,
)
_BREAK = str.maketrans({char: " " for char in ".。!！?？"})


def asks_meeting_prep(text: str) -> str | None:
    """'tomorrow' or 'next' when the whole message is this question."""
    raw = " ".join(text.split())
    if _TOMORROW.match(raw):
        return "tomorrow"
    if _NEXT.match(raw):
        return "next"
    return None


def answer_meeting_prep(runtime, request, *, owner: bool = True):
    """One meeting brief, or None so the other parsers still run."""
    scope = asks_meeting_prep(getattr(request, "message", ""))
    if scope is None:
        return None
    zh = getattr(request, "language", "en") == "zh"
    zone = zone_of(runtime)
    now = runtime.store.clock().astimezone(zone)
    chosen = _meeting(runtime, now, zone, scope, owner)
    task = None
    memory = None
    if chosen is not None and not chosen["redacted"] and chosen["title"]:
        task = _related_task(runtime, chosen["title"], owner)
        if owner:
            memory = _related_memory(runtime, chosen["title"], zone, zh)
    parts = [_lead(chosen, scope, zh), *_extras(chosen, task, memory, zh)]
    return {
        "mode": "local_rules",
        "kind": "meeting_prep",
        "saved": False,
        "acted": False,
        "message": _join(parts, zh),
        "meeting_prep": {
            "asked": scope,
            "scope": scope if chosen else "none",
            "title": "" if chosen is None or chosen["redacted"] else chosen["title"],
            "clock": "" if chosen is None else chosen["clock"],
            "until": "" if chosen is None else chosen["until"],
            "date": "" if chosen is None else chosen["date"],
            "location": "" if chosen is None or chosen["redacted"] else chosen["location"],
            "note": "" if chosen is None or chosen["redacted"] else chosen["note"],
            "underway": bool(chosen and chosen["underway"]),
            "redacted": bool(chosen and chosen["redacted"]),
            "task_title": "" if task is None else task["title"],
            "task_step": "" if task is None else task["step"],
            "memory_body": "" if memory is None else memory["body"],
            "memory_day": "" if memory is None else memory["day"],
            "event_id": "" if chosen is None or not owner else chosen["id"],
            "acted": False,
        },
    }


def _meeting(runtime, now, zone, scope, owner):
    if scope == "tomorrow":
        day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        begin, end = day, day + timedelta(days=1)
    else:
        begin, end = now - _LOOKBACK, now + _WINDOW
    chosen = None
    for item in runtime.store.snapshot(begin, end)["occurrences"]:
        if item.get("all_day") or item.get("completed") or item.get("busy") is False:
            continue
        start, finish = _aware(item.get("start")), _aware(item.get("end"))
        if start is None or finish is None or finish <= now:
            continue
        local_start = start.astimezone(zone)
        if scope == "tomorrow":
            if local_start.date() != begin.date():
                continue
        elif start > now + _WINDOW:
            continue
        rank = (start, str(item.get("id") or ""))
        if chosen is None or rank < chosen[0]:
            chosen = (rank, item, _hidden(item, owner), start, finish, local_start)
    if chosen is None:
        return None
    _, item, hidden, start, finish, local_start = chosen
    return {
        "id": str(item.get("id") or ""),
        "title": "" if hidden else _plain(item.get("title"), 160),
        "clock": local_start.strftime("%H:%M"),
        "until": finish.astimezone(zone).strftime("%H:%M"),
        "date": local_start.date().isoformat(),
        "location": "" if hidden else _plain(item.get("location"), 80),
        "note": "" if hidden else _plain(item.get("notes"), 80),
        "underway": start <= now < finish,
        "redacted": hidden,
    }


def _related_task(runtime, title, owner):
    matches = []
    for task in runtime.tasks.listing()["tasks"]:
        if _task_hidden(task, owner):
            continue
        task_title = _plain(task.get("title"), 160)
        if not task_title or not _shares(title, task_title):
            continue
        step = _plain(task.get("next_step"), 160)
        matches.append((0 if step else 1, task_title, step))
    if not matches:
        return None
    _, task_title, step = sorted(matches, key=lambda item: item[0])[0]
    return {"title": task_title, "step": step}


def _related_memory(runtime, title, zone, zh):
    for row in runtime.memory.active_facts():
        body = _plain(row.get("body"), 160)
        if body and _shares(title, body):
            return {"body": body, "day": spoken_day(row["created_at"], zone, zh)}
    return None


def _lead(chosen, scope, zh):
    if chosen is None:
        if scope == "tomorrow":
            return "明天没有定时会议，我还没有新增" if zh else (
                "There is no timed meeting tomorrow, and I have not added one"
            )
        return "接下来一天半没有定时会议，我还没有新增" if zh else (
            "There is no timed meeting in the next day and a half, and I have not added one"
        )
    if chosen["redacted"] or not chosen["title"]:
        if chosen["underway"]:
            return (
                f"一场私人会议正在进行，直到 {chosen['until']}，标题保持隐藏，我还没有改动日历"
                if zh
                else (
                    f"A private meeting is underway until {chosen['until']}, "
                    "and I have not changed the calendar"
                )
            )
        return (
            f"下一场是 {chosen['clock']} 的私人会议，标题保持隐藏，我还没有改动日历"
            if zh
            else (
                f"A private meeting is next at {chosen['clock']}, "
                "and I have not changed the calendar"
            )
        )
    place = ""
    if chosen["location"]:
        place = f"，地点{chosen['location']}" if zh else f" in {chosen['location']}"
    title, clock = chosen["title"], chosen["clock"]
    if chosen["underway"]:
        return (
            f"{title}正在进行，直到 {chosen['until']}{place}，我还没有改动日历"
            if zh
            else (
                f"{title} is underway until {chosen['until']}{place}, "
                "and I have not changed the calendar"
            )
        )
    if scope == "tomorrow":
        return (
            f"明天的会议是 {chosen['date']} {clock} 的{title}{place}，我还没有改动日历"
            if zh
            else (
                f"Tomorrow's meeting is {title} at {clock} on {chosen['date']}{place}, "
                "and I have not changed the calendar"
            )
        )
    return (
        f"下一场会议是 {clock} 的{title}{place}，我还没有改动日历"
        if zh
        else (
            f"The next meeting is {title} at {clock}{place}, "
            "and I have not changed the calendar"
        )
    )


def _extras(chosen, task, memory, zh):
    lines = []
    if chosen is not None and chosen["note"] and chosen["note"] != chosen["title"]:
        lines.append(f"记下的备注是{chosen['note']}" if zh else f"The saved note says {chosen['note']}")
    if task is not None:
        if task["step"]:
            lines.append(
                f"未完成的事务「{task['title']}」仍写着{task['step']}"
                if zh
                else f"The open task “{task['title']}” still says {task['step']}"
            )
        else:
            lines.append(
                f"未完成的事务「{task['title']}」仍未完成"
                if zh
                else f"The open task “{task['title']}” is still open"
            )
    if memory is not None:
        lines.append(
            f"你在{memory['day']}告诉我：{memory['body']}"
            if zh
            else f"You told me on {memory['day']}: {memory['body']}"
        )
    return lines


def _join(parts, zh):
    clean = [part.strip().rstrip(".。") for part in parts if part and part.strip()]
    if zh:
        return "。".join(clean) + "。"
    return ". ".join(clean) + "."


def _hidden(item, owner):
    if item.get("redacted"):
        return True
    if owner:
        return False
    return item.get("visibility") != "displayable"


def _task_hidden(task, owner):
    if task.get("redacted"):
        return True
    if owner:
        return False
    return task.get("visibility") != "displayable"


def _shares(event_title, other):
    if _latin(event_title) & _latin(other):
        return True
    folded = "".join(re.findall(r"[\u4e00-\u9fff]", other))
    for run in re.findall(r"[\u4e00-\u9fff]+", event_title):
        sizes = (len(run),) if len(run) < 3 else (len(run), 2)
        for size in sizes:
            for index in range(0, len(run) - size + 1):
                piece = run[index : index + size]
                if piece not in _STOP and piece in folded:
                    return True
    return False


def _latin(text):
    return {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text)
        if word.casefold() not in _STOP
    }


def _plain(value, limit):
    return " ".join(str(value or "").translate(_BREAK).split())[:limit].rstrip()


def _aware(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed
