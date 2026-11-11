"""A reply the owner owes is a conversation answer. Nothing is saved until they allow it."""

import json
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
from desk.reply_owed import parse_reply_owed

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


def _events(body: str):
    events = []
    for block in body.split("\n\n"):
        data = "".join(
            line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
        )
        if data:
            events.append(json.loads(data))
    return events


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
        "What am I waiting on?",
        "Who am I waiting for?",
        "I'm waiting on Sam for the budget",
        "我在等什么",
        "谁还没回我？",
        "Track: finish the report",
        "跟进：完成报告",
        "Goal: finish the report by Friday",
        "我要回复 Sam，关于场地",
        "Tomorrow 15:00-16:00 Project discussion",
        "Remember: I prefer morning meetings",
        "Save note: project ideas",
    ],
)
def test_other_conversation_phrases_are_not_a_reply_owed(text):
    assert parse_reply_owed(text) is None


def test_ask_record_and_a_missing_person_parse_without_saving():
    assert parse_reply_owed("Who do I need to reply to?")["kind"] == "ask"
    assert parse_reply_owed("What replies do I owe?")["kind"] == "ask"
    assert parse_reply_owed("我该回复谁")["kind"] == "ask"
    assert parse_reply_owed("还有谁等我回复？")["kind"] == "ask"
    assert parse_reply_owed("I need to reply")["kind"] == "need"
    assert parse_reply_owed("回复")["kind"] == "need"
    recorded = parse_reply_owed("I need to reply to Sam about the venue.")
    assert recorded["who"] == "Sam" and recorded["topic"] == "the venue"
    assert parse_reply_owed("i owe   Sam   a reply")["who"] == "Sam"
    assert parse_reply_owed("Reply to Sam.")["topic"] == ""
    assert parse_reply_owed("我该回复 Sam，关于场地")["topic"] == "场地"
    assert parse_reply_owed("回复 Sam 关于场地")["who"] == "Sam"
    assert parse_reply_owed("I need to reply to " + ("n" * 81))["kind"] == "long"


def test_http_draft_waits_for_allow_and_a_repeat_does_not_create_another(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    empty = send(client, "Who do I need to reply to?", key="ask-empty")
    assert empty.status_code == 200
    assert empty.json()["kind"] == "reply_owed"
    assert "do not owe" in empty.json()["message"]
    assert runtime.tasks.listing()["tasks"] == []
    draft = send(client, "I need to reply to Sam about the venue", key="draft-sam")
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["kind"] == "reply_owed" and body["saved"] is False
    assert body["proposal"]["data"]["task"]["status"] == "todo"
    assert body["proposal"]["data"]["task"]["title"] == "Reply to Sam about the venue"
    assert body["proposal"]["data"]["task"]["waiting_for"] == ""
    assert body["proposal"]["data"]["task"]["due_local"] is None
    assert "Nothing is saved" in body["message"]
    assert runtime.tasks.listing()["tasks"] == []
    runtime.tick()
    assert runtime.tasks.listing()["tasks"] == []
    again = send(client, "I need to reply to Sam about the venue", key="draft-sam")
    assert again.json()["proposal"]["id"] == body["proposal"]["id"]
    conflict = send(client, "I need to reply to Pat about the form", key="draft-sam")
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
    assert tasks[0]["status"] == "todo"
    assert tasks[0]["title"] == "Reply to Sam about the venue"
    assert tasks[0]["waiting_for"] == ""
    write(
        client,
        f"/api/assistant/proposals/{body['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-sam-again",
    )
    assert len(runtime.tasks.listing()["tasks"]) == 1
    repeat = send(client, "i need to   reply to   sam about the venue", key="draft-again")
    assert repeat.json()["kind"] == "reply_owed"
    assert "Sam" in repeat.json()["message"]
    assert "venue" in repeat.json()["message"]
    assert repeat.json().get("proposal") is None
    assert len(runtime.tasks.listing()["tasks"]) == 1
    listed = send(client, "Who do I need to reply to?", key="ask-sam")
    assert "Reply to Sam about the venue." in listed.json()["message"]
    omitted = send(client, "I need to reply to Sam", key="omit-topic")
    assert omitted.json().get("proposal") is None
    assert "venue" in omitted.json()["message"]
    assert len(runtime.tasks.listing()["tasks"]) == 1
    zh = send(client, "我该回复谁", key="ask-zh", language="zh")
    assert "Sam" in zh.json()["message"]
    assert "the venue" in zh.json()["message"]


def test_a_different_topic_is_another_reply_and_a_blank_topic_can_be_filled(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    first = send(client, "Reply to Sam", key="sam-plain").json()
    write(
        client,
        f"/api/assistant/proposals/{first['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-plain",
    )
    filled = send(client, "I need to reply to Sam about the venue", key="sam-venue")
    assert filled.json()["saved"] is False
    proposed = filled.json()["proposal"]["data"]["change"]["task"]
    assert proposed["title"] == "Reply to Sam about the venue"
    assert proposed["status"] == "todo"
    assert proposed["waiting_for"] == ""
    write(
        client,
        f"/api/assistant/proposals/{filled.json()['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-venue",
    )
    assert len(runtime.tasks.listing()["tasks"]) == 1
    other = send(client, "I owe Pat a reply about the form", key="pat")
    write(
        client,
        f"/api/assistant/proposals/{other.json()['proposal']['id']}/decisions",
        {"action": "confirm"},
        "allow-pat",
    )
    titles = {task["title"] for task in runtime.tasks.listing()["tasks"]}
    assert titles == {"Reply to Sam about the venue", "Reply to Pat about the form"}
    listed = send(client, "What replies do I owe?", key="ask-both")
    assert "Sam" in listed.json()["message"] and "Pat" in listed.json()["message"]


def test_adding_a_topic_keeps_the_due_date_and_a_chinese_sentence_names_both(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    saved = runtime.tasks.create(
        TaskInput(
            title="Reply to Sam",
            timezone="Asia/Hong_Kong",
            due_local="2026-12-01T09:00",
            next_step="Bring the map",
            visibility="displayable",
        ),
        "sam-blank",
    )["task"]
    filled = send(client, "I need to reply to Sam about the venue", key="fill-due")
    proposed = filled.json()["proposal"]["data"]["change"]["task"]
    assert proposed["title"] == "Reply to Sam about the venue"
    assert proposed["due_local"].startswith("2026-12-01T09:00")
    assert proposed["next_step"] == "Bring the map"
    assert proposed["visibility"] == "displayable"
    assert proposed["waiting_for"] == ""
    assert saved["title"] == "Reply to Sam"
    chinese = send(client, "我该回复 小明，关于场地", key="zh-ming", language="zh")
    assert chinese.status_code == 200, chinese.text
    assert chinese.json()["saved"] is False
    assert chinese.json()["proposal"]["data"]["task"]["title"] == "Reply to 小明 about 场地"
    assert "允许之后才会保存" in chinese.json()["message"]
    tasks = runtime.tasks.listing()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["id"] == saved["id"]
    assert tasks[0]["title"] == "Reply to Sam"
    assert tasks[0]["due_local"].startswith("2026-12-01T09:00")


def test_cancel_and_a_closed_task_save_nothing(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(client, "Reply to Riley", key="draft-riley").json()
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
    reply = _say(runtime, "I need to reply to Riley", "closed", task_id=task["id"])
    assert reply["kind"] == "clarify"
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "completed"
    bare = _say(runtime, "I need to reply", "bare")
    assert bare["kind"] == "clarify"
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
    reply = _say(
        runtime, "I need to reply to Sam about the venue", "update-kept", task_id=kept["id"]
    )
    proposed = reply["proposal"]["data"]["change"]["task"]
    assert proposed["title"] == "Report"
    assert proposed["due_local"].startswith("2026-10-20T15:00")
    assert proposed["next_step"] == "Send charts"
    assert proposed["steps"][0] == {"title": "Draft", "done": False}
    assert proposed["steps"][1]["title"] == "Reply to Sam about the venue"
    assert proposed["visibility"] == "displayable"
    assert proposed["follow_up_enabled"] is False
    assert proposed["interval_minutes"] == 60
    assert proposed["check_in_local"].startswith("2026-10-10T09:00")
    assert proposed["status"] == "todo"
    assert proposed["waiting_for"] == ""
    assert kept["status"] == "todo"
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "allow-kept")
    saved = runtime.tasks.detail(kept["id"])["task"]
    assert saved["title"] == "Report"
    assert saved["due_local"].startswith("2026-10-20T15:00")
    assert saved["next_step"] == "Send charts"
    assert saved["status"] == "todo"
    assert saved["waiting_for"] == ""
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
    moved = _say(runtime, "Reply to Nia about the menu", "update-stale", task_id=stale["id"])
    assert moved["proposal"]["data"]["change"]["task"]["check_in_local"] is None
    assert moved["proposal"]["data"]["change"]["task"]["due_local"].startswith("2026-12-01T09:00")
    assert moved["proposal"]["data"]["change"]["task"]["title"] == "Old check"
    runtime.assistant.decide(moved["proposal"]["id"], "confirm", "allow-stale")
    updated = runtime.tasks.detail(stale["id"])["task"]
    assert updated["due_local"].startswith("2026-12-01T09:00")
    assert updated["check_in_local"] is None
    assert any(step["title"] == "Reply to Nia about the menu" for step in updated["steps"])


def test_waiting_on_someone_is_not_listed_as_a_reply(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    runtime.tasks.create(
        TaskInput(title="Sam for the budget", status="waiting", waiting_for="Sam for the budget"),
        "waiting-sam",
    )
    asked = send(client, "Who do I need to reply to?", key="ask-waiting")
    assert "do not owe" in asked.json()["message"]
    assert "Sam" not in asked.json()["message"]
    assert len(runtime.tasks.listing()["tasks"]) == 1
    assert runtime.tasks.listing()["tasks"][0]["status"] == "waiting"


def test_interrupted_draft_and_confirm_are_not_success(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime

    def interrupt_draft(conn, key, payload):
        del conn, key
        if isinstance(payload, dict) and payload.get("type") == "assistant_draft":
            raise RuntimeError("interrupted draft")

    runtime.store.operation_guard = interrupt_draft
    with pytest.raises(RuntimeError, match="interrupted draft"):
        send(client, "I need to reply to Nia", key="draft-nia")
    assert runtime.tasks.listing()["tasks"] == []
    assert runtime.assistant.proposals() == []
    runtime.store.operation_guard = None
    draft = send(client, "I need to reply to Nia", key="draft-nia")
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
    assert tracked["proposal"]["data"]["task"]["title"] == "finish the report"
    goal = _say(runtime, "Goal: finish the report by Friday", "goal")
    assert goal["proposal"]["data"].get("goal") is True
    free = _say(runtime, "When am I free tomorrow?", "free")
    assert free["kind"] == "brief"
    meeting = _say(runtime, "Prep me for my next meeting", "meeting")
    assert meeting["kind"] == "clarify"
    nxt = _say(runtime, "What should I do next?", "next")
    assert nxt["kind"] == "clarify"
    waiting = _say(runtime, "What am I waiting on?", "waiting")
    assert waiting["kind"] == "clarify"
    stated = _say(runtime, "我要回复 Sam，关于场地", "goal-reply")
    assert stated["proposal"]["data"].get("goal") is True
    assert stated["proposal"]["data"]["task"]["title"] == "回复 Sam，关于场地"
    remembered = _say(runtime, "Remember: I prefer morning meetings", "remember")
    assert remembered["proposal"]["kind"] == "memory_save"
    assert runtime.tasks.listing()["tasks"] == []


def test_a_display_sees_a_count_and_cannot_save_or_read_the_name(tmp_path):
    app, owner = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(owner, f"I need to reply to {SECRET} about the venue", key="draft-secret").json()
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
        json={"message": "Who do I need to reply to?", "language": "en"},
        headers={"X-Operation-Id": "display-ask"},
    )
    assert asked.status_code == 200
    assert SECRET not in asked.text
    assert "1 reply is owed" in asked.json()["message"]
    refused = display.post(
        "/api/assistant/messages",
        json={"message": "I need to reply to Pat", "language": "en"},
        headers={"X-Operation-Id": "display-write"},
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"
    assert "Pat" not in refused.text
    titles = {task["title"] for task in runtime.tasks.listing()["tasks"]}
    assert titles == {f"Reply to {SECRET} about the venue"}
    stranger = TestClient(app)
    stranger.headers.update({"X-Desk-Request": "1"})
    denied = stranger.post(
        "/api/assistant/messages",
        json={"message": "I need to reply to Pat"},
        headers={"X-Operation-Id": "stranger"},
    )
    assert denied.status_code == 401
    assert "Pat" not in {task["title"] for task in runtime.tasks.listing()["tasks"]}


def test_hidden_private_tasks_are_not_named(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    draft = send(client, f"Reply to {SECRET}", key="hide-draft").json()
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
    asked = send(client, "Who do I need to reply to?", key="hide-ask")
    assert SECRET not in asked.text
    assert "hidden" in asked.json()["message"]
    again = send(client, f"Reply to {SECRET}", key="hide-again")
    assert again.json()["kind"] == "reply_owed"
    assert SECRET not in again.text
    assert again.json().get("proposal") is None
    assert len(runtime.tasks.listing(include_closed=True)["tasks"]) == 1


def test_full_access_saves_one_task_and_a_repeat_does_not_save_another(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    write(client, "/api/permissions", {"mode": "full", "expected_version": 1}, "full")
    first = send(client, "I need to reply to Ada about the form", key="full-ada")
    assert first.status_code == 200, first.text
    assert first.json()["saved"] is True
    tasks = runtime.tasks.listing()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Reply to Ada about the form"
    assert tasks[0]["status"] == "todo"
    second = send(client, "I need to reply to Ada about the form", key="full-ada-again")
    assert second.json()["kind"] == "reply_owed"
    assert second.json().get("proposal") is None
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
        AssistantMessage(message="Who do I need to reply to?"),
        "provider-ask",
        principal=principal,
    )
    recorded = service.message(
        AssistantMessage(message="I need to reply to Sam about the venue"),
        "provider-record",
        principal=principal,
    )
    assert calls == []
    assert reply["kind"] == "reply_owed"
    assert recorded["kind"] == "reply_owed" and recorded["saved"] is False
    assert runtime.tasks.listing()["tasks"] == []
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        service.message(
            AssistantMessage(message="I need to reply to someone else"),
            "provider-record",
            principal=principal,
        )


def test_files_on_the_message_are_not_treated_as_a_reply(tmp_path):
    app, _client = _app(tmp_path)
    runtime = app.state.runtime

    class Filed:
        attachment_ids = ["a" * 32]

    reply = runtime.assistant.local_message(
        AssistantMessage(message="Who do I need to reply to?"),
        "files",
        conversation=Filed(),
    )
    assert reply["kind"] != "reply_owed"
    assert runtime.tasks.listing()["tasks"] == []
    recorded = runtime.assistant.local_message(
        AssistantMessage(message="I need to reply to Sam about the venue"),
        "files-record",
        conversation=Filed(),
    )
    assert recorded.get("proposal") is None
    assert runtime.tasks.listing()["tasks"] == []


def test_the_stream_the_page_uses_answers_without_saving(tmp_path):
    app, client = _app(tmp_path)
    with client.stream(
        "POST",
        "/api/assistant/messages/stream",
        json={"message": "Who do I need to reply to?", "language": "en"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "stream-ask"},
    ) as response:
        assert response.status_code == 200
        events = _events(response.read().decode())
    done = [event for event in events if event.get("type") == "done"]
    assert done[-1]["reply"]["kind"] == "reply_owed"
    assert "do not owe" in done[-1]["reply"]["message"]
    assert app.state.runtime.tasks.listing()["tasks"] == []
