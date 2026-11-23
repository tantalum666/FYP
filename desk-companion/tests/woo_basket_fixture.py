"""In-memory Woo Store, reviewed merchant and Stripe HTTP fixtures for the ordinary composer."""

from contextlib import contextmanager
from copy import deepcopy
import json

import httpx

from desk.shop_checkout.provider import WooSandbox


TISSUES = "FYP-QA-POCKET-TISSUES"
PEN = "FYP-QA-PEN-BLUE"
CURRENCY = {"currency_code": "HKD", "currency_minor_unit": 2}
REQUEST = {
    "items": [
        {"product": "Pocket tissues", "quantity": 1},
        {"product": PEN, "quantity": 1},
        {"product": TISSUES, "quantity": 1},
    ]
}


def approved_basket():
    # Expected merchant lines come from the order fixture, independently of cart JSON.
    return {
        "items": [
            {
                "product_id": 21,
                "sku": TISSUES,
                "quantity": 2,
                "subtotal_minor": 800,
                "discount_minor": 0,
                "subtotal_tax_minor": 0,
                "tax_minor": 0,
            },
            {
                "product_id": 43,
                "sku": PEN,
                "quantity": 1,
                "subtotal_minor": 1700,
                "discount_minor": 0,
                "subtotal_tax_minor": 0,
                "tax_minor": 0,
            },
        ],
        "currency": "HKD",
        "subtotal_minor": 2500,
        "discount_minor": 0,
        "fees": [],
        "fees_minor": 0,
        "shipping_minor": 800,
        "shipping_tax_minor": 0,
        "tax_minor": 0,
        "total_minor": 3300,
        "rate_id": "flat_rate:1",
    }


def product(ident, sku, name, kind):
    return {
        "id": ident,
        "sku": sku,
        "name": name,
        "type": kind,
        "is_purchasable": True,
        "is_in_stock": True,
    }


class WooFixture(WooSandbox):
    def __init__(self):
        super().__init__(None)
        self.catalog = {
            21: product(21, TISSUES, "Pocket tissues", "simple"),
            42: product(42, "FYP-QA-PEN", "Stationery pen", "variable"),
            43: product(43, PEN, "Stationery pen – Blue", "variation"),
            44: product(44, "FYP-QA-PEN-RED", "Stationery pen – Red", "variation"),
        }
        self.units = {21: 400, 43: 1700, 44: 1700}
        self.shipping = 800
        self.carts = {}
        self.addressed = []
        self.posts = []
        self.orders = {}
        self.cancels = []
        self.stripe_reads = []
        self.cart_basis = approved_basket()
        self.gateway_terms = approved_basket()
        self.change_cart = lambda cart: None
        self.lose_ack = False
        self.visible = True
        self.captured = 3300
        self.charge_override = None
        self.account = "acct_fixture"
        self.intent_id = "pi_fixture"
        self.charge_id = "ch_fixture"
        self.amount_refunded = 0
        self.refunds = []
        self.page_size = 100

    @contextmanager
    def shop(self):
        with httpx.Client(
            base_url="https://woo.invalid/", transport=httpx.MockTransport(self.woo_http)
        ) as client:
            yield client, {}

    @contextmanager
    def stripe(self):
        with httpx.Client(
            base_url="https://stripe.invalid/", transport=httpx.MockTransport(self.stripe_http)
        ) as client:
            yield client, self.account

    def full_cart(self, units):
        lines = []
        for ident, qty in reversed(units):
            item = self.catalog[ident]
            unit = self.units[ident]
            lines.append(
                {
                    "id": ident,
                    "sku": item["sku"],
                    "name": item["name"],
                    "quantity": qty,
                    "prices": {**CURRENCY, "price": str(unit)},
                    "totals": {
                        **CURRENCY,
                        "line_subtotal": str(unit * qty),
                        "line_total": str(unit * qty),
                        "line_subtotal_tax": "0",
                        "line_total_tax": "0",
                    },
                }
            )
        subtotal = sum(self.units[ident] * qty for ident, qty in units)
        cart = {
            "items": lines,
            "fees": [],
            "needs_shipping": True,
            "has_calculated_shipping": True,
            "payment_methods": ["stripe_cc"],
            "shipping_rates": [
                {
                    "shipping_rates": [
                        {
                            **CURRENCY,
                            "selected": True,
                            "rate_id": "flat_rate:1",
                            "name": "HK delivery",
                            "price": str(self.shipping),
                            "taxes": "0",
                        }
                    ]
                }
            ],
            "totals": {
                **CURRENCY,
                "total_items": str(subtotal),
                "total_items_tax": "0",
                "total_discount": "0",
                "total_discount_tax": "0",
                "total_fees": "0",
                "total_fees_tax": "0",
                "total_shipping": str(self.shipping),
                "total_shipping_tax": "0",
                "total_tax": "0",
                "total_price": str(subtotal + self.shipping),
            },
        }
        self.change_cart(cart)
        return cart

    def woo_http(self, req):
        path = req.url.path
        body = json.loads(req.content) if req.content else {}
        if path == "/wc/store/v1/products":
            params = req.url.params
            rows = [
                p
                for p in self.catalog.values()
                if (p["type"] == "variation") == (params.get("type") == "variation")
            ]
            if "sku" in params:
                rows = [p for p in rows if p["sku"].casefold() == params["sku"].casefold()]
            else:
                rows = [p for p in rows if params["search"].casefold() in p["name"].casefold()]
            return httpx.Response(200, json=rows)
        if path == "/wc/store/v1/cart":
            token = f"cart-{len(self.carts)}"
            self.carts[token] = []
            return httpx.Response(200, json={}, headers={"Cart-Token": token})
        if path == "/wc/store/v1/cart/add-item":
            if not self.catalog[body["id"]]["is_in_stock"]:
                return httpx.Response(409, json={"code": "out_of_stock"})
            self.carts[req.headers["Cart-Token"]].append((body["id"], body["quantity"]))
            return httpx.Response(200, json={})
        if path == "/wc/store/v1/cart/update-customer":
            token = req.headers["Cart-Token"]
            assert body["shipping_address"]["country"] == "HK"
            self.addressed.append(token)
            return httpx.Response(200, json=self.full_cart(self.carts[token]))
        assert path.startswith("/fyp-alice/v1/orders/")
        ref = path.split("/")[4]
        if req.method == "GET":
            return httpx.Response(
                200,
                json=self.orders.get(ref, {"found": False}) if self.visible else {"found": False},
            )
        if path.endswith("/cancel"):
            order = self.orders[ref]
            assert body == {"order": order["order_id"], "amount_minor": self.captured}
            assert not self.refunds and self.amount_refunded == 0
            self.cancels.append(ref)
            self.amount_refunded = self.captured
            self.refunds = [self.refund("re_fixture", self.captured)]
            order.update(
                status="refunded",
                refunded_minor=self.captured,
                buyer_cancel_requested=True,
                can_cancel=False,
            )
            return httpx.Response(200, json=order)
        token = req.headers["Cart-Token"]
        assert token in self.addressed and body["test_method"] == "pm_fixture"
        assert body["cart_basis"] == self.cart_basis
        self.posts.append((ref, body["approved"]))
        if body["approved"] != self.gateway_terms:
            return httpx.Response(
                409,
                json={
                    "code": "fyp_quote_changed",
                    "data": {
                        "revision": {
                            "terms": self.gateway_terms,
                            "shipping_name": "HK delivery",
                        }
                    },
                },
            )
        assert ref not in self.orders, "second gateway dispatch"
        self.record_order(ref, self.gateway_terms)
        if self.lose_ack:
            self.visible = False
            return httpx.Response(503)
        return httpx.Response(200, json=self.orders[ref])

    def record_order(self, ref, terms):
        actual = deepcopy(terms)
        if "items" in actual:
            actual["items"].reverse()  # Woo order rows need not be in cart insertion order.
        self.orders[ref] = {
            "found": True,
            "order_id": 67,
            "terms": actual,
            "guest": True,
            "test_mode": True,
            "gateway": "stripe_cc",
            "paid": True,
            "status": "processing",
            "can_cancel": True,
            "refunded_minor": 0,
            "intent": self.intent_id,
            "transaction": self.charge_id,
        }

    def refund(self, ident, amount, status="succeeded"):
        return {
            "object": "refund", "id": ident, "charge": self.charge_id,
            "payment_intent": self.intent_id, "livemode": False, "currency": "hkd",
            "amount": amount, "status": status,
        }

    def stripe_http(self, req):
        path = req.url.path
        self.stripe_reads.append(path)
        if path == "/payment_methods/pm_card_visa":
            return httpx.Response(200, json={"livemode": False})
        if path == "/payment_methods":
            assert req.headers["Idempotency-Key"].startswith("fyp-woo-method-")
            return httpx.Response(
                200, json={"id": "pm_fixture", "livemode": False, "card": {"last4": "4242"}}
            )
        assert req.method == "GET"
        if path == "/payment_intents/" + self.intent_id:
            return httpx.Response(
                200,
                json={
                    "id": self.intent_id,
                    "livemode": False,
                    "latest_charge": self.charge_id,
                    "status": "succeeded",
                    "amount_received": self.captured,
                    "currency": "hkd",
                },
            )
        if path == "/charges/" + self.charge_id:
            return httpx.Response(
                200,
                json={
                    "id": self.charge_id,
                    "payment_intent": self.intent_id,
                    "livemode": False,
                    "status": "succeeded",
                    "paid": True,
                    "captured": True,
                    "amount_captured": self.captured if self.charge_override is None else self.charge_override,
                    "currency": "hkd",
                    "refunded": self.amount_refunded == self.captured,
                    "amount_refunded": self.amount_refunded,
                    "payment_method_details": {"card": {"brand": "visa", "last4": "4242"}},
                },
            )
        assert path == "/refunds" and req.url.params["charge"] == self.charge_id
        cursor = req.url.params.get("starting_after")
        start = [r["id"] for r in self.refunds].index(cursor) + 1 if cursor else 0
        end = start + min(self.page_size, int(req.url.params["limit"]))
        return httpx.Response(200, json={"has_more": end < len(self.refunds), "data": self.refunds[start:end]})
