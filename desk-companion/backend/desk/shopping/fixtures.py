"""Offline shopping fixture files. No store account and no network."""

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from ..calendar import iso
from ..schemas import StrictModel
from ..store import DomainError, encode

FIXTURE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
SUBJECT = re.compile(r"^(?:product|order):[a-z0-9][a-z0-9-]{0,40}$")
MAX_BYTES = 256 * 1024
MAX_EVENTS = 100


class ShoppingEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=40)
    seq: int = Field(ge=1, le=100000)
    observed_at: datetime
    kind: Literal["cart_change", "price_drop", "out_of_stock", "order_shipped", "order_delayed"]
    sku: str | None = None
    order_id: str | None = None
    continues_subject: str | None = None
    title: str | None = Field(default=None, max_length=160)
    quantity: int | None = Field(default=None, ge=1, le=99)
    unit_price_cents: int | None = Field(default=None, ge=0, le=100_000_000)
    eta: str | None = Field(default=None, max_length=80)
    delay_reason: str | None = Field(default=None, max_length=300)

    @field_validator("event_id", "sku", "order_id")
    @classmethod
    def token(cls, value):
        if value is not None and not TOKEN.fullmatch(value):
            raise ValueError("Use a lowercase fixture token")
        return value

    @field_validator("continues_subject")
    @classmethod
    def subject(cls, value):
        if value is not None and not SUBJECT.fullmatch(value):
            raise ValueError("Use product: or order: plus a lowercase token")
        return value

    @field_validator("title", "eta", "delay_reason")
    @classmethod
    def text(cls, value):
        if value is None:
            return None
        if any(ord(char) < 32 for char in value):
            raise ValueError("Control characters are not allowed")
        stripped = value.strip()
        return stripped or None

    @field_validator("observed_at")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at requires a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def identity(self):
        if self.kind in {"cart_change", "price_drop", "out_of_stock"} and not (
            self.sku or self.continues_subject
        ):
            raise ValueError("A product event needs a sku or continues_subject")
        if self.kind in {"order_shipped", "order_delayed"} and not self.order_id:
            raise ValueError("An order event needs an order_id")
        if self.kind == "price_drop" and self.unit_price_cents is None:
            raise ValueError("A price event needs unit_price_cents")
        return self


class ShoppingFixture(StrictModel):
    fixture_id: str
    merchant: str = Field(default="offline-fixture", min_length=1, max_length=80)
    currency: str = Field(default="HKD", min_length=3, max_length=3)
    price_drop_threshold_bps: int = Field(default=500, ge=0, le=10000)
    events: list[ShoppingEvent] = Field(min_length=1, max_length=MAX_EVENTS)

    @field_validator("fixture_id")
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

    @field_validator("merchant")
    @classmethod
    def merchant_name(cls, value):
        if any(ord(char) < 32 for char in value) or not value.strip():
            raise ValueError("Merchant name is required")
        return value.strip()


def fingerprint(event: ShoppingEvent) -> str:
    return hashlib.sha256(encode(event.model_dump(mode="json")).encode()).hexdigest()


def subject_key(event: ShoppingEvent) -> str:
    if event.continues_subject:
        return event.continues_subject
    if event.sku:
        return "product:" + event.sku
    return "order:" + event.order_id


def observed_stamp(event: ShoppingEvent) -> str:
    return iso(event.observed_at)


def advice_note(fixture_id: str, event: ShoppingEvent, reason: str) -> str:
    detail = {
        "needs_decision": "This change needs a decision.",
        "price_drop": "The price dropped past the saved threshold.",
        "ship_delay": "The shipment is delayed.",
        "shipped": "The order shipped.",
    }[reason]
    parts = [detail]
    if event.quantity is not None:
        parts.append(f"Quantity {event.quantity}.")
    if event.unit_price_cents is not None:
        parts.append(f"Unit price {event.unit_price_cents} cents.")
    if event.order_id:
        parts.append(f"Order {event.order_id}.")
    if event.delay_reason:
        parts.append(event.delay_reason)
    note = (
        f"Source fixture {fixture_id} observed at {observed_stamp(event)}. "
        + " ".join(parts)
        + " No purchase or checkout was performed."
    )
    return note[:2000]


def display_title(event: ShoppingEvent) -> str:
    if event.title:
        return event.title
    if event.sku:
        return event.sku
    return "Order " + event.order_id


def parse_fixture(body: bytes) -> ShoppingFixture:
    if len(body) > MAX_BYTES or b"\x00" in body:
        raise DomainError("SHOPPING_FIXTURE_INVALID", 422)
    try:
        raw = json.loads(body.decode("utf-8"))
        fixture = ShoppingFixture.model_validate(raw)
    except (UnicodeError, ValueError, ValidationError):
        raise DomainError("SHOPPING_FIXTURE_INVALID", 422) from None
    return fixture


class FixtureCatalog:
    """Reads fixture JSON from one directory. Paths cannot escape that directory."""

    def __init__(self, directory):
        self.directory = Path(directory)

    def path_for(self, fixture_id: str) -> Path:
        if not isinstance(fixture_id, str) or not FIXTURE_ID.fullmatch(fixture_id):
            raise DomainError("SHOPPING_FIXTURE_INVALID", 422)
        root = self.directory.resolve()
        path = (root / f"{fixture_id}.json").resolve()
        if path.parent != root:
            raise DomainError("SHOPPING_FIXTURE_INVALID", 422)
        return path

    def load(self, fixture_id: str) -> ShoppingFixture:
        path = self.path_for(fixture_id)
        if not path.is_file():
            raise DomainError("SHOPPING_FIXTURE_NOT_FOUND", 404)
        fixture = parse_fixture(path.read_bytes())
        if fixture.fixture_id != fixture_id:
            raise DomainError("SHOPPING_FIXTURE_INVALID", 422)
        return fixture


def catalog_from_env() -> FixtureCatalog:
    override = os.environ.get("DESK_SHOPPING_FIXTURES")
    if override:
        return FixtureCatalog(override)
    default = Path(__file__).resolve().parents[3] / "fixtures" / "shopping"
    return FixtureCatalog(default)
