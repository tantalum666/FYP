"""Scripted planner + fake browser protocol; never live-model or actual UI evidence."""

import hashlib
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from desk.agent_run_schemas import AgentDecision, RunCreate, RunToolCall
from desk.agent_runs import AgentRunService
from desk.agent_tools import PublicBriefTool, validate_tool_call
from desk.browser_policy import BrowserApproval, BrowserJobInput, PublicObservationInput, digest
from desk.store import DomainError
from test_agent_runs import world as world, start, model, detail, drive, action
from test_browser_jobs import FakeBrowser


@pytest.fixture
def browser_world(world):
    runtime = world[0]
    fake = FakeBrowser()
    runtime.browser_jobs.enabled = True
    runtime.browser_jobs.supervisor = fake
    runtime.browser_jobs.environment_id = digest(
        ["owned_local_chromium", fake.executable, "stackedit_markdown_v1"]
    )
    return world, fake


def browser_start(world, **changes):
    return start(
        world,
        source_ids=[],
        browser_source_ids=["python_asyncio"],
        browser_public_only=True,
        **model(world),
        **changes,
    )


def planner(world, *, required=True):
    seen = []

    def generate(system, context, schema, purpose):
        seen.append(context)
        if not context["plan"]:
            return AgentDecision(
                action="plan",
                plan=[
                    "Observe selected public excerpt",
                    "Request exact owner review",
                    "Report result",
                ],
            )
        if not context["observations"]:
            return AgentDecision(
                action="tool",
                tool_call=RunToolCall(
                    tool="browser_public_observe", arguments={"source_id": "python_asyncio"}
                ),
            )
        if not context["reviewed_effects"]:
            observed = next(e for e in context["observations"] if e["kind"] == "browser")
            return AgentDecision(
                action="tool",
                tool_call=RunToolCall(
                    tool="browser_public_brief",
                    arguments={"observation_id": observed["observation_id"]},
                    required=required,
                ),
            )
        if not context["artifacts"]:
            return AgentDecision(
                action="report",
                report={
                    "summary": "Observed public excerpt; effect outcome is reported separately.",
                    "sections": [
                        {
                            "title": "Public excerpt",
                            "text": context["observations"][0]["excerpt"],
                            "evidence_ids": ["browser:python_asyncio"],
                        }
                    ],
                    "limitations": [
                        "One public excerpt only. Fake browser protocol in this test; no live acceptance."
                    ],
                },
            )
        return AgentDecision(action="finish")

    world[0].text_ai.generate = generate
    return seen


def approve(world, run):
    r = world[0]
    job = detail(world, run)["browser_jobs"][0]
    r.browser_jobs.approve(
        job["id"],
        BrowserApproval(
            expected_version=job["version"], intent_hash=job["intent_hash"], public_only=True
        ),
        uuid4().hex,
        session_hash=world[2],
    )
    return job


def test_model_chooses_tool_waits_for_exact_review_and_continues_with_byte_proof(browser_world):
    world, fake = browser_world
    seen = planner(world)
    run = browser_start(world)
    waiting = drive(world, run)
    assert waiting["state"] == "waiting_review"
    assert waiting["tool_calls"] == 2
    assert len(fake.calls) == 1 and fake.calls[0]["operation"] == "observe"
    assert len(detail(world, run)["browser_jobs"]) == 1
    calls = len(seen)
    for _ in range(3):
        world[4][0] += timedelta(seconds=2)
        world[0].agent_runs.advance_one()
    assert len(seen) == calls  # no model polling while review pending
    job = approve(world, run)
    world[0].browser_jobs.advance_one()
    world[4][0] += timedelta(seconds=2)
    final = drive(world, run)
    assert final["state"] == "succeeded"
    result = final["effects"][0]
    body, _ = world[0].browser_jobs.export(job["id"], session_hash=world[2])
    assert result["state"] == "verified" and result["sha256"] == hashlib.sha256(body).hexdigest()
    assert result["cleanup_confirmed"] is True
    assert seen[-1]["reviewed_effects"][0]["state"] == "verified"
    assert seen[-1]["tool_results"][-1]["result"]["sha256"] == result["sha256"]
    assert len(fake.calls) == 2
    assert all("approve" not in t["tool"] for t in seen[0]["available_tools"])
    assert len(detail(world, run)["artifacts"]) == 2


def test_public_payload_cannot_include_private_goal_source_or_model_prose(browser_world):
    world, fake = browser_world
    secret = "PRIVATE GOAL AND SOURCE MARKER"
    planner(world)
    run = browser_start(world, goal=secret)
    drive(world, run)
    request = detail(world, run)["browser_jobs"][0]["request"]
    assert secret not in json.dumps(request)
    assert request["title"] == "Python official documentation: asyncio"
    with world[0].store.connection() as conn:
        internal = world[0].agent_runs._get(conn, run["id"])
    observation_id = internal["evidence"][0]["observation_id"]
    for bad in (
        {"observation_id": observation_id, "note": secret},
        {"observation_id": observation_id, "title": secret},
        {"observation_id": observation_id, "public_only": True},
    ):
        with pytest.raises(DomainError, match="RUN_TOOL_ARGUMENTS_INVALID"):
            validate_tool_call(
                world[0], internal, RunToolCall(tool="browser_public_brief", arguments=bad)
            )
    assert len(fake.calls) == 1


def test_unselected_sources_unknown_tools_and_foreign_observations_rejected(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    with world[0].store.connection() as conn:
        internal = world[0].agent_runs._get(conn, run["id"])
    for name, args, error in [
        (
            "browser_public_observe",
            {"source_id": "python_pathlib"},
            "RUN_BROWSER_SOURCE_NOT_SELECTED",
        ),
        (
            "browser_public_observe",
            {"source_id": "https://private.example/secret"},
            "RUN_BROWSER_SOURCE_NOT_SELECTED",
        ),
        (
            "browser_public_brief",
            {"observation_id": "a" * 32},
            "RUN_BROWSER_OBSERVATION_NOT_SELECTED",
        ),
        ("browser_approve", {}, "RUN_TOOL_NOT_ALLOWED"),
    ]:
        with pytest.raises(DomainError, match=error):
            validate_tool_call(world[0], internal, RunToolCall(tool=name, arguments=args))
    assert fake.calls == []


@pytest.mark.parametrize("public_only", [False, 1, "true"])
def test_browser_grant_requires_actual_true(browser_world, public_only):
    world, _ = browser_world
    data = dict(
        goal="Read",
        mode="model",
        provider_destination_id="fixture",
        retain=True,
        scope_revision="a" * 64,
        browser_source_ids=["python_asyncio"],
        browser_public_only=public_only,
    )
    with pytest.raises(ValidationError):
        RunCreate(**data)


def test_browser_disabled_scope_does_not_admit_run(world):
    model(world)
    with pytest.raises(DomainError, match="BROWSER_DISABLED"):
        browser_start(world)


@pytest.mark.parametrize("choice", ["cancel", "pause"])
def test_stop_cancels_exact_browser_review_even_at_capacity(browser_world, choice):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    drive(world, run)
    r = world[0]
    with r.store.connection(write=True) as conn:
        for n in range(2000):
            conn.execute(
                "INSERT INTO browser_operations VALUES(?,?,?,?)",
                (f"capacity-{n}", "fixture", "observe", "fixture"),
            )
    stopped = action(world, run, choice)
    assert stopped["state"] == ("cancelled" if choice == "cancel" else "paused")
    assert detail(world, run)["browser_jobs"][0]["state"] == "cancelled"
    assert stopped["effects"][0]["state"] == "rejected"
    assert len(fake.calls) == 1


def test_cancel_during_public_observation_fences_child_and_late_result(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    world[0].agent_runs.advance_one()
    fake.hook = lambda stage: action(world, run, "cancel") if stage == "before_observe" else None
    world[0].agent_runs.advance_one()
    value = detail(world, run)["run"]
    assert value["state"] == "cancelled" and value["evidence"] == []
    assert value["browser_job_ids"] == []
    with world[0].store.connection() as conn:
        row = conn.execute("SELECT * FROM browser_observations").fetchone()
    assert row["state"] == "failed"
    assert row["error"] == "RUN_CONTROL_CHANGED"


def test_cancel_after_observed_read_discards_late_evidence_with_cleanup_preserved(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    world[0].agent_runs.advance_one()
    fake.hook = lambda stage: action(world, run, "pause") if stage == "after_observe" else None
    world[0].agent_runs.advance_one()
    assert detail(world, run)["run"]["state"] == "paused"
    assert detail(world, run)["run"]["evidence"] == []
    with world[0].store.connection() as conn:
        row = conn.execute("SELECT * FROM browser_observations").fetchone()
    assert row["cleanup"] == 1 and row["state"] == "failed"


@pytest.mark.parametrize("stop", [False, True])
def test_prepare_lost_parent_link_recovers_same_child_or_cancels_it(
    browser_world, monkeypatch, stop
):
    world, fake = browser_world
    r = world[0]
    planner(world)
    run = browser_start(world)
    original = r.agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "tool_prepared":
            raise KeyboardInterrupt()
        return original(value, kind, result)

    monkeypatch.setattr(r.agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    jobs = r.browser_jobs.listing(review=True)["jobs"]
    assert len(jobs) == 1
    assert detail(world, run)["run"]["browser_job_ids"] == []
    r.agent_runs = AgentRunService(r)
    if stop:
        action(world, run, "cancel")
        assert r.browser_jobs.detail(jobs[0]["id"])["state"] == "cancelled"
    else:
        world[4][0] += timedelta(seconds=61)
        r.agent_runs.advance_one()
        assert detail(world, run)["run"]["browser_job_ids"] == [jobs[0]["id"]]
        assert detail(world, run)["run"]["state"] == "waiting_review"
    assert len(r.browser_jobs.listing()["jobs"]) == 1 and len(fake.calls) == 1


def test_child_receipt_collision_cannot_adopt_or_cancel_unrelated_job(browser_world, monkeypatch):
    world, fake = browser_world
    r = world[0]
    planner(world)
    run = browser_start(world)
    original = PublicBriefTool.dispatch
    unrelated = []

    def collision(adapter, runtime, value, arguments, key, checkpoint):
        observation = next(e for e in value["evidence"] if e["kind"] == "browser")
        unrelated.append(
            r.browser_jobs.prepare(
                BrowserJobInput(
                    observation_id=observation["observation_id"],
                    title="Unrelated draft",
                    note="unrelated",
                    public_only=True,
                ),
                key,
                session_hash=world[2],
            )["job"]
        )
        return original(adapter, runtime, value, arguments, key, checkpoint)

    monkeypatch.setattr(PublicBriefTool, "dispatch", collision)
    final = drive(world, run)
    assert (
        final["state"] == "blocked"
        and final["state_reason"] == "BROWSER_OPERATION_RECEIPT_CONFLICT"
    )
    assert final["browser_job_ids"] == []
    assert r.browser_jobs.detail(unrelated[0]["id"])["state"] == "review"
    assert len(fake.calls) == 1


def test_owner_session_expiry_while_waiting_review_cancels_child(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    drive(world, run)
    r = world[0]
    r.store.logout(world[1]["session"])
    world[4][0] += timedelta(seconds=2)
    r.agent_runs.advance_one()
    with r.store.connection() as conn:
        saved = r.agent_runs._get(conn, run["id"])
    assert saved["state"] == "blocked" and saved["state_reason"] == "RUN_SESSION_EXPIRED"
    assert r.browser_jobs.detail(saved["browser_job_ids"][0])["state"] == "cancelled"
    assert len(fake.calls) == 1


def test_verified_bytes_with_unknown_cleanup_remain_unknown_and_partial(browser_world):
    world, fake = browser_world
    seen = planner(world)
    run = browser_start(world)
    drive(world, run)
    job = approve(world, run)
    fake.cleanup = False
    world[0].browser_jobs.advance_one()
    world[4][0] += timedelta(seconds=2)
    final = drive(world, run)
    assert final["state"] == "partial"
    assert final["effects"][0]["state"] == "unknown"
    assert final["effects"][0]["cleanup_confirmed"] is False
    assert seen[-1]["reviewed_effects"][0]["state"] == "unknown"
    assert world[0].browser_jobs.detail(job["id"])["state"] == "unknown"
    assert len(fake.calls) == 2


def test_export_changed_after_browser_success_cannot_satisfy_goal(browser_world):
    world, _ = browser_world
    planner(world)
    run = browser_start(world)
    drive(world, run)
    job = approve(world, run)
    world[0].browser_jobs.advance_one()
    path = world[0].browser_jobs.root / job["id"] / "export.md"
    path.write_bytes(b"Corrupted export")
    final = drive(world, run)
    assert final["state"] == "partial" and final["effects"][0]["state"] == "unknown"


def test_configurable_budget_consumes_reserved_calls_without_reset(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world, model_call_budget=2, tool_call_budget=1)
    result = drive(world, run)
    assert result["state_reason"] == "RUN_MODEL_BUDGET_EXCEEDED"
    assert result["model_calls"] == 2 and len(fake.calls) == 1
    action(world, run, "resume")
    assert drive(world, run)["model_calls"] == 2
    for field, value in [("model_call_budget", 25), ("tool_call_budget", 17)]:
        with pytest.raises(ValidationError):
            browser_start(world, **{field: value})


def test_tool_budget_stops_before_second_dispatch(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world, tool_call_budget=1)
    final = drive(world, run)
    assert final["state_reason"] == "RUN_TOOL_BUDGET_EXCEEDED"
    assert final["browser_job_ids"] == [] and len(fake.calls) == 1


def test_read_only_recovery_validates_actual_child_not_only_operation_fingerprint(browser_world):
    world, _ = browser_world
    r = world[0]
    a = r.browser_jobs.observe(
        PublicObservationInput(source_id="python_asyncio", public_only=True),
        "observation-a",
        session_hash=world[2],
    )["observation"]
    b = r.browser_jobs.observe(
        PublicObservationInput(source_id="python_pathlib", public_only=True),
        "observation-b",
        session_hash=world[2],
    )["observation"]
    with r.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE browser_operations SET reference=? WHERE operation_key='observation-a'",
            (b["id"],),
        )
    with pytest.raises(DomainError, match="BROWSER_OPERATION_RECEIPT_CONFLICT"):
        r.browser_jobs.lookup_operation(
            PublicObservationInput(source_id="python_asyncio", public_only=True),
            "observation-a",
            kind="observe",
        )
    assert a["id"] != b["id"]


def test_shutdown_cancels_queued_child_before_restart_can_execute_it(browser_world):
    world, fake = browser_world
    planner(world)
    run = browser_start(world)
    drive(world, run)
    job = approve(world, run)
    world[0].agent_runs.shutdown()
    world[0].agent_runs = AgentRunService(world[0])
    world[0].browser_jobs.advance_one()
    assert world[0].browser_jobs.detail(job["id"])["state"] == "cancelled"
    assert detail(world, run)["run"]["state"] == "paused"
    assert len(fake.calls) == 1


def test_missing_export_becomes_unknown_without_crashing_run_worker(browser_world):
    world, _ = browser_world
    planner(world)
    run = browser_start(world)
    drive(world, run)
    job = approve(world, run)
    world[0].browser_jobs.advance_one()
    (world[0].browser_jobs.root / job["id"] / "export.md").unlink()
    final = drive(world, run)
    assert final["state"] == "partial"
    assert final["effects"][0]["state"] == "unknown"
    assert final["effects"][0]["code"] == "BROWSER_VERIFICATION_UNAVAILABLE"


def test_cancel_during_observation_validation_cannot_commit_late_child_body(
    browser_world, monkeypatch
):
    world, _ = browser_world
    planner(world)
    run = browser_start(world)
    runtime = world[0]
    runtime.agent_runs.advance_one()
    original = runtime.browser_jobs._validate_observation
    changed = []

    def validate(observation):
        original(observation)
        if not changed:
            changed.append(True)
            action(world, run, "cancel")

    monkeypatch.setattr(runtime.browser_jobs, "_validate_observation", validate)
    runtime.agent_runs.advance_one()
    assert detail(world, run)["run"]["state"] == "cancelled"
    with runtime.store.connection() as conn:
        child = conn.execute("SELECT * FROM browser_observations").fetchone()
    assert child["state"] == "failed" and child["data"] is None and child["cleanup"] == 1


def test_completed_public_read_lost_link_recovers_without_second_browser_read(
    browser_world, monkeypatch
):
    world, fake = browser_world
    runtime = world[0]
    planner(world)
    run = browser_start(world)
    original = runtime.agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "tool_observed":
            raise KeyboardInterrupt()
        return original(value, kind, result)

    monkeypatch.setattr(runtime.agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    assert len(fake.calls) == 1 and detail(world, run)["run"]["evidence"] == []
    runtime.agent_runs = AgentRunService(runtime)
    world[4][0] += timedelta(seconds=61)
    runtime.agent_runs.advance_one()
    assert detail(world, run)["run"]["evidence"][0]["kind"] == "browser"
    assert len(fake.calls) == 1
