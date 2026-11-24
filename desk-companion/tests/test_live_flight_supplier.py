"""The same production resolver, OAuth lifecycle, approval fence and receipt reader use HTTP fixtures."""

import base64
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.calendar import iso
from desk.flight_booking.live_fares import official_url
from desk.flight_booking.live_oauth import ISSUER, METADATA, REGISTER, RESOURCE
from desk.flight_booking.live_provider import LiveApprovedFare, LiveFlightProvider, LiveFlightQuery
from desk.store import DomainError, encode

NOW = datetime(2026, 11, 23, 3, tzinfo=timezone.utc)
REQUEST = dict(
    origin="HKG",
    destination="NRT",
    departure="2026-11-24",
    return_date="2026-12-01",
    outbound_flights=["BR852", "BR196"],
    outbound_departs_at="11:20",
    outbound_arrives_at="19:20",
)
PAX = dict(
    given_name="Sample",
    family_name="Fixture",
    born_on="1990-06-01",
    gender="f",
    nationality="HK",
    phone_number="+85220000000",
    phone_country="HK",
    address_line1="Example Lane",
    address_city="Hong Kong",
    address_postal="00000",
    address_country="HK",
)
MAIL = "synthetic@example.test"


def segment(frm, to, d, a, number):
    return dict(
        origin=frm,
        destination=to,
        departure_time=d,
        arrival_time=a,
        airline_code="BR",
        flight_number=number,
    )


class AgentLane:
    def __init__(self):
        self.requests = []
        self.starts = 0
        self.status = {
            "state": "completed",
            "pnr": "QA8G67",
            "charged_amount": 3389.59,
            "currency": "HKD",
        }
        self.booking = {
            "state": "booking_in_progress",
            "booking_ref": "private.acceptance.token",
            "held": {"amount": 3389.59, "currency": "HKD"},
            "charged": 0,
        }
        self.offer = {
            "id": "wo_original",
            "currency": "HKD",
            "price": "3389.59",
            "stops": 1,
            "segments": [
                segment("HKG", "TPE", "2026-11-24T11:20:00", "2026-11-24T13:10:00", "BR852"),
                segment("TPE", "NRT", "2026-11-24T15:10:00", "2026-11-24T19:20:00", "BR196"),
            ],
            "inbound": {
                **segment("NRT", "HKG", "2026-12-01T14:00:00", "2026-12-01T18:45:00", "BR123"),
                "stops": 0,
            },
            "bags_price": {"1_bag": 37.14},
            "bags_price_source": "estimate",
            "booking_url": "https://letsfg.co/en/book/wo_original",
        }
        self.take_search = {}
        self.extra = []
        self.token_posts = []
        self.result_flags = {}
        self.drop_ack = False
        self.refresh_failure = False

    def route(self, request):
        self.requests.append((request.method, request.url.path))
        url = str(request.url)
        path = request.url.path
        if url == METADATA:
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": "https://letsfg.co/connect",
                    "token_endpoint": ISSUER + "/oauth/token",
                    "registration_endpoint": REGISTER,
                    "scopes_supported": ["flights:search", "flights:book"],
                    "code_challenge_methods_supported": ["S256"],
                    "token_endpoint_auth_methods_supported": ["none"],
                },
            )
        if url == RESOURCE:
            return httpx.Response(
                200, json={"resource": "https://letsfg.co/mcp", "authorization_servers": [ISSUER]}
            )
        if url == REGISTER:
            data = json.loads(request.content)
            assert data["token_endpoint_auth_method"] == "none" and all(
                "callback" in u for u in data["redirect_uris"]
            )
            return httpx.Response(201, json={"client_id": "lfg_client_public_fixture"})
        if path.endswith("/oauth/token"):
            body = parse_qs(request.content.decode())
            self.token_posts.append(body)
            assert "client_secret" not in body
            if body["grant_type"] == ["refresh_token"] and self.refresh_failure:
                raise httpx.ReadTimeout("simulation of dropped rotation result")
            return httpx.Response(
                200,
                json={
                    "access_token": "private.test-access",
                    "refresh_token": "rotating-" + str(len(self.token_posts)),
                    "expires_in": 3600,
                    "scope": "flights:search flights:book",
                    "token_type": "Bearer",
                },
            )
        assert (
            request.url.host == "letsfg.co"
            and request.headers["authorization"] == "Bearer private.test-access"
        )
        if path == "/api/search":
            self.starts += 1
            self.take_search = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "search_id": f"ws_search{self.starts}",
                    "status": "searching",
                    "parsed": {
                        "adults": self.take_search["adults"],
                        "children": self.take_search["children"],
                        "infants": self.take_search["infants"],
                    },
                },
            )
        if path.startswith("/api/results/"):
            return httpx.Response(
                200, json={"status": "completed", "offers": [*self.extra, self.offer], **self.result_flags}
            )
        if path == "/api/agent-book":
            self.book_body = json.loads(request.content)
            if self.drop_ack:
                raise httpx.ReadTimeout("synthetic lost post acknowledgement")
            return httpx.Response(402 if "error" in self.booking else 202, json=self.booking)
        if path == "/api/agent-book/status":
            assert json.loads(request.content) == {"booking_ref": "private.acceptance.token"}
            return httpx.Response(200, json=self.status)
        raise AssertionError(path)


@pytest.fixture
def setup(tmp_path):
    a = create_app(tmp_path, password="test", scheduler=False, clock=lambda: NOW)
    client = TestClient(a)
    h = {"X-Desk-Request": "1"}
    runtime = client.post("/api/session", json={"username": "owner", "password": "test"}, headers=h)
    runtime.raise_for_status()
    runtime = a.state.runtime
    lane = AgentLane()
    runtime.letsfg_auth.transport = httpx.MockTransport(lane.route)
    provider = runtime.live_flight_provider
    provider.transport = httpx.MockTransport(lane.route)
    principal = {
        "kind": "owner",
        "id": "owner",
        "session": client.cookies["desk_companion_session"],
    }
    return client, runtime, lane, provider, principal


def authorize(setup):
    client, runtime, lane, supplier, principal = setup
    h = {"X-Desk-Request": "1", "Origin": "http://127.0.0.1:5190"}
    flow = client.post("/api/apps/letsfg/connect", headers=h).json()
    uri = urlsplit(flow["url"])
    q = parse_qs(uri.query)
    assert (
        uri.netloc == "letsfg.co"
        and uri.path == "/connect"
        and q["scope"] == ["flights:search flights:book"]
        and q["code_challenge_method"] == ["S256"]
    )
    assert not runtime.letsfg_auth.account()["connected"]
    result = client.get(
        "/api/apps/letsfg/callback", params={"state": q["state"][0], "code": "fixture-code"}
    )
    assert result.status_code == 200
    form = lane.token_posts[-1]
    calc = (
        base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"][0].encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert q["code_challenge"] == [calc] and form["redirect_uri"] == q["redirect_uri"]
    assert (
        client.get(
            "/api/apps/letsfg/callback", params={"state": q["state"][0], "code": "fixture-code"}
        ).status_code
        == 403
    )
    assert runtime.letsfg_auth.account()["connected"]
    return flow


def test_settled_public_agent_quote_requires_named_client_and_same_offer_page(setup):
    from desk.flight_booking.seller_verification import target

    _, _, lane, provider, principal = setup
    authorize(setup)
    lane.offer.pop("booking_url")
    lane.offer["ancillaries"] = {"checked_bag": {"included": True}, "price_source": "estimate"}
    flags = lane.result_flags
    flags["gf_enrich_pending"] = True
    query = LiveFlightQuery(**REQUEST, checked_bag_kg=20)

    def published_service(request):
        if not request.headers["User-Agent"].startswith("FYP-Desk-Companion/"):
            return httpx.Response(403, text="Forbidden")
        return lane.route(request)

    provider.transport = httpx.MockTransport(published_service)
    pending = provider.search(query, principal=principal)
    sid = pending["search_id"]
    assert pending["state"] == "searching" and not pending["offers"]
    flags.update(gf_enrich_pending=False, split_ticket_pending=True)
    assert provider.search(query, principal=principal, search_id=sid)["state"] == "searching"
    flags.update(split_ticket_pending=False)
    active = provider.search(query, principal=principal, search_id=sid)
    [offer] = active["offers"]
    assert offer["fare_minor"] == 338959 and offer["total_minor"] is None and not offer["ready"]
    receipt = {"source": {"url": "https://www.kiwi.com/u/test"}, "offers": [offer]}
    seller, url, _ = target(receipt, 1)
    params = parse_qs(urlsplit(url).query)
    assert seller == "LetsFG" and params["sid"] == [sid] and params["offer"] == [offer["offer_id"]]
    offer["booking_url"] = url.replace(sid, "ws_somewhere_else")
    assert target(receipt, 1)[:2] == ("Kiwi.com", receipt["source"]["url"])
    flags["parsed"] = {"date": "2026-11-25"}
    with pytest.raises(DomainError, match="LETSFG_OFFER_UNVERIFIED"):
        provider.search(query, principal=principal, search_id=sid)
    assert lane.starts == 1 and not hasattr(lane, "book_body")


def test_owner_pkce_rotating_refresh_and_reconnect_no_replay(setup):
    client, runtime, lane, supplier, principal = setup
    assert (
        TestClient(client.app)
        .post("/api/apps/letsfg/connect", headers={"X-Desk-Request": "1"})
        .status_code
        == 403
    )
    authorize(setup)

    def expire():
        a = runtime.letsfg_auth
        with a.store.connection(write=True) as db:
            sealed = db.execute("SELECT encrypted_tokens FROM letsfg_connection").fetchone()[0]
            token = json.loads(a.vault.decrypt(sealed))
            assert "rotating-" not in sealed
            token["expires_at"] = iso(NOW - timedelta(seconds=1))
            db.execute(
                "UPDATE letsfg_connection SET encrypted_tokens=?", (a.vault.encrypt(encode(token)),)
            )

    expire()
    assert runtime.letsfg_auth.grant(principal)[0] == "private.test-access"
    assert lane.token_posts[-1]["refresh_token"] == ["rotating-1"]
    expire()
    lane.refresh_failure = True
    with pytest.raises(DomainError, match="LETSFG_CONNECT_REQUIRED"):
        runtime.letsfg_auth.grant(principal)
    with pytest.raises(DomainError, match="LETSFG_REFRESH_PENDING"):
        runtime.letsfg_auth.grant(principal)
    assert len(lane.token_posts) == 3 and lane.token_posts[-1]["refresh_token"] == ["rotating-2"]


def test_roundtrip_original_legs_bag_gap_unknown_return_and_scope(setup):
    client, runtime, lane, supplier, principal = setup
    query = LiveFlightQuery(**REQUEST, checked_bags=1, checked_bag_kg=20)
    with pytest.raises(DomainError, match="LETSFG_CONNECT_REQUIRED"):
        supplier.search(query, principal=principal)
    authorize(setup)
    leg_change = deepcopy(lane.offer)
    leg_change["id"] = "other"
    leg_change["segments"][1]["flight_number"] = "BR999"
    missing = deepcopy(lane.offer)
    missing["id"] = "one_way"
    missing.pop("inbound")
    time_change = deepcopy(lane.offer)
    time_change["id"] = "other_time"
    time_change["segments"][0]["departure_time"] = "2026-11-24T11:21:00"
    lane.extra = [leg_change, missing, time_change]
    result = supplier.search(query, principal=principal)
    assert lane.take_search == dict(
        origin="HKG",
        destination="NRT",
        return_date="2026-12-01",
        adults=1,
        children=0,
        infants=0,
        currency="HKD",
        date_from="2026-11-24",
    )
    assert [o["offer_id"] for o in result["offers"]] == ["wo_original"]
    offer = result["offers"][0]
    assert (
        not offer["ready"]
        and offer["fare_minor"] == 338959
        and offer["total_minor"] is None
        and offer["checked_bag_kg"] is None
    )
    assert [s["flight"] for s in offer["outbound"]] == ["BR852", "BR196"] and offer["inbound"][0][
        "origin"
    ] == "NRT"
    assert (
        supplier.submit(
            LiveApprovedFare(approval_id="review-1", query=query, offer=offer),
            [PAX],
            MAIL,
            principal=principal,
        )["state"]
        == "unavailable"
    )
    assert ("POST", "/api/agent-book") not in lane.requests
    lane.offer["conditions"] = {
        "baggage": "1 checked bag of 20 kg per passenger included on all flights"
    }
    lane.offer["conditions_source"] = "estimate"
    assert not supplier.reprice(query, result["search_id"], offer["offer_id"], principal=principal)[
        "offers"
    ][0]["ready"]
    lane.offer["conditions_source"] = "airline"
    proven = supplier.reprice(query, result["search_id"], offer["offer_id"], principal=principal)[
        "offers"
    ][0]
    assert proven["ready"] and proven["checked_bag_kg"] == 20 and proven["total_minor"] == 338959
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        supplier.reprice(
            query,
            result["search_id"],
            offer["offer_id"],
            principal={"kind": "device", "id": "paired"},
        )


def test_changed_fare_bound_submission_held_then_independent_status(setup):
    client, runtime, lane, supplier, principal = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    original = supplier.search(q, principal=principal)["offers"][0]
    a = LiveApprovedFare(approval_id="first-review", query=q, offer=original)
    lane.offer["price"] = "3489.59"
    revised = supplier.submit(a, [PAX], MAIL, principal=principal)
    assert (
        revised["state"] == "reprice"
        and revised["offer"]["total_minor"] == 348959
        and ("POST", "/api/agent-book") not in lane.requests
    )
    lane.booking["held"]["amount"] = 3489.59
    lane.status["charged_amount"] = 3489.59
    a = LiveApprovedFare(approval_id="second-review", query=q, offer=revised["offer"])
    held = supplier.submit(a, [PAX], MAIL, principal=principal)
    assert held == dict(
        state="held",
        booking_ref="second-review",
        currency="HKD",
        held_minor=348959,
        charged_minor=0,
    )
    assert lane.book_body == dict(
        search_id=original["search_id"],
        offer_id=original["offer_id"],
        contact_email=MAIL,
        passenger=PAX,
    )
    assert supplier.submit(a, [PAX], MAIL, principal=principal) == held
    restarted = LiveFlightProvider(runtime, httpx.MockTransport(lane.route))
    lane.status["pnr"] = None
    assert (
        restarted.status(held["booking_ref"], a.offer, principal=principal)["state"]
        == "needs_attention"
    )
    lane.status.update(pnr="QA8G67", charged_amount=1)
    assert (
        restarted.status(held["booking_ref"], a.offer, principal=principal)["state"]
        == "needs_attention"
    )
    lane.status["charged_amount"] = 3489.59
    done = restarted.status(held["booking_ref"], a.offer, principal=principal)
    assert done == dict(
        state="completed",
        booking_ref="second-review",
        pnr="QA8G67",
        charged_minor=348959,
        currency="HKD",
    )
    assert lane.requests.count(("POST", "/api/agent-book")) == 1
    with runtime.store.connection() as db:
        journal = str(
            [
                tuple(row)
                for row in db.execute(
                    "SELECT request,response FROM operations WHERE id LIKE 'letsfg-live-order/%'"
                )
            ]
        )
    assert all(v not in journal for v in [MAIL, "private.acceptance.token", "Example Lane"])


@pytest.mark.parametrize(
    "error,url,expected",
    [
        (
            "payment_method_required",
            "https://letsfg.co/connect?setup=one",
            "https://letsfg.co/connect?setup=one",
        ),
        ("payment_declined", "https://evil.example/card", None),
        (
            "payment_method_required",
            "https://letsfg.co/connect?next=https%3A%2F%2Fevil.example",
            None,
        ),
    ],
)
def test_card_setup_only_trusted_link_and_owner_decision(setup, error, url, expected):
    client, runtime, lane, supplier, principal = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    o = supplier.search(q, principal=principal)["offers"][0]
    a = LiveApprovedFare(approval_id="card-review", query=q, offer=o)
    lane.booking = {"error": error, "add_card_url": url, "charged": 0}
    paid = supplier.submit(a, [PAX], MAIL, principal=principal)
    assert (
        paid["state"] == "card_required"
        and paid["action_url"] == expected
        and paid["charged_minor"] == 0
    )
    assert (
        supplier.submit(a, [PAX], MAIL, principal=principal) == paid
        and lane.requests.count(("POST", "/api/agent-book")) == 1
    )


def test_ambiguous_start_fenced_across_processes_and_second_review(setup):
    client, runtime, lane, supplier, principal = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    o = supplier.search(q, principal=principal)["offers"][0]
    lane.drop_ack = True
    a = LiveApprovedFare(approval_id="once", query=q, offer=o)
    first = supplier.submit(a, [PAX], MAIL, principal=principal)
    assert first["state"] == "uncertain"
    restarted = LiveFlightProvider(runtime, httpx.MockTransport(lane.route))
    assert restarted.status("once", o, principal=principal) == first
    assert restarted.submit(a, [PAX], MAIL, principal=principal) == first
    assert (
        restarted.submit(
            a.model_copy(update={"approval_id": "another-review"}), [PAX], MAIL, principal=principal
        )
        == first
    )
    changed_contacts = dict(PAX, address_city="Another test city")
    another = restarted.submit(
        a.model_copy(update={"approval_id": "corrected-contact"}),
        [changed_contacts],
        "changed@example.test",
        principal=principal,
    )
    assert another["state"] == "uncertain" and another["booking_ref"] is None
    assert lane.requests.count(("POST", "/api/agent-book")) == 1
    assert not official_url("https://letsfg.co@evil.example/connect")
    assert not official_url("https://letsfg.co/redirect?u=https%3A%2F%2Fevil.example")


def test_party_price_is_per_seat_one_submission_for_all_and_lap_infant(setup):
    _, _, lane, supplier, principal = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST, adults=1, children=1, infants=1)
    o = supplier.search(q, principal=principal)["offers"][0]
    assert o["total_minor"] == 677918 and o["passenger_count"] == 3
    a = LiveApprovedFare(approval_id="family", query=q, offer=o)
    assert supplier.submit(a, [PAX], MAIL, principal=principal)["state"] == "missing_details"
    child = dict(PAX, given_name="Child", born_on="2018-01-01")
    baby = dict(PAX, given_name="Baby", born_on="2026-01-01")
    lane.booking["held"]["amount"] = 6779.18
    assert supplier.submit(a, [PAX, child, baby], MAIL, principal=principal)["held_minor"] == 677918
    assert (
        len(lane.book_body["additional_passengers"]) == 2
        and lane.requests.count(("POST", "/api/agent-book")) == 1
    )


def test_concurrent_confirmations_create_one_hold_and_read_only_cancellation(setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    _, runtime, lane, supplier, owner = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    offer = supplier.search(q, principal=owner)["offers"][0]
    approved = LiveApprovedFare(approval_id="owner-review/7", query=q, offer=offer)
    again = LiveFlightProvider(runtime, httpx.MockTransport(lane.route))
    ready = Barrier(2)

    def submit(adapter):
        ready.wait(timeout=3)
        return adapter.submit(approved, [PAX], MAIL, principal=owner)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(submit, (supplier, again)))
    assert {r["state"] for r in results} <= {"uncertain", "held"}
    assert lane.requests.count(("POST", "/api/agent-book")) == 1
    lane.status = {"state": "failed", "charged_amount": None}
    end = again.status("owner-review/7", offer, principal=owner)
    assert end["state"] == "failed" and end["charged_minor"] == 0
    info = again.cancellation_info("owner-review/7", offer, principal=owner)
    assert info["state"] == "supplier_review_required" and not any(
        "/stop" in path for _, path in lane.requests
    )


def test_conflicting_offer_id_and_impossible_connection_are_not_payable(setup):
    _, _, lane, supplier, owner = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    wrong = deepcopy(lane.offer)
    wrong["segments"][1]["flight_number"] = "BR999"
    lane.extra = [wrong]
    assert supplier.search(q, principal=owner)["state"] == "no_verified_offer"
    lane.extra = []
    lane.offer["segments"][1]["departure_time"] = "2026-11-24T12:00:00"
    result = supplier.search(q, principal=owner)
    assert not result["offers"][0]["ready"]
    assert result["offers"][0]["reason"] == "itinerary_times_unverified"


def test_bank_challenge_and_untrusted_ref_do_not_create_ticket(setup):
    _, _, lane, supplier, owner = setup
    authorize(setup)
    q = LiveFlightQuery(**REQUEST)
    offer = supplier.search(q, principal=owner)["offers"][0]
    approved = LiveApprovedFare(approval_id="bank-review", query=q, offer=offer)
    lane.booking = {
        "booking_ref": "private.acceptance.token",
        "state": "awaiting_your_approval",
        "approve_url": "https://letsfg.co/connect?request=bank",
    }
    next_step = supplier.submit(approved, [PAX], MAIL, principal=owner)
    assert (
        next_step["state"] == "bank_approval" and next_step["action_url"] and "pnr" not in next_step
    )
    lane.status["booking_ref"] = "wrong"
    guarded = supplier.status("bank-review", offer, principal=owner)
    assert (
        guarded["state"] == "needs_attention"
        and "pnr" not in guarded
        and "charged_minor" not in guarded
    )


def test_first_price_change_invalidates_approval_and_previous_payment_stays_on_its_offer(setup):
    _, _, lane, supplier, principal = setup
    authorize(setup)
    query = LiveFlightQuery(**REQUEST)
    original = supplier.search(query, principal=principal)["offers"][0]
    initial = LiveApprovedFare(approval_id="initial-price", query=query, offer=original)
    lane.offer["price"] = "3530"
    change = supplier.submit(initial, [PAX], MAIL, principal=principal)
    assert change["state"] == "reprice"
    lane.offer["price"] = "3389.59"
    assert supplier.submit(initial, [PAX], MAIL, principal=principal) == change
    assert ("POST", "/api/agent-book") not in lane.requests
    approved = initial.model_copy(update={"approval_id": "owner-agreed-again"})
    assert supplier.submit(approved, [PAX], MAIL, principal=principal)["state"] == "held"
    assert (
        supplier.status(approved.approval_id, original, principal=principal)["state"] == "completed"
    )
    lane.offer["price"] = "3530"
    different = LiveApprovedFare(approval_id="higher-fare", query=query, offer=change["offer"])
    result = supplier.submit(different, [PAX], MAIL, principal=principal)
    assert result["state"] == "needs_attention" and result["booking_ref"] is None
    assert "charged_minor" not in result and "pnr" not in result
    assert lane.requests.count(("POST", "/api/agent-book")) == 1
