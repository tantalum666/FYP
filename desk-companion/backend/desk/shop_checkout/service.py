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
        "receipt": row.get("receipt") if row["state"] == "completed" else None,
    }


class ShopOrders(ChatReviews):
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
                row["receipt"] = receipt
                self._state(row, "completed")
            elif self.store.clock().timestamp() - row["submitted_at"] > 60:
                self._state(row, "retry")
        except DomainError as error:
            if error.code == "SHOP_UNVERIFIED":
                self._state(row, "unverified")
            elif error.code == "SHOP_PAYMENT_FAILED":
                self._state(row, "failed")
        self._save(row)

    def read(self, ident, owner, chat):
        with self.lock:
            row = self._get(ident, owner, chat)
            now = self.store.clock()
            if row["state"] in {"quoted", "reprice"} and row["expires"] <= iso(now):
                self._state(row, "expired")
                self._save(row)
            elif row["state"] in {"submitting", "checking"} and row["next_read"] <= now.timestamp():
                self._check(row)
            return public(row)

    def reopen(self, ident, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ident, owner, chat)
            if row["state"] != "completed":
                return self.read(ident, owner, chat)
            try:
                verified = self.provider.receipt(ident, row["quote"])
            except DomainError as error:
                if error.code not in {"SHOP_UNVERIFIED", "SHOP_PAYMENT_FAILED"}:
                    raise
                verified = None
            prior = row["receipt"]
            if not verified or any(
                verified.get(k) != prior.get(k) for k in ("order", "charged_minor", "test_mode")
            ):
                self._state(row, "unverified")
                self._save(row)
            elif verified != prior:
                # Fulfilment may advance from processing to completed after capture.
                row["receipt"] = verified
                self._save(row)
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
