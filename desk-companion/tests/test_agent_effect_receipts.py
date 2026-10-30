"""Exact reviewed application intent must match operation receipt and saved result."""

import pytest

from desk.agent_tools import verify_proposal
from desk.schemas import CreateEvents, EventInput, EventAction
from desk.tasks import TaskInput, TaskAction
from desk.store import DomainError
from test_agent_runs import world as world, start, drive


def pending(world, kind):
    runtime = world[0]
    task = runtime.tasks.create(TaskInput(title="Selected task"), "initial-task")["task"]
    event = EventInput(
        title="Selected event", start_local="2026-10-13T10:00:00", end_local="2026-10-13T11:00:00"
    )
    event_id = runtime.store.create(CreateEvents(event=event), "initial-event")["event_ids"][0]
    values = {
        "task_create": {"tool": "task_create_draft", "arguments": {"title": "Expected task"}},
        "task_change": {
            "tool": "task_change_draft",
            "arguments": {
                "task_id": task["id"],
                "change": {"action": "note", "expected_version": 1, "note": "Expected note"},
            },
        },
        "calendar_create": {
            "tool": "calendar_create_draft",
            "arguments": {
                "event": {**event.model_dump(mode="json"), "title": "Expected calendar event"}
            },
        },
        "calendar_change": {
            "tool": "calendar_change_draft",
            "arguments": {
                "event_id": event_id,
                "change": {
                    "action": "update",
                    "scope": "series",
                    "expected_version": 1,
                    "event": {**event.model_dump(mode="json"), "title": "Expected update"},
                },
            },
        },
    }
    run = start(
        world, task_ids=[task["id"]], event_ids=[event_id], mutation_requests=[values[kind]]
    )
    waiting = drive(world, run)
    return run, waiting["proposal_ids"][0], task, event_id, event


def collide(runtime, pid, kind, task, event_id, event):
    key = "assistant-confirm/" + pid
    if kind == "task_create":
        return runtime.tasks.create(TaskInput(title="Unrelated task"), key)
    if kind == "task_change":
        return runtime.tasks.action(
            task["id"], TaskAction(action="note", expected_version=1, note="Unrelated note"), key
        )
    if kind == "calendar_create":
        return runtime.store.create(
            CreateEvents(event=event.model_copy(update={"title": "Unrelated event"})), key
        )
    return runtime.store.event_action(
        event_id,
        EventAction(
            action="update",
            scope="series",
            expected_version=1,
            event=event.model_copy(update={"title": "Unrelated update"}),
        ),
        key,
    )


@pytest.mark.parametrize(
    "kind", ["task_create", "task_change", "calendar_create", "calendar_change"]
)
def test_guard_rejects_mismatched_confirmation_key_before_any_mutation(world, kind):
    runtime = world[0]
    _, pid, task, event_id, event = pending(world, kind)
    with pytest.raises(DomainError, match="RUN_EFFECT_RECEIPT_CONFLICT"):
        collide(runtime, pid, kind, task, event_id, event)
    with runtime.store.connection() as conn:
        assert not conn.execute(
            "SELECT 1 FROM operations WHERE id=?", ("assistant-confirm/" + pid,)
        ).fetchone()
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert runtime.tasks.get(conn, task["id"])["version"] == 1
        assert runtime.store.event(conn, event_id)["version"] == 1


@pytest.mark.parametrize(
    "kind", ["task_create", "task_change", "calendar_create", "calendar_change"]
)
def test_legacy_mismatched_receipt_never_satisfies_required_outcome(world, kind):
    runtime = world[0]
    run, pid, task, event_id, event = pending(world, kind)
    guard = runtime.store.operation_guard
    runtime.store.operation_guard = None  # Fixture simulates a receipt from a pre-guard version.
    try:
        collide(runtime, pid, kind, task, event_id, event)
    finally:
        runtime.store.operation_guard = guard
    assert verify_proposal(runtime, pid) == {
        "state": "unknown",
        "code": "RUN_EFFECT_RECEIPT_CONFLICT",
    }
    final = drive(world, run)
    assert final["state"] == "partial" and final["effects"][0]["state"] == "unknown"
