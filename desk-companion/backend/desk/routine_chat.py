"""Review one dated local routine exception through the ordinary conversation."""

import re
from typing import Literal

from pydantic import Field

from .calendar import iso
from .routines import RoutineDate
from .schemas import StrictModel
from .store import DomainError


class RoutineSkipDraft(StrictModel):
    when: Literal["tomorrow", "next"] | RoutineDate
    title: str | None = Field(default=None, min_length=1, max_length=160)


TOOL = {
    "name": "routine_skip_draft",
    "description": (
        "Prepare an owner review to skip exactly one occurrence of a saved local routine "
        "(day briefing or task review). Use tomorrow in the routine's timezone, next for its "
        "next future run, or the requested YYYY-MM-DD. Supply the exact routine title only if "
        "named. The owner selects among matches on the review card and confirms the dated skip. "
        "For '明天这一次不用提醒我，之后照常', use tomorrow. Never pause all reminders or "
        "change a calendar series for this request."
    ),
    "parameters": RoutineSkipDraft.model_json_schema(),
}


def skip_request(text):
    """Recognize a complete one-occurrence request even when the provider is offline."""
    text = text.strip().rstrip("。.!！").replace("’", "'")
    zh = re.fullmatch(
        r"(?:请)?(?P<day>明天|下次|[0-9]{4}-[0-9]{2}-[0-9]{2}日?)"
        r"(?:的(?P<title>.+?))?(?:这一次|这次)?(?:不用|不要|别)提醒我"
        r"(?:[，, ]*(?:之后|以后)照常)?",
        text,
    )
    if zh:
        day = zh["day"].removesuffix("日")
        arguments = {"when": {"明天": "tomorrow", "下次": "next"}.get(day, day)}
        if zh["title"]:
            arguments["title"] = zh["title"].strip()
        return arguments
    en = re.fullmatch(
        r"(?:please )?(?:skip (?:just )?(?:tomorrow's|the next) (?:routine|reminder|briefing)"
        r"|(?:don't|do not) remind me tomorrow)"
        r"(?:[, ]+(?:(?:then |and )?(?:continue|resume) as usual|keep the rest as usual))?",
        text,
        re.I,
    )
    if en:
        return {"when": "tomorrow" if "tomorrow" in text.lower() else "next"}
    named = re.fullmatch(r"skip (.+?) on ([0-9]{4}-[0-9]{2}-[0-9]{2}|tomorrow)", text, re.I)
    if named:
        return {"when": named[2].lower(), "title": named[1]}
    return None


def turn(runtime, request, key, principal):
    arguments = skip_request(request.message)
    if arguments is None:
        return None
    runtime.personal_context.require_visible(principal)
    zh = request.language == "zh"
    try:
        draft = runtime.assistant.tool(TOOL["name"], arguments, key)
    except DomainError as error:
        if error.code != "ROUTINE_OCCURRENCE_UNAVAILABLE":
            raise
        return {
            "mode": "local_rules",
            "kind": "clarify",
            "saved": False,
            "error": error.code,
            "message": (
                "没有符合条件的定时事务可在该日期跳过。"
                if zh
                else "There is no matching upcoming routine occurrence to skip."
            ),
        }
    return {
        "mode": "local_rules",
        "kind": "draft",
        **draft,
        "message": "请核对要跳过的定时事务和时间。"
        if zh
        else "Review the routine and time to skip.",
    }


def refresh_reply(store, reply, proposal_id, language):
    """Resolve the original review on retry, including a committed but unacknowledged skip."""
    with store.connection() as conn:
        if store.settings(conn)["hide_private"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        if not proposal_id:
            return reply
        row = conn.execute(
            "SELECT state,expires_at FROM assistant_proposals WHERE id=? AND kind='routine_skip'",
            (proposal_id,),
        ).fetchone()
        applied = conn.execute(
            "SELECT 1 FROM operations WHERE id=?", ("assistant-confirm/" + proposal_id,)
        ).fetchone()
        if applied or (row and row["state"] == "confirmed"):
            state = "confirmed"
            message = ("That routine occurrence was skipped.", "已跳过这一次提醒。")
        elif row and row["state"] == "pending" and row["expires_at"] > iso(store.clock()):
            return reply
        else:
            state = "cancelled" if row and row["state"] == "cancelled" else "expired"
            message = ("This skip request was cancelled or expired.", "本次请求已取消或到期。")
    return {
        **reply,
        "kind": "reply",
        "proposal": None,
        "action": {"kind": "routine_skip", "id": proposal_id, "state": state},
        "saved": state == "confirmed",
        "message": message[language == "zh"],
    }


def selected_choice(choices, routine_id):
    if routine_id is None and len(choices) == 1:
        return choices[0]
    for choice in choices:
        if choice["routine_id"] == routine_id:
            return choice
    raise DomainError("ROUTINE_SELECTION_REQUIRED", 422)
