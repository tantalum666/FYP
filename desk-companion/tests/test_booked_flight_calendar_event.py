from copy import deepcopy
from datetime import UTC, datetime

import pytest

from desk.calendar import wall_to_utc
from desk.flight_booking.calendar_event import build_calendar_event
from desk.store import DomainError


def _leg(flight, origin, destination, departs, arrives):
    return {
        "flight": flight,
        "origin": origin,
        "destination": destination,
        "departs": departs,
        "arrives": arrives,
    }


@pytest.fixture
def row():
    return {
        "state": "completed",
        "quote": {
            "segments": [
                _leg("CX504", "HKG", "NRT", "2026-07-04T23:45", "2026-07-05T05:10"),
                _leg("JL062", "NRT", "LAX", "2026-07-05T17:20+09:00", "2026-07-05T11:35"),
            ],
            "adults": 2,
            "currency": "HKD",
            "total_minor": 412345,
            "offer_id": "private-supplier-offer",
        },
        "approved": 456789,
        "capture": 456789,
        "pnr": "Q7W8E9",
        "id": "private-booking-id",
        "remote": "private-provider-reference",
        "passengers": [{"name": "Riley Example", "email": "riley@example.test"}],
    }


def _assert_unverified(row, zone="Asia/Hong_Kong"):
    with pytest.raises(DomainError, match="FLIGHT_CALENDAR_UNVERIFIED"):
        build_calendar_event(row, zone)


def test_approved_fare_increase_drafts_one_private_event_for_full_itinerary(row):
    before = deepcopy(row)
    draft = build_calendar_event(row, "Europe/London")
    assert row == before
    event = draft.event
    assert event.timezone == "Europe/London"
    instants = tuple(
        wall_to_utc(w, event.timezone, reject_ambiguous=True)
        for w in (event.start_local, event.end_local)
    )
    assert instants == (datetime(2026, 7, 4, 15, 45, tzinfo=UTC), datetime(2026, 7, 5, 18, 35, tzinfo=UTC))
    assert "test itinerary" in event.title.lower()
    for code in ("HKG", "LAX", "CX504", "JL062"):
        assert code in event.title
    assert event.visibility == "private" and event.busy and not event.all_day
    assert event.reminder_minutes == []
    assert draft.additional_dates == [] and event.recurrence.frequency == "none"

    payload = draft.model_dump_json()
    for secret in (
        row["pnr"], row["id"], row["remote"], row["quote"]["offer_id"],
        "Riley Example", "riley@example.test", "HKD", "412345", "456789", "4,567.89",
    ):
        assert secret not in payload


def test_locator_coinciding_with_a_designator_is_not_copied(row):
    row["pnr"] = row["quote"]["segments"][0]["flight"] = "CX4567"
    draft = build_calendar_event(row, "UTC")
    assert row["pnr"] not in draft.model_dump_json()
    assert "4567" in draft.event.title


@pytest.mark.parametrize("patch", [
    {"state": "reprice"}, {"pnr": "Q7-8E9"}, {"pnr": "Q7W8E90"},
    {"capture": 412345},  # Matches the old quote, not the exact approval.
    {"approved": 0, "capture": 0}, {"approved": -2, "capture": -2},
    {"approved": True, "capture": 1}, {"approved": 1, "capture": True},
    {"approved": 150.0, "capture": 150}, {"approved": 150, "capture": 150.0},
    {"approved": "150", "capture": "150"},
])
def test_unverified_receipts(row, patch):
    row.update(patch)
    _assert_unverified(row)


def test_missing_capture(row):
    del row["capture"]
    _assert_unverified(row)


@pytest.mark.parametrize("patch", [
    {"currency": "USD"}, {"total_minor": "412345"}, {"adults": True},
    {"segments": []}, {"segments": [None]}, {"segments": [{}]},
])
def test_malformed_or_unsupported_quote(row, patch):
    row["quote"].update(patch)
    _assert_unverified(row)


@pytest.mark.parametrize("patch", [
    {"flight": "JL062 (Riley Example)"},
    {"destination": "private-address", "arrives": "2026-07-05T11:35-07:00"},
    {"origin": "HND"},  # Disconnected from the first arrival.
    {"arrives": "2026-08-06T11:35"},  # Outside the supported calendar span.
])
def test_unsupported_itinerary(row, patch):
    row["quote"]["segments"][-1].update(patch)
    _assert_unverified(row)


@pytest.mark.parametrize(("day", "clock"), [("2025-03-09", "02:30"), ("2025-11-02", "01:30")])
def test_unresolved_airport_time_even_at_an_intermediate_stop(row, day, clock):
    row["quote"]["segments"] = [
        _leg("CX840", "HKG", "JFK", f"{day}T00:00+08:00", f"{day}T{clock}"),
        _leg("AA101", "JFK", "LAX", f"{day}T08:00", f"{day}T12:00"),
    ]
    _assert_unverified(row, "UTC")


def test_desk_fold_crossing_uses_utc_for_both_instants(row):
    # New York would show 01:50 EDT followed by 01:30 EST.
    row["quote"]["segments"] = [
        _leg("BR852", "HKG", "TPE", "2025-11-02T13:50+08:00", "2025-11-02T14:30+08:00"),
    ]
    event = build_calendar_event(row, "America/New_York").event
    assert event.timezone == "UTC"
    assert event.start_local == datetime(2025, 11, 2, 5, 50)
    assert event.end_local == datetime(2025, 11, 2, 6, 30)


@pytest.mark.parametrize(("index", "bound", "suffix"), [
    (0, "departs", ":01"), (-1, "arrives", ":00.000001"), (0, "departs", ":00.0000001"),
])
def test_subminute_bounds_are_not_rounded(row, index, bound, suffix):
    row["quote"]["segments"][index][bound] += suffix
    _assert_unverified(row)


@pytest.mark.parametrize("zone", ["Invalid/Desk", "", None])
def test_bad_desk_zone_is_not_a_reason_to_guess_utc(row, zone):
    _assert_unverified(row, zone)
