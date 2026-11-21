"""Owner calendar constraints are local and are rechecked at financial admission."""

from datetime import UTC, date, datetime
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.calendar import iso
from desk.commerce_review import ReviewDecision
from desk.conversation import Conversations
from desk.flight_booking.calendar_fit import check_itineraries
from desk.flight_booking.provider import FlightQuery, LetsFG
from desk.flight_booking.timetable import flight_window, published_time
from desk.schemas import CreateEvents, EventAction, EventInput
from desk.store import DomainError
from session_protocol_fixture import install_session_protocol

DAY = "2026-11-29"
PRIVATE = "Private appointment 82, details stay on the desk"
BASE = {"origin": "HKG", "destination": "HND", "departure": DAY, "avoid_calendar_conflicts": True}


def leg(flight, departure, arrival, origin="HKG", destination="HND"):
    return {
        "flight": flight,
        "origin": origin,
        "destination": destination,
        "departs": departure,
        "arrives": arrival,
    }


def offer(number, price, takeoff, landing):
    return {
        "id": "sb_" + number,
        "source_tier": "sandbox",
        "availability_seats": 2,
        "currency": "HKD",
        "price": price,
        "outbound": {
            "segments": [
                {
                    "flight_no": number,
                    "airline": number[:2],
                    "origin": "HKG",
                    "destination": "HND",
                    "departure": DAY + "T" + takeoff,
                    "arrival": landing,
                }
            ]
        },
    }


FARES = [
    offer("FA101", 35, "07:30", DAY + "T12:00"),
    offer("FA102", 37, "08:00", DAY + "T13:00"),
    offer("FA103", 38, "08:30", DAY + "T13:30"),
    offer("FA104", 47, "18:30", "2026-11-30T02:55"),
    offer("FA105", 49, "19:40", "2026-11-30T01:50"),
    offer("FA106", 65, "20:00", "2026-11-30T02:00"),
]


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    app = create_app(
        tmp_path,
        clock=lambda: datetime(2026, 11, 22, tzinfo=UTC),
        password="fixture",
        scheduler=False,
    )
    r = app.state.runtime
    calls = []

    def supplier(req):
        path = req.url.path.rsplit("/", 1)[-1]
        body = json.loads(req.content) if req.content else {}
        calls.append((req.method, path, body))
        assert path == "search", "Unexpected supplier write"
        return httpx.Response(
            200,
            json={
                "search_id": "sb_testsearch",
                "origin": "HKG",
                "destination": "HND",
                "currency": "HKD",
                "offers": FARES,
            },
        )

    r.flight_bookings.provider = LetsFG(httpx.MockTransport(supplier))
    who = {"kind": "owner", "session": r.store.create_owner_session()}
    chat = SimpleNamespace(id="calendar-fit", task_id=None, owner=Conversations.owner(who))
    return r, who, chat, calls, app


def event(r, start, end, **kwargs):
    doc = EventInput.model_validate(
        {
            "title": PRIVATE,
            "start_local": start,
            "end_local": end,
            "timezone": "Asia/Hong_Kong",
            "reminder_minutes": [],
            **kwargs,
        }
    )
    return r.store.create(CreateEvents(event=doc), start + str(kwargs))["event_ids"][0]


def choose(row, action="confirm"):
    return ReviewDecision(
        id=row["id"], version=row["version"], amount_minor=row["review_minor"], action=action
    )


def test_time_windows_handle_airports_offsets_date_line_and_connections():
    x = leg("QA100", "2026-11-29T23:00", "2026-11-30T06:00")
    assert tuple(map(iso, flight_window([x]))) == (
        "2026-11-29T15:00:00.000000Z",
        "2026-11-29T21:00:00.000000Z",
    )
    west = leg("QA101", "2026-11-29T20:00", "2026-11-29T12:30", "HND", "LAX")
    assert tuple(map(iso, flight_window([west]))) == (
        "2026-11-29T11:00:00.000000Z",
        "2026-11-29T20:30:00.000000Z",
    )
    assert published_time("2026-11-28T17:00:15Z", "HKG") == "2026-11-29T01:00:15+08:00"
    assert flight_window([leg("QA1", "2026-11-01T01:30", "2026-11-01T09:30", "JFK", "LAX")]) is None
    assert flight_window([leg("QA1", "2026-03-08T02:30", "2026-03-08T09:30", "JFK", "LAX")]) is None
    assert (
        flight_window(
            [leg("QA1", "2026-11-01T01:30-05:00", "2026-11-01T09:30-08:00", "JFK", "LAX")]
        )
        is not None
    )
    assert flight_window([dict(x, origin="ZZZ")]) is None
    assert (
        flight_window([x, leg("QA2", "2026-11-30T05:55", "2026-11-30T12:00", "HND", "SIN")]) is None
    )


def test_busy_boundaries_recurrence_exceptions_and_uncertain_duration(desk):
    r, *_ = desk
    edge = leg("QA1", DAY + "T09:00", DAY + "T12:00")
    event(r, DAY + "T08:15", DAY + "T09:00")
    event(r, DAY + "T11:00", DAY + "T11:15", busy=False)
    # 12:00 Tokyo is 11:00 in Hong Kong. A meeting exactly at landing is adjacent.
    event(r, DAY + "T11:00", DAY + "T11:30")
    with r.store.connection() as db:
        assert check_itineraries(
            r.store, db, [{"segments": [edge]}, {"segments": [edge], "duration_seconds": 10800}]
        ) == ["clear", "unknown"]
    series = event(r, "2026-11-22T09:30", "2026-11-22T09:50", recurrence={"frequency": "weekly"})
    with r.store.connection() as db:
        assert check_itineraries(r.store, db, [{"segments": [edge]}]) == ["conflict"]
    r.store.event_action(
        series,
        EventAction(
            action="complete", scope="occurrence", occurrence_key=DAY + "T09:30", expected_version=1
        ),
        "complete-instance",
    )
    with r.store.connection() as db:
        assert check_itineraries(r.store, db, [{"segments": [edge]}]) == ["clear"]
    event(r, DAY + "T00:00", "2026-11-30T00:00", all_day=True)
    with r.store.connection() as db:
        assert check_itineraries(r.store, db, [{"segments": [edge]}]) == ["conflict"]


def test_only_eligible_fares_and_no_calendar_data_leave_the_desk(desk):
    r, _, _, calls, _ = desk
    svc = r.flight_bookings
    event(r, DAY + "T09:00", DAY + "T10:00")
    raw = FlightQuery.model_validate(BASE | {"max_hkd": 50})
    selected = svc.prepare(raw)["sandbox_quote"]
    assert selected["segments"][0]["flight"] == "FA104" and selected["total_minor"] == 4700
    choices = svc.prepare(raw.model_copy(update={"flight_number": "FA101"}))["flight_alternatives"]
    assert choices["requested_calendar_fit"] == "conflict" and choices["avoid_calendar_conflicts"]
    assert [o["segment"]["flight"] for o in choices["alternatives"]] == ["FA104", "FA105"]
    assert calls and all(
        c[2]
        == {"origin": "HKG", "destination": "HND", "date_from": DAY, "adults": 1, "currency": "HKD"}
        for c in calls
    )
    assert PRIVATE not in json.dumps([selected, choices, calls])
    with pytest.raises(DomainError, match="FLIGHT_CALENDAR_BUSY"):
        svc.prepare(raw.model_copy(update={"max_hkd": 40}))
    plain = svc.prepare(raw.model_copy(update={"avoid_calendar_conflicts": False}))["sandbox_quote"]
    assert plain["segments"][0]["flight"] == "FA101" and "avoid_calendar_conflicts" not in plain


def test_midnight_event_blocks_the_original_approval_and_recovery_requires_a_fresh_choice(desk):
    r, who, chat, calls, _ = desk
    svc = r.flight_bookings
    q = svc.prepare(FlightQuery.model_validate(BASE | {"flight_number": "FA104"}))["sandbox_quote"]
    initial = svc.attach(q, "overnight-fare", who, chat)
    assert initial["calendar_fit"] == "clear"
    event_id = event(r, "2026-11-30T01:00", "2026-11-30T01:30", timezone="Asia/Tokyo")
    blocked = svc.decide(choose(initial), who, chat.id)
    assert (
        blocked["calendar_fit"] == "conflict"
        and blocked["approved_minor"] is None
        and blocked["state"] == "quoted"
    )
    assert blocked["version"] > initial["version"] and [v[1] for v in calls] == ["search"]
    r.store.event_action(
        event_id,
        EventAction(action="delete", scope="series", expected_version=1),
        "remove-calendar-conflict",
    )
    # A formerly blocked card must be refreshed before a payment even when the conflict clears.
    clear = svc.decide(choose(blocked), who, chat.id)
    assert (
        clear["calendar_fit"] == "clear"
        and clear["version"] > blocked["version"]
        and clear["approved_minor"] is None
    )
    assert svc.decide(choose(clear, "decline"), who, chat.id)["state"] == "cancelled"
    assert [v[1] for v in calls] == ["search"]


def test_private_mode_and_wrong_login_never_reveal_a_comparison(desk):
    r, who, chat, calls, _ = desk
    svc = r.flight_bookings
    q = svc.prepare(FlightQuery.model_validate(BASE))["sandbox_quote"]
    row = svc.attach(q, "personal", who, chat)
    other = {"kind": "owner", "session": r.store.create_owner_session()}
    with pytest.raises(DomainError, match="FLIGHT_NOT_FOUND"):
        svc.decide(choose(row), other, chat.id)
    with r.store.connection(write=True) as db:
        db.execute(
            "UPDATE settings SET data=json_set(data,'$.hide_private',json('true')),version=version+1"
        )
        r.store.bump(db)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        svc.prepare(FlightQuery.model_validate(BASE))
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        svc.decide(choose(row), who, chat.id)
    assert [v[1] for v in calls] == ["search"]


def test_ordinary_session_choice_cannot_drop_the_local_calendar_condition(desk):
    r, _, _, calls, app = desk
    protocol = install_session_protocol(r)
    c = TestClient(app)
    assert c.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success

    def ask(key, txt, **fields):
        return c.post(
            "/api/assistant/messages",
            json={"message": txt, "language": "zh", **fields},
            headers={"X-Desk-Request": "1", "X-Operation-Id": key},
        ).json()

    event(r, DAY + "T09:00", DAY + "T10:00")
    protocol.next_calls = [
        ("sandbox_flight_quote", BASE | {"flight_number": "FA101", "max_hkd": 50})
    ]
    first = ask("initial", "查 FA101，避开我的日程")
    assert first["flight_alternatives"]["requested_calendar_fit"] == "conflict"
    event(r, DAY + "T18:40", DAY + "T18:55")
    protocol.next_calls = [
        (
            "sandbox_flight_quote",
            {**BASE, "flight_number": "FA104", "avoid_calendar_conflicts": False},
        )
    ]
    answer = ask(
        "pick",
        "选 FA104，仍要避开桌面日程",
        flight_calendar_requested=True,
        conversation_id=first["conversation_id"],
    )
    row = answer["flight_booking"]
    assert row["calendar_fit"] == "conflict" and row["approved_minor"] is None
    assert PRIVATE not in json.dumps([protocol.creations, protocol.functions, protocol.followups])
    assert all(c[1] == "search" for c in calls)


def test_clear_fare_can_be_approved_once_and_legacy_fares_keep_their_behavior(desk, monkeypatch):
    r, who, chat, calls, _ = desk
    svc = r.flight_bookings
    submitted = []

    def submit(q, key, scenario):
        submitted.append(key)
        return {
            "sandbox": True,
            "booking_id": "sb_dev_one",
            "offer": {"search_id": q["search_id"], "offer_id": q["offer_id"]},
            "held": {
                "currency": "HKD",
                "amount": q["total_minor"] / 100,
                "card": {"last4": "4242"},
            },
            "charged": 0,
        }

    monkeypatch.setattr(svc.provider, "submit", submit)
    args = FlightQuery.model_validate(BASE | {"flight_number": "FA104"})
    first = svc.attach(svc.prepare(args)["sandbox_quote"], "approved-check", who, chat)
    assert svc.decide(choose(first), who, chat.id)["state"] == "processing"
    assert svc.decide(choose(first), who, chat.id)["state"] == "processing" and len(submitted) == 1
    event(r, DAY + "T18:45", DAY + "T19:00")
    legacy = svc.attach(
        svc.prepare(args.model_copy(update={"avoid_calendar_conflicts": False}))["sandbox_quote"],
        "unchecked-legacy",
        who,
        chat,
    )
    assert "calendar_fit" not in legacy
    assert (
        svc.decide(choose(legacy), who, chat.id)["approved_minor"] == 4700 and len(submitted) == 2
    )


def test_calendar_change_does_not_accept_a_reprice_or_prevent_decline(desk, monkeypatch):
    r, who, chat, _, _ = desk
    svc = r.flight_bookings
    q = svc.prepare(FlightQuery.model_validate(BASE | {"flight_number": "FA104"}))["sandbox_quote"]
    original = svc.attach(q, "reprice-gate", who, chat)
    row = svc._get(original["id"], chat.owner, chat.id)
    deadline = int((r.store.clock().timestamp() + 600) * 1000)
    question = {"round": 1, "old": 4700, "new": 4900, "expires": deadline}
    row.update(
        approved=4700, remote="sb_dev_price", state="reprice", question=question, next_read=0
    )
    svc._save(row)
    record = {
        "sandbox": True,
        "booking_id": "sb_dev_price",
        "offer": {k: q[k] for k in ("search_id", "offer_id")},
        "currency": "HKD",
        "card_last4": "4242",
        "state": "booking_in_progress",
        "terminal": False,
        "question": {
            "kind": "price_change",
            "round": 1,
            "expires_at_ms": deadline,
            "price_change": {"old_total": 47, "new_total": 49, "currency": "HKD"},
        },
    }
    decisions = []
    monkeypatch.setattr(svc.provider, "status", lambda ident: record)

    def answer(ident, rnd, agree):
        decisions.append(agree)
        return {"sandbox": True, "ok": True}

    monkeypatch.setattr(svc.provider, "answer", answer)
    shown = svc.read(row["id"], chat.owner, chat.id)
    assert shown["review_minor"] == 4900
    event(r, DAY + "T18:45", DAY + "T19:00")
    blocked = svc.decide(choose(shown), who, chat.id)
    assert (
        blocked["calendar_fit"] == "conflict"
        and blocked["approved_minor"] == 4700
        and not decisions
    )
    svc.decide(choose(blocked, "decline"), who, chat.id)
    assert decisions == [False]


def test_layover_counts_and_unknown_flight_time_never_looks_free(desk):
    r, _, _, _, _ = desk
    first = leg("QA1", DAY + "T06:30", DAY + "T10:45", "HKG", "HND")
    second = leg("QA2", DAY + "T12:30", DAY + "T14:00", "HND", "ICN")
    event(r, DAY + "T11:00", DAY + "T11:35", timezone="Asia/Tokyo")
    with r.store.connection() as db:
        assert check_itineraries(
            r.store, db, [{"segments": [first, second]}, {"segments": [dict(first, origin="ZZZ")]}]
        ) == ["conflict", "unknown"]


def test_departure_day_uses_the_departure_airport_even_when_the_desk_has_crossed_midnight():
    from desk.flight_booking.timetable import departure_day

    instant = datetime(2026, 11, 21, 17, 30, tzinfo=UTC)
    assert departure_day(instant, "LAX") == date(2026, 11, 21)
    assert departure_day(instant, "HKG") == date(2026, 11, 22)
    assert published_time("2026-11-29 18:30", "HKG") == "2026-11-29T18:30"
