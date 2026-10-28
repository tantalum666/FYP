"""A free calendar gap can suggest one open item, and dismissals are remembered."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventInput
from desk.store import Store


def test_a_gap_explains_itself_and_three_dismissals_pause_it(tmp_path):
    runtime = Runtime(
        Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 27, 2, tzinfo=UTC))
    )
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Meeting",
                start_local=datetime(2026, 10, 27, 10, 45),
                end_local=datetime(2026, 10, 27, 11, 30),
                visibility="displayable",
            )
        ),
        "meeting",
    )
    for index, title in enumerate(("finish the report", "send the notes", "file the receipt")):
        reply = runtime.assistant.local_message(
            AssistantMessage(message=f"Goal: {title} by Friday"),
            f"goal-{index}",
        )
        runtime.assistant.decide(reply["proposal"]["id"], "confirm", f"confirm-{index}")
    first = runtime.moments.view()["suggestion"]
    assert first["minutes"] == 45
    assert "Meeting" in first["reason_en"] and "not proof" in first["reason_en"]
    assert runtime.moments.view()["suggestion"]["id"] == first["id"]
    seen = set()
    for index in range(3):
        current = runtime.moments.view()["suggestion"]
        assert current["id"] not in seen
        seen.add(current["id"])
        runtime.moments.dismiss(current["id"], f"dismiss-{index}")
    paused = runtime.moments.view()
    assert paused["suggestion"] is None and paused["paused"] is True
    assert len(paused["dismissals"]) == 3
    reset = runtime.moments.reset("reset")
    assert reset["paused"] is False and reset["suggestion"] is not None


def test_quiet_hours_and_a_short_gap_suggest_nothing(tmp_path):
    clock = [datetime(2026, 10, 27, 15, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    reply = runtime.assistant.local_message(
        AssistantMessage(message="Goal: finish the report by Friday"),
        "goal",
    )
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "confirm")
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Late",
                start_local=datetime(2026, 10, 27, 23, 30),
                end_local=datetime(2026, 10, 27, 23, 45),
                visibility="displayable",
            )
        ),
        "late",
    )
    assert runtime.moments.view()["suggestion"] is None
    clock[0] = datetime(2026, 10, 27, 2, tzinfo=UTC)
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Soon",
                start_local=datetime(2026, 10, 27, 10, 10),
                end_local=datetime(2026, 10, 27, 10, 20),
                visibility="displayable",
            )
        ),
        "soon",
    )
    soon = runtime.moments.view()["suggestion"]
    assert soon["kind"] == "open_loop"
    assert "finish the report" in soon["reason_en"]
    assert "30 to 180" in soon["reason_en"]
    assert "Soon" not in soon["reason_en"]


def test_display_cannot_read_suggestions(tmp_path):
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
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-moments"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/moments").status_code == 403


def test_an_unanswered_followup_is_the_open_loop_and_three_dismissals_pause_it(tmp_path):
    clock = [datetime(2026, 10, 27, 2, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    from desk.tasks import TaskInput

    runtime.tasks.create(TaskInput(title="Call the lab", interval_minutes=15), "task")
    reply = runtime.assistant.local_message(
        AssistantMessage(message="Goal: finish the report by Friday"),
        "goal",
    )
    runtime.assistant.decide(reply["proposal"]["id"], "confirm", "confirm-goal")
    clock[0] = datetime(2026, 10, 27, 2, 16, tzinfo=UTC)
    runtime.tasks.tick()
    current = runtime.moments.view()["suggestion"]
    assert current["kind"] == "open_loop"
    assert current["title"] == "Call the lab"
    assert "unanswered" in current["reason_en"] and "30 to 180" in current["reason_en"]
    for index, message in enumerate(
        (
            "Goal: send the notes by Friday",
            "Goal: file the receipt by Friday",
        )
    ):
        extra = runtime.assistant.local_message(AssistantMessage(message=message), f"goal-{index}")
        runtime.assistant.decide(extra["proposal"]["id"], "confirm", f"confirm-{index}")
    # The follow-up is one loop. Dismiss it, then two goal loops, and the kind pauses.
    runtime.moments.dismiss(current["id"], "dismiss-follow")
    for index in range(2):
        nxt = runtime.moments.view()["suggestion"]
        assert nxt["kind"] == "open_loop"
        runtime.moments.dismiss(nxt["id"], f"dismiss-loop-{index}")
    paused = runtime.moments.view()
    assert paused["suggestion"] is None and paused["paused"] is True
    assert "Open-loop" in paused["pause_reason_en"]
    restored = runtime.moments.reset("reset-loops")
    assert restored["paused"] is False and restored["suggestion"]["kind"] == "open_loop"
