"""Provider-agnostic text steps. Hosted adapters stay behind TextAssistant.generate.

A scripted provider returns fixed steps for tests and the offline eval. It does
not open a socket. OpenAI, Qwen and Gemini use the same business-tool boundary.
"""

import copy
from dataclasses import dataclass, field
from typing import Protocol

from .store import DomainError


@dataclass(frozen=True)
class ModelStep:
    message: str
    tool: str = "none"
    arguments: dict = field(default_factory=dict)
    streamed: bool = False


class TextModel(Protocol):
    def complete(self, system: str, context: dict, on_delta=None) -> ModelStep: ...


class ScriptedProvider:
    """Deterministic stand-in. Steps are consumed in order, including scripted failures."""

    def __init__(self, steps: list[ModelStep | Exception]):
        self._steps = list(steps)
        self.calls = 0
        self.contexts: list[dict] = []

    def complete(self, system: str, context: dict, on_delta=None) -> ModelStep:
        self.calls += 1
        self.contexts.append(copy.deepcopy(context))
        if not self._steps:
            raise DomainError("TEXT_AI_UNAVAILABLE", 503)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        if on_delta is None or not step.message:
            return step
        for index in range(0, len(step.message), 5):
            on_delta(step.message[index : index + 5])
        return ModelStep(step.message, step.tool, dict(step.arguments), streamed=True)


class HostedTextProvider:
    """One completion through the existing text adapter and its configured cap."""

    def __init__(
        self, generate, generate_live=None, *, attachment_parts=None, attachment_guard=None
    ):
        self._generate = generate
        self._generate_live = generate_live
        self._attachment_kwargs = (
            {"attachment_parts": attachment_parts, "attachment_guard": attachment_guard}
            if attachment_parts
            else {}
        )

    def complete(self, system: str, context: dict, on_delta=None) -> ModelStep:
        from .text_ai import TextPlan

        if on_delta is None or self._generate_live is None:
            plan = self._generate(
                system, context, TextPlan, "conversation", **self._attachment_kwargs
            )
            return ModelStep(message=plan.message, tool=plan.tool, arguments=dict(plan.arguments))
        plan, streamed = self._generate_live(
            system, context, TextPlan, "conversation", on_delta, **self._attachment_kwargs
        )
        return ModelStep(
            message=plan.message,
            tool=plan.tool,
            arguments=dict(plan.arguments),
            streamed=streamed,
        )
