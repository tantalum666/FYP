"""Follow-up notices expose task_id for Inbox Open task."""

from datetime import UTC, datetime, timedelta

from desk.runtime import Runtime
from desk.store import Store
from desk.tasks import TaskInput


def test_followup_notice_includes_task_id(tmp_path):
    clock = [datetime(2026, 11, 16, 2, tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password="fixture", clock=lambda: clock[0]))
    task = r.tasks.create(
        TaskInput(
            title="Finish fictional inbox report",
            next_step="Draft three headings",
            interval_minutes=15,
        ),
        "task",
    )["task"]
    clock[0] += timedelta(minutes=16)
    r.tick()
    notices = [
        n
        for n in r.notify.listing()["notices"]
        if n.get("kind") == "followup" and n.get("state") == "open"
    ]
    assert len(notices) == 1
    assert notices[0]["task_id"] == task["id"]
