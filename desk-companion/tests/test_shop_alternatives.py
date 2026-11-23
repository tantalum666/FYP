from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from fastapi.testclient import TestClient
import httpx
import pytest

from desk.app import COOKIE
from desk.flight_booking.provider import LetsFG
from test_conversation_flight_booking import Sandbox
from test_conversation_shop_checkout import send
from test_shop_basket import desk as desk, render, start
from woo_basket_fixture import PEN, TISSUES, approved_basket, product


GEL = "QA-FINE-GEL"
INK = "QA-FINE-INK"
RED = "FYP-QA-PEN-RED"


def pen_options(woo, session):
    woo.catalog[43].update(is_in_stock=False, variation="Color: Blue, Nib: Fine")
    woo.catalog[44]["variation"] = "Color: Red, Nib: Fine"
    for ident, sku, name, nib, unit in [
        (45, "QA-BROAD", "Broad pen", "Broad", 200),
        (46, "QA-LUXE", "Premium pen", "Fine", 1900),
        (47, "QA-BACKORDER", "Backordered pen", "Fine", 200),
        (48, GEL, "Refill pen", "Fine", 900),
        (49, INK, "Refill pen", "Fine", 1400),
    ]:
        woo.catalog[ident] = {
            **product(ident, sku, name, "variation"),
            "variation": f"Color: Blue, Nib: {nib}", "is_on_backorder": ident == 47,
        }
        woo.units[ident] = unit
    query = {
        "items": [
            {"product": TISSUES, "quantity": 2},
            {"product": PEN, "quantity": 2, "allowed_quantities": [1], "alternative_search": "pen",
             "required_attributes": {"Nib": "Fine"}},
        ],
        "currency": "HKD", "budget_minor": 3400,
    }
    session.next_calls = [("sandbox_shop_quote", query)]
    return query


def card(client, chat, control, operation):
    return client.post(
        "/api/assistant/messages",
        headers={"X-Desk-Request": "1", "X-Operation-Id": operation},
        json={
            "message": control["message"], "conversation_id": chat, "selected_commerce_card": True,
            "shopping_review": {k: v for k, v in control["review"].items() if k != "kind"},
        },
    )


def listed(client, chat):
    return client.get("/api/assistant/commerce-reviews", params={"conversation_id": chat}).json()["rows"]


def test_basket_and_flight_options_keep_their_own_reviews_in_one_chat(desk):
    client, runtime, woo, session = desk
    pen_options(woo, session)
    chat, shopping = start(client)
    day = (runtime.store.clock().date() + timedelta(days=7)).isoformat()
    flight = Sandbox(day)
    runtime.flight_bookings.enabled = True
    runtime.flight_bookings.provider = LetsFG(httpx.MockTransport(flight))
    session.next_calls = [("sandbox_flight_quote", {
        "origin": "HKG", "destination": "HND", "departure": day, "flight_number": "XX999",
    })]
    offered = send(client, "other-flight", "Find test flight XX999 from HKG to HND", chat).json()
    assert offered["flight_alternatives"]["shortlist_number"] == 1
    reviews = client.get("/api/assistant/commerce-reviews", params={"conversation_id": chat}).json()
    assert reviews["has_flight_shortlist"] and [r["id"] for r in reviews["rows"]] == [shopping["id"]]
    ambiguous = send(client, "bare-ordinal", "select option 1", chat).json()
    assert ambiguous["kind"] == "clarify" and not ambiguous.get("flight_booking")
    assert not ambiguous.get("shopping_order") and len(flight.calls) == 1
    assert "购物" in ambiguous["message"] and "航班" in ambiguous["message"]
    selected = send(client, "shop-ordinal", "select option 1", chat, shopping).json()
    assert selected["shopping_order"]["id"] == shopping["id"]
    assert selected["shopping_order"]["state"] == "quoted" and not selected.get("flight_booking")
    assert len(flight.calls) == 1 and not woo.payment_methods and not woo.orders
    explicit = send(client, "flight-ordinal", "select option 1 from flight list 1", chat).json()
    assert explicit["flight_booking"]["state"] == "quoted" and len(flight.calls) == 2


def test_mixed_alternative_card_requotes_selected_units_then_separately_pays(desk):
    client, runtime, woo, session = desk
    pen_options(woo, session)
    chat, offers = start(client, "Two tissues and two fine blue pens, one pen is also OK. HK$34 delivered.")
    assert offers["state"] == "choosing" and offers["quote"] is offers["review_minor"] is None
    assert [
        (o["number"], o["sku"], o["quantity"], o["shipping_minor"], o["total_minor"])
        for o in offers["alternatives"]
    ] == [(1, GEL, 2, 800, 3400), (2, GEL, 1, 800, 2500), (3, INK, 1, 800, 3000)]
    view = render(offers)
    assert "Choose an alternative" in view["home"] and "decision" not in view
    assert "HK$34.00" in view["markup"] and len(view["choices"]) == 3
    for key, message in [("same-name", "Refill pen"), ("same-sku", GEL), ("no-approval", "pay")]:
        assert send(client, key, message, chat, offers).json()["error"] == "SHOP_CHOICE_AMBIGUOUS"
    assert not woo.posts and not woo.payment_methods

    runtime.voice.conversations.entries.clear()
    woo.shipping = 900
    select = view["choices"][1]
    assert select["review"]["amount_minor"] is None
    response = card(client, chat, select, "select-gel")
    assert response.is_success, response.text
    quoted = response.json()["shopping_order"]
    expected = approved_basket()
    expected["items"][1].update(product_id=48, sku=GEL, quantity=1, subtotal_minor=900)
    expected.update(subtotal_minor=1700, shipping_minor=900, total_minor=2600)
    assert quoted["quote"]["terms"] == expected and quoted["state"] == "quoted"
    assert quoted["approved_minor"] is None and quoted["version"] > offers["version"]
    assert card(client, chat, select, "select-gel").json()["shopping_order"] == quoted
    assert send(client, "old-offer", "pay HK$26.00", chat, offers).status_code == 409
    assert not woo.payment_methods and not woo.orders

    woo.cart_basis = woo.gateway_terms = expected
    woo.captured = 2600
    review = render(quoted)
    assert GEL in review["markup"] and TISSUES in review["markup"]
    paid = card(client, chat, review["decision"], "pay-new").json()["shopping_order"]
    assert paid["state"] == "completed" and paid["receipt"]["charged_minor"] == 2600
    assert card(client, chat, review["decision"], "repeat-payment").json()["shopping_order"] == paid
    assert woo.posts == [(offers["id"], expected)] and len(woo.orders) == 1
    assert {"/payment_intents/pi_fixture", "/charges/ch_fixture"} <= set(woo.stripe_reads)


def test_missing_choice_keeps_remaining_ordinals_and_original_constraints(desk):
    client, _, woo, session = desk
    pen_options(woo, session)
    chat, first = start(client)
    # The selected product loses its required attribute, and the other choice's delivery changes.
    woo.catalog[48]["variation"] = "Color: Red, Nib: Fine"
    woo.shipping = 850
    reply = send(client, "second-gone", "第二个", chat, first).json()
    left = reply["shopping_order"]
    assert left["state"] == "choosing" and left["version"] > first["version"]
    assert [(o["number"], o["sku"], o["total_minor"]) for o in left["alternatives"]] == [(3, INK, 3050)]
    assert "3." in reply["message"] and "HK$8.50" in reply["message"]
    assert send(client, "stale-offer", "选第三个", chat, first).status_code == 409
    assert send(client, "old-number", "2", chat).json()["error"] == "SHOP_CHOICE_AMBIGUOUS"
    woo.shipping = 1300  # Even the remaining single pen plus the tissues now exceeds HK$34.
    stopped = send(client, "over-budget", "第三个", chat, left).json()["shopping_order"]
    assert stopped["state"] == "unavailable" and stopped["unavailable_reason"] == "SHOP_OVER_BUDGET"

    # New search is an independent review. Even with the original blue SKU deleted,
    # its bound color, owner-approved counts, full basket, and cap are retained.
    del woo.catalog[43]
    woo.shipping = 800
    new = send(client, "fresh-search", "find same-store alternatives", chat).json()["shopping_order"]
    assert new["id"] != stopped["id"] and new["state"] == "choosing"
    assert [(o["sku"], o["quantity"], o["total_minor"]) for o in new["alternatives"]] == [(INK, 1, 3000)]
    assert {r["id"]: r["state"] for r in listed(client, chat)} == {
        first["id"]: "unavailable", new["id"]: "choosing",
    }
    assert not woo.posts and not woo.payment_methods


def test_only_owner_allowed_smaller_quantity_can_be_selected_and_cancelled(desk):
    client, runtime, woo, session = desk
    woo.stock[21] = 1
    item = {"product": TISSUES, "quantity": 3}
    session.next_calls = [("sandbox_shop_quote", {"items": [item]})]
    assert send(client, "exact", "Buy three packs of tissues").json()["error"] == "SHOP_ITEM_UNAVAILABLE"
    session.next_calls = [("sandbox_shop_quote", {"items": [{**item, "allowed_quantities": [1]}]})]
    chat, offers = start(client, "Three packs of tissues, or one if three are unavailable.")
    assert [(o["sku"], o["quantity"], o["total_minor"]) for o in offers["alternatives"]] == [(TISSUES, 1, 1200)]
    other = TestClient(client.app)
    other.cookies.set(COOKIE, runtime.store.create_owner_session())
    assert send(other, "other-owner", "第一个", chat, offers).status_code == 404
    cancelled = send(client, "stop", "cancel this shopping order", chat, offers).json()["shopping_order"]
    assert cancelled["state"] == "cancelled"
    assert send(client, "old-choice", "选第一个", chat, offers).status_code == 409
    assert listed(client, chat)[0]["state"] == "cancelled" and not woo.posts and not woo.payment_methods


def test_competing_selections_produce_one_review_and_leave_declined_cart_closed(desk):
    client, _, woo, session = desk
    pen_options(woo, session)
    chat, offers = start(client)
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(
            lambda n: send(client, f"select-{n}", f"option {n}", chat, offers), [1, 3]
        ))
    assert sorted(r.status_code for r in responses) == [200, 409]
    quoted = next(r.json()["shopping_order"] for r in responses if r.is_success)
    assert quoted["state"] == "quoted" and quoted["version"] == offers["version"] + 1
    stopped = send(client, "decline", "decline", chat, quoted).json()["shopping_order"]
    assert stopped["state"] == "cancelled"
    assert send(client, "late-pay", "confirm", chat, quoted).status_code == 409
    fresh = send(client, "new-request", "请重新查一下同店的蓝笔和纸巾", chat).json()["shopping_order"]
    assert fresh["id"] != stopped["id"] and fresh["state"] == "choosing"
    assert next(r for r in listed(client, chat) if r["id"] == stopped["id"])["state"] == "cancelled"
    assert not woo.posts and not woo.payment_methods


def test_currency_and_expiry_do_not_create_a_payable_cart(desk, monkeypatch):
    client, runtime, woo, session = desk
    query = pen_options(woo, session)
    session.next_calls = [("sandbox_shop_quote", {**query, "currency": "USD"})]
    rejected = send(client, "usd", "Fine pens for US$34").json()
    assert rejected["error"] == "SHOP_CURRENCY_UNAVAILABLE" and not woo.carts
    session.next_calls = [("sandbox_shop_quote", query)]
    chat, offers = start(client)
    later = runtime.store.clock() + timedelta(minutes=16)
    monkeypatch.setattr(runtime.store, "clock", lambda: later)
    assert listed(client, chat)[0]["state"] == "expired"
    assert send(client, "expired-selection", "choose 1", chat, offers).status_code == 409
    assert not woo.posts and not woo.orders


def test_unchanged_33_dollar_checkout_swap_stops_and_matches_exact_gateway_records(desk):
    client, _, woo, _ = desk
    # Same amount, account and original basket. A time/amount or account-wide
    # payment count cannot tell whether the subsequent review reached Stripe.
    control_chat, control = start(client)
    paid = send(client, "legitimate", "确认支付", control_chat, control).json()["shopping_order"]
    assert paid["receipt"]["charged_minor"] == 3300
    control_method = woo.payment_methods[control["id"]]
    reply = send(client, "another-basket", "再买两包纸巾和一支蓝笔").json()
    chat, row = reply["conversation_id"], reply["shopping_order"]
    woo.gateway_terms["items"][1].update(product_id=44, sku=RED)
    response = send(client, "guard", "确认支付 HK$33.00", chat, row).json()
    stopped = response["shopping_order"]
    assert stopped["state"] == "items_changed" and stopped["quote"] == row["quote"]
    assert stopped["receipt"] is None and stopped["checkout_change"]["total_minor"] == 3300
    home = render(stopped)
    for message in (response["message"], home["home"]):
        assert "Stationery pen – Blue" in message and "Stationery pen – Red" in message
        assert PEN in message and RED in message and "HK$33.00" in message
        assert TISSUES not in message
    assert "付款前" in response["message"] and "仍为" in response["message"]
    assert "Total still" in home["home"] and "decision" not in home
    assert send(client, "old-pay-again", "确认支付", chat, row).json()["shopping_order"] == stopped
    assert send(client, "pay-substitute", "确认支付", chat, stopped).status_code == 409
    assert listed(client, chat)[0]["state"] == "items_changed"
    ref = row["id"]
    assert woo.posts == [(control["id"], approved_basket()), (ref, approved_basket())]
    assert woo.mapping_reads[-2:] == [(ref, False), (ref, False)] and ref not in woo.orders
    blocked_method = woo.payment_methods[ref]
    assert blocked_method != control_method
    with woo.stripe() as (stripe, account):
        assert account == "acct_fixture"
        for path, amount in [("payment_intents", "amount_received"), ("charges", "amount_captured")]:
            records = stripe.get(path).json()
            assert records["has_more"] is False
            assert [(r["payment_method"], r[amount]) for r in records["data"]] == [(control_method, 3300)]
            assert not [r for r in records["data"] if r["payment_method"] == blocked_method]


@pytest.mark.parametrize("ambiguous", ["mapped", "missing_revision", "invalid_terms"])
def test_conflicting_or_incomplete_gateway_evidence_stays_unverified(desk, monkeypatch, ambiguous):
    client, _, woo, _ = desk
    chat, row = start(client)
    woo.gateway_terms["items"][1].update(product_id=44, sku=RED)
    original = woo.woo_http

    def merchant(request):
        response = original(request)
        if response.status_code == 409:
            if ambiguous == "mapped":
                woo.record_order(row["id"], woo.gateway_terms)
            else:
                conflict = response.json()
                if ambiguous == "missing_revision":
                    conflict["data"]["revision"] = None
                else:
                    conflict["data"]["revision"]["terms"]["total_minor"] = 10
                return httpx.Response(409, json=conflict)
        return response

    monkeypatch.setattr(woo, "woo_http", merchant)
    response = send(client, "conflict", "确认支付", chat, row).json()
    assert response["shopping_order"]["state"] == "unverified"
    assert "checkout_change" not in response["shopping_order"] and "待核对" in response["message"]
    assert len(woo.posts) == 1
