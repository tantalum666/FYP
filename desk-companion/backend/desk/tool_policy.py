"""One execution policy for text and realtime voice.

The voice adapter still receives the next call from its provider. It does not
run the multi-step text loop. Both paths call execute_tool(), which validates
through the registry, applies the capability timeout, keeps one accepted
outcome per effect key, and writes one audit row.

A timeout does not retry the tool. The first stored outcome wins. A late
unapproved draft or review job is discarded, including when the worker
finishes after the caller has already been told the action timed out.
"""

import contextlib
import hashlib
import json
import threading
from collections.abc import Callable
from typing import Any

from .store import DomainError, encode
from .tool_audit import channel_for


SENTENCES = {
    "cap": {
        "en": "The daily limit for hosted text calls has been reached. Nothing was changed.",
        "zh": "今天的托管文字调用已经到上限，没有做任何修改。",
    },
    "timeout": {
        "en": "This request reached its time limit. Nothing further was changed.",
        "zh": "这次请求达到了时间上限，没有继续修改。",
    },
    "refused": {
        "en": "That action is outside the tools this assistant can use. Nothing was changed.",
        "zh": "这个动作不在助理可用的工具里，没有做任何修改。",
    },
    "invalid": {
        "en": "I could not prepare that action. Nothing was saved.",
        "zh": "没能准备这个动作，没有保存任何内容。",
    },
    "steps": {
        "en": "Please identify the task you want to follow up.",
        "zh": "请明确要跟进哪件事。",
    },
    "unavailable": {
        "en": "The hosted model returned something I could not use. Nothing was changed.",
        "zh": "托管模型的回复无法使用，没有做任何修改。",
    },
    "tool_timeout": {
        "en": "That action took too long and was stopped. Nothing further was saved.",
        "zh": "这个动作超时并已停止，没有继续保存。",
    },
    "failed": {
        "en": "That action failed. Nothing was saved.",
        "zh": "这个动作失败了，没有保存任何内容。",
    },
    "cancelled": {
        "en": "That action was cancelled. Nothing was saved.",
        "zh": "这个动作已取消，没有保存任何内容。",
    },
    "limited": {
        "en": "Too many tool calls are in progress. Nothing was changed.",
        "zh": "工具调用太多，没有做任何修改。",
    },
    "prepared": {
        "en": "Prepared for review. Nothing was saved.",
        "zh": "已准备待审，没有保存。",
    },
}

CODE_KIND = {
    "TOOL_NOT_ALLOWED": "refused",
    "OWNER_SIGN_IN_REQUIRED": "refused",
    "TOOL_TIMEOUT": "tool_timeout",
    "TEXT_AI_UNAVAILABLE": "unavailable",
    "TOOL_ARGUMENTS_INVALID": "invalid",
    "PRESET_NOT_ALLOWED": "invalid",
    "TOOL_FAILED": "failed",
    "TOOL_CANCELLED": "cancelled",
    "TOOL_CALL_CONFLICT": "limited",
    "TOOL_LIMIT_REACHED": "limited",
    "TOOLS_BUSY": "limited",
}

_audit_off = threading.local()


def owner_message(kind: str, language: str = "en") -> str:
    row = SENTENCES.get(kind) or SENTENCES["invalid"]
    return row["zh" if language == "zh" else "en"]


def kind_for(code: str) -> str:
    return CODE_KIND.get(code, "invalid")


OWNER_ONLY_TOOLS = frozenset(
    {"owner_search", "plate_summary", "owner_clock", "propose_plan"}
)


def memory_blocked(name: object, allow_memory: bool) -> bool:
    """True when a paired session must not run this tool.

    Memory tools and the owner lookup tools stay on the owner session.
    Voice advertising uses the same check, so the model is not offered a tool
    the dispatcher would refuse.
    """
    if allow_memory or not isinstance(name, str):
        return False
    return name.startswith("memory_") or name in OWNER_ONLY_TOOLS


def tool_visible(name: str, allow_memory: bool) -> bool:
    return not memory_blocked(name, allow_memory)


def audit_suppressed() -> bool:
    return bool(getattr(_audit_off, "on", False))


@contextlib.contextmanager
def suppress_tool_audit():
    """Hide assistant.tool's own audit while execute_tool records the one row.

    Voice tests replace assistant.tool and only accept positional arguments, so
    the flag is thread-local instead of a new keyword on that call.
    """
    previous = audit_suppressed()
    _audit_off.on = True
    try:
        yield
    finally:
        _audit_off.on = previous


def effect_key(scope: str, name: str, arguments: dict) -> str:
    raw = encode({"scope": scope, "tool": name, "arguments": arguments})
    return "fx/" + hashlib.sha256(raw.encode()).hexdigest()


def discard_unapproved(runtime, result, prefix: str = "tool-discard") -> None:
    if not isinstance(result, dict):
        return
    proposal = result.get("proposal")
    if isinstance(proposal, dict) and isinstance(proposal.get("id"), str):
        with contextlib.suppress(DomainError):
            runtime.assistant.decide(proposal["id"], "cancel", prefix + "/" + proposal["id"])
    job = result.get("job")
    if isinstance(job, dict) and job.get("state") == "review" and isinstance(job.get("id"), str):
        with contextlib.suppress(DomainError):
            runtime.jobs.cancel(job["id"], prefix + "/" + job["id"], review_only=True)


def execute_tool(
    runtime,
    name: object,
    arguments: object,
    call_key: str,
    *,
    scope: str,
    allow_memory: bool = True,
    language: str = "en",
    channel: str | None = None,
    timeout: float | None = None,
    waiter: Callable[[threading.Event, float], bool] | None = None,
) -> dict:
    """Validate, run once, and return the tool result. Errors are dicts, not raises."""
    from .capabilities import CAPABILITIES, parse_call

    channel_name = channel or channel_for(call_key)
    raw = arguments if isinstance(arguments, dict) else {}
    try:
        capability, parsed = parse_call(name, arguments)
    except DomainError as error:
        result = {"error": error.code, "saved": False}
        _audit(
            runtime,
            name,
            raw,
            call_key,
            channel_name,
            error.code,
            result,
            language,
            CAPABILITIES,
        )
        return result
    if memory_blocked(capability.name, allow_memory):
        result = {"error": "OWNER_SIGN_IN_REQUIRED", "saved": False}
        _audit(
            runtime,
            capability.name,
            parsed,
            call_key,
            channel_name,
            "OWNER_SIGN_IN_REQUIRED",
            result,
            language,
            CAPABILITIES,
        )
        return result
    key = effect_key(scope, capability.name, parsed)
    stored = _stored(runtime, key)
    if stored is not None:
        return stored
    seconds = capability.timeout if timeout is None else timeout
    return _run_bounded(
        runtime,
        capability.name,
        parsed,
        call_key,
        key,
        channel_name,
        language,
        seconds,
        waiter or _wait,
        CAPABILITIES,
    )


def _run_bounded(
    runtime,
    name: str,
    arguments: dict,
    call_key: str,
    key: str,
    channel_name: str,
    language: str,
    seconds: float,
    waiter: Callable[[threading.Event, float], bool],
    capabilities: dict,
) -> dict:
    holder: dict[str, Any] = {}
    done = threading.Event()

    def work() -> None:
        produced: dict = {"error": "TOOL_FAILED", "saved": False}
        code = "TOOL_FAILED"
        try:
            try:
                with suppress_tool_audit():
                    # Positional only: voice tests replace tool() and reject new keywords.
                    # Memory denial is handled before this call.
                    value = runtime.assistant.tool(name, arguments, key)
                produced = value if isinstance(value, dict) else {"error": "TOOL_FAILED", "saved": False}
                code = "ok" if isinstance(value, dict) else "TOOL_FAILED"
            except DomainError as error:
                produced = {"error": error.code, "saved": False}
                code = error.code
            except Exception:
                produced = {"error": "TOOL_FAILED", "saved": False}
                code = "TOOL_FAILED"
            holder["produced"] = produced
            inserted, outcome, stored = _claim(runtime, key, code, produced)
            holder["stored"] = stored
            if outcome == "TOOL_TIMEOUT":
                discard_unapproved(runtime, produced)
            elif inserted:
                _audit(
                    runtime,
                    name,
                    arguments,
                    call_key,
                    channel_name,
                    outcome,
                    stored,
                    language,
                    capabilities,
                )
        finally:
            done.set()

    threading.Thread(target=work, name="tool-policy", daemon=True).start()
    if waiter(done, seconds):
        return holder.get("stored") or holder.get("produced") or {"error": "TOOL_FAILED", "saved": False}
    timeout_result = {"error": "TOOL_TIMEOUT", "saved": False}
    inserted, outcome, stored = _claim(runtime, key, "TOOL_TIMEOUT", timeout_result)
    if inserted:
        _audit(
            runtime,
            name,
            arguments,
            call_key,
            channel_name,
            "TOOL_TIMEOUT",
            stored,
            language,
            capabilities,
        )
    if outcome == "TOOL_TIMEOUT":
        threading.Thread(
            target=lambda: _late(done, runtime, holder),
            name="tool-policy-late",
            daemon=True,
        ).start()
        return stored
    if not done.wait(max(seconds, 1)):
        return stored
    return holder.get("stored", stored)


def _late(done: threading.Event, runtime, holder: dict) -> None:
    done.wait()
    discard_unapproved(runtime, holder.get("produced"))


def _wait(done: threading.Event, seconds: float) -> bool:
    return done.wait(seconds)


def _stored(runtime, key: str):
    with runtime.store.connection() as conn:
        row = conn.execute("SELECT result FROM tool_effects WHERE call_key=?", (key,)).fetchone()
    if row is None:
        return None
    value = json.loads(row["result"])
    return value if isinstance(value, dict) else {"error": "TOOL_FAILED", "saved": False}


def _claim(runtime, key: str, outcome: str, result: dict):
    payload = encode(result)
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tool_effects(call_key, outcome, result) VALUES(?,?,?)",
            (key, outcome, payload),
        )
        inserted = conn.execute("SELECT changes()").fetchone()[0] == 1
        row = conn.execute(
            "SELECT outcome, result FROM tool_effects WHERE call_key=?", (key,)
        ).fetchone()
    return inserted, row["outcome"], json.loads(row["result"])


def outcome_message(outcome: str, result, language: str = "en") -> str:
    if outcome == "ok" and _pending_side_effect(result):
        return owner_message("prepared", language)
    if outcome == "ok" and isinstance(result, dict):
        plan = result.get("plan")
        if isinstance(plan, dict) and isinstance(plan.get("summary"), str) and plan["summary"].strip():
            return plan["summary"].strip()
    if outcome == "ok":
        return ""
    return owner_message(kind_for(outcome), language)


def _pending_side_effect(result: dict) -> bool:
    if not isinstance(result, dict) or result.get("error"):
        return False
    if isinstance(result.get("proposal"), dict):
        return True
    job = result.get("job")
    return isinstance(job, dict) and job.get("state") == "review"


def _audit(runtime, name, arguments, call_key, channel_name, outcome, result, language, capabilities):
    message = outcome_message(outcome, result, language)
    risk = "refused"
    if isinstance(name, str) and name in capabilities:
        risk = capabilities[name].risk
    runtime.assistant.audit.record(
        name=name,
        arguments=arguments if isinstance(arguments, dict) else {},
        call_key=call_key,
        channel=channel_name,
        risk=risk,
        outcome=outcome,
        result=result,
        message=message,
    )
