"""One reviewed local occurrence, from the ordinary composer through durable delivery."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.routines import RoutineAction, RoutineService
from desk.store import DomainError
from desk.tool_policy import execute_tool
from session_protocol_fixture import install_session_protocol


ASK = {"message": "明天这一次不用提醒我，之后照常", "language": "zh"}


def owner(app):
    client = TestClient(app)
    client.cookies.set("desk_companion_session", app.state.store.create_owner_session())
    return client


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_WEB_PUSH", "0")
    clock = [datetime(2026, 10, 12, tzinfo=UTC)]
    app = create_app(
        tmp_path, password="fixture", clock=lambda: clock[0], scheduler=False, connector_configs=()
    )
    protocol = install_session_protocol(app.state.runtime)
    return app, owner(app), clock, protocol


def post(client, path, body, key=None):
    return client.post(
        "/api/" + path,
        json=body,
        headers={
            "X-Desk-Request": "1",
            "X-Operation-Id": key or uuid4().hex,
        },
    )


def create(client, **fields):
    response = post(
        client,
        "routines",
        {
            "title": "Morning review",
            "skill": "day_briefing",
            "frequency": "daily",
            "start_local": "2026-10-12T09:00",
            "timezone": "Asia/Hong_Kong",
            **fields,
        },
    )
    assert response.is_success, response.text
    return response.json()["routine"]


def details(client, routine):
    response = client.get("/api/routines/" + routine["id"])
    assert response.is_success, response.text
    return response.json()


def set_hidden(client, hidden, version):
    response = post(
        client,
        "settings",
        {
            "expected_version": version,
            "hide_private": hidden,
            "timezone": "Asia/Hong_Kong",
        },
    )
    assert response.is_success, response.text


def test_composer_selects_one_original_dated_occurrence_and_reads_it_back(desk):
    app, client, clock, protocol = desk
    runtime = app.state.runtime
    hk = create(client)
    la = create(client, timezone="America/Los_Angeles", frequency="weekly", skill="task_review")
    event = post(
        client,
        "events",
        {
            "event": {
                "title": hk["title"],
                "start_local": "2026-10-13T09:00",
                "end_local": "2026-10-13T09:30",
                "recurrence": {"frequency": "daily", "interval": 2},
                "reminder_minutes": [10],
            }
        },
    )
    assert event.is_success, event.text
    (event_id,) = event.json()["event_ids"]
    original_event = client.get("/api/events/" + event_id).json()
    configured = post(
        client,
        "workspace/preferences",
        {
            "expected_version": 1,
            "preferences": {
                "daily_brief_enabled": True,
                "quiet_enabled": True,
                "proactivity": "low",
            },
        },
    )
    assert configured.is_success, configured.text
    prefs = runtime.data.preferences()
    with runtime.store.connection() as conn:
        calendar = runtime.store.data(conn)
        settings = runtime.store.settings(conn)

    response = post(client, "assistant/messages/stream", ASK, "ask")
    events = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    assert events[-1]["type"] == "done", events
    draft = events[-1]["reply"]["proposal"]
    assert draft["kind"] == "routine_skip" and not protocol.creations
    assert post(client, "assistant/messages", ASK, "ask").json()["proposal"]["id"] == draft["id"]
    (review,) = client.get("/api/assistant/proposals").json()["proposals"]
    assert review["id"] == draft["id"]
    assert {
        (c["routine_id"], c["occurrence_key"], c["timezone"]) for c in review["data"]["choices"]
    } == {
        (hk["id"], "2026-10-13T09:00", "Asia/Hong_Kong"),
        (la["id"], "2026-10-12T09:00", "America/Los_Angeles"),
    }
    decision = f"assistant/proposals/{draft['id']}/decisions"
    assert post(client, decision, {"action": "confirm"}).status_code == 422
    assert post(client, decision, {"action": "confirm", "routine_id": "0" * 32}).status_code == 422
    assert details(client, hk)["skipped_dates"] == details(client, la)["skipped_dates"] == []
    choice = {"action": "confirm", "routine_id": hk["id"]}
    confirmed = post(client, decision, choice, "pick").json()
    assert confirmed["result"]["skipped_date"] == "2026-10-13"
    assert confirmed["result"]["routine"]["next_run_at"] == hk["next_run_at"]
    assert post(client, decision, choice, "pick").json() == confirmed
    assert post(client, decision, {**choice, "routine_id": la["id"]}, "pick").status_code == 409
    assert details(client, hk)["skipped_dates"] == ["2026-10-13"]
    assert details(client, la)["routine"] == la
    assert runtime.data.preferences() == prefs
    assert client.get("/api/events/" + event_id).json() == original_event
    with runtime.store.connection() as conn:
        assert runtime.store.settings(conn) == settings and runtime.store.data(conn) == calendar

    # Today's result remains pending through the skipped day. The other routine still runs.
    clock[0] += timedelta(hours=2)
    runtime.tick()
    clock[0] += timedelta(days=1)
    runtime.tick()
    client = owner(app)
    (kept,) = details(client, hk)["runs"]
    assert kept["occurrence_key"] == "2026-10-12T09:00" and kept["delivery_state"] == "pending"
    assert details(client, la)["runs"][0]["occurrence_key"] == "2026-10-12T09:00"
    claim = post(client, "routines/deliveries/claim", {}).json()
    assert kept["id"] in claim["delivery_ids"] and claim["claimed"] == 2
    clock[0] += timedelta(days=1)
    runtime.tick()
    latest = details(owner(app), hk)
    assert [r["occurrence_key"] for r in latest["runs"]] == ["2026-10-14T09:00", "2026-10-12T09:00"]
    assert latest["routine"]["start_local"] == hk["start_local"]


def test_review_cancellation_and_private_retries(desk):
    app, client, _, _ = desk
    runtime = app.state.runtime
    routine = create(client, title="Owner's private review")
    draft = post(client, "assistant/messages", ASK, "ask").json()["proposal"]
    path = f"assistant/proposals/{draft['id']}/decisions"
    paired = TestClient(app)
    paired.cookies.set(
        "desk_companion_device", runtime.access.enrol_display("fixture", "pair")["token"]
    )
    for denied in (
        post(paired, "assistant/messages", ASK),
        post(paired, path, {"action": "confirm"}),
    ):
        assert denied.status_code == 403
    assert paired.get("/api/assistant/proposals").json()["proposals"] == []
    set_hidden(client, True, version=1)
    assert client.get("/api/assistant/proposals").json()["proposals"] == []
    for denied in (
        post(client, "assistant/messages", ASK, "ask"),
        post(client, path, {"action": "confirm"}),
        post(
            client,
            f"routines/{routine['id']}/actions",
            {
                "action": "skip",
                "expected_version": 1,
                "local_date": "2026-10-13",
            },
        ),
    ):
        assert denied.status_code == 403 and routine["title"] not in denied.text
    set_hidden(client, False, version=2)
    for _ in range(2):
        assert post(client, path, {"action": "cancel"}, "cancel").json()["state"] == "cancelled"
    assert post(client, path, {"action": "confirm"}).status_code == 410
    retry = post(client, "assistant/messages", ASK, "ask").json()
    assert not retry["saved"] and retry["proposal"] is None
    assert details(client, routine)["routine"] == routine
    set_hidden(client, True, version=3)
    assert post(client, "assistant/messages", ASK, "ask").status_code == 403


def test_named_review_recovers_confirmed_date_after_interrupted_reply(desk, tmp_path, monkeypatch):
    app, client, clock, protocol = desk
    routine = create(client, title="晨间简报")
    other = create(client, title="作业检查")
    request = {"message": "明天的晨间简报这次不用提醒我，之后照常", "language": "zh"}
    draft = post(client, "assistant/messages", request, "ask-named").json()["proposal"]
    (review,) = client.get("/api/assistant/proposals").json()["proposals"]
    (selected,) = review["data"]["choices"]
    assert selected["routine_id"] == routine["id"]
    decision = f"assistant/proposals/{draft['id']}/decisions"

    def interrupted(*args, **kwargs):
        raise RuntimeError("synthetic lost acknowledgment")

    monkeypatch.setattr(app.state.runtime.assistant, "_finish_confirmation", interrupted)
    with pytest.raises(RuntimeError, match="synthetic lost acknowledgment"):
        post(client, decision, {"action": "confirm"}, "confirm")
    assert not protocol.requests
    restarted = create_app(tmp_path, clock=lambda: clock[0], scheduler=False, connector_configs=())
    client = owner(restarted)
    assert client.get("/api/assistant/proposals").json()["proposals"] == []
    reply = post(client, "assistant/messages", request, "ask-named").json()
    assert reply["saved"] and reply["proposal"] is None
    confirmed = post(client, decision, {"action": "confirm"}, "confirm").json()
    assert confirmed["result"]["skipped_date"] == "2026-10-13"
    assert details(client, routine)["routine"]["version"] == 2
    assert details(client, other)["skipped_dates"] == []
    set_hidden(client, True, version=1)
    assert post(client, "assistant/messages", request, "ask-named").status_code == 403
    assert post(client, decision, {"action": "confirm"}, "confirm").status_code == 403


def test_provider_review_rechecks_version_and_due_instant(desk):
    app, client, clock, protocol = desk
    routine = create(client, title="Private lab review", start_local="2026-10-12T08:02")
    protocol.next_calls = [("routine_skip_draft", {"title": routine["title"], "when": "next"})]
    draft = post(
        client, "assistant/messages", {"message": "Leave out just my upcoming lab check."}
    ).json()
    assert draft["proposal"]["kind"] == "routine_skip" and not draft["saved"]
    assert len(protocol.functions) == 1 and routine["title"] not in json.dumps(protocol.functions)
    (review,) = client.get("/api/assistant/proposals").json()["proposals"]
    assert review["data"]["choices"][0]["occurrence_key"] == "2026-10-12T08:02"
    path = f"assistant/proposals/{review['id']}/decisions"
    # Confirmation at the scheduled instant cannot skip a different occurrence.
    clock[0] += timedelta(minutes=2)
    assert (
        post(client, path, {"action": "confirm"}).json()["error"]["code"]
        == "ROUTINE_OCCURRENCE_UNAVAILABLE"
    )
    app.state.runtime.routines.tick()
    (pending,) = details(client, routine)["runs"]
    assert pending["delivery_state"] == "pending"
    action_path = f"routines/{routine['id']}/actions"
    future = post(
        client,
        action_path,
        {
            "expected_version": 1,
            "action": "skip",
            "local_date": "2026-10-14",
        },
    )
    assert future.is_success, future.text
    assert details(client, routine)["runs"] == [pending]
    new = post(client, "assistant/messages", ASK).json()["proposal"]
    assert post(client, action_path, {"expected_version": 2, "action": "pause"}).is_success
    assert (
        post(client, f"assistant/proposals/{new['id']}/decisions", {"action": "confirm"}).json()[
            "error"
        ]["code"]
        == "VERSION_CONFLICT"
    )
    assert details(client, routine)["skipped_dates"] == ["2026-10-14"]


def test_restart_on_skipped_fold_coalesces_backlog_and_never_replays_on_rollback(desk, tmp_path):
    _, client, clock, _ = desk
    clock[0] = datetime(2026, 10, 31, tzinfo=UTC)
    client = owner(client.app)
    routine = create(client, timezone="America/New_York", start_local="2026-10-31T01:30")
    path = f"routines/{routine['id']}/actions"
    skip = {"action": "skip", "local_date": "2026-11-01", "expected_version": 1}
    receipt = post(client, path, skip, "fold").json()
    # October 31 was never ticked. Both UTC instants for November 1's repeated local minute pass.
    clock[0] = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    restarted = create_app(tmp_path, clock=lambda: clock[0], scheduler=False, connector_configs=())
    client = owner(restarted)
    assert post(client, path, skip, "fold").json() == receipt
    routines = restarted.state.runtime.routines
    for hour in (5, 6):
        clock[0] = clock[0].replace(hour=hour)
        routines.tick()
    state = details(client, routine)
    assert state["runs"] == [] and routines.listing()["pending_count"] == 0
    assert state["routine"]["next_run_at"].startswith("2026-11-02T06:30")
    assert state["routine"]["last_scheduled_at"].startswith("2026-11-01T05:30")
    clock[0] -= timedelta(days=1)
    paused = post(client, path, {"action": "pause", "expected_version": 2}).json()["routine"]
    resumed = post(
        client, path, {"action": "resume", "expected_version": paused["version"]}
    ).json()["routine"]
    assert resumed["next_run_at"] == state["routine"]["next_run_at"]
    clock[0] = datetime(2026, 11, 4, 7, tzinfo=UTC)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: routines.tick(), range(2)))
    (latest,) = routines.detail(routine["id"])["runs"]
    assert latest["occurrence_key"] == "2026-11-04T01:30" and latest["result"]["catch_up"]


def test_weekly_gap_wrong_weekday_and_one_off(desk):
    app, _, clock, _ = desk
    clock[0] = datetime(2026, 3, 1, tzinfo=UTC)
    client = owner(app)
    weekly = create(
        client, timezone="America/New_York", frequency="weekly", start_local="2026-03-01T02:30"
    )
    path = f"routines/{weekly['id']}/actions"
    for day in ("2026-03-08", "2026-03-09", "2026-02-22"):
        denied = post(client, path, {"action": "skip", "local_date": day, "expected_version": 1})
        assert denied.json()["error"]["code"] == "ROUTINE_OCCURRENCE_UNAVAILABLE"
    assert post(
        client, path, {"action": "skip", "local_date": "2026-03-15", "expected_version": 1}
    ).is_success
    clock[0] += timedelta(hours=8)
    app.state.runtime.routines.tick()
    assert details(owner(app), weekly)["routine"]["next_run_at"].startswith("2026-03-22T06:30")
    client = owner(app)
    once = create(client, frequency="once", start_local="2026-03-02T09:00")
    path = f"routines/{once['id']}/actions"
    assert post(client, path, {"action": "skip", "expected_version": 1}).status_code == 422
    assert (
        post(
            client, path, {"action": "skip", "expected_version": 1, "local_date": "2026-02-30"}
        ).status_code
        == 422
    )
    assert (
        post(
            client, path, {"action": "pause", "expected_version": 1, "local_date": "2026-03-02"}
        ).status_code
        == 422
    )
    result = post(
        client, path, {"action": "skip", "expected_version": 1, "local_date": "2026-03-02"}
    ).json()
    assert result["routine"]["status"] == "completed" and result["routine"]["next_run_at"] is None
    clock[0] += timedelta(days=2)
    app.state.runtime.routines.tick()
    assert details(owner(app), once)["runs"] == []


def test_legacy_definition_concurrent_skips_and_old_action_receipt(desk):
    app, client, _, _ = desk
    runtime = app.state.runtime
    routine = create(client)
    service = runtime.routines
    pause = RoutineAction(action="pause", expected_version=1)
    previous = service.action(routine["id"], pause, "legacy-pause")
    with runtime.store.connection(write=True) as conn:
        # The previous release had this definition/operation format and no skip table.
        conn.execute("DROP TABLE routine_skips")
        assert json.loads(
            conn.execute("SELECT request FROM operations WHERE id='legacy-pause'").fetchone()[0]
        ) == {
            "type": "routine_action",
            "id": routine["id"],
            "action": "pause",
            "expected_version": 1,
        }
    service = RoutineService(runtime)
    assert service.action(routine["id"], pause, "legacy-pause") == previous
    service.action(routine["id"], RoutineAction(action="resume", expected_version=2), "resume")
    skip = RoutineAction(action="skip", local_date="2026-10-12", expected_version=3)
    with ThreadPoolExecutor(2) as pool:
        a, b = pool.map(lambda _: service.action(routine["id"], skip, "same"), range(2))
    assert a == b and a["routine"]["version"] == 4
    assert a["routine"]["next_run_at"].startswith("2026-10-13T01:00")
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        service.action(routine["id"], skip.model_copy(update={"local_date": "2026-10-13"}), "same")
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        service.action(routine["id"], pause, "other")
    assert details(client, routine)["skipped_dates"] == ["2026-10-12"]


def test_unmatched_request_and_paired_tool_cannot_propose_a_change(desk):
    app, client, _, protocol = desk
    create(client, frequency="weekly")
    reply = post(client, "assistant/messages", ASK).json()
    assert reply["kind"] == "clarify" and not reply["saved"] and not protocol.creations
    refused = execute_tool(
        app.state.runtime,
        "routine_skip_draft",
        {"when": "next"},
        "voice/paired",
        scope="paired",
        allow_memory=False,
    )
    assert refused["error"] == "OWNER_SIGN_IN_REQUIRED"
    assert client.get("/api/assistant/proposals").json()["proposals"] == []
