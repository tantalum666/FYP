"""Quote the existing WooCommerce sandbox cart and reopen a reviewed guest order."""

from contextlib import contextmanager
import hashlib
import html
import json
import os
from pathlib import Path
import re

import httpx
from pydantic import Field

from ..schemas import StrictModel
from ..store import DomainError


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


class ShopQuery(StrictModel):
    product: str = Field(
        min_length=1,
        max_length=140,
        description="Product name or SKU the owner asked for. Keep the original language.",
    )
    quantity: int = Field(
        ge=1, le=99, strict=True, description="Exact number of selling units requested."
    )


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


def _minor(value):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,11}", str(value)):
        raise DomainError("SHOP_UNVERIFIED", 502)
    return int(value)


def cart_quote(cart, product_id, quantity):
    items = cart.get("items", [])
    totals = cart.get("totals") or {}
    if (
        len(items) != 1
        or items[0].get("id") != product_id
        or items[0].get("quantity") != quantity
        or totals.get("currency_code") != "HKD"
        or totals.get("currency_minor_unit") != 2
        or "stripe_cc" not in cart.get("payment_methods", [])
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    item = items[0]
    selected = [
        rate
        for package in cart.get("shipping_rates", [])
        for rate in package["shipping_rates"]
        if rate["selected"]
    ]
    if cart.get("needs_shipping") and (
        not cart.get("has_calculated_shipping") or len(selected) != 1
    ):
        raise DomainError("SHOP_DELIVERY_UNAVAILABLE", 409)
    unit = _minor(item["prices"]["price"])
    terms = {
        "product_id": product_id,
        "sku": item["sku"],
        "quantity": quantity,
        "currency": "HKD",
        "subtotal_minor": _minor(item["totals"]["line_subtotal"]),
        "discount_minor": _minor(totals["total_discount"]),
        "shipping_minor": _minor(totals["total_shipping"]),
        "tax_minor": _minor(totals["total_tax"]),
        "fees_minor": _minor(totals["total_fees"]),
        "total_minor": _minor(totals["total_price"]),
        "rate_id": selected[0]["rate_id"] if selected else "",
    }
    if (
        not terms["sku"]
        or unit * quantity != terms["subtotal_minor"]
        or terms["total_minor"] <= 0
        or terms["total_minor"]
        != terms["subtotal_minor"]
        - terms["discount_minor"]
        + terms["shipping_minor"]
        + terms["tax_minor"]
        + terms["fees_minor"]
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    return {
        "terms": terms,
        "name": html.unescape(item["name"]),
        "unit_minor": unit,
        "shipping_name": html.unescape(selected[0]["name"]) if selected else "",
        "destination": "HK" if selected else None,
    }


def checkout_revision(basis, revised):
    """A merchant-only adjustment needs a complete, arithmetically consistent final quote."""
    original = basis["terms"]
    terms = revised.get("terms") if isinstance(revised, dict) else None
    if (
        not isinstance(terms, dict)
        or terms.keys() != original.keys()
        or any(terms[k] != original[k] for k in ("product_id", "sku", "quantity", "currency"))
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    amounts = {k: _minor(v) for k, v in terms.items() if k.endswith("_minor")}
    total = (
        amounts["subtotal_minor"]
        - amounts["discount_minor"]
        + amounts["shipping_minor"]
        + amounts["fees_minor"]
        + amounts["tax_minor"]
    )
    if (
        total != amounts["total_minor"]
        or total <= 0
        or amounts["subtotal_minor"] % terms["quantity"]
        or not isinstance(terms["rate_id"], str)
        or not isinstance(revised.get("shipping_name"), str)
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    return {
        **basis,
        "terms": {**terms, **amounts},
        "unit_minor": amounts["subtotal_minor"] // terms["quantity"],
        "shipping_name": html.unescape(revised["shipping_name"]),
        "checkout_basis": basis,
    }


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
    def cart(shop, product_id, quantity):
        token = shop.get("wc/store/v1/cart")
        _json(token)
        if not token.headers.get("Cart-Token"):
            raise DomainError("SHOP_UNVERIFIED", 502)
        h = {"Cart-Token": token.headers["Cart-Token"]}
        _json(
            shop.post(
                "wc/store/v1/cart/add-item",
                json={"id": product_id, "quantity": quantity},
                headers=h,
            )
        )
        cart = _json(
            shop.post(
                "wc/store/v1/cart/update-customer",
                json={"billing_address": BILLING, "shipping_address": ADDRESS},
                headers=h,
            )
        )
        return cart_quote(cart, product_id, quantity), h

    def quote(self, query):
        with self.shop() as (shop, _):
            search = query.product.strip()
            if not search:
                raise DomainError("SHOP_NO_MATCH", 404)
            field = "sku" if re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", search) else "search"
            matches = _json(
                shop.get("wc/store/v1/products", params={field: search, "per_page": 20})
            )
            eligible = [
                x
                for x in matches
                if x.get("is_purchasable")
                and x.get("is_in_stock")
                and x.get("type") == "simple"
                and x.get("sku")
            ]
            exact = [
                x
                for x in eligible
                if search.casefold() in {x["sku"].casefold(), html.unescape(x["name"]).casefold()}
            ]
            candidates = exact or eligible
            if len(candidates) != 1:
                raise DomainError("SHOP_NO_MATCH" if not candidates else "SHOP_AMBIGUOUS", 409)
            return self.cart(shop, candidates[0]["id"], query.quantity)[0]

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
                if _json(stripe.get("account")).get("id") != cfg["stripe_account"]:
                    raise DomainError("SHOP_TEST_CONFIG", 503)
                yield stripe
        except httpx.HTTPError:
            raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503) from None

    def test_method(self, ref):
        with self.stripe() as stripe:
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
            current, cart_headers = self.cart(shop, terms["product_id"], terms["quantity"])
            basis = approved.get("checkout_basis", approved)
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
                    revised = self.cart(fresh, terms["product_id"], terms["quantity"])[0]
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

    def receipt(self, ref, approved):
        with self.shop() as (shop, auth):
            order = _json(shop.get("fyp-alice/v1/orders/" + ref, headers=auth))
        if not order.get("found"):
            return None
        if (
            order.get("test_mode") is not True
            or order.get("guest") is not True
            or order.get("gateway") != "stripe_cc"
            or order.get("terms") != approved["terms"]
            or type(order.get("order_id")) is not int
            or order["order_id"] <= 0
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        if not order.get("paid") or order.get("status") not in {"processing", "completed"}:
            if order.get("status") in {"cancelled", "failed", "refunded"}:
                raise DomainError("SHOP_PAYMENT_FAILED", 409)
            return None
        pi, charge = order.get("intent"), order.get("transaction")
        if not re.fullmatch(r"pi_[a-zA-Z0-9]+", str(pi)) or not re.fullmatch(
            r"ch_[a-zA-Z0-9]+", str(charge)
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        with self.stripe() as stripe:
            intent = _json(stripe.get("payment_intents/" + pi))
            captured = _json(stripe.get("charges/" + charge))
        total = approved["terms"]["total_minor"]
        card = (captured.get("payment_method_details") or {}).get("card") or {}
        if (
            intent.get("id") != pi
            or intent.get("livemode") is not False
            or intent.get("latest_charge") != charge
            or intent.get("status") != "succeeded"
            or intent.get("amount_received") != total
            or intent.get("currency") != "hkd"
            or captured.get("id") != charge
            or captured.get("payment_intent") != pi
            or captured.get("livemode") is not False
            or captured.get("status") != "succeeded"
            or captured.get("paid") is not True
            or captured.get("captured") is not True
            or captured.get("amount_captured") != total
            or captured.get("currency") != "hkd"
            or captured.get("refunded") is not False
            or captured.get("amount_refunded") != 0
            or card.get("last4") != "4242"
            or card.get("brand") != "visa"
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        return {
            "order": order["order_id"],
            "order_status": order["status"],
            "charged_minor": total,
            "test_mode": True,
        }
