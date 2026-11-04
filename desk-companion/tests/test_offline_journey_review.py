"""Cross-journey regressions found while independently reviewing PRs 78–82."""

import json
from datetime import UTC, datetime

import pytest
from desk.app import create_app
from desk.access import digest
from desk.store import encode
from desk.workspace_data import WorkspacePreferences
from test_mailbox_journey import (
    connect as mail_connect,
    owner_app,
    restore_backup,
    sync as mail_sync,
    tasks,
)
from test_offline_calendar_journey import connect as calendar_connect, sync as calendar_sync
from test_shopping_fixtures import (
    build,
    cart,
    connect,
    login,
    shopping_notices,
    sync,
    write_fixture,
    snapshot,
    work_runs,
    paired_client,
)


def test_shopping_quiet_notice_is_delivered_after_quiet_hours(tmp_path, monkeypatch):
    app, fixtures, moment = build(tmp_path, monkeypatch)
    http = login(app)
    settings = WorkspacePreferences(quiet_start="08:00", quiet_end="12:00").model_dump()
    response = http.post(
        "/api/workspace/preferences",
        json={"expected_version": 1, "preferences": settings},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "quiet"},
    )
    assert response.status_code == 200
    write_fixture(fixtures, "quiet-cart", [cart()])
    cid = connect(http, "quiet-cart", "connect")
    sync(http, cid)
    assert shopping_notices(http) == []
    moment[0] = datetime(2026, 11, 3, 5, tzinfo=UTC)
    app.state.runtime.tick()
    assert len(shopping_notices(http)) == 1
    app.state.runtime.tick()
    assert len(shopping_notices(http)) == 1
    http.close()


def test_mailbox_backup_rejects_cross_thread_target_and_impossible_cursor(tmp_path):
    _, http = owner_app(tmp_path / "runtime")
    cid = mail_connect(http, "thread-journey")["id"]
    mail_sync(http, cid, "first")
    document = http.get("/api/exchange/backup.json").json()
    for label in ("task-target", "cursor"):
        bad = json.loads(json.dumps(document))
        bundle = bad["payload"]["mailbox_bundle"]
        if label == "task-target":
            bundle["messages"][0]["task_id"] = "f" * 32
        else:
            bundle["connections"][0]["history_cursor"] = "999999"
        bad["sha256"] = digest(encode(bad["payload"]))
        response = http.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(bad)},
            headers={"X-Operation-Id": label},
        )
        assert response.status_code == 422, response.text
    http.close()


def test_calendar_backup_after_later_batch_interrupt_remains_restorable(tmp_path, monkeypatch):
    fixtures = tmp_path / "calendar"
    fixtures.mkdir()
    monkeypatch.setattr("desk.offline_calendar.fixture.ROOT", fixtures)

    def item(seq, hour):
        return {
            "op": "upsert",
            "item": {
                "id": "meeting",
                "sequence": seq,
                "title": "Review",
                "observed_at": "2026-11-03T01:00:00Z",
                "start_local": f"2026-11-05T{hour:02d}:00:00",
                "end_local": f"2026-11-05T{hour:02d}:30:00",
            },
        }

    fixture = {
        "format": "desk-calendar-fixture-v1",
        "account_id": "account",
        "calendar_id": "calendar",
        "batches": [
            {"id": "first", "events": [item(1, 10)]},
            {"id": "second", "events": [item(2, 11), {"op": "interrupt"}, item(3, 12)]},
        ],
    }
    (fixtures / "partial.json").write_text(json.dumps(fixture))
    app, http = owner_app(tmp_path / "runtime")
    cid = calendar_connect(http, "partial")["id"]
    calendar_sync(http, cid, "first")
    stopped = calendar_sync(http, cid, "second")
    assert stopped["success"] is False
    assert stopped["connection"]["history_cursor"] == "1"
    backup = http.get("/api/exchange/backup.json").json()
    _, restored = owner_app(tmp_path / "restored")
    restore_backup(restored, backup, "preview", "restore")
    result = calendar_sync(restored, cid, "continue")
    assert result["success"] is True
    assert result["connection"]["history_cursor"] == "3"
    assert len(tasks(restored)) == 1
    assert tasks(restored)[0]["due_local"] == "2026-11-05T12:00:00"
    http.close()
    restored.close()


def calendar_item(uid, seq, start="10:00", end="11:00", op="upsert"):
    return {
        "op": op,
        "item": {
            "id": uid,
            "sequence": seq,
            "title": uid,
            "observed_at": "2026-11-03T01:00:00Z",
            "start_local": f"2026-11-05T{start}:00",
            "end_local": f"2026-11-05T{end}:00",
        },
    }


def local_calendar_fixture(tmp_path, monkeypatch, batches):
    directory = tmp_path / "calendar-inputs"
    directory.mkdir()
    monkeypatch.setattr("desk.offline_calendar.fixture.ROOT", directory)
    fixture = {
        "format": "desk-calendar-fixture-v1",
        "account_id": "account",
        "calendar_id": "calendar",
        "batches": batches,
    }
    (directory / "review.json").write_text(json.dumps(fixture))
    return owner_app(tmp_path / "runtime")


def test_calendar_rejects_conflicting_operation_for_same_revision(tmp_path, monkeypatch):
    _, http = local_calendar_fixture(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "batch",
                "events": [calendar_item("meeting", 1), calendar_item("meeting", 1, op="cancel")],
            }
        ],
    )
    response = http.post(
        "/api/offline-calendar/connections",
        json={"fixture": "review"},
        headers={"X-Operation-Id": "connect"},
    )
    assert response.status_code == 422, response.text
    assert tasks(http) == []
    http.close()


def test_calendar_conflict_can_resolve_and_reappear(tmp_path, monkeypatch):
    _, http = local_calendar_fixture(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "overlap",
                "events": [calendar_item("a", 1), calendar_item("b", 2, "10:30", "11:30")],
            },
            {"id": "resolve", "events": [calendar_item("b", 3, "12:00", "13:00")]},
            {"id": "reappear", "events": [calendar_item("b", 4, "10:30", "11:30")]},
        ],
    )
    cid = calendar_connect(http, "review")["id"]
    for key in ("first", "second", "third"):
        calendar_sync(http, cid, key)
    notices = http.get("/api/notices").json()["notices"]
    assert len([n for n in notices if n["kind"] == "calendar_conflict"]) == 2
    http.close()


def test_calendar_conflict_with_local_event_survives_backup(tmp_path, monkeypatch):
    _, http = local_calendar_fixture(
        tmp_path, monkeypatch, [{"id": "batch", "events": [calendar_item("imported", 1)]}]
    )
    response = http.post(
        "/api/events",
        json={
            "event": {
                "title": "Existing local appointment",
                "start_local": "2026-11-05T10:15:00",
                "end_local": "2026-11-05T10:45:00",
                "timezone": "Asia/Hong_Kong",
            }
        },
        headers={"X-Operation-Id": "local-event"},
    )
    assert response.status_code == 200, response.text
    local_id = response.json()["event_ids"][0]
    cid = calendar_connect(http, "review")["id"]
    calendar_sync(http, cid, "sync")
    backup = http.get("/api/exchange/backup.json").json()
    assert len(backup["payload"]["offline_calendar_bundle"]["conflicts"]) == 1
    preview = http.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(backup)},
        headers={"X-Operation-Id": "preview"},
    )
    assert preview.status_code == 200, preview.text
    removed = http.post(
        f"/api/events/{local_id}/actions",
        json={"action": "delete", "scope": "series", "expected_version": 1},
        headers={"X-Operation-Id": "delete-local"},
    )
    assert removed.status_code == 200, removed.text
    after = http.get("/api/exchange/backup.json").json()
    assert after["payload"]["offline_calendar_bundle"]["conflicts"] == []
    assert (
        http.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(after)},
            headers={"X-Operation-Id": "after-delete"},
        ).status_code
        == 200
    )
    http.close()


def test_shopping_event_ids_are_scoped_to_their_connection(tmp_path, monkeypatch):
    app, fixtures, _ = build(tmp_path, monkeypatch)
    http = login(app)
    for name in ("shop-a", "shop-b"):
        write_fixture(fixtures, name, [cart()])
        sync(http, connect(http, name, name))
    assert len(shopping_notices(http)) == 2
    http.close()


def test_mailbox_older_later_batch_does_not_rewind_a_thread(tmp_path, monkeypatch):
    fixtures = tmp_path / "mail"
    fixtures.mkdir()
    monkeypatch.setattr("desk.mailbox_fixture.ROOT", fixtures)

    def message(identifier, history, hour):
        return {
            "op": "message",
            "message": {
                "id": identifier,
                "thread_id": "thread",
                "history_id": history,
                "observed_at": "2026-11-03T01:00:00Z",
                "sender": "sender@example.test",
                "subject": "Review",
                "deadline_local": f"2026-11-04T{hour:02d}:00:00",
            },
        }

    fixture = {
        "format": "desk-mailbox-fixture-v1",
        "account_id": "account",
        "address": "owner@example.test",
        "batches": [
            {"id": "newer", "events": [message("new", 2, 15)]},
            {"id": "delayed", "events": [message("old", 1, 11)]},
        ],
    }
    (fixtures / "late-mail.json").write_text(json.dumps(fixture))
    _, http = owner_app(tmp_path / "runtime")
    cid = mail_connect(http, "late-mail")["id"]
    mail_sync(http, cid, "first")
    original = tasks(http)[0]
    mail_sync(http, cid, "second")
    final = tasks(http)[0]
    assert final["id"] == original["id"]
    assert final["due_local"] == original["due_local"]
    http.close()


def test_combined_backup_preserves_all_journeys_and_quiet_deliveries(tmp_path, monkeypatch):
    app, fixtures, moment = build(tmp_path, monkeypatch)
    http = login(app)
    http.headers.update({"X-Desk-Request": "1"})
    preferences = WorkspacePreferences(quiet_start="08:00", quiet_end="12:00").model_dump()
    assert (
        http.post(
            "/api/workspace/preferences",
            json={"expected_version": 1, "preferences": preferences},
            headers={"X-Operation-Id": "quiet"},
        ).status_code
        == 200
    )
    mail = mail_connect(http, "two-batches", "mail-connect")
    mail_sync(http, mail["id"], "mail-sync")
    calendar = calendar_connect(http, "soon-meeting", "calendar-connect")
    calendar_sync(http, calendar["id"], "calendar-sync")
    write_fixture(fixtures, "cart-backup", [cart()])
    shop_id = connect(http, "cart-backup", "shop-connect")
    sync(http, shop_id)
    original_task_ids = {task["id"] for task in tasks(http)}
    kinds = {item["kind"] for item in http.get("/api/assistant/proposals").json()["proposals"]}
    assert "shopping_advice" in kinds
    display = paired_client(app, http)
    visible = display.get("/api/assistant/proposals").json()["proposals"]
    assert not {"mailbox_reply", "calendar_advice", "shopping_advice"} & {
        item["kind"] for item in visible
    }
    backup = http.get("/api/exchange/backup.json").json()
    for key in ("mailbox_bundle", "shopping_bundle", "offline_calendar_bundle"):
        assert backup["payload"][key]["notice_holds"]
    restored_app = create_app(
        tmp_path / "restored", password="fixture", scheduler=False, clock=lambda: moment[0]
    )
    restored = login(restored_app)
    restored.headers.update({"X-Desk-Request": "1"})
    restore_backup(restored, backup, "preview", "apply")
    assert {task["id"] for task in tasks(restored)} == original_task_ids
    # Restore intentionally keeps the target desk's notification preferences.
    assert (
        restored.post(
            "/api/workspace/preferences",
            json={"expected_version": 1, "preferences": preferences},
            headers={"X-Operation-Id": "restored-quiet"},
        ).status_code
        == 200
    )
    restored_app.state.runtime.tick()
    assert restored.get("/api/notices").json()["notices"] == []
    moment[0] = datetime(2026, 11, 3, 5, tzinfo=UTC)
    restored_app.state.runtime.tick()
    notices = restored.get("/api/notices").json()["notices"]
    assert len(notices) == 3
    restored_app.state.runtime.tick()
    assert len(restored.get("/api/notices").json()["notices"]) == 3
    # Portable task backup does not retain execution authority. Explicit sync
    # must create exactly one paused tracking run for the existing task.
    sync(restored, shop_id)
    linked = snapshot(restored, shop_id)["subjects"][0]
    run = restored.get(f"/api/agent-runs/{linked['work_run_id']}")
    assert run.status_code == 200, run.text
    assert run.json()["run"]["state"] == "paused"
    assert run.json()["run"]["task_ids"] == [linked["task_id"]]
    sync(restored, shop_id)
    assert len(work_runs(restored)) == 1
    assert {task["id"] for task in tasks(restored)} == original_task_ids
    display.close()
    http.close()
    restored.close()


@pytest.mark.parametrize("kind", ["mailbox", "offline-calendar"])
@pytest.mark.parametrize("stop", ["revoke", "logout"])
def test_revocation_and_logout_stop_the_next_admitted_item(tmp_path, monkeypatch, kind, stop):
    fixtures = tmp_path / "input"
    fixtures.mkdir()
    if kind == "mailbox":
        monkeypatch.setattr("desk.mailbox_fixture.ROOT", fixtures)
        events = [
            {
                "op": "message",
                "message": {
                    "id": f"message-{n}",
                    "thread_id": f"thread-{n}",
                    "history_id": n,
                    "observed_at": "2026-11-03T01:00:00Z",
                    "sender": "sender@example.test",
                    "subject": f"Task {n}",
                },
            }
            for n in (1, 2)
        ]
        fixture = {
            "format": "desk-mailbox-fixture-v1",
            "account_id": "account",
            "address": "owner@example.test",
            "batches": [{"id": "batch", "events": events}],
        }
    else:
        monkeypatch.setattr("desk.offline_calendar.fixture.ROOT", fixtures)
        events = [
            {
                "op": "upsert",
                "item": {
                    "id": f"meeting-{n}",
                    "sequence": n,
                    "observed_at": "2026-11-03T01:00:00Z",
                    "title": f"Meeting {n}",
                    "start_local": f"2026-11-05T{9 + n:02d}:00:00",
                    "end_local": f"2026-11-05T{9 + n:02d}:30:00",
                },
            }
            for n in (1, 2)
        ]
        fixture = {
            "format": "desk-calendar-fixture-v1",
            "account_id": "account",
            "calendar_id": "calendar",
            "batches": [{"id": "batch", "events": events}],
        }
    (fixtures / "stop-check.json").write_text(json.dumps(fixture))
    app, http = owner_app(tmp_path / "runtime")
    response = http.post(
        f"/api/{kind}/connections",
        json={"fixture": "stop-check"},
        headers={"X-Operation-Id": "connect"},
    )
    assert response.status_code == 200, response.text
    cid = response.json()["connection"]["id"]
    create = app.state.runtime.tasks.create
    stopped = False

    def create_then_stop(*args, **kwargs):
        nonlocal stopped
        result = create(*args, **kwargs)
        if not stopped:
            stopped = True
            if stop == "logout":
                reply = http.delete("/api/session")
            else:
                reply = http.post(
                    f"/api/{kind}/connections/{cid}/revocation",
                    headers={"X-Operation-Id": "revoke"},
                )
            assert reply.status_code == 200, reply.text
        return result

    monkeypatch.setattr(app.state.runtime.tasks, "create", create_then_stop)
    result = http.post(f"/api/{kind}/connections/{cid}/sync", headers={"X-Operation-Id": "sync"})
    if stop == "logout":
        assert result.status_code == 403, result.text
        assert (
            http.post(
                "/api/session", json={"username": "owner", "password": "fixture-only"}
            ).status_code
            == 200
        )
    else:
        assert result.status_code == 200, result.text
        assert result.json()["success"] is False
        assert result.json()["status"] == "revoked"
    assert len(tasks(http)) == 1
    http.close()
