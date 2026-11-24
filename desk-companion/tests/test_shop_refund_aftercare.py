from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from fastapi.testclient import TestClient
import httpx
import pytest

from desk.app import COOKIE, create_app
from desk.commerce_chat import follow_orders
from desk.conversation import Conversations
from desk.shop_checkout.provider import WooSandbox
from desk.store import DomainError
from test_conversation_shop_checkout import send
from test_shop_basket import desk as desk, render, start
from woo_basket_fixture import WooFixture, approved_basket


def paid_order(client):
    chat, quote = start(client)
    paid = send(client, "approve", "确认支付", chat, quote).json()["shopping_order"]
    assert paid["state"] == "completed"
    return chat, paid


def amounts(row):
    receipt = row["receipt"]
    return tuple(receipt[key] for key in ("charged_minor", "refunded_minor", "net_minor", "pending_minor"))


def test_partial_then_pending_then_three_settlements_on_the_original_receipt(desk, tmp_path):
    client, runtime, woo, _ = desk
    chat, paid = paid_order(client)
    ref = paid["id"]
    order = woo.orders[ref]
    order["refunded_minor"] = woo.amount_refunded = 700
    first = woo.refund("re_first", 700)
    woo.refunds = [first, first.copy()]
    # The old paid card still offers a full cancellation. Its preflight must see the partial.
    partial = send(client, "old-card", "取消这笔购物订单并全额退款", chat, paid).json()["shopping_order"]
    assert partial["state"] == "partially_refunded" and amounts(partial) == (3300, 700, 2600, 0)
    assert not partial["receipt"]["can_cancel"] and not partial["receipt"]["buyer_cancel_requested"]
    view = render(partial)
    assert view["home"] == "#67 · Partially refunded"
    summary, details = view["markup"].split("</summary>")
    assert "Settled refund" not in summary and "Cancel and refund" not in details
    assert "Settled refund HK$7.00" in details and "Net charge HK$26.00" in details
    assert "Pending refund HK$0.00" in details

    # Woo and the Charge can already include the pending Refund in their counters.
    second = woo.refund("re_second", 800, "pending")
    woo.refunds = [second, first]
    woo.page_size = 1
    order["refunded_minor"] = woo.amount_refunded = 1500
    control = view["decision"]
    reply = client.post(
        "/api/assistant/messages",
        headers={"X-Desk-Request": "1", "X-Operation-Id": "receipt-control"},
        json={
            "conversation_id": chat, "message": control["message"], "selected_commerce_card": True,
            "shopping_review": {k: v for k, v in control["review"].items() if k != "kind"},
        },
    )
    pending = reply.json()["shopping_order"]
    assert pending["state"] == "refund_pending" and amounts(pending) == (3300, 700, 2600, 800)

    now = runtime.store.clock() + timedelta(minutes=10)
    app = create_app(tmp_path, clock=lambda: now, scheduler=False)
    restarted = app.state.runtime
    restarted.shop_orders.provider = woo
    reopened = TestClient(app)
    reopened.cookies.set(COOKIE, client.cookies[COOKIE])
    owner = {"kind": "owner", "session": client.cookies[COOKIE]}

    # One scheduled check and two simultaneous owner reads of the same persisted review.
    follow_orders(restarted)
    with ThreadPoolExecutor(2) as readers:
        snapshots = list(readers.map(lambda _: restarted.shop_orders.reopen(ref, owner, chat), range(2)))
    assert all(row["receipt"] == pending["receipt"] for row in snapshots)

    second["status"] = "succeeded"
    woo.refunds.insert(0, woo.refund("re_third", 1800))
    woo.amount_refunded = 3300
    order.update(status="refunded", paid=False, refunded_minor=3300)
    now += timedelta(seconds=10)
    follow_orders(restarted)
    listing = reopened.get("/api/assistant/commerce-reviews", params={"conversation_id": chat})
    full = listing.json()["rows"][0]
    assert full["state"] == "refunded" and amounts(full) == (3300, 3300, 0, 0)
    again = send(reopened, "repeat-cancel", "取消这笔购物订单并全额退款", chat, paid).json()
    assert again["shopping_order"]["receipt"] == full["receipt"]
    assert len(woo.orders) == len(woo.posts) == woo.stripe_reads.count("/payment_methods") == 1
    assert not woo.cancels


def test_pending_before_woo_or_charge_counter_and_unsuccessful_refund(desk):
    client, _, woo, _ = desk
    chat, paid = paid_order(client)
    attempt = woo.refund("re_pending", 900, "pending")
    woo.refunds = [attempt, woo.refund("re_prior", 900, "canceled")]
    result = send(client, "pending", "取消这笔购物订单并全额退款", chat, paid).json()["shopping_order"]
    assert result["state"] == "refund_pending" and amounts(result) == (3300, 0, 3300, 900)
    assert render(result)["home"] == "#67 · Checking refund"
    for status, pending in (("requires_action", 900), ("failed", 0), ("canceled", 0)):
        attempt["status"] = status
        row = send(client, status, "查回这笔购物订单的退款结果", chat).json()["shopping_order"]
        assert row["state"] == "refund_review" and amounts(row) == (3300, 0, 3300, pending)
    assert not woo.cancels and len(woo.posts) == 1


def test_owner_cancellation_follows_a_late_stripe_refund_without_resubmitting(desk, monkeypatch):
    client, runtime, woo, _ = desk
    chat, paid = paid_order(client)
    send_to_woo = woo.woo_http

    def delay_refund_list(request):
        response = send_to_woo(request)
        if request.url.path.endswith("/cancel"):
            woo.refunds.clear()  # Woo and the Charge updated before Refund list visibility.
        return response

    monkeypatch.setattr(woo, "woo_http", delay_refund_list)
    reply = send(client, "cancel-once", "取消这笔购物订单并全额退款", chat, paid).json()
    checking = reply["shopping_order"]
    assert checking["state"] == "refund_pending" and amounts(checking) == (3300, None, None, 0)
    details = render(checking)["markup"]
    assert "Settled refund Unverified" in details and "Net charge Unverified" in details
    woo.refunds = [woo.refund("re_original", 3300)]
    later = runtime.store.clock() + timedelta(seconds=10)
    monkeypatch.setattr(runtime.store, "clock", lambda: later)
    follow_orders(runtime)
    row = client.get("/api/assistant/commerce-reviews", params={"conversation_id": chat}).json()["rows"][0]
    assert row["state"] == "refunded" and amounts(row) == (3300, 3300, 0, 0)
    assert woo.cancels == [paid["id"]] and len(woo.posts) == 1


def test_legacy_full_receipt_survives_an_incompatible_first_reopen(desk):
    client, runtime, woo, _ = desk
    chat, paid = paid_order(client)
    owner = Conversations.owner({"kind": "owner", "session": client.cookies[COOKIE]})
    old = runtime.shop_orders._get(paid["id"], owner, chat)
    old.pop("payment_fingerprint")
    old["state"] = "refunded"
    old["receipt"] = {
        "order": 67, "order_status": "refunded", "charged_minor": 3300, "test_mode": True,
        "refund_status": "succeeded", "refunded_minor": 3300, "net_minor": 0, "can_cancel": False,
    }
    runtime.shop_orders._save(old)
    order = woo.orders[paid["id"]]
    order["transaction"] = woo.charge_id = "ch_substitute"
    read = "查回这笔购物订单的退款结果"
    conflict = send(client, "legacy-conflict", read, chat).json()["shopping_order"]
    assert conflict["state"] == "refund_review"
    assert conflict["receipt"] == {**old["receipt"], "last_verified": True}

    order["transaction"] = woo.charge_id = "ch_fixture"
    order.update(status="refunded", refunded_minor=3300)
    woo.amount_refunded = 3300
    woo.refunds = [woo.refund("re_a", 1200), woo.refund("re_b", 2100)]
    recovered = send(client, "legacy-corrected", read, chat).json()["shopping_order"]
    assert recovered["state"] == "refunded" and amounts(recovered) == (3300, 3300, 0, 0)
    assert not recovered["receipt"].get("last_verified") and not woo.cancels


def test_inconsistent_woo_status_reports_same_charge_settlements(desk):
    client, _, woo, _ = desk
    chat, paid = paid_order(client)
    order = woo.orders[paid["id"]]
    order.update(status="refunded", paid=False, refunded_minor=3300)
    woo.refunds = [woo.refund("re_partial", 1100)]
    woo.amount_refunded = 1100
    read = "查回这笔购物订单的退款结果"
    partial = send(client, "woo-ahead", read, chat).json()["shopping_order"]
    assert partial["state"] == "refund_review" and amounts(partial) == (3300, 1100, 2200, 0)
    order.update(status="processing", paid=True)
    woo.refunds.append(woo.refund("re_rest", 2200))
    woo.amount_refunded = 3300
    full = send(client, "woo-behind", read, chat).json()["shopping_order"]
    assert full["state"] == "refund_review" and amounts(full) == (3300, 3300, 0, 0)
    assert not full["receipt"]["can_cancel"] and not woo.cancels


@pytest.mark.parametrize("mismatch", ["currency", "refund_charge", "new_charge", "new_account"])
def test_mismatch_retains_verified_partial_and_can_reopen_after_correction(desk, mismatch):
    client, _, woo, _ = desk
    chat, paid = paid_order(client)
    order = woo.orders[paid["id"]]
    order["refunded_minor"] = woo.amount_refunded = 800
    refund = woo.refund("re_same", 800)
    woo.refunds = [refund]
    read = "查回这笔购物订单的退款结果"
    prior = send(client, "first-read", read, chat).json()["shopping_order"]
    if mismatch == "new_account":
        woo.account = "acct_another"
    elif mismatch == "new_charge":
        order["transaction"] = woo.charge_id = refund["charge"] = "ch_other"
    elif mismatch == "refund_charge":
        refund["charge"] = "ch_foreign"
    else:
        refund["currency"] = "usd"
    bad = send(client, "mismatched", read, chat).json()["shopping_order"]
    assert bad["state"] == ("unverified" if mismatch.startswith("new_") else "refund_review")
    assert bad["receipt"]["last_verified"] and not bad["receipt"]["can_cancel"]
    assert amounts(bad) == amounts(prior) == (3300, 800, 2500, 0)
    assert "payment_fingerprint" not in bad["receipt"]
    woo.account = "acct_fixture"
    order["transaction"] = woo.charge_id = refund["charge"] = "ch_fixture"
    refund["currency"] = "hkd"
    good = send(client, "corrected", read, chat).json()["shopping_order"]
    assert good["state"] == prior["state"] and good["receipt"] == prior["receipt"]
    assert not woo.cancels and len(woo.posts) == 1


@pytest.mark.parametrize("invalid", ["conflicting_id", "over_total", "wrong_intent", "live", "stuck_page"])
def test_unusable_refund_list_preserves_capture_without_inventing_amounts(invalid):
    woo = WooFixture()
    terms = approved_basket()
    woo.record_order("original", terms)
    refund = woo.refund("re_test", 1700)
    woo.refunds = [refund]
    if invalid == "conflicting_id":
        woo.refunds.append({**refund, "amount": 600})
    elif invalid == "over_total":
        woo.refunds.append({**refund, "id": "re_other", "status": "pending"})
    elif invalid == "wrong_intent":
        refund["payment_intent"] = "pi_other"
    elif invalid == "live":
        refund["livemode"] = True
    else:
        woo.page_size = 1
        woo.refunds = [refund] * 3
    receipt = woo.receipt("original", {"terms": terms})
    assert receipt["refund_status"] == "needs_review" and not receipt["can_cancel"]
    assert amounts({"receipt": receipt}) == (3300, None, None, None)


def test_refunds_are_read_only_from_the_configured_stripe_account(monkeypatch):
    provider = WooSandbox(None)
    monkeypatch.setattr(provider, "config", lambda: (
        {"stripe_account": "acct_original"}, {"test_secret_key": "fixture-only"},
    ))
    reads = []

    def respond(request):
        reads.append((request.method, request.url.path))
        return httpx.Response(200, json={"id": "acct_other"})

    client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    with pytest.raises(DomainError, match="SHOP_TEST_CONFIG"), provider.stripe():
        pytest.fail("receipt read was allowed on the other account")
    assert reads == [("GET", "/v1/account")]
