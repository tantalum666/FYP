"""Bounded tool loop. The model proposes one call per step; this module decides.

Reads may continue. A draft, cancel, or stop runs once through the existing
assistant tool path and ends the turn. Provider blips retry before any tool
for that step. A side effect is never replayed because a completion failed.
"""

import hashlib
from typing import Callable

from .capabilities import CAPABILITIES, parse_call
from .model_provider import HostedTextProvider, ModelStep, TextModel
from .store import DomainError


MAX_STEPS = 3
MAX_SECONDS = 45
PROVIDER_ATTEMPTS = 3

COPY = {
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
}


class AgentLoop:
    def __init__(
        self,
        runtime,
        provider: TextModel,
        *,
        max_steps: int = MAX_STEPS,
        max_seconds: float = MAX_SECONDS,
        attempts: int = PROVIDER_ATTEMPTS,
        clock: Callable[[], float] | None = None,
    ):
        self.runtime = runtime
        self.provider = provider
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.attempts = attempts
        self.clock = clock or _monotonic

    def run(self, *, system: str, context: dict, key: str, language: str, allow_memory: bool):
        context = dict(context)
        deadline = self.clock() + self.max_seconds
        for index in range(self.max_steps):
            if self.clock() > deadline:
                return _notice(language, "timeout")
            try:
                step = self._complete(system, context)
            except DomainError as error:
                if error.code == "TEXT_AI_CAP":
                    return _notice(language, "cap")
                raise
            if not _usable(step):
                raise DomainError("TEXT_AI_UNAVAILABLE", 503)
            if step.tool == "none":
                return {"mode": "ai", "kind": "reply", "message": step.message}
            if self.clock() > deadline:
                return _notice(language, "timeout")
            call_key = "text/" + hashlib.sha256(f"{key}/{index}".encode()).hexdigest()
            try:
                capability, arguments = parse_call(step.tool, step.arguments)
            except DomainError as error:
                self._reject(step.tool, step.arguments, call_key, error.code)
                kind = "refused" if error.code == "TOOL_NOT_ALLOWED" else "invalid"
                return _notice(language, kind, error.code)
            try:
                result = self.runtime.assistant.tool(
                    capability.name,
                    arguments,
                    call_key,
                    allow_memory=allow_memory,
                )
            except DomainError as error:
                result = {"error": error.code, "saved": False}
            if _ends_turn(capability.risk, result):
                return _side_reply(step.message, result, language)
            context["last_tool_result"] = {"tool": capability.name, "result": result}
        return _notice(language, "steps")

    def _complete(self, system: str, context: dict) -> ModelStep:
        last: DomainError | None = None
        for attempt in range(self.attempts):
            try:
                return self.provider.complete(system, context)
            except DomainError as error:
                last = error
                if error.code != "TEXT_AI_UNAVAILABLE" or attempt + 1 == self.attempts:
                    raise
        assert last is not None
        raise last

    def _reject(self, name, arguments, call_key, code):
        risk = CAPABILITIES[name].risk if isinstance(name, str) and name in CAPABILITIES else "refused"
        self.runtime.assistant.audit.record(
            name=name,
            arguments=arguments if isinstance(arguments, dict) else {},
            call_key=call_key,
            channel="text",
            risk=risk,
            outcome=code,
            result={"error": code, "saved": False},
        )


def _ends_turn(risk: str, result: dict) -> bool:
    if risk != "read":
        return True
    return result.get("error") in {"OWNER_SIGN_IN_REQUIRED", "TOOL_NOT_ALLOWED"}


def _side_reply(message: str, result: dict, language: str):
    error = result.get("error")
    if error in {"TOOL_NOT_ALLOWED", "OWNER_SIGN_IN_REQUIRED"}:
        return _notice(language, "refused", error)
    if error:
        return _notice(language, "invalid", error)
    kind = "draft" if "proposal" in result else "job" if "job" in result else "reply"
    reply = {"mode": "ai", "kind": kind, "message": message, **result}
    reply.setdefault("saved", False)
    return reply


def _notice(language: str, kind: str, error: str | None = None):
    reply = {
        "mode": "ai",
        "kind": "refused" if kind == "refused" else "clarify",
        "message": COPY[kind]["zh" if language == "zh" else "en"],
        "saved": False,
    }
    if error:
        reply["error"] = error
    return reply


def _usable(step: object) -> bool:
    return (
        isinstance(step, ModelStep)
        and isinstance(step.message, str)
        and 1 <= len(step.message.strip()) <= 2000
        and isinstance(step.tool, str)
    )


def _monotonic() -> float:
    import time

    return time.monotonic()


__all__ = ["AgentLoop", "HostedTextProvider", "MAX_SECONDS", "MAX_STEPS"]
