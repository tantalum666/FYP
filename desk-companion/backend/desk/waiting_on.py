"""Answer who the owner is waiting on, and hold a new reason until they allow it.

The list and the draft use tasks that are already saved. Nothing here sends mail,
buys, books, or marks a task complete. A paired display hears a count only.
Runtime.tick does not approve a draft.
"""

import re
from datetime import datetime

from pydantic import ValidationError

from .calendar import wall_to_utc
from .store import DomainError
from .tasks import OPEN, TaskInput

_ASK_EN = re.compile(
    r"^(?:please\s+)?(?:what|who) am i (?:still )?waiting (?:on|for)\s*[.!?]*$",
    re.I,
)
_ASK_ZH = re.compile(
    r"^(?:请问)?(?:(?:我)?(?:现在)?(?:还)?在等(?:什么|谁)|谁还没(?:回我|回复))"
    r"(?:呢|啊)?\s*[？?！!。]*$"
)
_NEED_EN = re.compile(r"^(?:please\s+)?(?:i(?:'m| am)\s+)?waiting\s*[.!?]*$", re.I)
_NEED_ZH = re.compile(r"^(?:我)?(?:现在)?(?:还)?在等\s*[。！？]*$")
_RECORD_EN = re.compile(
    r"^(?:please\s+)?(?:i(?:'m| am)\s+|we(?:'re| are)\s+)?waiting\s+(?:on|for)\s+(.+?)\s*[.!?]*$",
    re.I,
)
_RECORD_ZH = re.compile(r"^(?:我)?(?:现在)?(?:还)?在等(?!什么|谁)(.+?)\s*[。！？]*$")
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
_REASON_LIMIT = 500


def is_waiting_message(text: str) -> bool:
    """True when this whole message is a waiting question or a waiting statement."""
    return parse_waiting(text) is not None


def parse_waiting(text: str) -> dict | None:
    """Ask, a missing reason, or one collapsed reason. Other sentences return None."""
    raw = text.strip()
    if _ASK_EN.match(raw) or _ASK_ZH.match(raw):
        return {"kind": "ask"}
    if _NEED_EN.match(raw) or _NEED_ZH.match(raw):
        return {"kind": "need"}
    match = _RECORD_EN.match(raw) or _RECORD_ZH.match(raw)
    if not match:
        return None
    reason = " ".join(match.group(1).split()).strip(" .。!！?？")
    if not reason:
        return {"kind": "need"}
    if len(reason) > _REASON_LIMIT:
        return {"kind": "long"}
    return {"kind": "record", "reason": reason}


def _has_files(request, conversation) -> bool:
    """A message that brought files is not a waiting question.

    The field is absent until a later composer adds it. An empty list is not files.
    """
    for source in (request, conversation):
        ids = getattr(source, "attachment_ids", None)
        if ids:
            return True
    return False


def _raw_waiting(runtime) -> list[dict]:
    with runtime.store.connection() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
    tasks = [runtime.tasks.view(row) for row in rows]
    return [task for task in tasks if task["status"] == "waiting"]


def _private_hidden(runtime) -> bool:
    with runtime.store.connection() as conn:
        return bool(runtime.store.settings(conn)["hide_private"])


def _same(saved: str, reason: str) -> bool:
    return " ".join(saved.split()).casefold() == reason.casefold()


def _reply(kind: str, message: str, **extra) -> dict:
    return {"mode": "local_rules", "kind": kind, "saved": False, "message": message, **extra}


def _list(runtime, *, owner: bool, zh: bool) -> dict:
    waiting = _raw_waiting(runtime)
    if not owner or _private_hidden(runtime):
        count = len(waiting)
        if count == 0:
            message = "没有正在等待的人或事。" if zh else "You are not waiting on anyone."
        elif not owner:
            message = (
                f"有 {count} 项正在等待。请在本人的屏幕上查看在等谁。"
                if zh
                else f"{count} item(s) are waiting. Open Tasks on the owner's screen to see who."
            )
        else:
            message = (
                f"有 {count} 项正在等待。私人事务隐藏时不显示在等谁。"
                if zh
                else (
                    f"{count} item(s) are waiting. "
                    "Details stay hidden while private tasks are hidden."
                )
            )
        return _reply("waiting", message, count=count)
    named = [task for task in waiting if task.get("waiting_for")]
    named.sort(key=lambda task: task.get("created_at") or "")
    shown = named[:20]
    if zh:
        lines = [f"在等{task['waiting_for']}。" for task in shown]
        if not lines:
            lines = ["没有正在等待的人或事。"]
        if len(named) > 20:
            lines.append("仅列出前20项，其余请在事务中查看。")
    else:
        lines = [f"Waiting on {task['waiting_for']}." for task in shown]
        if not lines:
            lines = ["You are not waiting on anyone."]
        if len(named) > 20:
            lines.append("Showing the first 20. Open Tasks for the rest.")
    return _reply("waiting", "\n".join(lines), count=len(named))


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


def _update_body(runtime, task: dict, reason: str) -> dict:
    body = {name: task[name] for name in _TASK_FIELDS if name in task}
    zone_name = body.get("timezone") or "Asia/Hong_Kong"
    body["status"] = "waiting"
    body["waiting_for"] = reason
    body["check_in_local"] = _reusable_check(
        body.get("check_in_local"), zone_name, runtime.store.clock()
    )
    try:
        return TaskInput.model_validate(body).model_dump(mode="json")
    except ValidationError:
        raise DomainError("TOOL_ARGUMENTS_INVALID", 422) from None


def _already(reason: str, *, zh: bool, hidden: bool) -> dict:
    if hidden:
        message = "已经在等这件事。没有新增保存。" if zh else "Already waiting on that. Nothing new was saved."
    elif zh:
        message = f"已经在等{reason}。没有新增保存。"
    else:
        message = f"Already waiting on {reason}. Nothing new was saved."
    return _reply("waiting", message)


def _record(runtime, request, key, reason: str, *, zh: bool) -> dict:
    hidden = _private_hidden(runtime)
    if request.task_id:
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
                "这件事务已经结束。没有改动。" if zh else "That task is already closed. Nothing was changed.",
            )
        if task["status"] == "waiting" and _same(task.get("waiting_for") or "", reason):
            return _already(task.get("waiting_for") or reason, zh=zh, hidden=hidden)
        drafted = runtime.assistant.tool(
            "task_change_draft",
            {
                "task_id": task["id"],
                "change": {
                    "action": "update",
                    "expected_version": task["version"],
                    "task": _update_body(runtime, task, reason),
                },
            },
            key,
        )
    else:
        match = next(
            (
                task
                for task in _raw_waiting(runtime)
                if _same(task.get("waiting_for") or "", reason)
            ),
            None,
        )
        if match is not None:
            return _already(match.get("waiting_for") or reason, zh=zh, hidden=hidden)
        with runtime.store.connection() as conn:
            zone = runtime.store.settings(conn)["timezone"]
        drafted = runtime.assistant.tool(
            "task_create_draft",
            {
                "title": reason[:160],
                "timezone": zone,
                "status": "waiting",
                "waiting_for": reason,
                "visibility": "private",
            },
            key,
        )
    if zh:
        message = f"在等{reason}。允许之后才会保存。"
    else:
        message = f"Waiting on {reason}. Nothing is saved until you allow it."
    return _reply("draft", message, **drafted)


def answer_waiting(runtime, request, key, *, owner: bool, conversation=None):
    """A local reply, or None when this message is about something else.

    Files, when a later composer attaches them, stay with that composer.
    """
    if _has_files(request, conversation):
        return None
    parsed = parse_waiting(request.message)
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
            "请说明在等谁或在等什么。尚未保存。"
            if zh
            else "Say who or what you are waiting on. Nothing was saved.",
        )
    if parsed["kind"] == "long":
        return _reply(
            "clarify",
            "这句话太长，没能保存。请缩短后再说在等谁。"
            if zh
            else "That is too long to save. Say who or what in a shorter line. Nothing was saved.",
        )
    return _record(runtime, request, key, parsed["reason"], zh=zh)
