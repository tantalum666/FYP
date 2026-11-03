"""Offline mailbox journey through the owner HTTP task, draft, and notice paths."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.workspace_data import WorkspacePreferences

CLOCK = datetime(2026, 11, 3, 1, tzinfo=UTC)
SNIPPETS = (
    "Please confirm the Friday draft.",
    "Early copy of the same thread.",
    "No tracked field changes in this copy.",
    "The review moved to this evening.",
    "The quote is accepted.",
    "Must not be read",
    "Unread after disconnect",
    "Later secret",
)


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
        "/api/mailbox/connections",
        json={"fixture": fixture},
        headers={"X-Operation-Id": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["connection"]


def sync(http, connection_id, key):
    response = http.post(
        f"/api/mailbox/connections/{connection_id}/sync",
        headers={"X-Operation-Id": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def tasks(http):
    response = http.get("/api/tasks")
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


def proposals(http):
    response = http.get("/api/assistant/proposals")
    assert response.status_code == 200, response.text
    return response.json()["proposals"]


def proposal_for(items, mail_id):
    matches = [item for item in items if item["data"].get("mail_id") == mail_id]
    assert len(matches) == 1
    return matches[0]


def decide(http, proposal_id, action, key):
    return http.post(
        f"/api/assistant/proposals/{proposal_id}/decisions",
        json={"action": action},
        headers={"X-Operation-Id": key},
    )


def test_out_of_order_duplicate_and_unchanged_thread_uses_one_task(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "thread-journey")
    first = sync(http, connection["id"], "arrive")
    assert first["success"] is True and first["status"] == "applied"
    assert first["duplicate_message_ids"] == ["msg-quote-2"]
    assert first["applied_message_ids"] == ["msg-quote-1", "msg-quote-2"]
    assert first["connection"]["history_cursor"] == "2"
    listed = tasks(http)
    assert len(listed) == 1
    task = listed[0]
    assert task["title"] == "Friday review quote"
    assert task["due_local"].startswith("2026-11-20T18:00")
    assert task["waiting_for"] == "Vendor confirmation"
    assert task["next_step"] == "Read the quote"
    assert task["status"] == "waiting"
    assert first["connection"]["threads"] == [
        {
            "thread_id": "thread-quote",
            "task_id": task["id"],
            "work_item": {"kind": "task", "id": task["id"]},
        }
    ]
    replay = sync(http, connection["id"], "arrive")
    assert replay == first
    assert len(tasks(http)) == 1
    assert tasks(http)[0]["version"] == task["version"]
    assert len(notices(http)) == 2

    ping = sync(http, connection["id"], "ping")
    assert ping["success"] is True and ping["applied_message_ids"] == ["msg-quote-3"]
    assert tasks(http)[0]["version"] == task["version"]
    assert len(notices(http)) == 2
    assert all(snippet not in str(notices(http)) for snippet in SNIPPETS)

    noted = http.post(
        f"/api/tasks/{task['id']}/actions",
        json={
            "action": "note",
            "expected_version": task["version"],
            "note": "Owner note that must stay",
        },
        headers={"X-Operation-Id": "owner-note"},
    )
    assert noted.status_code == 200, noted.text
    moved = sync(http, connection["id"], "reschedule")
    assert moved["success"] is True
    current = tasks(http)[0]
    assert current["id"] == task["id"]
    assert current["due_local"].startswith("2026-11-03T18:00")
    assert current["waiting_for"] == "Vendor confirmation"
    assert current["next_step"] == "Confirm the new time"
    assert current["status"] == "waiting"
    assert current["steps"] == []
    body = detail(http, task["id"])
    assert any(row["note"] == "Owner note that must stay" for row in body["evidence"])
    deadline = next(item for item in notices(http) if "msg-quote-4" in item["body_en"])
    assert "within 24 hours" in deadline["body_en"]
    assert "2026-11-03T01:04:00" in deadline["body_en"]
    notice_count = len(notices(http))

    quiet = sync(http, connection["id"], "unchanged")
    assert quiet["success"] is True
    assert quiet["duplicate_message_ids"] == ["msg-quote-4"]
    assert quiet["applied_message_ids"] == []
    assert tasks(http)[0]["version"] == current["version"]
    assert len(notices(http)) == notice_count

    reply = sync(http, connection["id"], "reply")
    assert reply["success"] is True
    finished = tasks(http)[0]
    assert finished["id"] == task["id"]
    assert finished["status"] == "in_progress"
    assert finished["due_local"].startswith("2026-11-03T18:00")
    assert finished["waiting_for"] == "Vendor confirmation"
    assert finished["next_step"] == "File the accepted quote"
    assert len(tasks(http)) == 1
    assert len(notices(http)) == notice_count + 1

    drafts = proposals(http)
    early = proposal_for(drafts, "msg-quote-1")
    latest = proposal_for(drafts, "msg-quote-5")
    assert early["data"]["send"] is False and latest["data"]["send"] is False
    assert latest["data"]["observed_at"].startswith("2026-11-03T01:05:00")
    cancelled = decide(http, early["id"], "cancel", "cancel-early")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["saved"] is False
    confirmed = decide(http, latest["id"], "confirm", "confirm-latest")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["result"]["sent"] is False
    assert confirmed.json()["result"]["task"]["id"] == task["id"]
    read_back = detail(http, task["id"])
    notes = [row["note"] for row in read_back["evidence"]]
    assert sum("Nothing was sent" in note for note in notes) == 1
    assert any("msg-quote-5" in note and "Nothing was sent" in note for note in notes)
    assert not any("msg-quote-1" in note and "Nothing was sent" in note for note in notes)
    assert any(note == "Owner note that must stay" for note in notes)
    assert len(tasks(http)) == 1
    assert tasks(http)[0]["due_local"].startswith("2026-11-03T18:00")
    remaining = {item["data"].get("mail_id") for item in proposals(http)}
    assert "msg-quote-1" not in remaining and "msg-quote-5" not in remaining


def test_restart_mid_sync_keeps_one_task_and_the_attempt(tmp_path):
    app, http = owner_app(tmp_path)
    connection = connect(http, "restart-mid-sync")
    stopped = sync(http, connection["id"], "partial")
    assert stopped["success"] is False and stopped["status"] == "interrupted"
    assert stopped["connection"]["history_cursor"] is None
    assert stopped["applied_message_ids"] == ["msg-restart-1"]
    first = tasks(http)
    assert len(first) == 1
    assert first[0]["due_local"].startswith("2026-11-20T18:00")
    assert first[0]["next_step"] == "Start from the first page"

    _restarted, again = owner_app(tmp_path)
    resumed = sync(again, connection["id"], "resume")
    assert resumed["success"] is True and resumed["status"] == "applied"
    assert resumed["connection"]["history_cursor"] == "2"
    restored = tasks(again)
    assert len(restored) == 1
    assert restored[0]["id"] == first[0]["id"]
    assert restored[0]["due_local"].startswith("2026-11-21T18:00")
    assert restored[0]["next_step"] == "Continue after restart"
    with app.state.runtime.store.connection() as conn:
        rows = conn.execute(
            "SELECT id, state FROM mailbox_attempts ORDER BY started_at, id"
        ).fetchall()
    assert [row["id"] for row in rows] == ["partial", "resume"]
    assert rows[0]["state"] == "interrupted"
    assert rows[1]["state"] == "applied"


def test_revoke_during_sync_does_not_read_the_next_message(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "revoke-mid-sync")
    stopped = sync(http, connection["id"], "cut")
    assert stopped["success"] is False and stopped["status"] == "revoked"
    assert "Must not be read" not in str(stopped)
    assert [task["title"] for task in tasks(http)] == ["Kept request"]
    again = sync(http, connection["id"], "after-revoke")
    assert again["success"] is False and again["status"] == "revoked"
    assert again["events_read"] == 0
    assert again["applied_message_ids"] == []
    assert [task["title"] for task in tasks(http)] == ["Kept request"]


def test_endpoint_revoke_stops_the_next_batch(tmp_path):
    _app, http = owner_app(tmp_path)
    connection = connect(http, "two-batches", key="connect-later")
    first = sync(http, connection["id"], "visible")
    assert first["success"] is True
    assert [task["title"] for task in tasks(http)] == ["Visible request"]
    revoked = http.post(
        f"/api/mailbox/connections/{connection['id']}/revocation",
        headers={"X-Operation-Id": "revoke-later"},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["reads_stopped"] is True
    blocked = sync(http, connection["id"], "later")
    assert blocked["success"] is False and blocked["events_read"] == 0
    assert [task["title"] for task in tasks(http)] == ["Visible request"]
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


def test_draft_confirm_requires_the_owner_and_reads_back(tmp_path):
    app, http = owner_app(tmp_path)
    connection = connect(http, "two-batches", key="connect-draft")
    synced = sync(http, connection["id"], "visible-draft")
    assert synced["success"] is True and synced["sent"] is False
    draft = proposal_for(proposals(http), "msg-visible")
    assert draft["kind"] == "mailbox_reply"
    assert draft["data"]["send"] is False
    assert draft["data"]["observed_at"].startswith("2026-11-03T02:00:00")
    task_id = tasks(http)[0]["id"]
    http.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Operation-Id": "pair-mailbox"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + http.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/mailbox/connections").status_code == 403
    hidden = display.get("/api/assistant/proposals")
    assert hidden.status_code == 200
    assert all(item["kind"] != "mailbox_reply" for item in hidden.json()["proposals"])
    assert display.post(
        f"/api/mailbox/connections/{connection['id']}/sync",
        headers={"X-Operation-Id": "display-sync"},
    ).status_code == 403
    refused = decide(display, draft["id"], "confirm", "display-confirm")
    assert refused.status_code == 403
    assert "Nothing was sent" not in str(detail(http, task_id)["evidence"])
    anonymous = TestClient(app)
    anonymous.headers.update({"X-Desk-Request": "1"})
    assert anonymous.get("/api/mailbox/connections").status_code == 403

    confirmed = decide(http, draft["id"], "confirm", "owner-confirm")
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["result"]["sent"] is False
    assert body["result"]["task"]["id"] == task_id
    read_back = detail(http, task_id)
    assert any(
        "msg-visible" in row["note"] and "Nothing was sent" in row["note"]
        for row in read_back["evidence"]
    )
    assert len(tasks(http)) == 1
    assert tasks(http)[0]["waiting_for"] == "Owner reply"


def test_invalid_fixture_is_rejected_before_import(tmp_path):
    _app, http = owner_app(tmp_path)
    rejected = http.post(
        "/api/mailbox/connections",
        json={"fixture": "invalid-duplicate"},
        headers={"X-Operation-Id": "bad-fixture"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "FIXTURE_INVALID"
    assert http.get("/api/mailbox/connections").json()["connections"] == []
    traversal = http.post(
        "/api/mailbox/connections",
        json={"fixture": "../thread-journey"},
        headers={"X-Operation-Id": "traversal"},
    )
    assert traversal.status_code == 422


def test_quiet_hours_suppress_the_mailbox_notice(tmp_path):
    _app, http = owner_app(tmp_path)
    preferences = WorkspacePreferences(quiet_start="00:00", quiet_end="00:00").model_dump()
    saved = http.post(
        "/api/workspace/preferences",
        json={"expected_version": 1, "preferences": preferences},
        headers={"X-Operation-Id": "all-quiet"},
    )
    assert saved.status_code == 200, saved.text
    connection = connect(http, "two-batches", key="quiet-connect")
    synced = sync(http, connection["id"], "quiet-sync")
    assert synced["success"] is True
    assert [task["title"] for task in tasks(http)] == ["Visible request"]
    assert notices(http) == []
