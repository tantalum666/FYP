"""The original offered menu and the fresh, unapproved fare survive the chat process."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.flight_booking.provider import FlightQuery, LetsFG
from session_protocol_fixture import install_session_protocol
from test_flight_calendar_fit import DAY, FARES, PRIVATE, event, offer


TERMS = {
    "origin": "HKG",
    "destination": "HND",
    "departure": DAY,
    "adults": 1,
    "flight_number": "FA999",
    "airline": "FA",
    "nonstop": True,
    "max_hkd": 50,
}
COOKIE = "desk_companion_session"


class Inventory:
    def __init__(self):
        self.routes = {"HND": deepcopy(FARES)}
        self.searches = []
        self.on_search = None
        self.status = 200

    def __call__(self, req):
        assert (req.method, req.url.path) == ("POST", "/developers/api/v1/sandbox/flights/search")
        assert "Authorization" not in req.headers
        body = json.loads(req.content)
        assert body == {
            "origin": "HKG",
            "destination": body["destination"],
            "date_from": DAY,
            "adults": 1,
            "currency": "HKD",
        }
        self.searches.append(body)
        if self.on_search:
            self.on_search()
        return httpx.Response(
            self.status,
            json={
                "origin": "HKG",
                "destination": body["destination"],
                "currency": "HKD",
                "search_id": f"sb_search_{len(self.searches)}",
                "offers": self.routes[body["destination"]],
            },
        )


class Desk:
    def __init__(self, directory, inventory, cookie):
        app = create_app(
            directory,
            clock=lambda: datetime(2026, 11, 24, tzinfo=UTC),
            scheduler=False,
            password="fixture",
            connector_configs=(),
        )
        self.runtime = app.state.runtime
        self.session = install_session_protocol(self.runtime)
        self.inventory = inventory
        self.runtime.flight_bookings.provider = LetsFG(httpx.MockTransport(inventory))
        self.client = TestClient(app)
        self.cookie = cookie or self.runtime.store.create_owner_session()
        self.client.cookies.set(COOKIE, self.cookie)

    def ask(self, key, message, chat=None, *, status=200, stream=False, **fields):
        path = "/api/assistant/messages" + ("/stream" if stream else "")
        response = self.client.post(
            path,
            json={"message": message, "conversation_id": chat, **fields},
            headers={"X-Desk-Request": "1", "X-Operation-Id": key},
        )
        assert response.status_code == status, response.text
        if stream:
            last = [
                json.loads(line[5:])
                for line in response.text.splitlines()
                if line.startswith("data:")
            ][-1]
            assert last["type"] == "done", last
            return last["reply"]
        return response.json()

    def initial(self, chat=None, key="initial", **changes):
        terms = TERMS | changes
        self.session.next_calls = [("sandbox_flight_quote", terms)]
        return self.ask(
            key, f"Find flight {terms['flight_number']} to {terms['destination']} on {DAY}", chat
        )

    def reviews(self, chat):
        result = self.client.get(
            "/api/assistant/commerce-reviews", params={"conversation_id": chat}
        )
        assert result.is_success, result.text
        return result.json()


@pytest.fixture
def start(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    inventory = Inventory()
    return lambda cookie=None: Desk(tmp_path, inventory, cookie)


def decision(row):
    return {
        "flight_review": {
            "id": row["id"],
            "version": row["version"],
            "amount_minor": row["review_minor"],
        }
    }


def offered(reply):
    return [o["segment"]["flight"] for o in reply["flight_alternatives"]["alternatives"]]


def test_restart_recovers_exact_offers_reprices_once_and_reuses_the_review_row(start):
    desk = start()
    event_id = event(desk.runtime, DAY + "T09:00", DAY + "T10:00")
    first = desk.initial(
        flight_number="FA101", avoid_calendar_conflicts=True, rehearse_price_change=True
    )
    chat = first["conversation_id"]
    assert offered(first) == ["FA104", "FA105"]
    assert "revisit_flight_shortlist" not in {
        t["name"] for t in desk.session.creations[0]["agent"]["tools"]
    }
    assert first["flight_alternatives"]["requested_calendar_fit"] == "conflict"
    assert desk.reviews(chat) == {"has_flight_shortlist": True, "rows": []}

    fresh = dict(FARES[4], id="sb_new_offer", price=46.75)
    cheaper_different_time = offer("FA105", 20, "15:00", DAY + "T18:00")
    desk.inventory.routes["HND"] = [cheaper_different_time, fresh, FARES[3]]

    restarted = start(desk.cookie)
    assert not restarted.runtime.voice.conversations.entries
    assert restarted.reviews(chat) == {"has_flight_shortlist": True, "rows": []}
    prior = restarted.ask("history", "Show my original flight options", chat, stream=True)
    assert prior["flight_alternatives"]["original"] and offered(prior) == offered(first)
    assert [o["total_minor"] for o in prior["flight_alternatives"]["alternatives"]] == [4700, 4900]
    assert "Originally offered" in prior["message"]
    # A lost response for the first operation had no conversation ID in its request.
    replay = restarted.initial(
        flight_number="FA101", avoid_calendar_conflicts=True, rehearse_price_change=True
    )
    assert replay["conversation_id"] == chat and offered(replay) == offered(first)
    assert len(desk.inventory.searches) == 1

    picked = restarted.ask("selection", "Take the second one", chat, stream=True)
    row = picked["flight_booking"]
    assert row["segments"] == [first["flight_alternatives"]["alternatives"][1]["segment"]]
    assert (
        row["state"] == "quoted" and row["review_minor"] == 4675 and row["approved_minor"] is None
    )
    assert row["calendar_fit"] == "clear" and "HK$46.75" in picked["message"]
    assert restarted.ask("selection", "Take the second one", chat)["flight_booking"] == row
    assert [r["id"] for r in restarted.reviews(chat)["rows"]] == [row["id"]]
    with restarted.runtime.store.connection() as db:
        [record] = [
            json.loads(r[0]) for r in db.execute("SELECT data FROM sandbox_flight_bookings")
        ]
    assert (
        record["quote"]["offer_id"] == "sb_new_offer"
        and record["quote"]["search_id"] == "sb_search_2"
    )
    expected = FlightQuery.model_validate(
        TERMS
        | {
            "flight_number": "FA105",
            "avoid_calendar_conflicts": True,
            "rehearse_price_change": True,
        }
    )
    assert record["quote"]["search_terms"] == expected.model_dump(exclude_none=True)
    assert record["remote"] is None and record["original_search"]["flight_number"] == "FA101"
    assert len(desk.inventory.searches) == 2 and not restarted.session.requests
    transmitted = json.dumps([desk.session.creations, desk.session.events, desk.inventory.searches])
    assert PRIVATE not in transmitted and event_id not in transmitted


@pytest.mark.parametrize(
    "change", ["gone", "sold_out", "departure", "arrival", "over_budget", "carrier"]
)
def test_changed_inventory_cannot_replace_the_selection_or_leave_an_old_approval(start, change):
    desk = start()
    chat = desk.initial()["conversation_id"]
    old = desk.ask("first-pick", "choose FA102", chat)["flight_booking"]
    inventory = desk.inventory.routes["HND"]
    second = inventory[1]
    leg = second["outbound"]["segments"][0]
    if change == "gone":
        inventory.pop(1)
    elif change == "sold_out":
        second["availability_seats"] = 0
    elif change == "departure":
        leg["departure"] = DAY + "T10:00"
    elif change == "arrival":
        leg["arrival"] = DAY + "T14:00"
    elif change == "over_budget":
        second["price"] = 50.01
    else:
        leg["airline"] = "ZZ"
    failed = desk.ask("changed", "选第二班", chat)
    assert failed["error"] == "FLIGHT_OPTION_UNAVAILABLE" and "flight_booking" not in failed
    assert desk.ask("changed", "选第二班", chat)["error"] == failed["error"]
    assert desk.reviews(chat)["rows"][0]["state"] == "expired"
    assert (
        desk.ask("stale", "confirm", chat, status=409, **decision(old))["error"]["code"]
        == "FLIGHT_REVIEW_CHANGED"
    )
    assert len(desk.inventory.searches) == 3
    other = desk.ask("other", "选第一班", chat)["flight_booking"]
    assert other["id"] == old["id"] and other["segments"][0]["flight"] == "FA101"
    assert other["approved_minor"] is None and other["version"] > old["version"]


def test_two_unrelated_lists_and_repeated_flight_numbers_require_an_explicit_choice(start):
    desk = start()
    first = desk.initial()
    chat = first["conversation_id"]
    additional = [offer("FA201", 45, "14:30", DAY + "T19:00"), deepcopy(FARES[1])]
    for fare in additional:
        fare["outbound"]["segments"][0]["destination"] = "SIN"
    desk.inventory.routes["SIN"] = additional
    desk.session.next_calls = [
        ("sandbox_flight_quote", TERMS | {"destination": "SIN", "flight_number": "FA888"})
    ]
    second = desk.ask(
        "another-trip", f"Find flight FA888 to SIN on the {int(DAY[-2:])}th ({DAY})", chat
    )
    assert offered(second) == ["FA102", "FA201"]
    for key, message in [("ordinal", "take the second one"), ("number", "select FA102")]:
        answer = desk.ask(key, message, chat)
        assert all(label in answer["message"] for label in ["1. HKG → HND", "2. HKG → SIN"])
        assert "flight_booking" not in answer
    assert len(desk.inventory.searches) == 2
    distinct = desk.ask("unique", "pick FA103", chat)["flight_booking"]
    assert distinct["segments"][0]["destination"] == "HND"
    selected = desk.ask("specific", "选航班清单 2 的第 2 班", chat)["flight_booking"]
    assert (
        selected["segments"][0]["flight"] == "FA201"
        and selected["segments"][0]["destination"] == "SIN"
    )
    assert selected["id"] != distinct["id"]
    assert desk.ask("close", "cancel flight list 1", chat)["flight_booking"]["state"] == "cancelled"
    assert "no open" in desk.ask("closed", "select option 2 from flight list 1", chat)["message"]
    assert (
        desk.ask("remaining", "show flight list 2", chat)["flight_alternatives"]["shortlist_number"]
        == 2
    )
    assert len(desk.inventory.searches) == 4


def test_duplicate_flight_number_with_two_departures_requires_the_original_option_number(start):
    desk = start()
    desk.inventory.routes["HND"] = [FARES[1], offer("FA102", 39, "13:00", DAY + "T17:00")]
    chat = desk.initial()["conversation_id"]
    answer = desk.ask("ambiguous", "FA102", chat)
    assert "multiple departures" in answer["message"] and len(desk.inventory.searches) == 1
    chosen = desk.ask("specific", "select option 2 from flight list 1", chat)["flight_booking"]
    assert chosen["segments"][0]["departs"] == DAY + "T13:00" and chosen["approved_minor"] is None


def test_calendar_is_rechecked_at_selection_and_again_at_explicit_approval(start):
    desk = start()
    event(desk.runtime, DAY + "T09:00", DAY + "T10:00")
    first = desk.initial(flight_number="FA101", avoid_calendar_conflicts=True)
    chat = first["conversation_id"]
    pin = first["flight_alternatives"]["alternatives"][0]["calendar_choice"]
    event(desk.runtime, DAY + "T18:35", DAY + "T19:00")
    wrong = desk.ask("wrong-pin", "选 FA104", chat, calendar_flight_choice={**pin, "max_hkd": 100})
    assert "flight_booking" not in wrong and len(desk.inventory.searches) == 1
    blocked = desk.ask("old-client", "选 FA104", chat, calendar_flight_choice=pin)["flight_booking"]
    assert blocked["calendar_fit"] == "conflict" and blocked["approved_minor"] is None
    clear = desk.ask("another", "take the second flight", chat)["flight_booking"]
    assert clear["calendar_fit"] == "clear" and clear["version"] > blocked["version"]
    event(desk.runtime, DAY + "T20:00", DAY + "T20:20")
    final = desk.ask("approval", "Confirm", chat, selected_commerce_card=True, **decision(clear))[
        "flight_booking"
    ]
    assert final["calendar_fit"] == "conflict" and final["approved_minor"] is None
    assert len(desk.inventory.searches) == 3


def test_session_paraphrase_uses_only_the_owners_selector_and_keeps_calendar_local(start):
    desk = start()
    chat = desk.initial()["conversation_id"]
    event_id = event(desk.runtime, DAY + "T08:10", DAY + "T08:40")
    # An earlier calendar conversation can contain the same appointment in plain text.
    desk.runtime.voice.conversations.entries[chat].append("assistant", PRIVATE)
    desk.session.next_calls = [("revisit_flight_shortlist", {"flight_number": "FA101"})]
    shown = desk.ask("invented", "Could I look at those choices again?", chat)
    assert offered(shown) == ["FA101", "FA102", "FA103"] and len(desk.inventory.searches) == 1
    desk.session.next_calls = [
        ("revisit_flight_shortlist", {"option_number": 2, "check_calendar": True})
    ]
    desk.session.lose_result_once = True
    picked = desk.ask(
        "prose", "The second departure suits me. Could you check it against my calendar?", chat
    )
    advertised = {tool["name"] for tool in desk.session.creations[-1]["agent"]["tools"]}
    assert "revisit_flight_shortlist" in advertised
    assert advertised.isdisjoint({"sandbox_flight_quote", "calendar_query"})
    assert picked["flight_booking"]["segments"][0]["flight"] == "FA102"
    assert (
        picked["flight_booking"]["calendar_fit"] == "conflict" and len(desk.inventory.searches) == 2
    )
    transmitted = json.dumps([desk.session.creations, desk.session.events, desk.inventory.searches])
    assert PRIVATE not in transmitted and event_id not in transmitted
    output = json.loads(desk.session.functions[-1][0][0]["output"])
    assert output == {"kind": "clarify", "saved": False}


def test_scope_forgetting_and_closed_lists_block_old_choices_and_cached_replay(start):
    desk = start()
    first = desk.initial()
    chat = first["conversation_id"]
    foreign = start()
    assert foreign.reviews(chat) == {"has_flight_shortlist": False, "rows": []}
    assert (
        foreign.ask("guess", "show my original flight options", chat, status=404)["error"]["code"]
        == "CONVERSATION_NOT_FOUND"
    )
    foreign.ask("initial", f"Find flight FA999 to HND on {DAY}", status=404)
    desk.ask("cancel", "cancel flight list 1", chat)
    assert "no open" in desk.ask("late", "take the second one", chat)["message"]
    assert "closed" in desk.initial()["message"]
    assert desk.reviews(chat) == {"has_flight_shortlist": False, "rows": []}

    another = desk.initial(chat, "another")
    assert another["flight_alternatives"]["shortlist_number"] == 2
    assert desk.client.delete(
        "/api/voice/conversations/" + chat, headers={"X-Desk-Request": "1"}
    ).is_success
    assert desk.reviews(chat) == {"has_flight_shortlist": False, "rows": []}
    desk.ask("after-forget", "show flight list 2", chat, status=404)
    desk.ask("another", f"Find flight FA999 to HND on {DAY}", chat, status=404)
    assert len(desk.inventory.searches) == 2


def test_transient_lookup_can_retry_the_same_operation_and_still_needs_approval(start):
    desk = start()
    chat = desk.initial()["conversation_id"]
    desk.inventory.status = 503
    failed = desk.ask("pick", "take the second one", chat, status=503)
    assert (
        failed["error"]["code"] == "FLIGHT_PROVIDER_UNAVAILABLE"
        and desk.reviews(chat)["rows"] == []
    )
    desk.inventory.status = 200
    recovered = start(desk.cookie)
    row = recovered.ask("pick", "take the second one", chat)["flight_booking"]
    assert row["segments"][0]["flight"] == "FA102" and row["approved_minor"] is None
    assert recovered.ask("pick", "take the second one", chat)["flight_booking"] == row
    assert len(desk.inventory.searches) == 4


def test_cancellation_in_another_worker_wins_against_an_inflight_recheck(start):
    desk = start()
    chat = desk.initial()["conversation_id"]
    second = start(desk.cookie)
    entered, release = Event(), Event()

    def pause_search():
        entered.set()
        assert release.wait(10)

    desk.inventory.on_search = pause_search
    with ThreadPoolExecutor(max_workers=1) as worker:
        pending = worker.submit(desk.ask, "inflight", "choose FA102", chat, status=409)
        try:
            assert entered.wait(10)
            assert "cancelled" in second.ask("cancel", "cancel flight list 1", chat)["message"]
        finally:
            release.set()
        assert pending.result()["error"]["code"] == "FLIGHT_REVIEW_CHANGED"
    desk.ask("inflight", "choose FA102", chat, status=409)
    assert desk.reviews(chat) == {"has_flight_shortlist": False, "rows": []}
    assert len(desk.inventory.searches) == 2


def test_legacy_quote_and_pinned_card_without_a_saved_list_still_bind_their_own_terms(start):
    desk = start()
    original = desk.initial(flight_number="FA103")
    chat = original["conversation_id"]
    assert desk.reviews(chat)["has_flight_shortlist"] is False
    restarted = start(desk.cookie)
    restarted.session.next_calls = [
        (
            "sandbox_flight_quote",
            TERMS
            | {
                "flight_number": "FA106",
                "max_hkd": 100,
            },
        )
    ]
    pin = TERMS | {"flight_number": "FA104", "avoid_calendar_conflicts": True}
    row = restarted.ask("legacy-pin", "Check this flight again", chat, calendar_flight_choice=pin)[
        "flight_booking"
    ]
    assert row["segments"][0]["flight"] == "FA104" and row["calendar_fit"] == "clear"
    assert row["review_minor"] == 4700 and row["approved_minor"] is None
    assert {r["id"] for r in restarted.reviews(chat)["rows"]} == {
        original["flight_booking"]["id"],
        row["id"],
    }
    assert len(desk.inventory.searches) == 2


def test_a_submitted_record_is_no_longer_a_selectable_menu(start):
    desk = start()
    chat = desk.initial()["conversation_id"]
    row = desk.ask("pick", "choose FA102", chat)["flight_booking"]
    # Import an already approved review in the existing store, without submitting an order.
    with desk.runtime.store.connection(write=True) as db:
        db.execute(
            """UPDATE sandbox_flight_bookings SET serial=serial+1,
               data=json_set(data,'$.state','manual','$.approved',?,'$.remote','sb_dev_manual')
               WHERE id=?""",
            (row["review_minor"], row["id"]),
        )
    assert not desk.reviews(chat)["has_flight_shortlist"]
    assert "no open" in desk.ask("again", "choose FA101", chat)["message"]
    assert desk.reviews(chat)["rows"][0]["state"] == "manual" and len(desk.inventory.searches) == 2


def test_list_closed_while_the_session_interprets_a_followup(start):
    desk = start()
    chat = desk.initial()["conversation_id"]
    second = start(desk.cookie)

    def close_once():
        desk.session.on_check = None
        second.ask("close", "cancel flight list 1", chat)

    desk.session.on_check = close_once
    desk.session.next_calls = [("revisit_flight_shortlist", {"option_number": 2})]
    result = desk.ask(
        "interpret", "I'd like to see whether the second departure still works.", chat
    )
    assert "no open" in result["message"] and len(desk.inventory.searches) == 1
