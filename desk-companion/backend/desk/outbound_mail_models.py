"""Bounded plain-text mail, independent of the incoming mailbox fixtures."""

import re
from typing import Literal
from pydantic import Field, field_validator
from .schemas import StrictModel


def address(value):
    value = value.strip()
    if not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,188}[A-Za-z0-9])?\.[A-Za-z]{2,24}",
        value,
    ):
        raise ValueError("Use one email address without a display name")
    local, domain = value.rsplit("@", 1)
    if ".." in local or ".." in domain or local.startswith(".") or local.endswith("."):
        raise ValueError("Invalid email address")
    return local + "@" + domain.lower()


class MailDraft(StrictModel):
    provider: Literal["auto", "gmail", "outlook"] = "auto"
    to: str = Field(
        min_length=1,
        max_length=254,
        description="One email address, or 'me' for the selected connected email account.",
    )
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=12000)

    @field_validator("to")
    @classmethod
    def recipient(cls, value):
        return "me" if value.strip().lower() in {"me", "self"} else address(value)

    @field_validator("subject")
    @classmethod
    def subject_line(cls, value):
        if any(ord(c) < 32 or ord(c) == 127 for c in value) or not value.strip():
            raise ValueError("Use a nonempty single-line subject")
        return value.strip()

    @field_validator("body")
    @classmethod
    def text_body(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("Use a nonempty plain-text message")
        value.encode("utf-8")
        return value
