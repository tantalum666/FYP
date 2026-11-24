import json

import httpx
import pytest
from pydantic import ValidationError

from desk.browser_research import BrowserResearchDraft, current_chat_quote, status
from desk.conversation import Conversation
from desk.commerce_quotes import read_quote
from desk.context_budget import fit_context
from desk.store import DomainError
from session_protocol_fixture import install_session_protocol
import test_managed_browser as managed_cases

quote_world = managed_cases.world

SITE = "https://books.toscrape.com"
PAGE = SITE + "/public-listing"
AT = "2026-11-19T02:00:00Z"
SHOP = {
    "kind": "shopping",
    "product": "12-pack tissues",
    "quantity": 2,
    "fulfilment": "delivery",
    "currency": "HKD",
    "budget_minor": 6000,
}
FLIGHT = {
    "kind": "flight",
    "origin": "HKG",
    "destination": "HND",
    "departure": "2026-11-25",
    "adults": 1,
    "checked_bag_kg": 20,
    "currency": "HKD",
    "budget_minor": 150000,
}
PRICE = {
    "label": "12-pack tissues",
    "source_url": PAGE,
    "currency": "HKD",
    "price_minor": 3400,
    "priced_units": 2,
    "basis": "listed",
    "availability": "available",
    "price_evidence": "2 for $34",
    "extras_minor": None,
    "extras_evidence": None,
    "extras_source_url": None,
    "conditions": None,
}
PACK = {**PRICE, "product_matches": "yes", "fulfilment": "delivery"}
FARE = {
    **PRICE,
    "label": "Hong Kong to Haneda",
    "price_minor": 47000,
    "priced_units": 1,
    "price_evidence": "From HKD 470",
    "basis": "from",
    "origin": "HKG",
    "destination": "HND",
    "departure": "2026-11-25",
    "return_date": None,
    "journey": "one_way",
    "checked_bag_kg_per_adult": None,
}
FREE = {
    "extras_minor": 0,
    "extras_evidence": "All fees included for this selection",
    "extras_source_url": PAGE,
}


def report(offer):
    return json.dumps({"offer": offer, "note": "Check published conditions."})


def card(spec, offer):
    return read_quote(
        {"quote_request": spec, "start_url": PAGE, "allowed_origins": [SITE]}, report(offer), AT
    )


def test_bundle_is_one_lot_and_unknown_delivery_is_not_free():
    quote = card(SHOP, PACK)
    assert (quote["subtotal_minor"], quote["total_minor"], quote["budget_status"]) == (
        3400,
        None,
        "unknown",
    )
    complete = card(SHOP, {**PACK, **FREE, "extras_minor": 1000})
    assert (complete["total_minor"], complete["budget_status"]) == (4400, "within")
    assert card({**SHOP, "quantity": 3}, PACK)["subtotal_minor"] is None
    assert card(SHOP, {**PACK, **FREE, "currency": "SGD"})["budget_status"] == "unknown"
    assert card(SHOP, {**PACK, **FREE, "fulfilment": "pickup"})["total_minor"] is None


def test_fare_cannot_become_a_trip_total_without_matching_terms():
    assert card(FLIGHT, FARE)["subtotal_minor"] is None
    priced = {
        **FARE,
        **FREE,
        "basis": "listed",
        "price_evidence": "HKD 470",
        "checked_bag_kg_per_adult": 20,
    }
    assert card(FLIGHT, priced)["total_minor"] == 47000
    for update in (
        {"destination": "NRT"},
        {"departure": "2026-11-26"},
        {"journey": "round_trip"},
        {"priced_units": 2},
        {"checked_bag_kg_per_adult": 0},
        {"availability": "unknown"},
    ):
        assert card(FLIGHT, {**priced, **update})["total_minor"] is None
    assert card({**FLIGHT, "adults": 2}, priced)["total_minor"] is None
    assert card(FLIGHT, None)["offer"] is None


def test_only_the_approved_quantity_unlocks_a_multi_buy_price():
    bundle = {**PACK, "basis": "quantity_offer", "availability": "unknown"}
    assert card(SHOP, bundle)["subtotal_minor"] == 3400
    assert card(SHOP, bundle)["total_minor"] is None
    assert card({**SHOP, "quantity": 4}, bundle)["subtotal_minor"] is None
    assert card(SHOP, {**bundle, "basis": "conditional"})["subtotal_minor"] is None
    assert card(FLIGHT, {**FARE, "basis": "quantity_offer"})["subtotal_minor"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"source_url": "https://elsewhere.example/item"},
        {"source_url": PAGE + "?token=secret"},
        {"source_url": "http://books.toscrape.com/"},
        {"extras_minor": 0},
        {"price_minor": 34.5},
        {**FREE, "extras_source_url": "https://elsewhere.example/fees"},
    ],
)
def test_invalid_price_or_unapproved_source_fails_closed(changes):
    with pytest.raises(ValueError):
        card(SHOP, {**PACK, **changes})


def test_old_draft_bytes_and_invalid_approval():
    base = {"title": "Compare prices", "goal": "Read the listing", "start_url": PAGE}
    old = BrowserResearchDraft(**base)
    assert (
        "quote_request" not in old.model_dump() and "quote_request" not in old.intent().model_dump()
    )
    for opts in (
        {"engine": "local", "quote_request": SHOP},
        {"quote_request": {**FLIGHT, "return_date": "2026-11-24"}},
        {"quote_request": {**FLIGHT, "departure": "2026-02-30"}},
    ):
        with pytest.raises(ValidationError):
            BrowserResearchDraft(**base, **opts)


def test_unavailable_quote_handoff_preserves_only_a_public_url():
    intent = {
        "quote_request": FLIGHT,
        "allowed_origins": [SITE],
        "start_url": PAGE + "?session=private",
    }
    assert read_quote(intent, report(None), AT)["approved_page"] == SITE
    for url in ("https://127.0.0.1/item", "https://desk.local/item", SITE + "/checkout"):
        with pytest.raises(ValidationError):
            BrowserResearchDraft(
                title="A quote", goal="Read the listing", start_url=url, quote_request=SHOP
            )
    with pytest.raises(ValueError):
        card(SHOP, {**PACK, "source_url": SITE + "/%63heckout/"})


def test_long_sources_preserve_price_basis_and_unknown_fees_in_model_context():
    quote = card(SHOP, {**PACK, "source_url": SITE + "/" + "a" * 1700})
    result = {
        "proposal_id": "f" * 32,
        "record_verified": True,
        "quote": quote,
        "agent_report": "x" * 3999,
    }
    packed = fit_context(
        {"last_tool_result": {"tool": "browser_research_status", "result": result}}
    )
    short = packed["last_tool_result"]["result"]["quote"]
    assert (short["basis"], short["subtotal_minor"], short["total_minor"]) == ("listed", 3400, None)
    assert not short["transaction_confirmed"] and "source_url" not in short


@pytest.mark.parametrize(
    "observation,valid",
    [(PACK, True), ({**PACK, "source_url": "https://elsewhere.example/"}, False)],
)
def test_alice_approval_to_verified_quote_or_safe_failure(quote_world, observation, valid):
    runtime, provider, client, _owner = quote_world
    protocol = install_session_protocol(runtime)
    protocol.next_calls = [
        (
            "browser_research_draft",
            {
                "title": "Tissue quote",
                "goal": "Read the two-pack offer",
                "start_url": PAGE,
                "quote_request": SHOP,
            },
        )
    ]
    headers = {"X-Desk-Request": "1"}
    response = client.post(
        "/api/assistant/messages",
        json={"message": "Compare two retail packs"},
        headers={**headers, "X-Operation-Id": "quote-chat"},
    )
    proposal = response.json()["proposal"]
    assert proposal["data"]["browser"]["quote_request"] == SHOP
    assert runtime.jobs.listing() == [] and not provider.input
    decision = "/api/assistant/proposals/" + proposal["id"] + "/decisions"
    assert (
        client.post(
            decision,
            json={"action": "confirm"},
            headers={**headers, "X-Operation-Id": "missing-screen"},
        ).status_code
        == 422
    )
    approved = client.post(
        decision,
        json={"action": "confirm", "share_screen": True},
        headers={**headers, "X-Operation-Id": "admit-quote"},
    ).json()
    job_id = approved["job"]["id"]
    provider.report = report(observation)
    runtime.text_ai.transport = httpx.MockTransport(provider)
    runtime.jobs.run_one()
    assert provider.deleted
    create = next(
        body
        for method, path, body in provider.calls
        if method == "POST" and path.endswith("/sessions")
    )
    assert create["agent"]["text"]["format"]["schema"]["additionalProperties"] is False
    readback = status(runtime, {"proposal_id": proposal["id"]})
    assert not readback["transaction_confirmed"] and readback["record_verified"] is valid
    if not valid:
        assert readback["job"]["error"] == "COMPUTER_QUOTE_UNVERIFIED"
        assert "quote" not in readback
        return
    assert readback["quote"]["subtotal_minor"] == 3400 and readback["quote"]["total_minor"] is None
    detail = client.get("/api/computer/jobs/" + job_id).json()["job"]
    assert detail["result"]["readback"]["quote"] == readback["quote"]
    chat = runtime.voice.conversations.entries[response.json()["conversation_id"]]
    assert current_chat_quote(runtime, chat)["quote"]["subtotal_minor"] == 3400
    assert current_chat_quote(runtime, Conversation("fresh", chat.owner, chat.revision, 0)) is None
    foreign = Conversation("other", "other-owner", chat.revision, 0, items=chat.items)
    assert current_chat_quote(runtime, foreign) is None
    runtime.text_ai.transport = httpx.MockTransport(protocol)
    protocol.next_calls = []
    again = client.post(
        "/api/assistant/messages",
        json={
            "message": "What was that quote?",
            "conversation_id": chat.id,
        },
        headers={**headers, "X-Operation-Id": "same-chat-quote"},
    )
    assert again.status_code == 200 and again.json()["conversation_id"] == chat.id
    payload = json.loads(protocol.creations[-1]["input"][0]["content"][0]["text"])
    assert payload["current_chat_quote"]["proposal_id"] == proposal["id"]
    assert payload["current_chat_quote"]["quote"]["total_minor"] is None
    assert len(runtime.jobs.listing()) == 1
    receipt = runtime.jobs.managed_browser.root / job_id / "receipt.json"
    altered = json.loads(receipt.read_text())
    altered["quote"]["total_minor"] = 123
    receipt.write_text(json.dumps(altered))
    with pytest.raises(DomainError) as exc:
        status(runtime, {"proposal_id": proposal["id"]})
    assert exc.value.code == "COMPUTER_READBACK_CHANGED"
    assert "quote" not in current_chat_quote(runtime, chat)
