"""Owner-approved memory follow-ups. Drafts do not arm. Quiet hours hold one notice."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import TOOLS
from desk.runtime import Runtime
from desk.store import Store
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

SECRET = "The Thursday dentist visit is private"


def _app(tmp_path, when):
    clock = [when]
    app = create_app(
        tmp_path, password="fixture-only", scheduler=False, clock=lambda: clock[0]
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return app, client, clock


def _login(client):
    """Sessions last eight hours of workspace time, so a later check signs in again."""
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )


def _headers(key=None):
    headers = {"X-Desk-Request": "1"}
    if key is not None:
        headers["X-Operation-Id"] = key
    return headers


def _memory(client, body, key):
    response = client.post("/api/memory", json={"body": body}, headers=_headers(key))
    assert response.status_code == 200, response.text
    return response.json()["memory"]


def _rows(runtime):
    with runtime.store.connection() as conn:
        return conn.execute("SELECT * FROM memory_followups ORDER BY id").fetchall()


def _operation(runtime, key):
    with runtime.store.connection() as conn:
        return conn.execute("SELECT * FROM operations WHERE id=?", (key,)).fetchone()


def _channels(runtime):
    text = []
    with runtime.store.connection() as conn:
        for table in ("notice_inbox", "browser_notices", "device_notices"):
            present = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not present:
                continue
            for row in conn.execute(f"SELECT * FROM {table}"):
                text.append(" ".join(str(value) for value in tuple(row)))
    return "\n".join(text)


def _prefs(runtime, **fields):
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(**fields),
        ),
        uuid4().hex,
    )


def test_draft_does_not_arm_and_only_the_owner_can_approve(tmp_path, monkeypatch):
    app, client, _clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    assert all(tool["name"] != "memory_followup" for tool in TOOLS)
    stranger = TestClient(app)
    assert stranger.get("/api/memory-followups").status_code == 403
    assert (
        stranger.post(
            "/api/memory-followups/drafts",
            json={"memory_id": "a" * 32, "due_local": "2026-11-10T08:00"},
            headers=_headers(),
        ).status_code
        == 403
    )
    enrol = client.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers=_headers("pair-followup"),
    )
    assert enrol.status_code == 200
    display = TestClient(app)
    display.headers["Authorization"] = "Bearer " + client.cookies.get("desk_companion_device")
    assert display.get("/api/memory-followups", headers=_headers()).status_code == 403
    assert (
        display.post(
            "/api/memory-followups",
            json={
                "memory_id": "b" * 32,
                "due_local": "2026-11-10T08:00",
                "memory_version": 1,
            },
            headers=_headers("display-approve"),
        ).status_code
        == 403
    )

    fact = _memory(client, SECRET, "remember-dentist")
    draft = client.post(
        "/api/memory-followups/drafts",
        json={"memory_id": fact["id"], "due_local": "2026-11-10T08:00"},
        headers=_headers(),
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["saved"] is False and body["armed"] is False and body["draft"]["armed"] is False
    assert body["draft"]["body"] == SECRET
    assert body["draft"]["timezone"] == "Asia/Hong_Kong"
    assert _rows(runtime) == []

    past = client.post(
        "/api/memory-followups/drafts",
        json={"memory_id": fact["id"], "due_local": "2026-11-09T08:00"},
        headers=_headers(),
    )
    assert past.status_code == 422 and past.json()["error"]["code"] == "FOLLOWUP_TIME_PAST"
    ambiguous = client.post(
        "/api/memory-followups/drafts",
        json={
            "memory_id": fact["id"],
            "due_local": "2026-11-01T01:30",
            "timezone": "America/New_York",
        },
        headers=_headers(),
    )
    assert ambiguous.status_code == 422
    assert ambiguous.json()["error"]["code"] == "FOLLOWUP_TIME_INVALID"
    assert _rows(runtime) == []

    approved = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": body["draft"]["due_local"],
            "timezone": body["draft"]["timezone"],
        },
        headers=_headers("approve-dentist"),
    )
    assert approved.status_code == 200, approved.text
    followup = approved.json()["followup"]
    assert followup["state"] == "pending" and followup["armed"] is True
    assert len(_rows(runtime)) == 1
    again = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T09:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("second-open"),
    )
    assert again.status_code == 409 and again.json()["error"]["code"] == "MEMORY_FOLLOWUP_OPEN"
    assert len(_rows(runtime)) == 1

    other = _memory(client, "A second private fact", "remember-second")
    monkeypatch.setattr("desk.memory_followups.MAX_OPEN", 1)
    limited = client.post(
        "/api/memory-followups",
        json={
            "memory_id": other["id"],
            "memory_version": other["version"],
            "due_local": "2026-11-10T09:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("over-cap"),
    )
    assert limited.status_code == 422
    assert limited.json()["error"]["code"] == "MEMORY_FOLLOWUP_LIMIT"
    assert len(_rows(runtime)) == 1


def test_lost_response_retries_and_a_rejected_confirm_is_not_success(tmp_path):
    app, client, _clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    payload = {
        "memory_id": fact["id"],
        "memory_version": fact["version"],
        "due_local": "2026-11-10T08:00",
        "timezone": "Asia/Hong_Kong",
    }
    rejected = client.post(
        "/api/memory-followups",
        json={**payload, "memory_version": 9},
        headers=_headers("approve-once"),
    )
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "VERSION_CONFLICT"
    assert _rows(runtime) == []
    assert _operation(runtime, "approve-once") is None

    first = client.post("/api/memory-followups", json=payload, headers=_headers("approve-once"))
    second = client.post("/api/memory-followups", json=payload, headers=_headers("approve-once"))
    assert first.status_code == second.status_code == 200
    assert first.json()["followup"]["id"] == second.json()["followup"]["id"]
    assert len(_rows(runtime)) == 1
    conflict = client.post(
        "/api/memory-followups",
        json={**payload, "due_local": "2026-11-10T11:00"},
        headers=_headers("approve-once"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert _rows(runtime)[0]["due_local"] == "2026-11-10T08:00"


def test_omitted_revision_fields_stay_stored(tmp_path):
    app, client, _clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    approved = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T08:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    followup = approved.json()["followup"]
    original_due = followup["due_at"]
    untouched = client.post(
        f"/api/memory-followups/{followup['id']}/revisions",
        json={"expected_version": followup["version"]},
        headers=_headers("revise-empty"),
    )
    assert untouched.status_code == 200, untouched.text
    assert untouched.json()["followup"]["version"] == followup["version"]
    assert untouched.json()["followup"]["due_at"] == original_due
    assert untouched.json()["followup"]["timezone"] == "Asia/Hong_Kong"

    cleared = client.post(
        f"/api/memory-followups/{followup['id']}/revisions",
        json={"expected_version": followup["version"], "timezone": None},
        headers=_headers("revise-null"),
    )
    assert cleared.status_code == 422
    assert cleared.json()["error"]["code"] == "FOLLOWUP_TIME_REQUIRED"
    assert _rows(runtime)[0]["timezone"] == "Asia/Hong_Kong"
    assert _rows(runtime)[0]["version"] == followup["version"]

    moved = client.post(
        f"/api/memory-followups/{followup['id']}/revisions",
        json={"expected_version": followup["version"], "timezone": "UTC"},
        headers=_headers("revise-zone"),
    )
    assert moved.status_code == 200, moved.text
    zoned = moved.json()["followup"]
    assert zoned["timezone"] == "UTC"
    assert zoned["due_local"] == "2026-11-10T08:00"
    assert zoned["due_at"] != original_due
    later = client.post(
        f"/api/memory-followups/{followup['id']}/revisions",
        json={"expected_version": zoned["version"], "due_local": "2026-11-10T09:30"},
        headers=_headers("revise-time"),
    )
    assert later.status_code == 200, later.text
    shifted = later.json()["followup"]
    assert shifted["due_local"] == "2026-11-10T09:30"
    assert shifted["timezone"] == "UTC"
    refused = client.post(
        f"/api/memory-followups/{followup['id']}/resolutions",
        json={"action": "dismiss", "expected_version": shifted["version"]},
        headers=_headers("dismiss-wrong"),
    )
    assert refused.status_code == 422
    dismissed = client.post(
        f"/api/memory-followups/{followup['id']}/resolutions",
        json={"action": "dismissed", "expected_version": shifted["version"]},
        headers=_headers("dismiss"),
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["followup"]["state"] == "dismissed"


def test_raise_reads_the_current_wording_and_keeps_it_off_the_notice(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    approved = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T08:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    followup_id = approved.json()["followup"]["id"]
    corrected = client.post(
        f"/api/memory/{fact['id']}/revisions",
        json={"body": "The Thursday dentist visit moved to Friday", "expected_version": 1},
        headers=_headers("correct"),
    )
    assert corrected.status_code == 200, corrected.text
    runtime.tick()
    assert runtime.notify.listing()["notices"] == []
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    notices = runtime.notify.listing()["notices"]
    assert len(notices) == 1
    assert notices[0]["kind"] == "memory_followup"
    assert "Friday" not in notices[0]["body_en"]
    assert SECRET not in _channels(runtime)
    _login(client)
    listed = client.get("/api/memory-followups", headers=_headers()).json()["followups"]
    assert listed[0]["id"] == followup_id
    assert listed[0]["state"] == "raised"
    assert listed[0]["body"] == "The Thursday dentist visit moved to Friday"
    assert listed[0]["memory_updated"] is True
    assert "updated after approval" in listed[0]["reason_en"]
    assert "quiet hours are not in effect" in listed[0]["reason_en"]
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1
    assert len(_rows(runtime)) == 1


def test_quiet_hours_hold_the_same_followup_across_restart(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 10, 6, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    approved = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T23:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    followup_id = approved.json()["followup"]["id"]
    clock[0] = datetime(2026, 11, 10, 15, tzinfo=UTC)
    runtime.tick()
    _login(client)
    held = client.get("/api/memory-followups", headers=_headers()).json()["followups"][0]
    assert held["id"] == followup_id
    assert held["state"] == "held" and held["hold_reason"] == "quiet"
    assert "quiet hours are in effect" in held["reason_en"]
    assert runtime.notify.listing()["notices"] == []
    runtime.tick()
    assert _rows(runtime)[0]["version"] == held["version"]

    restarted = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    restarted.tick()
    assert restarted.notify.listing()["notices"] == []
    assert restarted.memory_followups.listing()["followups"][0]["state"] == "held"

    clock[0] = datetime(2026, 11, 10, 23, tzinfo=UTC)
    restarted.tick()
    raised = restarted.memory_followups.listing()["followups"][0]
    assert raised["state"] == "raised"
    assert "quiet hours have ended" in raised["reason_en"]
    assert len(restarted.notify.listing()["notices"]) == 1
    assert SECRET not in _channels(restarted)
    restarted.tick()
    assert len(restarted.notify.listing()["notices"]) == 1


def test_proactivity_off_holds_until_the_owner_turns_it_on(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T08:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    _prefs(runtime, proactivity="off")
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    held = runtime.memory_followups.listing()["followups"][0]
    assert held["state"] == "held" and held["hold_reason"] == "proactivity"
    assert "proactive reminders are off" in held["reason_en"]
    assert runtime.notify.listing()["notices"] == []
    _prefs(runtime, proactivity="normal")
    runtime.tick()
    assert runtime.memory_followups.listing()["followups"][0]["state"] == "raised"
    assert len(runtime.notify.listing()["notices"]) == 1


def test_forgetting_the_memory_cancels_the_followup_without_repeating_it(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T08:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    deleted = client.post(
        f"/api/memory/{fact['id']}/deletions",
        json={"expected_version": fact["version"]},
        headers=_headers("forget"),
    )
    assert deleted.status_code == 200, deleted.text
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    _login(client)
    followup = client.get("/api/memory-followups", headers=_headers()).json()["followups"][0]
    assert followup["state"] == "cancelled"
    assert followup["body"] is None
    assert SECRET not in followup["reason_en"]
    assert "no longer active" in followup["reason_en"]
    assert runtime.notify.listing()["notices"] == []
    runtime.tick()
    assert _rows(runtime)[0]["state"] == "cancelled"


def test_snooze_handled_and_the_raise_cap_are_one_followup_each(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    ids = []
    for index in range(4):
        fact = _memory(client, f"Private fact {index}", f"remember-{index}")
        approved = client.post(
            "/api/memory-followups",
            json={
                "memory_id": fact["id"],
                "memory_version": fact["version"],
                "due_local": "2026-11-10T08:00",
                "timezone": "Asia/Hong_Kong",
            },
            headers=_headers(f"approve-{index}"),
        )
        assert approved.status_code == 200, approved.text
        ids.append(approved.json()["followup"])
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    _login(client)
    assert len(runtime.notify.listing()["notices"]) == 3
    waiting = [
        row
        for row in runtime.memory_followups.listing()["followups"]
        if row["state"] == "pending"
    ]
    assert len(waiting) == 1
    clock[0] += timedelta(minutes=1)
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 4

    raised = next(
        row
        for row in runtime.memory_followups.listing()["followups"]
        if row["id"] == ids[0]["id"]
    )
    snoozed = client.post(
        f"/api/memory-followups/{raised['id']}/resolutions",
        json={"action": "snooze", "expected_version": raised["version"]},
        headers=_headers("snooze"),
    )
    assert snoozed.status_code == 200, snoozed.text
    assert snoozed.json()["followup"]["state"] == "pending"
    early = client.post(
        f"/api/memory-followups/{raised['id']}/resolutions",
        json={
            "action": "snooze",
            "expected_version": snoozed.json()["followup"]["version"],
        },
        headers=_headers("snooze-again"),
    )
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "FOLLOWUP_NOT_RAISED"
    before = len(runtime.notify.listing()["notices"])
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == before
    clock[0] += timedelta(hours=1, seconds=1)
    runtime.tick()
    notices = runtime.notify.listing()["notices"]
    assert len(notices) == before + 1
    assert len({notice["id"] for notice in notices}) == len(notices)

    target = next(
        row
        for row in runtime.memory_followups.listing()["followups"]
        if row["state"] == "raised"
    )
    handled = client.post(
        f"/api/memory-followups/{target['id']}/resolutions",
        json={"action": "handled", "expected_version": target["version"]},
        headers=_headers("handled"),
    )
    assert handled.status_code == 200, handled.text
    assert handled.json()["followup"]["state"] == "handled"
    retried = client.post(
        f"/api/memory-followups/{target['id']}/resolutions",
        json={"action": "handled", "expected_version": target["version"]},
        headers=_headers("handled"),
    )
    assert retried.json()["followup"]["state"] == "handled"
    clock[0] += timedelta(days=2)
    runtime.tick()
    assert all(
        row["id"] != target["id"] or row["state"] == "handled"
        for row in _rows(runtime)
    )


def test_a_dropped_notice_is_not_success_and_quiet_hours_still_hold_it(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, SECRET, "remember")
    client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": "2026-11-10T08:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("approve"),
    )
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    original = runtime.notify.publish

    def dropped(notice, *, quiet=False):
        raise RuntimeError("delivery dropped")

    runtime.notify.publish = dropped
    try:
        runtime.tick()
    except RuntimeError as error:
        assert str(error) == "delivery dropped"
    else:
        raise AssertionError("a dropped delivery was treated as success")
    runtime.notify.publish = original
    assert runtime.memory_followups.listing()["followups"][0]["state"] == "raised"
    assert runtime.notify.listing()["notices"] == []

    clock[0] = datetime(2026, 11, 10, 15, tzinfo=UTC)
    runtime.tick()
    assert runtime.notify.listing()["notices"] == []
    clock[0] = datetime(2026, 11, 10, 23, tzinfo=UTC)
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1
    assert SECRET not in _channels(runtime)
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1
