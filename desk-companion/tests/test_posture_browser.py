import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.posture import PostureAction, PosturePreferences
from desk.posture_browser import BrowserCamera, BrowserObservations
from desk.schemas import SettingsInput
from desk.store import DomainError
from test_posture import frame


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 11, 16, 2, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: clock[0])
    r = app.state.runtime
    session = r.store.create_owner_session()
    r.posture.action(
        PostureAction(
            action="configure",
            preferences=PosturePreferences(enabled=True, camera_source="browser"),
        ),
        "enable",
    )
    return r, session, clock, TestClient(app)


def camera():
    return BrowserCamera(client_id=str(uuid4()), camera_id="browser-fixture")


def batch(clock, lease, **changes):
    observation = frame(clock[0].timestamp(), 0, camera_id="browser-fixture").model_dump()
    return BrowserObservations(
        lease=lease["lease"],
        batch={
            "source": "live",
            "boot_id": lease["boot_id"],
            "observations": [observation],
            **changes,
        },
    )


def test_only_one_browser_and_only_landmarks_from_the_admitted_camera(world):
    r, session, clock, _ = world
    lease = r.browser_posture.claim(camera(), session)
    with pytest.raises(DomainError, match="POSTURE_CAMERA_BUSY"):
        r.browser_posture.claim(camera(), session)
    with pytest.raises(DomainError, match="POSTURE_CAMERA_SOURCE_CHANGED"):
        r.browser_posture.ingest(batch(clock, lease, source="replay"), session)
    result = r.browser_posture.ingest(batch(clock, lease), session)
    assert result["posture"]["connected"] and result["accepted_sequence"] == 0
    another = r.store.create_owner_session()
    with pytest.raises(DomainError, match="LEASE_EXPIRED"):
        r.browser_posture.ingest(batch(clock, lease), another)
    r.browser_posture.release(lease["lease"], another)
    assert r.browser_posture.lease is not None
    r.browser_posture.release(lease["lease"], session)
    assert r.browser_posture.lease is None


def test_offline_or_hidden_or_paused_observations_do_not_continue(world):
    r, session, clock, _ = world
    lease = r.browser_posture.claim(camera(), session)
    clock[0] += timedelta(seconds=5)
    with pytest.raises(DomainError, match="LEASE_EXPIRED"):
        r.browser_posture.ingest(batch(clock, lease), session)
    next_lease = r.browser_posture.claim(camera(), session)
    r.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True), "hide"
    )
    with pytest.raises(DomainError):
        r.browser_posture.ingest(batch(clock, next_lease), session)
    r.posture.action(PostureAction(action="pause"), "pause")
    with pytest.raises(DomainError, match="CAPTURE_DISABLED"):
        r.browser_posture.claim(camera(), session)


def test_same_browser_reload_replaces_its_lease_without_accepting_late_frames(world):
    r, session, clock, _ = world
    client = camera()
    previous = r.browser_posture.claim(client, session)
    current = r.browser_posture.claim(client, session)
    assert previous["lease"] != current["lease"]
    with pytest.raises(DomainError, match="LEASE_EXPIRED"):
        r.browser_posture.ingest(batch(clock, previous), session)
    assert r.browser_posture.ingest(batch(clock, current), session)["accepted_sequence"] == 0


def test_browser_route_is_owner_authenticated_and_camera_agent_yields(world):
    r, session, _, client = world
    assert (
        client.post(
            "/api/posture/browser/session",
            json=camera().model_dump(),
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 403
    )
    client.cookies.set("desk_companion_session", session)
    response = client.post(
        "/api/posture/browser/session", json=camera().model_dump(), headers={"X-Desk-Request": "1"}
    )
    assert response.status_code == 200
    agent = TestClient(client.app)
    agent.headers.update(
        {
            "Authorization": "Bearer "
            + json.loads((r.store.directory / "agent.json").read_text())["token"],
            "X-Desk-Request": "1",
        }
    )
    assert agent.get("/api/agent/config").json()["camera_enabled"] is False
