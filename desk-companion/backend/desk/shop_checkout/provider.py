"""Quote the existing WooCommerce sandbox cart and reopen a reviewed guest order."""

from contextlib import contextmanager
import hashlib
import html
import json
import os
from pathlib import Path
import re

import httpx

from ..store import DomainError
from .terms import (
    MAX_QUANTITY,
    ShopQuery,
    cart_quote,
    checked_terms,
    checkout_revision,
    selection,
)


STORE = "http://127.0.0.1:8993/wp-json/"
STRIPE = "https://api.stripe.com/v1/"
ADDRESS = {
    "first_name": "FYP",
    "last_name": "Sandbox",
    "address_1": "12 Example Road",
    "city": "Hong Kong",
    "state": "HONG KONG",
    "postcode": "",
    "country": "HK",
}
BILLING = {**ADDRESS, "email": "fyp-woo@example.com", "phone": "+12025550142"}


def _private(path):
    path = Path(path)
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_uid != os.getuid()
        or path.stat().st_mode & 0o077
    ):
        raise DomainError("SHOP_TEST_CONFIG", 503)
    return json.loads(path.read_text())


def _json(response):
    if not response.is_success:
        raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503)
    try:
        return response.json()
    except ValueError:
        raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503) from None


class WooSandbox:
    def __init__(self, config_path):
        self.config_path = config_path

    def config(self):
        if not self.config_path:
            raise DomainError("SHOP_DISABLED", 403)
        try:
            config = _private(self.config_path)
            keys = _private(config["stripe_keys_path"])
            if (
                not str(keys["test_publishable_key"]).startswith("pk_test_")
                or not keys["test_secret_key"]
                or keys["test_secret_key"].startswith(("sk_live_", "rk_live_"))
                or not config["stripe_account"].startswith("acct_")
                or len(config["review_key"]) < 32
            ):
                raise ValueError
            return config, keys
        except (KeyError, ValueError, OSError):
            raise DomainError("SHOP_TEST_CONFIG", 503) from None

    @contextmanager
    def shop(self):
        config, keys = self.config()
        try:
            with httpx.Client(
                base_url=STORE, trust_env=False, follow_redirects=False, timeout=14
            ) as shop:
                auth = {"X-FYP-Review-Key": config["review_key"]}
                info = _json(shop.get("fyp-alice/v1/store", headers=auth))
                if (
                    info.get("test_mode") is not True
                    or info.get("currency") != "HKD"
                    or info.get("gateway") != "stripe_cc"
                    or info.get("publishable_fingerprint")
                    != hashlib.sha256(keys["test_publishable_key"].encode()).hexdigest()
                ):
                    raise DomainError("SHOP_TEST_CONFIG", 503)
                yield shop, auth
        except httpx.HTTPError:
            raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503) from None

    @staticmethod
    def cart(shop, requested, quantity=None):
        token = shop.get("wc/store/v1/cart")
        _json(token)
        if not token.headers.get("Cart-Token"):
            raise DomainError("SHOP_UNVERIFIED", 502)
        headers = {"Cart-Token": token.headers["Cart-Token"]}
        units = (
            {requested: quantity}
            if quantity is not None
            else {ident: count for ident, (_, count) in requested.items()}
        )
        for ident, count in units.items():
            added = shop.post(
                "wc/store/v1/cart/add-item", json={"id": ident, "quantity": count}, headers=headers
            )
            if added.status_code in {400, 404, 409}:
                raise DomainError("SHOP_ITEM_UNAVAILABLE", 409)
            _json(added)
        cart = _json(
            shop.post(
                "wc/store/v1/cart/update-customer",
                json={"billing_address": BILLING, "shipping_address": ADDRESS},
                headers=headers,
            )
        )
        return cart_quote(cart, requested, quantity), headers

    @staticmethod
    def resolve(shop, search):
        if not search:
            raise DomainError("SHOP_NO_MATCH", 404)
        path = "wc/store/v1/products"
        # Woo excludes variations from its normal catalog. Only a concrete SKU
        # can select a variation; a variable parent needs an owner choice.
        for filters in ({"sku": search}, {"sku": search, "type": "variation"}):
            rows = _json(shop.get(path, params={**filters, "per_page": 20}))
            candidates = [p for p in rows if (p.get("sku") or "").casefold() == search.casefold()]
            if candidates:
                break
        else:
            response = shop.get(path, params={"search": search, "per_page": 20})
            rows = _json(response)
            if response.headers.get("X-WP-TotalPages", "1") not in {"0", "1"}:
                raise DomainError("SHOP_AMBIGUOUS", 409)
            exact = [p for p in rows if html.unescape(p["name"]).casefold() == search.casefold()]
            sku_like = re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", search, re.I)
            candidates = exact or ([] if sku_like else rows)
        if not candidates:
            raise DomainError("SHOP_NO_MATCH", 404)
        if len(candidates) != 1 or candidates[0].get("type") == "variable":
            raise DomainError("SHOP_AMBIGUOUS", 409)
        product = candidates[0]
        if product.get("type") == "variation" and search.casefold() != product["sku"].casefold():
            raise DomainError("SHOP_AMBIGUOUS", 409)
        if (
            product.get("type") not in {"simple", "variation"}
            or not isinstance(product.get("sku"), str)
            or not product["sku"]
            or product.get("is_purchasable") is not True
            or product.get("is_in_stock") is not True
        ):
            raise DomainError("SHOP_ITEM_UNAVAILABLE", 409)
        if type(product.get("id")) is not int or product["id"] <= 0:
            raise DomainError("SHOP_UNVERIFIED", 502)
        return product["id"], product["sku"]

    def quote(self, query: ShopQuery):
        with self.shop() as (shop, _):
            requested = {}
            for item in query.requested_items():
                ident, sku = self.resolve(shop, item.product.strip())
                prior_sku, count = requested.get(ident, (sku, 0))
                if prior_sku != sku:
                    raise DomainError("SHOP_UNVERIFIED", 502)
                count += item.quantity
                if count > MAX_QUANTITY:
                    raise DomainError("SHOP_QUANTITY_LIMIT", 409)
                requested[ident] = (sku, count)
            return self.cart(shop, requested)[0]

    @contextmanager
    def stripe(self):
        cfg, keys = self.config()
        try:
            with httpx.Client(
                base_url=STRIPE,
                auth=(keys["test_secret_key"], ""),
                trust_env=False,
                follow_redirects=False,
                timeout=14,
            ) as stripe:
                account = _json(stripe.get("account"))
                if not isinstance(account, dict) or account.get("id") != cfg["stripe_account"]:
                    raise DomainError("SHOP_TEST_CONFIG", 503)
                yield stripe, account["id"]
        except httpx.HTTPError:
            raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503) from None

    def test_method(self, ref):
        with self.stripe() as (stripe, _):
            fixture = _json(stripe.get("payment_methods/pm_card_visa"))
            if fixture.get("livemode") is not False:
                raise DomainError("SHOP_TEST_CONFIG", 503)
            method = _json(
                stripe.post(
                    "payment_methods",
                    data={
                        "type": "card",
                        "card[token]": "tok_visa",
                        "billing_details[name]": "FYP Sandbox",
                        "billing_details[email]": BILLING["email"],
                    },
                    headers={"Idempotency-Key": "fyp-woo-method-" + ref},
                )
            )
            if (
                method.get("livemode") is not False
                or (method.get("card") or {}).get("last4") != "4242"
                or not re.fullmatch(r"pm_[A-Za-z0-9]+", str(method.get("id", "")))
            ):
                raise DomainError("SHOP_TEST_CONFIG", 503)
            return method["id"]

    def checkout(self, ref, approved):
        terms = approved["terms"]
        with self.shop() as (shop, auth):
            path = "fyp-alice/v1/orders/" + ref
            if _json(shop.get(path, headers=auth)).get("found"):
                return None
            cart_args = (selection(terms),) if "items" in terms else (terms["product_id"], terms["quantity"])
            current, cart_headers = self.cart(shop, *cart_args)
            basis = approved.get("checkout_basis", approved)
            if "items" not in terms and "items" in current["terms"]:
                if current["terms"]["items"][0]["sku"] != terms["sku"]:
                    raise DomainError("SHOP_UNVERIFIED", 502)
            if current != basis:
                return current
            method = self.test_method(ref)
            resp = shop.post(
                path,
                headers={**auth, **cart_headers},
                json={"approved": terms, "cart_basis": basis["terms"], "test_method": method},
                timeout=35,
            )
            if resp.status_code == 409 and resp.json().get("code") == "fyp_quote_changed":
                # A final Woo calculation changed after the cart read, before its gateway.
                with self.shop() as (fresh, _):
                    revised = self.cart(fresh, *cart_args)[0]
                if revised != basis:
                    return revised
                revision = resp.json().get("data", {}).get("revision")
                if revision:
                    result = checkout_revision(revised, revision)
                    if result["terms"] != terms:
                        return result
                raise DomainError("SHOP_UNVERIFIED", 409)
            _json(resp)
            return None

    def cancel(self, ref, receipt):
        with self.shop() as (shop, auth):
            response = shop.post(
                f"fyp-alice/v1/orders/{ref}/cancel",
                headers=auth,
                json={"order": receipt["order"], "amount_minor": receipt["charged_minor"]},
                timeout=35,
            )
            if (
                response.status_code == 409
                and response.json().get("code") == "fyp_cancel_unavailable"
            ):
                raise DomainError("SHOP_CANCEL_UNAVAILABLE", 409)
            _json(response)

    def receipt(self, ref, approved):
        with self.shop() as (shop, auth):
            order = _json(shop.get("fyp-alice/v1/orders/" + ref, headers=auth))
        if not isinstance(order, dict) or type(order.get("found")) is not bool:
            raise DomainError("SHOP_UNVERIFIED", 502)
        if not order["found"]:
            return None
        actual = order.get("terms")
        if "items" in approved["terms"]:
            actual = checked_terms(actual)
        if (
            order.get("test_mode") is not True
            or order.get("guest") is not True
            or order.get("gateway") != "stripe_cc"
            or actual != approved["terms"]
            or actual.get("currency") != "HKD"
            or not isinstance(order.get("status"), str)
            or type(order.get("order_id")) is not int
            or order["order_id"] <= 0
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        requested = order.get("buyer_cancel_requested") is True
        refund_indicated = (
            requested or order["status"] == "refunded" or order.get("refunded_minor", 0) != 0
        )
        if not refund_indicated and (
            order.get("paid") is not True or order.get("status") not in {"processing", "completed"}
        ):
            if order.get("status") in {"cancelled", "failed", "refunded"}:
                raise DomainError("SHOP_PAYMENT_FAILED", 409)
            return None
        pi, charge = order.get("intent"), order.get("transaction")
        if not re.fullmatch(r"pi_[a-zA-Z0-9]+", str(pi)) or not re.fullmatch(
            r"ch_[a-zA-Z0-9]+", str(charge)
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        total = approved["terms"]["total_minor"]
        with self.stripe() as (stripe, account):
            intent = _json(stripe.get("payment_intents/" + pi))
            captured = _json(stripe.get("charges/" + charge))
            if not isinstance(intent, dict) or not isinstance(captured, dict):
                raise DomainError("SHOP_UNVERIFIED", 502)
            method = captured.get("payment_method_details")
            card = method.get("card") if isinstance(method, dict) else None
            if (
                intent.get("id") != pi
                or intent.get("livemode") is not False
                or intent.get("latest_charge") != charge
                or intent.get("status") != "succeeded"
                or type(intent.get("amount_received")) is not int
                or intent["amount_received"] != total
                or intent.get("currency") != "hkd"
                or captured.get("id") != charge
                or captured.get("payment_intent") != pi
                or captured.get("livemode") is not False
                or captured.get("status") != "succeeded"
                or captured.get("paid") is not True
                or captured.get("captured") is not True
                or type(captured.get("amount_captured")) is not int
                or captured["amount_captured"] != total
                or captured.get("currency") != "hkd"
                or not isinstance(card, dict)
                or card.get("last4") != "4242"
                or card.get("brand") != "visa"
            ):
                raise DomainError("SHOP_UNVERIFIED", 502)
            # A newly pending Refund can precede both Woo's total and the Charge's counter.
            try:
                amounts = refund_receipt(order, captured, charge_refunds(stripe, charge), total)
            except DomainError as error:
                if error.code != "SHOP_UNVERIFIED":
                    raise
                amounts = {
                    "refund_status": "needs_review", "refunded_minor": None,
                    "net_minor": None, "pending_minor": None,
                }
        return {
            "order": order["order_id"],
            "order_status": order["status"],
            "charged_minor": total,
            "test_mode": True,
            "payment_fingerprint": hashlib.sha256(f"{account}/{pi}/{charge}".encode()).hexdigest(),
            "can_cancel": order.get("can_cancel") is True and "refund_status" not in amounts,
            "buyer_cancel_requested": requested,
            **amounts,
        }


def charge_refunds(stripe, charge_id):
    params = {"charge": charge_id, "limit": 100}
    cursors = set()
    while True:
        page = _json(stripe.get("refunds", params=params))
        if (
            not isinstance(page, dict)
            or type(page.get("has_more")) is not bool
            or not isinstance(page.get("data"), list)
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        yield from page["data"]
        if not page["has_more"]:
            return
        # The consumer has validated every Refund ID before advancing the cursor.
        if not page["data"] or (cursor := page["data"][-1]["id"]) in cursors:
            raise DomainError("SHOP_UNVERIFIED", 502)
        cursors.add(cursor)
        params["starting_after"] = cursor


def refund_receipt(order, charge, records, total):
    """Recompute a snapshot of this capture. Pending funds still belong in its net."""
    by_id = {}
    for refund in records:
        if (
            not isinstance(refund, dict)
            or refund.get("object") != "refund"
            or not re.fullmatch(r"re_[a-zA-Z0-9]+", str(refund.get("id", "")))
            or refund.get("livemode", False) is not False
            or refund.get("charge") != charge["id"]
            or refund.get("payment_intent") != charge["payment_intent"]
            or refund.get("currency") != "hkd"
            or type(refund.get("amount")) is not int
            or not 0 < refund["amount"] <= total
            or refund.get("status") not in (
                "pending", "requires_action", "succeeded", "failed", "canceled"
            )
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        entry = (refund["amount"], refund["status"])
        if by_id.setdefault(refund["id"], entry) != entry:
            raise DomainError("SHOP_UNVERIFIED", 502)

    settled = sum(n for n, status in by_id.values() if status == "succeeded")
    pending = sum(n for n, status in by_id.values() if status in {"pending", "requires_action"})
    issued = settled + pending
    if issued > total:
        raise DomainError("SHOP_UNVERIFIED", 502)
    amounts = {"refunded_minor": settled, "net_minor": total - settled, "pending_minor": pending}
    recorded = charge.get("amount_refunded")
    flag = charge.get("refunded")
    status = order["status"]
    statuses = {s for _, s in by_id.values()}
    needs_review = "requires_action" in statuses or (
        not pending and bool(statuses & {"failed", "canceled"})
    )
    # Woo records a buyer cancellation before dispatching to Stripe. Either read
    # can arrive first, so keep following a recognized request while the counters catch up.
    awaiting_buyer_refund = (
        order.get("buyer_cancel_requested") is True
        and status in {"on-hold", "processing", "refunded"}
        and not needs_review
    )
    lag_status = "pending" if awaiting_buyer_refund else "needs_review"
    if (
        type(recorded) is not int or not 0 <= recorded <= total
        or type(flag) is not bool or (flag and recorded != total)
    ):
        return {
            "refund_status": "needs_review", "refunded_minor": None,
            "net_minor": None, "pending_minor": pending,
        }
    if not settled <= recorded <= issued or (settled == total and not flag):
        return {
            "refund_status": lag_status, "refunded_minor": None,
            "net_minor": None, "pending_minor": pending,
        }

    # Both ledgers can include a refund before Stripe completes it. Woo's order
    # status/total alone cannot establish settlement or authorize a cancellation.
    woo = order.get("refunded_minor", 0)
    if (
        type(woo) is not int or not 0 <= woo <= total
        or status not in {"on-hold", "processing", "completed", "refunded"}
    ):
        result = "needs_review"
    elif (
        not settled <= woo <= issued
        or (settled == total and status != "refunded")
        or (status == "refunded" and (woo != total or issued != total))
    ):
        result = lag_status
    elif settled == total:
        result = "succeeded"
    elif needs_review:
        result = "needs_review"
    elif pending or (order.get("buyer_cancel_requested") and not settled):
        result = "pending"
    elif settled:
        result = "partial"
    else:
        return amounts
    return {**amounts, "refund_status": result}
