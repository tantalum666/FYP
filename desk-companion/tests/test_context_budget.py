"""Long conversations keep approval state and drop lower-value context first."""

from datetime import UTC, datetime
from uuid import uuid4

from desk.agent_loop import AgentLoop
from desk.assistant import AssistantMessage
from desk.context import pack_conversation
from desk.context_budget import fit_context
from desk.model_provider import ModelStep, ScriptedProvider
from desk.runtime import Runtime
from desk.store import Store, encode
from desk.text_ai import TextPlan
from desk.turns import remember_exchange

from test_agent_loop import _runtime


def _stamp(runtime, memory_id, updated_at):
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE owner_memories SET updated_at=? WHERE id=?",
            (updated_at, memory_id),
        )


def test_overlap_beats_a_newer_unrelated_fact_and_a_deleted_fact_stays_out(tmp_path):
    runtime = _runtime(tmp_path)
    older = runtime.memory.create("晚上要带红灯笼。", "lantern")["memory"]
    newer = runtime.memory.create("苹果" * 80, "apple")["memory"]
    _stamp(runtime, older["id"], "2026-10-01T00:00:00+00:00")
    _stamp(runtime, newer["id"], "2026-10-20T00:00:00+00:00")
    wide = pack_conversation(runtime, user_message="灯笼", budget=100000)
    bodies = [row["body"] for row in wide["memory"]]
    assert bodies[0] == "晚上要带红灯笼。"
    assert newer["body"] in bodies
    tight = pack_conversation(runtime, user_message="灯笼", budget=len(encode(wide)) - 1)
    kept = [row["body"] for row in tight["memory"]]
    assert "晚上要带红灯笼。" in kept
    assert newer["body"] not in kept
    runtime.memory.delete(older["id"], older["version"], "delete-lantern")
    assert all("灯笼" not in row["body"] for row in pack_conversation(runtime)["memory"])


def test_pending_approval_survives_a_tiny_budget(tmp_path):
    runtime = _runtime(tmp_path)
    draft = runtime.assistant.tool(
        "memory_save_draft", {"body": "Keep this approval"}, "approval-row"
    )
    proposal_id = draft["proposal"]["id"]
    packed = pack_conversation(runtime, budget=1)
    row = packed["pending_approvals"][0]
    assert row["id"] == proposal_id
    assert row["state"] == "pending" and row["saved"] is False
    assert len(encode(packed)) > 1
    hidden = pack_conversation(runtime, include_memory=False, budget=100000)
    assert hidden["pending_approvals"] == []
    assert hidden["memory"] == []
    assert hidden["turns"] == []


def test_older_turns_drop_before_the_newest_and_the_profile_stays(tmp_path):
    runtime = _runtime(tmp_path)
    for index in range(4):
        remember_exchange(runtime, f"op-{index}", f"user-{index}", f"assistant-{index}")
    wide = pack_conversation(runtime, budget=100000)
    assert wide["profile"].startswith("You are Desk Companion")
    assert wide["turns"][0]["body"] == "assistant-3"
    tight = pack_conversation(runtime, budget=len(encode(wide)) - 1)
    bodies = [row["body"] for row in tight["turns"]]
    assert "assistant-3" in bodies
    assert "user-0" not in bodies
    assert tight["profile"].startswith("You are Desk Companion")


def test_selected_task_and_tool_result_outlive_calendar_tasks_and_memories():
    fitted = fit_context(
        {
            "profile": "You are Desk Companion",
            "user_message": "What is left?",
            "selected_task": {"id": "task-1", "title": "Keep the report"},
            "pending_approvals": [
                {
                    "id": "draft-1",
                    "kind": "task_change",
                    "state": "pending",
                    "expires_at": "2026-10-27T08:05:00+00:00",
                    "saved": False,
                    "preview": "status",
                }
            ],
            "last_tool_result": {
                "tool": "memory_save_draft",
                "result": {
                    "saved": False,
                    "proposal": {
                        "id": "draft-9",
                        "kind": "memory_save",
                        "state": "pending",
                        "expires_at": "2026-10-27T08:05:00+00:00",
                    },
                    "blob": "x" * 5000,
                },
            },
            "calendar": [{"title": "noise"} for _ in range(6)],
            "tasks": [{"id": "other", "title": "drop me"}],
            "turns": [{"role": "user", "body": "old turn"}],
            "memory": [{"id": "m", "version": 1, "body": "unrelated", "updated_at": "2026-10-01"}],
            "more_tasks": False,
        },
        budget=220,
    )
    assert fitted["selected_task"]["title"] == "Keep the report"
    assert fitted["user_message"] == "What is left?"
    assert fitted["pending_approvals"][0]["id"] == "draft-1"
    assert fitted["pending_approvals"][0]["saved"] is False
    assert fitted["last_tool_result"]["result"]["saved"] is False
    assert fitted["last_tool_result"]["result"]["proposal"]["id"] == "draft-9"
    assert fitted["calendar"] == []
    assert fitted["tasks"] == []
    assert fitted["more_tasks"] is True
    assert fitted["turns"] == []
    assert fitted["memory"] == []


def test_loop_refits_after_a_tool_without_dropping_the_result(tmp_path, monkeypatch):
    monkeypatch.setattr("desk.context_budget.DEFAULT_BUDGET", 160)
    runtime = _runtime(tmp_path)
    provider = ScriptedProvider(
        [
            ModelStep("Checking the clock.", "owner_clock", {}),
            ModelStep("Tuesday morning is clear.", "none", {}),
        ]
    )
    context = {
        "user_message": "What time is it?",
        "pending_approvals": [
            {
                "id": "keep-me",
                "kind": "memory_save",
                "state": "pending",
                "expires_at": "2026-10-27T08:05:00+00:00",
                "saved": False,
                "preview": "fact",
            }
        ],
        "calendar": [{"title": "noise " * 20} for _ in range(4)],
        "turns": [{"role": "user", "body": "ancient"}],
    }
    reply = AgentLoop(runtime, provider).run(
        system="persona",
        context=context,
        key="budget-clock",
        language="en",
        allow_memory=True,
    )
    second = provider.contexts[1]
    assert second["pending_approvals"][0]["id"] == "keep-me"
    assert second["pending_approvals"][0]["saved"] is False
    assert second["last_tool_result"]["tool"] == "owner_clock"
    assert second["calendar"] == []
    assert "ancient" not in [row["body"] for row in second["turns"]]
    assert reply["message"] == "Tuesday morning is clear."


def test_owner_turns_are_replayed_and_a_paired_session_does_not_receive_them(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path)
    runtime.memory.create("Private owner fact", "private-fact")
    captured = []

    def generate(system, context, schema, purpose):
        captured.append(context)
        return TextPlan(message="Public reply", tool="none")

    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)
    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    runtime.text_ai.message(AssistantMessage(message="Hello lantern"), "owner-one")
    runtime.text_ai.message(AssistantMessage(message="Next question"), "owner-two")
    runtime.text_ai.message(
        AssistantMessage(message="Hello lantern"), "display-one", allow_memory=False
    )
    assert captured[0]["turns"] == []
    assert captured[0]["memory"][0]["body"] == "Private owner fact"
    bodies = [row["body"] for row in captured[1]["turns"]]
    assert bodies[0] == "Public reply"
    assert "Hello lantern" in bodies
    assert captured[2]["turns"] == []
    assert captured[2]["memory"] == []


def test_store_clock_used_by_turns_is_the_runtime_clock(tmp_path):
    folder = tmp_path / uuid4().hex
    runtime = Runtime(
        Store(folder, password="fixture-only", clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))
    )
    remember_exchange(runtime, "one", "hello", "there")
    assert pack_conversation(runtime)["turns"][0]["created_at"].startswith("2026-10-27")
