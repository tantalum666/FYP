"""Asking Alice to prep the next meeting reads local records and changes nothing."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.meeting_prep import asks_meeting_prep
from desk.public_capture_schema import SCHEMA_VERSION
from desk.schemas import CreateEvents, EventAction, EventInput, Recurrence, SettingsInput
from desk.store import DomainError
from desk.tasks import TaskInput
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences


def test_only_the_whole_question_is_a_meeting_brief():
    assert asks_meeting_prep("Prep me for my next meeting") == "next"
    assert asks_meeting_prep("Please brief me before my next meeting.") == "next"
    assert asks_meeting_prep("What should I know before my next meeting?") == "next"
    assert asks_meeting_prep("下一场会要准备什么") == "next"
    assert asks_meeting_prep("开会前我要准备什么。") == "next"
    assert asks_meeting_prep("Prep me for tomorrow's meeting") == "tomorrow"
    assert asks_meeting_prep("明天的会议要准备什么？") == "tomorrow"
    assert asks_meeting_prep("What is on today?") is None
    assert asks_meeting_prep("What should I do next?") is None
    assert asks_meeting_prep("When am I free tomorrow?") is None
    assert asks_meeting_prep("Tomorrow 15:00-16:00 Studio time") is None
    assert asks_meeting_prep("Track: finish the report") is None
    assert asks_meeting_prep("Remember: I prefer morning meetings") is None
    assert asks_meeting_prep("Prep me for my next meeting and book a flight") is None


def _app(tmp_path, clock):
    app = create_app(tmp_path, clock=lambda: clock[0], password="meeting-prep-fixture", scheduler=False)
    app.state.runtime.text_ai.config.provider = "none"
    app.state.runtime.text_ai.config.api_key = ""
    return app


def _client(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "meeting-prep-fixture"},
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


def _event(client, key, **event):
    body = {
        "title": "Project discussion",
        "start_local": "2026-11-11T11:00",
        "end_local": "2026-11-11T12:00",
        "timezone": "Asia/Hong_Kong",
        "all_day": False,
        "calendar": "study",
        "color": "lavender",
        "visibility": "private",
        "busy": True,
        "location": "Studio 3",
        "notes": "Bring the adapter",
        "recurrence": {"frequency": "none", "interval": 1, "until": None},
        "reminder_minutes": [],
    }
    body.update(event)
    response = client.post(
        "/api/events",
        json={"event": body, "additional_dates": []},
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["event_ids"][0]


def _counts(runtime):
    with runtime.store.connection() as conn:
        return tuple(
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("events", "owner_memories", "assistant_proposals", "tasks")
        )


def test_the_owner_hears_the_meeting_task_and_cited_memory(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    event_id = _event(client, "meeting-1")
    task = runtime.tasks.create(
        TaskInput(title="Project discussion slides", next_step="check the room"),
        "slides-task",
    )["task"]
    runtime.tasks.create(TaskInput(title="Buy milk"), "milk-task")
    runtime.memory.create("Project discussion needs the cobalt adapter", "cobalt-fact")
    runtime.memory.create("The owner studies at CityU", "city-fact")
    version = task["version"]
    before = _counts(runtime)
    reply = _send(client, "Prep me for my next meeting", key="prep-1")
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["kind"] == "meeting_prep"
    assert body["saved"] is False and body["acted"] is False
    assert body["meeting_prep"]["acted"] is False
    assert body["meeting_prep"]["event_id"] == event_id
    assert body["meeting_prep"]["clock"] == "11:00"
    assert body["meeting_prep"]["location"] == "Studio 3"
    assert body["meeting_prep"]["task_step"] == "check the room"
    assert "cobalt adapter" in body["meeting_prep"]["memory_body"]
    assert "11 Nov 2026" in body["meeting_prep"]["memory_day"]
    assert "Project discussion" in body["message"]
    assert "Studio 3" in body["message"]
    assert "check the room" in body["message"]
    assert "cobalt adapter" in body["message"]
    assert "have not changed the calendar" in body["message"]
    assert "CityU" not in body["message"]
    assert "Buy milk" not in body["message"]
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    assert _counts(runtime) == before
    again = _send(client, "Prep me for my next meeting", key="prep-1")
    assert again.status_code == 200
    assert again.json()["message"] == body["message"]
    conflict = _send(client, "What is on today?", key="prep-1")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    renamed = runtime.store.event_action(
        event_id,
        EventAction(
            action="update",
            scope="series",
            expected_version=1,
            event=EventInput(
                title="Renamed discussion",
                start_local=datetime.fromisoformat("2026-11-11T11:00"),
                end_local=datetime.fromisoformat("2026-11-11T12:00"),
                visibility="private",
                location="Studio 3",
                notes="Bring the adapter",
                reminder_minutes=[],
            ),
        ),
        "rename-meeting",
    )
    assert renamed["event_id"] == event_id
    stale = _send(client, "Prep me for my next meeting", key="prep-1")
    assert "Project discussion" in stale.json()["message"]
    assert "Renamed discussion" not in stale.json()["message"]
    fresh = _send(client, "Prep me for my next meeting", key="prep-2")
    assert "Renamed discussion" in fresh.json()["message"]
    assert "have not changed the calendar" in fresh.json()["message"]
    other = _client(app)
    stolen = _send(other, "What is on today?", key="prep-2")
    assert stolen.status_code == 409
    replay = _send(other, "Prep me for my next meeting", key="prep-2")
    assert replay.status_code == 200
    assert replay.json()["message"] == fresh.json()["message"]


def test_omitted_fields_chinese_and_an_unknown_field(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    client = _client(app)
    _event(client, "meeting-zh", visibility="private", location="", notes="")
    omitted = client.post(
        "/api/assistant/messages",
        json={"message": "Prep me for my next meeting"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "omitted-prep"},
    )
    assert omitted.status_code == 200, omitted.text
    assert "Project discussion" in omitted.json()["message"]
    assert "have not changed the calendar" in omitted.json()["message"]
    chinese = _send(client, "下一场会要准备什么", key="zh-prep", language="zh")
    assert chinese.status_code == 200, chinese.text
    assert "Project discussion" in chinese.json()["message"]
    assert "我还没有改动日历" in chinese.json()["message"]
    unknown = client.post(
        "/api/assistant/messages",
        json={"message": "Prep me for my next meeting", "priority": 1},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "unknown-prep"},
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "priority" in unknown.json()["error"]["fields"]
    assert SCHEMA_VERSION == 3


def test_selected_task_is_not_rewritten_and_other_phrases_stay_put(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    _event(client, "meeting-keep", location="", notes="")
    task = runtime.tasks.create(TaskInput(title="Buy milk"), "milk")["task"]
    version = task["version"]
    asked = _send(client, "What should I know before my next meeting?", key="keep", task_id=task["id"])
    assert asked.status_code == 200, asked.text
    assert asked.json()["kind"] == "meeting_prep"
    assert asked.json()["acted"] is False
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "todo"
    today = _send(client, "What is on today?", key="today-list")
    assert today.status_code == 200, today.text
    assert today.json()["kind"] == "brief"
    assert "Project discussion" in today.json()["message"]
    nxt = _send(client, "What should I do next?", key="not-prep")
    assert nxt.json()["kind"] != "meeting_prep"
    free = _send(client, "When am I free tomorrow?", key="not-free")
    assert free.json()["kind"] != "meeting_prep"
    draft = _send(client, "Tomorrow 15:00-16:00 Studio time", key="draft-event")
    assert draft.status_code == 200, draft.text
    assert draft.json()["kind"] == "draft"
    goal = _send(client, "I will finish the report by 2026-11-20", key="goal-draft")
    assert goal.status_code == 200, goal.text
    assert goal.json()["kind"] == "draft"
    remembered = _send(client, "Remember: I prefer morning meetings", key="remember-fact")
    assert remembered.json()["kind"] == "draft"


def test_tomorrow_weekly_transparent_and_all_day(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    client = _client(app)
    _event(
        client,
        "today-sync",
        title="Today sync",
        start_local="2026-11-11T15:00",
        end_local="2026-11-11T16:00",
        location="",
        notes="",
    )
    _event(
        client,
        "tomorrow-studio",
        title="Tomorrow studio",
        start_local="2026-11-12T09:00",
        end_local="2026-11-12T10:00",
        location="",
        notes="",
    )
    _event(
        client,
        "hold",
        title="Hold",
        start_local="2026-11-11T11:00",
        end_local="2026-11-11T12:00",
        busy=False,
        location="",
        notes="",
    )
    _event(
        client,
        "away",
        title="Away day",
        start_local="2026-11-11T00:00",
        end_local="2026-11-12T00:00",
        all_day=True,
        location="",
        notes="",
    )
    nxt = _send(client, "Prep me for my next meeting", key="which-next").json()
    assert nxt["meeting_prep"]["title"] == "Today sync"
    assert nxt["meeting_prep"]["clock"] == "15:00"
    assert "Hold" not in nxt["message"]
    assert "Away day" not in nxt["message"]
    tomorrow = _send(client, "Prep me for tomorrow's meeting", key="which-tomorrow").json()
    assert tomorrow["meeting_prep"]["title"] == "Tomorrow studio"
    assert tomorrow["meeting_prep"]["date"] == "2026-11-12"
    assert tomorrow["meeting_prep"]["clock"] == "09:00"
    assert "Today sync" not in tomorrow["message"]
    assert "have not changed the calendar" in tomorrow["message"]
    zh = _send(client, "明天的会要准备什么", key="which-zh", language="zh").json()
    assert "Tomorrow studio" in zh["message"]
    assert "我还没有改动日历" in zh["message"]
    later = _app(tmp_path / "later", [datetime(2026, 11, 11, 2, tzinfo=UTC)])
    later_client = _client(later)
    far_only = _event(
        later_client,
        "far-only",
        title="Far review",
        start_local="2026-11-15T11:00",
        end_local="2026-11-15T12:00",
        location="",
        notes="",
    )
    assert far_only
    empty = _send(later_client, "Prep me for my next meeting", key="none-soon").json()
    assert empty["meeting_prep"]["scope"] == "none"
    assert "have not added one" in empty["message"]
    assert "Far review" not in empty["message"]
    assert empty["acted"] is False


def test_underway_and_weekly_occurrence(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    client = _client(app)
    _event(
        client,
        "live",
        title="Live review",
        start_local="2026-11-11T09:00",
        end_local="2026-11-11T11:00",
        location="",
        notes="",
    )
    live = _send(client, "Brief me for my next meeting", key="live-prep").json()
    assert live["meeting_prep"]["underway"] is True
    assert live["meeting_prep"]["until"] == "11:00"
    assert "underway until 11:00" in live["message"]
    assert "have not changed the calendar" in live["message"]
    weekly = _app(tmp_path / "weekly", clock)
    weekly.state.runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Weekly studio",
                start_local=datetime.fromisoformat("2026-11-05T15:00"),
                end_local=datetime.fromisoformat("2026-11-05T16:00"),
                visibility="displayable",
                reminder_minutes=[],
                recurrence=Recurrence(frequency="weekly"),
            )
        ),
        "weekly-studio",
    )
    found = _send(_client(weekly), "Prep me for my next meeting", key="weekly-prep").json()
    assert found["meeting_prep"]["title"] == "Weekly studio"
    assert found["meeting_prep"]["date"] == "2026-11-12"
    assert found["meeting_prep"]["clock"] == "15:00"


def test_quiet_hours_and_brief_style_still_answer(tmp_path):
    clock = [datetime(2026, 11, 11, 15, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    _event(
        client,
        "evening",
        title="Project discussion",
        start_local="2026-11-12T09:00",
        end_local="2026-11-12T10:00",
        location="Studio 3",
        notes="Bring the adapter",
    )
    runtime.tasks.create(
        TaskInput(title="Project discussion slides", next_step="check the room"),
        "slides",
    )
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
    reply = _send(client, "Prep me for my next meeting", key="asked-quiet").json()
    assert reply["message"].startswith("Sure — ")
    assert "Project discussion" in reply["message"]
    assert "have not changed the calendar" in reply["message"]
    assert reply["meeting_prep"]["task_step"] == "check the room"
    assert reply["meeting_prep"]["note"] == "Bring the adapter"
    assert "check the room" not in reply["message"]


def test_interruption_before_the_reply_is_not_success(tmp_path, monkeypatch):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    event_id = _event(client, "meeting-interrupt", location="", notes="")
    task = runtime.tasks.create(TaskInput(title="Buy milk"), "milk")["task"]
    version = task["version"]
    before = _counts(runtime)
    import desk.meeting_prep as meeting_prep

    original = meeting_prep.answer_meeting_prep
    calls = {"n": 0}

    def interrupt(runtime_arg, request, *, owner=True):
        calls["n"] += 1
        if calls["n"] == 1:
            raise DomainError("MEETING_PREP_INTERRUPTED", 503)
        return original(runtime_arg, request, owner=owner)

    monkeypatch.setattr(meeting_prep, "answer_meeting_prep", interrupt)
    failed = _send(client, "Prep me for my next meeting", key="recover-prep")
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "MEETING_PREP_INTERRUPTED"
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    assert _counts(runtime) == before
    recovered = _send(client, "Prep me for my next meeting", key="recover-prep")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["acted"] is False
    assert "Project discussion" in recovered.json()["message"]
    assert runtime.store.snapshot(
        datetime(2026, 11, 11, 0, tzinfo=UTC), datetime(2026, 11, 12, 0, tzinfo=UTC)
    )["occurrences"]
    assert event_id


def test_a_configured_provider_is_not_called(tmp_path, monkeypatch):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    _event(client, "meeting-provider", location="", notes="")
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)
    runtime.text_ai.config.extract_cap = 5

    def generate(*_args, **_kwargs):
        raise AssertionError("provider called")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    monkeypatch.setattr(runtime.text_ai, "generate_live", generate)
    reply = _send(client, "Prep me for my next meeting", key="offline-prep")
    assert reply.status_code == 200, reply.text
    assert reply.json()["kind"] == "meeting_prep"
    assert "Project discussion" in reply.json()["message"]
    stream = client.post(
        "/api/assistant/messages/stream",
        json={"message": "Prep me for my next meeting"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "stream-prep"},
    )
    assert stream.status_code == 200, stream.text
    events = []
    for block in stream.text.split("\n\n"):
        data = "".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        if data:
            events.append(json.loads(data))
    done = [event for event in events if event.get("type") == "done"]
    assert done and done[-1]["reply"]["kind"] == "meeting_prep"
    assert done[-1]["reply"]["acted"] is False
    assert "Project discussion" in done[-1]["reply"]["message"]


def test_private_meetings_stay_off_a_paired_screen_and_a_hidden_owner_display(tmp_path):
    clock = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = _app(tmp_path, clock)
    runtime = app.state.runtime
    client = _client(app)
    secret = _event(
        client,
        "secret-meeting",
        title="Secret errand",
        visibility="private",
        location="Vault",
        notes="the passphrase",
    )
    _event(
        client,
        "lobby-meeting",
        title="Lobby board",
        start_local="2026-11-11T16:00",
        end_local="2026-11-11T17:00",
        visibility="displayable",
        location="Lobby",
        notes="",
    )
    runtime.memory.create("Secret errand needs the cobalt passphrase", "secret-fact")
    task = runtime.tasks.create(
        TaskInput(title="Secret errand", next_step="call the lab", visibility="private"),
        "secret-task",
    )["task"]
    version = task["version"]
    try:
        runtime.text_ai.message(
            AssistantMessage(message="Prep me for my next meeting", task_id=task["id"]),
            "paired-task",
            allow_memory=False,
            principal={"kind": "paired", "id": "lobby", "session": "paired-session"},
        )
    except DomainError as error:
        assert error.code == "TASK_CONTEXT_NOT_ALLOWED" and error.status == 403
    else:
        raise AssertionError("a paired screen selected a task")
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    hidden = runtime.text_ai.message(
        AssistantMessage(message="Prep me for my next meeting"),
        "paired-day",
        allow_memory=False,
        principal={"kind": "paired", "id": "lobby", "session": "paired-session"},
    )
    assert hidden["meeting_prep"]["redacted"] is True
    assert hidden["meeting_prep"]["title"] == ""
    assert hidden["meeting_prep"]["event_id"] == ""
    assert "Secret errand" not in hidden["message"]
    assert "Vault" not in hidden["message"]
    assert "passphrase" not in hidden["message"]
    assert "cobalt" not in hidden["message"]
    assert "call the lab" not in hidden["message"]
    assert "Lobby board" not in hidden["message"]
    assert "private meeting" in hidden["message"]
    board_only = _app(tmp_path / "board", clock)
    board_client = _client(board_only)
    _event(
        board_client,
        "board-only",
        title="Lobby board",
        visibility="displayable",
        location="Lobby",
        notes="",
    )
    board_only.state.runtime.memory.create("Lobby board needs the cobalt adapter", "board-fact")
    visible = board_only.state.runtime.text_ai.message(
        AssistantMessage(message="Prep me for my next meeting"),
        "paired-board",
        allow_memory=False,
        principal={"kind": "paired", "id": "lobby", "session": "paired-session"},
    )
    assert visible["meeting_prep"]["title"] == "Lobby board"
    assert "Lobby" in visible["message"]
    assert "cobalt" not in visible["message"]
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
    owner_hidden = _send(client, "Prep me for my next meeting", key="hidden-owner")
    assert owner_hidden.status_code == 200, owner_hidden.text
    assert "Secret errand" not in owner_hidden.text
    assert "passphrase" not in owner_hidden.text
    assert "cobalt" not in owner_hidden.text
    assert owner_hidden.json()["meeting_prep"]["redacted"] is True
    assert secret
