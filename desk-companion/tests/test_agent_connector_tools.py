"""Shared durable planner to real local MCP HTTP fixture; no external/live-model claim."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from desk.agent_run_schemas import AgentDecision, RunCreate, RunAction
from desk.agent_runs import AgentRunService
from desk.connectors.agent_adapter import connector_adapters
from desk.store import DomainError
from test_mcp_connectors import server as server, world as world, ARGS


def start(world, **changes):
    runtime, service, owner, _, _, _, _ = world
    runtime.agent_tool_adapters = connector_adapters(service)
    destination = next(
        d["id"] for d in runtime.personal_context.destinations() if d["kind"] == "text"
    )
    payload = dict(
        goal="Create the reviewed public fixture note and report the actual tool response",
        mode="model",
        retain=True,
        provider_destination_id=destination,
        connector_tool_ids=["mcp.fixture.notes.create"],
        share_connector_results_with_provider=True,
        scope_revision=runtime.agent_runs.scope(owner)["scope_revision"],
    )
    payload.update(changes)
    return runtime.agent_runs.create(RunCreate(**payload), uuid4().hex, owner)["run"]


def detail(world, run):
    return world[0].agent_runs.detail(run["id"], world[2])["run"]


def drive(world, run):
    for _ in range(30):
        world[0].agent_runs.advance_one()
        world[5][0] += timedelta(seconds=2)
        value = detail(world, run)
        if value["state"] in {
            "waiting_review",
            "waiting_input",
            "blocked",
            "partial",
            "succeeded",
            "cancelled",
        }:
            return value
    raise AssertionError(value)


def script(world, *, required=True):
    seen = []

    def generate(system, context, schema, purpose):
        seen.append(context)
        if not context["plan"]:
            return AgentDecision(
                action="plan",
                plan=["Prepare exact connector review", "Inspect actual returned result"],
            )
        if not context["reviewed_effects"]:
            return AgentDecision(
                action="tool",
                tool_call={
                    "tool": "mcp.fixture.notes.create",
                    "arguments": {"arguments": ARGS, "public_only": True},
                    "required": required,
                },
            )
        if not context["observations"]:
            return AgentDecision(
                action="ask",
                question="The connector outcome is unknown; inspect the existing intent.",
            )
        if not context["artifacts"]:
            return AgentDecision(
                action="report",
                report={
                    "summary": "The remote service returned a response; actual write is not independently verified.",
                    "sections": [
                        {
                            "title": "Returned result",
                            "text": context["observations"][0]["excerpt"],
                            "evidence_ids": [context["observations"][0]["id"]],
                        }
                    ],
                },
            )
        return AgentDecision(action="finish")

    world[0].text_ai.generate = generate
    return seen


def approve(world, run):
    effect = detail(world, run)["effects"][0]
    item = world[1].detail(effect["reference_id"], world[2])
    world[1].approve(item["id"], item["version"], item["intent_hash"], world[2], public_only=True)
    return item


def test_planner_selects_registered_connector_reviews_and_continues_without_false_verification(
    world,
):
    seen = script(world)
    run = start(world)
    waiting = drive(world, run)
    assert waiting["state"] == "waiting_review" and world[4].saved == []
    spec = seen[0]["available_tools"][0]
    assert (
        spec["arguments"]["properties"]["arguments"]["properties"]["notebook"]["const"]
        == "public-fixture"
    )
    count = len(seen)
    world[0].agent_runs.advance_one()
    assert len(seen) == count
    approve(world, run)
    world[1].advance_one()
    world[5][0] += timedelta(seconds=2)
    final = drive(world, run)
    assert final["state"] == "partial" and final["state_reason"] == "RUN_REQUIRED_CHANGE_UNMET"
    assert final["effects"][0]["state"] == "observed"
    assert final["evidence"][0]["kind"] == "connector"
    assert final["evidence"][0]["coverage"]["independent_outcome_verified"] is False
    assert seen[-1]["reviewed_effects"][0]["verified"] is False
    assert world[4].saved == [ARGS]
    assert len([r for r in world[4].requests if r["method"] == "tools/call"]) == 1


def test_optional_connector_observation_allows_report_without_claiming_verified_write(world):
    script(world, required=False)
    run = start(world)
    drive(world, run)
    approve(world, run)
    world[1].advance_one()
    final = drive(world, run)
    assert final["state"] == "succeeded"
    assert final["effects"][0]["state"] == "observed" and final["effects"][0]["verified"] is False
    assert final["state_reason"] == "RUN_OUTPUTS_VERIFIED_QUALITY_UNASSESSED"


def test_unknown_connector_result_never_replays_and_returns_to_planner(world):
    seen = script(world)
    run = start(world)
    drive(world, run)
    approve(world, run)
    world[4].behavior = "disconnect"
    world[1].advance_one()
    result = drive(world, run)
    assert result["state"] == "waiting_input" and result["effects"][0]["state"] == "unknown"
    assert seen[-1]["reviewed_effects"][0]["state"] == "unknown"
    assert world[4].saved == [ARGS]
    assert not world[1].advance_one()
    assert world[4].saved == [ARGS]


@pytest.mark.parametrize(
    "private",
    [
        {"source_ids": ["private"]},
        {"task_ids": ["private"]},
        {"event_ids": ["private"]},
        {"personal_context": {"memory_ids": ["private"], "retain_derived_context": True}},
    ],
)
def test_connector_grant_cannot_mix_private_selected_data(world, private):
    with pytest.raises(ValidationError, match="Public connector runs"):
        start(world, **private)
    assert world[4].requests == []


def test_connector_output_needs_separate_provider_sharing_ack(world):
    with pytest.raises(ValidationError, match="connector-result sharing"):
        start(world, share_connector_results_with_provider=False)
    assert world[4].requests == []


def test_connector_pause_cancels_review_and_never_queues_network(world):
    script(world)
    run = start(world)
    waiting = drive(world, run)
    world[0].agent_runs.action(
        run["id"],
        RunAction(action="pause", expected_version=waiting["version"]),
        uuid4().hex,
        world[2],
    )
    assert detail(world, run)["state"] == "paused"
    assert world[1].detail(waiting["effects"][0]["reference_id"], world[2])["state"] == "cancelled"
    assert not world[1].advance_one() and world[4].requests == []


def test_connector_lost_parent_link_recovers_without_second_intent(world, monkeypatch):
    script(world)
    run = start(world)
    original = world[0].agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "tool_prepared":
            raise KeyboardInterrupt()
        return original(value, kind, result)

    monkeypatch.setattr(world[0].agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    with world[0].store.connection() as conn:
        before = conn.execute("SELECT id FROM connector_intents").fetchall()
    assert len(before) == 1
    world[0].agent_runs = AgentRunService(world[0])
    world[5][0] += timedelta(seconds=61)
    value = drive(world, run)
    assert value["state"] == "waiting_review"
    assert value["effects"][0]["reference_id"] == before[0]["id"]
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM connector_intents").fetchone()[0] == 1
    assert world[4].requests == []


def test_unselected_registered_connector_tool_cannot_be_chosen(world):
    script(world)
    with pytest.raises(DomainError, match="RUN_CONNECTOR_NOT_SELECTED"):
        start(world, connector_tool_ids=["mcp.fixture.other"])
    assert world[4].requests == []


def test_recovered_already_observed_child_is_verified_as_observation_and_never_stalls(
    world, monkeypatch
):
    script(world)
    run = start(world)
    original = world[0].agent_runs._checkpoint

    def crash(value, kind, result=None):
        if kind == "tool_prepared":
            raise KeyboardInterrupt()
        return original(value, kind, result)

    monkeypatch.setattr(world[0].agent_runs, "_checkpoint", crash)
    with pytest.raises(KeyboardInterrupt):
        drive(world, run)
    with world[0].store.connection() as conn:
        child_id = conn.execute("SELECT id FROM connector_intents").fetchone()[0]
    child = world[1].detail(child_id, world[2])
    world[1].approve(child_id, child["version"], child["intent_hash"], world[2], public_only=True)
    world[1].advance_one()
    assert world[4].saved == [ARGS]
    world[0].agent_runs = AgentRunService(world[0])
    world[5][0] += timedelta(seconds=61)
    assert drive(world, run)["state"] == "waiting_review"
    final = drive(world, run)
    assert final["state"] == "partial" and final["effects"][0]["state"] == "observed"
    assert world[4].saved == [ARGS]
