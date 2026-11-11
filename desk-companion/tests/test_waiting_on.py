"""Waiting-on is a conversation answer. A draft is not a saved task until the owner allows it."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.schemas import SettingsInput
from desk.store import DomainError
from desk.tasks import TaskAction, TaskInput
from desk.text_ai import TextAssistant, TextConfig
from desk.waiting_on import parse_waiting

from test_task_job_journey import write
from test_text_conversation_scope import owner_client, send

ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
SECRET = "ZX-ledger"


def _app(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    app.state.runtime.text_ai.config = TextConfig(provider="none")
    return app, owner_client(app)


def _say(runtime, message, key, **fields):
    return runtime.assistant.local_message(AssistantMessage(message=message, **fields), key)


@pytest.mark.parametrize(
    "text",
    [
        "What should I do next?",
        "what's next",
        "When am I free tomorrow?",
        "When am I free next week?",
        "Prep me for my next meeting",
        "Prep me for tomorrow's meeting",
        "What is on today?",
        "What is on tomorrow?",
        "What is on next week?",
        "明天的行程",
        "今天的行程",
        "我明天什么时候有空？",
        "明天的会要准备什么",
        "Track: finish the report",
        "跟进：完成报告",
        "Goal: finish the report by Friday",
        "Tomorrow 15:00-16:00 Project discussion",
        "Remember: I prefer morning meetings",
    ],
)
def test_other_conversation_phrases_are_not_waiting(text):
    assert parse_waiting(text) is None


def test_ask_record_and_a_missing_reason_parse_without_saving():
    assert parse_waiting("What am I waiting on?")["kind"] == "ask"
    assert parse_waiting("Who am I waiting for?")["kind"] == "ask"
    assert parse_waiting("我在等什么")["kind"] == "ask"
    assert parse_waiting("谁还没回我？")["kind"] == "ask"
    assert parse_waiting("I'm waiting")["kind"] == "need"
    assert parse_waiting("在等")["kind"] == "need"
    assert parse_waiting("I'm waiting on Sam for the budget")["reason"] == "Sam for the budget"
    assert parse_waiting("i'm   waiting   on   Sam.")["reason"] == "Sam"
    assert parse_waiting("在等 Sam 的预算")["reason"] == "Sam 的预算"
    assert parse_waiting("I'm waiting on " + ("n" * 501))["kind"] == "long"


def test_http_draft_waits_for_allow_and_a_repeat_does_not_create_another(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    empty = send(client, "What am I waiting on?", key="ask-empty")
    assert empty.status_code == 200
    assert empty.json()["kind"] == "waiting"
    assert "not waiting" in empty.json()["message"]
    assert runtime.tasks.listing()["tasks"] == []
    draft = send(client, "I'm waiting on Sam for the budget", key="draft-sam")
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["kind"] == "draft" and body["saved"] is False
    assert body["proposal"]["data"]["task"]["status"] == "waiting"
    assert body["proposal"]["data"]["task"]["waiting_for"] == "Sam for the budget"
    assert "Nothing is saved" in body["message"]
    assert runtime.tasks.listing()["tasks"] == []
    runtime.tick()
    assert runtime.tasks.listing()["tasks"] == []
    again = send(client, "I'm waiting on Sam for the budget", key="draft-sam")
    assert again.json()["proposal"]["id"] == body["proposal"]["id"]
    conflict = send(client, "I'm waiting on Pat for the form", key="draft-sam")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    saved = write(
        client,
        f"/api/assistant/proposals/{body['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-sam",
    )
    assert saved["saved"] is True
    tasks = runtime.tasks.listing()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["status"] == "waiting"
    assert tasks[0]["waiting_for"] == "Sam for the budget"
    write(
        client,
        f"/api/assistant/proposals/{body['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-sam-again",
    )
    assert len(runtime.tasks.listing()["tasks"]) == 1
    repeat = send(client, "i'm   waiting   on   sam for the budget", key="draft-again")
    assert repeat.json()["kind"] == "waiting"
    assert "Sam for the budget" in repeat.json()["message"]
    assert repeat.json().get("proposal") is None
    assert len(runtime.tasks.listing()["tasks"]) == 1
    listed = send(client, "What am I waiting on?", key="ask-sam")
    assert "Waiting on Sam for the budget." in listed.json()["message"]
    zh = send(client, "我在等什么", key="ask-zh", language="zh")
    assert "Sam for the budget" in zh.json()["message"]


def test_cancel_and_a_closed_task_save_nothing(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(client, "Waiting on Riley", key="draft-riley").json()
    cancelled = write(
        client,
        f"/api/assistant/proposals/{draft['proposal']['id']}/decisions",
        {"action": "cancel"},
        "cancel-riley",
    )
    assert cancelled["saved"] is False
    assert runtime.tasks.listing()["tasks"] == []
    task = runtime.tasks.create(TaskInput(title="Report"), "make-report")["task"]
    task = runtime.tasks.action(
        task["id"],
        TaskAction(action="complete", expected_version=task["version"]),
        "complete-report",
    )["task"]
    reply = _say(runtime, "I'm waiting on Riley", "closed", task_id=task["id"])
    assert reply["kind"] == "clarify"
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "completed"
    bare = _say(runtime, "I'm waiting", "bare")
    assert bare["kind"] == "clarify"
    stored = runtime.tasks.detail(task["id"])["task"]
    assert stored["status"] == "completed"
    assert len(runtime.tasks.listing(include_closed=True)["tasks"]) == 1


def test_selected_task_keeps_fields_the_sentence_did_not_mention(tmp_path):
    clock = [datetime(2026, 10, 3, 1, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: clock[0])
    app.state.runtime.text_ai.config = TextConfig(provider="none")
    runtime = app.state.runtime
    kept = runtime.tasks.create(
        TaskInput(
            title="Report",
            timezone="Asia/Hong_Kong",
            due_local="2026-10-20T15:00",
            next_step="Send charts",
            steps=[{"title": "Draft", "done": False}],
            visibility="displayable",
            follow_up_enabled=False,
            check_in_local="2026-10-10T09:00",
            interval_minutes=60,
        ),
        "make-kept",
    )["task"]
    reply = _say(runtime, "I'm waiting on the printer", "update-kept", task_id=kept["id"])
    proposed = reply["proposal"]["data"]["change"]["task"]
    assert proposed["title"] == "Report"
    assert proposed["due_local"].startswith("2026-10-20T15:00")
    assert proposed["next_step"] == "Send charts"
    assert proposed["steps"] == [{"title": "Draft", "done": False}]
    assert proposed["visibility"] == "displayable"
    assert proposed["follow_up_enabled"] is False
    assert proposed["interval_minutes"] == 60
    assert proposed["check_in_local"].startswith("2026-10-10T09:00")
    assert proposed["status"] == "waiting"
    assert proposed["waiting_for"] == "the printer"
    assert kept["status"] == "todo"
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "allow-kept")
    saved = runtime.tasks.detail(kept["id"])["task"]
    assert saved["status"] == "waiting"
    assert saved["title"] == "Report"
    assert saved["due_local"].startswith("2026-10-20T15:00")
    assert saved["next_step"] == "Send charts"
    assert saved["visibility"] == "displayable"
    assert saved["follow_up_enabled"] is False
    assert saved["steps"][0]["title"] == "Draft"
    stale = runtime.tasks.create(
        TaskInput(
            title="Old check",
            timezone="Asia/Hong_Kong",
            check_in_local="2026-10-04T09:00",
            due_local="2026-12-01T09:00",
        ),
        "make-stale",
    )["task"]
    clock[0] += timedelta(days=3)
    moved = _say(runtime, "Waiting on a part", "update-stale", task_id=stale["id"])
    assert moved["proposal"]["data"]["change"]["task"]["check_in_local"] is None
    assert moved["proposal"]["data"]["change"]["task"]["due_local"].startswith("2026-12-01T09:00")
    runtime.assistant.decide(moved["proposal"]["id"], "confirm", "allow-stale")
    updated = runtime.tasks.detail(stale["id"])["task"]
    assert updated["waiting_for"] == "a part"
    assert updated["due_local"].startswith("2026-12-01T09:00")
    assert updated["check_in_local"] is None


def test_interrupted_draft_and_confirm_are_not_success(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime

    def interrupt_draft(conn, key, payload):
        del conn, key
        if isinstance(payload, dict) and payload.get("type") == "assistant_draft":
            raise RuntimeError("interrupted draft")

    runtime.store.operation_guard = interrupt_draft
    with pytest.raises(RuntimeError, match="interrupted draft"):
        send(client, "I'm waiting on Nia", key="draft-nia")
    assert runtime.tasks.listing()["tasks"] == []
    assert runtime.assistant.proposals() == []
    runtime.store.operation_guard = None
    draft = send(client, "I'm waiting on Nia", key="draft-nia")
    assert draft.status_code == 200
    proposal_id = draft.json()["proposal"]["id"]

    def interrupt_confirm(conn, key, payload):
        del conn, key
        if isinstance(payload, dict) and payload.get("type") == "task_create":
            raise RuntimeError("interrupted confirm")

    runtime.store.operation_guard = interrupt_confirm
    with pytest.raises(RuntimeError, match="interrupted confirm"):
        write(
            client,
            f"/api/assistant/proposals/{proposal_id}/decisions",
            {"action": "confirm"},
            "allow-nia",
        )
    assert runtime.tasks.listing()["tasks"] == []
    runtime.store.operation_guard = None
    saved = write(
        client,
        f"/api/assistant/proposals/{proposal_id}/decisions",
        {"action": "confirm"},
        "allow-nia",
    )
    assert saved["saved"] is True
    assert len(runtime.tasks.listing()["tasks"]) == 1
    write(
        client,
        f"/api/assistant/proposals/{proposal_id}/decisions",
        {"action": "confirm"},
        "allow-nia-retry",
    )
    assert len(runtime.tasks.listing()["tasks"]) == 1


def test_older_phrases_still_reach_their_own_parsers(tmp_path):
    app, _client = _app(tmp_path)
    runtime = app.state.runtime
    today = _say(runtime, "What is on today?", "today")
    assert today["kind"] == "brief"
    tracked = _say(runtime, "Track: finish the report", "track")
    assert tracked["proposal"]["kind"] == "task_create"
    assert tracked["proposal"]["data"]["task"]["status"] == "todo"
    goal = _say(runtime, "Goal: finish the report by Friday", "goal")
    assert goal["proposal"]["data"].get("goal") is True
    free = _say(runtime, "When am I free tomorrow?", "free")
    assert free["kind"] == "open_time"
    meeting = _say(runtime, "Prep me for my next meeting", "meeting")
    assert meeting["kind"] == "meeting_prep"
    nxt = _say(runtime, "What should I do next?", "next")
    assert nxt["kind"] == "next_step"
    remembered = _say(runtime, "Remember: I prefer morning meetings", "remember")
    assert remembered["proposal"]["kind"] == "memory_save"
    assert runtime.tasks.listing()["tasks"] == []


def test_a_display_sees_a_count_and_cannot_save_or_read_the_reason(tmp_path):
    app, owner = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(owner, f"I'm waiting on {SECRET}", key="draft-secret").json()
    write(
        owner,
        f"/api/assistant/proposals/{draft['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-secret",
    )
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    asked = display.post(
        "/api/assistant/messages",
        json={"message": "What am I waiting on?", "language": "en"},
        headers={"X-Operation-Id": "display-ask"},
    )
    assert asked.status_code == 200
    assert SECRET not in asked.text
    assert "1 item" in asked.json()["message"]
    refused = display.post(
        "/api/assistant/messages",
        json={"message": "I'm waiting on Pat", "language": "en"},
        headers={"X-Operation-Id": "display-write"},
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"
    assert "Pat" not in refused.text
    reasons = {task["waiting_for"] for task in runtime.tasks.listing()["tasks"]}
    assert reasons == {SECRET}
    stranger = TestClient(app)
    stranger.headers.update({"X-Desk-Request": "1"})
    denied = stranger.post(
        "/api/assistant/messages",
        json={"message": "I'm waiting on Pat"},
        headers={"X-Operation-Id": "stranger"},
    )
    assert denied.status_code == 401
    assert "Pat" not in {task["waiting_for"] for task in runtime.tasks.listing()["tasks"]}


def test_hidden_private_tasks_are_not_named(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(client, f"I'm waiting on {SECRET}", key="hide-draft").json()
    write(
        client,
        f"/api/assistant/proposals/{draft['proposal']['id']}/decisions",
        {"action": "confirm"},
        "hide-allow",
    )
    runtime.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide",
    )
    asked = send(client, "What am I waiting on?", key="hide-ask")
    assert SECRET not in asked.text
    assert "hidden" in asked.json()["message"]
    again = send(client, f"I'm waiting on {SECRET}", key="hide-again")
    assert again.json()["kind"] == "waiting"
    assert SECRET not in again.text
    assert len(runtime.tasks.listing(include_closed=True)["tasks"]) == 1


def test_full_access_saves_one_task_and_a_repeat_does_not_save_another(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    write(client, "/api/permissions", {"mode": "full", "expected_version": 1}, "full")
    first = send(client, "I'm waiting on Ada for the form", key="full-ada")
    assert first.status_code == 200, first.text
    assert first.json()["saved"] is True
    tasks = runtime.tasks.listing()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["waiting_for"] == "Ada for the form"
    assert tasks[0]["status"] == "waiting"
    second = send(client, "I'm waiting on Ada for the form", key="full-ada-again")
    assert second.json()["kind"] == "waiting"
    assert len(runtime.tasks.listing()["tasks"]) == 1


def test_a_configured_provider_answers_locally_and_does_not_call_the_model(tmp_path):
    app, _client = _app(tmp_path)
    runtime = app.state.runtime
    calls = []

    def response(request):
        calls.append(request.content)
        return httpx.Response(500)

    service = TextAssistant(
        runtime,
        TextConfig(
            provider="qwen",
            model="test-model",
            api_key="fixture-key",
            endpoint=ENDPOINT,
            extract_cap=1,
        ),
        httpx.MockTransport(response),
    )
    principal = {"kind": "owner", "session": "fixture"}
    reply = service.message(
        AssistantMessage(message="What am I waiting on?"),
        "provider-ask",
        principal=principal,
    )
    recorded = service.message(
        AssistantMessage(message="I'm waiting on Sam for the budget"),
        "provider-record",
        principal=principal,
    )
    assert calls == []
    assert reply["kind"] == "waiting"
    assert recorded["kind"] == "draft" and recorded["saved"] is False
    assert runtime.tasks.listing()["tasks"] == []
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        service.message(
            AssistantMessage(message="I'm waiting on someone else"),
            "provider-record",
            principal=principal,
        )


def test_files_on_the_message_are_not_treated_as_waiting(tmp_path):
    app, _client = _app(tmp_path)
    runtime = app.state.runtime

    class Filed:
        attachment_ids = ["a" * 32]

    reply = runtime.assistant.local_message(
        AssistantMessage(message="What am I waiting on?"),
        "files",
        conversation=Filed(),
    )
    assert reply["kind"] != "waiting"
