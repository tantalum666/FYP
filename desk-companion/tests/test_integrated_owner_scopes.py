"""The private live checkout, sandbox shop, and owner overview share one real composer."""

from fastapi.testclient import TestClient

from desk.app import COOKIE
from test_conversation_shop_checkout import Shop, quote
from test_flight_shortlist import start as start
from test_quiet_catch_up import review
from test_real_flight_checkout import BUY, HEAD, action, ask, desk as desk, payment, research


def test_live_checkout_and_shop_need_an_explicit_original_card(desk):
    d = desk
    chat, _, _ = research(d)
    d.account["connected"] = True
    source = ask(d.c, "open-original", BUY, chat)["live_flight_checkout"]
    offers = action(d, source, chat, "search")
    live = action(d, offers, chat, "select", 1)
    assert live["state"] == "review"
    who = {"kind": "owner", "id": "owner", "session": d.c.cookies[COOKIE]}
    shop = d.r.shop_orders
    shop.enabled, shop.provider = True, Shop()
    live_amount = live["choices"][live["selected"] - 1]["total_minor"]
    shop.provider.rate = live_amount - 3400
    row = shop.attach(
        quote(shop.provider.rate), "synthetic-cart", who, d.r.voice.conversations.entries[chat]
    )
    card = review(row)

    def say(words, key, **fields):
        response = d.c.post(
            "/api/assistant/messages",
            headers={"X-Operation-Id": key},
            json={"message": words, "conversation_id": chat, **fields},
        )
        response.raise_for_status()
        return response.json()

    generic = say("yes", "generic")
    assert generic["kind"] == "clarify" and not generic["acted"]
    inferred = say("confirm", "inferred-card", shopping_review=card)
    assert inferred["kind"] == "clarify" and not inferred["acted"]
    assert say("confirm", "inferred-card", shopping_review=card) == inferred
    shared_amount = say(f"确认支付 HK${live_amount / 100:.2f}", "same-amount", shopping_review=card)
    assert shared_amount["kind"] == "clarify" and not shared_amount["acted"]
    snapshot = say("What needs my approval?", "mixed-decisions")
    assert snapshot["total"] == 2 and not snapshot["acted"]
    assert "BR852" in str(snapshot["items"]) and "测试文具包" in str(snapshot["items"])
    assert not shop.provider.submissions and not d.source.submitted
    assert len(d.source.searches) == 1

    chosen = say("decline", "decline-only-cart", shopping_review=card, selected_commerce_card=True)
    assert chosen["shopping_order"]["state"] == "cancelled"
    assert (
        say("decline", "decline-only-cart", shopping_review=card, selected_commerce_card=True)
        == chosen
    )
    assert say("What needs my approval?", "remaining")["total"] == 1
    own_url = f"/api/assistant/flight-checkouts/{live['id']}"
    assert d.c.get(own_url, params={"conversation_id": chat}).json()["state"] == "review"
    with TestClient(d.app, base_url="https://testserver", headers=HEAD) as other:
        other.post(
            "/api/session", json={"username": "owner", "password": "fixture"}
        ).raise_for_status()
        assert other.get(own_url, params={"conversation_id": chat}).status_code == 404
        wrong = other.post(
            "/api/assistant/messages",
            json={"message": "What needs my approval?", "conversation_id": chat},
            headers={"X-Operation-Id": "mixed-decisions"},
        )
        assert wrong.status_code == 404 and "BR852" not in wrong.text
    display = d.r.access.enrol_display("Synthetic shared screen", "review-display")
    with TestClient(
        d.app,
        base_url="https://testserver",
        headers={**HEAD, "Authorization": "Bearer " + display["token"]},
    ) as paired:
        assert paired.get(own_url, params={"conversation_id": chat}).status_code == 403
    d.c.delete("/api/voice/conversations/" + chat).raise_for_status()
    assert d.c.get(own_url, params={"conversation_id": chat}).status_code == 404
    assert not d.source.submitted and not shop.provider.submissions


def test_saved_sandbox_list_does_not_project_the_separate_live_fare(start, monkeypatch):
    from desk import browser_research

    d = start()
    chat = d.initial()["conversation_id"]
    monkeypatch.setattr(
        browser_research,
        "current_chat_quote",
        lambda *_: {
            "record_verified": True,
            "proposal_id": "other-fare-receipt",
            "quote": {"supplier": "Other real itinerary"},
        },
    )
    d.session.next_calls = [("revisit_flight_shortlist", {"option_number": 2})]
    start_count = len(d.session.creations)
    result = d.ask(
        "originals-only",
        "The second departure suits me. Could you check it against my calendar?",
        chat,
    )
    assert result["flight_booking"]["segments"][0]["flight"] == "FA102"
    assert len(d.session.creations) > start_count
    requested = d.session.creations[-1]
    assert "flight_purchase_review" not in {tool["name"] for tool in requested["agent"]["tools"]}
    assert "other-fare-receipt" not in str(requested["input"])


def test_approval_snapshot_excludes_unavailable_offers_and_completed_receipts(desk, monkeypatch):
    d = desk
    chat, _, _ = research(d)

    def lookup(key):
        return ask(d.c, key, "What needs my approval?", chat)

    public = ask(d.c, "real-source", BUY, chat)["live_flight_checkout"]
    assert public["state"] == "source" and lookup("source-only")["total"] == 0
    d.account["connected"] = True
    d.source.offer["checked_bag_kg"] = None
    offers = action(d, public, chat, "search")
    unpayable = action(d, offers, chat, "select", 1)
    assert unpayable["state"] == "seller_only" and lookup("unverified-bag")["total"] == 0
    d.source.offer["checked_bag_kg"] = 20
    refreshed = action(d, unpayable, chat, "search")
    ready = action(d, refreshed, chat, "select", 1)
    assert ready["state"] == "review" and lookup("selected-terms")["total"] == 1
    calls = (len(d.source.searches), len(d.source.rereads), len(d.source.reads))
    d.account["connected"] = False
    unavailable = lookup("same-overview-key")
    assert (
        not unavailable["complete"]
        and unavailable["total"] is None
        and "BR852" not in unavailable["message"]
    )
    d.account.update(connected=True, version="replacement")
    assert lookup("same-overview-key")["items"] == []
    d.account["version"] = "account-version"
    assert lookup("same-overview-key")["total"] == 1
    assert calls == (len(d.source.searches), len(d.source.rereads), len(d.source.reads))
    assert not d.source.submitted

    with monkeypatch.context() as patch:

        def unavailable_source(*args):
            raise TimeoutError()

        patch.setattr(d.r.live_flight_checkouts, "pending_reviews", unavailable_source)
        partial = lookup("temporarily-unreadable")
        assert not partial["complete"] and partial["total"] is None and not partial["acted"]
    url = f"/api/assistant/flight-checkouts/{ready['id']}/confirm"
    body = payment(ready, chat)
    held = d.c.post(url, json=body).json()
    done = action(d, held, chat, "status")
    assert done["state"] == "completed" and done["receipt"]["charged_minor"] == body["amount_minor"]
    before = (
        len(d.source.searches),
        len(d.source.rereads),
        len(d.source.reads),
        len(d.source.submitted),
    )
    terminal = lookup("selected-terms")
    assert terminal["complete"] and terminal["total"] == 0 and terminal["items"] == []
    assert done["receipt"]["pnr"] not in terminal["message"]
    assert before == (
        len(d.source.searches),
        len(d.source.rereads),
        len(d.source.reads),
        len(d.source.submitted),
    )
