"""Local calendar fixtures. No network, credentials, or provider SDK."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from ..schemas import EventInput, Recurrence, StrictModel
from ..store import DomainError, encode

FORMAT = "desk-calendar-fixture-v1"
NAME = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
TOKEN = r"^[a-z0-9][a-z0-9-]{0,63}$"
ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "offline-calendar"
MAX_BYTES = 256 * 1024


class FixtureItem(StrictModel):
    """One offline event or series revision. Omitted schedule fields are not updates."""

    id: str = Field(pattern=TOKEN)
    sequence: int = Field(ge=1, le=1_000_000_000)
    observed_at: datetime
    title: str | None = Field(default=None, min_length=1, max_length=160)
    start_local: datetime | None = None
    end_local: datetime | None = None
    timezone: str | None = None
    location: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)
    reminder_minutes: list[int] | None = Field(default=None, max_length=4)
    busy: bool | None = None
    recurrence: Recurrence | None = None
    status: Literal["confirmed", "cancelled"] = "confirmed"
    prepare: bool = False
    needs_decision: bool = False
    rsvp: Literal["requested"] | None = None

    @field_validator("observed_at")
    @classmethod
    def utc_observation(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("observed_at must be explicit UTC")
        return value.astimezone(UTC)

    @field_validator("start_local", "end_local")
    @classmethod
    def local_wall(cls, value: datetime | None) -> datetime | None:
        return EventInput.local_datetime(value) if value else None

    @field_validator("timezone")
    @classmethod
    def zone(cls, value: str | None) -> str | None:
        return EventInput.valid_zone(value) if value else None

    @field_validator("title")
    @classmethod
    def title_value(cls, value: str | None) -> str | None:
        return EventInput.title_not_blank(value) if value else None

    @field_validator("reminder_minutes")
    @classmethod
    def reminders(cls, value: list[int] | None) -> list[int] | None:
        return EventInput.reminders(value) if value is not None else None

    @field_validator("location", "notes")
    @classmethod
    def single_line(cls, value: str | None) -> str | None:
        if value is not None and any(char in value for char in "\r\n\x00"):
            raise ValueError("Calendar text must be a single line")
        return value

    @model_validator(mode="after")
    def times_together(self):
        has_start = "start_local" in self.model_fields_set
        has_end = "end_local" in self.model_fields_set
        if has_start != has_end:
            raise ValueError("start_local and end_local must be provided together")
        return self


class FixtureEvent(StrictModel):
    op: Literal["upsert", "cancel", "interrupt", "revoke", "disconnect"]
    item: FixtureItem | None = None

    @model_validator(mode="after")
    def item_matches_op(self):
        needs_item = self.op in {"upsert", "cancel"}
        if needs_item != (self.item is not None):
            raise ValueError("upsert and cancel require an item; control events do not")
        return self


class FixtureBatch(StrictModel):
    id: str = Field(pattern=TOKEN)
    events: list[FixtureEvent] = Field(min_length=1, max_length=50)


class CalendarFixture(StrictModel):
    format: Literal["desk-calendar-fixture-v1"]
    account_id: str = Field(pattern=TOKEN)
    calendar_id: str = Field(pattern=TOKEN)
    batches: list[FixtureBatch] = Field(min_length=1, max_length=20)


@dataclass(frozen=True)
class FlatEvent:
    batch_id: str
    op: str
    item: FixtureItem | None


def item_fingerprint(item: FixtureItem, op: str = "upsert") -> str:
    body = item.model_dump(mode="json", exclude_unset=True)
    operation = "cancel" if op == "cancel" or item.status == "cancelled" else "upsert"
    return hashlib.sha256(
        encode({"operation": operation, "item": body}).encode("utf-8")
    ).hexdigest()


def load_fixture(name: str) -> CalendarFixture:
    """Validate a named fixture completely before the caller writes any row."""
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
        fixture = CalendarFixture.model_validate(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError):
        raise DomainError("FIXTURE_INVALID", 422) from None
    _validate_identity(fixture)
    return fixture


def flatten(fixture: CalendarFixture) -> list[FlatEvent]:
    return [
        FlatEvent(batch.id, event.op, event.item)
        for batch in fixture.batches
        for event in batch.events
    ]


def _validate_identity(fixture: CalendarFixture) -> None:
    batch_ids: set[str] = set()
    seen: dict[tuple[str, int], str] = {}
    sequences: dict[int, str] = {}
    count = 0
    for batch in fixture.batches:
        if batch.id in batch_ids:
            raise DomainError("FIXTURE_INVALID", 422)
        batch_ids.add(batch.id)
        for event in batch.events:
            count += 1
            if event.item is None:
                continue
            digest = item_fingerprint(event.item, event.op)
            identity = (event.item.id, event.item.sequence)
            previous = seen.get(identity)
            if previous is not None and previous != digest:
                raise DomainError("FIXTURE_INVALID", 422)
            seen[identity] = digest
            owner = sequences.get(event.item.sequence)
            if owner is not None and owner != event.item.id:
                raise DomainError("FIXTURE_INVALID", 422)
            sequences[event.item.sequence] = event.item.id
    if count > 200:
        raise DomainError("FIXTURE_INVALID", 422)
