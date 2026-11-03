"""Offline shopping fixtures through the task, Work, draft and notice HTTP paths."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.permissions import SOFTWARE_PROPOSALS

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
