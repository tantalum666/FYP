"""Strict owner requests and bounded model output for durable work packages."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .schemas import StrictModel
from .agent_context import RunPersonalContextSelection


class RunMutation(StrictModel):
    tool: Literal[
        "task_create_draft", "task_change_draft", "calendar_create_draft", "calendar_change_draft"
    ]
    arguments: dict
    required: bool = True


class RunCreate(StrictModel):
    goal: str = Field(min_length=1, max_length=4000)
    mode: Literal["deterministic", "model"] = "deterministic"
    source_ids: list[str] = Field(default_factory=list, max_length=12)
    task_ids: list[str] = Field(default_factory=list, max_length=10)
    event_ids: list[str] = Field(default_factory=list, max_length=10)
    retain: Literal[True]
    voice_origin_ref: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    scope_revision: str = Field(min_length=64, max_length=64)
    provider_destination_id: str | None = None
    share_sources_with_provider: bool = False
    required_sections: list[str] = Field(default_factory=list, max_length=8)
    allow_mutation_proposals: bool = False
    mutation_requests: list[RunMutation] = Field(default_factory=list, max_length=3)
    personal_context: RunPersonalContextSelection | None = None
    share_connector_results_with_provider: bool = Field(default=False, strict=True)
    connector_tool_ids: list[str] = Field(default_factory=list, max_length=8)
    browser_source_ids: list[str] = Field(default_factory=list, max_length=2)
    browser_public_only: bool = Field(default=False, strict=True)
    model_call_budget: int = Field(default=8, ge=1, le=24, strict=True)
    tool_call_budget: int = Field(default=8, ge=1, le=16, strict=True)

    @field_validator("retain", mode="before")
    @classmethod
    def explicit_retention(cls, value):
        if value is not True:
            raise ValueError("Explicit boolean retention acknowledgement required")
        return value

    @field_validator("goal")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("A goal is required")
        return value.strip()

    @field_validator("source_ids", "task_ids", "event_ids", "browser_source_ids")
    @classmethod
    def ids(cls, values):
        if len(set(values)) != len(values) or any(not v or len(v) > 64 for v in values):
            raise ValueError("Unique bounded IDs required")
        return values

    @field_validator("connector_tool_ids")
    @classmethod
    def connector_ids(cls, values):
        if len(set(values)) != len(values) or any(not v or len(v) > 180 for v in values):
            raise ValueError("Unique bounded tool IDs required")
        return values

    @model_validator(mode="after")
    def selected(self):
        if not (
            self.source_ids
            or self.task_ids
            or self.event_ids
            or self.browser_source_ids
            or self.connector_tool_ids
        ):
            raise ValueError("Select evidence for this work package")
        if self.browser_source_ids and (self.mode != "model" or not self.browser_public_only):
            raise ValueError(
                "Browser selection requires model mode and explicit public-only consent"
            )
        if self.connector_tool_ids and self.mode != "model":
            raise ValueError("Connector tools require model mode")
        if self.connector_tool_ids and not self.share_connector_results_with_provider:
            raise ValueError(
                "Explicit connector-result sharing with the selected provider is required"
            )
        if self.connector_tool_ids and (
            self.source_ids
            or self.task_ids
            or self.event_ids
            or self.personal_context
            and self.personal_context.selected
        ):
            raise ValueError(
                "Public connector runs cannot include private sources, application records or personal context"
            )
        if self.personal_context and self.personal_context.selected and self.mode != "model":
            raise ValueError("Personal context requires model mode")
        if any(not s.strip() or len(s) > 160 for s in self.required_sections):
            raise ValueError("Bounded section titles required")
        if (
            self.mode == "model"
            and len(self.source_ids)
            + len(self.task_ids)
            + len(self.event_ids)
            + len(self.browser_source_ids)
            > 10
        ):
            raise ValueError("Model mode supports at most ten selected evidence items")
        if self.mode == "model" and not self.provider_destination_id:
            raise ValueError("An exact model destination is required")
        return self


class RunAction(StrictModel):
    action: Literal["pause", "resume", "cancel", "steer", "retry_model", "answer"]
    expected_version: int = Field(ge=1)
    goal: str | None = Field(default=None, min_length=1, max_length=4000)
    answer: str | None = Field(default=None, min_length=1, max_length=2000)


class ReportSection(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=6000)
    evidence_ids: list[str] = Field(min_length=1, max_length=32)


class WorkReport(StrictModel):
    """The model supplies prose, never grants, executable code or success flags."""

    summary: str = Field(min_length=1, max_length=2000)
    sections: list[ReportSection] = Field(min_length=1, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=12)


class RunToolCall(StrictModel):
    """Registry lookup, never an executable tool name or authority supplied by a model."""

    tool: str = Field(min_length=1, max_length=180, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    arguments: dict
    required: bool = Field(default=True, strict=True)


class AgentDecision(StrictModel):
    action: Literal["plan", "read", "report", "propose", "tool", "ask", "finish"]
    plan: list[str] = Field(default_factory=list, max_length=8)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    evidence_id: str | None = Field(default=None, max_length=80)
    start_line: int = Field(default=1, ge=1, le=1000000)
    max_lines: int = Field(default=200, ge=1, le=200)
    report: WorkReport | None = None
    mutation: RunMutation | None = None
    tool_call: RunToolCall | None = None
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    summary: str = Field(default="", max_length=1000)


class ToolObservation(StrictModel):
    """Bounded untrusted evidence from a registered adapter, never authority."""

    id: str = Field(min_length=1, max_length=160)
    kind: Literal["browser", "connector"]
    record_id: str = Field(min_length=1, max_length=180)
    observation_id: str | None = Field(default=None, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: int = Field(ge=1, strict=True)
    at: str = Field(min_length=1, max_length=40)
    excerpt: str = Field(max_length=1800)
    coverage: dict
    statistics: None = None
    provenance: None = None
    url: str | None = Field(default=None, max_length=160)
    heading: str | None = Field(default=None, max_length=300)


class ToolReceipt(StrictModel):
    reference_id: str = Field(min_length=1, max_length=100)
    state: Literal["observed", "pending", "unknown", "rejected"]
    result: dict
    evidence: ToolObservation | None = None
