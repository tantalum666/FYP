"""Confirm exact Woo cart terms; recover payments from the shop and its Stripe sandbox."""

from datetime import timedelta
import os

from ..calendar import iso
from ..commerce_review import ChatReviews
from ..store import DomainError
from .provider import WooSandbox


def public(row):
    quote = row["quote"]
    return {
        "id": row["id"],
        "version": row["version"],
        "state": row["state"],
        "quote": {k: v for k, v in quote.items() if k != "checkout_basis"},
        "review_minor": quote["terms"]["total_minor"],
        "previous": {k: v for k, v in row["previous"].items() if k != "checkout_basis"}
        if row.get("previous")
        else None,
        "approved_minor": row.get("approved"),
        "receipt": row.get("receipt")
        if row["state"]
        in {"completed", "refund_pending", "refund_retry", "refund_review", "refunded"}
        else None,
        "cancel_unavailable": row.get("cancel_unavailable", False),
    }


class ShopOrders(ChatReviews):
    follow_states = ("submitting", "checking", "refund_pending")

    def __init__(self, runtime):
        super().__init__(runtime, "SHOP")
        config = os.getenv("DESK_WOO_SANDBOX_CONFIG")
        self.enabled = bool(config)
        self.provider = WooSandbox(config)

    def prepare(self, query):
        if not self.enabled:
            raise DomainError("SHOP_DISABLED", 403)
        with self.store.connection() as db:
            if self.store.settings(db)["hide_private"]:
                raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        return {"shop_quote": self.provider.quote(query), "saved": False}

    def attach(self, quote, key, principal, chat):
        row = {
            "quote": {k: v for k, v in quote.items() if k != "checkout_basis"},
            "expires": iso(self.store.clock() + timedelta(minutes=15)),
            "next_read": 0,
        }
        return public(self.insert(row, key, principal, chat))

    def _check(self, row):
        self._state(row, "checking")
        row["next_read"] = self.store.clock().timestamp() + 8
        self._save(row)
        try:
            receipt = self.provider.receipt(row["id"], row["quote"])
            if receipt:
                self._apply_receipt(row, receipt)
            elif self.store.clock().timestamp() - row["submitted_at"] > 60:
                self._state(row, "retry")
        except DomainError as error:
            if error.code == "SHOP_UNVERIFIED":
                self._state(row, "unverified")
            elif error.code == "SHOP_PAYMENT_FAILED":
                self._state(row, "failed")
        self._save(row)

    def read(self, ident, owner, chat, *, following=False):
        with self.lock:
            row = self._read_row(ident, owner, chat, following)
            if row is None:
                return None
            now = self.store.clock()
            if row["state"] in {"quoted", "reprice"} and row["expires"] <= iso(now):
                self._state(row, "expired")
                self._save(row)
            elif row["state"] in {"submitting", "checking"} and row["next_read"] <= now.timestamp():
                self._check(row)
            elif row["state"] == "refund_pending" and row["next_read"] <= now.timestamp():
                self._read_payment(row)
            return public(row)

    def _apply_receipt(self, row, receipt):
        prior = row.get("receipt")
        if not receipt or (
            prior
            and any(receipt.get(k) != prior.get(k) for k in ("order", "charged_minor", "test_mode"))
        ):
            self._state(row, "unverified")
            return
        row["receipt"] = receipt
        refund = receipt.get("refund_status")
        if refund == "succeeded":
            self._state(row, "refunded")
        elif refund or row.get("cancel_requested_at"):
            if receipt.get("buyer_cancel_requested") or refund:
                overdue = (
                    self.store.clock().timestamp()
                    - row.get("cancel_requested_at", self.store.clock().timestamp())
                    > 120
                )
                self._state(
                    row,
                    "refund_review" if refund == "needs_review" or overdue else "refund_pending",
                )
            elif receipt.get("can_cancel") and not row.get("cancel_unavailable"):
                self._state(row, "refund_retry")
            else:
                row["cancel_unavailable"] = True
                self._state(row, "completed")
        else:
            self._state(row, "completed")

    def _read_payment(self, row, required=False):
        row["next_read"] = self.store.clock().timestamp() + 8
        try:
            self._apply_receipt(row, self.provider.receipt(row["id"], row["quote"]))
        except DomainError as error:
            if error.code in {"SHOP_UNVERIFIED", "SHOP_PAYMENT_FAILED"}:
                self._state(row, "unverified")
            elif required:
                raise
        self._save(row)

    def cancel(self, ref, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ref.id, owner, chat)
            if row["state"] in {"refund_pending", "refund_review", "refunded"}:
                self._read_payment(row, required=True)
                return public(row)
            if (
                row["state"] not in {"completed", "refund_retry"}
                or ref.version != row["version"]
                or ref.amount_minor != public(row)["review_minor"]
            ):
                raise DomainError("SHOP_REVIEW_CHANGED", 409)
            self._read_payment(row, required=True)
            if row["state"] not in {"completed", "refund_retry"}:
                return public(row)
            if not row["receipt"].get("can_cancel"):
                row["cancel_unavailable"] = True
                self._save(row)
                return public(row)
            row.update(cancel_requested_at=self.store.clock().timestamp(), next_read=0)
            self._state(row, "refund_pending")
            self._save(row)
            try:
                self.provider.cancel(ref.id, row["receipt"])
            except DomainError as error:
                if error.code == "SHOP_CANCEL_UNAVAILABLE":
                    row["cancel_unavailable"] = True
            self._read_payment(row)
            return public(row)

    def reopen(self, ident, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ident, owner, chat)
            if row["state"] not in {
                "completed",
                "refunded",
                "refund_pending",
                "refund_retry",
                "refund_review",
            }:
                return self.read(ident, owner, chat)
            self._read_payment(row, required=True)
            return public(row)

    def decide(self, review, principal, chat):
        owner = self.owner(principal)
        if not self.enabled:
            raise DomainError("SHOP_DISABLED", 403)
        with self.lock:
            row = self._get(review.id, owner, chat)
            if row.get("last_review") == review.model_dump():
                return public(row)
            if (
                row["state"] not in {"quoted", "reprice", "retry"}
                or review.version != row["version"]
                or review.amount_minor != row["quote"]["terms"]["total_minor"]
            ):
                raise DomainError("SHOP_REVIEW_CHANGED", 409)
            if row["state"] != "retry" and row["expires"] <= iso(self.store.clock()):
                self._state(row, "expired")
                self._save(row)
                raise DomainError("SHOP_REVIEW_CHANGED", 409)
            if review.action == "decline":
                if row["state"] == "retry":
                    raise DomainError("SHOP_UNVERIFIED", 409)
                self._state(row, "cancelled")
                self._save(row)
                return public(row)
            now = self.store.clock()
            row.update(
                last_review=review.model_dump(),
                approved=review.amount_minor,
                submitted_at=now.timestamp(),
                next_read=now.timestamp() + 45,
            )
            self._state(row, "submitting")
            self._save(row)
            try:
                revised = self.provider.checkout(row["id"], row["quote"])
            except DomainError as error:
                if error.code == "SHOP_UNVERIFIED":
                    self._state(row, "unverified")
                    self._save(row)
                else:
                    self._check(row)
                return public(row)
            if revised:
                row.update(
                    previous=row["quote"], quote=revised, expires=iso(now + timedelta(minutes=15))
                )
                self._state(row, "reprice")
                self._save(row)
            else:
                self._check(row)
            return public(row)
