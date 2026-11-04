"""Offline shopping fixtures through the task, Work, draft and notice HTTP paths."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.access import digest
from desk.app import create_app
from desk.permissions import SOFTWARE_PROPOSALS
from desk.store import encode

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


def headers(operation_id):
    return {**HEADERS, "X-Operation-Id": operation_id}


def event(event_id, seq, kind, **fields):
    body = {
        "event_id": event_id,
        "seq": seq,
        "observed_at": f"2026-11-03T02:{seq:02d}:00Z",
        "kind": kind,
    }
    body.update(fields)
    return body


def write_fixture(directory, fixture_id, events, threshold=500):
    directory.mkdir(parents=True, exist_ok=True)
    body = {
        "fixture_id": fixture_id,
        "merchant": "offline-fixture",
        "currency": "HKD",
        "price_drop_threshold_bps": threshold,
        "events": events,
    }
    (directory / f"{fixture_id}.json").write_text(json.dumps(body), encoding="utf-8")


def build(tmp_path, monkeypatch, name="runtime"):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setenv("DESK_SHOPPING_FIXTURES", str(fixtures))
    moment = [datetime(2026, 11, 3, 2, tzinfo=UTC)]
    app = create_app(
        tmp_path / name,
        password="fixture",
        scheduler=False,
        clock=lambda: moment[0],
    )
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


def close(client):
    client.close()


def connect(client, fixture_id, operation_id):
    response = client.post(
        "/api/shopping/connections",
        json={"fixture_id": fixture_id},
        headers=headers(operation_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checkout"] == "not_performed"
    return body["connection"]["id"]


def sync(client, connection_id, payload=None):
    response = client.post(
        f"/api/shopping/connections/{connection_id}/sync",
        json={} if payload is None else payload,
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checkout"] == "not_performed"
    return body


def tasks_of(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200, response.text
    return response.json()["tasks"]


def task_detail(client, task_id):
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200, response.text
    return response.json()


def shopping_notices(client):
    response = client.get("/api/notices")
    assert response.status_code == 200, response.text
    return [item for item in response.json()["notices"] if item["kind"] == "shopping"]


def shopping_drafts(client):
    response = client.get("/api/assistant/proposals")
    assert response.status_code == 200, response.text
    return [item for item in response.json()["proposals"] if item["kind"] == "shopping_advice"]


def work_runs(client):
    response = client.get("/api/agent-runs")
    assert response.status_code == 200, response.text
    return response.json()["runs"]


def snapshot(client, connection_id):
    response = client.get(f"/api/shopping/connections/{connection_id}")
    assert response.status_code == 200, response.text
    return response.json()


def cart(seq=1, event_id="cart-1", price=3200, quantity=2):
    return event(
        event_id,
        seq,
        "cart_change",
        sku="tissue-3ply",
        title="3-ply tissues",
        quantity=quantity,
        unit_price_cents=price,
    )


def paired_client(app, owner):
    enrolled = owner.post(
        "/api/devices/enrol-display",
        json={"name": "Fixture screen"},
        headers=headers("enrol-" + uuid4().hex),
    )
    assert enrolled.status_code == 200, enrolled.text
    client = TestClient(app)
    client.headers.update(
        {**HEADERS, "Authorization": "Bearer " + owner.cookies.get("desk_companion_device")}
    )
    return client


def cited(detail, fixture_id):
    return [
        row
        for row in detail["evidence"]
        if fixture_id in (row["note"] or "") and "observed at" in (row["note"] or "")
    ]


def test_gap_duplicate_continuity_and_silent_repeat(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    shipped = event(
        "ship-1",
        3,
        "order_shipped",
        order_id="ord-9",
        continues_subject="product:tissue-3ply",
    )
    write_fixture(fixtures, "tissue-gap", [cart(), dict(cart()), shipped])
    client = login(app)
    try:
        connection_id = connect(client, "tissue-gap", "connect-gap")
        first = sync(client, connection_id)
        assert first["completed"] is False
        assert first["stopped"] == "gap"
        assert first["cursor"] == 1
        assert [row["event_id"] for row in first["applied"]] == ["cart-1"]
        held = snapshot(client, connection_id)
        assert held["buffered"] == [{"event_id": "ship-1", "seq": 3}]
        assert len(tasks_of(client)) == 1
        assert len(shopping_notices(client)) == 1
        assert len(work_runs(client)) == 1
        task_id = held["subjects"][0]["task_id"]
        run_id = held["subjects"][0]["work_run_id"]
        run = client.get(f"/api/agent-runs/{run_id}")
        assert run.status_code == 200, run.text
        assert run.json()["run"]["state"] == "paused"
        assert run.json()["run"]["task_ids"] == [task_id]
        assert task_detail(client, task_id)["task"]["title"] == "3-ply tissues"
        assert cited(task_detail(client, task_id), "tissue-gap") == []

        write_fixture(
            fixtures,
            "tissue-gap",
            [
                cart(),
                event(
                    "price-small",
                    2,
                    "price_drop",
                    sku="tissue-3ply",
                    unit_price_cents=3100,
                ),
                cart(seq=4, event_id="cart-same", price=3100),
            ],
        )
        second = sync(client, connection_id)
        assert second["completed"] is True
        assert second["cursor"] == 4
        assert [row["event_id"] for row in second["applied"]] == [
            "price-small",
            "ship-1",
            "cart-same",
        ]
        assert [row["notified"] for row in second["applied"]] == [False, True, False]
        again = snapshot(client, connection_id)
        assert again["subjects"][0]["task_id"] == task_id
        assert again["subjects"][0]["work_run_id"] == run_id
        assert len(tasks_of(client)) == 1
        assert len(work_runs(client)) == 1
        assert len(shopping_notices(client)) == 2
        quiet = sync(client, connection_id)
        assert quiet["applied"] == []
        assert len(shopping_notices(client)) == 2
        assert len(tasks_of(client)) == 1
    finally:
        close(client)


def test_disconnect_restart_and_conflict_keep_one_task(tmp_path, monkeypatch):
    app, fixtures, moment = build(tmp_path, monkeypatch)
    events = [
        cart(),
        event("price-1", 2, "price_drop", sku="tissue-3ply", unit_price_cents=2900),
        event("stock-1", 3, "out_of_stock", sku="tissue-3ply"),
    ]
    write_fixture(fixtures, "tissue-sync", events)
    client = login(app)
    try:
        connection_id = connect(client, "tissue-sync", "connect-sync")
        dropped = sync(client, connection_id, {"disconnect_after": 0})
        assert dropped["completed"] is False
        assert dropped["stopped"] == "disconnected"
        assert dropped["cursor"] == 0
        assert tasks_of(client) == []
        partial = sync(client, connection_id, {"disconnect_after": 1})
        assert partial["completed"] is False
        assert partial["stopped"] == "disconnected"
        assert partial["cursor"] == 1
        task_id = snapshot(client, connection_id)["subjects"][0]["task_id"]
        assert len(shopping_notices(client)) == 1
    finally:
        close(client)

    restarted = create_app(
        tmp_path / "runtime",
        password="fixture",
        scheduler=False,
        clock=lambda: moment[0],
    )
    client = login(restarted)
    try:
        listed = client.get("/api/shopping/connections")
        assert listed.status_code == 200, listed.text
        assert listed.json()["connections"][0]["id"] == connection_id
        finished = sync(client, connection_id)
        assert finished["completed"] is True
        assert finished["cursor"] == 3
        assert len(tasks_of(client)) == 1
        assert tasks_of(client)[0]["id"] == task_id
        assert len(work_runs(client)) == 1
        assert len(shopping_notices(client)) == 3
        replay = sync(client, connection_id)
        assert replay["applied"] == []
        assert len(shopping_notices(client)) == 3

        events[0] = cart(price=1000)
        write_fixture(fixtures, "tissue-sync", events)
        conflict = client.post(
            f"/api/shopping/connections/{connection_id}/sync",
            json={},
            headers=HEADERS,
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "SHOPPING_EVENT_CONFLICT"
        assert snapshot(client, connection_id)["connection"]["cursor_seq"] == 3
        assert tasks_of(client)[0]["id"] == task_id
    finally:
        close(client)


def test_revoke_stops_before_another_fixture_read(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "tissue-revoke", [cart()])
    client = login(app)
    try:
        connection_id = connect(client, "tissue-revoke", "connect-revoke")
        assert sync(client, connection_id)["cursor"] == 1
        (fixtures / "tissue-revoke.json").write_text("{", encoding="utf-8")
        broken = client.post(
            f"/api/shopping/connections/{connection_id}/sync",
            json={},
            headers=HEADERS,
        )
        assert broken.status_code == 422
        assert broken.json()["error"]["code"] == "SHOPPING_FIXTURE_INVALID"
        revoked = client.post(
            f"/api/shopping/connections/{connection_id}/revocation",
            headers=headers("revoke-1"),
        )
        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["state"] == "revoked"
        blocked = client.post(
            f"/api/shopping/connections/{connection_id}/sync",
            json={},
            headers=HEADERS,
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "SHOPPING_REVOKED"
        assert len(tasks_of(client)) == 1
        checkout = client.post("/api/shopping/checkout", headers=HEADERS)
        assert checkout.status_code == 405
        assert checkout.json().get("checkout") != "performed"
    finally:
        close(client)


def test_draft_needs_owner_and_keeps_fields_the_event_omitted(tmp_path, monkeypatch):
    assert "shopping_advice" not in SOFTWARE_PROPOSALS
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "tissue-draft", [cart()])
    client = login(app)
    paired = None
    try:
        connection_id = connect(client, "tissue-draft", "connect-draft")
        sync(client, connection_id)
        task = tasks_of(client)[0]
        task_id = task["id"]
        draft = shopping_drafts(client)[0]
        assert draft["data"]["shopping"]["fixture_id"] == "tissue-draft"
        assert "2026-11-03T02:01:00" in draft["data"]["shopping"]["observed_at"]
        assert "No purchase or checkout" in draft["data"]["shopping"]["note"]
        assert cited(task_detail(client, task_id), "tissue-draft") == []

        current = task_detail(client, task_id)["task"]
        updated = {key: current[key] for key in TASK_FIELDS}
        updated["next_step"] = "Keep the 3-ply pack"
        saved = client.post(
            f"/api/tasks/{task_id}/actions",
            json={"action": "update", "expected_version": current["version"], "task": updated},
            headers=headers("keep-step"),
        )
        assert saved.status_code == 200, saved.text

        write_fixture(
            fixtures,
            "tissue-draft",
            [
                cart(),
                event(
                    "ship-1",
                    2,
                    "order_shipped",
                    order_id="ord-9",
                    continues_subject="product:tissue-3ply",
                ),
            ],
        )
        sync(client, connection_id)
        pending = shopping_drafts(client)
        assert len(pending) == 1
        assert pending[0]["data"]["shopping"]["event_id"] == "ship-1"
        assert "next_step" not in pending[0]["data"]["shopping"]["provided_fields"]
        paired = paired_client(app, client)
        denied = paired.post(
            f"/api/assistant/proposals/{pending[0]['id']}/decisions",
            json={"action": "confirm"},
            headers=headers("paired-confirm"),
        )
        assert denied.status_code == 403, denied.text
        assert paired.get("/api/shopping/connections").status_code == 403
        hidden = paired.get("/api/assistant/proposals")
        assert hidden.status_code == 200, hidden.text
        assert all(item["kind"] != "shopping_advice" for item in hidden.json()["proposals"])
        before = task_detail(client, task_id)
        assert before["task"]["status"] == "todo"
        assert before["task"]["next_step"] == "Keep the 3-ply pack"
        assert cited(before, "tissue-draft") == []

        confirmed = client.post(
            f"/api/assistant/proposals/{pending[0]['id']}/decisions",
            json={"action": "confirm"},
            headers=headers("owner-confirm"),
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["saved"] is True
        after = task_detail(client, task_id)
        assert after["task"]["id"] == task_id
        assert after["task"]["status"] == "waiting"
        assert after["task"]["next_step"] == "Keep the 3-ply pack"
        assert after["task"]["waiting_for"] == "Shipment ord-9"
        notes = cited(after, "tissue-draft")
        assert len(notes) == 1
        assert "2026-11-03T02:02:00" in notes[0]["note"]
        assert "No purchase or checkout was performed." in notes[0]["note"]
        assert shopping_drafts(client) == []

        write_fixture(
            fixtures,
            "tissue-cancel",
            [event("delay-1", 1, "order_delayed", order_id="ord-8", delay_reason="Weather")],
        )
        other = connect(client, "tissue-cancel", "connect-cancel")
        sync(client, other)
        delay = shopping_drafts(client)[0]
        cancelled = client.post(
            f"/api/assistant/proposals/{delay['id']}/decisions",
            json={"action": "cancel"},
            headers=headers("owner-cancel"),
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["saved"] is False
        delay_task = snapshot(client, other)["subjects"][0]["task_id"]
        assert cited(task_detail(client, delay_task), "tissue-cancel") == []
        replay = client.post(
            f"/api/assistant/proposals/{delay['id']}/decisions",
            json={"action": "confirm"},
            headers=headers("confirm-cancelled"),
        )
        assert replay.status_code == 410
        assert cited(task_detail(client, delay_task), "tissue-cancel") == []
    finally:
        if paired is not None:
            close(paired)
        close(client)


def test_unsafe_fixture_names_and_a_separate_login_cannot_see_another_desk(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    write_fixture(fixtures, "tissue-desk", [cart()])
    client = login(app)
    try:
        connection_id = connect(client, "tissue-desk", "connect-desk")
        for bad in ("Tissue", "../tissue-desk", "tissue-desk.json"):
            rejected = client.post(
                "/api/shopping/connections",
                json={"fixture_id": bad},
                headers=headers("bad-" + bad[-4:]),
            )
            assert rejected.status_code == 422, rejected.text
        client.delete("/api/session", headers=HEADERS)
        assert client.get("/api/shopping/connections").status_code == 403
        again = client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers=HEADERS,
        )
        assert again.status_code == 200, again.text
        listed = client.get("/api/shopping/connections")
        assert listed.status_code == 200
        assert listed.json()["connections"][0]["id"] == connection_id
    finally:
        close(client)

    other = create_app(tmp_path / "other-desk", password="fixture", scheduler=False)
    stranger = login(other)
    try:
        listed = stranger.get("/api/shopping/connections")
        assert listed.status_code == 200
        assert listed.json()["connections"] == []
    finally:
        close(stranger)


def test_shipped_sample_fixture_maps_one_paused_work_run(tmp_path):
    moment = [datetime(2026, 11, 3, 2, tzinfo=UTC)]
    app = create_app(
        tmp_path / "sample",
        password="fixture",
        scheduler=False,
        clock=lambda: moment[0],
    )
    client = login(app)
    try:
        connection_id = connect(client, "tissue-journey", "connect-sample")
        result = sync(client, connection_id)
        assert result["completed"] is True
        assert result["cursor"] == 2
        assert [row["notified"] for row in result["applied"]] == [True, True]
        assert len({row["task_id"] for row in result["applied"]}) == 1
        assert len(tasks_of(client)) == 1
        assert len(work_runs(client)) == 1
        assert work_runs(client)[0]["state"] == "paused"
        assert len(shopping_notices(client)) == 2
    finally:
        close(client)


def test_backup_restore_keeps_one_task_on_the_next_sync(tmp_path, monkeypatch):
    app, fixtures, _moment = build(tmp_path, monkeypatch)
    shipped = event(
        "ship-1",
        4,
        "order_shipped",
        order_id="ord-9",
        continues_subject="product:tissue-3ply",
    )
    write_fixture(
        fixtures,
        "tissue-backup",
        [
            cart(),
            event("price-1", 2, "price_drop", sku="tissue-3ply", unit_price_cents=2900),
            shipped,
        ],
    )
    client = login(app)
    try:
        connection_id = connect(client, "tissue-backup", "connect-backup")
        first = sync(client, connection_id)
        assert first["cursor"] == 2
        assert first["stopped"] == "gap"
        task = tasks_of(client)[0]
        noted = client.post(
            f"/api/tasks/{task['id']}/actions",
            json={
                "action": "update",
                "expected_version": task["version"],
                "task": {name: task[name] for name in TASK_FIELDS}
                | {"next_step": "Keep the 3-ply pack"},
            },
            headers=headers("keep-step"),
        )
        assert noted.status_code == 200, noted.text
        saved = snapshot(client, connection_id)
        document = client.get("/api/exchange/backup.json")
        assert document.status_code == 200, document.text
        backup = document.json()
        bundle = backup["payload"]["shopping_bundle"]
        assert bundle["connections"][0]["cursor_seq"] == 2
        assert bundle["connections"][0]["fixture_id"] == "tissue-backup"
        assert "created_session_hash" not in bundle["connections"][0]
        assert bundle["buffered"][0]["event_id"] == "ship-1"
        assert bundle["subjects"][0]["task_id"] == task["id"]
        assert bundle["subjects"][0]["work_run_id"] == saved["subjects"][0]["work_run_id"]
        encoded = json.dumps(backup)
        assert client.cookies.get("desk_companion_session") not in encoded
        assert saved["connection"]["created_session_hash"] not in encoded
        assert "password_hash" not in encoded
    finally:
        close(client)

    restored = create_app(
        tmp_path / "restored",
        password="fixture",
        scheduler=False,
        clock=app.state.runtime.store.clock,
    )
    owner = login(restored)
    paired = paired_client(restored, owner)
    try:
        assert paired.get("/api/exchange/backup.json").status_code == 403
        refused = paired.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(backup)},
            headers=headers("paired-preview"),
        )
        assert refused.status_code == 403, refused.text
        preview = owner.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(backup)},
            headers=headers("owner-preview"),
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["metadata"]["shopping_connections"] == 1
        assert preview.json()["metadata"]["shopping_restore"] == "merge_keep_existing"
        preview_id = preview.json()["preview_id"]
        blocked = paired.post(
            f"/api/exchange/{preview_id}/apply",
            json={},
            headers=headers("paired-apply"),
        )
        assert blocked.status_code == 403, blocked.text
        assert tasks_of(owner) == []
        applied = owner.post(
            f"/api/exchange/{preview_id}/apply",
            json={},
            headers=headers("owner-apply"),
        )
        assert applied.status_code == 200, applied.text
        assert applied.json()["shopping_created"] == 1
        restored_tasks = tasks_of(owner)
        assert len(restored_tasks) == 1
        assert restored_tasks[0]["id"] == task["id"]
        assert restored_tasks[0]["next_step"] == "Keep the 3-ply pack"
        again = snapshot(owner, connection_id)
        assert again["connection"]["cursor_seq"] == 2
        assert again["buffered"] == [{"event_id": "ship-1", "seq": 4}]
        assert again["subjects"][0]["task_id"] == task["id"]
        assert again["subjects"][0]["work_run_id"] == saved["subjects"][0]["work_run_id"]
        assert (
            again["connection"]["created_session_hash"]
            != saved["connection"]["created_session_hash"]
        )
        assert work_runs(owner) == []

        replay = sync(owner, connection_id)
        assert replay["applied"] == []
        assert replay["cursor"] == 2
        assert replay["completed"] is False
        assert replay["stopped"] == "gap"
        assert [item["id"] for item in tasks_of(owner)] == [task["id"]]
        assert len(work_runs(owner)) == 1
        restored_run = work_runs(owner)[0]
        assert restored_run["state"] == "paused"
        assert restored_run["task_ids"] == [task["id"]]
        assert shopping_notices(owner) == []

        write_fixture(
            fixtures,
            "tissue-backup",
            [
                cart(),
                event("price-1", 2, "price_drop", sku="tissue-3ply", unit_price_cents=2900),
                event(
                    "delay-1",
                    3,
                    "order_delayed",
                    order_id="ord-9",
                    continues_subject="product:tissue-3ply",
                    eta="2026-11-20",
                    delay_reason="Weather",
                ),
                shipped,
            ],
        )
        continued = sync(owner, connection_id)
        assert continued["cursor"] == 4
        assert continued["completed"] is True
        assert {row["task_id"] for row in continued["applied"]} == {task["id"]}
        assert [item["id"] for item in tasks_of(owner)] == [task["id"]]
        assert len(work_runs(owner)) == 1
        assert snapshot(owner, connection_id)["subjects"][0]["work_run_id"] == restored_run["id"]

        second = owner.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(backup)},
            headers=headers("preview-again"),
        )
        assert second.status_code == 200, second.text
        kept = owner.post(
            f"/api/exchange/{second.json()['preview_id']}/apply",
            json={},
            headers=headers("apply-again"),
        )
        assert kept.status_code == 200, kept.text
        assert kept.json()["shopping_created"] == 0
        assert kept.json()["shopping_kept"] == 1
        assert snapshot(owner, connection_id)["connection"]["cursor_seq"] == 4
        quiet = sync(owner, connection_id)
        assert quiet["applied"] == []
        assert quiet["cursor"] == 4
        assert [item["id"] for item in tasks_of(owner)] == [task["id"]]

        tampered = json.loads(json.dumps(backup))
        tampered["payload"]["shopping_bundle"]["connections"][0]["cursor_seq"] = 1
        tampered["sha256"] = digest(encode(tampered["payload"]))
        rejected = owner.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(tampered)},
            headers=headers("tampered-shopping"),
        )
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["error"]["code"] == "INVALID_BACKUP"
        assert [item["id"] for item in tasks_of(owner)] == [task["id"]]
        assert snapshot(owner, connection_id)["connection"]["cursor_seq"] == 4

        legacy = json.loads(json.dumps(backup))
        legacy["payload"].pop("shopping_bundle")
        legacy["sha256"] = digest(encode(legacy["payload"]))
        legacy_preview = owner.post(
            "/api/exchange/backup/preview",
            json={"content": json.dumps(legacy)},
            headers=headers("legacy-shopping"),
        )
        assert legacy_preview.status_code == 200, legacy_preview.text
        assert legacy_preview.json()["metadata"]["shopping_connections"] == 0
    finally:
        close(paired)
        close(owner)
