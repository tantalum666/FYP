from typing import Literal

from pydantic import Field, field_validator

from .mail_threads import identifier
from .schemas import StrictModel


class MailFollowupDraft(StrictModel):
    provider: Literal["gmail", "outlook"]
    message_id: str = Field(min_length=1, max_length=512)
    task_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    task_version: int | None = Field(default=None, ge=1, strict=True)

    @field_validator("message_id")
    @classmethod
    def valid_id(cls, value):
        return identifier(value)


class MailFollowupQuery(StrictModel):
    followup_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    task_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class MailFollowupAcknowledge(StrictModel):
    observed_revision: int = Field(ge=0, strict=True)


class MailFollowupStop(StrictModel):
    followup_id: str = Field(pattern=r"^[a-f0-9]{32}$")
