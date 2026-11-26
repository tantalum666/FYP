"""Real text entry and supplier adapter with isolated Session and supplier transports."""

from datetime import datetime, timezone
import json

import httpx
from fastapi.testclient import TestClient
import pytest

from desk.app import create_app
from desk.flight_booking.market_search import MarketFlightRequest, accepted_airports
from session_protocol_fixture import install_session_protocol

DAY = "2030-04-19"
QUESTION = "东京想飞成田机场（NRT）还是羽田机场（HND）？"
REQUEST = {
    "origin": "TPE",
    "destination": "Tokyo (NRT or HND)",
    "departure": DAY,
    "adults": 1,
    "checked_bag_kg": 18,
}


class MarketLane:
    def __init__(self, runtime):
        self.searches = []
        self.gets = []
        self.pending = set()
        self.fail = set()
        self.price = {"NRT": 1010, "HND": 820}
        self.grant = "sample-grant"
        self.bag_proven = False
        runtime.letsfg_auth.account = lambda: {"connected": bool(self.grant), "version": self.grant}
        runtime.letsfg_auth.grant = lambda principal: ("synthetic", self.grant)
        runtime.live_flight_provider.transport = httpx.MockTransport(self.handle)

    def handle(self, req):
        path = req.url.path
        if path == "/api/search":
            body = json.loads(req.content)
            self.searches.append(body)
            return httpx.Response(202, json={"search_id": "ws_" + body["destination"]})
        assert req.method == "GET" and path.startswith("/api/results/"), (req.method, path)
        airport = path.rsplit("_", 1)[1]
        self.gets.append(airport)
        if airport in self.fail:
            return httpx.Response(503, json={})
        if airport in self.pending:
            self.pending.remove(airport)
            return httpx.Response(200, json={"status": "searching"})
        dates = next(row for row in self.searches if row["destination"] == airport)
        origin = dates["origin"]
        day = dates["date_from"]
        offer = {
            "id": "wo_" + airport,
            "currency": "HKD",
            "price": self.price[airport],
            "stops": 0,
            "origin": origin,
            "destination": airport,
            "departure_time": day + "T12:00:00",
            "arrival_time": day + "T15:15:00",
            "airline_code": "CI",
            "flight_number": "CI100",
        }
        if self.bag_proven:
            offer.update(
                conditions_source="airline",
                conditions={
                    "baggage": "1 checked bag of 20 kg per passenger included on all flights"
                },
            )
        return httpx.Response(200, json={"status": "completed", "offers": [offer]})


def send(client, words, key, chat=None):
    res = client.post(
        "/api/assistant/messages",
        json={"message": words, "language": "zh", "conversation_id": chat},
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )
    res.raise_for_status()
    return res.json()


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    app = create_app(
        tmp_path,
        password="fixture",
        scheduler=False,
        clock=lambda: datetime(2030, 4, 18, 3, 0, tzinfo=timezone.utc),
    )
    c = TestClient(app, headers={"X-Desk-Request": "1"})
    c.post("/api/session", json={"username": "owner", "password": "fixture"}).raise_for_status()
    r = app.state.runtime
    return c, r, install_session_protocol(r), MarketLane(r)


def test_either_airport_keeps_party_date_and_bag_through_verified_prices(desk):
    c, r, model, lane = desk
    model.final = QUESTION
    one = send(c, "明天从台北去东京，一位成人，要托运一件18公斤的行李。请查航班。", "first")
    assert "HND" in one["message"] and not lane.searches
    model.next_calls = [("live_flight_search", REQUEST)]
    reply = send(c, "都行", "either", one["conversation_id"])
    assert reply["kind"] == "live_flight_checkout", reply
    view = reply["live_flight_checkout"]
    assert view["state"] == "offers", view
    assert [q["destination"] for q in lane.searches] == ["NRT", "HND"]
    assert all(
        q["origin"] == "TPE" and q["adults"] == 1 and q["date_from"] == DAY for q in lane.searches
    )
    assert view["market"]["checked_bag_kg"] == 18
    assert [(o["outbound"][-1]["destination"], o["fare_minor"]) for o in view["choices"]] == [
        ("HND", 82000),
        ("NRT", 101000),
    ]
    assert all(o["total_minor"] is None and not o["payable"] for o in view["choices"])
    assert (
        send(c, "都行", "either", one["conversation_id"])["live_flight_checkout"]["id"]
        == view["id"]
    )
    assert len(lane.searches) == 2
    link = f"/api/assistant/flight-checkouts/{view['id']}"
    chosen = c.post(
        link + "/actions",
        json={
            "conversation_id": one["conversation_id"],
            "version": view["version"],
            "action": "select",
            "number": 2,
        },
    ).json()
    assert (
        chosen["selected"] == 2
        and chosen["state"] == "seller_only"
        and chosen["source"]["request"]["destination"] == "NRT"
    )
    assert lane.gets[-1] == "NRT"
    with r.store.connection() as db:
        assert db.execute("select count(*) from sandbox_flight_bookings").fetchone()[0] == 0
        assert (
            db.execute(
                "select count(*) from operations where id like 'letsfg-live-order/%'"
            ).fetchone()[0]
            == 0
        )


def test_one_route_fails_other_completes_without_restarting_search(desk):
    c, r, model, lane = desk
    lane.pending.add("NRT")
    lane.fail.add("HND")
    model.next_calls = [("live_flight_search", REQUEST)]
    reply = send(c, "查台北去东京两座机场的价格", "search")
    first = reply["live_flight_checkout"]
    assert first["state"] == "searching"
    url = f"/api/assistant/flight-checkouts/{first['id']}/actions"
    view = c.post(
        url,
        json={
            "action": "status",
            "version": first["version"],
            "conversation_id": reply["conversation_id"],
        },
    ).json()
    assert view["state"] == "offers" and len(view["choices"]) == 1
    assert [r["state"] for r in view["routes"]] == ["offers", "unavailable"]
    assert len(lane.searches) == 2
    lane.grant = "different"
    hidden = c.get(
        url.removesuffix("/actions"), params={"conversation_id": reply["conversation_id"]}
    ).json()
    assert hidden["state"] == "source" and hidden["choices"] == []


def test_an_explicit_airport_choice_is_not_broadened():
    from types import SimpleNamespace

    chat = SimpleNamespace(
        items=[{"role": "assistant", "text": "希思罗（LHR）还是盖特威克（LGW）？"}]
    )
    q = MarketFlightRequest.model_validate(REQUEST | {"destination": "LHR"}).model_dump()
    assert accepted_airports(q, "都行", chat)["destination"] == ["LHR", "LGW"]
    assert accepted_airports(q, "只要希思罗", chat)["destination"] == ["LHR"]


def test_parallel_airport_calls_make_one_scoped_list_and_spoken_choice_only_reprices(desk):
    c, r, model, lane = desk
    model.next_calls = [
        ("live_flight_search", REQUEST | {"destination": d}) for d in ("NRT", "HND")
    ]
    reply = send(c, "帮我查成田和羽田机场", "both-functions")
    view = reply["live_flight_checkout"]
    assert view["market"]["destination"] == ["NRT", "HND"]
    assert len(view["choices"]) == 2 and len(lane.searches) == 2
    selected = send(c, "选第二班", "choose", reply["conversation_id"])
    assert selected["live_flight_checkout"]["selected"] == 2
    assert selected["live_flight_checkout"]["state"] == "seller_only"
    assert len(lane.searches) == 2 and lane.gets[-1] == "NRT"


def test_unconnected_desk_keeps_requested_airports_and_makes_no_sandbox_order(desk):
    c, _, model, lane = desk
    lane.grant = None
    model.next_calls = [("live_flight_search", REQUEST)]
    view = send(c, "帮我查台北飞东京", "needs-connection")["live_flight_checkout"]
    assert view["state"] == "source" and not view["connected"] and view["choices"] == []
    assert view["market"]["destination"] == ["NRT", "HND"] and not lane.searches


def test_selected_airport_is_repriced_and_a_changed_total_never_submits(desk):
    c, runtime, model, lane = desk
    lane.bag_proven = True
    model.next_calls = [("live_flight_search", REQUEST)]
    reply = send(c, "查这两个机场", "listed")
    view = reply["live_flight_checkout"]
    chat = reply["conversation_id"]
    pick = next(o for o in view["choices"] if o["outbound"][-1]["destination"] == "HND")
    principal = {"kind": "owner", "id": "owner", "session": c.cookies["desk_companion_session"]}
    checkout = runtime.live_flight_checkouts
    reviewed = checkout.action(
        principal, chat, view["id"], "select", view["version"], pick["number"]
    )
    assert reviewed["state"] == "review" and pick["total_minor"] == 82000
    lane.price["HND"] = 845
    changed = checkout.confirm(
        principal, chat, view["id"], reviewed["version"], 82000, "HKD", [], "fixture@example.test"
    )
    assert changed["state"] == "review" and changed["reason"] == "terms_changed"
    assert changed["choices"][pick["number"] - 1]["total_minor"] == 84500
    with runtime.store.connection() as db:
        assert (
            db.execute(
                "select count(*) from operations where id like 'letsfg-live-order/%'"
            ).fetchone()[0]
            == 0
        )


def test_parallel_searches_cannot_drop_different_bag_or_budget_constraints():
    from desk.flight_booking.market_search import combine
    from desk.store import DomainError

    left = {"origin": ["TPE"], "destination": ["HND"], "departure": DAY}
    right = left | {"destination": ["NRT"]}
    assert combine(left, right | {"adults": 1})["destination"] == ["HND", "NRT"]
    for extra in ({"max_hkd": 500}, {"checked_bag_kg": 18}, {"return_date": "2030-04-22"}):
        with pytest.raises(DomainError, match="FLIGHT_DIFFERENT_SEARCH_TERMS"):
            combine(left, right | extra)
        with pytest.raises(DomainError, match="FLIGHT_DIFFERENT_SEARCH_TERMS"):
            combine(left | extra, right)
