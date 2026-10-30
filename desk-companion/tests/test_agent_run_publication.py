"""Atomic local publication and reviewed-effect fences; no live model or network."""

from pathlib import Path
from uuid import uuid4

import pytest

from desk.agent_run_schemas import AgentDecision
from desk.personal_memory import MemoryAction
from desk.store import DomainError
from test_agent_context import context_world as context_world, memory, selection
from test_agent_personal_context_integration import start, script, detail, drive, action


def forget(world, remembered):
    world["runtime"].memories.action(
        remembered["id"], MemoryAction(action="forget", expected_version=1), uuid4().hex
    )


@pytest.mark.parametrize("change", ["forget", "cancel"])
def test_context_change_at_temp_synced_cannot_publish_final_artifact(
    context_world, monkeypatch, change
):
    world = context_world
    remembered = memory(world, "PRIVATE_DERIVED_ARTIFACT_MARKER")
    script(world, echo_context=True)
    run = start(world, selection(remembered))
    runtime = world["runtime"]
    interrupted = []

    def phase(stage, row):
        if stage == "temp_synced" and not interrupted:
            interrupted.append(row)
            if change == "forget":
                forget(world, remembered)
            else:
                action(world, run, "cancel")

    monkeypatch.setattr(runtime.artifacts.files, "phase", phase)
    for _ in range(10):
        runtime.agent_runs.advance_one()
        result = detail(world, run)["run"]
        if result["state"] in {"blocked", "cancelled"}:
            break
    assert result["state"] == ("blocked" if change == "forget" else "cancelled")
    assert result["artifact_ids"] == []
    assert len(interrupted) == 1
    directory = Path(runtime.store.directory) / "artifacts"
    final = directory / runtime.artifacts.files.filename(interrupted[0])
    assert not final.exists()
    assert not (directory / ("." + interrupted[0]["id"] + ".pending")).exists()
    artifacts = runtime.artifacts.listing(
        session_hash=world["identity"]["session_hash"], run_id=run["id"]
    )["artifacts"]
    assert len(artifacts) == 1 and artifacts[0]["status"] != "verified"


def pending_personal_draft(world):
    remembered = memory(world, "SELECTED_PRIVATE_DRAFT_MARKER")
    run = start(world, selection(remembered), allow_mutation_proposals=True)
    decisions = [
        AgentDecision(action="plan", plan=["Prepare a reviewed local task"]),
        AgentDecision(
            action="propose",
            mutation={
                "tool": "task_create_draft",
                "arguments": {"title": "SELECTED_PRIVATE_DRAFT_MARKER"},
            },
        ),
    ]
    world["runtime"].text_ai.generate = lambda *args: decisions.pop(0)
    waiting = drive(world, run)
    return remembered, run, waiting["proposal_ids"][0]


def test_run_origin_review_rejects_forgotten_context_before_worker_poll(context_world):
    world = context_world
    remembered, run, pid = pending_personal_draft(world)
    forget(world, remembered)
    with pytest.raises(DomainError, match="RUN_(PERSONAL_)?CONTEXT_CHANGED"):
        world["runtime"].agent_runs.require_proposal_access(pid, world["owner"])
    assert detail(world, run)["run"]["state"] == "waiting_review"
    assert world["runtime"].tasks.listing()["tasks"] == []


def test_atomic_application_guard_closes_gap_after_route_review(context_world, monkeypatch):
    world = context_world
    runtime = world["runtime"]
    remembered, _, pid = pending_personal_draft(world)
    runtime.agent_runs.require_proposal_access(pid, world["owner"])
    original = runtime.tasks.create

    def change_before_commit(*args, **kwargs):
        forget(world, remembered)
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.tasks, "create", change_before_commit)
    with pytest.raises(DomainError, match="RUN_(PERSONAL_)?CONTEXT_CHANGED"):
        runtime.assistant.decide(pid, "confirm", uuid4().hex)
    assert runtime.tasks.listing()["tasks"] == []
    with runtime.store.connection() as conn:
        assert not conn.execute(
            "SELECT 1 FROM operations WHERE id=?", ("assistant-confirm/" + pid,)
        ).fetchone()


def test_atomic_guard_still_allows_cancelling_stale_derived_draft(context_world):
    world = context_world
    runtime = world["runtime"]
    remembered, _, pid = pending_personal_draft(world)
    forget(world, remembered)
    runtime.agent_runs.require_proposal_access(pid, world["owner"], action="cancel")
    assert runtime.assistant.decide(pid, "cancel", uuid4().hex)["state"] == "cancelled"
    assert runtime.tasks.listing()["tasks"] == []


@pytest.mark.parametrize("change", ["forget", "cancel"])
def test_final_model_admission_rechecks_after_context_projection(
    context_world, monkeypatch, change
):
    world = context_world
    runtime = world["runtime"]
    remembered = memory(world, "PRIVATE_PRE_DISPATCH_MARKER")
    run = start(world, selection(remembered))
    original = runtime.agent_runs.context_bridge.project
    calls = []

    def projection(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == "forget":
            forget(world, remembered)
        else:
            action(world, run, "cancel")
        return value

    monkeypatch.setattr(runtime.agent_runs.context_bridge, "project", projection)
    runtime.text_ai.generate = lambda *args: calls.append(args)
    runtime.agent_runs.advance_one()
    assert calls == []
    result = detail(world, run)["run"]
    assert result["state"] == ("blocked" if change == "forget" else "cancelled")
    assert result["state_reason"] != "RUN_PROVIDER_OUTCOME_UNKNOWN"
    with runtime.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT state FROM agent_attempts WHERE run_id=?", (run["id"],)
            ).fetchone()[0]
            == "dispatch_refused"
        )


def test_real_transport_guard_runs_after_http_request_serialization(context_world, monkeypatch):
    import httpx

    world = context_world
    runtime = world["runtime"]
    remembered = memory(world, "PRIVATE_SERIALIZED_MARKER")
    run = start(world, selection(remembered))
    transmitted = []
    runtime.text_ai.transport = httpx.MockTransport(lambda request: transmitted.append(request))
    original = httpx.Client.build_request
    changed = []

    def build(client, *args, **kwargs):
        request = original(client, *args, **kwargs)
        if not changed:
            changed.append(True)
            assert b"PRIVATE_SERIALIZED_MARKER" in request.content
            forget(world, remembered)
        return request

    monkeypatch.setattr(httpx.Client, "build_request", build)
    runtime.agent_runs.advance_one()
    assert changed and transmitted == []
    result = detail(world, run)["run"]
    assert result["state"] == "blocked" and result["state_reason"] != "RUN_PROVIDER_OUTCOME_UNKNOWN"
    with runtime.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT state FROM agent_attempts WHERE run_id=?", (run["id"],)
            ).fetchone()[0]
            == "dispatch_refused"
        )
        # A local usage reservation can exist; it never contains private request bodies.
        assert "PRIVATE_SERIALIZED_MARKER" not in str(
            list(conn.execute("SELECT * FROM text_ai_usage"))
        )


def test_projection_denial_is_known_before_dispatch_and_not_unknown_on_restart(
    context_world, monkeypatch
):
    from desk.agent_runs import AgentRunService

    world = context_world
    runtime = world["runtime"]
    remembered = memory(world, "PRIVATE_PROJECTION_MARKER")
    run = start(world, selection(remembered))
    original = runtime.agent_runs.context_bridge.project
    calls = []

    def denied_projection(*args, **kwargs):
        forget(world, remembered)
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.agent_runs.context_bridge, "project", denied_projection)
    runtime.text_ai.generate = lambda *args: calls.append(args)
    runtime.agent_runs.advance_one()
    assert calls == []
    with runtime.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT state FROM agent_attempts WHERE run_id=?", (run["id"],)
            ).fetchone()[0]
            == "dispatch_refused"
        )
    runtime.agent_runs = AgentRunService(runtime)
    result = detail(world, run)["run"]
    assert result["state"] == "blocked" and result["state_reason"] == "RUN_PERSONAL_CONTEXT_CHANGED"
