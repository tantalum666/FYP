"""Provider-agnostic text steps. Hosted adapters stay behind TextAssistant.generate.

A scripted provider returns fixed steps for tests and the offline eval. It does
not open a socket. Qwen and Gemini remain the only hosted adapters.
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


class TextModel(Protocol):
    def complete(self, system: str, context: dict) -> ModelStep: ...


class ScriptedProvider:
    """Deterministic stand-in. Steps are consumed in order, including scripted failures."""

    def __init__(self, steps: list[ModelStep | Exception]):
        self._steps = list(steps)
        self.calls = 0
        self.contexts: list[dict] = []

    def complete(self, system: str, context: dict) -> ModelStep:
        self.calls += 1
        self.contexts.append(copy.deepcopy(context))
        if not self._steps:
            raise DomainError("TEXT_AI_UNAVAILABLE", 503)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


class HostedTextProvider:
    """One completion through the existing text adapter and its configured cap."""

    def __init__(self, generate):
        self._generate = generate

    def complete(self, system: str, context: dict) -> ModelStep:
        from .text_ai import TextPlan

        plan = self._generate(system, context, TextPlan, "conversation")
        return ModelStep(message=plan.message, tool=plan.tool, arguments=dict(plan.arguments))
