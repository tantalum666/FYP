"""Confirm exact Woo cart terms; recover payments from the shop and its Stripe sandbox."""

from datetime import timedelta
import os

from ..calendar import iso
from ..commerce_review import ChatReviews
from ..store import DomainError
from .provider import WooSandbox


REFUND_STATES = {"refunded", "partially_refunded", "refund_pending", "refund_review"}
RECEIPT_STATES = REFUND_STATES | {"completed", "refund_retry", "unverified"}


def public_quote(quote):
    result = {k: v for k, v in quote.items() if k != "checkout_basis"}
    terms = quote["terms"]
    if len(terms.get("items", [])) == 1:
        # Keep the original single-product display fields for earlier clients.
        line = terms["items"][0]
        result.update(
            name=quote["item_names"][str(line["product_id"])],
            unit_minor=line["subtotal_minor"] // line["quantity"],
            terms={**terms, **{k: line[k] for k in ("product_id", "sku", "quantity")}},
        )
    return result


def public(row):
    quote = row["quote"]
    receipt = row.get("receipt") if row["state"] in RECEIPT_STATES else None
    if receipt and (row.get("receipt_stale") or row["state"] == "unverified"):
        receipt = {**receipt, "last_verified": True, "can_cancel": False}
    return {
        "id": row["id"],
        "version": row["version"],
        "state": row["state"],
        "quote": public_quote(quote),
        "review_minor": quote["terms"]["total_minor"],
        "previous": public_quote(row["previous"]) if row.get("previous") else None,
        "approved_minor": row.get("approved"),
        "receipt": receipt,
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
            if error.code in {"SHOP_UNVERIFIED", "SHOP_TEST_CONFIG"}:
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
        ) or (
            row.get("payment_fingerprint")
            and row["payment_fingerprint"] != receipt.get("payment_fingerprint")
        ):
            self._state(row, "unverified")
            return
        refund = receipt.get("refund_status")
        if prior and (
            (prior.get("refunded_minor") or 0) > (receipt.get("refunded_minor") or 0)
            or (prior.get("buyer_cancel_requested") and not receipt.get("buyer_cancel_requested"))
            or (prior.get("refund_status") in {"pending", "partial", "succeeded"} and not refund)
            or (prior.get("pending_minor") and receipt.get("pending_minor") is None)
        ):
            row["receipt_stale"] = True
            if refund != "pending" or receipt.get("refunded_minor") is not None:
                self._state(row, "refund_review")
                return
        else:
            if fingerprint := receipt.get("payment_fingerprint"):
                # A rejected read must not change the binding of a historical receipt.
                row["payment_fingerprint"] = fingerprint
            row.pop("receipt_stale", None)
            row["receipt"] = {k: v for k, v in receipt.items() if k != "payment_fingerprint"}
        if refund == "succeeded":
            self._state(row, "refunded")
        elif refund == "partial":
            self._state(row, "partially_refunded")
        elif refund == "needs_review":
            self._state(row, "refund_review")
        elif refund == "pending" or receipt.get("buyer_cancel_requested"):
            now = self.store.clock().timestamp()
            overdue = now - row.get("cancel_requested_at", now) > 120
            self._state(row, "refund_review" if overdue else "refund_pending")
        elif row.get("cancel_requested_at"):
            if receipt.get("can_cancel") and not row.get("cancel_unavailable"):
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
            if error.code in {"SHOP_UNVERIFIED", "SHOP_PAYMENT_FAILED", "SHOP_TEST_CONFIG"}:
                self._state(row, "unverified")
            elif row.get("receipt"):
                row["receipt_stale"] = True
            elif required:
                raise
        self._save(row)

    def cancel(self, ref, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ref.id, owner, chat)
            if row["state"] in REFUND_STATES:
                self._read_payment(row, required=True)
                return public(row)
            if (
                row["state"] not in {"completed", "refund_retry"}
                or ref.version != row["version"]
                or ref.amount_minor != public(row)["review_minor"]
            ):
                raise DomainError("SHOP_REVIEW_CHANGED", 409)
            self._read_payment(row, required=True)
            if row["state"] not in {"completed", "refund_retry"} or row.get("receipt_stale"):
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
            if row["state"] not in RECEIPT_STATES:
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
            recovering = row["state"] == "retry"
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
                if not recovering and error.code in {"SHOP_ITEM_UNAVAILABLE", "SHOP_DELIVERY_UNAVAILABLE"}:
                    self._state(row, "unavailable")
                    self._save(row)
                elif error.code == "SHOP_UNVERIFIED":
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
