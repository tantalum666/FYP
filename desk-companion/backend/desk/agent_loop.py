"""Bounded tool loop. The model proposes one call per step; this module decides.

Reads may continue. A draft, cancel, stop, or tool timeout runs once through
the shared tool policy and ends the turn. Provider blips and unusable model
output retry before any tool for that step. A side effect is never replayed
because a completion failed.
"""

import hashlib
from typing import Callable

from .capabilities import CAPABILITIES
from .context_budget import fit_context
from .model_provider import HostedTextProvider, ModelStep, TextModel
from .store import DomainError
from .tool_policy import execute_tool, ends_text_turn, text_effect_reply, text_notice


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

    def run(
        self,
        *,
        system: str,
        context: dict,
        key: str,
        language: str,
        allow_memory: bool,
        principal: dict | None = None,
        on_event: Callable[[dict], None] | None = None,
    ):
        context = dict(context)
        deadline = self.clock() + self.max_seconds
        plan = None

        def finish(reply):
            if plan and isinstance(reply, dict):
                return {**reply, "plan": plan}
            return reply

        for index in range(self.max_steps):
            if self.clock() > deadline:
                return finish(text_notice(language, "timeout"))
            preview = ""

            def on_delta(piece):
                nonlocal preview
                if not isinstance(piece, str) or not piece:
                    return
                preview += piece
                if on_event is not None:
                    on_event({"type": "preview", "text": preview})

            try:
                step = self._complete(system, context, on_delta if on_event is not None else None)
            except DomainError as error:
                if error.code == "TEXT_AI_CAP":
                    return finish(text_notice(language, "cap"))
                raise
            if step is None:
                return finish(text_notice(language, "unavailable"))
            if step.tool == "none":
                _mark_streamed(on_event, step)
                return finish({"mode": "ai", "kind": "reply", "message": step.message})
            if self.clock() > deadline:
                return finish(text_notice(language, "timeout"))
            call_key = "text/" + hashlib.sha256(f"{key}/{index}".encode()).hexdigest()
            risk = CAPABILITIES[step.tool].risk if step.tool in CAPABILITIES else "refused"
            if on_event is not None and risk == "read" and preview:
                on_event({"type": "preview", "text": ""})
            if on_event is not None:
                on_event({"type": "tool", "phase": "started", "tool": step.tool})
            result = execute_tool(
                self.runtime,
                step.tool,
                step.arguments,
                call_key,
                scope=key,
                allow_memory=allow_memory,
                principal=principal,
                language=language,
                channel="text",
            )
            if on_event is not None:
                on_event(
                    {
                        "type": "tool",
                        "phase": "finished",
                        "tool": step.tool,
                        "outcome": result.get("error") or "ok",
                        "saved": bool(result.get("saved")),
                    }
                )
            summary = _plan_summary(result)
            if summary:
                plan = summary
            if ends_text_turn(step.tool, result):
                if risk != "read":
                    _mark_streamed(on_event, step)
                return finish(text_effect_reply(step.message, result, language))
            context["last_tool_result"] = {"tool": step.tool, "result": result}
            context = fit_context(context)
        return finish(text_notice(language, "steps"))

    def _complete(self, system: str, context: dict, on_delta) -> ModelStep | None:
        for attempt in range(self.attempts):
            try:
                if on_delta is None:
                    step = self.provider.complete(system, context)
                else:
                    step = self.provider.complete(system, context, on_delta=on_delta)
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


def _mark_streamed(on_event, step: ModelStep) -> None:
    if on_event is not None and step.streamed:
        on_event({"type": "preview", "text": step.message, "final": True})


def _plan_summary(result: dict) -> str | None:
    plan = result.get("plan") if isinstance(result, dict) else None
    if not isinstance(plan, dict):
        return None
    summary = plan.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return None


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
