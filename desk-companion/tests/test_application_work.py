"""Scripted Work decisions + real services/files; the bridge here is a test double."""

import json
from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from desk.agent_run_schemas import AgentDecision, RunCreate, RunToolCall
from desk.agent_runs import AgentRunService
from desk.agent_tools import validate_tool_call
from desk.application_executor import ApplicationExecutor
from desk.application_work import JOB_TOOL
from desk.jobs import JobApproval
from desk.permissions import PermissionChange
from desk.store import DomainError
from desk.tasks import TaskInput
from test_agent_runs import world as world, start, model, detail, drive, action
from test_application_jobs import FakeBridge, payload


@pytest.fixture
def app_world(world, tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "quote.txt").write_text("Fictional quote\nPrice: 12\n")
    (inputs / "unselected.txt").write_text("Not part of this work")
    monkeypatch.setenv("DESK_APPLICATION_ENABLED", "1")
    monkeypatch.setenv("DESK_APPLICATION_INPUTS", str(inputs))
    r = world[0]
    r.jobs.applications = ApplicationExecutor(r.store.directory)
    r.jobs.applications.bridge = FakeBridge(r.jobs.applications.root)
    r.jobs.applications.sources.bridge = r.jobs.applications.bridge
    task = r.tasks.create(TaskInput(title="Compare quotes", follow_up_enabled=False), "app-task")[
        "task"
    ]
    return world, task


def create(app_world, **changes):
    world, task = app_world
    values = dict(
        source_ids=[],
        task_ids=[task["id"]],
        allow_application_jobs=True,
        application_source_ids=["quote.txt"],
        **model(world),
    )
    values.update(changes)
    return start(world, **values)


def planner(app_world, *, revise=True):
    world, task = app_world
    seen = []

    def generate(system, ctx, schema, purpose):
        seen.append(ctx)
        if not ctx["plan"]:
            return AgentDecision(
                action="plan", plan=["Read quote", "Write and revise workbook", "Verify results"]
            )
        if not any(e["kind"] == "task" for e in ctx["observations"]):
            return AgentDecision(action="read", evidence_id="task:" + task["id"])
        if not any(e["kind"] == "application" for e in ctx["observations"]):
            return AgentDecision(
                action="tool",
                tool_call=RunToolCall(
                    tool="application_source_read", arguments={"source_id": "quote.txt"}
                ),
            )
        effects = ctx["reviewed_effects"]
        if len(effects) < (2 if revise else 1):
            prior = effects[0]["reference_id"] if effects else None
            request = payload(
                task, source=prior, value="Revised" if prior else "Initial"
            ).model_dump(mode="json")
            request["sources"] = [
                {k: ctx["application_sources"][0][k] for k in ("source_id", "sha256")}
            ]
            return AgentDecision(
                action="tool", tool_call=RunToolCall(tool=JOB_TOOL, arguments=request)
            )
        if not ctx["artifacts"]:
            return AgentDecision(
                action="report",
                report={
                    "summary": "Scripted integration result.",
                    "sections": [
                        {
                            "title": "Evidence",
                            "text": "Observed quote and file results; semantic quality unassessed.",
                            "evidence_ids": [e["id"] for e in ctx["observations"]],
                        }
                    ],
                },
            )
        return AgentDecision(action="finish")

    world[0].text_ai.generate = generate
    return seen


def approve(r, job):
    current = r.jobs.detail(job["id"], review=True)
    return r.jobs.approve(
        job["id"],
        JobApproval(expected_version=current["version"], intent_hash=current["intent_hash"]),
        uuid4().hex,
    )


def complete(app_world, run, *, review=True):
    world, _ = app_world
    r = world[0]
    for _ in range(50):
        r.agent_runs.advance_one()
        d = detail(world, run)
        for job in d["application_jobs"]:
            if review and job["state"] == "review":
                approve(r, job)
        r.jobs.run_one()
        world[4][0] += timedelta(seconds=2)
        if d["run"]["state"] in {"succeeded", "partial", "blocked", "cancelled"}:
            return d
    raise AssertionError(d)


def test_app_work_reads_only_selected_source_reviews_continues_and_keeps_versions(app_world):
    seen = planner(app_world)
    run = create(app_world)
    pending = drive(app_world[0], run)
    assert pending["state"] == "waiting_review"
    r = app_world[0][0]
    assert r.jobs.applications.bridge.edits == 0
    result = complete(app_world, run)
    assert result["run"]["state"] == "succeeded", result["run"]["state_reason"]
    assert len(result["application_jobs"]) == 2
    assert r.jobs.applications.bridge.edits == 2
    assert result["run"]["effects"][0]["version_scope"] == "superseded_history"
    assert result["run"]["effects"][1]["version_scope"] == "current"
    assert all(e["state"] == "verified" for e in result["run"]["effects"])
    bodies = [r.jobs.application_download(j["id"])[1] for j in result["application_jobs"]]
    assert bodies[0] != bodies[1] and b"Initial" in bodies[0] and b"Revised" in bodies[1]
    assert any(
        c["reviewed_effects"] and c["reviewed_effects"][0]["state"] == "verified" for c in seen
    )
    assert "Not part of this work" not in json.dumps(seen)


def test_full_access_is_captured_for_new_work_only(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    r.permissions.change(PermissionChange(mode="full", expected_version=1), "full")
    run = create(app_world)
    done = complete(app_world, run, review=False)
    assert done["run"]["state"] == "succeeded"
    assert done["application_jobs"][0]["authorization"]["mode"] == "full"


def test_turning_on_full_later_does_not_authorize_existing_work(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    run = create(app_world)
    r.permissions.change(PermissionChange(mode="full", expected_version=1), "later-full")
    drive(world, run)
    assert detail(world, run)["application_jobs"][0]["state"] == "review"


def test_revocation_fences_queued_work_before_execution(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    r.permissions.change(PermissionChange(mode="full", expected_version=1), "full")
    run = create(app_world)
    drive(world, run, stop=("waiting_effect", "blocked"))
    r.permissions.change(PermissionChange(mode="ask", expected_version=2), "revoke")
    r.jobs.run_one()
    job = detail(world, run)["application_jobs"][0]
    assert job["state"] == "failed" and job["error"] == "PERMISSION_CHANGED"
    assert r.jobs.applications.bridge.edits == 0


@pytest.mark.parametrize("control", ["pause", "cancel"])
def test_parent_control_cancels_child_and_rejects_old_approval(app_world, control):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    run = create(app_world)
    drive(world, run)
    job = detail(world, run)["application_jobs"][0]
    action(world, run, control)
    with pytest.raises(DomainError):
        approve(r, job)
    r.jobs.run_one()
    assert r.jobs.applications.bridge.edits == 0
    assert r.jobs.detail(job["id"])["state"] == "cancelled"


def test_expired_parent_session_stops_already_queued_child(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    run = create(app_world)
    drive(world, run)
    job = detail(world, run)["application_jobs"][0]
    approve(r, job)
    with r.store.connection(write=True) as conn:
        conn.execute("DELETE FROM sessions")
    r.jobs.run_one()
    assert r.jobs.detail(job["id"])["error"] == "RUN_SESSION_EXPIRED"
    assert r.jobs.applications.bridge.edits == 0


def test_changed_selected_source_stops_planner_before_dispatch(app_world):
    world, _ = app_world
    seen = planner(app_world)
    run = create(app_world)
    (world[0].jobs.applications.sources.root / "quote.txt").write_text("New quote")
    result = drive(world, run)
    assert result["state_reason"] == "RUN_APPLICATION_SOURCE_CHANGED"
    assert seen == []


def test_unselected_source_and_foreign_job_are_denied(app_world):
    world, task = app_world
    planner(app_world, revise=False)
    run = create(app_world)
    drive(world, run)
    with world[0].store.connection() as conn:
        saved = world[0].agent_runs._get(conn, run["id"])
    with pytest.raises(DomainError, match="RUN_APPLICATION_SOURCE_NOT_SELECTED"):
        validate_tool_call(
            world[0],
            saved,
            RunToolCall(tool="application_source_read", arguments={"source_id": "unselected.txt"}),
        )
    request = payload(task, source="a" * 32).model_dump(mode="json")
    with pytest.raises(DomainError, match="RUN_APPLICATION_JOB_NOT_SELECTED"):
        validate_tool_call(world[0], saved, RunToolCall(tool=JOB_TOOL, arguments=request))


def test_lost_draft_receipt_recovers_same_job_after_restart(app_world, monkeypatch):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    run = create(app_world)
    original = r.jobs.prepare

    def lose(payload, key):
        original(payload, key)
        raise SystemExit("simulated abrupt process loss")

    monkeypatch.setattr(r.jobs, "prepare", lose)
    with pytest.raises(SystemExit):
        drive(world, run)
    jobs = r.jobs.listing()
    assert len(jobs) == 1
    monkeypatch.setattr(r.jobs, "prepare", original)
    r.agent_runs = AgentRunService(r)
    r.store.operation_guard = r.agent_runs.guard_operation
    world[4][0] += timedelta(seconds=61)
    done = complete(app_world, run)
    assert done["run"]["state"] == "succeeded"
    assert [j["id"] for j in done["application_jobs"]] == [jobs[0]["id"]]
    assert r.jobs.applications.bridge.edits == 1


def test_tampered_historical_version_prevents_success(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world)
    run = create(app_world)
    done = complete(app_world, run)
    job = done["application_jobs"][0]
    path = r.jobs.applications.version_target(job["request"])
    path.write_bytes(b"tampered")
    from desk.application_work import ApplicationJobTool

    with pytest.raises((DomainError, ValueError)):
        ApplicationJobTool().verify(r, done["run"], done["run"]["effects"][0])


def test_application_opt_in_and_sharing_are_strict(app_world):
    world, task = app_world
    params = dict(
        goal="Work",
        retain=True,
        task_ids=[task["id"]],
        scope_revision="a" * 64,
        mode="model",
        provider_destination_id="fixture",
        application_source_ids=["quote.txt"],
    )
    with pytest.raises(ValidationError):
        RunCreate(**params)
    with pytest.raises(ValidationError):
        RunCreate(**params, allow_application_jobs=True)
    with pytest.raises(ValidationError):
        RunCreate(**params, allow_application_jobs="yes", share_sources_with_provider=True)


def test_selected_inputs_remain_bound_when_planner_omits_sources(app_world):
    world, task = app_world
    r = world[0]
    planner(app_world, revise=False)
    run = create(app_world)
    drive(world, run)
    with r.store.connection() as conn:
        saved = r.agent_runs._get(conn, run["id"])
    _, normalized = validate_tool_call(
        r, saved, RunToolCall(tool=JOB_TOOL, arguments=payload(task).model_dump(mode="json"))
    )
    assert normalized["sources"][0]["source_id"] == "quote.txt"
    job = detail(world, run)["application_jobs"][0]
    approve(r, job)
    (r.jobs.applications.sources.root / "quote.txt").write_text("Changed after approval")
    r.jobs.run_one()
    assert r.jobs.detail(job["id"])["error"] == "APPLICATION_SOURCE_CHANGED"
    assert r.jobs.applications.bridge.edits == 0


def test_auto_queued_work_is_waiting_for_application_not_owner_approval(app_world):
    world, _ = app_world
    r = world[0]
    planner(app_world, revise=False)
    r.permissions.change(PermissionChange(mode="full", expected_version=1), "full")
    run = create(app_world)
    current = drive(world, run, stop=("waiting_effect", "blocked"))
    assert current["state"] == "waiting_effect"
    assert current["state_reason"] == "RUN_APPLICATION_RUNNING"
    r.agent_runs.shutdown()
    assert r.jobs.detail(detail(world, run)["application_jobs"][0]["id"])["state"] == "cancelled"


def test_cancel_does_not_reopen_completed_applications_under_parent_lock(app_world, monkeypatch):
    world, _ = app_world
    r = world[0]
    planner(app_world)
    run = create(app_world)
    drive(world, run)
    approve(r, detail(world, run)["application_jobs"][0])
    r.jobs.run_one()
    world[4][0] += timedelta(seconds=2)
    r.agent_runs.advance_one()
    drive(world, run)

    def no_reopen(*args, **kwargs):
        raise AssertionError("Cancellation must not wait on an office readback")

    monkeypatch.setattr(r.jobs, "application_readback", no_reopen)
    stopped = action(world, run, "cancel")
    assert stopped["state"] == "cancelled"
    assert [j["state"] for j in detail(world, run)["application_jobs"]] == [
        "succeeded",
        "cancelled",
    ]
