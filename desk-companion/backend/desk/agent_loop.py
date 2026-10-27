"""Bounded tool loop. The model proposes one call per step; this module decides.

Reads may continue. A draft, cancel, stop, or tool timeout runs once through
the shared tool policy and ends the turn. Provider blips and unusable model
output retry before any tool for that step. A side effect is never replayed
because a completion failed.
"""

import hashlib
from typing import Callable

from .capabilities import CAPABILITIES
from .model_provider import HostedTextProvider, ModelStep, TextModel
from .store import DomainError
from .tool_policy import execute_tool, kind_for, owner_message


MAX_STEPS = 3
MAX_SECONDS = 45
PROVIDER_ATTEMPTS = 3


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
            if step is None:
                return _notice(language, "unavailable")
            if step.tool == "none":
                return {"mode": "ai", "kind": "reply", "message": step.message}
            if self.clock() > deadline:
                return _notice(language, "timeout")
            call_key = "text/" + hashlib.sha256(f"{key}/{index}".encode()).hexdigest()
            result = execute_tool(
                self.runtime,
                step.tool,
                step.arguments,
                call_key,
                scope=key,
                allow_memory=allow_memory,
                language=language,
                channel="text",
            )
            if _ends_turn(step.tool, result):
                return _side_reply(step.message, result, language)
            context["last_tool_result"] = {"tool": step.tool, "result": result}
        return _notice(language, "steps")

    def _complete(self, system: str, context: dict) -> ModelStep | None:
        for attempt in range(self.attempts):
            try:
                step = self.provider.complete(system, context)
            except DomainError as error:
                if error.code == "TEXT_AI_CAP" or error.code != "TEXT_AI_UNAVAILABLE":
                    raise
                if attempt + 1 == self.attempts:
                    return None
                continue
            if _usable(step):
                return step
            if attempt + 1 == self.attempts:
                return None
        return None


def _ends_turn(name: str, result: dict) -> bool:
    if result.get("error") == "TOOL_TIMEOUT":
        return True
    risk = CAPABILITIES[name].risk if name in CAPABILITIES else "refused"
    if risk != "read":
        return True
    return result.get("error") in {"OWNER_SIGN_IN_REQUIRED", "TOOL_NOT_ALLOWED"}


def _side_reply(message: str, result: dict, language: str):
    error = result.get("error")
    if error:
        return _notice(language, kind_for(error), error)
    kind = "draft" if "proposal" in result else "job" if "job" in result else "reply"
    reply = {"mode": "ai", "kind": kind, "message": message, **result}
    reply.setdefault("saved", False)
    return reply


def _notice(language: str, kind: str, error: str | None = None):
    reply = {
        "mode": "ai",
        "kind": "refused" if kind == "refused" else "clarify",
        "message": owner_message(kind, language),
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
