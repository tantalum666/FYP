"""A bounded plan is visible and does not write."""

from desk.agent_loop import AgentLoop
from desk.model_provider import ModelStep, ScriptedProvider

from test_agent_loop import _runtime


def _event():
    return {
        "event": {
            "title": "Review the draft",
            "start_local": "2026-10-28T09:00",
            "end_local": "2026-10-28T09:30",
            "timezone": "Asia/Hong_Kong",
        }
    }


def test_plan_then_draft_stays_unapproved_and_is_audited(tmp_path):
    runtime = _runtime(tmp_path)
    provider = ScriptedProvider(
        [
            ModelStep("Checking the clock.", "owner_clock", {}),
            ModelStep(
                "Here is a short plan.",
                "propose_plan",
                {
                    "title": "Tomorrow",
                    "steps": [
                        {"text": "Review the draft"},
                        {"text": "Keep the afternoon open"},
                    ],
                },
            ),
            ModelStep("I prepared one reminder.", "calendar_create_draft", _event()),
        ]
    )
    reply = AgentLoop(runtime, provider).run(
        system="persona",
        context={},
        key="plan-week",
        language="en",
        allow_memory=True,
    )
    assert provider.calls == 3
    assert reply["kind"] == "draft" and reply["saved"] is False
    assert "Review the draft" in reply["plan"]
    assert reply["proposal"]["kind"] == "create"
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    plan = next(row for row in runtime.assistant.audit.listing() if row["tool"] == "propose_plan")
    assert plan["risk"] == "read" and plan["saved"] is False
    assert "Keep the afternoon open" in plan["message"]
    assert plan["arguments"]["steps"][0]["text"] == "Review the draft"


def test_oversized_plan_is_refused_before_any_draft(tmp_path):
    runtime = _runtime(tmp_path)
    provider = ScriptedProvider(
        [
            ModelStep(
                "I planned everything.",
                "propose_plan",
                {"title": "Week", "steps": [{"text": f"Step {index}"} for index in range(6)]},
            ),
            ModelStep("Saving anyway.", "calendar_create_draft", _event()),
        ]
    )
    reply = AgentLoop(runtime, provider).run(
        system="persona",
        context={},
        key="too-big",
        language="en",
        allow_memory=True,
    )
    assert provider.calls == 1
    assert reply["kind"] == "clarify" and reply["saved"] is False
    assert reply["error"] == "TOOL_ARGUMENTS_INVALID"
    assert runtime.assistant.proposals() == []
