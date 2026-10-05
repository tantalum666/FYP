from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.schemas import EventAction
from desk.store import DomainError, Store


@pytest.fixture
def env(tmp_path):
    clock = [datetime(2026, 9, 29, 1, 0, tzinfo=UTC)]
    app = create_app(
        tmp_path / "isolated",
        clock=lambda: clock[0],
        password="Calendar-test-only!",
        scheduler=False,
    )
    with TestClient(app) as client:
        client.headers["X-Desk-Request"] = "1"
        assert (
            client.post(
                "/api/session", json={"username": "owner", "password": "Calendar-test-only!"}
            ).status_code
            == 200
        )
        yield client, app.state.store, clock


def event(**updates):
    return {
        "title": "Planning",
        "start_local": "2026-09-29T10:00",
        "end_local": "2026-09-29T11:00",
        "timezone": "Asia/Hong_Kong",
        "all_day": False,
        "calendar": "study",
        "color": "lavender",
        "visibility": "private",
        "busy": True,
        "location": "",
        "notes": "",
        "recurrence": {"frequency": "none", "interval": 1, "until": None},
        "reminder_minutes": [10],
        **updates,
    }


def post(client, path, body, key=None):
    return client.post("/api" + path, json=body, headers={"X-Operation-Id": key or uuid4().hex})


def create(client, document=None, dates=None, key=None):
    return post(
        client, "/events", {"event": document or event(), "additional_dates": dates or []}, key
    )


def calendar(client, start="2026-09-28T00:00:00Z", end="2026-10-05T00:00:00Z"):
    response = client.get("/api/calendar", params={"start": start, "end": end})
    assert response.status_code == 200, response.text
    return response.json()


def action(client, occurrence, kind, **extra):
    return post(
        client,
        f"/events/{occurrence['id']}/actions",
        {
            "action": kind,
            "expected_version": occurrence["version"],
            "scope": "occurrence",
            "occurrence_key": occurrence["occurrence_key"],
            **extra,
        },
    )


def test_session_authorization_and_logout(env):
    client, _, _ = env
    assert client.delete("/api/session").status_code == 200
    for path in [
        "/api/calendar?start=2026-09-29T00:00Z&end=2026-09-30T00:00Z",
        "/api/records",
        "/api/revision",
    ]:
        assert client.get(path).status_code == 401
    assert create(client).status_code == 401
    assert (
        client.post("/api/session", json={"username": "owner", "password": "wrong"}).status_code
        == 401
    )


def test_cookie_and_request_boundary(env):
    client, _, _ = env
    assert post(client, "/events", {"event": event()}, "one").status_code == 200
    assert (
        client.post(
            "/api/events", json={"event": event()}, headers={"X-Desk-Request": ""}
        ).status_code
        == 403
    )
    assert client.get("/api/calendar", headers={"Origin": "https://example.org"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400


def test_create_persists_after_store_reopen(env):
    client, store, clock = env
    response = create(client)
    assert response.status_code == 200
    reopened = Store(store.directory, clock=lambda: clock[0])
    snapshot = reopened.snapshot(
        datetime(2026, 9, 29, tzinfo=UTC), datetime(2026, 9, 30, tzinfo=UTC)
    )
    assert snapshot["occurrences"][0]["title"] == "Planning"
    assert snapshot["occurrences"][0]["start"] == "2026-09-29T02:00:00.000000Z"
    assert snapshot["device"]["camera"] == "not_connected"


def test_batch_and_retry_are_atomic_and_repeat_safe(env):
    client, _, _ = env
    dates = ["2026-09-30", "2026-10-02"]
    first = create(client, dates=dates, key="batch")
    second = create(client, dates=dates, key="batch")
    assert first.json() == second.json()
    assert len(first.json()["event_ids"]) == 3
    occurrences = calendar(client)["occurrences"]
    assert {o["start_local"][:10] for o in occurrences} == {
        "2026-09-29",
        "2026-09-30",
        "2026-10-02",
    }
    assert len({o["batch_id"] for o in occurrences}) == 1


def test_invalid_batch_dst_date_does_not_partially_save(env):
    client, _, _ = env
    document = event(
        start_local="2026-03-07T02:30", end_local="2026-03-07T03:30", timezone="America/New_York"
    )
    response = create(client, document, dates=["2026-03-08"])
    assert response.status_code == 422
    assert calendar(client)["event_count"] == 0


def test_same_operation_id_different_payload_is_rejected(env):
    client, _, _ = env
    assert create(client, key="stable").status_code == 200
    assert create(client, event(title="Other"), key="stable").status_code == 409
    assert calendar(client)["event_count"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "   "},
        {"end_local": "2026-09-29T09:59"},
        {"timezone": "Mars/Station"},
        {"start_local": "2026-09-29T10:00Z"},
        {"reminder_minutes": [-1]},
        {"reminder_minutes": [10081]},
        {"recurrence": {"frequency": "weekly", "interval": 0, "until": None}},
        {"all_day": True},
        {"end_local": "2026-11-01T10:00"},
        {
            "start_local": "2026-03-08T02:30",
            "end_local": "2026-03-08T03:30",
            "timezone": "America/New_York",
        },
        {
            "start_local": "2026-11-01T01:30",
            "end_local": "2026-11-01T02:30",
            "timezone": "America/New_York",
        },
    ],
)
def test_invalid_calendar_inputs_are_rejected(env, changes):
    client, _, _ = env
    assert create(client, event(**changes)).status_code == 422
    assert calendar(client)["event_count"] == 0


@pytest.mark.parametrize(
    "dates,recurrence",
    [
        (["2026-09-30", "2026-09-30"], "none"),
        (["2026-09-29"], "none"),
        (["2026-09-30"], "weekly"),
    ],
)
def test_batch_selection_rules(env, dates, recurrence):
    client, _, _ = env
    assert (
        create(
            client,
            event(recurrence={"frequency": recurrence, "interval": 1, "until": None}),
            dates=dates,
        ).status_code
        == 422
    )


def test_weekly_repeat_until_includes_last_date_only(env):
    client, _, _ = env
    document = event(
        start_local="2026-09-29T00:00",
        end_local="2026-09-30T00:00",
        all_day=True,
        recurrence={"frequency": "daily", "interval": 1, "until": "2026-10-01"},
    )
    assert create(client, document).status_code == 200
    assert [o["start_local"][:10] for o in calendar(client)["occurrences"]] == [
        "2026-09-29",
        "2026-09-30",
        "2026-10-01",
    ]


def test_monthly_end_of_month_skips_invalid_dates(env):
    client, _, _ = env
    create(
        client,
        event(
            start_local="2026-01-31T10:00",
            end_local="2026-01-31T11:00",
            recurrence={"frequency": "monthly", "interval": 1, "until": None},
        ),
    )
    rows = calendar(client, "2026-02-01T00:00Z", "2026-04-01T00:00Z")["occurrences"]
    assert [o["start_local"][:10] for o in rows] == ["2026-03-31"]


def test_leap_anniversary_does_not_silently_change_date(env):
    client, _, _ = env
    create(
        client,
        event(
            start_local="2024-02-29T10:00",
            end_local="2024-02-29T11:00",
            recurrence={"frequency": "yearly", "interval": 1, "until": None},
        ),
    )
    assert calendar(client, "2027-02-01T00:00Z", "2027-03-01T00:00Z")["occurrences"] == []
    assert (
        calendar(client, "2028-02-01T00:00Z", "2028-03-01T00:00Z")["occurrences"][0]["start_local"][
            :10
        ]
        == "2028-02-29"
    )


def test_occurrence_update_preserves_series_and_can_move_into_window(env):
    client, _, _ = env
    create(client, event(recurrence={"frequency": "weekly", "interval": 1, "until": None}))
    initial = calendar(client)["occurrences"][0]
    moved = event(
        title="Moved meeting", start_local="2026-10-08T12:00", end_local="2026-10-08T13:00"
    )
    assert action(client, initial, "update", event=moved).status_code == 200
    assert calendar(client)["occurrences"] == []
    rows = calendar(client, "2026-10-05T00:00Z", "2026-10-12T00:00Z")["occurrences"]
    assert [o["title"] for o in rows] == ["Planning", "Moved meeting"]
    assert rows[1]["occurrence_key"] == "2026-09-29T10:00"


def test_cancel_one_occurrence_preserves_following_weeks(env):
    client, _, _ = env
    create(client, event(recurrence={"frequency": "weekly", "interval": 1, "until": None}))
    initial = calendar(client)["occurrences"][0]
    assert action(client, initial, "delete").status_code == 200
    assert calendar(client)["occurrences"] == []
    assert len(calendar(client, "2026-10-05T00:00Z", "2026-10-12T00:00Z")["occurrences"]) == 1


def test_complete_and_reopen_one_instance(env):
    client, _, _ = env
    create(client, event(recurrence={"frequency": "daily", "interval": 1, "until": "2026-10-01"}))
    first = calendar(client)["occurrences"][0]
    assert action(client, first, "complete").status_code == 200
    rows = calendar(client)["occurrences"]
    assert [o["completed"] for o in rows] == [True, False, False]
    assert action(client, rows[0], "reopen").status_code == 200
    assert not calendar(client)["occurrences"][0]["completed"]


def test_series_with_exceptions_cannot_lose_occurrence_identity(env):
    client, _, _ = env
    create(client, event(recurrence={"frequency": "weekly", "interval": 1, "until": None}))
    first = calendar(client)["occurrences"][0]
    action(client, first, "complete")
    first = calendar(client)["occurrences"][0]
    changed = event(
        start_local="2026-09-30T10:00",
        end_local="2026-09-30T11:00",
        recurrence={"frequency": "weekly", "interval": 1, "until": None},
    )
    response = action(client, first, "update", scope="series", event=changed)
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "SERIES_HAS_EXCEPTIONS"
    )
    assert calendar(client)["occurrences"][0]["completed"]


def test_concurrent_edits_have_one_winner(env):
    client, store, _ = env
    create(client)
    original = calendar(client)["occurrences"][0]

    def change(name):
        payload = EventAction(
            action="update", scope="series", expected_version=1, event=event(title=name)
        )
        try:
            return store.event_action(original["id"], payload, uuid4().hex)
        except DomainError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, ["A", "B"]))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert "VERSION_CONFLICT" in results
    assert calendar(client)["occurrences"][0]["version"] == 2


def test_overlap_and_touching_boundaries(env):
    client, _, _ = env
    create(client)
    create(
        client,
        event(title="Overlapping", start_local="2026-09-29T10:30", end_local="2026-09-29T11:00"),
    )
    create(
        client,
        event(title="Adjacent", start_local="2026-09-29T11:00", end_local="2026-09-29T12:00"),
    )
    create(client, event(title="Free time", busy=False))
    rows = {o["title"]: o for o in calendar(client)["occurrences"]}
    assert len(rows["Planning"]["conflicts"]) == 1
    assert rows["Adjacent"]["conflicts"] == [] and rows["Free time"]["conflicts"] == []


def test_cross_midnight_event_appears_in_both_days(env):
    client, _, _ = env
    create(client, event(start_local="2026-09-29T23:30", end_local="2026-09-30T00:30"))
    for start, end in [
        ("2026-09-28T16:00Z", "2026-09-29T16:00Z"),
        ("2026-09-29T16:00Z", "2026-09-30T16:00Z"),
    ]:
        assert len(calendar(client, start, end)["occurrences"]) == 1


def test_all_day_stays_on_calendar_date_after_timezone_change(env):
    client, _, _ = env
    create(
        client, event(start_local="2026-09-29T00:00", end_local="2026-09-30T00:00", all_day=True)
    )
    assert (
        post(
            client,
            "/settings",
            {"expected_version": 1, "timezone": "America/New_York", "hide_private": False},
        ).status_code
        == 200
    )
    rows = calendar(client, "2026-09-29T04:00Z", "2026-09-30T04:00Z")["occurrences"]
    assert rows[0]["start"] == "2026-09-29T04:00:00.000000Z"
    assert calendar(client, "2026-09-28T04:00Z", "2026-09-29T04:00Z")["occurrences"] == []


def test_privacy_projection_covers_events_records_and_reminders(env):
    client, store, clock = env
    create(
        client,
        event(
            title="Secret title",
            location="Secret room",
            notes="Secret notes",
            start_local="2026-09-29T09:10",
            end_local="2026-09-29T10:10",
        ),
    )
    post(
        client,
        "/settings",
        {"expected_version": 1, "timezone": "Asia/Hong_Kong", "hide_private": True},
    )
    serialized = str(calendar(client)) + client.get("/api/records").text
    for value in ["Secret title", "Secret room", "Secret notes"]:
        assert value not in serialized
    assert calendar(client)["occurrences"][0]["redacted"]
    assert calendar(client)["reminders"][0]["redacted"]


def test_reminder_due_snooze_and_ack_are_repeat_safe(env):
    client, store, clock = env
    create(client, event(start_local="2026-09-29T09:15", end_local="2026-09-29T10:15"))
    assert calendar(client)["reminders"] == []
    clock[0] += timedelta(minutes=5)
    store.tick()
    reminder = calendar(client)["reminders"][0]
    payload = {"action": "snooze", "expected_version": reminder["version"], "minutes": 10}
    one = post(client, f"/reminders/{reminder['id']}/actions", payload, "snooze")
    two = post(client, f"/reminders/{reminder['id']}/actions", payload, "snooze")
    assert one.json() == two.json()
    clock[0] += timedelta(minutes=9)
    store.tick()
    assert calendar(client)["reminders"][0]["status"] == "snoozed"
    clock[0] += timedelta(minutes=1)
    store.tick()
    reminder = calendar(client)["reminders"][0]
    assert reminder["status"] == "due"
    assert (
        post(
            client,
            f"/reminders/{reminder['id']}/actions",
            {"action": "acknowledge", "expected_version": reminder["version"]},
        ).status_code
        == 200
    )
    store.tick()
    assert calendar(client)["reminders"] == []


def test_editing_title_does_not_repeat_acknowledged_reminder(env):
    client, store, _ = env
    create(client, event(start_local="2026-09-29T09:10", end_local="2026-09-29T10:10"))
    snapshot = calendar(client)
    reminder = snapshot["reminders"][0]
    post(
        client,
        f"/reminders/{reminder['id']}/actions",
        {"action": "acknowledge", "expected_version": reminder["version"]},
    )
    changed = event(title="Renamed", start_local="2026-09-29T09:10", end_local="2026-09-29T10:10")
    action(client, snapshot["occurrences"][0], "update", scope="series", event=changed)
    store.tick()
    assert calendar(client)["reminders"] == []


def test_reschedule_invalidates_old_due_and_creates_correct_new_time(env):
    client, store, clock = env
    create(client, event(start_local="2026-09-29T09:10", end_local="2026-09-29T10:10"))
    old = calendar(client)
    old_reminder = old["reminders"][0]
    changed = event(start_local="2026-09-29T10:10", end_local="2026-09-29T11:10")
    assert (
        action(client, old["occurrences"][0], "update", scope="series", event=changed).status_code
        == 200
    )
    assert calendar(client)["reminders"] == []
    assert (
        post(
            client,
            f"/reminders/{old_reminder['id']}/actions",
            {"action": "acknowledge", "expected_version": old_reminder["version"]},
        ).status_code
        == 409
    )
    clock[0] += timedelta(hours=1)
    store.tick()
    assert len(calendar(client)["reminders"]) == 1


def test_completion_cancels_reminder(env):
    client, _, _ = env
    create(client, event(start_local="2026-09-29T09:10", end_local="2026-09-29T10:10"))
    snap = calendar(client)
    assert action(client, snap["occurrences"][0], "complete").status_code == 200
    assert calendar(client)["reminders"] == []


def test_reminder_survives_restart_without_duplication(env):
    client, store, clock = env
    create(client, event(start_local="2026-09-29T09:10", end_local="2026-09-29T10:10"))
    first = calendar(client)["reminders"]
    reopened = Store(store.directory, clock=lambda: clock[0])
    reopened.tick()
    reopened.tick()
    assert calendar(client)["reminders"] == first


def test_long_offline_gap_records_missed_not_live_alarm(env):
    client, store, clock = env
    create(client)
    clock[0] += timedelta(hours=4)
    store.tick()
    assert calendar(client)["reminders"] == []
    with store.connection() as conn:
        assert conn.execute("SELECT status FROM reminders").fetchone()[0] == "missed"


def test_dst_recurring_gap_is_skipped(env):
    client, _, _ = env
    create(
        client,
        event(
            start_local="2026-03-07T02:30",
            end_local="2026-03-07T03:30",
            timezone="America/New_York",
            recurrence={"frequency": "daily", "interval": 1, "until": "2026-03-09"},
        ),
    )
    rows = calendar(client, "2026-03-07T00:00Z", "2026-03-10T00:00Z")["occurrences"]
    assert [r["start_local"][:10] for r in rows] == ["2026-03-07", "2026-03-09"]


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-01-01T00:00Z", "2026-12-31T00:00Z"),
        ("2026-09-29T00:00", "2026-09-30T00:00"),
        ("2026-09-30T00:00Z", "2026-09-29T00:00Z"),
    ],
)
def test_invalid_query_ranges_are_explicit(env, start, end):
    client, _, _ = env
    assert client.get("/api/calendar", params={"start": start, "end": end}).status_code == 422


def test_delete_entire_series_preserves_audit_and_removes_occurrences(env):
    client, _, _ = env
    create(client, event(recurrence={"frequency": "weekly", "interval": 1, "until": None}))
    row = calendar(client)["occurrences"][0]
    assert action(client, row, "delete", scope="series").status_code == 200
    assert calendar(client)["event_count"] == 0
    records = client.get("/api/records").json()["records"]
    assert [r["action"] for r in records] == ["delete", "created"]


def test_unknown_or_cancelled_instance_cannot_be_edited(env):
    client, _, _ = env
    create(client)
    row = calendar(client)["occurrences"][0]
    assert action(client, row, "complete", occurrence_key="2026-10-01T10:00").status_code == 422
    action(client, row, "delete")
    assert action(client, {**row, "version": 2}, "update", event=event()).status_code == 409


def test_backup_contains_saved_calendar(env, tmp_path):
    client, store, _ = env
    create(client)
    backup = tmp_path / "backup.sqlite3"
    store.backup(backup)
    import sqlite3

    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 1
