"""Asking Alice what to do next reads local records and does not do the step."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.next_step import asks_next_step
from desk.schemas import SettingsInput
from desk.store import DomainError
from desk.tasks import TaskAction, TaskInput
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences


def test_only_the_whole_question_is_a_next_step():
    assert asks_next_step("What should I do next?")
    assert asks_next_step("接下来做什么？")
    assert asks_next_step("Please what's my next step.")
    assert not asks_next_step("What is on today?")
    assert not asks_next_step("What is next week?")
    assert not asks_next_step("What should I do tomorrow at 15:00?")
    assert not asks_next_step("Track: finish the report")


def _app(tmp_path, clock):
    app = create_app(tmp_path, clock=lambda: clock[0], password="next-step-fixture", scheduler=False)
    app.state.runtime.text_ai.config.provider = "none"
    app.state.runtime.text_ai.config.api_key = ""
    return app


def _client(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "next-step-fixture"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return client


def _send(client, message, *, key=None, **extra):
    return client.post(
        "/api/assistant/messages",
        json={"message": message, **extra},
        headers={"X-Desk-Request": "1", "X-Operation-Id": key or uuid4().hex},
    )


def _task(runtime, **fields):
    created = runtime.tasks.create(TaskInput(**fields), uuid4().hex)
    return created["task"]


def _proposals(runtime) -> int:
    with runtime.store.connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0]


def test_selected_task_is_spoken_and_not_performed(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    task = _task(runtime, title="Print the handout", next_step="check the room")
    version = task["version"]
    before = _proposals(runtime)
    client = _client(app)
    body = {"message": "What should I do next?"}
    first = _send(client, body["message"], key="same-step", task_id=task["id"])
    assert first.status_code == 200, first.text
    reply = first.json()
    assert reply["kind"] == "next_step" and reply["acted"] is False and reply["saved"] is False
    assert "check the room" in reply["message"] and "have not done it" in reply["message"]
    assert reply["next_step"]["source"] == "task"
    assert reply["next_step"]["target_id"] == task["id"]
    again = _send(client, body["message"], key="same-step", task_id=task["id"])
    assert again.status_code == 200
    assert again.json()["message"] == reply["message"]
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "todo"
    assert _proposals(runtime) == before
    conflict = _send(client, "What is on today?", key="same-step", task_id=task["id"])
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"


def test_omitted_fields_use_the_soonest_event_and_a_new_question_rereads(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    task = _task(runtime, title="Print the handout", next_step="check the room")
    client = _client(app)
    created = client.post(
        "/api/events",
        json={
            "event": {
                "title": "Project discussion",
                "start_local": "2026-11-11T11:00",
                "end_local": "2026-11-11T12:00",
                "timezone": "Asia/Hong_Kong",
                "all_day": False,
                "calendar": "study",
                "color": "lavender",
                "visibility": "private",
                "busy": True,
                "location": "",
                "notes": "",
                "recurrence": {"frequency": "none", "interval": 1, "until": None},
                "reminder_minutes": [],
            },
            "additional_dates": [],
        },
        headers={"X-Desk-Request": "1", "X-Operation-Id": "event-1"},
    )
    assert created.status_code == 200, created.text
    # language, task_id and conversation_id are omitted on purpose.
    day = _send(client, "What should I do next?", key="day-step")
    assert day.status_code == 200, day.text
    reply = day.json()
    assert reply["next_step"]["source"] == "calendar"
    assert "Project discussion" in reply["message"] and "11:00" in reply["message"]
    assert "check the room" not in reply["message"]
    assert "have not changed the calendar" in reply["message"]
    selected = _send(client, "接下来做什么？", key="task-step", language="zh", task_id=task["id"])
    assert selected.status_code == 200, selected.text
    assert "check the room" in selected.json()["message"]
    assert "我还没有去做" in selected.json()["message"]
    runtime.tasks.action(
        task["id"],
        TaskAction(
            action="update",
            expected_version=task["version"],
            task=TaskInput(title="Print the handout", next_step="print the slides"),
        ),
        "revise-step",
    )
    stale = _send(client, "接下来做什么？", key="task-step", language="zh", task_id=task["id"])
    assert "check the room" in stale.json()["message"]
    assert "print the slides" not in stale.json()["message"]
    fresh = _send(client, "What should I do next?", key="fresh-step", task_id=task["id"])
    assert "print the slides" in fresh.json()["message"]
    other = _client(app)
    stolen = _send(other, "What is on today?", key="day-step")
    assert stolen.status_code == 409
    replay = _send(other, "What should I do next?", key="day-step")
    assert replay.status_code == 200
    assert replay.json()["message"] == reply["message"]
    assert replay.json()["acted"] is False


def test_quiet_hours_and_proactivity_off_still_answer_the_question(tmp_path):
    clock = [datetime(2026, 11, 11, 15, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    _task(runtime, title="Print the handout", next_step="check the room")
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(
                proactivity="off",
                verbosity="brief",
                tone="warm",
                quiet_enabled=True,
                quiet_start="00:00",
                quiet_end="00:00",
            ),
        ),
        "style-off",
    )
    assert runtime.moments.view()["suggestion"] is None
    reply = _send(_client(app), "What should I do next?", key="asked").json()
    assert "check the room" in reply["message"]
    assert "have not done it" in reply["message"]
    assert reply["message"].startswith("Sure — ")


def test_interruption_before_the_reply_is_not_success(tmp_path, monkeypatch):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    task = _task(runtime, title="Print the handout", next_step="check the room")
    version = task["version"]
    original = runtime.assistant.next_step_turn
    calls = {"n": 0}

    def interrupt(request, *, owner=True):
        calls["n"] += 1
        if calls["n"] == 1:
            raise DomainError("NEXT_STEP_INTERRUPTED", 503)
        return original(request, owner=owner)

    monkeypatch.setattr(runtime.assistant, "next_step_turn", interrupt)
    client = _client(app)
    failed = _send(client, "What should I do next?", key="recover-step", task_id=task["id"])
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "NEXT_STEP_INTERRUPTED"
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    assert _proposals(runtime) == 0
    recovered = _send(client, "What should I do next?", key="recover-step", task_id=task["id"])
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["acted"] is False
    assert "check the room" in recovered.json()["message"]
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "todo"
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version


def test_a_configured_provider_is_not_called(tmp_path, monkeypatch):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    _task(runtime, title="Print the handout", next_step="check the room")
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(*_args, **_kwargs):
        raise AssertionError("provider called")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    monkeypatch.setattr(runtime.text_ai, "generate_live", generate)
    reply = _send(_client(app), "What's next?", key="offline-step")
    assert reply.status_code == 200, reply.text
    assert reply.json()["kind"] == "next_step"
    assert "check the room" in reply.json()["message"]


def test_stream_and_calendar_question_stay_on_their_own_paths(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    _task(runtime, title="Print the handout", next_step="check the room")
    client = _client(app)
    stream = client.post(
        "/api/assistant/messages/stream",
        json={"message": "What should I do next?"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "stream-step"},
    )
    assert stream.status_code == 200, stream.text
    events = []
    for block in stream.text.split("\n\n"):
        data = "".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        if data:
            events.append(json.loads(data))
    done = [event for event in events if event.get("type") == "done"]
    assert done and done[-1]["reply"]["kind"] == "next_step"
    assert done[-1]["reply"]["acted"] is False
    assert "check the room" in done[-1]["reply"]["message"]
    today = _send(client, "What is on today?", key="today")
    assert today.status_code == 200, today.text
    assert today.json()["kind"] == "brief"
    assert "check the room" not in today.json()["message"]


def test_waiting_goal_and_empty_day_do_not_invent_work(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    empty = _send(client, "What should I do next?", key="empty-step").json()
    assert empty["next_step"]["source"] == "none"
    assert "have not created one" in empty["message"]
    assert runtime.tasks.listing()["tasks"] == []
    waiting = _task(
        runtime,
        title="Lab delivery",
        status="waiting",
        waiting_for="the supplier",
    )
    held = _send(client, "What should I do next?", key="waiting-step").json()
    assert held["next_step"]["source"] == "waiting"
    assert "the supplier" in held["message"] and "have not changed it" in held["message"]
    runtime.tasks.action(
        waiting["id"],
        TaskAction(
            action="cancel",
            expected_version=waiting["version"],
            note="Dropped the delivery.",
        ),
        "cancel-wait",
    )
    goal_task = _task(runtime, title="Finish the report")
    runtime.goals.record(goal_task["id"], "Finish the report", "2026-11-12T02:00:00+00:00")
    goal = _send(client, "What should I do next?", key="goal-step").json()
    assert goal["next_step"]["source"] == "goal"
    assert "Finish the report" in goal["message"] and "2026-11-12" in goal["message"]
    assert "have not closed it" in goal["message"]


def test_private_steps_stay_off_a_paired_screen_and_a_hidden_owner_display(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    secret = _task(runtime, title="Secret errand", next_step="call the lab")
    board = _task(
        runtime,
        title="Lobby board",
        next_step="post the notice",
        visibility="displayable",
    )
    version = secret["version"]
    try:
        runtime.text_ai.message(
            AssistantMessage(message="What should I do next?", task_id=secret["id"]),
            "paired-step",
            allow_memory=False,
            principal={"kind": "paired", "id": "lobby", "session": "paired-session"},
        )
    except DomainError as error:
        assert error.code == "TASK_CONTEXT_NOT_ALLOWED" and error.status == 403
    else:
        raise AssertionError("a paired screen selected a private task")
    assert runtime.tasks.detail(secret["id"])["task"]["version"] == version
    hidden_direct = runtime.assistant.local_message(
        AssistantMessage(message="What should I do next?", task_id=secret["id"]),
        "owner-hidden-direct",
        owner=False,
    )
    assert hidden_direct["next_step"]["redacted"] is True
    assert "call the lab" not in hidden_direct["message"]
    visible = runtime.text_ai.message(
        AssistantMessage(message="What should I do next?"),
        "paired-day",
        allow_memory=False,
        principal={"kind": "paired", "id": "lobby", "session": "paired-session"},
    )
    assert visible["next_step"]["source"] == "task"
    assert visible["next_step"]["target_id"] == board["id"]
    assert "post the notice" in visible["message"]
    assert "call the lab" not in visible["message"]
    with runtime.store.connection() as conn:
        current = runtime.store.settings(conn)
    runtime.store.update_settings(
        SettingsInput(
            expected_version=current["version"],
            timezone="Asia/Hong_Kong",
            hide_private=True,
        ),
        "hide-private",
    )
    blocked = _send(
        _client(app), "What should I do next?", key="hidden-step", task_id=secret["id"]
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PRIVATE_TASK_HIDDEN"
    assert "call the lab" not in blocked.text
    hidden_owner = runtime.assistant.local_message(
        AssistantMessage(message="What should I do next?", task_id=secret["id"]),
        "hidden-owner-direct",
    )
    assert hidden_owner["next_step"]["redacted"] is True
    assert "call the lab" not in hidden_owner["message"]
    day = _send(_client(app), "What should I do next?", key="hidden-day").json()
    assert "call the lab" not in day["message"]
    assert "post the notice" in day["message"]
