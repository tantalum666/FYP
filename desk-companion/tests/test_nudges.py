"""Check-ins reuse quiet hours and say why they fired. No model call is involved."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.context import pack_conversation
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.store import Store, encode
from desk.tasks import TaskInput
from desk.text_ai import TextAssistant, TextConfig
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences


def _runtime(tmp_path, when):
    clock = [when]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    return runtime, clock


def _prefs(runtime, **fields):
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(**fields),
        ),
        uuid4().hex,
    )


def test_morning_brief_explains_itself_once_and_quiet_hours_block_it(tmp_path):
    runtime, clock = _runtime(tmp_path, datetime(2026, 10, 2, tzinfo=UTC))
    _prefs(runtime, daily_brief_enabled=True)
    runtime.tick()
    nudges = runtime.nudges.listing()["nudges"]
    assert len(nudges) == 1 and nudges[0]["kind"] == "morning_brief"
    assert "08:00" in nudges[0]["reason_en"] and "quiet hours" in nudges[0]["reason_en"]
    runtime.tick()
    assert len(runtime.nudges.listing()["nudges"]) == 1
    runtime.nudges.dismiss(nudges[0]["id"], "dismiss")
    runtime.tick()
    assert runtime.nudges.listing()["nudges"][0]["state"] == "dismissed"
    clock[0] = datetime(2026, 10, 2, 0, 2, tzinfo=UTC)
    assert runtime.nudges.listing()["nudges"][0]["state"] == "dismissed"

    edge, _edge_clock = _runtime(tmp_path / "edge", datetime(2026, 10, 2, 0, 2, tzinfo=UTC))
    _prefs(edge, daily_brief_enabled=True)
    edge.tick()
    assert edge.nudges.listing()["nudges"] == []

    later, _later_clock = _runtime(tmp_path / "quiet", datetime(2026, 10, 2, 15, tzinfo=UTC))
    _prefs(later, daily_brief_enabled=True, daily_brief_time="23:00")
    later.tick()
    assert later.nudges.listing()["nudges"] == []
    claimed = later.data.claim_announcement("display-quiet")
    assert claimed["quiet"] is True and claimed["announcement"] is None


def test_evening_check_in_counts_open_tasks_and_the_spoken_brief_includes_why(tmp_path):
    runtime, _clock = _runtime(tmp_path, datetime(2026, 10, 2, 13, tzinfo=UTC))
    runtime.tasks.create(TaskInput(title="Report", interval_minutes=15), "task")
    _prefs(runtime, evening_check_enabled=True)
    runtime.tick()
    nudge = runtime.nudges.listing()["nudges"][0]
    assert nudge["kind"] == "evening_check"
    assert "21:00" in nudge["reason_en"] and "quiet hours" in nudge["reason_en"]
    assert nudge["summary_en"].startswith("1 open task")
    app = create_app(
        tmp_path / "claim",
        password="fixture-only",
        scheduler=False,
        clock=lambda: datetime(2026, 10, 2, tzinfo=UTC),
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    app.state.runtime.data.update(
        PreferencesUpdate(
            expected_version=1,
            preferences=WorkspacePreferences(daily_brief_enabled=True),
        ),
        "enable-brief",
    )
    claimed = app.state.runtime.data.claim_announcement("display-one")
    assert claimed["announcement"]["kind"] == "brief"
    assert "08:00" in claimed["announcement"]["reason_en"]
    display = TestClient(app)
    owner_headers = {"X-Desk-Request": "1", "X-Operation-Id": "pair"}
    enrol = client.post("/api/devices/enrol-display", json={"name": "Screen"}, headers=owner_headers)
    display.headers["Authorization"] = "Bearer " + client.cookies.get("desk_companion_device")
    assert enrol.status_code == 200
    assert display.get("/api/nudges", headers={"X-Desk-Request": "1"}).status_code == 403


def test_task_followups_explain_the_rule_including_quiet_hours(tmp_path):
    runtime, clock = _runtime(tmp_path, datetime(2026, 10, 3, 1, tzinfo=UTC))
    task = runtime.tasks.create(
        TaskInput(title="Report", interval_minutes=15, next_step="Prepare charts"), "open"
    )["task"]
    clock[0] += timedelta(minutes=16)
    runtime.tick()
    followup = runtime.tasks.detail(task["id"])["task"]["followup"]
    assert "saved check time" in followup["reason_en"]
    assert "quiet hours ended" not in followup["reason_en"]
    assert "Prepare charts" not in followup["reason_en"]

    waiting, waiting_clock = _runtime(tmp_path / "wait", datetime(2026, 10, 3, 1, tzinfo=UTC))
    held = waiting.tasks.create(
        TaskInput(
            title="Figures",
            status="waiting",
            waiting_for="the group",
            interval_minutes=15,
        ),
        "waiting",
    )["task"]
    waiting_clock[0] += timedelta(minutes=16)
    waiting.tick()
    assert "waiting" in waiting.tasks.detail(held["id"])["task"]["followup"]["reason_en"]

    quiet, quiet_clock = _runtime(tmp_path / "quiet-task", datetime(2026, 10, 3, 15, tzinfo=UTC))
    deferred = quiet.tasks.create(TaskInput(title="Later", interval_minutes=15), "later")["task"]
    quiet_clock[0] += timedelta(minutes=16)
    quiet.tick()
    assert quiet.tasks.detail(deferred["id"])["task"]["followup"] is None
    quiet_clock[0] = datetime(2026, 10, 3, 23, 1, tzinfo=UTC)
    quiet.tick()
    reason = quiet.tasks.detail(deferred["id"])["task"]["followup"]["reason_en"]
    assert "quiet hours ended" in reason

    hidden, hidden_clock = _runtime(tmp_path / "private", datetime(2026, 10, 3, 1, tzinfo=UTC))
    hidden.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide",
    )
    private = hidden.tasks.create(
        TaskInput(title="Secret", next_step="Hidden step", interval_minutes=15), "private"
    )["task"]
    hidden_clock[0] += timedelta(minutes=16)
    hidden.tick()
    redacted = hidden.tasks.listing()["tasks"][0]["followup"]
    assert private["visibility"] == "private"
    assert "Hidden step" not in redacted["reason_en"]
    assert "details stay hidden" in redacted["reason_en"]


def test_background_advice_keeps_the_nudge_reason(tmp_path):
    runtime, clock = _runtime(tmp_path, datetime(2026, 10, 3, 1, tzinfo=UTC))
    task = runtime.tasks.create(TaskInput(title="Report", interval_minutes=15), "task")["task"]
    clock[0] += timedelta(minutes=16)
    runtime.tick()
    reason = runtime.tasks.detail(task["id"])["task"]["followup"]["reason_en"]

    def response(request):
        assert "Report" in request.content.decode()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"en": "Any progress?", "zh": "有进展吗？"})
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1},
            },
        )

    service = TextAssistant(
        runtime,
        TextConfig(
            "qwen",
            "test-model",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "fixture",
            True,
        ),
        httpx.MockTransport(response),
    )
    service.enrich_one()
    followup = runtime.tasks.detail(task["id"])["task"]["followup"]
    assert followup["mode"] == "ai" and followup["reason_en"] == reason


def test_saved_style_is_packed_and_proactivity_gates_check_ins(tmp_path):
    runtime, _clock = _runtime(tmp_path, datetime(2026, 10, 2, tzinfo=UTC))
    _prefs(
        runtime,
        tone="warm",
        verbosity="brief",
        proactivity="off",
        daily_brief_enabled=True,
        evening_check_enabled=True,
    )
    assert "tone warm" in pack_conversation(runtime)["style"]
    assert "verbosity brief" in pack_conversation(runtime)["style"]
    runtime.tick()
    assert runtime.nudges.listing()["nudges"] == []

    low, _low_clock = _runtime(tmp_path / "low", datetime(2026, 10, 2, tzinfo=UTC))
    _prefs(
        low,
        proactivity="low",
        daily_brief_enabled=True,
        evening_check_enabled=True,
    )
    low.tick()
    assert [row["kind"] for row in low.nudges.listing()["nudges"]] == ["morning_brief"]
    clock_low = datetime(2026, 10, 2, 13, tzinfo=UTC)
    evening, _evening_clock = _runtime(tmp_path / "evening", clock_low)
    _prefs(evening, proactivity="low", evening_check_enabled=True, daily_brief_enabled=True)
    evening.tick()
    assert evening.nudges.listing()["nudges"] == []

    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE workspace_preferences SET data=? WHERE id=1",
            (encode({"quiet_enabled": True, "reminder_strength": "chime"}),),
        )
    restored = runtime.data.preferences()
    assert restored["tone"] == "plain"
    assert restored["verbosity"] == "normal"
    assert restored["proactivity"] == "normal"
    assert restored["reminder_strength"] == "chime"
