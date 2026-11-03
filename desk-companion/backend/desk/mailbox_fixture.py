"""Local mailbox fixtures. No network, credentials, or provider SDK."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from .schemas import EventInput, StrictModel
from .store import DomainError, encode

FORMAT = "desk-mailbox-fixture-v1"
NAME = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
TOKEN = r"^[a-z0-9][a-z0-9-]{0,63}$"
ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "mailbox"
MAX_BYTES = 256 * 1024


class FixtureMessage(StrictModel):
    """One offline message. Omitted task fields are not updates."""

    id: str = Field(pattern=TOKEN)
    thread_id: str = Field(pattern=TOKEN)
    history_id: int = Field(ge=1, le=1_000_000_000)
    observed_at: datetime
    sender: str = Field(min_length=3, max_length=200)
    subject: str = Field(min_length=1, max_length=160)
    snippet: str = Field(default="", max_length=500)
    deadline_local: datetime | None = None
    timezone: str | None = None
    await_reply: bool | None = None
    waiting_for: str | None = Field(default=None, max_length=500)
    next_step: str | None = Field(default=None, max_length=500)
    needs_decision: bool = False

    @field_validator("observed_at")
    @classmethod
    def utc_observation(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must be explicit UTC")
        return value.astimezone(UTC)

    @field_validator("deadline_local")
    @classmethod
    def local_deadline(cls, value: datetime | None) -> datetime | None:
        return EventInput.local_datetime(value) if value else None

    @field_validator("timezone")
    @classmethod
    def zone(cls, value: str | None) -> str | None:
        return EventInput.valid_zone(value) if value else None

    @field_validator("sender", "subject", "snippet")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(char in value for char in "\r\n\x00"):
            raise ValueError("Mailbox text must be a single line")
        return value

    @model_validator(mode="after")
    def timezone_with_deadline(self):
        if self.timezone and "deadline_local" not in self.model_fields_set:
            raise ValueError("timezone requires deadline_local")
        return self


class FixtureEvent(StrictModel):
    op: Literal["message", "interrupt", "revoke", "disconnect"]
    message: FixtureMessage | None = None

    @model_validator(mode="after")
    def message_matches_op(self):
        if (self.op == "message") != (self.message is not None):
            raise ValueError("message events require a message; control events do not")
        return self


class FixtureBatch(StrictModel):
    id: str = Field(pattern=TOKEN)
    events: list[FixtureEvent] = Field(min_length=1, max_length=50)


class MailboxFixture(StrictModel):
    format: Literal["desk-mailbox-fixture-v1"]
    account_id: str = Field(pattern=TOKEN)
    address: str = Field(pattern=r"^[^@\s]+@[^@\s]+$", max_length=200)
    batches: list[FixtureBatch] = Field(min_length=1, max_length=20)


@dataclass(frozen=True)
class FlatEvent:
    batch_id: str
    op: str
    message: FixtureMessage | None


def message_fingerprint(message: FixtureMessage) -> str:
    body = message.model_dump(mode="json", exclude_unset=True)
    return hashlib.sha256(encode(body).encode("utf-8")).hexdigest()


def load_fixture(name: str) -> MailboxFixture:
    """Validate a named fixture completely before the caller imports any row."""
    if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(NAME, name):
        raise DomainError("FIXTURE_INVALID", 422)
    path = (ROOT / f"{name}.json").resolve()
    root = ROOT.resolve()
    if path.parent != root or path.suffix != ".json":
        raise DomainError("FIXTURE_INVALID", 422)
    if not path.is_file():
        raise DomainError("FIXTURE_NOT_FOUND", 404)
    if path.stat().st_size > MAX_BYTES:
        raise DomainError("FIXTURE_INVALID", 422)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fixture = MailboxFixture.model_validate(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError):
        raise DomainError("FIXTURE_INVALID", 422) from None
    _validate_identity(fixture)
    return fixture


def flatten(fixture: MailboxFixture) -> list[FlatEvent]:
    return [
        FlatEvent(batch.id, event.op, event.message)
        for batch in fixture.batches
        for event in batch.events
    ]


def _validate_identity(fixture: MailboxFixture) -> None:
    batch_ids: set[str] = set()
    seen: dict[str, str] = {}
    histories: dict[int, str] = {}
    count = 0
    for batch in fixture.batches:
        if batch.id in batch_ids:
            raise DomainError("FIXTURE_INVALID", 422)
        batch_ids.add(batch.id)
        for event in batch.events:
            count += 1
            if event.message is None:
                continue
            digest = message_fingerprint(event.message)
            previous = seen.get(event.message.id)
            if previous is not None and previous != digest:
                raise DomainError("FIXTURE_INVALID", 422)
            seen[event.message.id] = digest
            owner = histories.get(event.message.history_id)
            if owner is not None and owner != event.message.id:
                raise DomainError("FIXTURE_INVALID", 422)
            histories[event.message.history_id] = event.message.id
    if count > 200:
        raise DomainError("FIXTURE_INVALID", 422)
