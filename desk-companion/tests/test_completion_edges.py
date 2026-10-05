from datetime import UTC, datetime

import pytest

from desk.outputs import OutputHeartbeat
from desk.phone import phone_snapshot
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventInput
from desk.store import Store, DomainError
from desk.posture import PosturePreferences, classify, features
from test_posture import calibrated, feed, frame


def test_phone_projection_never_exposes_private_titles_or_notes(tmp_path):
    store = Store(
        tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, 12, tzinfo=UTC)
    )
    runtime = Runtime(store)
    store.create(
        CreateEvents(
            event=EventInput(
                title="Private appointment",
                start_local="2026-10-02T21:00",
                end_local="2026-10-02T22:00",
                notes="private notes",
            )
        ),
        "private",
    )
    store.create(
        CreateEvents(
            event=EventInput(
                title="Public review",
                visibility="displayable",
                start_local="2026-10-03T09:00",
                end_local="2026-10-03T10:00",
            )
        ),
        "public",
    )
    snapshot = phone_snapshot(runtime)
    assert snapshot["items"][0]["title"] == "" and snapshot["items"][0]["redacted"]
    assert snapshot["items"][1]["title"] == "Public review"
    assert "private notes" not in str(snapshot) and "Private appointment" not in str(snapshot)
    assert snapshot["notifications"][0]["at"] == "2026-10-02T12:50:00.000000Z"
    assert snapshot["expires_at"] == "2026-10-02T12:20:00.000000Z"


def test_change_review_resolves_the_requested_occurrence_instead_of_first_series_date(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    event = EventInput(
        title="Weekly review",
        start_local="2026-10-02T15:00",
        end_local="2026-10-02T16:00",
        recurrence={"frequency": "weekly"},
    )
    event_id = runtime.store.create(CreateEvents(event=event), "create")["event_ids"][0]
    proposal = runtime.assistant.tool(
        "calendar_change_draft",
        {
            "event_id": event_id,
            "change": {
                "action": "delete",
                "scope": "occurrence",
                "expected_version": 1,
                "occurrence_key": "2026-10-16T15:00",
            },
        },
        "draft",
    )["proposal"]
    assert proposal["data"]["original"]["start_local"] == "2026-10-16T15:00:00"
    assert proposal["data"]["original"]["end_local"] == "2026-10-16T16:00:00"


def test_phone_reminders_are_bounded_and_do_not_claim_push_synchronization(tmp_path):
    runtime = Runtime(
        Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    )
    for n in range(4):
        runtime.store.create(
            CreateEvents(
                event=EventInput(
                    title="Daily fixture",
                    start_local=f"2026-10-02T{10 + n}:00",
                    end_local=f"2026-10-02T{11 + n}:00",
                    recurrence={"frequency": "daily"},
                    reminder_minutes=[0, 5, 10, 15],
                )
            ),
            f"event-{n}",
        )
    result = phone_snapshot(runtime)
    assert len(result["notifications"]) == 64 and result["notifications_truncated"]
    assert len(result["items"]) == 3
    assert all(not row["sound"] for row in result["notifications"])


def test_model_feedback_stays_a_draft_then_reports_queue_not_physical_success(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    runtime.outputs.heartbeat(
        OutputHeartbeat(
            source="replay", capabilities=["arm"], hardware_verified=True, stopped=False
        )
    )
    runtime.outputs.enable("enable")
    result = runtime.assistant.tool(
        "device_feedback_draft", {"kind": "arm", "preset": "rest"}, "draft"
    )
    assert not runtime.outputs.claim()["commands"]
    confirmed = runtime.assistant.decide(result["proposal"]["id"], "confirm", "confirm")
    assert (
        confirmed["queued"]
        and not confirmed["saved"]
        and not confirmed["physical_completion_confirmed"]
    )
    assert len(runtime.outputs.claim()["commands"]) == 1
    runtime.assistant.tool("stop_physical_outputs", {}, "stop")
    assert runtime.outputs.snapshot()["stopped"]
    with pytest.raises(DomainError):
        runtime.assistant.tool(
            "device_feedback_draft", {"kind": "arm", "preset": "rotate_180"}, "bad"
        )


def test_replay_prompts_cannot_drive_live_outputs(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    runtime.outputs.heartbeat(
        OutputHeartbeat(
            source="live", capabilities=["arm", "light"], hardware_verified=True, stopped=False
        )
    )
    runtime.outputs.enable("enable")
    runtime.on_posture_prompt(
        {"source": "replay", "type": "posture_prompt", "kind": "forward", "created_at": 1}
    )
    assert not runtime.outputs.claim()["commands"]


def test_opposite_side_is_a_mirrored_calibrated_example():
    engine, at, seq = calibrated()
    sample = frame(at, seq, "side")
    mirrored = sample.model_copy(
        update={
            "landmarks": {
                name: point.model_copy(update={"x": 1 - point.x})
                for name, point in sample.landmarks.items()
            }
        }
    )
    vector, reason = features(mirrored)
    assert reason is None and classify(vector, engine.anchors) == "side"


def test_movement_prompt_requires_observed_duration_and_absence_for_reset():
    engine, at, seq = calibrated()
    engine.configure(PosturePreferences(enabled=True, movement_minutes=15))
    events, at, seq = feed(engine, at, seq, seconds=901)
    assert len([e for e in events if e["type"] == "movement_prompt"]) == 1
    assert engine.movement_feedback["source"] == "replay"
    feed(engine, at, seq, seconds=31, brightness=5)
    assert engine.movement_feedback["outcome"] == "notice"
    at += 32
    seq += 130
    events, _, _ = feed(engine, at, seq, seconds=33, person_count=0)
    assert any(e["type"] == "movement_reassessment" for e in events)
    assert engine.movement_feedback["outcome"] == "observed_away"
