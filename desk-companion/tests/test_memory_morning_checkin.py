"""One approved morning check-in cites several due memories. No second scheduler."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import TOOLS
from desk.runtime import Runtime
from desk.store import Store
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

DENTIST = "The Thursday dentist visit is private"
LAB = "The Friday lab key is private"
PASSPORT = "The expired passport scan is private"
LATER = "The Saturday archive code is private"


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


def _headers(key=None):
    headers = {"X-Desk-Request": "1"}
    if key is not None:
        headers["X-Operation-Id"] = key
    return headers


def _memory(client, body, key):
    response = client.post("/api/memory", json={"body": body}, headers=_headers(key))
    assert response.status_code == 200, response.text
    return response.json()["memory"]


def _followup(client, fact, when, key):
    response = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": fact["version"],
            "due_local": when,
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers(key),
    )
    assert response.status_code == 200, response.text
    return response.json()["followup"]


def _login(client):
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )


def _operation(runtime, key):
    with runtime.store.connection() as conn:
        return conn.execute("SELECT * FROM operations WHERE id=?", (key,)).fetchone()


def _checkins(runtime):
    with runtime.store.connection() as conn:
        return conn.execute("SELECT * FROM memory_morning_checkins ORDER BY id").fetchall()


def _table_text(runtime, table):
    with runtime.store.connection() as conn:
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not present:
            return ""
        return "\n".join(
            " ".join(str(value) for value in tuple(row))
            for row in conn.execute(f"SELECT * FROM {table}")
        )


def _prefs(runtime, **fields):
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(**fields),
        ),
        uuid4().hex,
    )


def _notices(runtime, kind=None):
    notices = runtime.notify.listing()["notices"]
    if kind is None:
        return notices
    return [notice for notice in notices if notice["kind"] == kind]


def test_draft_does_not_arm_and_only_the_owner_can_approve(tmp_path):
    app, client, _clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    assert all("morning" not in tool["name"] for tool in TOOLS)
    stranger = TestClient(app)
    assert stranger.get("/api/memory-followups/morning").status_code == 403
    assert (
        stranger.post(
            "/api/memory-followups/morning/drafts",
            json={"due_local": "2026-11-10T09:00"},
            headers=_headers(),
        ).status_code
        == 403
    )
    other = TestClient(app)
    denied = other.post(
        "/api/session",
        json={"username": "someone", "password": "not-the-owner"},
        headers=_headers(),
    )
    assert denied.status_code == 401
    assert other.get("/api/memory-followups/morning").status_code == 403
    enrol = client.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers=_headers("pair-morning"),
    )
    assert enrol.status_code == 200, enrol.text
    display = TestClient(app)
    display.headers["Authorization"] = "Bearer " + client.cookies.get("desk_companion_device")
    assert display.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("display-morning"),
    ).status_code == 403

    dentist = _memory(client, DENTIST, "remember-dentist")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    one = client.post(
        "/api/memory-followups/morning/drafts",
        json={"due_local": "2026-11-10T09:00"},
        headers=_headers(),
    )
    assert one.status_code == 200, one.text
    assert one.json()["saved"] is False and one.json()["armed"] is False
    assert one.json()["draft"]["ready"] is False
    assert one.json()["draft"]["citations"][0]["body"] == DENTIST
    assert _checkins(runtime) == []

    lab = _memory(client, LAB, "remember-lab")
    _followup(client, lab, "2026-11-10T08:30", "follow-lab")
    past = client.post(
        "/api/memory-followups/morning/drafts",
        json={"due_local": "2026-11-09T08:00"},
        headers=_headers(),
    )
    assert past.status_code == 422 and past.json()["error"]["code"] == "FOLLOWUP_TIME_PAST"
    ambiguous = client.post(
        "/api/memory-followups/morning/drafts",
        json={"due_local": "2026-11-01T01:30", "timezone": "America/New_York"},
        headers=_headers(),
    )
    assert ambiguous.status_code == 422
    assert ambiguous.json()["error"]["code"] == "FOLLOWUP_TIME_INVALID"
    assert _checkins(runtime) == []

    draft = client.post(
        "/api/memory-followups/morning/drafts",
        json={"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers(),
    )
    assert draft.status_code == 200, draft.text
    bodies = [item["body"] for item in draft.json()["draft"]["citations"]]
    assert bodies == [DENTIST, LAB]
    assert draft.json()["draft"]["ready"] is True
    assert _checkins(runtime) == []

    short = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:15", "timezone": "Asia/Hong_Kong"},
        headers=_headers("too-early"),
    )
    assert short.status_code == 422
    assert short.json()["error"]["code"] == "MORNING_CHECKIN_NEEDS_SEVERAL"
    assert _operation(runtime, "too-early") is None
    assert _checkins(runtime) == []


def test_lost_response_retries_and_a_rejected_confirm_is_not_success(tmp_path):
    app, client, _clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:30", "follow-lab")
    payload = {"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"}
    rejected = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-09T08:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve-once"),
    )
    assert rejected.status_code == 422
    assert _operation(runtime, "approve-once") is None
    assert _checkins(runtime) == []

    first = client.post("/api/memory-followups/morning", json=payload, headers=_headers("approve-once"))
    second = client.post("/api/memory-followups/morning", json=payload, headers=_headers("approve-once"))
    assert first.status_code == second.status_code == 200
    assert first.json()["checkin"]["id"] == second.json()["checkin"]["id"]
    assert len(_checkins(runtime)) == 1
    conflict = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T11:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve-once"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert _checkins(runtime)[0]["due_local"] == "2026-11-10T09:00"

    checkin = first.json()["checkin"]
    stale = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={"expected_version": 9, "due_local": "2026-11-10T10:00"},
        headers=_headers("revise-once"),
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "VERSION_CONFLICT"
    assert _operation(runtime, "revise-once") is None
    assert _checkins(runtime)[0]["version"] == checkin["version"]
    moved = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={"expected_version": checkin["version"], "due_local": "2026-11-10T10:00"},
        headers=_headers("revise-once"),
    )
    assert moved.status_code == 200, moved.text
    again = client.post(
        "/api/memory-followups/morning",
        json=payload,
        headers=_headers("second-checkin"),
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "MORNING_CHECKIN_OPEN"
    assert _operation(runtime, "second-checkin") is None
    assert len(_checkins(runtime)) == 1


def test_omitted_revision_fields_stay_stored_and_a_dropped_fact_is_released(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    later = _memory(client, LATER, "remember-later")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, later, "2026-11-10T10:00", "follow-later")
    approved = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T10:30", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    checkin = approved.json()["checkin"]
    untouched = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={"expected_version": checkin["version"]},
        headers=_headers("revise-empty"),
    )
    assert untouched.status_code == 200, untouched.text
    assert untouched.json()["checkin"]["version"] == checkin["version"]
    assert untouched.json()["checkin"]["due_local"] == "2026-11-10T10:30"
    assert untouched.json()["checkin"]["timezone"] == "Asia/Hong_Kong"
    cleared = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={"expected_version": checkin["version"], "timezone": None},
        headers=_headers("revise-null"),
    )
    assert cleared.status_code == 422
    assert cleared.json()["error"]["code"] == "FOLLOWUP_TIME_REQUIRED"
    assert _checkins(runtime)[0]["timezone"] == "Asia/Hong_Kong"
    assert _checkins(runtime)[0]["version"] == checkin["version"]

    zoned = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={"expected_version": checkin["version"], "timezone": "UTC"},
        headers=_headers("revise-zone"),
    )
    assert zoned.status_code == 200, zoned.text
    assert zoned.json()["checkin"]["timezone"] == "UTC"
    assert zoned.json()["checkin"]["due_local"] == "2026-11-10T10:30"
    restored = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/revisions",
        json={
            "expected_version": zoned.json()["checkin"]["version"],
            "timezone": "Asia/Hong_Kong",
            "due_local": "2026-11-10T09:00",
        },
        headers=_headers("revise-earlier"),
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["checkin"]["due_local"] == "2026-11-10T09:00"
    assert [item["body"] for item in restored.json()["checkin"]["citations"]] == [DENTIST]
    assert LATER not in restored.text

    clock[0] = datetime(2026, 11, 10, 1, tzinfo=UTC)
    runtime.tick()
    morning = _notices(runtime, "memory_morning")
    assert len(morning) == 1
    assert DENTIST in morning[0]["body_en"]
    assert LATER not in morning[0]["body_en"]
    assert _notices(runtime, "memory_followup") == []
    clock[0] = datetime(2026, 11, 10, 2, tzinfo=UTC)
    runtime.tick()
    individual = _notices(runtime, "memory_followup")
    assert len(individual) == 1
    assert LATER not in individual[0]["body_en"]
    assert DENTIST not in individual[0]["body_en"]
    assert len(_notices(runtime, "memory_morning")) == 1


def test_one_notice_cites_several_due_followups_and_not_the_display(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    facts = []
    for index, body in enumerate((DENTIST, LAB, PASSPORT, LATER)):
        fact = _memory(client, body, f"remember-{index}")
        _followup(client, fact, "2026-11-10T08:00", f"follow-{index}")
        facts.append(fact)
    corrected = client.post(
        f"/api/memory/{facts[0]['id']}/revisions",
        json={"body": "The Thursday dentist visit moved to Friday", "expected_version": 1},
        headers=_headers("correct"),
    )
    assert corrected.status_code == 200, corrected.text
    approved = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    assert approved.status_code == 200, approved.text
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    morning = _notices(runtime, "memory_morning")
    assert len(morning) == 1
    assert _notices(runtime, "memory_followup") == []
    assert len(_notices(runtime)) == 1
    body = morning[0]["body_en"]
    assert "Alice is citing 4" in body
    assert "moved to Friday" in body
    assert DENTIST not in body
    assert LAB in body and PASSPORT in body and LATER in body
    assert "quiet hours are not in effect" in morning[0]["reason_en"]
    inbox = _table_text(runtime, "notice_inbox")
    device = _table_text(runtime, "device_notices")
    assert "moved to Friday" in inbox and LAB in inbox
    assert "moved to Friday" not in device and LAB not in device and PASSPORT not in device
    assert "Open Memory to read the morning check-in." in device
    _login(client)
    listed = client.get("/api/memory-followups/morning", headers=_headers()).json()["checkin"]
    assert listed["state"] == "raised"
    assert {item["body"] for item in listed["citations"]} == {
        "The Thursday dentist visit moved to Friday",
        LAB,
        PASSPORT,
        LATER,
    }
    followups = client.get("/api/memory-followups", headers=_headers()).json()["followups"]
    assert len(followups) == 4
    assert all(item["bundled"] and item["state"] == "raised" for item in followups)
    assert all("separate reminder" in item["reason_en"] for item in followups)
    runtime.tick()
    assert len(_notices(runtime)) == 1


def test_early_followups_wait_and_an_already_raised_fact_is_not_cited_again(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    early = _memory(client, DENTIST, "remember-early")
    _followup(client, early, "2026-11-10T07:30", "follow-early")
    clock[0] = datetime(2026, 11, 9, 23, 30, tzinfo=UTC)
    runtime.tick()
    assert runtime.memory_followups.listing()["followups"][0]["state"] == "raised"
    assert _notices(runtime, "memory_followup")
    assert DENTIST not in _table_text(runtime, "notice_inbox")

    lab = _memory(client, LAB, "remember-lab")
    passport = _memory(client, PASSPORT, "remember-passport")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    _followup(client, passport, "2026-11-10T08:15", "follow-passport")
    approved = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:30", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    assert approved.status_code == 200, approved.text
    assert [item["body"] for item in approved.json()["checkin"]["citations"]] == [LAB, PASSPORT]
    runtime.tick()
    held = [
        row
        for row in runtime.memory_followups.listing()["followups"]
        if row["state"] == "held"
    ]
    assert len(held) == 2
    assert all(row["hold_reason"] == "morning" for row in held)
    assert len(_notices(runtime, "memory_morning")) == 0
    version = runtime.memory_followups.morning_listing()["checkin"]["version"]
    runtime.tick()
    assert runtime.memory_followups.morning_listing()["checkin"]["version"] == version

    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    morning = _notices(runtime, "memory_morning")
    assert len(morning) == 1
    assert LAB in morning[0]["body_en"] and PASSPORT in morning[0]["body_en"]
    assert DENTIST not in morning[0]["body_en"]
    assert len(_notices(runtime, "memory_followup")) == 1
    runtime.tick()
    assert len(_notices(runtime, "memory_morning")) == 1


def test_quiet_hours_and_proactivity_hold_the_same_checkin_across_restart(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    _followup(client, dentist, "2026-11-10T23:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T23:00", "follow-lab")
    client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T23:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    clock[0] = datetime(2026, 11, 10, 15, tzinfo=UTC)
    runtime.tick()
    held = runtime.memory_followups.morning_listing()["checkin"]
    assert held["state"] == "held" and held["hold_reason"] == "quiet"
    assert "quiet hours are in effect" in held["reason_en"]
    assert _notices(runtime) == []
    runtime.tick()
    assert runtime.memory_followups.morning_listing()["checkin"]["version"] == held["version"]

    restarted = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    restarted.tick()
    assert restarted.notify.listing()["notices"] == []
    assert restarted.memory_followups.morning_listing()["checkin"]["state"] == "held"
    clock[0] = datetime(2026, 11, 10, 23, tzinfo=UTC)
    restarted.tick()
    raised = restarted.memory_followups.morning_listing()["checkin"]
    assert raised["state"] == "raised"
    assert "quiet hours have ended" in raised["reason_en"]
    notices = restarted.notify.listing()["notices"]
    assert len(notices) == 1 and notices[0]["kind"] == "memory_morning"
    assert DENTIST in notices[0]["body_en"] and LAB in notices[0]["body_en"]
    assert DENTIST not in _table_text(restarted, "device_notices")
    restarted.tick()
    assert len(restarted.notify.listing()["notices"]) == 1

    off, off_client, off_clock = _app(
        tmp_path / "off", datetime(2026, 11, 9, 16, tzinfo=UTC)
    )
    off_runtime = off.state.runtime
    first = _memory(off_client, DENTIST, "remember-dentist")
    second = _memory(off_client, LAB, "remember-lab")
    _followup(off_client, first, "2026-11-10T08:00", "follow-dentist")
    _followup(off_client, second, "2026-11-10T08:00", "follow-lab")
    off_client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve-off"),
    )
    _prefs(off_runtime, proactivity="off")
    off_clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    off_runtime.tick()
    waiting = off_runtime.memory_followups.morning_listing()["checkin"]
    assert waiting["state"] == "held" and waiting["hold_reason"] == "proactivity"
    assert "proactive reminders are off" in waiting["reason_en"]
    assert off_runtime.notify.listing()["notices"] == []
    _prefs(off_runtime, proactivity="normal")
    off_runtime.tick()
    assert len(_notices(off_runtime, "memory_morning")) == 1
    assert _notices(off_runtime, "memory_followup") == []


def test_forgotten_and_expired_wording_never_appears(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    passport = _memory(client, PASSPORT, "remember-passport")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    _followup(client, passport, "2026-11-10T08:00", "follow-passport")
    deleted = client.post(
        f"/api/memory/{dentist['id']}/deletions",
        json={"expected_version": dentist["version"]},
        headers=_headers("forget"),
    )
    assert deleted.status_code == 200, deleted.text
    expiry = client.post(
        f"/api/memory/{passport['id']}/expiry",
        json={"expected_version": passport["version"], "expires_at": "2026-11-10T00:10:00Z"},
        headers=_headers("expire"),
    )
    assert expiry.status_code == 200, expiry.text
    client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    _login(client)
    checkin = client.get("/api/memory-followups/morning", headers=_headers()).json()["checkin"]
    page = client.get("/api/memory-followups", headers=_headers()).text
    notices = runtime.notify.listing()["notices"]
    assert len(notices) == 1
    assert notices[0]["kind"] == "memory_morning"
    assert LAB in notices[0]["body_en"]
    assert "Alice is citing 1" in notices[0]["body_en"]
    combined = notices[0]["body_en"] + notices[0]["reason_en"] + checkin["reason_en"] + page
    for table in ("notice_inbox", "browser_notices", "device_notices"):
        combined += _table_text(runtime, table)
    assert DENTIST not in combined
    assert PASSPORT not in combined
    assert [item["body"] for item in checkin["citations"]] == [LAB]
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1


def test_a_dropped_notice_is_sent_once_after_quiet_hours(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:00", "timezone": "Asia/Hong_Kong"},
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
    assert runtime.memory_followups.morning_listing()["checkin"]["state"] == "raised"
    assert runtime.notify.listing()["notices"] == []
    assert DENTIST not in _table_text(runtime, "notice_inbox")

    clock[0] = datetime(2026, 11, 10, 15, tzinfo=UTC)
    runtime.tick()
    assert runtime.notify.listing()["notices"] == []
    clock[0] = datetime(2026, 11, 10, 23, tzinfo=UTC)
    runtime.tick()
    notices = runtime.notify.listing()["notices"]
    assert len(notices) == 1
    assert DENTIST in notices[0]["body_en"] and LAB in notices[0]["body_en"]
    assert DENTIST not in _table_text(runtime, "device_notices")
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1


def test_forgetting_before_the_retry_drops_the_wording(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T08:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    def dropped(notice, *, quiet=False):
        raise RuntimeError("delivery dropped")

    runtime.notify.publish = dropped
    try:
        runtime.tick()
    except RuntimeError as error:
        assert str(error) == "delivery dropped"
    else:
        raise AssertionError("a dropped delivery was treated as success")
    _login(client)
    for fact, key in ((dentist, "forget-dentist"), (lab, "forget-lab")):
        deleted = client.post(
            f"/api/memory/{fact['id']}/deletions",
            json={"expected_version": fact["version"]},
            headers=_headers(key),
        )
        assert deleted.status_code == 200, deleted.text
    runtime.tick()
    assert runtime.notify.listing()["notices"] == []
    combined = ""
    for table in ("notice_inbox", "browser_notices", "device_notices"):
        combined += _table_text(runtime, table)
    listed = client.get("/api/memory-followups/morning", headers=_headers()).text
    assert DENTIST not in combined and LAB not in combined
    assert DENTIST not in listed and LAB not in listed


def test_dismiss_uses_an_operation_id_and_then_each_followup_can_raise_alone(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    approved = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    checkin = approved.json()["checkin"]
    clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=UTC)
    runtime.tick()
    assert runtime.notify.listing()["notices"] == []
    assert all(
        row["hold_reason"] == "morning"
        for row in runtime.memory_followups.listing()["followups"]
    )
    _login(client)
    stale = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/dismissals",
        json={"expected_version": 9},
        headers=_headers("dismiss-once"),
    )
    assert stale.status_code == 409
    assert _operation(runtime, "dismiss-once") is None
    current = runtime.memory_followups.morning_listing()["checkin"]
    dismissed = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/dismissals",
        json={"expected_version": current["version"]},
        headers=_headers("dismiss-once"),
    )
    assert dismissed.status_code == 200, dismissed.text
    assert dismissed.json()["checkin"]["state"] == "dismissed"
    repeat = client.post(
        f"/api/memory-followups/morning/{checkin['id']}/dismissals",
        json={"expected_version": dismissed.json()["checkin"]["version"]},
        headers=_headers("dismiss-again"),
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["checkin"]["state"] == "dismissed"
    again = client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve-again"),
    )
    assert again.status_code == 200, again.text
    closed = client.post(
        f"/api/memory-followups/morning/{again.json()['checkin']['id']}/dismissals",
        json={"expected_version": again.json()["checkin"]["version"]},
        headers=_headers("dismiss-second"),
    )
    assert closed.status_code == 200, closed.text
    runtime.tick()
    individual = _notices(runtime, "memory_followup")
    assert len(individual) == 2
    assert _notices(runtime, "memory_morning") == []
    inbox = _table_text(runtime, "notice_inbox")
    assert DENTIST not in inbox and LAB not in inbox
    runtime.tick()
    assert len(_notices(runtime, "memory_followup")) == 2


def test_a_followup_approved_after_the_checkin_joins_it(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 9, 16, tzinfo=UTC))
    runtime = app.state.runtime
    dentist = _memory(client, DENTIST, "remember-dentist")
    lab = _memory(client, LAB, "remember-lab")
    passport = _memory(client, PASSPORT, "remember-passport")
    _followup(client, dentist, "2026-11-10T08:00", "follow-dentist")
    _followup(client, lab, "2026-11-10T08:00", "follow-lab")
    client.post(
        "/api/memory-followups/morning",
        json={"due_local": "2026-11-10T09:00", "timezone": "Asia/Hong_Kong"},
        headers=_headers("approve"),
    )
    _followup(client, passport, "2026-11-10T08:30", "follow-passport")
    clock[0] = datetime(2026, 11, 10, 1, tzinfo=UTC)
    runtime.tick()
    morning = _notices(runtime, "memory_morning")
    assert len(morning) == 1
    assert DENTIST in morning[0]["body_en"]
    assert LAB in morning[0]["body_en"] and PASSPORT in morning[0]["body_en"]
    assert "Alice is citing 3" in morning[0]["body_en"]
    assert _notices(runtime, "memory_followup") == []


def test_an_existing_followup_table_gains_the_bundle_column(tmp_path):
    store = Store(tmp_path, password="fixture-only")
    with store.connection(write=True) as conn:
        conn.execute(
            """CREATE TABLE memory_followups(
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                due_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                due_local TEXT NOT NULL,
                state TEXT NOT NULL,
                version INTEGER NOT NULL,
                hold_reason TEXT,
                hold_until TEXT,
                not_before TEXT,
                quiet_delayed INTEGER NOT NULL,
                raise_generation INTEGER NOT NULL,
                notice_id TEXT,
                raised_at TEXT,
                approved_memory_version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
    Runtime(store)
    with store.connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(memory_followups)")}
        morning = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_morning_checkins'"
        ).fetchone()
    assert "bundle_id" in columns
    assert morning
