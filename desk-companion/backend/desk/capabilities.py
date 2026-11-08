"""Tool registry for the hosted model. Schemas and risk live here; execution does not.

Read tools return data. Draft tools only prepare a proposal or a job in review.
Cancel and stop call the existing job-cancel and output-stop paths. Nothing in
this module approves a write, and unknown names are refused.
"""

from typing import Literal

from pydantic import Field, ValidationError

from .jobs import JobInput, JobQuery
from .application_models import ApplicationJobInput, ApplicationStateQuery, SourceQuery
from .memory import MemoryDeleteDraft, MemoryQuery, MemoryReplaceDraft, MemorySaveDraft
from .outbound_mail_models import MailDraft
from .app_connection_models import ConnectedAppQuery
from .outputs import PRESETS
from .schemas import CreateEvents, StrictModel
from .store import DomainError
from .tasks import TaskChange, TaskInput, TaskQuery
from .assistant import CalendarQuery, ChangeProposal
from .owner_lookup import OwnerClockArgs, OwnerSearch, PlateQuery
from .owner_plan import ProposePlan


Risk = Literal["read", "draft", "cancel", "stop"]

# A timeout stops waiting and discards a late unapproved draft. It does not kill
# the worker thread; SQLite may still finish the write that is already in flight.
TIMEOUTS = {"read": 5.0, "draft": 8.0, "cancel": 5.0, "stop": 3.0}


class EmptyArgs(StrictModel):
    pass


class TaskDetailsArgs(StrictModel):
    task_id: str = Field(min_length=1, max_length=64)


class FeedbackDraft(StrictModel):
    kind: Literal["light", "arm"]
    preset: Literal["off", "attention", "calm", "rest", "point_calendar"]


class Capability:
    def __init__(
        self,
        name: str,
        risk: Risk,
        model: type[StrictModel],
        timeout: float | None = None,
    ):
        self.name, self.risk, self.model = name, risk, model
        self.timeout = TIMEOUTS[risk] if timeout is None else timeout


def _capabilities() -> dict[str, Capability]:
    rows = [
        Capability("connected_app_query", "read", ConnectedAppQuery, timeout=12),
        Capability("email_status", "read", EmptyArgs),
        Capability("email_send_draft", "draft", MailDraft),
        Capability("application_sources", "read", EmptyArgs),
        Capability("application_source_read", "read", SourceQuery, timeout=10),
        Capability("application_job_draft", "draft", ApplicationJobInput),
        Capability("application_task_state", "read", ApplicationStateQuery),
        Capability("application_artifact_read", "read", JobQuery, timeout=15),
        Capability("memory_query", "read", MemoryQuery),
        Capability("memory_save_draft", "draft", MemorySaveDraft),
        Capability("memory_replace_draft", "draft", MemoryReplaceDraft),
        Capability("memory_delete_draft", "draft", MemoryDeleteDraft),
        Capability("computer_job_draft", "draft", JobInput),
        Capability("computer_job_status", "read", JobQuery),
        Capability("computer_job_cancel", "cancel", JobQuery),
        Capability("task_details", "read", TaskDetailsArgs),
        Capability("task_query", "read", TaskQuery),
        Capability("task_create_draft", "draft", TaskInput),
        Capability("task_change_draft", "draft", TaskChange),
        Capability("device_status", "read", EmptyArgs),
        Capability("stop_physical_outputs", "stop", EmptyArgs),
        Capability("device_feedback_draft", "draft", FeedbackDraft),
        Capability("calendar_query", "read", CalendarQuery),
        Capability("calendar_create_draft", "draft", CreateEvents),
        Capability("calendar_change_draft", "draft", ChangeProposal),
        Capability("posture_status", "read", EmptyArgs),
        Capability("owner_search", "read", OwnerSearch),
        Capability("plate_summary", "read", PlateQuery),
        Capability("owner_clock", "read", OwnerClockArgs),
        Capability("propose_plan", "read", ProposePlan),
    ]
    return {row.name: row for row in rows}


CAPABILITIES = _capabilities()


def parse_call(name: object, arguments: object) -> tuple[Capability, dict]:
    """Validate one structured call. Raises DomainError and does not execute."""
    if not isinstance(name, str) or name not in CAPABILITIES:
        raise DomainError("TOOL_NOT_ALLOWED", 422)
    if not isinstance(arguments, dict):
        raise DomainError("TOOL_ARGUMENTS_INVALID", 422)
    capability = CAPABILITIES[name]
    try:
        parsed = capability.model.model_validate(arguments)
    except ValidationError:
        raise DomainError("TOOL_ARGUMENTS_INVALID", 422) from None
    if capability.name == "device_feedback_draft" and parsed.preset not in PRESETS[parsed.kind]:
        raise DomainError("PRESET_NOT_ALLOWED", 422)
    return capability, parsed.model_dump(mode="json", exclude_unset=True)
