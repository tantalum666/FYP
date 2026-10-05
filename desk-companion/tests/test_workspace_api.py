from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.schemas import CreateEvents, EventInput


def test_paired_client_cannot_approve_devices_or_enable_motors_and_logout_revokes(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    owner = TestClient(app)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": uuid4().hex}
    assert (
        owner.post(
            "/api/session", json={"username": "owner", "password": "fixture-only"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        owner.post(
            "/api/devices/enrol-display", json={"name": "Test display"}, headers=headers
        ).status_code
        == 200
    )
    token = owner.cookies.get("desk_companion_device")
    device = TestClient(app)
    device.headers["Authorization"] = "Bearer " + token
    assert device.get("/api/workspace").json()["principal"]["kind"] == "display"
    assert "pairing" not in device.get("/api/workspace").json()
    assert (
        device.post("/api/pairing/codes", json={"kind": "controller"}, headers=headers).status_code
        == 403
    )
    assert device.post("/api/outputs/enable", headers=headers).status_code == 403
    assert owner.delete("/api/session", headers=headers).status_code == 200
    assert device.get("/api/workspace").status_code == 401


def test_display_away_privacy_is_projected_on_server_and_replay_requires_opt_in(tmp_path):
    now = datetime(2026, 10, 2, 12, tzinfo=UTC)
    app = create_app(
        tmp_path, clock=lambda: now, password="fixture-only", scheduler=False, allow_replay=False
    )
    store, runtime = app.state.store, app.state.runtime
    store.create(
        CreateEvents(
            event=EventInput(
                title="Private title", start_local="2026-10-02T21:00", end_local="2026-10-02T22:00"
            )
        ),
        "event",
    )
    client = TestClient(app)
    client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    from desk.posture import PosturePreferences

    runtime.posture.engine.configure(PosturePreferences(enabled=True))
    args = {"start": now.isoformat(), "end": (now + timedelta(days=1)).isoformat()}
    assert (
        client.get("/api/calendar", params=args).json()["occurrences"][0]["title"]
        == "Private title"
    )
    projected = client.get("/api/calendar", params={**args, "display": "true"}).json()
    assert projected["automatic_privacy"] and not projected["occurrences"][0]["title"]
    assert client.get("/api/agent/config").status_code == 401
    import json

    agent = json.loads((tmp_path / "agent.json").read_text())["token"]
    from test_posture import frame

    response = client.post(
        "/api/agent/observations",
        json={
            "boot_id": "fixture-boot",
            "source": "replay",
            "observations": [frame(now.timestamp(), 0).model_dump()],
        },
        headers={"Authorization": "Bearer " + agent, "X-Desk-Request": "1"},
    )
    assert response.status_code == 403
