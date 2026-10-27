"""What a hosted model may see for one turn. Secrets and deleted facts stay out."""

from datetime import timedelta

from .calendar import iso
from .context_budget import fit_context
from .rank import rank_rows
from .store import encode
from .turns import recent_turns


def pack_conversation(
    runtime,
    task_id=None,
    *,
    include_memory=True,
    user_message="",
    last_tool_result=None,
    budget=None,
):
    now = runtime.store.clock()
    tasks = runtime.tasks.listing(include_closed=bool(task_id))
    selected = runtime.tasks.detail(task_id) if task_id else None
    window = runtime.store.snapshot(now, now + timedelta(days=7))
    packed = {
        "now": iso(now),
        "timezone": tasks["timezone"],
        "profile": _profile(runtime),
        "pending_approvals": _approvals(runtime, allow_memory=include_memory),
        "memory": _memories(runtime, user_message) if include_memory else [],
        "turns": recent_turns(runtime) if include_memory else [],
        "tasks": tasks["tasks"][:30],
        "more_tasks": len(tasks["tasks"]) > 30,
        "selected_task": selected,
        "calendar": window["occurrences"][:80],
    }
    if user_message:
        packed["user_message"] = user_message
    if last_tool_result is not None:
        packed["last_tool_result"] = last_tool_result
    return fit_context(packed, budget=budget)


def _profile(runtime) -> str:
    body = runtime.persona.current()["body"]
    return " ".join(str(body or "").split())[:240]


def _approvals(runtime, *, allow_memory: bool) -> list[dict]:
    rows = []
    for item in runtime.assistant.proposals(allow_memory=allow_memory):
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        rows.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "state": item["state"],
                "expires_at": item["expires_at"],
                "saved": False,
                "preview": encode(data)[:160],
            }
        )
    return rows


def _memories(runtime, user_message: str) -> list[dict]:
    facts = []
    for item in runtime.memory.listing()["memories"]:
        facts.append(
            {
                "id": item["id"],
                "version": item["version"],
                "body": item["body"],
                "updated_at": item["updated_at"],
            }
        )
    rows = [
        {"text": fact["body"], "time": fact["updated_at"], "id": fact["id"], "payload": fact}
        for fact in facts
    ]
    matched = rank_rows(user_message, rows, limit=max(len(rows), 1))
    seen = {fact["id"] for fact in matched}
    rest = [fact for fact in facts if fact["id"] not in seen]
    rest.sort(key=lambda fact: (fact["updated_at"], fact["id"]), reverse=True)
    return matched + rest
