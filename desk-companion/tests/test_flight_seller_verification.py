"""Public seller inspection is scoped evidence. Only a fresh bookable supplier offer can be approved."""

from copy import deepcopy
import json
import pytest
from test_real_flight_checkout import OUT, IN
from test_real_flight_checkout import BACK, BUY, DAY, Supplier, action, ask, desk as desk, research

URL = "https://letsfg.co/en/book/live-offer"


def unverified(d):
    d.account["connected"] = True
    d.source.offer.update(checked_bag_kg=None, ready=False, total_minor=None, booking_url=URL)
    chat, _, _ = research(d)
    source = ask(d.c, "live-start", BUY, chat)["live_flight_checkout"]
    options = action(d, source, chat, "search")
    blocked = action(d, options, chat, "select", 1)
    assert blocked["state"] == "seller_only" and not blocked["choices"][0]["payable"]
    return chat, blocked


@pytest.mark.parametrize("proof", ["generic_airline_policy", "one_direction", "same_offer"])
def test_owner_checked_seller_page_is_bound_to_original_then_repriced_without_purchase(desk, proof):
    d = desk
    chat, blocked = unverified(d)
    url = f"/api/assistant/flight-checkouts/{blocked['id']}/actions"
    body = {
        "conversation_id": chat,
        "version": blocked["version"],
        "action": "verify_seller",
        "number": 1,
    }
    assert d.c.post(url, json=body).status_code == 422
    assert len(d.r.jobs.listing()) == 1
    started = d.c.post(url, json={**body, "share_seller_page": True})
    started.raise_for_status()
    pending = started.json()
    assert pending["state"] == "seller_verification" and not d.source.submitted
    jobs = d.r.jobs.listing(review=True)
    job = next(j for j in jobs if j["state"] == "queued")
    assert job["request"]["start_url"] == URL and job["request"]["allowed_origins"] == [
        "https://letsfg.co"
    ]
    assert job["request"]["quote_request"] == {
        "kind": "flight",
        "origin": "HKG",
        "destination": "NRT",
        "departure": DAY,
        "return_date": BACK,
        "adults": 1,
        "checked_bag_kg": 20,
        "currency": "HKD",
        "budget_minor": None,
    }
    assert all(
        x in job["request"]["goal"]
        for x in ("live-offer", "BR852", "BR196", "BR197", "BR851", "public read-only")
    )

    class PublicPage:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, intent, checkpoint, on_session, **kwargs):
            checkpoint()
            on_session("fixture-inspection")
            page = (
                URL
                if proof != "generic_airline_policy"
                else "https://letsfg.co/en/fares/economy-discount"
            )
            item = {
                "label": "BR852 BR196 BR197 BR851",
                "source_url": page,
                "currency": "HKD",
                "price_minor": 350000,
                "priced_units": 1,
                "basis": "listed",
                "price_evidence": "This public listing HKD 3,500 total",
                "availability": "available",
                "extras_minor": 0,
                "extras_evidence": "All fees and the checked bag are included",
                "extras_source_url": page,
                "conditions": None,
                "origin": "HKG",
                "destination": "NRT",
                "departure": DAY,
                "return_date": BACK,
                "journey": "round_trip",
                "checked_bag_kg_per_adult": 20,
                "seller_offer_reference": "live-offer",
                "ticketed_sectors": [
                    {
                        "direction": side,
                        "origin": a,
                        "destination": b,
                        "flight": n,
                        "operating_carrier": "Verified example airline",
                        "departs": departs,
                    }
                    for side, rows in [("outbound", OUT), ("inbound", IN)]
                    for a, b, n, departs, _ in rows
                    if not (proof == "one_direction" and side == "inbound")
                ],
                "included_checked_bags_for_party": 1,
                "baggage_coverage": "partial"
                if proof == "one_direction"
                else "all_ticketed_segments_for_every_traveller",
                "baggage_evidence": "One 20 kg checked bag on all four segments",
            }
            return {
                "report": json.dumps({"offer": item, "note": "Public seller read"}),
                "activity_count": 1,
                "usage": {"input_tokens": 5, "output_tokens": 2},
                "session_deleted": True,
                "deletion_readback": True,
                "stop_code": None,
                "turn_completed": True,
                "account_access_authorized": False,
                "stream_reconnections": 0,
            }

    d.r.jobs.managed_browser.client_factory = PublicPage
    d.r.jobs.run_one()
    assert d.r.jobs.detail(job["id"])["state"] == "succeeded"
    checked = d.c.get(
        f"/api/assistant/flight-checkouts/{blocked['id']}", params={"conversation_id": chat}
    ).json()
    assert checked["seller_check"]["status"] == (
        "page_verified" if proof == "same_offer" else "unverified"
    )
    assert checked["state"] == "seller_only" and not checked["choices"][0]["payable"]
    assert d.source.rereads[-1] == ("live-search", "live-offer") and not d.source.submitted
    assert checked["checked_sellers"] == ["LetsFG"]
    another = d.c.post(
        url,
        json={
            **body,
            "action": "verify_original",
            "version": checked["version"],
            "share_seller_page": True,
        },
    )
    another.raise_for_status()
    assert another.json()["seller_check"]["seller"] == "Kiwi.com"
    job2 = next(j for j in d.r.jobs.listing(review=True) if j["state"] == "queued")
    assert (
        job2["request"]["start_url"] == "https://www.kiwi.com/u/public-test-only"
        and job2["request"]["quote_request"]["checked_bag_kg"] == 20
    )
    d.r.jobs.run_one()
    checked = d.c.get(
        f"/api/assistant/flight-checkouts/{blocked['id']}", params={"conversation_id": chat}
    ).json()
    assert checked["checked_sellers"] == ["LetsFG", "Kiwi.com"] and not d.source.submitted
    # The supplier finally verifies coverage itself. A conflicting page total still blocks this fare.
    d.source.offer.update(
        checked_bag_kg=20, total_minor=355000 if proof == "same_offer" else 350000, ready=True
    )
    candidate = action(d, checked, chat, "select", 1)
    assert (
        candidate["state"] == ("seller_only" if proof == "same_offer" else "review")
        and not d.source.submitted
    )


def test_named_other_offer_rechecks_the_same_route_and_baggage_without_new_search(desk):
    d = desk
    d.account["connected"] = True
    original = d.source
    sibling = deepcopy(original.offer)
    sibling.update(offer_id="other-exact", total_minor=351000)
    original.offer.update(total_minor=None, checked_bag_kg=None, ready=False, booking_url=URL)

    def search(query, **kwargs):
        result = Supplier.search(original, query, **kwargs)
        result["offers"].append(dict(sibling))
        return result

    def reprice(query, sid, oid, **kwargs):
        if oid == "other-exact":
            original.rereads.append((sid, oid))
            assert query.return_date == BACK and query.checked_bag_kg == 20
            return {"state": "offers", "search_id": sid, "offers": [dict(sibling)]}
        return Supplier.reprice(original, query, sid, oid, **kwargs)

    original.search = search
    original.reprice = reprice
    chat, _, _ = research(d)
    source = ask(d.c, "buy", BUY, chat)["live_flight_checkout"]
    first = action(d, source, chat, "search")
    blocked = action(d, first, chat, "select", 1)
    other = action(d, blocked, chat, "other_offers")
    assert (
        other["alternatives_checked"] == 1
        and other["state"] == "offers"
        and other["choices"][0]["total_minor"] == 351000
    )
    assert len(original.searches) == 1 and not original.submitted
