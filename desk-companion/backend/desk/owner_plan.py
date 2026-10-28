"""A bounded plan the owner can read. Preparing a plan does not write.

Calendar, task, memory, and note changes still go through the existing draft
tools. This module only checks the shape and returns the text the owner sees.
"""

from pydantic import Field, field_validator

from .schemas import StrictModel


class PlanStep(StrictModel):
    text: str = Field(min_length=1, max_length=200)

    @field_validator("text")
    @classmethod
    def compact(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("A plan step needs text")
        return text


class ProposePlan(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    steps: list[PlanStep] = Field(min_length=1, max_length=5)

    @field_validator("title")
    @classmethod
    def compact_title(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("A plan needs a title")
        return text


def propose_plan(arguments: dict) -> dict:
    parsed = ProposePlan.model_validate(arguments)
    steps = [step.text for step in parsed.steps]
    summary = parsed.title + ": " + " ".join(f"{index}. {text}" for index, text in enumerate(steps, 1))
    return {
        "saved": False,
        "plan": {"title": parsed.title, "steps": steps, "summary": summary},
    }
