"""Daily and weekly digests count saved records and do not call a model."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.runtime import Runtime
from desk.store import Store
from desk.tasks import TaskAction, TaskInput


def _runtime(path, when):
    clock = [when]
    runtime = Runtime(Store(path, password="fixture-only", clock=lambda: clock[0]))
    return runtime, clock


def test_digest_counts_saved_work_and_polish_stays_off(tmp_path):
    runtime, clock = _runtime(tmp_path, datetime(2026, 10, 27, 2, tzinfo=UTC))
    task = runtime.tasks.create(TaskInput(title="Report"), "task")["task"]
    runtime.tasks.action(
        task["id"],
        TaskAction(action="complete", expected_version=task["version"]),
        "done",
    )
    runtime.memory.create("I prefer tea", "memory")
    stated = runtime.assistant.local_message(
        AssistantMessage(message="Goal: finish the report by Friday"),
        "goal",
    )
    runtime.assistant.decide(stated["proposal"]["id"], "confirm", "confirm-goal")

    def fail_generate(*_args, **_kwargs):
        raise AssertionError("digest must not call the model")

    runtime.text_ai.generate = fail_generate
    day = runtime.digests.view("day", polish=True)
    assert day["polished"] is False
    assert day["completed"] == 1 and day["memory_changes"] == 1
    assert "finish the report" in day["text_en"]
    assert "finish the report" not in day["spoken_en"]
    week = runtime.digests.view("week")
    assert week["completed"] == 1
    clock[0] -= timedelta(days=8)
    runtime.memory.create("Old fact", "old")
    clock[0] = datetime(2026, 10, 27, 2, tzinfo=UTC)
    assert runtime.digests.view("day")["memory_changes"] == 1
    assert runtime.digests.view("week")["memory_changes"] == 1


def test_device_hears_counts_only_and_quiet_hours_hold_them(tmp_path):
    runtime, clock = _runtime(tmp_path, datetime(2026, 10, 27, 2, tzinfo=UTC))
    runtime.memory.create("I prefer tea", "memory")
    sent = runtime.digests.announce("day")
    assert any(item["status"] == "delivered" for item in sent["deliveries"])
    claimed = runtime.data.claim_announcement("display-one")
    assert claimed["announcement"]["kind"] == "notice"
    assert "I prefer tea" not in claimed["announcement"]["body_en"]
    assert "memory change" in claimed["announcement"]["body_en"]
    clock[0] = datetime(2026, 10, 27, 15, tzinfo=UTC)
    held = runtime.digests.announce("week")
    assert all(item["status"] == "quiet" for item in held["deliveries"])


def test_display_cannot_read_the_digest(tmp_path):
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
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-digest"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/digests").status_code == 403
