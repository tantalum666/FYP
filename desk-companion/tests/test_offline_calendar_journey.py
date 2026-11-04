"""Offline calendar journey through the owner HTTP task, event, draft, and notice paths."""

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from desk.access import digest
from desk.app import create_app
from desk.store import encode
from desk.workspace_data import WorkspacePreferences

CLOCK = datetime(2026, 11, 3, 1, tzinfo=UTC)
SECRETS = ("Must not be read", "Later secret", "Unread after disconnect", "Replace me")


def owner_app(directory, clock=None):
    clock = clock if clock is not None else [CLOCK]
    app = create_app(
        directory, password="fixture-only", scheduler=False, clock=lambda: clock[0]
    )
    http = TestClient(app)
    http.headers.update({"X-Desk-Request": "1"})
    response = http.post(
        "/api/session", json={"username": "owner", "password": "fixture-only"}
    )
    assert response.status_code == 200
    return app, http


def connect(http, fixture, key="connect"):
    response = http.post(
        "/api/offline-calendar/connections",
        json={"fixture": fixture},
        headers={"X-Operation-Id": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["connection"]


def sync(http, connection_id, key):
    response = http.post(
        f"/api/offline-calendar/connections/{connection_id}/sync",
        headers={"X-Operation-Id": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def tasks(http, include_closed=False):
    response = http.get("/api/tasks", params={"include_closed": include_closed})
    assert response.status_code == 200, response.text
    return response.json()["tasks"]


def notices(http):
    response = http.get("/api/notices")
    assert response.status_code == 200, response.text
    return response.json()["notices"]


def detail(http, task_id):
    response = http.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200, response.text
    return response.json()


def event(http, event_id):
    response = http.get(f"/api/events/{event_id}")
    assert response.status_code == 200, response.text
    return response.json()


def proposals(http):
    response = http.get("/api/assistant/proposals")
    assert response.status_code == 200, response.text
    return response.json()["proposals"]


def proposal_for(items, event_uid):
    matches = [item for item in items if item["data"].get("event_uid") == event_uid]
    assert len(matches) == 1
    return matches[0]


def decide(http, proposal_id, action, key):
    return http.post(
        f"/api/assistant/proposals/{proposal_id}/decisions",
        json={"action": action},
        headers={"X-Operation-Id": key},
    )


def item_for(connection, uid):
    matches = [item for item in connection["items"] if item["uid"] == uid]
    assert len(matches) == 1
    return matches[0]


def task_for(items, task_id):
    matches = [item for item in items if item["id"] == task_id]
    assert len(matches) == 1
    return matches[0]


def task_fields(task, **changes):
    body = {
        key: task[key]
        for key in (
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
    }
    body.update(changes)
    return body


def test_out_of_order_duplicate_preserves_fields_and_one_task(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "schedule-journey")
    first = sync(http, connection["id"], "arrive")
    assert first["success"] is True and first["status"] == "applied"
    assert first["accepted"] is False and first["sent"] is False
    assert first["duplicate_uids"] == ["evt-review"]
    assert first["applied_uids"] == ["evt-review", "evt-review", "series-standup"]
    assert first["connection"]["history_cursor"] == "3"
    review = item_for(first["connection"], "evt-review")
    series = item_for(first["connection"], "series-standup")
    assert review["kind"] == "event" and series["kind"] == "series"
    assert review["work_item"] == {"kind": "task", "id": review["task_id"]}
    assert series["work_item"] == {"kind": "task", "id": series["task_id"]}
    assert review["task_id"] != series["task_id"]
    listed = tasks(http)
    assert {item["id"] for item in listed} == {review["task_id"], series["task_id"]}
    assert task_for(listed, review["task_id"])["due_local"].startswith("2026-11-20T19:00")
    assert task_for(listed, series["task_id"])["title"] == "Standup"
    saved = event(http, review["event_id"])
    assert saved["location"] == "Library"
    assert saved["notes"] == "Bring the brief"
    assert saved["reminder_minutes"] == [30, 10]
    assert saved["start_local"].startswith("2026-11-20T19:00")
    standup = event(http, series["event_id"])
    assert standup["recurrence"]["frequency"] == "weekly"
    assert standup["location"] == "Desk"
    replay = sync(http, connection["id"], "arrive")
    assert replay == first
    assert len(tasks(http)) == 2
    assert notices(http) == []

    moved = sync(http, connection["id"], "series")
    assert moved["success"] is True and moved["applied_uids"] == ["series-standup"]
    series_now = item_for(moved["connection"], "series-standup")
    assert series_now["task_id"] == series["task_id"]
    assert series_now["event_id"] == series["event_id"]
    assert task_for(tasks(http), series["task_id"])["due_local"].startswith("2026-11-20T10:00")
    kept = event(http, series["event_id"])
    assert kept["location"] == "Desk"
    assert kept["notes"] == "Weekly"
    assert kept["reminder_minutes"] == [5]
    assert kept["recurrence"]["frequency"] == "weekly"
    assert notices(http) == []

    before = task_for(tasks(http), review["task_id"])["version"]
    quiet = sync(http, connection["id"], "unchanged")
    assert quiet["success"] is True and quiet["duplicate_uids"] == ["evt-review"]
    assert quiet["applied_uids"] == []
    assert task_for(tasks(http), review["task_id"])["version"] == before
    assert notices(http) == []

    noted = http.post(
        f"/api/tasks/{review['task_id']}/actions",
        json={
            "action": "update",
            "expected_version": before,
            "task": task_fields(
                task_for(tasks(http), review["task_id"]), next_step="Owner plan"
            ),
            "note": "Owner note that must stay",
        },
        headers={"X-Operation-Id": "owner-note"},
    )
    assert noted.status_code == 200, noted.text
    near = sync(http, connection["id"], "near")
    assert near["success"] is True
    current = task_for(tasks(http), review["task_id"])
    assert current["due_local"].startswith("2026-11-03T18:00")
    assert current["next_step"] == "Owner plan"
    assert current["title"] == "Design review"
    preserved = event(http, review["event_id"])
    assert preserved["location"] == "Library"
    assert preserved["notes"] == "Bring the brief"
    assert preserved["reminder_minutes"] == [30, 10]
    assert preserved["start_local"].startswith("2026-11-03T18:00")
    assert any(row["note"] == "Owner note that must stay" for row in detail(http, review["task_id"])["evidence"])
    deadline = next(item for item in notices(http) if "evt-review" in item["body_en"])
    assert "within 24 hours" in deadline["body_en"]
    assert "2026-11-03T01:05:00" in deadline["body_en"]
    notice_count = len(notices(http))

    conflict = sync(http, connection["id"], "conflict")
    assert conflict["success"] is True and conflict["accepted"] is False
    clash = item_for(conflict["connection"], "evt-clash")
    assert clash["task_id"] not in {review["task_id"], series["task_id"]}
    assert len(tasks(http)) == 3
    window = http.get(
        "/api/calendar",
        params={"start": "2026-11-03T00:00:00Z", "end": "2026-11-04T00:00:00Z"},
    )
    assert window.status_code == 200, window.text
    occurrences = [
        row
        for row in window.json()["occurrences"]
        if row["id"] in {review["event_id"], clash["event_id"]}
    ]
    assert len(occurrences) == 2
    assert all(row["conflicts"] for row in occurrences)
    drafts = proposals(http)
    overlap = proposal_for(drafts, "evt-clash")
    assert overlap["kind"] == "calendar_advice"
    assert overlap["data"]["accept"] is False and overlap["data"]["send"] is False
    assert "evt-review" in overlap["data"]["summary"]
    assert "evt-clash" in overlap["data"]["summary"]
    assert overlap["data"]["observed_at"].startswith("2026-11-03T01:06:00")
    conflict_notice = next(item for item in notices(http) if "evt-clash" in item["body_en"])
    assert "New schedule conflict." in conflict_notice["body_en"]
    assert "evt-review" in conflict_notice["body_en"]
    assert len(notices(http)) == notice_count + 1

    prepared = sync(http, connection["id"], "prepare")
    assert prepared["success"] is True
    assert event(http, review["event_id"])["notes"] == "Bring the brief"
    assert event(http, review["event_id"])["location"] == "Library"
    assert task_for(tasks(http), review["task_id"])["due_local"].startswith("2026-11-03T18:00")
    prepare = proposal_for(proposals(http), "evt-review")
    assert prepare["data"]["accept"] is False and prepare["data"]["send"] is False
    assert prepare["data"]["observed_at"].startswith("2026-11-03T01:07:00")
    assert "evt-review" in prepare["data"]["summary"]
    assert len(notices(http)) == notice_count + 2

    invited = sync(http, connection["id"], "rsvp")
    assert invited["success"] is True and invited["accepted"] is False and invited["sent"] is False
    invite = proposal_for(proposals(http), "evt-invite")
    assert invite["data"]["accept"] is False and invite["data"]["send"] is False
    assert "rsvp" in invite["data"]["reasons"]
    assert invite["data"]["observed_at"].startswith("2026-11-03T01:08:00")
    assert len(tasks(http)) == 4
    assert len(notices(http)) == notice_count + 3

    cancelled = decide(http, prepare["id"], "cancel", "cancel-prepare")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["saved"] is False
    confirmed = decide(http, overlap["id"], "confirm", "confirm-conflict")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["result"]["sent"] is False
    assert confirmed.json()["result"]["accepted"] is False
    assert confirmed.json()["result"]["task"]["id"] == clash["task_id"]
    clash_notes = [row["note"] for row in detail(http, clash["task_id"])["evidence"]]
    assert sum("No invite was accepted" in note for note in clash_notes) == 1
    assert any("evt-clash" in note and "evt-review" in note for note in clash_notes)
    review_notes = [row["note"] for row in detail(http, review["task_id"])["evidence"]]
    assert any(note == "Owner note that must stay" for note in review_notes)
    assert not any("No invite was accepted" in note for note in review_notes)
    invite_task = item_for(invited["connection"], "evt-invite")["task_id"]
    invite_notes = [row["note"] for row in detail(http, invite_task)["evidence"]]
    assert not any("No invite was accepted" in note for note in invite_notes)
    assert proposal_for(proposals(http), "evt-invite")["data"]["accept"] is False

    removed = sync(http, connection["id"], "cancel")
    assert removed["success"] is True
    assert [item["id"] for item in tasks(http) if item["id"] == clash["task_id"]] == []
    closed = task_for(tasks(http, include_closed=True), clash["task_id"])
    assert closed["status"] == "cancelled"
    assert task_for(tasks(http), review["task_id"])["id"] == review["task_id"]
    assert event(http, review["event_id"])["location"] == "Library"
    cancel_notice = next(
        item for item in notices(http) if "Cancelled meeting" in item["body_en"]
    )
    assert "evt-clash" in cancel_notice["body_en"]
    assert "2026-11-03T01:09:00" in cancel_notice["body_en"]
    idle = sync(http, connection["id"], "done")
    assert idle["success"] is True and idle["status"] == "idle" and idle["events_read"] == 0
    assert len(notices(http)) == notice_count + 4
    assert all(secret not in str(notices(http)) for secret in SECRETS)


def test_restart_mid_sync_keeps_one_task_and_omitted_fields(tmp_path):
    app, http = owner_app(tmp_path)
    connection = connect(http, "restart-mid-sync")
    stopped = sync(http, connection["id"], "partial")
    assert stopped["success"] is False and stopped["status"] == "interrupted"
    assert stopped["connection"]["history_cursor"] is None
    assert stopped["applied_uids"] == ["evt-restart"]
    first = tasks(http)
    assert len(first) == 1
    assert first[0]["due_local"].startswith("2026-11-20T18:00")
    saved = event(http, item_for(stopped["connection"], "evt-restart")["event_id"])
    assert saved["location"] == "Room" and saved["notes"] == "Stay"
    assert saved["reminder_minutes"] == [15]

    _restarted, again = owner_app(tmp_path)
    resumed = sync(again, connection["id"], "resume")
    assert resumed["success"] is True and resumed["status"] == "applied"
    assert resumed["connection"]["history_cursor"] == "2"
    restored = tasks(again)
    assert len(restored) == 1
    assert restored[0]["id"] == first[0]["id"]
    assert restored[0]["due_local"].startswith("2026-11-21T18:00")
    kept = event(again, item_for(resumed["connection"], "evt-restart")["event_id"])
    assert kept["id"] == saved["id"]
    assert kept["location"] == "Room" and kept["notes"] == "Stay"
    assert kept["reminder_minutes"] == [15]
    with app.state.runtime.store.connection() as conn:
        rows = conn.execute(
            "SELECT id, state FROM offline_calendar_attempts ORDER BY started_at, id"
        ).fetchall()
    assert [row["id"] for row in rows] == ["partial", "resume"]
    assert rows[0]["state"] == "interrupted"
    assert rows[1]["state"] == "applied"


def test_revoke_during_sync_does_not_read_the_next_event(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "revoke-mid-sync")
    stopped = sync(http, connection["id"], "cut")
    assert stopped["success"] is False and stopped["status"] == "revoked"
    assert "Must not be read" not in str(stopped)
    assert [task["title"] for task in tasks(http)] == ["Kept meeting"]
    again = sync(http, connection["id"], "after-revoke")
    assert again["success"] is False and again["status"] == "revoked"
    assert again["events_read"] == 0
    assert again["applied_uids"] == []
    assert [task["title"] for task in tasks(http)] == ["Kept meeting"]


def test_endpoint_revoke_stops_the_next_batch(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "two-batches", key="connect-later")
    first = sync(http, connection["id"], "visible")
    assert first["success"] is True
    assert [task["title"] for task in tasks(http)] == ["Visible meeting"]
    assert notices(http) == []
    revoked = http.post(
        f"/api/offline-calendar/connections/{connection['id']}/revocation",
        headers={"X-Operation-Id": "revoke-later"},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["reads_stopped"] is True
    blocked = sync(http, connection["id"], "later")
    assert blocked["success"] is False and blocked["events_read"] == 0
    assert [task["title"] for task in tasks(http)] == ["Visible meeting"]
    assert "Later secret" not in str(blocked)


def test_disconnect_is_not_a_successful_sync(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "disconnect-mid-sync")
    stopped = sync(http, connection["id"], "drop")
    assert stopped["success"] is False and stopped["status"] == "disconnected"
    assert stopped["connection"]["history_cursor"] is None
    assert [task["title"] for task in tasks(http)] == ["Seen before disconnect"]
    again = sync(http, connection["id"], "after-drop")
    assert again["success"] is False and again["events_read"] == 0
    assert len(tasks(http)) == 1

    other = connect(http, "two-batches", key="connect-endpoint")
    assert sync(http, other["id"], "seen")["success"] is True
    dropped = http.post(
        f"/api/offline-calendar/connections/{other['id']}/disconnection",
        headers={"X-Operation-Id": "disconnect-later"},
    )
    assert dropped.status_code == 200, dropped.text
    assert dropped.json()["reads_stopped"] is True
    blocked = sync(http, other["id"], "hidden")
    assert blocked["success"] is False and blocked["events_read"] == 0
    assert "Later secret" not in str(blocked)


def test_stale_revision_does_not_clear_fields(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "stale-revision")
    newer = sync(http, connection["id"], "newer")
    assert newer["success"] is True
    held = item_for(newer["connection"], "evt-hold")
    older = sync(http, connection["id"], "older")
    assert older["success"] is True
    assert older["skipped_uids"] == ["evt-hold"]
    assert older["applied_uids"] == []
    current = item_for(older["connection"], "evt-hold")
    assert current["task_id"] == held["task_id"]
    assert current["event_id"] == held["event_id"]
    assert len(tasks(http)) == 1
    assert tasks(http)[0]["due_local"].startswith("2026-11-21T15:00")
    saved = event(http, held["event_id"])
    assert saved["location"] == "Keep me"
    assert saved["notes"] == "Original note"
    assert saved["reminder_minutes"] == [20]
    assert notices(http) == []


def test_status_cancel_notifies_and_blocks_a_later_update(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "status-cancel")
    created = sync(http, connection["id"], "create")
    assert created["success"] is True
    assert notices(http) == []
    dropped = sync(http, connection["id"], "drop")
    assert dropped["success"] is True
    assert tasks(http) == []
    closed = tasks(http, include_closed=True)
    assert closed[0]["status"] == "cancelled" and closed[0]["title"] == "Drop me"
    assert any("Cancelled meeting" in item["body_en"] for item in notices(http))
    rejected = http.post(
        f"/api/offline-calendar/connections/{connection['id']}/sync",
        headers={"X-Operation-Id": "again"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "CALENDAR_ITEM_CANCELLED"
    assert len(tasks(http, include_closed=True)) == 1


def test_draft_confirm_requires_the_owner_and_reads_back(tmp_path):
    app, http = owner_app(tmp_path)
    opened = http.post(
        "/api/permissions",
        json={"mode": "full", "expected_version": 1},
        headers={"X-Operation-Id": "full"},
    )
    assert opened.status_code == 200, opened.text
    connection = connect(http, "decision-meeting", key="connect-draft")
    synced = sync(http, connection["id"], "ask")
    assert synced["success"] is True and synced["accepted"] is False and synced["sent"] is False
    draft = proposal_for(proposals(http), "evt-decide")
    assert draft["kind"] == "calendar_advice" and draft["state"] == "pending"
    assert draft["data"]["accept"] is False and draft["data"]["send"] is False
    assert draft["data"]["observed_at"].startswith("2026-11-03T09:00:00")
    tracked = item_for(synced["connection"], "evt-decide")
    assert event(http, tracked["event_id"])["location"] == "Hall"
    assert event(http, tracked["event_id"])["notes"] == "Slides"
    assert event(http, tracked["event_id"])["reminder_minutes"] == [45]
    http.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Operation-Id": "pair-calendar"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + http.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/offline-calendar/connections").status_code == 403
    hidden = display.get("/api/assistant/proposals")
    assert hidden.status_code == 200
    assert all(item["kind"] != "calendar_advice" for item in hidden.json()["proposals"])
    assert display.post(
        f"/api/offline-calendar/connections/{connection['id']}/sync",
        headers={"X-Operation-Id": "display-sync"},
    ).status_code == 403
    refused = decide(display, draft["id"], "confirm", "display-confirm")
    assert refused.status_code == 403
    assert "No invite was accepted" not in str(detail(http, tracked["task_id"])["evidence"])
    anonymous = TestClient(app)
    anonymous.headers.update({"X-Desk-Request": "1"})
    assert anonymous.get("/api/offline-calendar/connections").status_code == 403

    confirmed = decide(http, draft["id"], "confirm", "owner-confirm")
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["result"]["sent"] is False and body["result"]["accepted"] is False
    assert body["result"]["task"]["id"] == tracked["task_id"]
    read_back = detail(http, tracked["task_id"])
    assert any(
        "evt-decide" in row["note"] and "No invite was accepted" in row["note"]
        for row in read_back["evidence"]
    )
    assert event(http, tracked["event_id"])["location"] == "Hall"
    assert event(http, tracked["event_id"])["reminder_minutes"] == [45]
    assert len(tasks(http)) == 1


def test_invalid_fixture_is_rejected_before_import(tmp_path):
    _app, http = owner_app(tmp_path)
    rejected = http.post(
        "/api/offline-calendar/connections",
        json={"fixture": "invalid-duplicate"},
        headers={"X-Operation-Id": "bad-fixture"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "FIXTURE_INVALID"
    assert http.get("/api/offline-calendar/connections").json()["connections"] == []
    traversal = http.post(
        "/api/offline-calendar/connections",
        json={"fixture": "../schedule-journey"},
        headers={"X-Operation-Id": "traversal"},
    )
    assert traversal.status_code == 422


def save_quiet(http, version, start, end, key):
    preferences = WorkspacePreferences(quiet_start=start, quiet_end=end).model_dump()
    saved = http.post(
        "/api/workspace/preferences",
        json={"expected_version": version, "preferences": preferences},
        headers={"X-Operation-Id": key},
    )
    assert saved.status_code == 200, saved.text
    return saved.json()["version"]


def backup_document(http):
    response = http.get("/api/exchange/backup.json")
    assert response.status_code == 200, response.text
    return response.json()


def restore_backup(http, document, preview_key, apply_key):
    preview = http.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(document)},
        headers={"X-Operation-Id": preview_key},
    )
    assert preview.status_code == 200, preview.text
    applied = http.post(
        f"/api/exchange/{preview.json()['preview_id']}/apply",
        json={},
        headers={"X-Operation-Id": apply_key},
    )
    assert applied.status_code == 200, applied.text
    return applied.json()


def test_quiet_hours_hold_a_notice_until_the_rules_tick(tmp_path):
    _app, http = owner_app(tmp_path)
    version = save_quiet(http, 1, "08:00", "18:00", "quiet-on")
    connection = connect(http, "soon-meeting", key="quiet-connect")
    synced = sync(http, connection["id"], "quiet-sync")
    assert synced["success"] is True
    task_id = tasks(http)[0]["id"]
    assert [task["title"] for task in tasks(http)] == ["Soon"]
    assert notices(http) == []
    saved_event = event(http, item_for(synced["connection"], "evt-soon")["event_id"])
    assert saved_event["location"] == "Quiet room"
    assert saved_event["notes"] == "Do not page"
    _app.state.runtime.tick()
    assert notices(http) == []

    _restarted, again = owner_app(tmp_path)
    _restarted.state.runtime.tick()
    assert notices(again) == []
    document = backup_document(again)
    holds = document["payload"]["offline_calendar_bundle"]["notice_holds"]
    assert holds and "evt-soon" in json.dumps(holds)
    restored_app, restored = owner_app(tmp_path / "restored")
    applied = restore_backup(restored, document, "quiet-preview", "quiet-restore")
    assert applied["offline_calendar_created"] == 1
    assert [task["id"] for task in tasks(restored)] == [task_id]
    assert notices(restored) == []
    restored_app.state.runtime.tick()
    delivered = notices(restored)
    assert len(delivered) == 1
    assert "evt-soon" in delivered[0]["body_en"]
    assert "within 24 hours" in delivered[0]["body_en"]
    restored_app.state.runtime.tick()
    assert notices(restored) == delivered
    replay = sync(restored, connection["id"], "quiet-sync")
    assert replay["applied_uids"] == synced["applied_uids"]
    assert [task["id"] for task in tasks(restored)] == [task_id]

    save_quiet(again, version, "22:00", "07:00", "quiet-off")
    _restarted.state.runtime.tick()
    source = notices(again)
    assert len(source) == 1 and "evt-soon" in source[0]["body_en"]
    _restarted.state.runtime.tick()
    assert notices(again) == source
    _after, third = owner_app(tmp_path)
    _after.state.runtime.tick()
    assert notices(third) == source


def test_backup_restore_keeps_the_cursor_and_one_task(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "schedule-journey")
    first = sync(http, connection["id"], "arrive")
    review = item_for(first["connection"], "evt-review")
    series = item_for(first["connection"], "series-standup")
    noted = http.post(
        f"/api/tasks/{review['task_id']}/actions",
        json={
            "action": "note",
            "expected_version": task_for(tasks(http), review["task_id"])["version"],
            "note": "Owner note that must stay",
        },
        headers={"X-Operation-Id": "owner-note"},
    )
    assert noted.status_code == 200, noted.text
    document = backup_document(http)
    bundle = document["payload"]["offline_calendar_bundle"]
    assert bundle["connections"][0]["history_cursor"] == "3"
    assert bundle["connections"][0]["next_event"] == first["connection"]["next_event"]
    assert {item["uid"] for item in bundle["items"]} == {"evt-review", "series-standup"}
    assert "password_hash" not in json.dumps(document)

    fresh_app, fresh = owner_app(tmp_path / "restored")
    fresh.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Operation-Id": "pair-backup"},
    )
    display = TestClient(fresh_app)
    display.headers.update(
        {
            "Authorization": "Bearer " + fresh.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/exchange/backup.json").status_code == 403
    assert (
        display.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(document)},
            headers={"X-Operation-Id": "display-preview"},
        ).status_code
        == 403
    )
    preview = fresh.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(document)},
        headers={"X-Operation-Id": "preview-calendar"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["metadata"]["offline_calendar_restore"] == "merge_keep_existing"
    preview_id = preview.json()["preview_id"]
    assert (
        display.post(
            f"/api/exchange/{preview_id}/apply",
            json={},
            headers={"X-Operation-Id": "display-apply"},
        ).status_code
        == 403
    )
    assert tasks(fresh) == []
    applied = fresh.post(
        f"/api/exchange/{preview_id}/apply",
        json={},
        headers={"X-Operation-Id": "apply-calendar"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["offline_calendar_created"] == 1
    restored_ids = {task["id"] for task in tasks(fresh)}
    assert restored_ids == {review["task_id"], series["task_id"]}
    assert task_for(tasks(fresh), review["task_id"])["due_local"].startswith("2026-11-20T19:00")
    assert any(
        row["note"] == "Owner note that must stay"
        for row in detail(fresh, review["task_id"])["evidence"]
    )
    kept = event(fresh, review["event_id"])
    assert kept["location"] == "Library"
    assert kept["notes"] == "Bring the brief"
    assert kept["reminder_minutes"] == [30, 10]
    again = fresh.get(f"/api/offline-calendar/connections/{connection['id']}")
    assert again.status_code == 200, again.text
    assert again.json()["connection"]["history_cursor"] == "3"
    assert again.json()["connection"]["next_event"] == first["connection"]["next_event"]
    assert item_for(again.json()["connection"], "evt-review")["task_id"] == review["task_id"]

    replay = sync(fresh, connection["id"], "arrive")
    assert replay == first
    assert {task["id"] for task in tasks(fresh)} == restored_ids
    second = restore_backup(fresh, document, "preview-again", "apply-again")
    assert second["offline_calendar_created"] == 0 and second["offline_calendar_kept"] == 1
    moved = sync(fresh, connection["id"], "series")
    assert moved["applied_uids"] == ["series-standup"]
    series_now = item_for(moved["connection"], "series-standup")
    assert series_now["task_id"] == series["task_id"]
    assert series_now["event_id"] == series["event_id"]
    assert {task["id"] for task in tasks(fresh)} == restored_ids
    assert task_for(tasks(fresh), series["task_id"])["due_local"].startswith("2026-11-20T10:00")
    assert event(fresh, series["event_id"])["location"] == "Desk"
    assert event(fresh, series["event_id"])["notes"] == "Weekly"
    assert event(fresh, review["event_id"])["location"] == "Library"

    tampered = json.loads(json.dumps(document))
    tampered["payload"]["offline_calendar_bundle"]["connections"][0]["next_event"] = -1
    tampered["sha256"] = digest(encode(tampered["payload"]))
    rejected = fresh.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(tampered)},
        headers={"X-Operation-Id": "tampered-calendar"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "INVALID_BACKUP"
    legacy = json.loads(json.dumps(document))
    legacy["payload"].pop("offline_calendar_bundle")
    legacy["sha256"] = digest(encode(legacy["payload"]))
    legacy_preview = fresh.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(legacy)},
        headers={"X-Operation-Id": "legacy-calendar"},
    )
    assert legacy_preview.status_code == 200, legacy_preview.text
    assert legacy_preview.json()["metadata"]["offline_calendar_connections"] == 0


def test_another_runtime_does_not_see_the_calendar(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "soon-meeting")
    assert sync(http, connection["id"], "soon")["success"] is True
    assert len(tasks(http)) == 1
    _other, second = owner_app(tmp_path / "other")
    assert second.get("/api/offline-calendar/connections").json()["connections"] == []
    assert tasks(second) == []
    assert [task["title"] for task in tasks(http)] == ["Soon"]
