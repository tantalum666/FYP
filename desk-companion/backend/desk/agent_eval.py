"""Offline scenarios for the agent loop. No network and no hosted model.

Add a scenario by writing `scenario_<name>(new_runtime)`, raising AssertionError
when the contract fails, and registering the function in `run_all`. Use
ScriptedProvider for model steps. Do not open a socket. The text and voice
paths share execute_tool(); a scenario that needs voice submits one call
through ToolDispatcher and compares the audit row with the text loop.
"""

import asyncio
import copy
import os
from dataclasses import dataclass

from .agent_loop import AgentLoop
from .model_provider import ModelStep, ScriptedProvider
from .store import DomainError
from .tool_dispatch import ToolDispatcher


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    passed: bool
    detail: str


def run_all(new_runtime) -> list[ScenarioResult]:
    """Run every scripted scenario against a fresh runtime from new_runtime()."""
    results = []
    for scenario in (
        scenario_remind,
        scenario_recall,
        scenario_refuse,
        scenario_approval,
        scenario_step_bound,
        scenario_time_bound,
        scenario_provider_retry,
        scenario_voice_same_policy,
    ):
        try:
            scenario(new_runtime)
        except Exception as error:
            results.append(ScenarioResult(scenario.__name__, False, f"{type(error).__name__}: {error}"))
        else:
            results.append(ScenarioResult(scenario.__name__, True, ""))
    return results


def scenario_remind(new_runtime):
    runtime = new_runtime()
    provider = ScriptedProvider(
        [
            ModelStep(
                "I prepared a reminder for you to review.",
                "calendar_create_draft",
                {
                    "event": {
                        "title": "Submit the draft",
                        "start_local": "2026-10-28T09:00",
                        "end_local": "2026-10-28T09:30",
                    }
                },
            )
        ]
    )
    reply = _run(runtime, provider, "remind")
    if reply["kind"] != "draft" or reply["saved"] is not False:
        raise AssertionError(reply)
    if reply["proposal"]["kind"] != "create":
        raise AssertionError(reply["proposal"])
    with runtime.store.connection() as conn:
        saved = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if saved:
        raise AssertionError("reminder was written without approval")
    _expect_audit(runtime, tool="calendar_create_draft", risk="draft", outcome="ok", saved=False)


def scenario_recall(new_runtime):
    runtime = new_runtime()
    runtime.memory.create("The project code is lantern.", "fact")

    class Recall(ScriptedProvider):
        def complete(self, system, context):
            self.calls += 1
            self.contexts.append(copy.deepcopy(context))
            if self.calls == 1:
                return ModelStep("I will check what you told me.", "memory_query", {})
            memories = context["last_tool_result"]["result"]["memories"]
            return ModelStep(memories[0]["body"], "none", {})

    provider = Recall([])
    reply = _run(runtime, provider, "recall")
    if reply["kind"] != "reply" or reply["message"] != "The project code is lantern.":
        raise AssertionError(reply)
    if "lantern" in str(provider.contexts[0]):
        raise AssertionError("fact was placed in the prompt before the lookup")
    if len(runtime.memory.for_model()) != 1:
        raise AssertionError("lookup changed memory")
    _expect_audit(runtime, tool="memory_query", risk="read", outcome="ok", saved=False)


def scenario_refuse(new_runtime):
    runtime = new_runtime()
    provider = ScriptedProvider(
        [ModelStep("I deleted the folder.", "shell_exec", {"command": "rm -rf /"})]
    )
    reply = _run(runtime, provider, "refuse")
    if reply["kind"] != "refused" or reply["saved"] is not False:
        raise AssertionError(reply)
    if "deleted" in reply["message"] or reply.get("error") != "TOOL_NOT_ALLOWED":
        raise AssertionError(reply)
    if runtime.assistant.proposals():
        raise AssertionError("refusal created a draft")
    with runtime.store.connection() as conn:
        jobs = conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0]
    if jobs:
        raise AssertionError("refusal created a computer job")
    _expect_audit(runtime, tool="shell_exec", risk="refused", outcome="TOOL_NOT_ALLOWED", saved=False)


def scenario_approval(new_runtime):
    previous = os.environ.get("DESK_COMPUTER_ENABLED")
    os.environ["DESK_COMPUTER_ENABLED"] = "1"
    try:
        runtime = new_runtime()
        provider = ScriptedProvider(
            [
                ModelStep(
                    "Review this note.",
                    "computer_job_draft",
                    {"title": "Note", "content": "Hello"},
                )
            ]
        )
        reply = _run(runtime, provider, "approve")
        if reply["kind"] != "job" or reply["saved"] is not False or reply["job"]["state"] != "review":
            raise AssertionError(reply)
        if provider.calls != 1:
            raise AssertionError("approval draft was retried")
        if list(runtime.store.directory.glob("computer-notes/*.txt")):
            raise AssertionError("note was written before approval")
        _expect_audit(runtime, tool="computer_job_draft", risk="draft", outcome="ok", saved=False)
    finally:
        if previous is None:
            os.environ.pop("DESK_COMPUTER_ENABLED", None)
        else:
            os.environ["DESK_COMPUTER_ENABLED"] = previous


def scenario_step_bound(new_runtime):
    runtime = new_runtime()
    provider = ScriptedProvider([ModelStep("Checking.", "memory_query", {})] * 4)
    reply = AgentLoop(runtime, provider, max_steps=3).run(
        system="You are a test persona.",
        context={"user_message": "steps"},
        key="steps",
        language="en",
        allow_memory=True,
    )
    if provider.calls != 3 or reply["kind"] != "clarify" or "identify the task" not in reply["message"]:
        raise AssertionError((provider.calls, reply))
    if reply["saved"] is not False:
        raise AssertionError(reply)


def scenario_time_bound(new_runtime):
    runtime = new_runtime()
    ticks = iter([0, 0, 0, 100])
    provider = ScriptedProvider(
        [
            ModelStep("Checking.", "memory_query", {}),
            ModelStep("Again.", "memory_query", {}),
        ]
    )
    reply = AgentLoop(runtime, provider, max_seconds=10, clock=lambda: next(ticks)).run(
        system="You are a test persona.",
        context={"user_message": "time"},
        key="time",
        language="en",
        allow_memory=True,
    )
    if provider.calls != 1 or reply["kind"] != "clarify" or "time limit" not in reply["message"]:
        raise AssertionError((provider.calls, reply))
    if len(runtime.assistant.audit.listing()) != 1:
        raise AssertionError(runtime.assistant.audit.listing())


def scenario_provider_retry(new_runtime):
    runtime = new_runtime()
    provider = ScriptedProvider(
        [DomainError("TEXT_AI_UNAVAILABLE", 503), ModelStep("Still here.", "none", {})]
    )
    reply = _run(runtime, provider, "retry")
    if provider.calls != 2 or reply["message"] != "Still here.":
        raise AssertionError((provider.calls, reply))
    if runtime.assistant.audit.listing():
        raise AssertionError("a provider retry recorded a tool call")


def scenario_voice_same_policy(new_runtime):
    runtime = new_runtime()
    provider = ScriptedProvider(
        [ModelStep("I deleted the folder.", "shell_exec", {"command": "rm -rf /"})]
    )
    reply = _run(runtime, provider, "voice-policy")

    async def once():
        dispatcher = ToolDispatcher(runtime, "eval-voice", allow_memory=True)
        dispatcher.submit({"id": "call-1", "name": "shell_exec", "arguments": {"command": "rm -rf /"}})
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=2)
        await dispatcher.close()
        return result

    result = asyncio.run(once())
    if result != {"error": "TOOL_NOT_ALLOWED", "saved": False}:
        raise AssertionError(result)
    if reply.get("error") != "TOOL_NOT_ALLOWED" or reply["saved"] is not False:
        raise AssertionError(reply)
    rows = [row for row in runtime.assistant.audit.listing() if row["tool"] == "shell_exec"]
    if len(rows) != 2 or {row["channel"] for row in rows} != {"text", "voice"}:
        raise AssertionError(rows)
    if any(row["outcome"] != "TOOL_NOT_ALLOWED" or row["risk"] != "refused" or row["saved"] for row in rows):
        raise AssertionError(rows)
    if rows[0]["message"] != rows[1]["message"] or "Nothing was changed" not in rows[0]["message"]:
        raise AssertionError(rows)


def _run(runtime, provider, key):
    return AgentLoop(runtime, provider).run(
        system="You are a test persona.",
        context={"user_message": key},
        key=key,
        language="en",
        allow_memory=True,
    )


def _expect_audit(runtime, *, tool, risk, outcome, saved):
    rows = runtime.assistant.audit.listing()
    match = next((row for row in rows if row["tool"] == tool and row["outcome"] == outcome), None)
    if match is None or match["risk"] != risk or match["saved"] is not saved:
        raise AssertionError(rows)
