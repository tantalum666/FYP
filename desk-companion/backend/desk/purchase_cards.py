"""Owner-confirmed staple purchase card.

A card records what the owner already authorized: item, quantity, merchants,
a budget that includes shipping, whether a cheaper same-spec substitute is
allowed, and an address label. An offline offer is checked against that card.
Nothing here places an order, calls a merchant, or treats a missing receipt
as a purchase.

Portable mailbox, shopping, and offline-calendar bundles are not extended.
"""

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from .calendar import iso
from .notify import Notice
from .schemas import StrictModel
from .store import DomainError, encode
from .tasks import TaskAction, TaskInput
from .workspace_data import is_quiet

TOKEN_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CARD_LIMIT = 20
OFFER_LIMIT = 50
APPROVAL_NOTE = "Approved to prepare this offer. No order was placed."
RECEIPT_NOTE = "Fixture receipt {receipt_id} recorded. This is not a live purchase or payment."


def _token(value: str) -> str:
    text = value.strip().lower()
    if TOKEN_RE.fullmatch(text) is None or len(text) > 64:
        raise ValueError("Use lowercase letters, digits, and hyphens")
    return text


def _label(value: str) -> str:
    text = value.strip()
    if not text or len(text) > 80 or any(ch in text for ch in "\r\n\t"):
        raise ValueError("Enter a short item name")
    return text


def _currency(value: str) -> str:
    text = value.strip().upper()
    if len(text) != 3 or not text.isalpha():
        raise ValueError("Use a three-letter currency")
    return text


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Offer time needs a timezone")
    return value


def offer_total(quantity: int, unit_price_minor: int, shipping_minor: int) -> int:
    total = quantity * unit_price_minor + shipping_minor
    if total < 0 or total > 10**12:
        raise DomainError("PURCHASE_TOTAL_INVALID", 422)
    return total


def classify(card: dict, offer: dict) -> tuple[str, str | None]:
    """Match an offer to the confirmed card. A match still needs a fresh approval."""
    if offer["currency"] != card["currency"]:
        return "refused", "currency_mismatch"
    if offer["merchant"] not in card["merchants"]:
        return "refused", "merchant_not_allowed"
    if offer["address_scope"] != card["address_scope"]:
        return "refused", "address_scope_mismatch"
    if offer["quantity"] != card["quantity"] or offer["unit"] != card["unit"]:
        return "refused", "spec_mismatch"
    same_item = offer["sku"] == card["sku"]
    if not same_item and (card["substitution"] != "same_spec_cheaper" or not offer["same_spec"]):
        return "refused", "spec_mismatch"
    total = offer_total(offer["quantity"], offer["unit_price_minor"], offer["shipping_minor"])
    if total > card["budget_minor"]:
        return "refused", "over_budget"
    if not same_item:
        reference = offer.get("reference_total_minor")
        if reference is None:
            return "refused", "reference_price_required"
        if total >= reference:
            return "refused", "not_cheaper"
    return "needs_approval", None


def _notice_id(card_id: str, offer_id: str, version: int, state: str) -> str:
    material = f"{card_id}/{offer_id}/{version}/{state}"
    return "buy-" + hashlib.sha256(material.encode()).hexdigest()[:32]


class CardCreate(StrictModel):
    label: str
    sku: str
    quantity: int = Field(ge=1, le=99, strict=True)
    unit: str
    merchants: list[str] = Field(min_length=1, max_length=5)
    budget_minor: int = Field(ge=1, le=10_000_000, strict=True)
    currency: str
    substitution: Literal["none", "same_spec_cheaper"]
    address_scope: str

    @field_validator("label")
    @classmethod
    def label_value(cls, value: str) -> str:
        return _label(value)

    @field_validator("sku", "unit", "address_scope")
    @classmethod
    def token_value(cls, value: str) -> str:
        return _token(value)

    @field_validator("currency")
    @classmethod
    def currency_value(cls, value: str) -> str:
        return _currency(value)

    @field_validator("merchants")
    @classmethod
    def merchant_values(cls, value: list[str]) -> list[str]:
        items = [_token(item) for item in value]
        if len(set(items)) != len(items):
            raise ValueError("Merchants must be unique")
        return items


class CardVersion(StrictModel):
    expected_version: int = Field(ge=1, strict=True)


class CardPatch(CardVersion):
    label: str | None = None
    sku: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=99, strict=True)
    unit: str | None = None
    merchants: list[str] | None = Field(default=None, min_length=1, max_length=5)
    budget_minor: int | None = Field(default=None, ge=1, le=10_000_000, strict=True)
    currency: str | None = None
    substitution: Literal["none", "same_spec_cheaper"] | None = None
    address_scope: str | None = None

    @field_validator("label")
    @classmethod
    def label_value(cls, value: str | None) -> str | None:
        return None if value is None else _label(value)

    @field_validator("sku", "unit", "address_scope")
    @classmethod
    def token_value(cls, value: str | None) -> str | None:
        return None if value is None else _token(value)

    @field_validator("currency")
    @classmethod
    def currency_value(cls, value: str | None) -> str | None:
        return None if value is None else _currency(value)

    @field_validator("merchants")
    @classmethod
    def merchant_values(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        items = [_token(item) for item in value]
        if len(set(items)) != len(items):
            raise ValueError("Merchants must be unique")
        return items


class OfferInput(StrictModel):
    offer_id: str
    merchant: str
    sku: str
    quantity: int = Field(ge=1, le=99, strict=True)
    unit: str
    unit_price_minor: int = Field(ge=0, le=10_000_000, strict=True)
    shipping_minor: int = Field(ge=0, le=10_000_000, strict=True)
    currency: str
    address_scope: str
    observed_at: datetime
    same_spec: bool = False
    reference_total_minor: int | None = Field(default=None, ge=1, le=10_000_000, strict=True)
    interrupt: Literal["write", "open"] | None = None

    @field_validator("offer_id", "merchant", "sku", "unit", "address_scope")
    @classmethod
    def token_value(cls, value: str) -> str:
        return _token(value)

    @field_validator("currency")
    @classmethod
    def currency_value(cls, value: str) -> str:
        return _currency(value)

    @field_validator("observed_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        return _aware(value)


class ApprovalInput(CardVersion):
    interrupt: Literal["hold"] | None = None


class ReceiptInput(StrictModel):
    receipt_id: str
    interrupt: Literal["write"] | None = None

    @field_validator("receipt_id")
    @classmethod
    def token_value(cls, value: str) -> str:
        return _token(value)


def _operation_key(key: str) -> str:
    if not isinstance(key, str) or not key.strip() or len(key) > 100:
        raise DomainError("OPERATION_ID_REQUIRED", 422)
    if key.startswith("assistant-confirm/"):
        raise DomainError("RESERVED_OPERATION_ID", 422)
    return key


def _commercial(offer: OfferInput) -> dict:
    return {
        "address_scope": offer.address_scope,
        "currency": offer.currency,
        "merchant": offer.merchant,
        "observed_at": iso(offer.observed_at),
        "offer_id": offer.offer_id,
        "quantity": offer.quantity,
        "same_spec": offer.same_spec,
        "reference_total_minor": offer.reference_total_minor,
        "shipping_minor": offer.shipping_minor,
        "sku": offer.sku,
        "unit": offer.unit,
        "unit_price_minor": offer.unit_price_minor,
    }


class PurchaseNotices:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS purchase_notice_holds("
                "notice_id TEXT PRIMARY KEY, card_id TEXT NOT NULL, "
                "offer_id TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def hold(self, conn, notice: Notice, card_id: str, offer_id: str) -> bool:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO purchase_notice_holds VALUES(?,?,?,?)",
            (notice.id, card_id, offer_id, encode(asdict(notice))),
        )
        return cursor.rowcount == 1

    def publish(self, notice: Notice, *, quiet: bool) -> str:
        if quiet:
            return "held"
        results = self.runtime.notify.publish(notice, quiet=False)
        delivered = any(row["status"] in {"delivered", "duplicate"} for row in results)
        if delivered:
            with self.store.connection(write=True) as conn:
                conn.execute("DELETE FROM purchase_notice_holds WHERE notice_id=?", (notice.id,))
            return (
                "delivered" if any(row["status"] == "delivered" for row in results) else "duplicate"
            )
        return "held"

    def release(self, *, quiet: bool) -> None:
        if quiet:
            return
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM purchase_notice_holds ORDER BY notice_id"
            ).fetchall()
        for row in rows:
            self.publish(Notice(**json.loads(row["payload"])), quiet=False)


class PurchaseCardService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.notices = PurchaseNotices(runtime)
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS purchase_cards (
                    id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    merchants TEXT NOT NULL,
                    budget_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    substitution TEXT NOT NULL,
                    address_scope TEXT NOT NULL,
                    task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS purchase_offers (
                    card_id TEXT NOT NULL,
                    offer_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    card_version INTEGER NOT NULL,
                    merchant TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    unit_price_minor INTEGER NOT NULL,
                    shipping_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    same_spec INTEGER NOT NULL,
                    address_scope TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    total_minor INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    reason TEXT,
                    task_id TEXT,
                    receipt_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (card_id, offer_id)
                );
                CREATE TABLE IF NOT EXISTS purchase_claims (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    response TEXT
                );
                """
            )

    def release_quiet_notices(self) -> None:
        self.notices.release(quiet=self._quiet())

    def listing(self, principal) -> dict:
        self._owner(principal)
        with self.store.connection() as conn:
            rows = conn.execute("SELECT * FROM purchase_cards ORDER BY created_at, id").fetchall()
            cards = [self._card_view(conn, row) for row in rows]
        return {"cards": cards, "purchased": False, "live_purchase": False}

    def create(self, payload: CardCreate, key: str, principal) -> dict:
        self._owner(principal)
        key = _operation_key(key)
        fingerprint = encode(payload.model_dump(mode="json"))

        def produce(conn):
            count = conn.execute("SELECT COUNT(*) FROM purchase_cards").fetchone()[0]
            if count >= CARD_LIMIT:
                raise DomainError("PURCHASE_CARD_LIMIT", 422)
            now = iso(self.store.clock())
            card_id = uuid4().hex
            conn.execute(
                "INSERT INTO purchase_cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    card_id,
                    "draft",
                    1,
                    payload.label,
                    payload.sku,
                    payload.quantity,
                    payload.unit,
                    encode(payload.merchants),
                    payload.budget_minor,
                    payload.currency,
                    payload.substitution,
                    payload.address_scope,
                    None,
                    now,
                    now,
                ),
            )
            return {"card": self._card_view(conn, self._card_row(conn, card_id)), "saved": True}

        return self._commit(key, fingerprint, produce, principal)

    def confirm(self, card_id: str, payload: CardVersion, key: str, principal) -> dict:
        self._owner(principal)
        key = _operation_key(key)

        def produce(conn):
            card = self._card(self._card_row(conn, card_id))
            if card["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            if card["state"] == "revoked":
                raise DomainError("PURCHASE_CARD_REVOKED", 409)
            if card["state"] == "draft":
                now = iso(self.store.clock())
                conn.execute(
                    "UPDATE purchase_cards SET state='confirmed', updated_at=? WHERE id=?",
                    (now, card_id),
                )
            return {"card": self._card_view(conn, self._card_row(conn, card_id)), "saved": True}

        return self._commit(
            key,
            encode(
                {
                    "card_id": card_id,
                    "action": "confirm",
                    "expected_version": payload.expected_version,
                }
            ),
            produce,
            principal,
        )

    def update(self, card_id: str, payload: CardPatch, key: str, principal) -> dict:
        self._owner(principal)
        key = _operation_key(key)
        provided = self._provided(payload)
        fingerprint = encode(
            {
                "card_id": card_id,
                "action": "update",
                "fields": provided,
                "expected_version": payload.expected_version,
            }
        )

        def produce(conn):
            card = self._card(self._card_row(conn, card_id))
            if card["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            if card["state"] == "revoked":
                raise DomainError("PURCHASE_CARD_REVOKED", 409)
            if not provided:
                return {
                    "card": self._card_view(conn, self._card_row(conn, card_id)),
                    "saved": False,
                }
            assignments = []
            values = []
            for name, value in provided.items():
                assignments.append(f"{name}=?")
                values.append(encode(value) if name == "merchants" else value)
            version = card["version"] + 1
            now = iso(self.store.clock())
            assignments.extend(["version=?", "updated_at=?"])
            values.extend([version, now, card_id])
            conn.execute(
                f"UPDATE purchase_cards SET {', '.join(assignments)} WHERE id=?",
                values,
            )
            conn.execute(
                "UPDATE purchase_offers SET state='needs_reapproval', reason='card_changed', "
                "updated_at=? WHERE card_id=? AND state IN ('needs_approval', 'approved') "
                "AND receipt_id IS NULL",
                (now, card_id),
            )
            return {"card": self._card_view(conn, self._card_row(conn, card_id)), "saved": True}

        return self._commit(key, fingerprint, produce, principal)

    def revoke(self, card_id: str, key: str, principal) -> dict:
        self._owner(principal)
        key = _operation_key(key)

        def produce(conn):
            card = self._card(self._card_row(conn, card_id))
            now = iso(self.store.clock())
            if card["state"] != "revoked":
                conn.execute(
                    "UPDATE purchase_cards SET state='revoked', updated_at=? WHERE id=?",
                    (now, card_id),
                )
                conn.execute(
                    "UPDATE purchase_offers SET state='closed', reason='card_revoked', updated_at=? "
                    "WHERE card_id=? AND state IN ('opened', 'needs_approval', 'approved', "
                    "'needs_reapproval') AND receipt_id IS NULL",
                    (now, card_id),
                )
            return {
                "card": self._card_view(conn, self._card_row(conn, card_id)),
                "revoked": True,
                "saved": True,
            }

        return self._commit(
            key, encode({"card_id": card_id, "action": "revoke"}), produce, principal
        )

    def submit_offer(self, card_id: str, payload: OfferInput, key: str, principal) -> dict:
        self._owner(principal)
        key = _operation_key(key)
        commercial = _commercial(payload)
        fingerprint = encode({"card_id": card_id, "action": "offer", **commercial})
        notice = None
        with self.store.connection(write=True) as conn:
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            replay = self._claim(conn, key, fingerprint)
            if replay is not None:
                body = replay
            else:
                body, notice = self._offer_work(
                    conn, card_id, commercial, encode(commercial), payload.interrupt
                )
                if body["completed"]:
                    self._store_claim(conn, key, body)
        if notice is not None and body.get("completed"):
            self.notices.publish(notice, quiet=self._quiet())
        return self._raise_if_needed(body)

    def approve(self, card_id: str, offer_id: str, payload: ApprovalInput, key: str, principal):
        self._owner(principal)
        key = _operation_key(key)
        fingerprint = encode(
            {
                "card_id": card_id,
                "offer_id": offer_id,
                "action": "approve",
                "expected_version": payload.expected_version,
            }
        )
        with self.store.connection(write=True) as conn:
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            replay = self._claim(conn, key, fingerprint)
            if replay is not None:
                body = replay
            else:
                card = self._card(self._card_row(conn, card_id))
                if card["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
                body = self._approve_work(conn, card_id, offer_id, payload.interrupt)
                if body["completed"] or body.get("code") == "STALE_CARD":
                    self._store_claim(conn, key, body)
        return self._raise_if_needed(body)

    def record_receipt(
        self, card_id: str, offer_id: str, payload: ReceiptInput, key: str, principal
    ):
        self._owner(principal)
        key = _operation_key(key)
        fingerprint = encode(
            {
                "card_id": card_id,
                "offer_id": offer_id,
                "action": "receipt",
                "receipt_id": payload.receipt_id,
            }
        )
        with self.store.connection(write=True) as conn:
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            replay = self._claim(conn, key, fingerprint)
            if replay is not None:
                body = replay
            else:
                body = self._receipt_work(
                    conn, card_id, offer_id, payload.receipt_id, payload.interrupt
                )
                if body["completed"] or body.get("code") == "STALE_CARD":
                    self._store_claim(conn, key, body)
        return self._raise_if_needed(body)

    def _offer_work(self, conn, card_id, commercial, fingerprint, interrupt):
        card = self._card(self._card_row(conn, card_id))
        if card["state"] == "revoked":
            raise DomainError("PURCHASE_CARD_REVOKED", 409)
        if card["state"] != "confirmed":
            raise DomainError("PURCHASE_CARD_NOT_CONFIRMED", 409)
        existing = self._offer_row(conn, card_id, commercial["offer_id"])
        if existing and existing["fingerprint"] != fingerprint:
            raise DomainError("PURCHASE_OFFER_CONFLICT", 409)
        if interrupt == "write" and existing is None:
            return self._interrupted(card, commercial, None), None
        if existing is None:
            count = conn.execute(
                "SELECT COUNT(*) FROM purchase_offers WHERE card_id=?", (card_id,)
            ).fetchone()[0]
            if count >= OFFER_LIMIT:
                raise DomainError("PURCHASE_OFFER_LIMIT", 422)
            task_id = card["task_id"] or self._create_task(conn, card)
            self._insert_offer(conn, card, commercial, fingerprint, task_id)
            existing = self._offer_row(conn, card_id, commercial["offer_id"])
        if interrupt == "open" and existing["state"] == "opened":
            return self._interrupted(card, commercial, existing), None
        if existing["state"] in {"approved", "receipt_recorded", "closed"}:
            return self._outcome(existing), None
        if (
            existing["state"] == "needs_approval"
            and existing["card_version"] == card["version"]
            and existing["fingerprint"] == fingerprint
        ):
            return self._outcome(existing), None
        offer = {**commercial, "same_spec": bool(commercial["same_spec"])}
        state, reason = classify(card, offer)
        total = offer_total(offer["quantity"], offer["unit_price_minor"], offer["shipping_minor"])
        now = iso(self.store.clock())
        conn.execute(
            "UPDATE purchase_offers SET state=?, reason=?, card_version=?, total_minor=?, "
            "updated_at=? WHERE card_id=? AND offer_id=?",
            (state, reason, card["version"], total, now, card_id, commercial["offer_id"]),
        )
        existing = self._offer_row(conn, card_id, commercial["offer_id"])
        notice = self._notice(card_id, existing)
        if not self.notices.hold(conn, notice, card_id, commercial["offer_id"]):
            notice = None
        return self._outcome(existing), notice

    def _approve_work(self, conn, card_id, offer_id, interrupt):
        card = self._card(self._card_row(conn, card_id))
        offer = self._require_offer(conn, card_id, offer_id)
        if card["state"] != "confirmed":
            raise DomainError("PURCHASE_CARD_REVOKED", 409)
        if offer["state"] == "approved":
            return self._outcome(offer)
        if offer["state"] == "needs_reapproval" or (
            offer["state"] == "needs_approval" and offer["card_version"] != card["version"]
        ):
            self._mark_reapproval(conn, card_id, offer_id)
            return self._stale(card, self._offer_row(conn, card_id, offer_id))
        if offer["state"] != "needs_approval":
            raise DomainError("PURCHASE_APPROVAL_NOT_READY", 409)
        if interrupt == "hold":
            return self._interrupted(card, offer, offer)
        self._set_waiting(
            conn,
            offer["task_id"],
            "Fixture receipt",
            APPROVAL_NOTE,
        )
        now = iso(self.store.clock())
        conn.execute(
            "UPDATE purchase_offers SET state='approved', reason=NULL, updated_at=? "
            "WHERE card_id=? AND offer_id=?",
            (now, card_id, offer_id),
        )
        return self._outcome(self._offer_row(conn, card_id, offer_id))

    def _receipt_work(self, conn, card_id, offer_id, receipt_id, interrupt):
        card = self._card(self._card_row(conn, card_id))
        offer = self._require_offer(conn, card_id, offer_id)
        if offer["state"] == "receipt_recorded":
            if offer["receipt_id"] == receipt_id:
                return self._outcome(offer)
            raise DomainError("PURCHASE_RECEIPT_CONFLICT", 409)
        if offer["state"] == "needs_reapproval" or (
            offer["state"] == "approved" and offer["card_version"] != card["version"]
        ):
            if offer["state"] == "approved":
                self._mark_reapproval(conn, card_id, offer_id)
            fresh = self._offer_row(conn, card_id, offer_id)
            return {**self._outcome(fresh), "completed": False, "code": "STALE_CARD", "status": 409}
        if offer["state"] != "approved":
            return {
                **self._outcome(offer),
                "completed": False,
                "code": "PURCHASE_RECEIPT_NOT_READY",
                "status": 409,
            }
        if interrupt == "write":
            return self._interrupted(card, offer, offer)
        self._set_waiting(
            conn,
            offer["task_id"],
            f"Fixture receipt {receipt_id} recorded. Not a live purchase.",
            RECEIPT_NOTE.format(receipt_id=receipt_id),
        )
        now = iso(self.store.clock())
        conn.execute(
            "UPDATE purchase_offers SET state='receipt_recorded', receipt_id=?, updated_at=? "
            "WHERE card_id=? AND offer_id=?",
            (receipt_id, now, card_id, offer_id),
        )
        return self._outcome(self._offer_row(conn, card_id, offer_id))

    def _create_task(self, conn, card) -> str:
        task = self.runtime.tasks.insert_task(
            conn,
            TaskInput(
                title=card["label"],
                status="todo",
                follow_up_enabled=False,
                visibility="private",
                next_step="",
                waiting_for="",
            ),
            "purchase_card",
        )
        conn.execute("UPDATE purchase_cards SET task_id=? WHERE id=?", (task["id"], card["id"]))
        return task["id"]

    def _insert_offer(self, conn, card, commercial, fingerprint, task_id) -> None:
        now = iso(self.store.clock())
        total = offer_total(
            commercial["quantity"], commercial["unit_price_minor"], commercial["shipping_minor"]
        )
        conn.execute(
            "INSERT INTO purchase_offers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                card["id"],
                commercial["offer_id"],
                fingerprint,
                0,
                commercial["merchant"],
                commercial["sku"],
                commercial["quantity"],
                commercial["unit"],
                commercial["unit_price_minor"],
                commercial["shipping_minor"],
                commercial["currency"],
                int(commercial["same_spec"]),
                commercial["address_scope"],
                commercial["observed_at"],
                total,
                "opened",
                None,
                task_id,
                None,
                now,
                now,
            ),
        )

    def _set_waiting(self, conn, task_id, waiting_for, note) -> None:
        current = self.runtime.tasks.get(conn, task_id)
        data = {name: current[name] for name in TaskInput.model_fields}
        data["status"] = "waiting"
        data["waiting_for"] = waiting_for
        self.runtime.tasks.apply_action(
            conn,
            task_id,
            TaskAction(
                action="update",
                expected_version=current["version"],
                task=TaskInput.model_validate(data),
                note=note,
            ),
            "purchase_card",
        )

    def _mark_reapproval(self, conn, card_id, offer_id) -> None:
        conn.execute(
            "UPDATE purchase_offers SET state='needs_reapproval', reason='card_changed', "
            "updated_at=? WHERE card_id=? AND offer_id=? AND receipt_id IS NULL",
            (iso(self.store.clock()), card_id, offer_id),
        )

    def _notice(self, card_id, offer) -> Notice:
        return Notice(
            id=_notice_id(card_id, offer["offer_id"], offer["card_version"], offer["state"]),
            kind="purchase_card",
            title_en="Purchase decision",
            title_zh="购买待决定",
            body_en="A saved item needs a decision. Nothing was bought.",
            body_zh="一件已保存的商品需要决定。没有购买。",
            reason_en="The offer was checked against the saved card.",
            reason_zh="已按保存的购买卡片核对这次报价。",
        )

    def _commit(self, key, fingerprint, produce, principal) -> dict:
        with self.store.connection(write=True) as conn:
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            replay = self._claim(conn, key, fingerprint)
            if replay is not None:
                body = replay
            else:
                body = produce(conn)
                body = self._flags(body)
                self._store_claim(conn, key, body)
        return self._raise_if_needed(body)

    def _claim(self, conn, key, fingerprint):
        row = conn.execute(
            "SELECT fingerprint, response FROM purchase_claims WHERE id=?", (key,)
        ).fetchone()
        if row is None:
            conn.execute("INSERT INTO purchase_claims VALUES(?,?,NULL)", (key, fingerprint))
            return None
        if row["fingerprint"] != fingerprint:
            raise DomainError("OPERATION_ID_CONFLICT")
        if row["response"] is None:
            return None
        return json.loads(row["response"])

    def _store_claim(self, conn, key, body) -> None:
        conn.execute("UPDATE purchase_claims SET response=? WHERE id=?", (encode(body), key))

    def _owner(self, principal) -> None:
        token = principal.get("session") if isinstance(principal, dict) else None
        if not isinstance(principal, dict) or principal.get("kind") != "owner":
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not self.store.session_valid(token):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)

    def _quiet(self) -> bool:
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(self.runtime.data.preferences(), self.store.clock().astimezone(zone))

    def _card_row(self, conn, card_id):
        if not isinstance(card_id, str) or len(card_id) != 32:
            raise DomainError("PURCHASE_CARD_NOT_FOUND", 404)
        row = conn.execute("SELECT * FROM purchase_cards WHERE id=?", (card_id,)).fetchone()
        if row is None:
            raise DomainError("PURCHASE_CARD_NOT_FOUND", 404)
        return row

    def _card(self, row) -> dict:
        card = dict(row)
        card["merchants"] = json.loads(card["merchants"])
        return card

    def _offer_row(self, conn, card_id, offer_id):
        row = conn.execute(
            "SELECT * FROM purchase_offers WHERE card_id=? AND offer_id=?",
            (card_id, offer_id),
        ).fetchone()
        return None if row is None else dict(row)

    def _require_offer(self, conn, card_id, offer_id):
        self._card_row(conn, card_id)
        offer = self._offer_row(conn, card_id, offer_id)
        if offer is None:
            raise DomainError("PURCHASE_OFFER_NOT_FOUND", 404)
        return offer

    def _card_view(self, conn, row) -> dict:
        card = self._card(row)
        offers = [
            self._offer_view(item)
            for item in conn.execute(
                "SELECT * FROM purchase_offers WHERE card_id=? ORDER BY created_at DESC, offer_id "
                "LIMIT 20",
                (card["id"],),
            ).fetchall()
        ]
        return {
            "id": card["id"],
            "state": card["state"],
            "version": card["version"],
            "label": card["label"],
            "sku": card["sku"],
            "quantity": card["quantity"],
            "unit": card["unit"],
            "merchants": card["merchants"],
            "budget_minor": card["budget_minor"],
            "currency": card["currency"],
            "substitution": card["substitution"],
            "address_scope": card["address_scope"],
            "task_id": card["task_id"],
            "offers": offers,
            "purchased": False,
            "live_purchase": False,
        }

    @staticmethod
    def _offer_view(row) -> dict:
        offer = dict(row)
        return {
            "offer_id": offer["offer_id"],
            "state": offer["state"],
            "reason": offer["reason"],
            "total_minor": offer["total_minor"],
            "card_version": offer["card_version"],
            "merchant": offer["merchant"],
            "sku": offer["sku"],
            "quantity": offer["quantity"],
            "unit": offer["unit"],
            "unit_price_minor": offer["unit_price_minor"],
            "shipping_minor": offer["shipping_minor"],
            "currency": offer["currency"],
            "same_spec": bool(offer["same_spec"]),
            "address_scope": offer["address_scope"],
            "observed_at": offer["observed_at"],
            "task_id": offer["task_id"],
            "receipt_id": offer["receipt_id"],
            "purchased": False,
            "live_purchase": False,
        }

    def _outcome(self, offer) -> dict:
        return {
            **self._flags({}),
            "completed": True,
            "stopped": None,
            "card_id": offer["card_id"],
            "offer_id": offer["offer_id"],
            "task_id": offer["task_id"],
            "state": offer["state"],
            "reason": offer["reason"],
            "total_minor": offer["total_minor"],
            "card_version": offer["card_version"],
            "receipt_id": offer["receipt_id"],
        }

    def _interrupted(self, card, commercial, existing) -> dict:
        return {
            **self._flags({}),
            "completed": False,
            "stopped": "interrupted",
            "card_id": card["id"],
            "offer_id": commercial["offer_id"],
            "task_id": None if existing is None else existing["task_id"],
            "state": "unopened" if existing is None else existing["state"],
            "reason": None,
            "total_minor": None if existing is None else existing["total_minor"],
            "card_version": card["version"],
            "receipt_id": None,
        }

    def _stale(self, card, offer) -> dict:
        fresh = offer
        return {
            **self._outcome(fresh),
            "completed": False,
            "card_id": card["id"],
            "state": "needs_reapproval",
            "reason": "card_changed",
            "code": "STALE_CARD",
            "status": 409,
        }

    @staticmethod
    def _flags(body) -> dict:
        body["purchased"] = False
        body["live_purchase"] = False
        return body

    @staticmethod
    def _provided(payload: CardPatch) -> dict:
        provided = {}
        for name in payload.model_fields_set:
            if name == "expected_version":
                continue
            value = getattr(payload, name)
            if value is None:
                raise DomainError("FIELD_NOT_CLEARABLE", 422)
            provided[name] = value
        return provided

    @staticmethod
    def _raise_if_needed(body):
        code = body.get("code")
        if code:
            raise DomainError(code, body.get("status", 409))
        return body


def purchase_card_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/purchase-cards", dependencies=[Depends(owner)])

    def principal(request: Request):
        token = request.cookies.get("desk_companion_session")
        if not runtime.store.session_valid(token):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"kind": "owner", "id": "owner", "name": "Owner", "session": token}

    @router.get("")
    def listing(request: Request):
        return runtime.purchase_cards.listing(principal(request))

    @router.post("")
    def create(payload: CardCreate, request: Request, key=Depends(operation_id)):
        return runtime.purchase_cards.create(payload, key, principal(request))

    @router.post("/{card_id}/confirmation")
    def confirm(card_id: str, payload: CardVersion, request: Request, key=Depends(operation_id)):
        return runtime.purchase_cards.confirm(card_id, payload, key, principal(request))

    @router.post("/{card_id}/updates")
    def update(card_id: str, payload: CardPatch, request: Request, key=Depends(operation_id)):
        return runtime.purchase_cards.update(card_id, payload, key, principal(request))

    @router.post("/{card_id}/revocation")
    def revoke(card_id: str, request: Request, key=Depends(operation_id)):
        return runtime.purchase_cards.revoke(card_id, key, principal(request))

    @router.post("/{card_id}/offers")
    def offer(card_id: str, payload: OfferInput, request: Request, key=Depends(operation_id)):
        return runtime.purchase_cards.submit_offer(card_id, payload, key, principal(request))

    @router.post("/{card_id}/offers/{offer_id}/approval")
    def approve(
        card_id: str,
        offer_id: str,
        request: Request,
        payload: ApprovalInput,
        key=Depends(operation_id),
    ):
        return runtime.purchase_cards.approve(card_id, offer_id, payload, key, principal(request))

    @router.post("/{card_id}/offers/{offer_id}/receipt")
    def receipt(
        card_id: str,
        offer_id: str,
        payload: ReceiptInput,
        request: Request,
        key=Depends(operation_id),
    ):
        return runtime.purchase_cards.record_receipt(
            card_id, offer_id, payload, key, principal(request)
        )

    return router
