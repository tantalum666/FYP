from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from desk.app import COOKIE, create_app
from desk.capabilities import parse_call
from desk.commerce_review import ReviewDecision
from desk.conversation import Conversations
from desk.shop_checkout.provider import ShopQuery, cart_quote, checkout_revision
from desk.store import DomainError
from session_protocol_fixture import install_session_protocol
from test_conversation_shop_checkout import quote as original_single_quote, send
from woo_basket_fixture import PEN, REQUEST, TISSUES, WooFixture, approved_basket, product


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_WOO_SANDBOX_CONFIG", "/fixture-only")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    session = install_session_protocol(runtime)
    session.next_calls = [("sandbox_shop_quote", REQUEST)]
    runtime.shop_orders.provider = woo = WooFixture()
    client = TestClient(app)
    client.cookies.set(COOKIE, runtime.store.create_owner_session())
    return client, runtime, woo, session


def start(client, message="买两包纸巾和一支蓝笔"):
    response = send(client, "basket", message)
    assert response.is_success, response.text
    reply = response.json()
    assert reply["kind"] == "shopping_order", reply
    return reply["conversation_id"], reply["shopping_order"]


def render(row):
    script = Path(__file__).resolve().parents[1] / "frontend/tests/fixtures/shop-basket-review.mjs"
    result = subprocess.run(
        ["node", "--experimental-strip-types", str(script)],
        input=json.dumps(row),
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_one_cart_one_review_then_original_full_refund(desk):
    client, _, woo, session = desk
    chat, row = start(client)
    tool = next(
        t for t in session.creations[0]["agent"]["tools"] if t["name"] == "sandbox_shop_quote"
    )
    assert {"product", "quantity", "items", "budget_minor", "currency"} == tool["parameters"]["properties"].keys()
    assert row["quote"]["terms"] == approved_basket()
    assert list(woo.carts.values()) == [[(21, 2), (43, 1)]]
    assert woo.addressed == ["cart-0"] and not woo.posts and not woo.stripe_reads
    view = render(row)
    assert view["home"] == "2 products · HK$33.00"
    summary, details = view["markup"].split("<details>")
    assert TISSUES not in summary and PEN not in summary
    assert details.count("<li>") == 2 and TISSUES in details and PEN in details
    assert "HK$8.00" in details and "HK$17.00" in details
    decision = view["decision"]
    assert decision["review"] == {
        "kind": "shop",
        "id": row["id"],
        "amount_minor": 3300,
        "version": row["version"],
    }
    result = client.post(
        "/api/assistant/messages",
        headers={"X-Desk-Request": "1", "X-Operation-Id": "card"},
        json={
            "message": decision["message"],
            "conversation_id": chat,
            "shopping_review": {k: v for k, v in decision["review"].items() if k != "kind"},
        },
    )
    assert result.is_success, result.text
    paid = result.json()["shopping_order"]
    assert paid["receipt"]["charged_minor"] == 3300 and paid["state"] == "completed"
    assert len(woo.addressed) == 2 and len(woo.posts) == len(woo.orders) == 1
    # The payment and aftercare read back the original Woo order and its independent Stripe records.
    refund = send(client, "cancel-paid", "取消这笔购物订单并全额退款", chat, paid).json()[
        "shopping_order"
    ]
    assert refund["state"] == "refunded" and refund["receipt"]["refunded_minor"] == 3300
    assert refund["receipt"]["net_minor"] == 0 and woo.cancels == [row["id"]]
    again = send(client, "refund-again", "取消这笔购物订单并全额退款", chat, paid).json()[
        "shopping_order"
    ]
    assert again["receipt"] == refund["receipt"] and len(woo.cancels) == 1
    assert {"/payment_intents/pi_fixture", "/charges/ch_fixture", "/refunds"} <= set(
        woo.stripe_reads
    )


def test_cart_rebalances_line_gross_at_same_total_then_owner_declines(desk):
    client, _, woo, _ = desk
    chat, first = start(client)
    woo.units.update({21: 450, 43: 1600})
    reply = send(client, "confirm", "确认支付 HK$33.00", chat, first).json()
    revised = reply["shopping_order"]
    assert revised["state"] == "reprice" and revised["review_minor"] == first["review_minor"]
    assert revised["previous"] == first["quote"] and "仍为" in reply["message"]
    assert [line["subtotal_minor"] for line in revised["quote"]["terms"]["items"]] == [900, 1600]
    assert render(revised)["home"] == "2 products · Terms changed · HK$33.00"
    replay = send(client, "stale", "确认支付 HK$33.00", chat, first).json()["shopping_order"]
    assert replay["state"] == "reprice" and not woo.posts and not woo.stripe_reads
    assert (
        send(client, "decline", "取消购物", chat, revised).json()["shopping_order"]["state"]
        == "cancelled"
    )
    assert not woo.orders


@pytest.mark.parametrize("shipping", [790, 800])
def test_gateway_only_discount_fee_and_rate_require_new_approval(desk, shipping):
    client, _, woo, _ = desk
    chat, first = start(client)
    actual = woo.gateway_terms
    actual["items"][1]["discount_minor"] = 200
    actual.update(
        discount_minor=200,
        fees_minor=180,
        fees=[{"name": "Handling", "total_minor": 180, "tax_minor": 10}],
        shipping_minor=shipping,
        shipping_tax_minor=10,
        tax_minor=20,
        total_minor=2500 + shipping,
        rate_id="flat_rate:2",
    )
    revised = send(client, "pay-first", "确认支付", chat, first).json()["shopping_order"]
    assert revised["state"] == "reprice" and revised["quote"]["terms"] == actual
    assert "checkout_basis" not in revised["quote"] and not woo.orders
    woo.captured = actual["total_minor"]
    paid = send(client, "pay-revised", "确认支付", chat, revised).json()["shopping_order"]
    assert paid["state"] == "completed" and paid["receipt"]["charged_minor"] == 2500 + shipping
    assert woo.posts == [(first["id"], approved_basket()), (first["id"], actual)]


@pytest.mark.parametrize("problem", ["ambiguous", "unknown", "unavailable", "combined_limit"])
def test_whole_request_fails_without_quoting_a_subset(desk, problem):
    client, _, woo, session = desk
    if problem == "ambiguous":
        woo.catalog[22] = product(22, "FYP-QA-OTHER", "Pocket tissues", "simple")
    elif problem == "unknown":
        del woo.catalog[43]
    elif problem == "unavailable":
        woo.catalog[43]["is_in_stock"] = False
    else:
        request = deepcopy(REQUEST)
        request["items"][2]["quantity"] = 99
        session.next_calls = [("sandbox_shop_quote", request)]
    reply = send(client, "bad-basket", "买纸巾和蓝笔").json()
    assert reply["kind"] == "clarify" and "shopping_order" not in reply
    assert (
        reply["error"]
        == {
            "ambiguous": "SHOP_AMBIGUOUS",
            "unknown": "SHOP_NO_MATCH",
            "unavailable": "SHOP_ITEM_UNAVAILABLE",
            "combined_limit": "SHOP_QUANTITY_LIMIT",
        }[problem]
    )
    assert not woo.carts and not woo.posts and not woo.orders


@pytest.mark.parametrize("stage", ["add", "addressed"])
def test_out_of_stock_after_review_cannot_submit_the_other_line(desk, stage):
    client, _, woo, _ = desk
    chat, row = start(client)
    if stage == "add":
        woo.catalog[43]["is_in_stock"] = False
    else:
        # Woo can retain every priced line alongside a cart validation error.
        woo.change_cart = lambda cart: cart.update(errors=[{"code": "product_out_of_stock"}])
    result = send(client, "stock", "确认支付", chat, row).json()["shopping_order"]
    assert result["state"] == "unavailable" and result["receipt"] is None
    assert not woo.posts and not woo.stripe_reads


def test_null_shipping_is_valid_only_for_a_virtual_cart():
    woo = WooFixture()
    woo.catalog[55] = product(55, "FYP-QA-EBOOK", "Test ebook", "simple")
    woo.units[55] = 500
    cart = woo.full_cart([(55, 1)])
    requested = {55: ("FYP-QA-EBOOK", 1)}
    cart["totals"].update(total_shipping=None, total_shipping_tax=None, total_price="500")
    with pytest.raises(DomainError, match="SHOP_UNVERIFIED"):
        cart_quote(cart, requested)
    cart.update(needs_shipping=False, has_calculated_shipping=False, shipping_rates=[])
    quote = cart_quote(cart, requested)
    terms = quote["terms"]
    assert quote["destination"] is None and terms["rate_id"] == ""
    assert terms["shipping_minor"] == terms["shipping_tax_minor"] == 0
    assert terms["subtotal_minor"] == terms["total_minor"] == 500


@pytest.mark.parametrize(
    "problem", ["omitted", "extra", "duplicate", "variant", "sku", "quantity", "currency", "rate"]
)
def test_final_addressed_cart_must_match_every_requested_line(problem):
    woo = WooFixture()

    def change(cart):
        line = cart["items"][0]
        if problem == "omitted":
            missing = cart["items"].pop()
            subtotal = int(cart["totals"]["total_items"]) - int(missing["totals"]["line_subtotal"])
            cart["totals"].update(total_items=str(subtotal), total_price=str(subtotal + 800))
        elif problem == "extra":
            cart["items"].append({**line, "id": 44, "sku": "RED"})
        elif problem == "duplicate":
            cart["items"].append(line)
        elif problem == "variant":
            line["id"] = 42  # Variable parent at the same price.
        elif problem == "sku":
            line["sku"] = "RED"
        elif problem == "quantity":
            line["quantity"] += 1
        elif problem == "currency":
            line["totals"]["currency_code"] = "USD"
        else:
            cart["shipping_rates"][0]["shipping_rates"][0]["selected"] = False

    woo.change_cart = change
    with pytest.raises(DomainError, match="SHOP_DELIVERY_UNAVAILABLE|SHOP_UNVERIFIED"):
        woo.quote(ShopQuery.model_validate(REQUEST))
    assert not woo.posts


def test_unknown_submission_and_concurrent_recovery_use_one_reference(desk, monkeypatch):
    client, runtime, woo, _ = desk
    chat, row = start(client)
    woo.lose_ack = True
    unknown = send(client, "pay", "确认支付", chat, row).json()["shopping_order"]
    assert unknown["state"] == "checking" and unknown["receipt"] is None
    later = runtime.store.clock() + timedelta(seconds=75)
    monkeypatch.setattr(runtime.store, "clock", lambda: later)
    retry = client.get("/api/assistant/commerce-reviews", params={"conversation_id": chat}).json()[
        "rows"
    ][0]
    assert retry["state"] == "retry" and len(woo.orders) == 1
    woo.visible = True
    decision = ReviewDecision(
        id=row["id"], amount_minor=3300, version=retry["version"], action="confirm"
    )
    who = {"kind": "owner", "session": client.cookies[COOKIE]}
    with ThreadPoolExecutor(2) as pool:
        receipts = list(
            pool.map(lambda _: runtime.shop_orders.decide(decision, who, chat), range(2))
        )
    assert all(
        r["state"] == "completed" and r["receipt"]["charged_minor"] == 3300 for r in receipts
    )
    assert woo.posts == [(row["id"], approved_basket())] and len(woo.carts) == 2


@pytest.mark.parametrize("mismatch", ["capture", "merchant_line"])
def test_completed_receipt_requires_both_independent_records(desk, mismatch):
    client, _, woo, _ = desk
    chat, row = start(client)
    if mismatch == "capture":
        woo.charge_override = 3299  # Intent and Woo still report the approved HK$33.
        result = send(client, "pay", "确认支付", chat, row)
    else:
        paid = send(client, "pay", "确认支付", chat, row).json()["shopping_order"]
        assert paid["state"] == "completed"
        terms = woo.orders[row["id"]]["terms"]
        terms["items"][0]["subtotal_minor"] -= 100
        terms["items"][1]["subtotal_minor"] += 100
        result = send(client, "lookup", "查回这笔购物订单的实际模拟扣款金额", chat)
    checked = result.json()["shopping_order"]
    assert checked["state"] == "unverified"
    if mismatch == "capture":
        assert checked["receipt"] is None
    else:
        assert checked["receipt"]["last_verified"] and checked["receipt"]["charged_minor"] == 3300
    assert len(woo.posts) == 1 and not woo.cancels


def test_original_paid_single_row_reopens_without_catalog_or_checkout(desk):
    client, runtime, woo, _ = desk
    ref, chat = "e" * 32, "historical-chat"
    # Original persisted single-product layout and amounts from the pre-basket fixture.
    old = {
        "id": ref,
        "task_id": None,
        "state": "completed",
        "version": 4,
        "quote": original_single_quote(),
        "approved": 4200,
        "expires": "2026-11-19T10:15:00+08:00",
        "submitted_at": 1795053600,
        "next_read": 1795053608,
        "last_review": {"id": ref, "version": 1, "amount_minor": 4200, "action": "confirm"},
        "receipt": {
            "order": 67,
            "order_status": "processing",
            "charged_minor": 4200,
            "test_mode": True,
        },
    }
    owner = Conversations.owner({"kind": "owner", "session": client.cookies[COOKIE]})
    with runtime.store.connection(write=True) as db:
        db.execute(
            "INSERT INTO sandbox_shop_orders(id,owner,chat,data) VALUES(?,?,?,?)",
            (ref, owner, chat, json.dumps(old)),
        )
    woo.record_order(ref, old["quote"]["terms"])
    woo.captured = 4200
    woo.catalog.clear()
    result = send(client, "original", "帮我查回这笔购物订单的订单号和实际模拟扣款金额", chat).json()
    row = result["shopping_order"]
    assert row["state"] == "completed" and row["quote"] == old["quote"]
    assert row["receipt"]["charged_minor"] == 4200 and "HK$42.00" in result["message"]
    assert "测试文具包" in render(row)["markup"] and not woo.posts and not woo.carts
    assert woo.stripe_reads == ["/payment_intents/pi_fixture", "/charges/ch_fixture", "/refunds"]


def test_pending_legacy_approval_gets_detailed_terms_before_payment():
    woo = WooFixture()
    old = original_single_quote()
    woo.catalog[15] = product(15, old["terms"]["sku"], old["name"], "simple")
    woo.units[15] = 1700
    revised = woo.checkout("old-review", old)
    assert revised["terms"]["total_minor"] == old["terms"]["total_minor"]
    assert [(i["product_id"], i["sku"], i["quantity"]) for i in revised["terms"]["items"]] == [
        (15, old["terms"]["sku"], 2)
    ]
    assert not woo.posts and not woo.stripe_reads


def test_single_tool_shape_and_public_fields_still_work(desk):
    client, _, woo, session = desk
    session.next_calls = [("sandbox_shop_quote", {"product": TISSUES, "quantity": 2})]
    chat, row = start(client, "买两包纸巾")
    assert row["quote"]["name"] == "Pocket tissues" and row["quote"]["unit_minor"] == 400
    assert row["quote"]["terms"]["sku"] == TISSUES and row["quote"]["terms"]["quantity"] == 2
    assert row["review_minor"] == 1600 and render(row)["home"] == "Pocket tissues × 2 · HK$16.00"
    single = approved_basket()
    single["items"].pop()
    single.update(subtotal_minor=800, total_minor=1600)
    woo.cart_basis = woo.gateway_terms = single
    woo.captured = 1600
    paid = send(client, "pay-single", "确认支付 HK$16.00", chat, row).json()["shopping_order"]
    assert paid["state"] == "completed" and paid["receipt"]["charged_minor"] == 1600
    for args in (
        {},
        {"items": []},
        {"items": REQUEST["items"] * 3},
        {"product": TISSUES, "quantity": 1, **REQUEST},
        {"items": [{"product": PEN, "quantity": True}]},
    ):
        with pytest.raises(DomainError, match="TOOL_ARGUMENTS_INVALID"):
            parse_call("sandbox_shop_quote", args)


def test_checked_components_include_each_discount_tax_fee_and_delivery():
    woo = WooFixture()
    cart = woo.full_cart([(21, 2), (43, 1)])
    currency = {"currency_code": "HKD", "currency_minor_unit": 2}
    cart["items"][0]["totals"].update(
        line_total="1600", line_subtotal_tax="85", line_total_tax="80"
    )
    cart["fees"] = [{"name": "Handling", "totals": {**currency, "total": "100", "total_tax": "5"}}]
    cart["shipping_rates"][0]["shipping_rates"][0]["taxes"] = "40"
    cart["totals"].update(
        total_items_tax="85",
        total_discount="100",
        total_discount_tax="5",
        total_fees="100",
        total_fees_tax="5",
        total_shipping_tax="40",
        total_tax="125",
        total_price="3425",
    )
    basis = cart_quote(cart, {21: (TISSUES, 2), 43: (PEN, 1)})
    t = basis["terms"]
    assert [line["discount_minor"] for line in t["items"]] == [0, 100]
    assert [line["tax_minor"] for line in t["items"]] == [0, 80]
    assert t["fees"] == [{"name": "Handling", "total_minor": 100, "tax_minor": 5}]
    assert t["shipping_minor"] == 800 and t["shipping_tax_minor"] == 40 and t["total_minor"] == 3425
    for change in (
        {"currency": "USD"},
        {"items": t["items"][:1]},
        {"fees_minor": 101},
        {"shipping_tax_minor": 0},
        {"rate_id": ""},
        {"items": [{**t["items"][0], "product_id": 99}, t["items"][1]]},
    ):
        with pytest.raises(DomainError, match="SHOP_UNVERIFIED"):
            checkout_revision(basis, {"terms": {**t, **change}, "shipping_name": "HK delivery"})


@pytest.mark.skipif(shutil.which("php") is None, reason="local PHP CLI unavailable")
def test_php_merchant_matches_concrete_variation_and_original_single_order():
    fixture = Path(__file__).parent / "fixtures/woo_order_terms.php"
    result = subprocess.run(
        ["php", str(fixture)],
        input=json.dumps(approved_basket(), sort_keys=True),
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "basket": approved_basket(),
        "matches": True,
        "inconsistent_shipping": [None, None],
        "substituted": False,
        "legacy": original_single_quote()["terms"],
        "refund_totals": [1500, None, None, None],
    }
