"""Connect a recovered Kiwi source through the actual wallet/booking adapter on synthetic wires."""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from session_protocol_fixture import install_session_protocol
from test_live_flight_supplier import authorize, setup as setup
from test_real_flight_checkout import BUY, HEAD, KiwiSession, action, ask, payment, research


def test_kiwi_receipt_to_real_adapter_with_missing_baggage_then_renewed_fare(setup):
    c, runtime, lane, provider, _ = setup
    owner = TestClient(c.app, base_url="https://testserver", headers=HEAD)
    owner.cookies.update(c.cookies)

    class OriginalLayout(KiwiSession):
        async def run(self, *args, **kwargs):
            result = await super().run(*args, **kwargs)
            report = json.loads(result["report"])
            del report["supplier"]["outbound"], report["supplier"]["inbound"]
            result["report"] = json.dumps(report)
            return result

    runtime.jobs.managed_browser.enabled = True
    runtime.jobs.managed_browser.client_factory = OriginalLayout
    d = SimpleNamespace(r=runtime, c=owner, session=install_session_protocol(runtime))
    chat, _, _ = research(d)
    row = ask(owner, "live-purchase", BUY, chat)["live_flight_checkout"]
    assert not row["connected"] and row["source"]["listed_minor"] == 338959
    assert not lane.requests
    authorize(setup)
    first = action(d, row, chat, "search")
    assert (
        lane.take_search["origin"],
        lane.take_search["destination"],
        lane.take_search["date_from"],
        lane.take_search["return_date"],
    ) == ("HKG", "NRT", "2026-11-24", "2026-12-01")
    assert first["choices"][0]["total_minor"] is None and not first["choices"][0]["payable"]
    missing = action(d, first, chat, "select", 1)
    assert missing["state"] == "seller_only" and ("POST", "/api/agent-book") not in lane.requests
    lane.offer["conditions"] = {
        "baggage": "1 checked bag of 20 kg per passenger included on all flights",
        "refundable": "Non-refundable",
    }
    lane.offer["conditions_source"] = "airline"
    fresh = action(d, missing, chat, "search")
    selected = action(d, fresh, chat, "select", 1)
    assert (
        selected["choices"][0]["total_minor"] == 338959
        and selected["choices"][0]["checked_bag_kg"] == 20
    )
    lane.offer["price"] = "3489.59"
    lane.booking["held"]["amount"] = 3489.59
    lane.status["charged_amount"] = 3489.59
    body = payment(selected, chat)
    url = f"/api/assistant/flight-checkouts/{selected['id']}/confirm"
    changed = owner.post(url, json=body).json()
    assert changed["state"] == "review" and changed["reason"] == "terms_changed"
    assert ("POST", "/api/agent-book") not in lane.requests
    approved = payment(changed, chat)
    final = owner.post(url, json=approved)
    final.raise_for_status()
    completed = final.json()
    assert completed["state"] == "completed" and completed["receipt"]["pnr"] == "QA8G67"
    assert (
        completed["receipt"]["charged_minor"] == 348959
        and completed["receipt"]["currency"] == "HKD"
    )
    assert owner.post(url, json=approved).json() == completed
    assert (
        lane.requests.count(("POST", "/api/agent-book")) == 1
        and lane.requests.count(("POST", "/api/agent-book/status")) == 1
    )
    assert "private.acceptance.token" not in json.dumps(completed)
