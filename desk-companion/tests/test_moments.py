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
    assert runtime.moments.view()["suggestion"] is None


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
