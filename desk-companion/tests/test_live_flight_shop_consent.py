"""Ordinary composer assent with a real flight review and a separate sandbox cart."""

import pytest

from desk.app import COOKIE
from desk.conversation import memory_context
from test_conversation_shop_checkout import Shop, quote
from test_real_flight_checkout import BUY, action, ask, desk as desk, research


@pytest.mark.parametrize(
    "selection,expected",
    [
        ("plain", 0),
        ("inferred", 0),
        ("explicit", 1),
        ("other_chat", 1),
    ],
)
def test_generic_consent_keeps_the_original_card_scope(desk, selection, expected):
    d = desk
    trip_chat, _, _ = research(d)
    d.account["connected"] = True
    initial = ask(d.c, "original", BUY, trip_chat)["live_flight_checkout"]
    candidates = action(d, initial, trip_chat, "search")
    purchase = action(d, candidates, trip_chat, "select", 1)
    assert purchase["state"] == "review"
    principal = {"kind": "owner", "id": "owner", "session": d.c.cookies[COOKIE]}
    chats = d.r.voice.conversations
    chat = (
        chats.open(principal, memory_context(d.r, True)[0])
        if selection == "other_chat"
        else chats.entries[trip_chat]
    )
    service = d.r.shop_orders
    service.enabled, service.provider = True, Shop()
    cart = service.attach(quote(), "cart", principal, chat)
    body = {"message": "yes", "conversation_id": chat.id}
    if selection != "plain":
        body["shopping_review"] = {
            "id": cart["id"],
            "version": cart["version"],
            "amount_minor": cart["review_minor"],
        }
    if selection == "explicit":
        body["selected_commerce_card"] = True

    headers = {"X-Operation-Id": "same-question"}
    first = d.c.post("/api/assistant/messages", json=body, headers=headers)
    first.raise_for_status()
    repeat = d.c.post("/api/assistant/messages", json=body, headers=headers)
    repeat.raise_for_status()
    assert (
        first.json()["kind"]
        == repeat.json()["kind"]
        == ("shopping_order" if expected else "clarify")
    )
    assert service.provider.submissions == expected and not d.source.submitted
    assert service.read(cart["id"], chat.owner, chat.id)["state"] == (
        "completed" if expected else "quoted"
    )
    view = d.c.get(
        f"/api/assistant/flight-checkouts/{purchase['id']}", params={"conversation_id": trip_chat}
    )
    assert view.json()["state"] == "review"
