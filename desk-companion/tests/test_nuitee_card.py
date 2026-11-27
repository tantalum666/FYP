"""Exercise the ordinary chat, scoped review and independent ticket/card receipts."""

from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib

from fastapi.testclient import TestClient
import httpx
import pytest

from desk.app import create_app
from desk.flight_booking.market_search import nuitee_test_requested
from session_protocol_fixture import install_session_protocol

QUERY = {
    "origin": ["HKG"],
    "destination": ["PEK"],
    "departure": "2030-04-19",
    "adults": 1,
    "checked_bag_kg": 15,
}
NOW = datetime(2030, 4, 18, 3, tzinfo=timezone.utc)


def test_ios_allows_only_the_named_local_test_frame_over_http():
    from desk.flight_booking.card_frame import HOST

    info = Path(__file__).resolve().parents[1] / "frontend/ios/App/App/Info.plist"
    with info.open("rb") as plist:
        ats = plistlib.load(plist)["NSAppTransportSecurity"]
    domain = ats["NSExceptionDomains"][HOST]
    assert domain["NSExceptionAllowsInsecureHTTPLoads"] is True
    assert not domain.get("NSIncludesSubdomains")
    assert not ats.get("NSAllowsArbitraryLoads") and not ats.get("NSAllowsArbitraryLoadsInWebContent")


class Supplier:
    def __init__(self):
        self.price = 1200
        self.kg = 23
        self.intent = "requires_payment_method"
        self.amount_received = None
        self.intent_amount = 120000
        self.intent_currency = "hkd"
        self.ticketed = False
        self.prebooks = 0
        self.price_at_prebook = None
        self.orders = []

    def raw(self):
        return {
            "searchId": "testsearch",
            "offerId": "testoffer",
            "expiration": "2030-04-18T05:00:00Z",
            "segments": [
                {
                    "direction": "OUTBOUND",
                    "originCode": "HKG",
                    "destinationCode": "PEK",
                    "departureTime": "2030-04-19T10:00:00",
                    "arrivalTime": "2030-04-19T13:00:00",
                    "carrier": {"marketingName": "Nuitée Air", "marketingCode": "ND"},
                    "flight": {"marketingNumber": "201"},
                    "stopCount": 0,
                }
            ],
            "pricing": {"display": {"total": self.price, "currency": "HKD"}},
            "baggage": {
                "hasCheckedBag": True,
                "included": [
                    {
                        "bagType": "checked",
                        "passengerType": "ALL",
                        "weightKg": self.kg,
                        "pieces": 1,
                        "pricing": {"display": {"amount": 0, "currency": "HKD"}},
                    }
                ],
            },
            "fare": {"family": "Standard", "mixedFareFamily": False},
            "terms": {"refundable": False},
            "passengers": {"adults": 1},
        }

    def handle(self, req):
        raw = self.raw()
        path = req.url.path
        if req.url.host == "api.stripe.com":
            assert "X-API-Key" not in req.headers
            return httpx.Response(
                200,
                json={
                    "id": "pi_fixture",
                    "livemode": False,
                    "amount": self.intent_amount,
                    "currency": self.intent_currency,
                    "status": self.intent,
                    "amount_received": self.amount_received,
                },
            )
        assert req.url.host == "api.liteapi.travel" and req.headers["X-API-Key"].startswith("sand_")
        body = json.loads(req.content) if req.content else None
        if path.endswith("/rates"):
            data = {
                "searchId": "testsearch",
                "journeys": [{"segments": raw["segments"], "offers": [raw]}],
            }
        elif path.endswith("/verify"):
            assert body == {"offerId": "testoffer"}
            data = {"searchId": "testsearch", "journey": raw}
        elif path.endswith("/prebooks") or path.endswith("/prebooks/testprebook"):
            if req.method == "POST":
                assert body["usePaymentSdk"] and body["passengers"][0]["lastName"] == "Doe"
                self.prebooks += 1
                if self.price_at_prebook:
                    self.price = self.price_at_prebook
                    raw = self.raw()
            data = {
                "prebookId": "testprebook",
                "searchId": "testsearch",
                "transactionId": "testtxn",
                "secretKey": "pi_fixture_secret_example",
                "paymentTypes": ["TRANSACTION_ID"],
                "price": self.price,
                "currency": "HKD",
                "booking": {
                    "journey": raw,
                    "order": {"reference": {"orderId": "orderref", "airlineBookings": []}},
                },
            }
        elif path.endswith("/bookings/"):
            self.orders.append(body)
            assert body == {
                "prebookId": "testprebook",
                "payment": {"method": "TRANSACTION_ID", "transactionId": "testtxn"},
            }
            data = {"booking": {"bookingId": "testbooking"}}
        elif path.endswith("/bookings/testbooking"):
            book = {
                "bookingId": "testbooking",
                "order": {"reference": {"orderId": "orderref", "airlineBookings": []}},
                "pricing": {"totalAmount": self.price, "currency": "HKD"},
                "payment": {"amount": self.price, "currency": "HKD"},
                "paymentStatus": "completed",
                "status": "CONFIRMED",
                "journey": raw,
                "airlineLocators": [{"airlineCode": "ND", "airlinePnr": "ABC123"}],
            }
            if self.ticketed:
                book["ticketData"] = {
                    "ticketedAt": "2030-04-18T03:00:00Z",
                    "tickets": [{"status": "issued", "ticketNumber": "9990000000001"}],
                }
            data = {"booking": book}
        else:
            raise AssertionError(path)
        return httpx.Response(200, json={"data": [data]})


@pytest.fixture
def lane(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: NOW)
    c = TestClient(app, base_url="https://testserver", headers={"X-Desk-Request": "1"})
    c.post("/api/session", json={"username": "owner", "password": "fixture"}).raise_for_status()
    runtime = app.state.runtime
    supplier = Supplier()
    adapter = runtime.live_flight_checkouts.nuitee
    adapter.keys = {"private": "sand_" + "s" * 22, "public": "pk_test_" + "p" * 22}
    adapter.transport = httpx.MockTransport(supplier.handle)
    model = install_session_protocol(runtime)
    model.next_calls = [("live_flight_search", QUERY)]
    reply = c.post(
        "/api/assistant/messages",
        headers={"X-Operation-Id": "nuitee-quote"},
        json={
            "message": "用 Nuitée 沙盒查香港 HKG 去北京 PEK 的测试航班，4月19日，1人，15公斤托运。",
            "language": "zh",
        },
    ).json()
    view = reply["live_flight_checkout"]
    assert view["provider"] == "nuitee_sandbox" and view["choices"][0]["checked_bag_kg"] == 23
    chat = reply["conversation_id"]
    path = f"/api/assistant/flight-checkouts/{view['id']}"

    def act(view, action, **extra):
        response = c.post(
            path + "/actions",
            json={"conversation_id": chat, "version": view["version"], "action": action, **extra},
        )
        response.raise_for_status()
        return response.json()

    review = act(view, "select", number=1)

    def pay(view):
        res = c.post(
            path + "/test-card",
            json={
                "conversation_id": chat,
                "version": view["version"],
                "amount_minor": view["choices"][0]["total_minor"],
                "currency": "HKD",
                "confirm_purchase": True,
            },
        )
        res.raise_for_status()
        assert res.headers["cache-control"] == "no-store"
        return res.json()

    return c, path, chat, review, pay, act, supplier


def test_ticket_and_processor_capture_are_independently_reconciled(lane):
    client, path, chat, review, pay, act, supplier = lane
    start = pay(review)
    assert start["card"]["client_secret"] == "pi_fixture_secret_example"
    assert "secret" not in json.dumps(start["view"]) and not supplier.orders
    assert "card" not in pay(review) and supplier.prebooks == 1
    supplier.intent = "requires_capture"
    waiting = act(start["view"], "status")
    assert waiting["state"] == "processing" and waiting["receipt"]["held_minor"] == 120000
    assert "pnr" not in waiting["receipt"]
    supplier.ticketed = True
    issued = act(waiting, "status")
    assert issued["state"] == "ticketed_payment_pending"
    assert issued["receipt"]["ticket_numbers"] == ["9990000000001"]
    assert "charged_minor" not in issued["receipt"]
    supplier.intent = "succeeded"
    unknown = act(issued, "status")
    assert (
        unknown["state"] == "ticketed_payment_pending" and "charged_minor" not in unknown["receipt"]
    )
    supplier.amount_received = 120000
    final = act(unknown, "status")
    assert final["state"] == "completed" and final["receipt"]["charged_minor"] == 120000
    assert len(supplier.orders) == 1
    assert "secret" not in client.get(path, params={"conversation_id": chat}).text
    other = TestClient(client.app, base_url="https://testserver", headers={"X-Desk-Request": "1"})
    other.post("/api/session", json={"username": "owner", "password": "fixture"}).raise_for_status()
    assert other.get(path, params={"conversation_id": chat}).status_code >= 400


def test_reprice_and_missing_bag_require_another_decision(lane):
    _, _, _, review, pay, _, supplier = lane
    supplier.price = 1269
    changed = pay(review)
    assert "card" not in changed and changed["view"]["reason"] == "terms_changed"
    assert changed["view"]["choices"][0]["total_minor"] == 126900 and supplier.prebooks == 0
    supplier.kg = 10
    missing = pay(changed["view"])
    assert "card" not in missing and not missing["view"]["choices"][0]["payable"]
    assert not supplier.orders and supplier.prebooks == 0


def test_sandbox_requires_explicit_selection():
    assert not nuitee_test_requested("请帮我订真实机票，别用 Nuitée 沙盒", None)
    assert not nuitee_test_requested("帮我买机票", None)
    assert nuitee_test_requested("用 Nuitée 沙盒查机票", None)
    assert nuitee_test_requested("用Nuitée沙盒查机票", None)
    assert not nuitee_test_requested("不要Nuitée沙盒，帮我买机票", None)


def test_baggage_change_after_card_hold_does_not_commit_a_booking(lane):
    client, _, _, review, pay, act, supplier = lane
    approved = pay(review)["view"]
    supplier.intent = "requires_capture"
    supplier.kg = 10
    stopped = act(approved, "status")
    assert stopped["state"] == "needs_attention"
    assert stopped["revised_terms"]["checked_bag_kg"] == 10
    assert stopped["revised_terms"]["total_minor"] is None
    assert stopped["receipt"]["held_minor"] == 120000 and "charged_minor" not in stopped["receipt"]
    assert not supplier.orders
    supplier.kg = 23
    restored = act(stopped, "status")
    assert not supplier.orders, "Reading a restored fare must wait for a fresh buyer decision"
    assert restored["state"] == "reconfirm_original"
    assert act(restored, "status")["version"] == restored["version"]
    assert "card" not in pay(approved) and not supplier.orders

    # A second change while the restored quote is on screen invalidates that version too.
    supplier.price = 1350
    changed = pay(restored)
    assert "card" not in changed and not supplier.orders
    assert changed["view"]["revised_terms"]["total_minor"] == 135000
    assert changed["view"]["receipt"]["held_minor"] == 120000
    # Read a receipt created by the preceding release, where only the reason was stored.
    with client.app.state.runtime.store.connection(write=True) as db:
        db.execute(
            "UPDATE live_flight_checkouts SET data=json_remove(data,'$.revised_terms','$.approval_invalidated') WHERE id=?",
            (stopped["id"],),
        )
    supplier.price = 1200
    final_review = act(changed["view"], "status")
    assert final_review["state"] == "reconfirm_original" and not supplier.orders
    supplier.ticketed = True
    issued = pay(final_review)
    assert "card" not in issued and issued["view"]["state"] == "ticketed_payment_pending"
    assert issued["view"]["receipt"]["ticket_numbers"] == ["9990000000001"]
    assert "card" not in pay(final_review)
    assert len(supplier.orders) == supplier.prebooks == 1


def test_reconfirming_an_unfunded_prebook_keeps_the_original_card_intent(lane):
    _, _, _, review, pay, act, supplier = lane
    original = pay(review)
    supplier.price = 1350
    stopped = pay(original["view"])
    assert "card" not in stopped and stopped["view"]["revised_terms"]["fare_minor"] == 135000
    supplier.price = 1200
    restored = act(stopped["view"], "status")
    assert restored["state"] == "reconfirm_original" and not supplier.orders
    assert pay(restored)["card"] == original["card"]
    assert supplier.prebooks == 1 and not supplier.orders


def test_restored_fare_remains_a_question_after_restart(lane):
    client, _, chat, review, pay, act, supplier = lane
    pending = pay(review)["view"]
    supplier.intent = "requires_capture"
    supplier.kg = 10
    assert act(pending, "status")["state"] == "needs_attention"
    before = client.app.state.runtime
    restarted = create_app(before.store.directory, scheduler=False, clock=lambda: NOW)
    adapter = restarted.state.runtime.live_flight_checkouts.nuitee
    adapter.keys = before.live_flight_checkouts.nuitee.keys
    adapter.transport = httpx.MockTransport(supplier.handle)
    with TestClient(
        restarted, base_url="https://testserver", headers={"X-Desk-Request": "1"}
    ) as reopened:
        reopened.cookies.update(client.cookies)
        supplier.kg = 23
        result = reopened.post(
            "/api/assistant/messages",
            headers={"X-Operation-Id": "read-restored-original"},
            json={
                "conversation_id": chat,
                "message": "请查回这张机票的电子客票号。",
                "language": "zh",
            },
        )
    result.raise_for_status()
    assert result.json()["live_flight_checkout"]["state"] == "reconfirm_original"
    assert "再确认" in result.json()["message"] and not supplier.orders


@pytest.mark.parametrize(
    "field,changed,original",
    [
        ("intent_amount", 130000, 120000),
        ("intent_currency", "usd", "hkd"),
        ("amount_received", 60000, 120000),
    ],
)
def test_changed_card_amount_waits_for_the_buyer(lane, field, changed, original):
    _, _, _, review, pay, act, supplier = lane
    start = pay(review)["view"]
    supplier.intent = "succeeded" if field == "amount_received" else "requires_capture"
    setattr(supplier, field, changed)
    stopped = act(start, "status")
    assert stopped["reason"] == "FLIGHT_NUITEE_CARD_AMOUNT_CHANGED" and not supplier.orders
    if field == "amount_received":
        assert stopped["receipt"]["charged_minor"] == changed
    setattr(supplier, field, original)
    restored = act(stopped, "status")
    assert restored["state"] == "reconfirm_original" and not supplier.orders
    supplier.ticketed = True
    result = pay(restored)
    assert "card" not in result and len(supplier.orders) == supplier.prebooks == 1


def test_payment_frame_cannot_use_minimal_or_authenticated_desk_api(lane, tmp_path):
    client, *_ = lane
    from desk.flight_booking import card_frame
    from starlette.requests import Request

    def request(path):
        return Request(
            {
                "type": "http",
                "scheme": "http",
                "path": path,
                "query_string": b"",
                "method": "GET",
                "headers": [(b"host", b"nuitee-card.localhost:8831")],
                "client": ("127.0.0.1", 35000),
                "server": ("127.0.0.1", 8831),
            }
        )

    (tmp_path / card_frame.FRAME).write_text("<html></html>")
    response = card_frame.static_response(request("/" + card_frame.FRAME), tmp_path, True)
    assert (
        response.status_code == 200
        and "js.stripe.com" in response.headers["content-security-policy"]
    )
    assert (
        card_frame.static_response(request("/api/session/connect"), tmp_path, True).status_code
        == 404
    )
    assert (
        card_frame.static_response(request("/" + card_frame.FRAME), tmp_path, False).status_code
        == 404
    )
    response = client.get("/api/diagnostics", headers={"Host": "nuitee-card.localhost:8831"})
    assert response.status_code == 404


def test_ticket_receipt_followup_stays_in_the_original_chat(lane):
    client, _, chat, review, pay, act, supplier = lane
    pending = pay(review)["view"]
    supplier.ticketed = True
    supplier.intent = "requires_capture"
    assert act(pending, "status")["state"] == "ticketed_payment_pending"
    message = "帮我查回这张机票的电子客票号、订座编号和实际扣款。"
    response = client.post(
        "/api/assistant/messages",
        headers={"X-Operation-Id": "ticket-read"},
        json={"message": message, "language": "zh", "conversation_id": chat},
    )
    response.raise_for_status()
    data = response.json()
    assert data["live_flight_checkout"]["receipt"]["pnr"] == "ABC123"
    assert all(text in data["message"] for text in ("9990000000001", "ABC123", "预授权", "待核实"))
    assert len(supplier.orders) == 1


def test_prebook_changed_while_original_fare_was_being_prepared(lane):
    _, _, _, review, pay, _, supplier = lane
    supplier.price_at_prebook = 1350
    result = pay(review)
    assert "card" not in result and not supplier.orders
    assert result["view"]["state"] == "review" and result["view"]["reason"] == "terms_changed"
    assert result["view"]["choices"][0]["total_minor"] == 135000
