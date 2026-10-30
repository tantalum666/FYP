import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.routines import DeliveryClaim, RoutineAction, RoutineInput, RoutineService
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventInput, SettingsInput
from desk.store import DomainError, Store
from desk.tasks import TaskInput


@pytest.fixture
def desk(tmp_path):
    clock = [datetime(2026, 10, 12, 0, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    if not hasattr(runtime, "routines"):
        runtime.routines = RoutineService(runtime)
    return runtime, clock


def create(runtime, **fields):
    data = {
        "title": "Morning review",
        "skill": "day_briefing",
        "frequency": "daily",
        "start_local": "2026-10-12T09:00",
        "timezone": "Asia/Hong_Kong",
        **fields,
    }
    return runtime.routines.create(RoutineInput(**data), uuid4().hex)["routine"]


def action(runtime, routine, verb, key=None):
    return runtime.routines.action(
        routine["id"],
        RoutineAction(action=verb, expected_version=routine["version"]),
        key or uuid4().hex,
    )["routine"]


def test_due_result_persists_once_and_coalesces_restart_backlog(desk):
    runtime, clock = desk
    routine = create(runtime)
    clock[0] += timedelta(days=4, hours=2)
    runtime.routines.tick()
    runtime.routines.tick()
    results = runtime.routines.detail(routine["id"])
    assert len(results["runs"]) == 1
    assert results["runs"][0]["occurrence_key"] == "2026-10-16T09:00"
    assert results["runs"][0]["result"]["catch_up"]
    assert results["routine"]["next_run_at"].startswith("2026-10-17T01:00")
    recovered = RoutineService(runtime)
    recovered.tick()
    assert recovered.detail(routine["id"])["runs"] == results["runs"]


def test_one_off_is_completed_and_never_repeats(desk):
    runtime, clock = desk
    routine = create(runtime, frequency="once")
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    clock[0] += timedelta(days=20)
    runtime.routines.tick()
    result = runtime.routines.detail(routine["id"])
    assert result["routine"]["status"] == "completed"
    assert result["routine"]["next_run_at"] is None
    assert len(result["runs"]) == 1


def test_duplicate_creation_and_optimistic_version(desk):
    runtime, _ = desk
    payload = RoutineInput(
        title="Review", skill="task_review", frequency="daily", start_local="2026-10-12T09:00"
    )
    saved = runtime.routines.create(payload, "create-routine")
    assert runtime.routines.create(payload, "create-routine") == saved
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        runtime.routines.create(payload.model_copy(update={"title": "Other"}), "create-routine")
    paused = action(runtime, saved["routine"], "pause", "pause")
    assert action(runtime, saved["routine"], "pause", "pause") == paused
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        action(runtime, saved["routine"], "cancel")


def test_pause_resume_skips_paused_recurrences_and_cancel_stops(desk):
    runtime, clock = desk
    routine = action(runtime, create(runtime), "pause")
    clock[0] += timedelta(days=3, hours=2)
    runtime.routines.tick()
    assert not runtime.routines.detail(routine["id"])["runs"]
    routine = action(runtime, routine, "resume")
    assert routine["next_run_at"].startswith("2026-10-16T01:00")
    runtime.routines.tick()
    assert not runtime.routines.detail(routine["id"])["runs"]
    clock[0] += timedelta(days=1)
    runtime.routines.tick()
    assert runtime.routines.listing()["pending_count"] == 1
    action(runtime, routine, "cancel")
    assert runtime.routines.listing()["pending_count"] == 0
    clock[0] += timedelta(days=100)
    runtime.routines.tick()
    assert len(runtime.routines.detail(routine["id"])["runs"]) == 1


def test_paused_one_off_can_resume_overdue_once(desk):
    runtime, clock = desk
    routine = action(runtime, create(runtime, frequency="once"), "pause")
    clock[0] += timedelta(days=2)
    action(runtime, routine, "resume")
    runtime.routines.tick()
    result = runtime.routines.detail(routine["id"])
    assert result["routine"]["status"] == "completed" and len(result["runs"]) == 1


def test_weekly_preserves_anchor_weekday(desk):
    runtime, clock = desk
    routine = create(runtime, frequency="weekly")
    clock[0] += timedelta(days=17, hours=2)
    runtime.routines.tick()
    result = runtime.routines.detail(routine["id"])
    assert result["runs"][0]["occurrence_key"] == "2026-10-26T09:00"
    assert result["routine"]["next_run_at"].startswith("2026-11-02T01:00")


def test_daily_dst_gap_skips_instead_of_shifting(desk):
    runtime, clock = desk
    clock[0] = datetime(2026, 3, 7, 0, tzinfo=UTC)
    routine = create(runtime, start_local="2026-03-07T02:30", timezone="America/New_York")
    clock[0] = datetime(2026, 3, 7, 8, tzinfo=UTC)
    runtime.routines.tick()
    assert runtime.routines.detail(routine["id"])["routine"]["next_run_at"].startswith(
        "2026-03-09T06:30"
    )
    clock[0] = datetime(2026, 3, 8, 12, tzinfo=UTC)
    runtime.routines.tick()
    assert len(runtime.routines.detail(routine["id"])["runs"]) == 1


def test_daily_dst_fold_runs_first_occurrence_once(desk):
    runtime, clock = desk
    clock[0] = datetime(2026, 10, 31, 0, tzinfo=UTC)
    routine = create(runtime, start_local="2026-10-31T01:30", timezone="America/New_York")
    clock[0] = datetime(2026, 11, 1, 5, 31, tzinfo=UTC)
    runtime.routines.tick()
    clock[0] = datetime(2026, 11, 1, 6, 31, tzinfo=UTC)
    runtime.routines.tick()
    result = runtime.routines.detail(routine["id"])
    assert len(result["runs"]) == 1
    assert result["runs"][0]["scheduled_at"].startswith("2026-11-01T05:30")
    assert result["routine"]["next_run_at"].startswith("2026-11-02T06:30")


@pytest.mark.parametrize(
    "fields",
    [
        {"start_local": "2026-11-01T01:30", "timezone": "America/New_York"},
        {"start_local": "2026-03-08T02:30", "timezone": "America/New_York"},
        {"start_local": "2026-10-12T09:00:01"},
        {"start_local": "2026-10-12T09:00+08:00"},
        {"timezone": "invalid/zone"},
        {"skill": "shell"},
        {"url": "https://example.com"},
        {"frequency": "every_second"},
        {"title": " "},
    ],
)
def test_unsafe_or_invalid_schedule_inputs_are_rejected(desk, fields):
    with pytest.raises(ValidationError):
        create(desk[0], **fields)


def test_past_initial_time_is_rejected(desk):
    with pytest.raises(DomainError, match="ROUTINE_START_IN_PAST"):
        create(desk[0], start_local="2026-10-12T07:59")


def test_one_pending_per_routine_claims_latest_without_repeat(desk):
    runtime, clock = desk
    routine = create(runtime)
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    first_id = runtime.routines.detail(routine["id"])["runs"][0]["id"]
    clock[0] += timedelta(days=3)
    runtime.routines.tick()
    assert runtime.routines.listing()["pending_count"] == 1
    claim = runtime.routines.claim(DeliveryClaim(), "claim-first")
    assert claim["delivery_ids"] == [first_id]
    assert claim["deliveries"][0]["coalesced_delivery"]
    assert claim["deliveries"][0]["result"]["local_date"] == "2026-10-15"
    assert runtime.routines.claim(DeliveryClaim(), "claim-first") == claim
    assert not runtime.routines.claim(DeliveryClaim(), "claim-other")["deliveries"]
    recovered = RoutineService(runtime)
    recovered.tick()
    assert not recovered.claim(DeliveryClaim(), "claim-restart")["deliveries"]


def test_global_pending_limit_and_all_results_are_retained(desk):
    runtime, clock = desk
    routines = [create(runtime, title=f"Routine {i}") for i in range(22)]
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    assert runtime.routines.listing()["pending_count"] == 20
    assert all(len(runtime.routines.detail(r["id"])["runs"]) == 1 for r in routines)
    assert len(runtime.routines.claim(DeliveryClaim(limit=20), "claim-all")["deliveries"]) == 20


def test_concurrent_ticks_and_claims_do_not_duplicate(desk):
    runtime, clock = desk
    routine = create(runtime)
    clock[0] += timedelta(hours=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: runtime.routines.tick(), range(2)))
        replies = list(
            pool.map(
                lambda i: runtime.routines.claim(DeliveryClaim(), f"concurrent-{i}"),
                range(2),
            )
        )
    assert len(runtime.routines.detail(routine["id"])["runs"]) == 1
    assert sum(r["claimed"] for r in replies) == 1


def test_readonly_skill_result_privacy_and_retry_projection(desk):
    runtime, clock = desk
    task = runtime.tasks.create(
        TaskInput(
            title="Private project",
            due_local="2026-10-12T10:00",
            next_step="Secret notes",
        ),
        "task",
    )["task"]
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Private appointment",
                start_local="2026-10-12T11:00",
                end_local="2026-10-12T12:00",
                notes="Secret appointment notes",
            )
        ),
        "event",
    )
    routine = create(runtime)
    with runtime.store.connection() as conn:
        before = {
            t: [tuple(row) for row in conn.execute(f"SELECT * FROM {t}")]
            for t in ("tasks", "events", "exceptions", "computer_jobs")
        }
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    output = runtime.routines.detail(routine["id"])["runs"][0]["result"]
    assert output["counts"] == {"events": 1, "tasks": 1, "overdue_tasks": 1, "waiting_tasks": 0}
    assert any(i["id"] == task["id"] and i["title"] == "Private project" for i in output["items"])
    with runtime.store.connection() as conn:
        after = {t: [tuple(row) for row in conn.execute(f"SELECT * FROM {t}")] for t in before}
        persisted = conn.execute("SELECT result FROM routine_runs").fetchone()[0]
    assert before == after
    assert "Private" not in persisted and "Secret" not in persisted
    assert "Secret" not in json.dumps(output)
    runtime.routines.claim(DeliveryClaim(), "claim-private")
    runtime.store.update_settings(
        SettingsInput(timezone="Asia/Hong_Kong", hide_private=True, expected_version=1),
        "hide",
    )
    replay = runtime.routines.claim(DeliveryClaim(), "claim-private")
    assert "Private project" not in json.dumps(replay)
    assert "Private appointment" not in json.dumps(replay)
    assert all(
        i["redacted"] and i["title"] == "" for i in replay["deliveries"][0]["result"]["items"]
    )


def test_task_review_uses_open_tasks_not_calendar_and_copies_no_notes(desk):
    runtime, clock = desk
    runtime.tasks.create(
        TaskInput(
            title="Waiting task",
            status="waiting",
            waiting_for="Colleague",
            next_step="Private note",
        ),
        "waiting",
    )
    routine = create(runtime, skill="task_review")
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    result = runtime.routines.detail(routine["id"])["runs"][0]["result"]
    assert result["counts"]["waiting_tasks"] == 1
    assert result["counts"]["events"] == 0
    assert result["suggested_action"] == "review_tasks"
    assert "Colleague" not in json.dumps(result) and "Private note" not in json.dumps(result)


def test_bounded_history_and_clock_rollback_do_not_repeat(desk):
    runtime, clock = desk
    routine = create(runtime)
    clock[0] += timedelta(hours=2)
    for _ in range(55):
        runtime.routines.tick()
        runtime.routines.claim(DeliveryClaim(), uuid4().hex)
        clock[0] += timedelta(days=1)
    assert len(runtime.routines.detail(routine["id"])["runs"]) == 50
    clock[0] -= timedelta(days=45)
    routine = action(runtime, routine, "pause")
    routine = action(runtime, routine, "resume")
    runtime.routines.tick()
    assert runtime.routines.listing()["pending_count"] == 0
    assert datetime.fromisoformat(routine["next_run_at"]) > clock[0] + timedelta(days=40)


def test_runtime_tick_and_owner_only_routes(tmp_path):
    clock = [datetime(2026, 10, 12, 0, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture-only", clock=lambda: clock[0], scheduler=False)
    with TestClient(app) as client:
        assert client.get("/api/routines").status_code == 403
        headers = {"X-Desk-Request": "1", "X-Operation-Id": "create-routine"}
        assert (
            client.post(
                "/api/session",
                headers=headers,
                json={"username": "owner", "password": "fixture-only"},
            ).status_code
            == 200
        )
        response = client.post(
            "/api/routines",
            headers=headers,
            json={
                "title": "Morning",
                "skill": "day_briefing",
                "frequency": "daily",
                "start_local": "2026-10-12T09:00",
                "timezone": "Asia/Hong_Kong",
            },
        )
        assert response.status_code == 200
        routine_id = response.json()["routine"]["id"]
        clock[0] += timedelta(hours=2)
        app.state.runtime.tick()
        assert len(client.get(f"/api/routines/{routine_id}").json()["runs"]) == 1
        assert (
            client.post(
                "/api/routines/deliveries/claim",
                headers={
                    **headers,
                    "X-Operation-Id": "claim-api",
                },
                json={},
            ).json()["claimed"]
            == 1
        )
        client.cookies.clear()
        assert (
            client.post("/api/routines/deliveries/claim", headers=headers, json={}).status_code
            == 403
        )


def test_bad_source_receipt_does_not_block_other_routine_or_repeat(desk, monkeypatch):
    runtime, clock = desk
    failing = create(runtime, skill="day_briefing")
    good = create(runtime, skill="task_review")
    original = runtime.routines._result

    def read(conn, routine, now):
        if routine["id"] == failing["id"]:
            raise ValueError("private text from a malformed source")
        return original(conn, routine, now)

    monkeypatch.setattr(runtime.routines, "_result", read)
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    runtime.routines.tick()
    bad = runtime.routines.detail(failing["id"])["runs"]
    assert len(bad) == 1 and bad[0]["result"]["status"] == "failed"
    assert "private text" not in json.dumps(bad)
    assert runtime.routines.detail(good["id"])["runs"][0]["result"]["status"] == "ready"


def test_hidden_privacy_blocks_routine_api_without_claiming(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        headers = {"X-Desk-Request": "1", "X-Operation-Id": "hide-api"}
        client.post(
            "/api/session", headers=headers, json={"username": "owner", "password": "fixture-only"}
        )
        app.state.store.update_settings(
            SettingsInput(timezone="Asia/Hong_Kong", hide_private=True, expected_version=1),
            "hide-settings",
        )
        assert client.get("/api/routines").json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
        assert (
            client.post("/api/routines/deliveries/claim", headers=headers, json={}).status_code
            == 403
        )
        with app.state.store.connection() as conn:
            assert conn.execute("SELECT 1 FROM operations WHERE id='hide-api'").fetchone() is None


@pytest.mark.parametrize("change", ["cancel_occurrence", "move_series"])
def test_removed_event_occurrence_is_unavailable_in_result_and_claim(desk, change):
    from desk.schemas import EventAction

    runtime, clock = desk
    payload = EventInput(
        title="Appointment", start_local="2026-10-12T11:00", end_local="2026-10-12T12:00"
    )
    event_id = runtime.store.create(CreateEvents(event=payload), "event")["event_ids"][0]
    routine = create(runtime)
    clock[0] += timedelta(hours=2)
    runtime.routines.tick()
    if change == "cancel_occurrence":
        mutation = EventAction(
            action="delete",
            scope="occurrence",
            expected_version=1,
            occurrence_key="2026-10-12T11:00",
        )
    else:
        mutation = EventAction(
            action="update",
            scope="series",
            expected_version=1,
            event=payload.model_copy(
                update={
                    "start_local": datetime(2026, 10, 13, 11),
                    "end_local": datetime(2026, 10, 13, 12),
                }
            ),
        )
    runtime.store.event_action(event_id, mutation, "event-changed")
    for result in [
        runtime.routines.detail(routine["id"])["runs"][0],
        runtime.routines.claim(DeliveryClaim(), "claim-changed")["deliveries"][0],
    ]:
        item = result["result"]["items"][0]
        assert item["available"] is False and item["title"] == ""
        assert result["result"]["counts"]["events"] == 1
