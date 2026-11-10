"""Offline trip-quote files. No airline, payment, or network."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, ValidationError, field_validator, model_validator

from ..schemas import StrictModel
from ..store import DomainError, encode

FIXTURE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
AIRPORT = re.compile(r"^[A-Z]{3}$")
LOCAL_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
QUOTE_HASH = re.compile(r"^[a-f0-9]{64}$")
MAX_BYTES = 256 * 1024
MAX_EVENTS = 100
TERMS = (
    "origin",
    "destination",
    "depart_local",
    "arrive_local",
    "timezone",
    "arrive_timezone",
    "passengers",
    "baggage_kg",
    "total_cents",
    "currency",
    "fare_rules",
)
QUOTE_REQUIRED = tuple(key for key in TERMS if key != "currency")


def quote_id(terms: dict) -> str:
    body = {key: terms[key] for key in TERMS}
    if any(body[key] is None or body[key] == "" for key in TERMS):
        raise DomainError("TRIP_QUOTE_INCOMPLETE", 422)
    return hashlib.sha256(encode(body).encode()).hexdigest()


def _text(value: str) -> str:
    if any(ord(char) < 32 for char in value):
        raise ValueError("Control characters are not allowed")
    stripped = value.strip()
    if not stripped:
        raise ValueError("Omit a field to leave it unchanged")
    return stripped


class TripEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=40)
    seq: int = Field(ge=1, le=100000)
    observed_at: datetime
    kind: Literal["quote", "reprice", "schedule_change", "payment_failed", "ticketed"]
    origin: str | None = None
    destination: str | None = None
    depart_local: str | None = None
    arrive_local: str | None = None
    timezone: str | None = None
    arrive_timezone: str | None = None
    passengers: int | None = Field(default=None, ge=1, le=9)
    baggage_kg: int | None = Field(default=None, ge=0, le=60)
    total_cents: int | None = Field(default=None, ge=0, le=100_000_000)
    fare_rules: str | None = Field(default=None, max_length=300)
    next_step: str | None = Field(default=None, max_length=500)
    waiting_for: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=300)
    covers_quote: str | None = None
    receipt_id: str | None = None

    @field_validator("event_id", "receipt_id")
    @classmethod
    def token(cls, value):
        if value is not None and not TOKEN.fullmatch(value):
            raise ValueError("Use a lowercase fixture token")
        return value

    @field_validator("origin", "destination")
    @classmethod
    def airport(cls, value):
        if value is not None and not AIRPORT.fullmatch(value):
            raise ValueError("Use a three-letter airport code")
        return value

    @field_validator("depart_local", "arrive_local")
    @classmethod
    def local_time(cls, value):
        if value is None:
            return None
        if not LOCAL_TIME.fullmatch(value):
            raise ValueError("Use YYYY-MM-DDTHH:MM without an offset")
        datetime.fromisoformat(value)
        return value

    @field_validator("timezone", "arrive_timezone")
    @classmethod
    def zone(cls, value):
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("Use an IANA timezone") from None
        return value

    @field_validator("fare_rules", "next_step", "waiting_for", "reason")
    @classmethod
    def prose(cls, value):
        return None if value is None else _text(value)

    @field_validator("covers_quote")
    @classmethod
    def quote_hash(cls, value):
        if value is not None and not QUOTE_HASH.fullmatch(value):
            raise ValueError("covers_quote must be the current quote id")
        return value

    @field_validator("observed_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at requires a timezone")
        return value

    @model_validator(mode="after")
    def present_fields(self):
        optional = (
            "origin",
            "destination",
            "depart_local",
            "arrive_local",
            "timezone",
            "arrive_timezone",
            "passengers",
            "baggage_kg",
            "total_cents",
            "fare_rules",
            "next_step",
            "waiting_for",
            "reason",
            "covers_quote",
            "receipt_id",
        )
        for name in optional:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError("Omit a field to leave it unchanged")
        if self.kind == "quote":
            missing = [name for name in QUOTE_REQUIRED if getattr(self, name) is None]
            if missing:
                raise ValueError("A quote needs the full itinerary")
        if self.kind == "reprice" and self.total_cents is None:
            raise ValueError("A reprice needs total_cents")
        if self.kind == "schedule_change" and not (self.depart_local or self.arrive_local):
            raise ValueError("A schedule change needs a departure or arrival time")
        if self.kind == "payment_failed" and not self.reason:
            raise ValueError("A payment failure needs a reason")
        if self.kind == "ticketed" and not (self.covers_quote and self.receipt_id):
            raise ValueError("A ticket event needs covers_quote and receipt_id")
        return self


class TripFixture(StrictModel):
    fixture_id: str
    itinerary_id: str
    carrier: str = Field(default="offline-fixture", min_length=1, max_length=80)
    currency: str = Field(min_length=3, max_length=3)
    events: list[TripEvent] = Field(min_length=1, max_length=MAX_EVENTS)

    @field_validator("fixture_id", "itinerary_id")
    @classmethod
    def identifier(cls, value):
        if not FIXTURE_ID.fullmatch(value):
            raise ValueError("Use a lowercase fixture id")
        return value

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value):
        if not value.isalpha() or not value.isupper():
            raise ValueError("Use an uppercase currency code")
        return value

    @field_validator("carrier")
    @classmethod
    def carrier_name(cls, value):
        return _text(value)

    @model_validator(mode="after")
    def unique_events(self):
        ids = [event.event_id for event in self.events]
        seqs = [event.seq for event in self.events]
        if len(ids) != len(set(ids)) or len(seqs) != len(set(seqs)):
            raise ValueError("Event ids and sequence numbers must be unique")
        return self


def event_body(event: TripEvent) -> dict:
    """Only fields the fixture sent. Omitted fields must not come back as nulls."""
    return event.model_dump(mode="json", exclude_unset=True)


def fingerprint(event: TripEvent) -> str:
    return hashlib.sha256(encode(event_body(event)).encode()).hexdigest()


def parse_fixture(body: bytes) -> TripFixture:
    if len(body) > MAX_BYTES or b"\x00" in body:
        raise DomainError("TRIP_FIXTURE_INVALID", 422)
    try:
        import json

        fixture = TripFixture.model_validate(json.loads(body.decode("utf-8")))
    except (UnicodeError, ValueError, ValidationError):
        raise DomainError("TRIP_FIXTURE_INVALID", 422) from None
    return fixture


class FixtureCatalog:
    """Read one directory of fixture JSON. Paths cannot leave that directory."""

    def __init__(self, directory):
        self.directory = Path(directory)

    def path_for(self, fixture_id: str) -> Path:
        if not isinstance(fixture_id, str) or not FIXTURE_ID.fullmatch(fixture_id):
            raise DomainError("TRIP_FIXTURE_INVALID", 422)
        root = self.directory.resolve()
        path = (root / f"{fixture_id}.json").resolve()
        if path.parent != root:
            raise DomainError("TRIP_FIXTURE_INVALID", 422)
        return path

    def load(self, fixture_id: str) -> TripFixture:
        path = self.path_for(fixture_id)
        if not path.is_file():
            raise DomainError("TRIP_FIXTURE_NOT_FOUND", 404)
        fixture = parse_fixture(path.read_bytes())
        if fixture.fixture_id != fixture_id:
            raise DomainError("TRIP_FIXTURE_INVALID", 422)
        return fixture


def catalog_from_env() -> FixtureCatalog:
    override = os.environ.get("DESK_TRAVEL_FIXTURES")
    if override:
        return FixtureCatalog(override)
    return FixtureCatalog(Path(__file__).resolve().parents[3] / "fixtures" / "travel")
