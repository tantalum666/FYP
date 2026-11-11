"""Answer who the owner still needs to reply to, and hold one until they allow it.

A reply owed is the owner's own unanswered note. It is not someone they are
waiting on, and it is not a message that gets sent. Tasks already store open
work. This slice reads and drafts those tasks. Nothing here sends mail, buys,
books, or marks a task complete. Runtime.tick does not approve a draft.
"""

import re
from datetime import datetime

from pydantic import ValidationError

from .calendar import wall_to_utc
from .store import DomainError
from .tasks import OPEN, TaskInput

_ASK_EN = re.compile(
    r"^(?:please\s+)?"
    r"(?:"
    r"who\s+do\s+i\s+(?:still\s+)?(?:need|have)\s+to\s+reply\s+to"
    r"|who\s+should\s+i\s+(?:still\s+)?reply\s+to"
    r"|who\s+am\s+i\s+supposed\s+to\s+reply\s+to"
    r"|who\s+do\s+i\s+(?:still\s+)?owe\s+a\s+reply(?:\s+to)?"
    r"|what\s+replies\s+do\s+i\s+(?:still\s+)?owe"
    r")\s*[.!?]*$",
    re.I,
)
_ASK_ZH = re.compile(
    r"^(?:请问)?(?:"
    r"我(?:还)?(?:该|需要|应当)回复谁"
    r"|还有谁等我回复"
    r"|谁等我回复"
    r"|我还欠谁(?:的)?回复"
    r")(?:呢|啊)?\s*[？?！!。]*$"
)
_NEED_EN = re.compile(
    r"^(?:please\s+)?(?:"
    r"i\s+(?:need|have|ought)\s+to\s+reply"
    r"|i\s+should\s+reply"
    r"|i\s+owe\s+a\s+reply"
    r"|reply\s+to"
    r")\s*[.!?]*$",
    re.I,
)
_NEED_ZH = re.compile(r"^(?:请)?回复\s*[。！？]*$")
_OWE_EN = re.compile(
    r"^(?:please\s+)?i\s+owe\s+(.+?)\s+a\s+reply(?:\s+about\s+(.+))?\s*[.!?]*$",
    re.I,
)
_REPLY_EN = re.compile(
    r"^(?:please\s+)?(?:i\s+(?:need|have|ought)\s+to\s+|i\s+should\s+)?"
    r"reply\s+to\s+(.+?)(?:\s+about\s+(.+))?\s*[.!?]*$",
    re.I,
)
_REPLY_ZH = re.compile(
    r"^(?:请)?(?:我(?:该|得|需要|应当))?回复(?!谁)\s*"
    r"(.+?)\s*(?:[，,]\s*)?关于\s*(.+?)\s*[。！？]*$"
)
_REPLY_ZH_BARE = re.compile(
    r"^(?:请)?(?:我(?:该|得|需要|应当))?回复(?!谁)\s*(.+?)\s*[。！？]*$"
)
_STORED = re.compile(r"^Reply to (.+?)(?: about (.+))?$")
_TASK_FIELDS = (
    "title",
    "timezone",
    "due_local",
    "status",
    "next_step",
    "waiting_for",
    "steps",
    "visibility",
    "follow_up_enabled",
    "check_in_local",
    "interval_minutes",
)
_WHO_LIMIT = 80
_TOPIC_LIMIT = 60


def is_reply_owed_message(text: str) -> bool:
    """True when this whole message is a reply question or a reply statement."""
    return parse_reply_owed(text) is not None


def parse_reply_owed(text: str) -> dict | None:
    """Ask, a missing person, or one person and an optional topic.

    Any other sentence, including who the owner is waiting on, returns None.
    """
    raw = text.strip()
    if _ASK_EN.match(raw) or _ASK_ZH.match(raw):
        return {"kind": "ask"}
    owed = _OWE_EN.match(raw)
    reply = _REPLY_EN.match(raw)
    chinese = _REPLY_ZH.match(raw)
    bare = _REPLY_ZH_BARE.match(raw)
    match = owed or reply or chinese or bare
    if match is None:
        if _NEED_EN.match(raw) or _NEED_ZH.match(raw):
            return {"kind": "need"}
        return None
    who = _clean(match.group(1))
    topic = _clean(match.group(2) or "") if match.lastindex and match.lastindex >= 2 else ""
    if not who:
        return {"kind": "need"}
    if len(who) > _WHO_LIMIT or len(topic) > _TOPIC_LIMIT or len(_canonical(who, topic)) > 160:
        return {"kind": "long"}
    return {"kind": "record", "who": who, "topic": topic}


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" .。!！?？")


def _canonical(who: str, topic: str) -> str:
    if topic:
        return f"Reply to {who} about {topic}"
    return f"Reply to {who}"


def _parts(title: str) -> tuple[str, str] | None:
    match = _STORED.match(title.strip())
    if not match:
        return None
    who = match.group(1).strip()
    topic = (match.group(2) or "").strip()
    if not who:
        return None
    return who, topic


def _has_files(request, conversation) -> bool:
    """A message that brought files is not a reply question.

    The field is absent until a later composer adds it. An empty list is not files.
    """
    for source in (request, conversation):
        ids = getattr(source, "attachment_ids", None)
        if ids:
            return True
    return False


def _same(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


def _raw_open(runtime) -> list[dict]:
    with runtime.store.connection() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
    tasks = [runtime.tasks.view(row) for row in rows]
    return [task for task in tasks if task["status"] in OPEN]


def _obligations(task: dict) -> list[dict]:
    found = []
    title = _parts(task.get("title") or "")
    if title:
        found.append({"where": "title", "who": title[0], "topic": title[1]})
    for index, step in enumerate(task.get("steps") or []):
        parts = _parts(str(step.get("title") or ""))
        if parts:
            found.append(
                {"where": "step", "index": index, "who": parts[0], "topic": parts[1]}
            )
    return found


def _private_hidden(runtime) -> bool:
    with runtime.store.connection() as conn:
        return bool(runtime.store.settings(conn)["hide_private"])


def _reply(kind: str, message: str, **extra) -> dict:
    return {"mode": "local_rules", "kind": kind, "saved": False, "message": message, **extra}


def _line(who: str, topic: str, *, zh: bool) -> str:
    if zh:
        return f"待回复{who}，关于{topic}。" if topic else f"待回复{who}。"
    return f"Reply to {who} about {topic}." if topic else f"Reply to {who}."


def _list(runtime, *, owner: bool, zh: bool) -> dict:
    named = []
    seen = set()
    for task in _raw_open(runtime):
        for item in _obligations(task):
            key = (task["id"], item["who"].casefold(), item["topic"].casefold())
            if key in seen:
                continue
            seen.add(key)
            named.append({**item, "created_at": task.get("created_at") or ""})
    named.sort(key=lambda item: (item["created_at"], item["who"].casefold()))
    if not owner or _private_hidden(runtime):
        count = len(named)
        if count == 0:
            message = "没有待回复的人。" if zh else "You do not owe a reply."
        elif not owner:
            message = (
                f"有 {count} 项待回复。请在本人的屏幕上查看要回复谁。"
                if zh
                else (
                    f"{count} reply is owed. Open Tasks on the owner's screen to see who."
                    if count == 1
                    else f"{count} replies are owed. Open Tasks on the owner's screen to see who."
                )
            )
        else:
            message = (
                f"有 {count} 项待回复。私人事务隐藏时不显示要回复谁。"
                if zh
                else (
                    f"{count} reply is owed. Details stay hidden while private tasks are hidden."
                    if count == 1
                    else (
                        f"{count} replies are owed. "
                        "Details stay hidden while private tasks are hidden."
                    )
                )
            )
        return _reply("reply_owed", message, count=count)
    shown = named[:20]
    if zh:
        lines = [_line(item["who"], item["topic"], zh=True) for item in shown]
        if not lines:
            lines = ["没有待回复的人。"]
        if len(named) > 20:
            lines.append("仅列出前20项，其余请在事务中查看。")
    else:
        lines = [_line(item["who"], item["topic"], zh=False) for item in shown]
        if not lines:
            lines = ["You do not owe a reply."]
        if len(named) > 20:
            lines.append("Showing the first 20. Open Tasks for the rest.")
    return _reply("reply_owed", "\n".join(lines), count=len(named))


def _reusable_check(value, zone_name: str, now: datetime):
    """Keep a future check-in. A past or unreadable one is omitted, not replayed."""
    if not value or not isinstance(value, str):
        return None
    try:
        wall = datetime.fromisoformat(value)
    except ValueError:
        return None
    if wall.tzinfo is not None:
        return None
    try:
        instant = wall_to_utc(wall, zone_name, reject_ambiguous=True)
    except (ValueError, KeyError, OverflowError):
        return None
    if instant <= now:
        return None
    return value


def _body(runtime, task: dict, *, title: str | None = None, steps: list | None = None) -> dict:
    body = {name: task[name] for name in _TASK_FIELDS if name in task}
    if title is not None:
        body["title"] = title
    if steps is not None:
        body["steps"] = steps
    zone_name = body.get("timezone") or "Asia/Hong_Kong"
    body["check_in_local"] = _reusable_check(
        body.get("check_in_local"), zone_name, runtime.store.clock()
    )
    try:
        return TaskInput.model_validate(body).model_dump(mode="json")
    except ValidationError:
        raise DomainError("TOOL_ARGUMENTS_INVALID", 422) from None


def _already(who: str, topic: str, *, zh: bool, hidden: bool) -> dict:
    if hidden:
        message = "已经记下要回复的人。没有新增保存。" if zh else (
            "That reply is already saved. Nothing new was saved."
        )
    elif zh:
        message = _line(who, topic, zh=True) + "没有新增保存。"
    else:
        lead = _line(who, topic, zh=False)
        message = f"Already saved: {lead} Nothing new was saved."
    return _reply("reply_owed", message)


def _person(task: dict, who: str) -> list[dict]:
    return [item for item in _obligations(task) if _same(item["who"], who)]


def _find(runtime, who: str, topic: str) -> tuple[dict, dict, str] | None:
    """The saved obligation this sentence already covers, oldest task first.

    An omitted topic matches any saved topic for that person and must not clear it.
    A provided topic prefers the same topic, otherwise one saved line that had no topic.
    """
    blank = None
    tasks = sorted(_raw_open(runtime), key=lambda task: task.get("created_at") or "")
    for task in tasks:
        for item in _person(task, who):
            if not topic or _same(item["topic"], topic):
                return task, item, "exact"
            if not item["topic"] and blank is None:
                blank = (task, item, "blank")
    return blank


def _fill(runtime, key, task: dict, item: dict, who: str, topic: str, *, zh: bool) -> dict:
    text = _canonical(who, topic)
    title = None
    steps = None
    if item["where"] == "title":
        title = text
    else:
        steps = [dict(step) for step in task.get("steps") or []]
        steps[item["index"]] = {**steps[item["index"]], "title": text}
    drafted = _change(runtime, key, task, _body(runtime, task, title=title, steps=steps))
    return _pending(drafted, who, topic, zh=zh)


def _append(runtime, key, task: dict, who: str, topic: str, *, zh: bool) -> dict:
    steps = [dict(step) for step in task.get("steps") or []]
    if len(steps) >= 20:
        return _reply(
            "clarify",
            "这件事务的步骤已满。没有保存。"
            if zh
            else "That task already has 20 steps. Nothing was saved.",
        )
    steps.append({"title": _canonical(who, topic), "done": False})
    drafted = _change(runtime, key, task, _body(runtime, task, steps=steps))
    return _pending(drafted, who, topic, zh=zh)


def _change(runtime, key, task: dict, body: dict) -> dict:
    return runtime.assistant.tool(
        "task_change_draft",
        {
            "task_id": task["id"],
            "change": {
                "action": "update",
                "expected_version": task["version"],
                "task": body,
            },
        },
        key,
    )


def _pending(drafted: dict, who: str, topic: str, *, zh: bool) -> dict:
    if zh:
        message = _line(who, topic, zh=True) + "允许之后才会保存。"
    else:
        message = _line(who, topic, zh=False) + " Nothing is saved until you allow it."
    return _reply("reply_owed", message, **drafted)


def _create(runtime, key, who: str, topic: str, *, zh: bool) -> dict:
    with runtime.store.connection() as conn:
        zone = runtime.store.settings(conn)["timezone"]
    drafted = runtime.assistant.tool(
        "task_create_draft",
        {
            "title": _canonical(who, topic),
            "timezone": zone,
            "status": "todo",
            "visibility": "private",
        },
        key,
    )
    return _pending(drafted, who, topic, zh=zh)


def _record(runtime, request, key, who: str, topic: str, *, zh: bool) -> dict:
    hidden = _private_hidden(runtime)
    found = _find(runtime, who, topic)
    if found is not None and found[2] == "exact":
        _task, item, _kind = found
        return _already(item["who"], item["topic"], zh=zh, hidden=hidden)
    if found is not None and found[2] == "blank":
        task, item, _kind = found
        return _fill(runtime, key, task, item, who, topic, zh=zh)
    if not request.task_id:
        return _create(runtime, key, who, topic, zh=zh)
    try:
        task = runtime.tasks.detail(request.task_id)["task"]
    except DomainError as error:
        if error.code == "PRIVATE_TASK_HIDDEN":
            return _reply(
                "clarify",
                "这件事务已隐藏。没有保存。" if zh else "That task is hidden. Nothing was saved.",
            )
        raise
    if task["status"] not in OPEN:
        return _reply(
            "clarify",
            "这件事务已经结束。没有改动。"
            if zh
            else "That task is already closed. Nothing was changed.",
        )
    return _append(runtime, key, task, who, topic, zh=zh)


def answer_reply_owed(runtime, request, key, *, owner: bool, conversation=None):
    """A local reply, or None when this message is about something else.

    Files, when a later composer attaches them, stay with that composer.
    """
    if _has_files(request, conversation):
        return None
    parsed = parse_reply_owed(request.message)
    if parsed is None:
        return None
    zh = request.language == "zh"
    if parsed["kind"] == "ask":
        return _list(runtime, owner=owner, zh=zh)
    if not owner:
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    if parsed["kind"] == "need":
        return _reply(
            "clarify",
            "请说明要回复谁。尚未保存。" if zh else "Say who you need to reply to. Nothing was saved.",
        )
    if parsed["kind"] == "long":
        return _reply(
            "clarify",
            "这句话太长，没能保存。请缩短后再说要回复谁。"
            if zh
            else "That is too long to save. Say who in a shorter line. Nothing was saved.",
        )
    return _record(runtime, request, key, parsed["who"], parsed["topic"], zh=zh)
