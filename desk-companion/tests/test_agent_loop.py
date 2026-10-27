"""Agent loop, tool registry, audit, cap, and offline scenarios."""

import asyncio
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.agent_eval import run_all
from desk.agent_loop import AgentLoop
from desk.app import create_app
from desk.assistant import TOOLS, AssistantMessage
from desk.capabilities import CAPABILITIES, parse_call
from desk.model_provider import ModelStep, ScriptedProvider
from desk.runtime import Runtime
from desk.store import DomainError, Store
from desk.text_ai import TextAssistant, TextConfig
from desk.tool_dispatch import ToolDispatcher


def _runtime(tmp_path):
    folder = tmp_path / uuid4().hex
    return Runtime(
        Store(folder, password="fixture-only", clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))
    )


def _run(runtime, provider, key="turn", language="en"):
    return AgentLoop(runtime, provider).run(
        system="persona",
        context={"user_message": key},
        key=key,
        language=language,
        allow_memory=True,
    )


def test_registry_matches_the_voice_tool_list_and_rejects_unknown_calls():
    assert {tool["name"] for tool in TOOLS} == set(CAPABILITIES)
    with pytest.raises(DomainError, match="TOOL_NOT_ALLOWED"):
        parse_call("shell_exec", {"command": "ls"})
    with pytest.raises(DomainError, match="TOOL_ARGUMENTS_INVALID"):
        parse_call("memory_query", {"body": "extra"})
    capability, arguments = parse_call("memory_save_draft", {"body": "A fact"})
    assert capability.risk == "draft" and arguments == {"body": "A fact"}


def test_offline_scenarios_cover_remind_recall_refusal_and_provider_retry(tmp_path):
    results = run_all(lambda: _runtime(tmp_path))
    failed = [result for result in results if not result.passed]
    assert not failed and len(results) == 4


def test_read_failure_is_returned_to_the_model_and_a_bad_draft_is_not_retried(tmp_path):
    runtime = _runtime(tmp_path)
    lookup = ScriptedProvider(
        [
            ModelStep("Checking.", "task_details", {"task_id": "missing"}),
            ModelStep("I could not find that task.", "none", {}),
        ]
    )
    reply = _run(runtime, lookup, "lookup")
    assert lookup.calls == 2 and reply["message"] == "I could not find that task."
    assert lookup.contexts[1]["last_tool_result"]["result"]["error"] == "TASK_NOT_FOUND"
    assert runtime.assistant.audit.listing()[0]["outcome"] == "TASK_NOT_FOUND"

    draft = ScriptedProvider(
        [
            ModelStep("Saving.", "calendar_create_draft", {"event": {"title": ""}}),
            ModelStep("Trying again.", "calendar_create_draft", {"event": {"title": "Later"}}),
        ]
    )
    refused = _run(runtime, draft, "bad-draft")
    assert draft.calls == 1 and refused["kind"] == "clarify" and refused["saved"] is False
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_note_draft_stays_in_review_and_the_loop_stops_after_three_reads(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    runtime = _runtime(tmp_path)
    provider = ScriptedProvider(
        [ModelStep("Review this note.", "computer_job_draft", {"title": "Note", "content": "Hello"})]
    )
    reply = _run(runtime, provider, "note")
    assert reply["kind"] == "job" and reply["saved"] is False and reply["job"]["state"] == "review"
    assert provider.calls == 1
    assert list(runtime.store.directory.glob("computer-notes/*.txt")) == []

    repeated = ScriptedProvider([ModelStep("Checking.", "memory_query", {})] * 3)
    exhausted = AgentLoop(runtime, repeated, max_steps=3).run(
        system="persona",
        context={},
        key="reads",
        language="zh",
        allow_memory=True,
    )
    assert repeated.calls == 3
    assert exhausted["kind"] == "clarify" and "跟进" in exhausted["message"]


def test_time_limit_does_not_start_another_tool(tmp_path):
    runtime = _runtime(tmp_path)
    ticks = iter([0, 0, 0, 100])
    provider = ScriptedProvider(
        [
            ModelStep("Checking.", "memory_query", {}),
            ModelStep("Again.", "memory_query", {}),
        ]
    )
    reply = AgentLoop(runtime, provider, max_seconds=10, clock=lambda: next(ticks)).run(
        system="persona",
        context={},
        key="time",
        language="en",
        allow_memory=True,
    )
    assert provider.calls == 1 and reply["kind"] == "clarify" and "time limit" in reply["message"]
    assert len(runtime.assistant.audit.listing()) == 1


def test_daily_cap_stops_before_another_hosted_call(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_TEXT_DAILY_CAP", "1")
    runtime = _runtime(tmp_path)
    calls = []

    def response(request):
        calls.append(json.loads(request.content))
        plan = {"message": "Ready.", "tool": "none", "arguments": {}}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(plan)}}]})

    service = TextAssistant(
        runtime,
        TextConfig(
            provider="qwen",
            model="qwen-test",
            endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            api_key="fixture-key",
        ),
        httpx.MockTransport(response),
    )
    payload = AssistantMessage(message="Hello")
    assert service.message(payload, "one")["kind"] == "reply"
    capped = service.message(payload, "two")
    assert capped["kind"] == "clarify" and capped["saved"] is False and "daily limit" in capped["message"]
    assert len(calls) == 1
    assert service.message(payload, "two") == capped


def test_local_and_voice_calls_are_audited_for_the_owner_only(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    runtime = app.state.runtime
    reply = runtime.assistant.local_message(
        AssistantMessage(message="Remember: the code is lantern", language="en"),
        "remember",
    )
    assert reply["saved"] is False and runtime.memory.for_model() == []
    local = runtime.assistant.audit.listing()[0]
    assert local["channel"] == "local" and local["tool"] == "memory_save_draft"
    assert local["risk"] == "draft" and local["saved"] is False
    assert local["arguments"]["body"] == "the code is lantern"

    async def voice():
        dispatcher = ToolDispatcher(runtime, "owner-session", allow_memory=True)
        dispatcher.submit({"id": "mem", "name": "memory_query", "arguments": {}})
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=2)
        assert result["memories"] == []
        await dispatcher.close()

    asyncio.run(voice())
    voice_row = next(row for row in runtime.assistant.audit.listing() if row["channel"] == "voice")
    assert voice_row["tool"] == "memory_query" and voice_row["outcome"] == "ok"

    owner = TestClient(app)
    owner.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    listed = owner.get("/api/assistant/tool-calls", headers={"X-Desk-Request": "1"})
    assert listed.status_code == 200
    assert any(row["tool"] == "memory_save_draft" for row in listed.json()["calls"])
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-audit"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    hidden = display.get("/api/assistant/tool-calls")
    assert hidden.status_code == 403
    assert hidden.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"
    assert "lantern" not in hidden.text


def test_malformed_hosted_output_is_retried_then_rejected(tmp_path):
    runtime = _runtime(tmp_path)
    calls = []

    def response(request):
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"message": "Done", "tool": "confirm", "arguments": {}}
                            )
                        }
                    }
                ]
            },
        )

    service = TextAssistant(
        runtime,
        TextConfig(
            "qwen",
            "test-model",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "fixture",
        ),
        httpx.MockTransport(response),
    )
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        service.message(AssistantMessage(message="Create"), "invalid")
    assert len(calls) == 3 and not runtime.tasks.listing()["tasks"]
    assert os.environ.get("DESK_TEXT_PROVIDER", "none") == "none"
