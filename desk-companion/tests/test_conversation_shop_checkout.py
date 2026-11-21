import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.commerce_review import ReviewDecision
from desk.shop_checkout.provider import cart_quote
from desk.store import DomainError
from session_protocol_fixture import install_session_protocol


def quote(shipping=800):
    return {
        "name": "测试文具包",
        "unit_minor": 1700,
        "destination": "HK",
        "shipping_name": "HK test delivery",
        "terms": {
            "product_id": 15,
            "quantity": 2,
            "sku": "FYP-QA-DELIVERY-PACK",
            "currency": "HKD",
            "subtotal_minor": 3400,
            "discount_minor": 0,
            "fees_minor": 0,
            "shipping_minor": shipping,
            "tax_minor": 0,
            "total_minor": 3400 + shipping,
            "rate_id": "flat_rate:1",
        },
    }


class Shop:
    def __init__(self):
        self.rate = 800
        self.orders = {}
        self.checks = 0
        self.submissions = 0
        self.lose_ack = False

    def quote(self, request):
        assert request.quantity == 2 and request.product == "测试文具包"
        return quote(self.rate)

    def checkout(self, ref, approved):
        self.submissions += 1
        if quote(self.rate) != approved:
            return quote(self.rate)
        self.orders.setdefault(
            ref,
            {
                "order": 20,
                "charged_minor": approved["terms"]["total_minor"],
                "order_status": "processing",
                "test_mode": True,
            },
        )
        if self.lose_ack:
            raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503)
        return None

    def receipt(self, ref, approved):
        self.checks += 1
        return self.orders.get(ref)


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_WOO_SANDBOX_CONFIG", "/fixture")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    protocol = install_session_protocol(runtime)
    protocol.next_calls = [("sandbox_shop_quote", {"product": "测试文具包", "quantity": 2})]
    provider = Shop()
    runtime.shop_orders.provider = provider
    c = TestClient(app)
    login(c)
    return c, runtime, provider


def login(c):
    assert c.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success


def send(c, key, message, chat=None, order=None):
    payload = {"message": message, "language": "zh", "conversation_id": chat}
    if order:
        payload["shopping_review"] = {k: order[k] for k in ("id", "version")} | {
            "amount_minor": order["review_minor"]
        }
    return c.post(
        "/api/assistant/messages",
        json=payload,
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )


@pytest.mark.parametrize(
    "rate,decision", [(1200, "确认支付"), (500, "确认支付"), (1200, "拒绝新价格")]
)
def test_changed_cart_requires_bound_second_owner_decision(desk, rate, decision):
    c, r, s = desk
    initial = send(c, "first", "请买两包测试文具包").json()
    assert initial["kind"] == "shopping_order" and "HK$42.00" in initial["message"]
    row = initial["shopping_order"]
    chat = initial["conversation_id"]
    assert s.submissions == 0 and not s.orders
    assert send(c, "unbound", "确认", chat).json()["kind"] == "clarify"
    s.rate = rate
    changed = send(c, "review1", "确认支付 HK$42.00", chat, row).json()["shopping_order"]
    assert changed["state"] == "reprice" and changed["approved_minor"] == 4200 and not s.orders
    assert (
        changed["quote"]["terms"]["shipping_minor"] == rate and changed["previous"] == row["quote"]
    )
    assert send(c, "bad", "确认支付 HK$42.00", chat, changed).status_code == 409
    other = TestClient(c.app)
    login(other)
    assert send(other, "foreign", decision, chat, changed).status_code == 404
    r.voice.conversations.entries.clear()
    final = send(c, "review2", decision, chat, changed).json()["shopping_order"]
    if decision == "确认支付":
        assert final["receipt"]["charged_minor"] == 3400 + rate
        assert (
            c.get("/api/assistant/commerce-reviews", params={"conversation_id": chat}).json()[
                "rows"
            ][0]["kind"]
            == "shop"
        )
        reads = s.checks
        lookup = send(c, "lookup", "帮我查回这笔购物订单的订单号和实际模拟扣款金额", chat).json()
        assert lookup["shopping_order"]["receipt"] == final["receipt"] and s.checks > reads
        assert len(s.orders) == 1
    else:
        assert final["state"] == "cancelled" and not s.orders


def test_duplicate_or_lost_checkout_response_reopens_one_order(desk):
    c, r, s = desk
    s.lose_ack = True
    initial = send(c, "q", "买两包测试文具包").json()
    row = initial["shopping_order"]
    chat = initial["conversation_id"]
    review = ReviewDecision(
        id=row["id"], version=row["version"], amount_minor=row["review_minor"], action="confirm"
    )
    owner = {"kind": "owner", "id": "owner", "session": c.cookies["desk_companion_session"]}
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: r.shop_orders.decide(review, owner, chat), range(2)))
    assert (
        s.submissions == 1
        and len(s.orders) == 1
        and all(x["receipt"]["charged_minor"] == 4200 for x in results)
    )
    s.orders[row["id"]]["order_status"] = "completed"
    assert r.shop_orders.reopen(row["id"], owner, chat)["receipt"]["order_status"] == "completed"
    s.orders[row["id"]]["charged_minor"] = 5
    uncertain = r.shop_orders.reopen(row["id"], owner, chat)
    assert uncertain["state"] == "unverified" and uncertain["receipt"] is None


def test_missing_shipping_cannot_be_displayed_as_free():
    cart = {
        "items": [{"id": 15, "quantity": 2}],
        "totals": {"currency_code": "HKD", "currency_minor_unit": 2},
        "payment_methods": ["stripe_cc"],
        "needs_shipping": True,
        "has_calculated_shipping": False,
        "shipping_rates": [],
    }
    with pytest.raises(DomainError, match="SHOP_DELIVERY_UNAVAILABLE"):
        cart_quote(cart, 15, 2)


@pytest.mark.parametrize(
    "bad", ["refund", "wrong_currency", "other_intent", "live", "wrong_amount"]
)
def test_independent_gateway_read_rejects_unmatched_capture(bad):
    from contextlib import contextmanager
    import httpx
    from desk.shop_checkout.provider import WooSandbox

    shop = WooSandbox(None)
    cart = quote()
    order = {
        "found": True,
        "test_mode": True,
        "guest": True,
        "gateway": "stripe_cc",
        "terms": cart["terms"],
        "order_id": 23,
        "paid": True,
        "status": "processing",
        "intent": "pi_fixture",
        "transaction": "ch_fixture",
    }
    pi = {
        "id": "pi_fixture",
        "livemode": False,
        "latest_charge": "ch_fixture",
        "status": "succeeded",
        "amount_received": 4200,
        "currency": "hkd",
    }
    charge = {
        "id": "ch_fixture",
        "payment_intent": "pi_fixture",
        "livemode": False,
        "status": "succeeded",
        "paid": True,
        "captured": True,
        "amount_captured": 4200,
        "currency": "hkd",
        "refunded": False,
        "amount_refunded": 0,
        "payment_method_details": {"card": {"brand": "visa", "last4": "4242"}},
    }

    @contextmanager
    def store():
        with httpx.Client(
            base_url="http://localhost/",
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=order)),
        ) as client:
            yield client, {}

    @contextmanager
    def stripe():
        with httpx.Client(
            base_url="https://api.stripe.com/v1/",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json=pi if "/payment_intents/" in r.url.path else charge
                )
            ),
        ) as client:
            yield client

    shop.shop = store
    shop.stripe = stripe
    assert shop.receipt("fixture", cart)["charged_minor"] == 4200
    charge.update(
        {
            "refund": {"refunded": True, "amount_refunded": 100},
            "wrong_currency": {"currency": "usd"},
            "other_intent": {"payment_intent": "pi_foreign"},
            "live": {"livemode": True},
            "wrong_amount": {"amount_captured": 4199},
        }[bad]
    )
    with pytest.raises(DomainError, match="SHOP_UNVERIFIED"):
        shop.receipt("fixture", cart)


@pytest.mark.parametrize("rate", [700, 900])
def test_exact_second_approval_of_gateway_only_shipping_change(rate):
    import httpx
    from contextlib import contextmanager
    from desk.shop_checkout.provider import WooSandbox, checkout_revision

    basis = quote()
    updated = quote(rate)
    revision = checkout_revision(
        basis, {"terms": updated["terms"], "shipping_name": updated["shipping_name"]}
    )
    sent = []

    def merchant(req):
        if req.method == "GET":
            return httpx.Response(200, json={"found": False})
        body = json.loads(req.content)
        sent.append(body)
        return httpx.Response(200, json={"found": True})

    @contextmanager
    def session():
        with httpx.Client(
            base_url="http://localhost/", transport=httpx.MockTransport(merchant)
        ) as client:
            yield client, {}

    s = WooSandbox(None)
    s.shop = session
    s.test_method = lambda ref: "pm_fixture"
    s.cart = lambda client, product, qty: (basis, {"Cart-Token": "fixture"})
    assert s.checkout("one", revision) is None
    assert (
        len(sent) == 1
        and sent[0]["approved"] == updated["terms"]
        and sent[0]["cart_basis"] == basis["terms"]
    )
    with pytest.raises(DomainError, match="SHOP_UNVERIFIED"):
        checkout_revision(basis, {"terms": dict(updated["terms"], quantity=3), "shipping_name": ""})


def test_buyer_cancellation_in_chat_refund_recovery_and_foreign_order(desk, monkeypatch):
    c, runtime, shop = desk
    initial = send(c, "buy", "买两包文具").json()
    chat = initial["conversation_id"]
    paid = send(c, "pay", "确认支付", chat, initial["shopping_order"]).json()["shopping_order"]
    record = shop.orders[paid["id"]]
    record["can_cancel"] = True
    cancel_calls = []

    def request(ref, prior):
        cancel_calls.append(ref)
        record.update(buyer_cancel_requested=True, can_cancel=False, refund_status="pending")
        raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503)

    monkeypatch.setattr(shop, "cancel", request, raising=False)
    other = TestClient(c.app)
    login(other)
    assert send(other, "wrong", "取消这笔购物订单并全额退款", chat, paid).status_code == 404
    assert not cancel_calls
    result = send(c, "stop", "帮我取消这笔购物订单并全额退款", chat).json()
    assert result["shopping_order"]["state"] == "refund_pending" and len(cancel_calls) == 1
    runtime.voice.conversations.entries.clear()
    record.update(
        order_status="refunded", refund_status="succeeded", refunded_minor=4200, net_minor=0
    )
    repeated = send(c, "same", "取消这笔购物订单并全额退款", chat, paid).json()["shopping_order"]
    assert repeated["state"] == "refunded" and len(cancel_calls) == 1
    reopened = send(c, "read-refund", "查回这笔购物订单的退款结果", chat).json()
    assert (
        reopened["shopping_order"]["receipt"]["charged_minor"] == 4200
        and "净扣款 HK$0.00" in reopened["message"]
    )


def test_refund_cannot_be_claimed_from_a_charge_or_wrong_refund_alone():
    from desk.shop_checkout.provider import refund_receipt

    charge = {
        "id": "ch_test",
        "payment_intent": "pi_test",
        "refunded": True,
        "amount_refunded": 1200,
    }
    order = {"status": "refunded", "refunded_minor": 1200, "buyer_cancel_requested": True}
    refund = {
        "object": "refund",
        "charge": "ch_test",
        "id": "re_test",
        "payment_intent": "pi_test",
        "currency": "hkd",
        "amount": 1200,
        "status": "succeeded",
    }
    read = lambda values: refund_receipt(order, charge, {"data": values, "has_more": False}, 1200)
    assert read([]) == {"refund_status": "pending"}
    assert read([refund | {"status": "pending"}]) == {"refund_status": "pending"}
    assert read([refund])["net_minor"] == 0
    for changes in (
        {"charge": "ch_other"},
        {"payment_intent": "pi_other"},
        {"amount": 650},
        {"currency": "usd"},
        {"livemode": True},
    ):
        with pytest.raises(DomainError):
            read([refund | changes])


def test_fulfilled_order_cannot_refund_on_a_buyer_request(desk):
    c, _, shop = desk
    quote = send(c, "q", "买两包文具").json()
    chat = quote["conversation_id"]
    paid = send(c, "p", "确认支付", chat, quote["shopping_order"]).json()["shopping_order"]
    shop.orders[paid["id"]].update(order_status="completed", can_cancel=False)
    result = send(c, "late", "取消这笔购物订单并全额退款", chat, paid).json()
    assert result["shopping_order"]["state"] == "completed" and "未接受" in result["message"]


def test_asking_about_or_quoting_a_cancellation_never_refunds(desk, monkeypatch):
    c, _, shop = desk
    quoted = send(c, "read-q", "买两包文具").json()
    chat = quoted["conversation_id"]
    paid = send(c, "read-p", "确认支付", chat, quoted["shopping_order"]).json()["shopping_order"]
    shop.orders[paid["id"]].update(can_cancel=True)
    calls = []
    monkeypatch.setattr(shop, "cancel", lambda *args: calls.append(args), raising=False)
    result = send(c, "can-i", "这笔购物订单可以取消吗？", chat).json()
    assert result["shopping_order"]["state"] == "completed" and "仍接受" in result["message"]
    from desk import commerce_aftercare
    from types import SimpleNamespace

    fake = SimpleNamespace(
        attachment_ids=[], flight_review=None, shopping_review=None, language="zh"
    )
    for text in ["取消这笔购物订单？", "不要取消这笔订单", "她说「取消这笔订单」"]:
        fake.message = text
        assert (
            commerce_aftercare.turn(
                None, fake, {"kind": "owner"}, SimpleNamespace(attachment_ids=[])
            )
            is None
        )
    assert not calls


def test_inferred_price_ref_cannot_cancel_another_order_in_the_same_chat(desk, monkeypatch):
    from desk.assistant import AssistantMessage
    from desk.store import encode
    from copy import deepcopy
    from datetime import timedelta
    from desk.calendar import iso

    client, runtime, shop = desk
    first = send(client, "multi-quote", "买两包文具").json()
    chat = first["conversation_id"]
    paid = send(client, "multi-pay", "确认支付", chat, first["shopping_order"]).json()[
        "shopping_order"
    ]
    shop.orders[paid["id"]]["can_cancel"] = True
    # Recreate a second previously saved, unapproved quote from this chat.
    with runtime.store.connection(write=True) as db:
        record = db.execute(
            "select owner,data from sandbox_shop_orders where id=?", (paid["id"],)
        ).fetchone()
        second = deepcopy(json.loads(record["data"]))
        second.update(
            id="e" * 32,
            state="quoted",
            version=1,
            expires=iso(runtime.store.clock() + timedelta(minutes=5)),
        )
        second.pop("receipt")
        second.pop("last_review")
        db.execute(
            "insert into sandbox_shop_orders(id,owner,chat,data) values(?,?,?,?)",
            (second["id"], record["owner"], chat, encode(second)),
        )
    inferred = {"id": second["id"], "version": 1, "review_minor": 4200}
    ambiguous = send(client, "multi-generic", "取消这笔购物订单并全额退款", chat, inferred).json()
    assert ambiguous["kind"] == "clarify"
    named = send(client, "multi-read", "查回购物订单 #20 的退款结果", chat, inferred).json()
    assert (
        named["shopping_order"]["id"] == paid["id"]
        and named["shopping_order"]["state"] == "completed"
    )
    calls = []

    def cancel(ref, prior):
        calls.append(ref)
        shop.orders[ref].update(
            buyer_cancel_requested=True,
            can_cancel=False,
            refund_status="succeeded",
            refunded_minor=4200,
            net_minor=0,
        )

    monkeypatch.setattr(shop, "cancel", cancel, raising=False)
    decision = {
        "message": "取消这笔购物订单并全额退款",
        "conversation_id": chat,
        "language": "zh",
        "selected_commerce_card": True,
        "shopping_review": {"id": paid["id"], "version": paid["version"], "amount_minor": 4200},
    }
    selected = client.post(
        "/api/assistant/messages",
        json=decision,
        headers={"X-Desk-Request": "1", "X-Operation-Id": "multi-card"},
    ).json()
    assert selected["shopping_order"]["state"] == "refunded" and calls == [paid["id"]]
    assert "selected_commerce_card" not in AssistantMessage(message="old request").model_dump()
