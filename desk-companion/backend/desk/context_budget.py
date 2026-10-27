"""Character budget for one model context. No tokenizer and no new package.

The tool list is not counted: dropping a name would hide an allowed action.
Pending approvals, the selected task, the current user message, the short
profile, and the latest tool result stay even when that makes the text longer
than the budget. Calendar rows go first, then tasks, older turns, and
lower-ranked memories.
"""

from .store import encode


DEFAULT_BUDGET = 12000
TOOL_RESULT_LIMIT = 4000


def fit_context(context: dict, *, budget: int | None = None) -> dict:
    limit = DEFAULT_BUDGET if budget is None else budget
    fitted = dict(context)
    if fitted.get("last_tool_result") is not None:
        fitted["last_tool_result"] = _clip_tool_result(fitted["last_tool_result"])
    lists = {
        key: list(fitted[key])
        for key in ("calendar", "tasks", "turns", "memory")
        if isinstance(fitted.get(key), list)
    }
    task_count = len(lists.get("tasks", []))

    def publish() -> int:
        for key, value in lists.items():
            fitted[key] = value
        if "tasks" in lists and len(lists["tasks"]) < task_count:
            fitted["more_tasks"] = True
        visible = {key: value for key, value in fitted.items() if key != "tools"}
        return len(encode(visible))

    while publish() > limit and any(lists.values()):
        for key in ("calendar", "tasks", "turns", "memory"):
            if lists.get(key):
                lists[key].pop()
                break
    publish()
    return fitted


def _clip_tool_result(value):
    if not isinstance(value, dict) or len(encode(value)) <= TOOL_RESULT_LIMIT:
        return value
    result = value.get("result") if isinstance(value.get("result"), dict) else {}
    kept = {"saved": bool(result.get("saved"))}
    if result.get("error"):
        kept["error"] = result["error"]
    proposal = result.get("proposal")
    if isinstance(proposal, dict):
        kept["proposal"] = {
            key: proposal.get(key) for key in ("id", "kind", "state", "expires_at")
        }
    job = result.get("job")
    if isinstance(job, dict):
        kept["job"] = {key: job.get(key) for key in ("id", "state")}
    memories = result.get("memories")
    if isinstance(memories, list):
        kept["memories"] = [
            {"id": row.get("id"), "body": str(row.get("body") or "")[:160]}
            for row in memories[:8]
            if isinstance(row, dict)
        ]
    kept["preview"] = encode(result)[:240]
    return {"tool": value.get("tool"), "result": kept}
