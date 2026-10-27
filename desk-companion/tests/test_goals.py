"""A stated goal is tracked only after confirm, and it is not closed by the clock."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.goals import parse_goal
from desk.runtime import Runtime
from desk.store import Store
from zoneinfo import ZoneInfo


def test_friday_and_a_chinese_prefix_resolve_to_one_title():
    now = datetime(2026, 10, 27, 10, tzinfo=ZoneInfo("Asia/Hong_Kong"))
    parsed = parse_goal("Goal: finish the report by Friday", now)
    assert parsed["title"] == "finish the report"
    assert parsed["due_local"].isoformat() == "2026-10-30T18:00:00+08:00"
    chinese = parse_goal("目标：周五前完成报告", now)
    assert chinese["title"] == "完成报告"
    assert chinese["due_local"].date().isoformat() == "2026-10-30"
    assert parse_goal("hello", now) is None


def test_confirm_tracks_a_goal_and_closing_asks_first(tmp_path):
    clock = [datetime(2026, 10, 27, 2, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    reply = runtime.assistant.local_message(
        AssistantMessage(message="Goal: finish the report by Friday"),
        "state-goal",
    )
    assert reply["kind"] == "draft" and reply["saved"] is False
    assert runtime.goals.listing()["goals"] == []
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "confirm-goal")
    goal = runtime.goals.listing()["goals"][0]
    assert goal["title"] == "finish the report" and goal["state"] == "open"
    task = runtime.tasks.detail(goal["task_id"])["task"]
    assert task["due_local"].startswith("2026-10-30T18:00")
    assert task["check_in_local"].startswith("2026-10-30T09:00")
    clock[0] = datetime(2026, 10, 30, 1, 1, tzinfo=UTC)
    runtime.tasks.tick()
    followed = runtime.tasks.detail(goal["task_id"])["task"]
    assert followed["followup"] and followed["status"] == "todo"
    close = runtime.assistant.local_message(
        AssistantMessage(message="Done with: finish the report"),
        "ask-close",
    )
    assert "Confirm before" in close["message"]
    assert runtime.goals.listing()["goals"][0]["state"] == "open"
    runtime.assistant.decide(close["proposal"]["id"], "confirm", "confirm-close")
    assert runtime.tasks.detail(goal["task_id"])["task"]["status"] == "completed"
    assert runtime.goals.listing()["goals"][0]["state"] == "closed"


def test_a_due_goal_is_asked_once_per_day_and_stays_open(tmp_path):
    clock = [datetime(2026, 10, 27, 2, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    reply = runtime.assistant.local_message(
        AssistantMessage(message="I will finish the report by 2026-10-27", language="en"),
        "due-today",
    )
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "confirm-due")
    clock[0] = datetime(2026, 10, 27, 10, 5, tzinfo=UTC)
    runtime.goals.tick()
    runtime.goals.tick()
    with runtime.store.connection() as conn:
        drafts = conn.execute(
            "SELECT COUNT(*) FROM assistant_proposals WHERE kind='task_change'"
        ).fetchone()[0]
    assert drafts == 1
    assert runtime.goals.listing()["goals"][0]["state"] == "open"
    clock[0] += timedelta(days=1)
    runtime.goals.tick()
    with runtime.store.connection() as conn:
        later = conn.execute(
            "SELECT COUNT(*) FROM assistant_proposals WHERE kind='task_change'"
        ).fetchone()[0]
    assert later == 2
    assert runtime.goals.listing()["goals"][0]["task_status"] == "todo"


def test_display_cannot_list_goals(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    owner = TestClient(app)
    owner.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-goals"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/goals").status_code == 403
