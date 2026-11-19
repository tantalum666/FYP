"""One normal text entry, server-bound prices and two independent owner choices."""

import json
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.flight_booking.provider import LetsFG
from session_protocol_fixture import install_session_protocol


class Sandbox:
    def __init__(self, day):
        self.day = day
        self.calls = []
        self.answer = None
        self.question = True
        self.loss = False
        self.total = 35.43

    def __call__(self, req):
        assert req.url.host == "letsfg.co" and req.url.path.startswith(
            "/developers/api/v1/sandbox/flights/"
        )
        assert "Authorization" not in req.headers and "X-API-Key" not in req.headers
        path = req.url.path.split("/flights/")[1]
        b = json.loads(req.content) if req.content else {}
        self.calls.append((req.method, path, b))
        offer = {"offer_id": "sb_fixture1", "search_id": "sb_search1"}
        base = {"sandbox": True, "booking_id": "sb_dev_fixture", "offer": offer}
        if path == "search":
            leg = {
                "flight_no": "FR4315",
                "airline": "FR",
                "origin": "HKG",
                "destination": "HND",
                "departure": self.day + "T19:00:00",
                "arrival": self.day + "T22:10:00",
            }
            return httpx.Response(
                200,
                json={
                    "origin": "HKG",
                    "destination": "HND",
                    "currency": "HKD",
                    "search_id": offer["search_id"],
                    "offers": [
                        {
                            "id": offer["offer_id"],
                            "source_tier": "sandbox",
                            "outbound": {"segments": [leg]},
                            "availability_seats": 2,
                            "currency": "HKD",
                            "price": 34,
                        }
                    ],
                },
            )
        if path == "book":
            assert b["offer_id"] == offer["offer_id"] and b["sandbox"] == {
                "scenario": "price_change",
                "speed": "realistic",
            }
            assert b["passengers"][0]["email"].endswith("@example.com")
            if self.loss:
                self.loss = False
                raise httpx.ReadTimeout("lost creation acknowledgement")
            return httpx.Response(
                202,
                json=base
                | {
                    "held": {"currency": "HKD", "amount": 34, "card": {"last4": "4242"}},
                    "charged": 0,
                },
            )
        if path.endswith("/answer"):
            assert b["round"] == 1
            self.answer = b
            return httpx.Response(200, json={"ok": True, "sandbox": True})
        assert req.method == "GET"
        r = base | {
            "currency": "HKD",
            "card_last4": "4242",
            "held_amount": 34,
            "charged_amount": None,
            "pnr": "",
            "terminal": False,
            "state": "booking_in_progress",
        }
        if self.answer and self.answer.get("confirm"):
            r.update(state="completed", terminal=True, pnr="FYP123", charged_amount=self.total)
        elif self.answer:
            r.update(state="failed", terminal=True, message="The hold was released.")
        elif self.question:
            r["question"] = {
                "kind": "price_change",
                "round": 1,
                "expires_at_ms": 9999999999999,
                "price_change": {"old_total": 34, "new_total": 35.43, "currency": "HKD"},
            }
        return httpx.Response(200, json=r)


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    fixture = install_session_protocol(runtime)
    day = (date.today() + timedelta(days=7)).isoformat()
    sandbox = Sandbox(day)
    runtime.flight_bookings.provider = LetsFG(httpx.MockTransport(sandbox))
    fixture.next_calls = [
        (
            "sandbox_flight_quote",
            {
                "origin": "HKG",
                "destination": "HND",
                "departure": day,
                "flight_number": "FR4315",
                "rehearse_price_change": True,
            },
        )
    ]
    client = TestClient(app)
    login(client)
    return runtime, client, sandbox


def login(client):
    assert client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success


def send(client, key, message, chat=None, booking=None):
    b = {"message": message, "language": "zh", "conversation_id": chat}
    if booking:
        b["flight_review"] = {k: booking[k] for k in ("id", "version")} | {
            "amount_minor": booking["review_minor"]
        }
    return client.post(
        "/api/assistant/messages", json=b, headers={"X-Desk-Request": "1", "X-Operation-Id": key}
    )


def status(c, chat):
    return c.get("/api/assistant/flight-bookings", params={"conversation_id": chat}).json()[
        "bookings"
    ]


@pytest.mark.parametrize(
    "decision,terminal", [("确认新总价 HK$35.43", "completed"), ("拒绝加价", "failed")]
)
def test_quote_approval_reprice_and_terminal_readback(desk, decision, terminal):
    r, c, s = desk
    q = send(c, "init", "帮我订 HKG 去 HND 的测试航班").json()
    assert q.get("flight_booking"), q
    chat = q["conversation_id"]
    fare = q["flight_booking"]
    assert fare["state"] == "quoted" and fare["review_minor"] == 3400 and "FR4315" in q["message"]
    assert [x[1] for x in s.calls] == ["search"]
    assert send(c, "wrong", "确认新总价 HK$35.43", chat, fare).status_code == 409
    assert send(c, "unbound", "确认", chat).json()["kind"] == "clarify"
    assert send(c, "initial", "确认", chat, fare).json()["flight_booking"]["state"] == "processing"
    assert send(c, "initial", "确认", chat, fare).is_success
    changed = status(c, chat)[0]
    assert (
        changed["state"] == "reprice"
        and changed["previous_minor"] == 3400
        and changed["review_minor"] == 3543
    )
    assert s.answer is None
    assert send(c, "stale", "同意新总价", chat, fare).json()["flight_booking"]["state"] == "reprice"
    other = TestClient(c.app)
    login(other)
    assert status(other, chat) == []
    assert send(other, "foreign", "确认", chat, changed).status_code == 404
    assert send(c, "changed", decision, chat, changed).is_success
    result = status(c, chat)[0]
    assert result["state"] == terminal and result["pnr"] == (
        "FYP123" if terminal == "completed" else None
    )
    assert result["charged_minor"] == (3543 if terminal == "completed" else None)
    assert result["released"] == (terminal == "failed")
    assert len([x for x in s.calls if x[1] == "book"]) == 1
    assert len([x for x in s.calls if x[1].endswith("/answer")]) == 1
    assert s.calls[-1][0] == "GET"
    assert send(c, "followup", "查一下订单", chat).json()["flight_booking"] == result


def test_uncertain_creation_reuses_original_idempotency_key_and_rejects_bad_capture(desk):
    r, c, s = desk
    initial = send(c, "q", "Book a test flight").json()
    chat = initial["conversation_id"]
    fare = initial["flight_booking"]
    s.loss = True
    uncertain = send(c, "yes", "确认", chat, fare).json()["flight_booking"]
    assert uncertain["state"] == "submit_unknown"
    assert send(c, "retry", "恢复原测试单", chat, uncertain).is_success
    assert len({b["idempotency_key"] for _, path, b in s.calls if path == "book"}) == 1
    revised = status(c, chat)[0]
    assert send(c, "reprice", "确认新总价 HK$35.43", chat, revised).is_success
    s.total = 36
    assert status(c, chat)[0]["state"] == "unverified"


def test_transient_quote_can_recover_without_creating_an_order(desk):
    r, client, sandbox = desk
    first = True

    def respond(req):
        nonlocal first
        if first:
            first = False
            assert req.url.path.endswith("/search")
            return httpx.Response(503, json={})
        return sandbox(req)

    r.flight_bookings.provider = LetsFG(httpx.MockTransport(respond))
    assert (
        send(client, "quote-transient", "Please book that test flight").json()["flight_booking"][
            "state"
        ]
        == "quoted"
    )
    assert [path for _, path, _ in sandbox.calls] == ["search"]
