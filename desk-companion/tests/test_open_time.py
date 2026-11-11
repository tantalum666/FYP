"""Asked availability is read from the saved calendar and books nothing."""

import json
from contextlib import contextmanager
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.open_time import parse_ask
from desk.store import encode
from desk.tasks import TaskInput
from desk.text_ai import TextAssistant, TextConfig
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences, is_quiet

WHEN = datetime(2026, 11, 11, 6, tzinfo=UTC)  # Wednesday 14:00 in Hong Kong
ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


def _app(tmp_path, when=WHEN):
    app = create_app(tmp_path, password="fixture-only", scheduler=False, clock=lambda: when)
    client = TestClient(app)
    client.headers["X-Desk-Request"] = "1"
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": "fixture-only"}
        ).status_code
        == 200
    )
    return app, client


def _event(**updates):
    body = {
        "title": "Project discussion",
        "start_local": "2026-11-12T10:00",
        "end_local": "2026-11-12T11:30",
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
    }
    body.update(updates)
    return body


def _create(client, **updates):
    response = client.post(
        "/api/events",
        json={"event": _event(**updates), "additional_dates": []},
        headers={"X-Operation-Id": "event-" + updates.get("title", "one")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _count(runtime):
    with runtime.store.connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]


def _ask(client, message, key, **extra):
    body = {"message": message, "language": "en"}
    body.update(extra)
    return client.post("/api/assistant/messages", json=body, headers={"X-Operation-Id": key})


def _events(text):
    found = []
    for block in text.split("\n\n"):
        if block.startswith("data: "):
            found.append(json.loads(block[6:]))
    return found


def test_other_questions_are_not_availability():
    assert parse_ask("What is on today?") is None
    assert parse_ask("What is on next week?") is None
    assert parse_ask("When am I free next week?") is None
    assert parse_ask("What should I do next?") is None
    assert parse_ask("接下来做什么？") is None
    assert parse_ask("Tomorrow 15:00–16:00 Studio time") is None
    assert parse_ask("Remember: I am free on Thursdays") is None
    assert parse_ask("When am I free tomorrow?")["instant"] is None
    assert parse_ask("") is None


def test_tomorrow_names_the_open_stretches_and_books_nothing(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    assert _count(runtime) == 0
    _create(client)
    _create(
        client,
        title="Office hours",
        start_local="2026-11-12T16:00",
        end_local="2026-11-12T17:00",
        busy=False,
        visibility="displayable",
    )
    response = _ask(client, "When am I free tomorrow?", "tomorrow")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "open_time" and body["saved"] is False and body["acted"] is False
    assert body["open_time"]["booked"] is False
    assert body["open_time"]["date"] == "2026-11-12"
    assert body["open_time"]["timezone"] == "Asia/Hong_Kong"
    assert body["open_time"]["openings"] == [
        {"start": "08:00", "end": "10:00"},
        {"start": "11:30", "end": "21:00"},
    ]
    assert "Project discussion" not in body["message"]
    assert "Office hours" not in body["message"]
    assert "not a claim that you are free" in body["message"]
    assert "nothing was booked" in body["message"]
    assert "09:00" not in body["message"]
    assert _count(runtime) == 2
    assert client.get("/api/assistant/proposals").json()["proposals"] == []
    zh = _ask(client, "我明天什么时候有空？", "tomorrow-zh", language="zh")
    assert zh.status_code == 200
    assert zh.json()["open_time"]["openings"] == body["open_time"]["openings"]
    assert "没有写入任何日程" in zh.json()["message"]
    afternoon = _ask(client, "明天下午3点有空吗", "afternoon-zh", language="zh")
    assert afternoon.json()["open_time"]["instant"] == "15:00"
    assert afternoon.json()["open_time"]["openings"] == [{"start": "15:00", "end": "18:00"}]
    assert _count(runtime) == 2


def test_a_clock_time_names_the_conflict_and_a_transparent_event_does_not(tmp_path):
    app, client = _app(tmp_path)
    _create(client, start_local="2026-11-12T15:00", end_local="2026-11-12T16:30")
    _create(
        client,
        title="Hold",
        start_local="2026-11-12T18:00",
        end_local="2026-11-12T19:00",
        busy=False,
    )
    conflict = _ask(client, "Does Thursday at 15:00 work?", "conflict")
    assert conflict.status_code == 200
    body = conflict.json()
    assert body["kind"] == "open_time" and body["open_time"]["filled"] is True
    assert body["open_time"]["overlaps"][0]["labels"] == ["Project discussion"]
    assert "16:30" in body["message"] and "nothing was booked" in body["message"]
    assert _count(app.state.runtime) == 2
    free = _ask(client, "Am I free Thursday at 6pm?", "transparent")
    assert free.json()["open_time"]["openings"] == [{"start": "18:00", "end": "21:00"}]
    assert "Hold" not in free.json()["message"]
    passed = _ask(client, "When am I free this morning?", "morning")
    assert "already passed" in passed.json()["message"]
    assert passed.json()["open_time"]["openings"] == []
    outside = _ask(client, "Am I free tomorrow morning at 3pm?", "outside")
    assert "outside" in outside.json()["message"] and "15:00" in outside.json()["message"]
    assert outside.json()["open_time"]["openings"] == []


def test_weekly_and_all_day_events_block_the_asked_day(tmp_path):
    _app_pair = _app(tmp_path)
    app, client = _app_pair
    _create(
        client,
        title="Thursday rehearsal",
        start_local="2026-11-12T10:00",
        end_local="2026-11-12T11:00",
        recurrence={"frequency": "weekly", "interval": 1, "until": None},
    )
    _create(
        client,
        title="Leave",
        start_local="2026-11-13T00:00",
        end_local="2026-11-14T00:00",
        all_day=True,
        visibility="displayable",
    )
    later = _ask(client, "When am I free next Thursday?", "next-thursday")
    assert later.json()["open_time"]["date"] == "2026-11-19"
    assert later.json()["open_time"]["openings"] == [
        {"start": "08:00", "end": "10:00"},
        {"start": "11:00", "end": "21:00"},
    ]
    friday = _ask(client, "When am I free Friday?", "friday")
    assert friday.json()["open_time"]["date"] == "2026-11-13"
    assert friday.json()["open_time"]["openings"] == []
    assert "Leave" in friday.json()["message"] and "all day" in friday.json()["message"]
    assert _count(app.state.runtime) == 2


def test_a_short_gap_is_not_offered_as_a_meeting(tmp_path):
    app, client = _app(tmp_path)
    _create(
        client,
        title="Long seminar",
        start_local="2026-11-11T14:00",
        end_local="2026-11-11T20:40",
    )
    listed = _ask(client, "When am I free today?", "today")
    assert listed.json()["open_time"]["openings"] == []
    assert "20:40" in listed.json()["message"] and "30 minutes" in listed.json()["message"]
    point = _ask(client, "Am I free today at 20:45?", "point")
    assert point.json()["open_time"]["openings"] == [{"start": "20:45", "end": "21:00"}]
    assert "until 21:00" in point.json()["message"]
    assert _count(app.state.runtime) == 1


def test_private_titles_stay_off_a_paired_display_and_a_hidden_calendar(tmp_path):
    app, owner = _app(tmp_path)
    runtime = app.state.runtime
    _create(client=owner, title="Dentist", start_local="2026-11-12T10:00", end_local="2026-11-12T11:00")
    _create(
        client=owner,
        title="Office hours",
        start_local="2026-11-12T14:00",
        end_local="2026-11-12T15:00",
        visibility="displayable",
    )
    seen = _ask(owner, "Does Thursday at 10:00 work?", "owner-private")
    assert "Dentist" in seen.json()["message"]
    public = _ask(owner, "Does Thursday at 14:00 work?", "owner-public")
    assert "Office hours" in public.json()["message"]
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers={"X-Operation-Id": "pair"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    hidden = display.post(
        "/api/assistant/messages",
        json={"message": "Does Thursday at 10:00 work?", "language": "en"},
        headers={"X-Operation-Id": "display-private"},
    )
    assert hidden.status_code == 200, hidden.text
    assert "Dentist" not in hidden.text
    assert "private event" in hidden.json()["message"]
    shown = display.post(
        "/api/assistant/messages",
        json={"message": "Does Thursday at 14:00 work?", "language": "en"},
        headers={"X-Operation-Id": "display-public"},
    )
    assert "Office hours" in shown.json()["message"]
    stranger = TestClient(app)
    stranger.headers["X-Desk-Request"] = "1"
    refused = stranger.post(
        "/api/assistant/messages",
        json={"message": "Does Thursday at 10:00 work?", "language": "en"},
        headers={"X-Operation-Id": "stranger"},
    )
    assert refused.status_code == 401
    assert "Dentist" not in refused.text and "Office hours" not in refused.text
    with runtime.store.connection(write=True) as conn:
        row = conn.execute("SELECT data FROM settings WHERE id=1").fetchone()
        data = json.loads(row["data"])
        data["hide_private"] = True
        conn.execute("UPDATE settings SET data=? WHERE id=1", (encode(data),))
    redacted = _ask(owner, "Does Thursday at 10:30 work?", "owner-hidden")
    assert "Dentist" not in redacted.json()["message"]
    assert redacted.json()["open_time"]["overlaps"][0]["labels"] == []
    assert redacted.json()["open_time"]["overlaps"][0]["private"] is True


def test_the_receipt_is_idempotent_and_a_missing_field_is_not_invented(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    first = _ask(client, "When am I free tomorrow?", "same")
    assert first.status_code == 200
    assert first.json()["open_time"]["openings"] == [{"start": "08:00", "end": "21:00"}]
    omitted = client.post(
        "/api/assistant/messages",
        json={"message": "When am I free tomorrow?"},
        headers={"X-Operation-Id": "language-omitted"},
    )
    assert omitted.status_code == 200
    assert omitted.json()["message"] == first.json()["message"]
    _create(client, title="Added later")
    repeated = _ask(client, "When am I free tomorrow?", "same")
    assert repeated.status_code == 200
    assert repeated.json()["message"] == first.json()["message"]
    assert repeated.json()["open_time"]["openings"] == [{"start": "08:00", "end": "21:00"}]
    fresh = _ask(client, "When am I free tomorrow?", "after-change")
    assert fresh.json()["open_time"]["openings"][0] == {"start": "08:00", "end": "10:00"}
    conflict = _ask(client, "When am I free Friday?", "same")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert _ask(client, "When am I free tomorrow?", "same").json()["message"] == first.json()["message"]
    missing = client.post(
        "/api/assistant/messages", json={"message": "When am I free tomorrow?", "language": "en"}
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "OPERATION_ID_REQUIRED"
    extra = client.post(
        "/api/assistant/messages",
        json={"message": "When am I free tomorrow?", "language": "en", "book_it": True},
        headers={"X-Operation-Id": "unknown-field"},
    )
    assert extra.status_code == 422
    assert "08:00" not in extra.text
    assert _count(runtime) == 1
    stream = client.post(
        "/api/assistant/messages/stream",
        json={"message": "When am I free Friday?", "language": "en"},
        headers={"X-Operation-Id": "stream-friday"},
    )
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    events = _events(stream.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["kind"] == "open_time"
    assert events[-1]["reply"]["open_time"]["date"] == "2026-11-13"
    assert not any(event["type"] == "tool" for event in events)
    deltas = "".join(event["text"] for event in events if event["type"] == "delta")
    assert deltas == events[-1]["reply"]["message"]
    assert "nothing was booked" in deltas


def test_an_interruption_before_the_reply_is_stored_is_not_success(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    _create(client)
    before = _count(runtime)
    original = runtime.store.connection
    failed = {"inserts": 0}

    @contextmanager
    def wrapped(write=False):
        with original(write=write) as conn:
            class Guard:
                def execute(self, sql, *args, **kwargs):
                    if isinstance(sql, str) and "INSERT INTO assistant_replies" in sql:
                        failed["inserts"] += 1
                        raise RuntimeError("interrupted before the reply was stored")
                    return conn.execute(sql, *args, **kwargs)

                def __getattr__(self, name):
                    return getattr(conn, name)

            yield Guard()

    runtime.store.connection = wrapped
    broken = TestClient(app, raise_server_exceptions=False)
    broken.headers["X-Desk-Request"] = "1"
    broken.cookies.update(client.cookies)
    response = broken.post(
        "/api/assistant/messages",
        json={"message": "When am I free tomorrow?", "language": "en"},
        headers={"X-Operation-Id": "interrupted"},
    )
    assert response.status_code == 500
    assert failed["inserts"] == 1
    runtime.store.connection = original
    with runtime.store.connection() as conn:
        stored = conn.execute("SELECT COUNT(*) FROM assistant_replies").fetchone()[0]
    assert stored == 0
    assert _count(runtime) == before
    recovered = _ask(client, "When am I free tomorrow?", "interrupted")
    assert recovered.status_code == 200
    assert recovered.json()["open_time"]["openings"][0] == {"start": "08:00", "end": "10:00"}
    with runtime.store.connection() as conn:
        stored = conn.execute("SELECT COUNT(*) FROM assistant_replies").fetchone()[0]
    assert stored == 1
    assert _count(runtime) == before


def test_a_configured_provider_is_not_called_and_a_task_is_not_rewritten(tmp_path):
    app, client = _app(tmp_path)
    runtime = app.state.runtime
    calls = []

    def response(_request):
        calls.append(1)
        return httpx.Response(500)

    service = TextAssistant(
        runtime,
        TextConfig("qwen", "test-model", ENDPOINT, "fixture-key"),
        httpx.MockTransport(response),
    )
    principal = {"kind": "owner", "session": "fixture"}
    reply = service.message(
        AssistantMessage(message="When am I free tomorrow?"),
        "paid",
        principal=principal,
    )
    assert calls == []
    assert reply["kind"] == "open_time" and reply["open_time"]["booked"] is False
    task = runtime.tasks.create(TaskInput(title="Print the handout"), "task-1")["task"]
    version = task["version"]
    scoped = _ask(client, "When am I free tomorrow?", "scoped", task_id=task["id"])
    assert scoped.json()["kind"] == "open_time"
    assert runtime.tasks.detail(task["id"])["task"]["version"] == version
    remembered = _ask(client, "Remember: I am free on Thursdays", "remember")
    assert remembered.json()["kind"] == "draft" and remembered.json()["saved"] is False
    assert runtime.memory.for_model() == []
    listed = _ask(client, "What is on tomorrow?", "list")
    assert listed.json()["kind"] == "brief"
    drafted = _ask(client, "Tomorrow 15:00–16:00 Studio time", "draft-event")
    assert drafted.json()["kind"] == "draft"
    assert drafted.json()["saved"] is False
    assert _count(runtime) == 0
    assert parse_ask("What should I do next?") is None
    nxt = _ask(client, "What should I do next?", "next")
    assert nxt.json()["kind"] != "open_time"


def test_quiet_hours_and_a_brief_warm_reply_still_include_the_times(tmp_path):
    app, client = _app(tmp_path, datetime(2026, 11, 11, 15, tzinfo=UTC))
    runtime = app.state.runtime
    _create(client)
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(tone="warm", verbosity="brief", proactivity="off"),
        ),
        "style-off",
    )
    now = runtime.store.clock().astimezone(ZoneInfo("Asia/Hong_Kong"))
    assert is_quiet(runtime.data.preferences(), now)
    reply = _ask(client, "When am I free tomorrow?", "styled")
    assert reply.status_code == 200, reply.text
    message = reply.json()["message"]
    assert message.startswith("Sure — ")
    assert "08:00" in message and "10:00" in message and "11:30" in message
    assert "nothing was booked" in message
    assert "not a claim that you are free" in message
    week = _ask(client, "When am I free next week?", "week")
    assert week.json()["kind"] == "brief"
    assert week.json()["kind"] != "open_time"
