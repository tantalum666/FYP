"""Offline trip quotes. A search result is not a hold, a failure is not a ticket."""

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

HEADERS = {"X-Desk-Request": "1"}
TASK_FIELDS = (
    "title",
    "timezone",
    "due_local",
    "status",
    "next_step",
    "waiting_for",
    "steps",
    "visibility",
    "follow_up_enabled",
    "check_in_local",
    "interval_minutes",
)


def headers(operation_id=None):
    body = dict(HEADERS)
    if operation_id is not None:
        body["X-Operation-Id"] = operation_id
    return body


def quote(**overrides):
    body = {
        "event_id": "quote-1",
        "seq": 1,
        "observed_at": "2026-11-10T01:00:00Z",
        "kind": "quote",
        "origin": "HKG",
        "destination": "TYO",
        "depart_local": "2026-12-01T09:00",
        "arrive_local": "2026-12-02T14:30",
        "timezone": "Asia/Hong_Kong",
        "arrive_timezone": "Asia/Tokyo",
        "passengers": 2,
        "baggage_kg": 20,
        "total_cents": 208000,
        "fare_rules": "Changeable before departure.",
    }
    body.update(overrides)
    return body


def event(event_id, seq, kind, **fields):
    body = {
        "event_id": event_id,
        "seq": seq,
        "observed_at": f"2026-11-10T01:{seq:02d}:00Z",
        "kind": kind,
    }
    body.update(fields)
    return body


def write_fixture(directory, fixture_id, events):
    directory.mkdir(parents=True, exist_ok=True)
    body = {
        "fixture_id": fixture_id,
        "itinerary_id": fixture_id,
        "carrier": "offline-fixture",
        "currency": "HKD",
        "events": events,
    }
    (directory / f"{fixture_id}.json").write_text(json.dumps(body), encoding="utf-8")


def build(tmp_path, monkeypatch):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setenv("DESK_TRAVEL_FIXTURES", str(fixtures))
    moment = [datetime(2026, 11, 10, 1, tzinfo=UTC)]
    app = create_app(tmp_path / "runtime", password="fixture", scheduler=False, clock=lambda: moment[0])
    return app, fixtures, moment


def login(app):
    client = TestClient(app)
    response = client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    return client


def connect(client, fixture_id, operation_id="connect-trip"):
    response = client.post(
        "/api/trips/connections",
        json={"fixture_id": fixture_id},
        headers=headers(operation_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["purchase"] == "not_performed"
    return body


def sync(client, connection_id, payload=None):
    response = client.post(
        f"/api/trips/connections/{connection_id}/sync",
        json={} if payload is None else payload,
        headers=HEADERS,
    )
    return response


def snapshot(client, connection_id):
    response = client.get(f"/api/trips/connections/{connection_id}")
    assert response.status_code == 200, response.text
    return response.json()


def tasks_of(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200, response.text
    return response.json()["tasks"]


def task_detail(client, task_id):
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200, response.text
    return response.json()


def trip_notices(client):
    response = client.get("/api/notices")
    assert response.status_code == 200, response.text
    return [item for item in response.json()["notices"] if item["kind"] == "trip"]


def hold(client, connection_id, quote_id, version, operation_id, extra=None):
    body = {"quote_id": quote_id, "expected_task_version": version}
    if extra:
        body.update(extra)
    return client.post(
        f"/api/trips/connections/{connection_id}/holds",
        json=body,
        headers=headers(operation_id),
    )


def operation_row(app, key):
    with app.state.runtime.store.connection() as conn:
        return conn.execute("SELECT * FROM operations WHERE id=?", (key,)).fetchone()


def test_quote_is_not_a_hold_and_a_second_connect_stays_on_one_task(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    first = connect(client, "hkg-tyo")
    connection_id = first["connection"]["id"]
    assert first["saved"] is True
    assert first["itinerary"] is None
    read = sync(client, connection_id)
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["completed"] is True
    assert body["purchase"] == "not_performed"
    assert body["applied"][0]["outcome"] == "recorded"
    view = snapshot(client, connection_id)
    assert view["itinerary"]["booking_state"] == "quoted"
    assert view["itinerary"]["held_covers"] is False
    assert view["itinerary"]["ticketed"] is False
    assert view["itinerary"]["live_ticket"] is False
    assert view["itinerary"]["terms"]["arrive_local"] == "2026-12-02T14:30"
    assert view["itinerary"]["terms"]["arrive_timezone"] == "Asia/Tokyo"
    assert len(tasks_of(client)) == 1
    again = sync(client, connection_id)
    assert again.json()["applied"] == []
    assert len(trip_notices(client)) == 1
    second = connect(client, "hkg-tyo", "connect-again")
    assert second["saved"] is False
    assert second["connection"]["id"] == connection_id
    assert len(tasks_of(client)) == 1
    shopping = client.get("/api/shopping/connections")
    assert shopping.status_code == 200
    assert shopping.json()["checkout"] == "not_performed"


def test_omitted_task_fields_survive_and_null_does_not_clear(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    view = snapshot(client, connection_id)
    task_id = view["connection"]["task_id"]
    current = task_detail(client, task_id)["task"]
    updated = client.post(
        f"/api/tasks/{task_id}/actions",
        json={
            "action": "update",
            "expected_version": current["version"],
            "task": {**{field: current[field] for field in TASK_FIELDS}, "next_step": "Pack the bag"},
        },
        headers=headers("set-step"),
    )
    assert updated.status_code == 200, updated.text
    write_fixture(
        fixtures,
        "hkg-tyo",
        [quote(), event("price-1", 2, "reprice", total_cents=226000)],
    )
    priced = sync(client, connection_id)
    assert priced.status_code == 200, priced.text
    kept = task_detail(client, task_id)["task"]
    assert kept["next_step"] == "Pack the bag"
    assert kept["waiting_for"] == ""
    assert kept["title"] == "HKG to TYO"
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            event("price-1", 2, "reprice", total_cents=226000),
            event("price-2", 3, "reprice", total_cents=226000, next_step=None),
        ],
    )
    rejected = sync(client, connection_id)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "TRIP_FIXTURE_INVALID"
    assert snapshot(client, connection_id)["connection"]["cursor_seq"] == 2
    assert task_detail(client, task_id)["task"]["next_step"] == "Pack the bag"
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            event("price-1", 2, "reprice", total_cents=226000),
            event("wait-1", 3, "reprice", total_cents=230000, waiting_for="Confirm the new fare"),
        ],
    )
    moved = sync(client, connection_id)
    assert moved.status_code == 200, moved.text
    after = task_detail(client, task_id)["task"]
    assert after["next_step"] == "Pack the bag"
    assert after["waiting_for"] == "Confirm the new fare"


def test_rejected_hold_is_not_success_and_the_same_key_can_retry(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    view = snapshot(client, connection_id)
    quote_id = view["itinerary"]["quote_id"]
    version = view["task_version"]
    stale = hold(client, connection_id, "a" * 64, version, "hold-1")
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "TRIP_QUOTE_CHANGED"
    assert operation_row(app, "hold-1") is None
    assert snapshot(client, connection_id)["itinerary"]["booking_state"] == "quoted"
    wrong_version = hold(client, connection_id, quote_id, version + 9, "hold-1")
    assert wrong_version.status_code == 409
    assert wrong_version.json()["error"]["code"] == "VERSION_CONFLICT"
    assert operation_row(app, "hold-1") is None
    blank = hold(client, connection_id, quote_id, version, "hold-1", {"next_step": None})
    assert blank.status_code == 422
    assert task_detail(client, view["connection"]["task_id"])["task"]["next_step"] == ""
    approved = hold(client, connection_id, quote_id, version, "hold-1")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["saved"] is True
    assert body["purchase"] == "not_performed"
    assert body["itinerary"]["held_covers"] is True
    assert body["itinerary"]["ticketed"] is False
    replay = hold(client, connection_id, quote_id, version, "hold-1")
    assert replay.status_code == 200
    assert replay.json()["operation_id"] == "hold-1"
    notes = [
        row["note"]
        for row in task_detail(client, view["connection"]["task_id"])["evidence"]
        if "Owner approved" in (row["note"] or "")
    ]
    assert len(notes) == 1
    conflict = hold(
        client, connection_id, quote_id, body["task_version"], "hold-1", {"next_step": "Call the airline"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert task_detail(client, view["connection"]["task_id"])["task"]["next_step"] == ""


def test_reprice_and_payment_failure_are_not_a_ticket(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    view = snapshot(client, connection_id)
    approved = hold(client, connection_id, view["itinerary"]["quote_id"], view["task_version"], "hold-price")
    assert approved.status_code == 200, approved.text
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            event("price-1", 2, "reprice", total_cents=226000),
            event("pay-1", 3, "payment_failed", reason="Card declined"),
            event("ticket-early", 4, "ticketed", covers_quote="b" * 64, receipt_id="fix-ticket-1"),
        ],
    )
    read = sync(client, connection_id)
    assert read.status_code == 200, read.text
    applied = {row["event_id"]: row for row in read.json()["applied"]}
    assert applied["price-1"]["booking_state"] == "quoted"
    assert applied["pay-1"]["booking_state"] == "payment_failed"
    assert applied["ticket-early"]["outcome"] == "blocked"
    view = snapshot(client, connection_id)
    assert view["itinerary"]["held_covers"] is False
    assert view["itinerary"]["approval_stale"] is True
    assert view["itinerary"]["ticketed"] is False
    assert view["itinerary"]["ticket_receipt"] is None
    assert view["itinerary"]["booking_state"] == "payment_failed"
    assert view["purchase"] == "not_performed"
    assert len(tasks_of(client)) == 1
    texts = " ".join(item["body_en"] for item in trip_notices(client))
    assert "not ticketed" in texts.lower() or "not held" in texts.lower()
    assert "No card was charged" in texts


def test_ticket_matches_only_the_approved_quote(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    view = snapshot(client, connection_id)
    quote_id = view["itinerary"]["quote_id"]
    blocked = event("ticket-blocked", 2, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-1")
    write_fixture(fixtures, "hkg-tyo", [quote(), blocked])
    early = sync(client, connection_id)
    assert early.status_code == 200, early.text
    assert early.json()["applied"][0]["outcome"] == "blocked"
    assert snapshot(client, connection_id)["itinerary"]["ticketed"] is False
    approved = hold(client, connection_id, quote_id, view["task_version"], "hold-ticket")
    assert approved.status_code == 200, approved.text
    write_fixture(
        fixtures,
        "hkg-tyo",
        [quote(), blocked, event("ticket-1", 3, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-1")],
    )
    ticket = sync(client, connection_id)
    assert ticket.status_code == 200, ticket.text
    view = snapshot(client, connection_id)
    assert view["itinerary"]["ticketed"] is True
    assert view["itinerary"]["ticket_receipt"] == "fix-ticket-1"
    assert view["itinerary"]["receipt_covers_quote"] is True
    assert view["itinerary"]["live_ticket"] is False
    assert view["purchase"] == "not_performed"
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            blocked,
            event("ticket-1", 3, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-1"),
            event("ticket-2", 4, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-2"),
        ],
    )
    second = sync(client, connection_id)
    assert second.json()["applied"][0]["outcome"] == "blocked"
    assert snapshot(client, connection_id)["itinerary"]["ticket_receipt"] == "fix-ticket-1"
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            blocked,
            event("ticket-1", 3, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-1"),
            event("ticket-2", 4, "ticketed", covers_quote=quote_id, receipt_id="fix-ticket-2"),
            event("shift-1", 5, "schedule_change", arrive_local="2026-12-02T18:00"),
        ],
    )
    changed = sync(client, connection_id)
    assert changed.status_code == 200, changed.text
    view = snapshot(client, connection_id)
    assert view["itinerary"]["booking_state"] == "changed"
    assert view["itinerary"]["ticketed"] is False
    assert view["itinerary"]["ticket_receipt"] == "fix-ticket-1"
    assert view["itinerary"]["receipt_covers_quote"] is False
    assert view["itinerary"]["terms"]["arrive_local"] == "2026-12-02T18:00"
    assert len(tasks_of(client)) == 1


def test_disconnect_gap_conflict_and_restart_keep_one_task(tmp_path, monkeypatch):
    app, fixtures, moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote(), event("shift-1", 3, "schedule_change", depart_local="2026-12-01T11:00")])
    client = login(app)
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    stopped = sync(client, connection_id, {"disconnect_after": 0})
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["completed"] is False
    assert stopped.json()["stopped"] == "disconnected"
    assert stopped.json()["cursor"] == 0
    assert tasks_of(client) == []
    partial = sync(client, connection_id, {"disconnect_after": 1})
    assert partial.json()["completed"] is False
    assert partial.json()["cursor"] == 1
    gapped = sync(client, connection_id)
    assert gapped.json()["completed"] is False
    assert gapped.json()["stopped"] == "gap"
    assert snapshot(client, connection_id)["buffered"] == [{"event_id": "shift-1", "seq": 3}]
    client.close()

    restarted = create_app(
        tmp_path / "runtime", password="fixture", scheduler=False, clock=lambda: moment[0]
    )
    client = login(restarted)
    assert client.get("/api/trips/connections").json()["connections"][0]["id"] == connection_id
    write_fixture(
        fixtures,
        "hkg-tyo",
        [
            quote(),
            event("shift-1", 3, "schedule_change", depart_local="2026-12-01T11:00"),
            event("mid-1", 2, "reprice", total_cents=210000),
        ],
    )
    finished = sync(client, connection_id)
    assert finished.status_code == 200, finished.text
    assert finished.json()["completed"] is True
    assert finished.json()["cursor"] == 3
    assert len(tasks_of(client)) == 1
    task_id = snapshot(client, connection_id)["connection"]["task_id"]
    original = json.loads((fixtures / "hkg-tyo.json").read_text(encoding="utf-8"))
    original["events"][0]["total_cents"] = 1
    (fixtures / "hkg-tyo.json").write_text(json.dumps(original), encoding="utf-8")
    conflict = sync(client, connection_id)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "TRIP_EVENT_CONFLICT"
    assert snapshot(client, connection_id)["connection"]["cursor_seq"] == 3
    assert snapshot(client, connection_id)["connection"]["task_id"] == task_id


def test_revoke_hides_from_other_principals_and_a_bad_itinerary_does_not_advance(
    tmp_path, monkeypatch
):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    stranger = TestClient(app)
    assert stranger.get("/api/trips/connections").status_code == 403
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    enrolled = client.post(
        "/api/devices/enrol-display",
        json={"name": "Fixture screen"},
        headers=headers("enrol-trip"),
    )
    assert enrolled.status_code == 200, enrolled.text
    paired = TestClient(app)
    paired.headers["Authorization"] = "Bearer " + client.cookies.get("desk_companion_device")
    assert paired.get("/api/trips/connections").status_code == 403
    assert paired.post(
        f"/api/trips/connections/{connection_id}/holds",
        json={"quote_id": "c" * 64, "expected_task_version": 1},
        headers=headers("paired-hold"),
    ).status_code == 403
    with app.state.runtime.store.connection() as conn:
        version = app.state.runtime.store.settings(conn)["version"]
    hidden = client.post(
        "/api/settings",
        json={"expected_version": version, "timezone": "Asia/Hong_Kong", "hide_private": True},
        headers=headers("hide-trip"),
    )
    assert hidden.status_code == 200, hidden.text
    assert client.get("/api/trips/connections").status_code == 403
    view = None
    shown = client.post(
        "/api/settings",
        json={"expected_version": version + 1, "timezone": "Asia/Hong_Kong", "hide_private": False},
        headers=headers("show-trip"),
    )
    assert shown.status_code == 200, shown.text
    view = snapshot(client, connection_id)
    assert view["itinerary"]["booking_state"] == "quoted"
    revoked = client.post(
        f"/api/trips/connections/{connection_id}/revocation",
        json={},
        headers=headers("revoke-trip"),
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["completed"] is False
    write_fixture(fixtures, "hkg-tyo", [quote(), event("price-1", 2, "reprice", total_cents=199000)])
    stopped = sync(client, connection_id)
    assert stopped.json()["completed"] is False
    assert stopped.json()["stopped"] == "revoked"
    assert stopped.json()["cursor"] == 1
    assert len(tasks_of(client)) == 1

    write_fixture(
        fixtures,
        "too-early",
        [quote(arrive_local="2026-12-01T08:00", arrive_timezone="Asia/Hong_Kong")],
    )
    early_id = connect(client, "too-early", "connect-early")["connection"]["id"]
    invalid = sync(client, early_id)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "TRIP_ITINERARY_INVALID"
    assert snapshot(client, early_id)["connection"]["cursor_seq"] == 0
    assert snapshot(client, early_id)["connection"]["task_id"] is None
    escaped = client.post(
        "/api/trips/connections",
        json={"fixture_id": "../shopping"},
        headers=headers("escape-trip"),
    )
    assert escaped.status_code == 422
    upper = client.post(
        "/api/trips/connections",
        json={"fixture_id": "HKG-TYO"},
        headers=headers("upper-trip"),
    )
    assert upper.status_code == 422


def test_quiet_hours_deliver_one_notice_after_they_end(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "hkg-tyo", [quote()])
    client = login(app)
    runtime = app.state.runtime
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(quiet_enabled=True, quiet_start="00:00", quiet_end="23:59"),
        ),
        "quiet-trip",
    )
    connection_id = connect(client, "hkg-tyo")["connection"]["id"]
    assert sync(client, connection_id).status_code == 200
    assert trip_notices(client) == []
    with runtime.store.connection() as conn:
        held = conn.execute("SELECT COUNT(*) FROM trip_notice_holds").fetchone()[0]
    assert held == 1
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(quiet_enabled=False),
        ),
        "sound-trip",
    )
    runtime.tick()
    assert len(trip_notices(client)) == 1
    runtime.tick()
    assert len(trip_notices(client)) == 1
    assert "No card was charged" in trip_notices(client)[0]["body_en"]
