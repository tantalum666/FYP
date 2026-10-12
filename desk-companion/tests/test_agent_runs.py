"""Real SQLite/filesystem orchestration; scripted decisions are not live-model evidence."""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from desk.agent_run_schemas import RunCreate, RunAction, AgentDecision
from desk.agent_runs import AgentRunService
from desk.context import ContextSettings
from desk.runtime import Runtime
from desk.sources import SourceInput
from desk.store import Store, DomainError
from desk.tasks import TaskInput
from desk.text_ai import TextConfig


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 10, 12, 14, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    token = runtime.store.authenticate("owner", "fixture-only")
    owner = {"kind": "owner", "session": token}
    session = hashlib.sha256(token.encode()).hexdigest()
    source = runtime.sources.ingest(
        SourceInput(name="requirements.csv", format="csv"),
        b"item,hours\nread,2\nwrite,3\n",
        "source",
        session_hash=session,
    )["source"]
    return runtime, owner, session, source, clock


def start(world, **changes):
    r, owner, _, source, _ = world
    data = dict(
        goal="Compile the selected requirements and identify effort.",
        retain=True,
        source_ids=[source["id"]],
        scope_revision=r.agent_runs.scope(owner)["scope_revision"],
    )
    data.update(changes)
    return r.agent_runs.create(RunCreate(**data), uuid4().hex, owner)["run"]


def detail(world, run):
    return world[0].agent_runs.detail(run["id"], world[1])


def drive(
    world,
    run,
    stop=("succeeded", "partial", "blocked", "waiting_input", "waiting_review"),
    limit=40,
):
    r, _, _, _, clock = world
    for _ in range(limit):
        r.agent_runs.advance_one()
        clock[0] += timedelta(seconds=2)
        current = detail(world, run)["run"]
        if current["state"] in stop:
            return current
    raise AssertionError(current)


def action(world, run, name, **fields):
    current = detail(world, run)["run"]
    return world[0].agent_runs.action(
        run["id"],
        RunAction(action=name, expected_version=current["version"], **fields),
        uuid4().hex,
        world[1],
    )["run"]


def model(world):
    r = world[0]
    r.text_ai.config = TextConfig(provider="gemini", model="fixture-model", api_key="fixture")
    settings = r.personal_context.settings()
    dest = next(d["id"] for d in settings["destinations"] if d["kind"] == "text")
    r.personal_context.update(
        ContextSettings(
            expected_version=settings["version"],
            save_text_history=False,
            use_text_history_in_ai=False,
            use_memory_in_ai=False,
            share_business_context=True,
            approved_destinations=[dest],
        ),
        uuid4().hex,
    )
    return {"mode": "model", "provider_destination_id": dest, "share_sources_with_provider": True}


def script(r, decisions):
    seen = []

    def generate(system, context, schema, purpose):
        seen.append(context)
        return AgentDecision.model_validate(decisions.pop(0))

    r.text_ai.generate = generate
    return seen


def test_real_files_deterministic_restart_and_steer(world):
    run = start(world)
    world[0].agent_runs.advance_one()
    world[0].agent_runs = AgentRunService(world[0])
    result = drive(world, run)
    assert result["state"] == "succeeded" and result["model_calls"] == 0
    d = detail(world, run)
    assert len(d["artifacts"]) == 2
    assert {a["format"] for a in d["artifacts"]} == {"markdown", "csv"}
    assert all(a["verification"] == "byte_readback" for a in d["artifacts"])
    assert d["run"]["evidence"][0]["statistics"]["numeric_column_sums"] == {"hours": "5"}
    old = d["run"]["artifact_ids"]
    action(world, run, "steer", goal="Compile again with a revised constraint")
    revised = drive(world, run)
    assert revised["state"] == "succeeded" and len(revised["artifact_ids"]) == 4
    assert revised["artifact_ids"][:2] == old
    assert revised["reads"] == 1  # selected immutable snapshot reused


def test_creation_idempotency_scope_and_authority(world):
    r, owner, _, source, _ = world
    payload = RunCreate(
        goal="Use selected file",
        retain=True,
        source_ids=[source["id"]],
        scope_revision=r.agent_runs.scope(owner)["scope_revision"],
    )
    one = r.agent_runs.create(payload, "same", owner)
    assert r.agent_runs.create(payload, "same", owner) == one
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.agent_runs.create(payload, "fake", {"kind": "owner"})
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        r.agent_runs.create(payload.model_copy(update={"goal": "different"}), "same", owner)
    r.tasks.create(TaskInput(title="new task"), "task")
    with pytest.raises(DomainError, match="RUN_SCOPE_CHANGED"):
        r.agent_runs.create(payload, "stale", owner)


def test_reviewed_task_effect_continues_and_rereads(world):
    run = start(
        world,
        mutation_requests=[
            {
                "tool": "task_create_draft",
                "arguments": {"title": "Read requirements"},
                "required": True,
            }
        ],
    )
    waiting = drive(world, run)
    assert waiting["state"] == "waiting_review"
    r = world[0]
    assert r.tasks.listing()["tasks"] == []
    pid = waiting["proposal_ids"][0]
    r.assistant.decide(pid, "confirm", "approval")
    r.agent_runs = AgentRunService(r)
    result = drive(world, run)
    assert result["state"] == "succeeded" and result["effects"][0]["state"] == "verified"
    assert len(r.tasks.listing()["tasks"]) == 1
    assert r.agent_runs.advance_one() is False


def test_rejection_partial_and_cancellation_no_rollback(world):
    run = start(
        world,
        mutation_requests=[{"tool": "task_create_draft", "arguments": {"title": "Draft only"}}],
    )
    waiting = drive(world, run)
    world[0].assistant.decide(waiting["proposal_ids"][0], "cancel", "reject")
    result = drive(world, run)
    assert result["state"] == "partial" and world[0].tasks.listing()["tasks"] == []


def test_expired_session_blocks_without_fake_owner(world):
    run = start(world)
    world[0].store.logout(world[1]["session"])
    assert world[0].agent_runs.advance_one()
    with world[0].store.connection() as conn:
        row = world[0].agent_runs._get(conn, run["id"])
    assert row["state"] == "blocked" and row["state_reason"] == "RUN_SESSION_EXPIRED"


def test_scripted_adaptive_plan_read_ask_report_finish(world):
    r, _, _, source, _ = world
    config = model(world)
    eid = "source:" + source["id"]
    seen = script(
        r,
        [
            {"action": "plan", "plan": ["Read requirements", "Ask priority", "Produce report"]},
            {"action": "read", "evidence_id": eid},
            {"action": "ask", "question": "Which priority matters?"},
            {
                "action": "report",
                "report": {
                    "summary": "Source-based brief",
                    "sections": [
                        {"title": "Plan", "text": "Read then write", "evidence_ids": [eid]}
                    ],
                },
            },
            {"action": "finish"},
        ],
    )
    run = start(world, **config)
    assert drive(world, run)["state"] == "waiting_input"
    action(world, run, "answer", answer="Accuracy first")
    result = drive(world, run)
    assert result["state"] == "succeeded" and result["model_calls"] == 5
    assert seen[-1]["answers"] == ["Accuracy first"]
    assert seen[-1]["observations"][0]["id"] == eid
    assert len(seen[-1]["artifacts"]) == 2


def test_model_call_unknown_not_replayed_without_explicit_retry(world):
    r = world[0]
    config = model(world)
    calls = []

    def fail(*args):
        calls.append(1)
        raise TimeoutError()

    r.text_ai.generate = fail
    run = start(world, **config)
    result = drive(world, run)
    assert result["state_reason"] == "RUN_PROVIDER_OUTCOME_UNKNOWN" and len(calls) == 1
    assert r.agent_runs.advance_one() is False
    with pytest.raises(DomainError, match="RUN_EXPLICIT_MODEL_RETRY_REQUIRED"):
        action(world, run, "resume")
    action(world, run, "retry_model")
    drive(world, run)
    assert len(calls) == 2


def test_reject_model_unselected_read_and_fabricated_citation(world):
    r = world[0]
    config = model(world)
    script(
        r,
        [
            {"action": "plan", "plan": ["Read"]},
            {"action": "read", "evidence_id": "source:not-selected"},
        ],
    )
    run = start(world, **config)
    assert drive(world, run)["state_reason"] == "RUN_SOURCE_NOT_SELECTED"


def test_shutdown_fences_late_provider_result(world):
    r = world[0]
    config = model(world)

    def late(*args):
        r.agent_runs.shutdown()
        return AgentDecision(action="plan", plan=["Late plan"])

    r.text_ai.generate = late
    run = start(world, **config)
    r.agent_runs.advance_one()
    assert detail(world, run)["run"]["state_reason"] == "RUN_PROVIDER_OUTCOME_UNKNOWN"
    assert detail(world, run)["run"]["plan"] == []
    assert r.agent_runs.advance_one() is False


def test_cancel_recovers_orphan_draft_after_crash(world, monkeypatch):
    r = world[0]
    run = start(
        world,
        mutation_requests=[
            {"tool": "task_create_draft", "arguments": {"title": "Never silently save"}}
        ],
    )
    checkpoint = r.agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "proposal":
            raise KeyboardInterrupt("simulated process loss after child draft")
        return checkpoint(value, kind, result)

    monkeypatch.setattr(r.agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    assert len(r.assistant.proposals()) == 1
    cancelled = action(world, run, "cancel")
    assert cancelled["state"] == "cancelled"
    assert len(cancelled["effects"]) == 1
    assert cancelled["effects"][0]["state"] == "rejected"
    assert r.assistant.proposals() == [] and r.tasks.listing()["tasks"] == []


def test_restart_recovers_draft_once_with_durable_intent(world, monkeypatch):
    r, _, _, _, clock = world
    run = start(
        world, mutation_requests=[{"tool": "task_create_draft", "arguments": {"title": "Once"}}]
    )
    checkpoint = r.agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "proposal":
            raise KeyboardInterrupt()
        return checkpoint(value, kind, result)

    monkeypatch.setattr(r.agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    pid = r.assistant.proposals()[0]["id"]
    clock[0] += timedelta(seconds=61)
    r.agent_runs = AgentRunService(r)
    waiting = drive(world, run)
    assert waiting["proposal_ids"] == [pid]
    assert len(r.assistant.proposals()) == 1


def test_restart_applies_returned_model_decision_without_new_paid_call(world, monkeypatch):
    r, _, _, _, clock = world
    config = model(world)
    calls = script(r, [{"action": "plan", "plan": ["Read selected evidence"]}])
    run = start(world, **config)
    monkeypatch.setattr(
        r.agent_runs, "_checkpoint", lambda *a: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        r.agent_runs.advance_one()
    clock[0] += timedelta(seconds=61)
    r.agent_runs = AgentRunService(r)
    r.agent_runs.advance_one()
    assert len(calls) == 1 and detail(world, run)["run"]["plan"] == ["Read selected evidence"]


def test_cancel_during_first_artifact_fences_second_dispatch(world, monkeypatch):
    r = world[0]
    run = start(world)
    publish = r.artifacts.publish
    calls = []

    def cancel_after_first(*args, **kwargs):
        result = publish(*args, **kwargs)
        calls.append(result["artifact"]["id"])
        action(world, run, "cancel")
        return result

    monkeypatch.setattr(r.artifacts, "publish", cancel_after_first)
    drive(world, run, stop=("cancelled",))
    assert len(calls) == 1
    # Cancellation does not pretend the already-written file was rolled back.
    assert len(detail(world, run)["artifacts"]) == 1


def test_model_selected_unread_source_prevents_success(world):
    r, _, session, source, _ = world
    second = r.sources.ingest(
        SourceInput(name="second.txt", format="text"),
        b"Important missing requirement\n",
        "second",
        session_hash=session,
    )["source"]
    config = model(world)
    eid = "source:" + source["id"]
    script(
        r,
        [
            {"action": "plan", "plan": ["Read", "Report"]},
            {"action": "read", "evidence_id": eid},
            {
                "action": "report",
                "report": {
                    "summary": "Incomplete report",
                    "sections": [
                        {"title": "Finding", "text": "Read one source", "evidence_ids": [eid]}
                    ],
                },
            },
            {"action": "finish"},
        ],
    )
    run = start(world, source_ids=[source["id"], second["id"]], **config)
    result = drive(world, run)
    assert result["state"] == "partial"
    assert result["unmet_requirements"] == [
        {"code": "RUN_SELECTED_EVIDENCE_UNREAD", "evidence_id": "source:" + second["id"]}
    ]


def test_model_batch_read_accumulates_actual_evidence_under_budget(world):
    r, _, session, source, _ = world
    second = r.sources.ingest(
        SourceInput(name="second.txt", format="text"),
        b"Extra scope\n",
        "second",
        session_hash=session,
    )["source"]
    config = model(world)
    ids = ["source:" + source["id"], "source:" + second["id"]]
    seen = script(
        r,
        [
            {"action": "plan", "plan": ["Read both", "Compare"]},
            {"action": "read", "evidence_ids": ids},
            {
                "action": "report",
                "report": {
                    "summary": "Comparison",
                    "sections": [
                        {"title": "Finding", "text": "Both sources considered", "evidence_ids": ids}
                    ],
                },
            },
            {"action": "finish"},
        ],
    )
    run = start(world, source_ids=[source["id"], second["id"]], **config)
    result = drive(world, run)
    assert result["state"] == "succeeded" and result["model_calls"] == 4
    assert {e["id"] for e in seen[-1]["observations"]} == set(ids)


def test_model_truncated_source_marks_required_coverage_unmet(world):
    r, _, session, _, _ = world
    source = r.sources.ingest(
        SourceInput(name="long.txt", format="text"),
        b"line with useful evidence\n" * 200,
        "long",
        session_hash=session,
    )["source"]
    config = model(world)
    eid = "source:" + source["id"]
    script(
        r,
        [
            {"action": "plan", "plan": ["Read"]},
            {"action": "read", "evidence_id": eid},
            {
                "action": "report",
                "report": {
                    "summary": "Excerpt only",
                    "sections": [
                        {"title": "Finding", "text": "Partial evidence", "evidence_ids": [eid]}
                    ],
                },
            },
            {"action": "finish"},
        ],
    )
    run = start(world, source_ids=[source["id"]], **config)
    result = drive(world, run)
    assert result["state"] == "partial"
    unmet = result["unmet_requirements"][0]
    assert unmet["code"] == "RUN_SOURCE_PARTIAL_COVERAGE"
    assert unmet["covered_through_line"] < unmet["total_lines"]
    evidence = result["evidence"][0]
    assert evidence["coverage"]["end_line"] == evidence["excerpt"].count("\n")


def test_required_section_is_not_model_success_flag(world):
    run = start(world, required_sections=["A requested comparison"])
    result = drive(world, run)
    assert result["state"] == "partial"
    assert result["unmet_requirements"][0]["code"] == "RUN_REQUIRED_SECTION_MISSING"


def test_model_review_continuation_uses_saved_result(world):
    r, _, _, source, _ = world
    config = model(world)
    eid = "source:" + source["id"]
    mutation = {"tool": "task_create_draft", "arguments": {"title": "Read scope"}, "required": True}
    seen = script(
        r,
        [
            {"action": "plan", "plan": ["Read", "Report", "Prepare task"]},
            {"action": "read", "evidence_id": eid},
            {
                "action": "report",
                "report": {
                    "summary": "Plan",
                    "sections": [{"title": "Finding", "text": "Read scope", "evidence_ids": [eid]}],
                },
            },
            {"action": "propose", "mutation": mutation},
            {"action": "finish"},
        ],
    )
    run = start(world, allow_mutation_proposals=True, **config)
    waiting = drive(world, run)
    assert waiting["state"] == "waiting_review"
    r.assistant.decide(waiting["proposal_ids"][0], "confirm", "confirm")
    result = drive(world, run)
    assert result["state"] == "succeeded"
    assert seen[-1]["reviewed_effects"][0]["state"] == "verified"
    assert len(r.tasks.listing()["tasks"]) == 1


def test_real_calendar_creation_drift_is_not_verified(world):
    from desk.schemas import EventAction, EventInput
    from desk.agent_tools import verify_proposal

    r = world[0]
    event = {
        "title": "Review",
        "start_local": "2026-10-13T10:00:00",
        "end_local": "2026-10-13T11:00:00",
    }
    proposal = r.assistant.tool("calendar_create_draft", {"event": event}, "draft")["proposal"]
    result = r.assistant.decide(proposal["id"], "confirm", "save")
    assert verify_proposal(r, proposal["id"])["state"] == "verified"
    eid = result["result"]["event_ids"][0]
    changed = EventInput(**{**event, "title": "Different"})
    r.store.event_action(
        eid, EventAction(action="update", scope="series", expected_version=1, event=changed), "edit"
    )
    assert verify_proposal(r, proposal["id"])["state"] == "unknown"


def test_nine_sources_valid_for_deterministic_report(world):
    r, _, session, source, _ = world
    ids = [source["id"]]
    for n in range(8):
        ids.append(
            r.sources.ingest(
                SourceInput(name=f"{n}.txt", format="text"),
                f"Entry {n}\n".encode(),
                f"src{n}",
                session_hash=session,
            )["source"]["id"]
        )
    run = start(world, source_ids=ids)
    assert drive(world, run)["state"] == "succeeded"


def test_model_missing_source_consent_never_calls(world):
    r = world[0]
    config = model(world)
    script(r, [])
    with pytest.raises(DomainError, match="RUN_SOURCE_SHARING_NOT_APPROVED"):
        start(world, **{**config, "share_sources_with_provider": False})


def test_routes_owner_only_and_real_session_bound(tmp_path):
    from fastapi.testclient import TestClient
    from desk.app import create_app

    app = create_app(tmp_path, password="fixture-only")
    with TestClient(app, headers={"X-Desk-Request": "1"}) as client:
        assert client.get("/api/agent-runs").status_code == 403
        assert (
            client.post(
                "/api/session", json={"username": "owner", "password": "fixture-only"}
            ).status_code
            == 200
        )
        response = client.get("/api/agent-runs/scope")
        assert response.status_code == 200
        assert response.json()["modes"] == ["deterministic"]


def test_hidden_private_masks_caches_but_allows_cancel(world):
    from desk.schemas import SettingsInput

    r = world[0]
    run = start(world)
    with r.store.connection() as conn:
        settings = r.store.settings(conn)
    r.store.update_settings(
        SettingsInput(
            expected_version=settings["version"], timezone=settings["timezone"], hide_private=True
        ),
        "hide",
    )
    listing = r.agent_runs.listing(world[1])["runs"][0]
    assert listing["private_hidden"] and "goal" not in listing
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        detail(world, run)
    result = r.agent_runs.action(
        run["id"],
        RunAction(action="cancel", expected_version=listing["version"]),
        "cancel",
        world[1],
    )["run"]
    assert result["state"] == "cancelled" and "goal" not in result


def test_plan_revision_and_budget_are_not_reset_by_resume(world):
    r = world[0]
    config = model(world)
    seen = script(r, [{"action": "plan", "plan": ["Use evidence"]}] * 8)
    run = start(world, **config)
    result = drive(world, run)
    assert result["state_reason"] == "RUN_MODEL_BUDGET_EXCEEDED" and len(seen) == 8
    action(world, run, "resume")
    result = drive(world, run)
    assert result["model_calls"] == 8 and len(seen) == 8


def test_model_more_than_ten_inputs_rejected_before_dispatch(world):
    from pydantic import ValidationError

    r, _, session, source, _ = world
    ids = [source["id"]]
    for n in range(10):
        ids.append(
            r.sources.ingest(
                SourceInput(name=f"{n}.txt", format="text"),
                f"Row {n}\n".encode(),
                f"src{n}",
                session_hash=session,
            )["source"]["id"]
        )
    config = model(world)
    with pytest.raises(ValidationError):
        start(world, source_ids=ids, **config)


def test_model_unobserved_mutation_target_is_rejected(world):
    r = world[0]
    task = r.tasks.create(TaskInput(title="Selected"), "task")["task"]
    config = model(world)
    script(
        r,
        [
            {"action": "plan", "plan": ["Propose change"]},
            {
                "action": "propose",
                "mutation": {
                    "tool": "task_change_draft",
                    "arguments": {
                        "task_id": task["id"],
                        "change": {"action": "note", "expected_version": 1, "note": "New note"},
                    },
                },
            },
        ],
    )
    run = start(world, task_ids=[task["id"]], allow_mutation_proposals=True, **config)
    assert drive(world, run)["state_reason"] == "RUN_OBSERVED_VERSION_REQUIRED"
    assert r.assistant.proposals() == []


def test_corrupt_artifact_prevents_terminal_success(world, monkeypatch):
    r = world[0]
    run = start(world)
    original = r.artifacts.detail

    def unverified(*args, **kwargs):
        result = original(*args, **kwargs)
        return {**result, "status": "unknown", "verification": "unverified"}

    monkeypatch.setattr(r.artifacts, "detail", unverified)
    assert drive(world, run)["state_reason"] == "RUN_ARTIFACT_OUTCOME_UNKNOWN"


def test_read_batch_restart_reuses_completed_acquisitions(world):
    r, _, session, source, _ = world
    second = r.sources.ingest(
        SourceInput(name="second.txt", format="text"), b"Second\n", "second", session_hash=session
    )["source"]
    config = model(world)
    ids = ["source:" + source["id"], "source:" + second["id"]]
    seen = script(
        r, [{"action": "plan", "plan": ["Read both"]}, {"action": "read", "evidence_ids": ids}]
    )
    run = start(world, source_ids=[source["id"], second["id"]], **config)
    for _ in range(3):
        r.agent_runs.advance_one()
    assert detail(world, run)["run"]["evidence_count"] == 1
    r.agent_runs = AgentRunService(r)
    r.agent_runs.advance_one()
    assert detail(world, run)["run"]["evidence_count"] == 2
    assert len(seen) == 2


def test_post_report_read_cannot_retroactively_repair_output(world):
    r, _, session, source, _ = world
    second = r.sources.ingest(
        SourceInput(name="later.txt", format="text"),
        b"Later source\n",
        "later",
        session_hash=session,
    )["source"]
    config = model(world)
    eid = "source:" + source["id"]
    script(
        r,
        [
            {"action": "plan", "plan": ["Read", "Report"]},
            {"action": "read", "evidence_id": eid},
            {
                "action": "report",
                "report": {
                    "summary": "Old report",
                    "sections": [{"title": "Finding", "text": "One source", "evidence_ids": [eid]}],
                },
            },
            {"action": "read", "evidence_id": "source:" + second["id"]},
            {"action": "finish"},
        ],
    )
    run = start(world, source_ids=[source["id"], second["id"]], **config)
    result = drive(world, run)
    assert result["evidence_count"] == 2 and result["state"] == "partial"
    assert result["unmet_requirements"][0]["code"] == "RUN_SELECTED_EVIDENCE_UNREAD"


def test_mutation_schema_is_given_to_adaptive_model(world):
    r = world[0]
    config = model(world)
    systems = []

    def generate(system, *args):
        systems.append(system)
        return AgentDecision(action="ask", question="Clarify")

    r.text_ai.generate = generate
    start(world, allow_mutation_proposals=True, **config)
    r.agent_runs.advance_one()
    assert "expected_version" in systems[0] and "additional_dates" in systems[0]
    assert "additionalProperties" in systems[0] and "task_change_draft" in systems[0]


def test_control_receipts_bounded_without_disabling_cancel(world):
    r = world[0]
    run = start(world)
    with r.store.connection(write=True) as conn:
        for n in range(63):
            conn.execute(
                "INSERT INTO agent_run_operations VALUES(?,?,?)",
                (f"past-{n}", "bounded-test", run["id"]),
            )
    with pytest.raises(DomainError, match="RUN_CONTROL_LIMIT_REACHED"):
        action(world, run, "pause")
    assert action(world, run, "cancel")["state"] == "cancelled"


def test_real_api_selected_source_to_downloadable_artifacts(tmp_path):
    from fastapi.testclient import TestClient
    from desk.app import create_app

    app = create_app(tmp_path, password="fixture-only")
    # No lifespan worker here: advance the production service deterministically.
    client = TestClient(app, headers={"X-Desk-Request": "1"})
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": "fixture-only"}
        ).status_code
        == 200
    )
    source = client.post(
        "/api/sources/upload?name=notes.md&format=markdown",
        content=b"# Project\nReview typed tool safety.\n",
        headers={"X-Operation-Id": "upload"},
    ).json()["source"]
    scope = client.get("/api/agent-runs/scope").json()
    response = client.post(
        "/api/agent-runs",
        json={
            "goal": "Compile source-backed work package",
            "retain": True,
            "source_ids": [source["id"]],
            "scope_revision": scope["scope_revision"],
        },
        headers={"X-Operation-Id": "run"},
    )
    assert response.status_code == 200
    rid = response.json()["run"]["id"]
    for _ in range(5):
        app.state.runtime.agent_runs.advance_one()
    result = client.get("/api/agent-runs/" + rid).json()
    assert result["run"]["state"] == "succeeded"
    for artifact in result["artifacts"]:
        response = client.get("/api/artifacts/" + artifact["id"] + "/download")
        assert response.status_code == 200
        assert hashlib.sha256(response.content).hexdigest() == artifact["sha256"]
        assert "attachment" in response.headers["content-disposition"]
    assert (
        b"Review typed tool safety"
        in client.get(
            "/api/artifacts/"
            + next(a["id"] for a in result["artifacts"] if a["format"] == "markdown")
            + "/download"
        ).content
    )


def test_actual_routes_keep_run_drafts_owner_only_and_preserve_legacy(tmp_path):
    from fastapi.testclient import TestClient
    from desk.app import create_app

    app = create_app(tmp_path, password="fixture-only")
    r = app.state.runtime
    owner = TestClient(app, headers={"X-Desk-Request": "1"})
    owner.post("/api/session", json={"username": "owner", "password": "fixture-only"})
    with r.store.connection(write=True) as conn:
        _, token = r.access._enrol(conn, "Fixture controller", "controller")
    controller = TestClient(
        app, headers={"X-Desk-Request": "1", "Authorization": "Bearer " + token}
    )
    source = owner.post(
        "/api/sources/upload?name=private.md&format=markdown",
        content=b"Private source-derived work\n",
        headers={"X-Operation-Id": "src"},
    ).json()["source"]
    scope = owner.get("/api/agent-runs/scope").json()
    created = owner.post(
        "/api/agent-runs",
        json={
            "goal": "Prepare source-backed task",
            "retain": True,
            "source_ids": [source["id"]],
            "scope_revision": scope["scope_revision"],
            "mutation_requests": [
                {
                    "tool": "task_create_draft",
                    "arguments": {"title": "Private source-derived draft"},
                }
            ],
        },
        headers={"X-Operation-Id": "start"},
    ).json()["run"]
    for _ in range(5):
        r.agent_runs.advance_one()
    pid = owner.get("/api/agent-runs/" + created["id"]).json()["run"]["proposal_ids"][0]
    assert r.agent_runs.is_run_proposal(pid)
    assert not any(
        p["id"] == pid for p in controller.get("/api/assistant/proposals").json()["proposals"]
    )
    assert any(p["id"] == pid for p in owner.get("/api/assistant/proposals").json()["proposals"])
    for choice in ["confirm", "cancel"]:
        assert (
            controller.post(
                f"/api/assistant/proposals/{pid}/decisions",
                json={"action": choice},
                headers={"X-Operation-Id": "deny-" + choice},
            ).status_code
            == 403
        )
    confirmed = owner.post(
        f"/api/assistant/proposals/{pid}/decisions",
        json={"action": "confirm"},
        headers={"X-Operation-Id": "owner-confirm"},
    )
    assert confirmed.status_code == 200 and confirmed.json()["saved"]
    legacy = r.assistant.tool("task_create_draft", {"title": "Legacy controller draft"}, "legacy")[
        "proposal"
    ]["id"]
    assert not r.agent_runs.is_run_proposal(legacy)
    assert any(
        p["id"] == legacy for p in controller.get("/api/assistant/proposals").json()["proposals"]
    )
    assert (
        controller.post(
            f"/api/assistant/proposals/{legacy}/decisions",
            json={"action": "confirm"},
            headers={"X-Operation-Id": "legacy-confirm"},
        ).status_code
        == 200
    )


def test_orphan_run_draft_guard_before_parent_checkpoint(world, monkeypatch):
    r = world[0]
    run = start(
        world,
        mutation_requests=[{"tool": "task_create_draft", "arguments": {"title": "Private orphan"}}],
    )
    checkpoint = r.agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "proposal":
            raise KeyboardInterrupt()
        return checkpoint(value, kind, result)

    monkeypatch.setattr(r.agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    with r.store.connection() as conn:
        assert r.agent_runs._get(conn, run["id"])["proposal_ids"] == []
    proposal = r.assistant.proposals()[0]
    assert r.agent_runs.is_run_proposal(proposal["id"])
    controller = {"kind": "controller", "id": "fixture"}
    assert r.agent_runs.filter_proposals([proposal], controller) == []
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.agent_runs.require_proposal_access(proposal["id"], controller)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.agent_runs.require_proposal_access(proposal["id"], {"kind": "owner"})
    r.agent_runs.require_proposal_access(proposal["id"], world[1])


def test_owner_hidden_run_draft_is_filtered_and_cannot_be_confirmed(world):
    from desk.schemas import SettingsInput

    r = world[0]
    run = start(
        world,
        mutation_requests=[
            {"tool": "task_create_draft", "arguments": {"title": "Sensitive draft"}}
        ],
    )
    waiting = drive(world, run)
    pid = waiting["proposal_ids"][0]
    with r.store.connection() as conn:
        settings = r.store.settings(conn)
    r.store.update_settings(
        SettingsInput(
            expected_version=settings["version"], timezone=settings["timezone"], hide_private=True
        ),
        "hide",
    )
    assert r.agent_runs.filter_proposals(r.assistant.proposals(), world[1]) == []
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        r.agent_runs.require_proposal_access(pid, world[1])


@pytest.mark.parametrize("same_intent", [False, True])
def test_recovered_effect_receipt_must_match_reserved_typed_intent(world, monkeypatch, same_intent):
    r = world[0]
    run = start(
        world,
        mutation_requests=[
            {"tool": "task_create_draft", "arguments": {"title": "Requested exact task"}}
        ],
    )
    dispatch = r.agent_runs._dispatch_effect
    prior = []

    def collision(value):
        intent = value["pending_effect"]
        args = (
            intent["mutation"]["arguments"] if same_intent else {"title": "Unrelated legacy task"}
        )
        prior.append(r.assistant.tool("task_create_draft", args, intent["key"])["proposal"])
        return dispatch(value)

    monkeypatch.setattr(r.agent_runs, "_dispatch_effect", collision)
    result = drive(world, run)
    proposal = prior[0]
    if same_intent:
        assert result["state"] == "waiting_review"
        assert result["proposal_ids"] == [proposal["id"]]
        assert r.agent_runs.is_run_proposal(proposal["id"])
        r.assistant.decide(proposal["id"], "confirm", "confirm")
        assert drive(world, run)["state"] == "succeeded"
        assert r.tasks.listing()["tasks"][0]["title"] == "Requested exact task"
    else:
        assert result["state_reason"] == "RUN_EFFECT_RECEIPT_CONFLICT"
        assert result["effects"] == [] and result["proposal_ids"] == []
        assert not r.agent_runs.is_run_proposal(proposal["id"])
        assert r.agent_runs.filter_proposals([proposal], {"kind": "controller"}) == [proposal]
        assert r.assistant.proposals()[0]["state"] == "pending"  # unrelated draft not cancelled
        r.assistant.decide(proposal["id"], "confirm", "legacy-confirm")
        assert detail(world, run)["run"]["state"] == "blocked"
        assert r.tasks.listing()["tasks"][0]["title"] == "Unrelated legacy task"


def test_decimal_statistics_exact_in_admitted_range():
    from desk.agent_tools import table_stats

    value = table_stats(
        "hours,unsupported\n0.1,0.0000000000000000000001\n0.2,0.0000000000000000000002\n"
    )
    assert value["numeric_column_sums"] == {"hours": "0.3"}
