from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from senplate_api.app import create_app, passwords
from senplate_api.config import Settings
from senplate_api.models import Base, Membership, User, Workspace

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api():
    data = json.loads((ROOT / ".runtime/config.json").read_text())
    url = make_url(data["database_url"]).set(database="senplate_test")
    assert url.host == "127.0.0.1" and url.database == "senplate_test" and url.port == 55437
    assert (ROOT / ".runtime/SENPLATE_LOCAL_ONLY").exists()
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ws = Workspace(name="Demo dining room")
        other = Workspace(name="Other room")
        db.add_all([ws, other])
        db.flush()
        ids = {}
        for username, role in [("manager", "manager"), ("staff", "staff"), ("viewer", "viewer"), ("personal", None)]:
            user = User(username=username, name=username, password_hash=passwords.hash("fixture-password"))
            db.add(user)
            db.flush()
            ids[username] = user.id
            if role:
                db.add(Membership(user_id=user.id, workspace_id=ws.id, role=role))
        workspace_id, other_id = ws.id, other.id
        db.commit()
    cfg = Settings(url.render_as_string(hide_password=False), "fixture-device-key", "fixture-simulator-key", True,
                   console_key="fixture-console-key", console_workspace_id=workspace_id)
    app = create_app(cfg)
    with TestClient(app) as client:
        def login(username):
            r = client.post("/v1/auth/sessions", json={"username": username, "password": "fixture-password"})
            assert r.status_code == 200
            return {"Authorization": "Bearer " + r.json()["access_token"], "X-Context-ID": workspace_id}
        headers = {name: login(name) for name in ids}
        # Avoid cookie fallback masking an intentionally missing Authorization header.
        client.cookies.clear()
        machine = {"X-Device-Key": cfg.simulator_key}
        key = str(uuid4())
        res = client.post("/v1/dev/runs", headers={**machine, "Idempotency-Key": key}, json={
            "workspace_id": workspace_id, "client_operation_id": key})
        assert res.status_code == 200, res.text
        run = res.json()
        yield {"client": client, "headers": headers, "machine": machine, "run": run,
               "engine": engine, "workspace": workspace_id, "other": other_id, "ids": ids, "settings": cfg}
    engine.dispose()


def get_state(a):
    r = a["client"].get(f"/v1/stations/{a['run']['station_id']}/snapshot", headers=a["headers"]["manager"])
    assert r.status_code == 200, r.text
    return r.json()


def step(a, action, amount=0, seconds=0, key=None):
    key = key or str(uuid4())
    r = a["client"].post(f"/v1/dev/runs/{a['run']['run_id']}/actions",
                          headers={**a["machine"], "Idempotency-Key": key}, json={
                              "client_operation_id": key, "action": action, "amount_g": amount, "seconds": seconds})
    assert r.status_code == 200, r.text
    return r


def low(a):
    step(a, "consume", 300)
    step(a, "consume", 500)
    return get_state(a)["recommendation"]


def decision(a, rec, actor="manager", choice="accept", key=None, **extra):
    key = key or str(uuid4())
    return a["client"].post(f"/v1/recommendations/{rec['id']}/decisions",
        headers={**a["headers"][actor], "Idempotency-Key": key}, json={"client_operation_id": key,
        "expected_version": rec["version"], "decision": choice, **extra})


def act(a, task, action, key=None, **extra):
    key = key or str(uuid4())
    return a["client"].post(f"/v1/tasks/{task['id']}/actions",
        headers={**a["headers"]["manager"], "Idempotency-Key": key}, json={"client_operation_id": key,
        "expected_version": task["version"], "action": action, **extra})


def test_complete_replenishment_chain_and_retries(api):
    a = api
    rec = low(a)
    assert get_state(a)["net_g"] == 700
    key = str(uuid4())
    accepted = decision(a, rec, key=key)
    assert accepted.status_code == 200
    assert decision(a, rec, key=key).json() == accepted.json()
    assert decision(a, rec, key=key, accepted_g=1500).status_code == 409
    assert len(get_state(a)["tasks"]) == 1
    for action in ["start", "mark_ready", "begin_replenishment"]:
        task = get_state(a)["tasks"][0]
        assert act(a, task, action).status_code == 200
        assert get_state(a)["net_g"] == 700
    task = get_state(a)["tasks"][0]
    assert task["eligible_events"] == []
    assert act(a, task, "confirm_replenishment").status_code == 409
    addition_key = str(uuid4())
    step(a, "add", 1000, key=addition_key)
    step(a, "add", 1000, key=addition_key)
    state = get_state(a)
    added = next(e for e in state["events"] if e["kind"] == "food_added")
    assert [e["id"] for e in state["tasks"][0]["eligible_events"]] == [added["id"]]
    confirm_key = str(uuid4())
    result = act(a, task, "confirm_replenishment", key=confirm_key, physical_event_id=added["id"])
    assert result.status_code == 200, result.text
    assert act(a, task, "confirm_replenishment", key=confirm_key, physical_event_id=added["id"]).json() == result.json()
    state = get_state(a)
    assert (state["net_g"], state["provided_g"], state["removed_g"], state["incoming_g"]) == (1700, 2500, 800, 0)
    assert state["tasks"][0]["actual_added_g"] == 1000
    assert state["tasks"][0]["state"] == "completed"
    operation = a["client"].get(f"/v1/operations/{confirm_key}", headers=a["headers"]["manager"])
    assert operation.json() == result.json()


def test_two_staff_accept_concurrently(api):
    a = api
    rec = low(a)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda actor: decision(a, rec, actor=actor), ["manager", "staff"]))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert len(get_state(a)["tasks"]) == 1


def test_event_order_is_stable_when_demo_time_is_unchanged(api):
    a = api
    decision(a, low(a))
    for action in ["start", "mark_ready"]:
        assert act(a, get_state(a)["tasks"][0], action).status_code == 200
    events = get_state(a)["events"]
    assert [e["kind"] for e in events[:4]] == ["task_ready", "task_in_progress", "recommendation_accepted", "recommendation_created"]
    assert all(events[i]["sequence"] > events[i + 1]["sequence"] for i in range(len(events) - 1))


def test_version_conflict_and_assignment(api):
    a = api
    rec = low(a)
    decision(a, rec)
    old = get_state(a)["tasks"][0]
    assert act(a, old, "start").status_code == 200
    assert act(a, old, "mark_ready").json()["error"]["code"] == "VERSION_CONFLICT"
    task = get_state(a)["tasks"][0]
    key = str(uuid4())
    r = a["client"].post(f"/v1/tasks/{task['id']}/actions", headers={**a["headers"]["staff"], "Idempotency-Key": key},
                         json={"client_operation_id": key, "expected_version": task["version"], "action": "mark_ready"})
    assert r.status_code == 403


@pytest.mark.parametrize("action,status", [("remove", "absent"), ("unstable", "unstable")])
def test_invalid_samples_are_not_consumption(api, action, status):
    a = api
    step(a, action)
    state = get_state(a)
    assert state["measurement_status"] == status
    assert state["net_g"] is None and state["last_valid_g"] == 1500
    assert state["removed_g"] == 0 and state["recommendation"] is None
    step(a, "restore")
    assert get_state(a)["provided_g"] == 1500


def test_stale_then_offline_and_heartbeat_does_not_fake_measurement(api):
    a = api
    low(a)
    step(a, "advance", seconds=6)
    s = get_state(a)
    assert (s["freshness"], s["connectivity"]) == ("stale", "online")
    assert s["last_valid_g"] == 700 and s["recommendation"] is None
    step(a, "advance", seconds=10)
    s = get_state(a)
    assert s["connectivity"] == "offline"
    r = a["client"].post("/v1/device/heartbeats", headers=a["machine"], json={
        "session_id": s["run_id"], "device_id": s["device_id"], "at": s["clock_at"]})
    assert r.status_code == 200
    s = get_state(a)
    assert s["connectivity"] == "online" and s["freshness"] == "stale"


def test_occlusion_keeps_valid_weight_and_incoming_suppresses_duplicates(api):
    a = api
    rec = low(a)
    step(a, "occlude")
    s = get_state(a)
    assert s["vision_status"] == "occluded" and s["net_g"] == 700
    assert decision(a, rec).status_code == 200
    step(a, "consume", 100, seconds=1)
    s = get_state(a)
    assert s["incoming_g"] == 1000 and s["recommendation"] is None
    assert s["suggestion_reason"] == "INCOMING_SUFFICIENT"


def test_rebind_and_end_of_service_invalidate_suggestion(api):
    a = api
    rec = low(a)
    step(a, "rebind")
    assert decision(a, rec).status_code == 409
    current = get_state(a)["recommendation"]
    step(a, "closing")
    assert get_state(a)["recommendation"] is None
    assert get_state(a)["suggestion_reason"] == "SERVICE_ENDING"
    if current:
        assert decision(a, current).status_code == 409


def make_observation(a, sequence, weight=600, **kwargs):
    s = get_state(a)
    return {"observation_id": str(uuid4()), "session_id": s["run_id"], "device_id": s["device_id"],
            "boot_id": s["boot_id"], "sequence": sequence, "observed_at": s["clock_at"],
            "gross_g": weight + 500, "tare_g": 500, "net_g": weight, "weight_quality": "valid",
            "pan_presence": "present", "vision_status": "available", "calibration_version": "fixture",
            "binding_revision": s["binding_revision"], **kwargs}


def test_duplicate_reordered_and_inconsistent_packets(api):
    a = api
    low(a)
    item = make_observation(a, 4)
    older = make_observation(a, 3, 900,
        observed_at=(datetime.fromisoformat(item["observed_at"]) - timedelta(seconds=1)).isoformat())
    r = a["client"].post("/v1/device/observations/batch", headers=a["machine"],
                          json={"observations": [item, item, older]})
    assert [x["status"] for x in r.json()["results"]] == ["accepted", "duplicate", "accepted_historical"]
    assert get_state(a)["net_g"] == 600
    conflict = {**item, "net_g": 500, "gross_g": 1000}
    bad = make_observation(a, 5, gross_g=42)
    r = a["client"].post("/v1/device/observations/batch", headers=a["machine"], json={"observations": [conflict, bad]})
    assert all(x["status"] == "rejected" for x in r.json()["results"])
    assert get_state(a)["net_g"] == 600


def test_auth_context_and_machine_boundaries(api):
    a = api
    path = f"/v1/workspaces/{a['workspace']}/overview"
    assert a["client"].get(path).status_code == 401
    assert a["client"].get(path, headers=a["headers"]["personal"]).status_code == 403
    assert a["client"].get(path, headers={**a["headers"]["manager"], "X-Context-ID": "personal"}).status_code == 403
    assert a["client"].get(f"/v1/workspaces/{a['other']}/overview", headers=a["headers"]["manager"]).status_code == 403
    rec = low(a)
    assert decision(a, rec, actor="viewer").status_code == 403
    key = str(uuid4())
    assert a["client"].post("/v1/dev/runs", headers={**a["headers"]["manager"], "Idempotency-Key": key}, json={
        "client_operation_id": key, "workspace_id": a["workspace"]}).status_code == 401
    item = make_observation(a, 4)
    assert a["client"].post("/v1/device/observations/batch", headers=a["machine"],
                           json={"observations": [{**item, "data_origin": "hardware"}]}).status_code == 422


def test_revoke_membership_blocks_cached_operation_and_websocket(api):
    a = api
    rec = low(a)
    key = str(uuid4())
    assert decision(a, rec, key=key).status_code == 200
    with a["client"].websocket_connect(f"/v1/events?context_id={a['workspace']}", headers=a["headers"]["manager"]) as ws:
        assert ws.receive_json()["type"] == "state.changed"
        with Session(a["engine"]) as db:
            db.get(Membership, (a["ids"]["manager"], a["workspace"])).active = False
            db.commit()
        with pytest.raises(Exception):
            ws.receive_json()
    assert decision(a, rec, key=key).status_code == 403


def test_persistence_after_api_recreation_and_origin_filter(api):
    a = api
    rec = low(a)
    assert decision(a, rec).status_code == 200
    with TestClient(create_app(a["settings"])) as fresh:
        r = fresh.get(f"/v1/stations/{a['run']['station_id']}/snapshot", headers=a["headers"]["manager"])
        assert r.json()["net_g"] == 700 and len(r.json()["tasks"]) == 1
        r = fresh.get(f"/v1/stations/{a['run']['station_id']}/events?data_origin=hardware", headers=a["headers"]["manager"])
        assert r.json()["items"] == []


def test_old_event_cannot_verify_new_task_and_no_zero_adjustment(api):
    a = api
    rec = low(a)
    assert decision(a, rec, choice="adjust", accepted_g=0, reason_code="SMALL_BATCH").status_code == 422
    assert decision(a, rec, choice="adjust", accepted_g=900, reason_code="SMALL_BATCH").status_code == 200
    task = get_state(a)["tasks"][0]
    for action in ["start", "mark_ready"]:
        assert act(a, task, action).status_code == 200
        task = get_state(a)["tasks"][0]
    step(a, "add", 100)
    old_event = next(e for e in get_state(a)["events"] if e["kind"] == "food_added")
    assert act(a, task, "begin_replenishment").status_code == 200
    task = get_state(a)["tasks"][0]
    assert act(a, task, "confirm_replenishment", physical_event_id=old_event["id"]).status_code == 409
    step(a, "add", 850)
    newest = next(e for e in get_state(a)["events"] if e["kind"] == "food_added")
    assert act(a, task, "confirm_replenishment", physical_event_id=newest["id"]).status_code == 200
    assert get_state(a)["tasks"][0]["actual_added_g"] == 850


def test_logout_invalidates_token(api):
    a = api
    h = a["headers"]["manager"]
    assert a["client"].delete("/v1/auth/sessions/current", headers=h).status_code == 200
    assert a["client"].get("/v1/me", headers=h).status_code == 401
