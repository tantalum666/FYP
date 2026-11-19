"""Owner-reviewed test flights. LetsFG owns fulfillment; the desk records exact approvals."""

from datetime import timedelta
import hashlib
import json
import os
import threading

from pydantic import Field
from typing import Literal
from zoneinfo import ZoneInfo

from ..calendar import iso
from ..conversation import Conversations
from ..schemas import StrictModel
from ..store import DomainError, encode
from .provider import LetsFG, PNR, booking_id, matched, minor


class FlightRef(StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    version: int = Field(ge=1, strict=True)
    amount_minor: int = Field(gt=0, strict=True)


class FlightReview(FlightRef):
    action: Literal["confirm", "decline"]


def public(row):
    quote = row["quote"]
    return {
        "id": row["id"],
        "version": row["version"],
        "state": row["state"],
        "segments": quote["segments"],
        "adults": quote["adults"],
        "currency": quote["currency"],
        "quoted_minor": quote["total_minor"],
        "approved_minor": row["approved"],
        "review_minor": row["question"]["new"] if row["question"] else quote["total_minor"],
        "review_deadline_ms": row["question"]["expires"] if row["question"] else None,
        "previous_minor": row["question"]["old"] if row["question"] else None,
        "pnr": row.get("pnr"),
        "charged_minor": row.get("capture"),
        "released": row.get("released", False),
    }


class FlightBookings:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.provider = LetsFG()
        self.lock = threading.RLock()
        self.enabled = os.getenv("DESK_LETSFG_SANDBOX_ENABLED") == "1"
        with self.store.connection(write=True) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sandbox_flight_bookings(id TEXT PRIMARY KEY, owner TEXT NOT NULL, chat TEXT NOT NULL, data TEXT NOT NULL, serial INTEGER NOT NULL DEFAULT 0)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS sandbox_flight_chat ON sandbox_flight_bookings(owner,chat)"
            )

    def owner(self, principal):
        if (
            not principal
            or not self.store.session_valid(principal.get("session"))
            or not (owner := Conversations.owner(principal))
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        return owner

    def prepare(self, query):
        if not self.enabled:
            raise DomainError("FLIGHT_SANDBOX_DISABLED", 403)
        when = self.store.clock().astimezone(ZoneInfo("Asia/Hong_Kong")).date()
        quote = self.provider.quote(query, when)
        quote["scenario"] = "price_change" if query.rehearse_price_change else "success"
        return {"sandbox_quote": quote, "saved": False}

    def attach(self, quote, key, principal, chat):
        owner = self.owner(principal)
        if not chat or chat.owner != owner:
            raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
        ident = hashlib.sha256(key.encode()).hexdigest()[:32]
        row = {
            "id": ident,
            "quote": quote,
            "state": "quoted",
            "version": 1,
            "question": None,
            "approved": None,
            "expires": iso(self.store.clock() + timedelta(minutes=15)),
            "remote": None,
            "next_read": 0,
            "scenario": quote["scenario"],
            "task_id": chat.task_id,
        }
        with self.store.connection(write=True) as db:
            db.execute(
                "INSERT OR IGNORE INTO sandbox_flight_bookings(id,owner,chat,data) VALUES(?,?,?,?)",
                (ident, owner, chat.id, encode(row)),
            )
        return public(self._get(ident, owner, chat.id))

    def _get(self, ident, owner, chat):
        with self.store.connection() as db:
            record = db.execute(
                "SELECT data,serial FROM sandbox_flight_bookings WHERE id=? AND owner=? AND chat=?",
                (ident, owner, chat),
            ).fetchone()
        if not record:
            raise DomainError("FLIGHT_NOT_FOUND", 404)
        return dict(json.loads(record["data"]), _serial=record["serial"])

    def can_resume(self, principal, chat, review, task_id):
        if (
            not chat
            or not review
            or not self.enabled
            or not self.runtime.personal_context.visible(principal)
        ):
            return False
        try:
            row = self._get(review.id, self.owner(principal), chat)
        except DomainError:
            return False
        return row.get("task_id") == task_id

    def _save(self, row):
        data = {k: v for k, v in row.items() if k != "_serial"}
        with self.store.connection(write=True) as db:
            updated = db.execute(
                "UPDATE sandbox_flight_bookings SET data=?,serial=serial+1 WHERE id=? AND serial=?",
                (encode(data), row["id"], row["_serial"]),
            )
            if updated.rowcount != 1:
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        row["_serial"] += 1

    @staticmethod
    def _state(row, state):
        if state != row["state"]:
            row["state"] = state
            row["version"] += 1

    def listing(self, principal, chat):
        owner = self.owner(principal)
        with self.store.connection() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM sandbox_flight_bookings WHERE owner=? AND chat=? ORDER BY rowid DESC",
                    (owner, chat),
                )
            ]
        return [self.read(ident, owner, chat) for ident in ids]

    def read(self, ident, owner, chat):
        with self.lock:
            row = self._get(ident, owner, chat)
            now = self.store.clock()
            if row["state"] == "quoted" and row["expires"] <= iso(now):
                self._state(row, "expired")
                self._save(row)
            elif row["state"] == "submitting" and row["next_read"] <= now.timestamp():
                self._state(row, "submit_unknown")
                self._save(row)
            elif (
                row["remote"]
                and row["state"] in {"processing", "reprice", "answering"}
                and row["next_read"] <= now.timestamp()
            ):
                self._refresh(row)
            return public(row)

    def _refresh(self, row, *, required=False):
        row["next_read"] = self.store.clock().timestamp() + 20
        self._save(row)
        try:
            record = self.provider.status(row["remote"])
            self._project(row, record)
        except DomainError as error:
            if error.code == "FLIGHT_PROVIDER_UNAVAILABLE":
                if required:
                    raise
                return
            self._state(row, "unverified")
        except (KeyError, TypeError, ValueError):
            self._state(row, "unverified")
        self._save(row)

    def _project(self, row, record):
        matched(record, row["remote"], row["quote"])
        if record.get("currency") != "HKD" or record.get("card_last4") != "4242":
            raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
        state = record.get("state")
        if record.get("terminal") is True:
            ref = record.get("pnr")
            if (
                state == "completed"
                and (row.get("last_review") or {}).get("action") != "decline"
                and isinstance(ref, str)
                and PNR.fullmatch(ref)
                and minor(record.get("charged_amount")) == row["approved"]
            ):
                row.update(pnr=ref, capture=row["approved"], question=None)
                self._state(row, "completed")
            elif state == "failed" and not ref and record.get("charged_amount") in (None, 0):
                row.update(
                    released="hold was released" in str(record.get("message", "")).lower(),
                    question=None,
                )
                self._state(row, "failed")
            else:
                self._state(row, "unverified")
            return
        if record.get("terminal") is not False or state not in {
            "authorised",
            "card_issued",
            "booking_in_progress",
            "awaiting_settlement",
        }:
            self._state(row, "unverified")
            return
        question = record.get("question")
        if not question:
            row["question"] = None
            self._state(row, "processing")
            return
        change = question.get("price_change") or {}
        rnd = question.get("round")
        if (
            question.get("kind") != "price_change"
            or type(rnd) is not int
            or rnd < 1
            or type(question.get("expires_at_ms")) is not int
            or change.get("currency") != "HKD"
            or minor(change.get("new_total")) <= minor(change.get("old_total"))
        ):
            self._state(row, "unverified")
            return
        pending = {
            "round": rnd,
            "old": minor(change["old_total"]),
            "new": minor(change["new_total"]),
            "expires": question["expires_at_ms"],
        }
        if row["state"] == "answering" and row["question"] == pending:
            if self.store.clock().timestamp() < row["answer_at"] + 20:
                return
            # The provider still needs a decision. Offer the current round again.
            row["approved"] = pending["old"]
        if pending["old"] != row["approved"]:
            raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
        if pending != row["question"]:
            row["version"] += 1
        row["question"] = pending
        self._state(row, "reprice")

    def decide(self, review, principal, chat):
        owner = self.owner(principal)
        if not self.enabled:
            raise DomainError("FLIGHT_SANDBOX_DISABLED", 403)
        with self.lock:
            row = self._get(review.id, owner, chat)
            if row.get("last_review") == review.model_dump() and row["state"] != "submit_unknown":
                return public(row)
            if row["state"] == "reprice":
                self._refresh(row, required=True)
            view = public(row)
            if row["version"] != review.version or review.amount_minor != view["review_minor"]:
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            if row["state"] in {"quoted", "submit_unknown"}:
                if row["state"] == "quoted" and row["expires"] <= iso(self.store.clock()):
                    self._state(row, "expired")
                    self._save(row)
                    raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
                if review.action == "decline":
                    if row["state"] != "quoted":
                        raise DomainError("FLIGHT_OUTCOME_UNKNOWN", 409)
                    self._state(row, "cancelled")
                    self._save(row)
                else:
                    row.update(
                        approved=view["review_minor"],
                        last_review=review.model_dump(),
                        next_read=self.store.clock().timestamp() + 40,
                    )
                    self._state(row, "submitting")
                    self._save(row)
                    self._submit(row)
            elif row["state"] == "reprice":
                q = row["question"]
                if q["expires"] <= self.store.clock().timestamp() * 1000:
                    raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
                row.update(
                    last_review=review.model_dump(),
                    next_read=0,
                    answer_at=self.store.clock().timestamp(),
                )
                if review.action == "confirm":
                    row["approved"] = q["new"]
                self._state(row, "answering")
                self._save(row)
                try:
                    answer = self.provider.answer(
                        row["remote"], q["round"], review.action == "confirm"
                    )
                    if answer.get("sandbox") is not True or answer.get("ok") is not True:
                        raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
                except DomainError:
                    # A lost acknowledgement is ambiguous. Poll the original booking only.
                    pass
            else:
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            return public(row)

    def _submit(self, row):
        try:
            result = self.provider.submit(row["quote"], "fyp-flight-" + row["id"], row["scenario"])
            ident = booking_id(result.get("booking_id"))
            matched(result, ident, row["quote"])
            row["remote"] = ident
            if not result.get("duplicate"):
                held = result.get("held") or {}
                if (
                    held.get("currency") != "HKD"
                    or minor(held.get("amount")) != row["approved"]
                    or (held.get("card") or {}).get("last4") != "4242"
                    or result.get("charged") != 0
                ):
                    raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
            self._state(row, "processing")
            row["next_read"] = 0
        except DomainError as error:
            self._state(
                row,
                "submit_unknown" if error.code == "FLIGHT_PROVIDER_UNAVAILABLE" else "unverified",
            )
        self._save(row)
