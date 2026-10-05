from datetime import UTC, datetime

import pytest

from desk.posture import Observation, PostureEngine, PosturePreferences, classify, features
from desk.posture_service import PostureService
from desk.store import Store


def frame(at, sequence, pose="reference", **updates):
    coordinates = {
        "reference": [(0.5, 0.30), (0.4, 0.60), (0.6, 0.60), (0.45, 0.32), (0.55, 0.32)],
        "forward": [(0.5, 0.39), (0.37, 0.60), (0.63, 0.60), (0.43, 0.40), (0.57, 0.40)],
        "side": [(0.58, 0.30), (0.4, 0.60), (0.6, 0.60), (0.53, 0.32), (0.63, 0.32)],
    }[pose]
    return Observation.model_validate(
        {
            "sequence": sequence,
            "captured_ms": int(at * 1000),
            "camera_id": "fixture-camera",
            "frame_width": 640,
            "frame_height": 480,
            "person_count": 1,
            "brightness": 110,
            "landmarks": {
                name: {"x": p[0], "y": p[1], "visibility": 0.98}
                for name, p in zip(
                    ["nose", "left_shoulder", "right_shoulder", "left_ear", "right_ear"],
                    coordinates,
                )
            },
            **updates,
        }
    )


def calibrated():
    e = PostureEngine()
    e.configure(
        PosturePreferences(
            enabled=True, persistence_seconds=5, reassess_seconds=5, cooldown_seconds=30
        )
    )
    at, sequence = 1000.0, 0
    for pose in ["reference", "forward", "side"]:
        e.begin_calibration(pose)
        for _ in range(22):
            e.ingest(frame(at, sequence, pose), at, "replay", "fixture-boot")
            at += 0.25
            sequence += 1
    assert len(e.anchors) == 3
    return e, at, sequence


def feed(e, at, sequence, pose="reference", seconds=1, **updates):
    events = []
    for _ in range(int(seconds * 4)):
        events.extend(e.ingest(frame(at, sequence, pose, **updates), at, "replay", "fixture-boot"))
        at += 0.25
        sequence += 1
    return events, at, sequence


def test_cannot_calibrate_secondary_pose_without_reference():
    with pytest.raises(ValueError, match="CALIBRATE_REFERENCE_FIRST"):
        PostureEngine().begin_calibration("forward")


def test_calibration_requires_visible_continuous_distinct_examples():
    e = PostureEngine(preferences=PosturePreferences(enabled=True).model_dump())
    e.begin_calibration("reference")
    for i in range(30):
        e.ingest(frame(1000 + i / 4, i, person_count=2), 1000 + i / 4, "replay", "boot-one")
    assert not e.anchors and not e.samples
    e, at, seq = calibrated()
    e.anchors.pop("forward")
    e.begin_calibration("forward")
    feed(e, at, seq, "reference", seconds=6)
    assert "forward" not in e.anchors
    assert e.phase_result == "poses_not_distinct"


def test_brief_movement_does_not_alert_but_persistent_movement_does():
    e, at, seq = calibrated()
    vector, _ = features(frame(at, seq, "forward"))
    assert classify(vector, e.anchors) == "forward"  # Baseline triggers immediately.
    short, at, seq = feed(e, at, seq, "forward", seconds=3)
    assert not any(x["type"] == "posture_prompt" for x in short)
    _, at, seq = feed(e, at, seq, seconds=1)
    sustained, at, seq = feed(e, at, seq, "forward", seconds=6)
    assert len([x for x in sustained if x["type"] == "posture_prompt"]) == 1
    assert e.feedback["outcome"] == "waiting"


def test_adjustment_requires_new_sustained_observations():
    e, at, seq = calibrated()
    _, at, seq = feed(e, at, seq, "side", seconds=6)
    result, at, seq = feed(e, at, seq, seconds=6)
    assert [x["outcome"] for x in result if x["type"] == "posture_reassessment"] == ["adjusted"]
    extra, _, _ = feed(e, at, seq, "side", seconds=10)
    assert not any(x["type"] == "posture_prompt" for x in extra)


def test_no_frames_after_prompt_becomes_unknown_not_adjusted():
    e, at, seq = calibrated()
    _, at, seq = feed(e, at, seq, "forward", seconds=6)
    result = e.tick(at + 8)
    assert result[0]["outcome"] == "unknown"
    assert e.snapshot(at + 8)["status"] == "unknown"


def test_occlusion_breaks_persistence_and_does_not_reset_presence_as_a_break():
    e, at, seq = calibrated()
    _, at, seq = feed(e, at, seq, "forward", seconds=4)
    presence = e.continuous_presence
    _, at, seq = feed(e, at, seq, seconds=35, brightness=5)
    assert e.continuous_presence == presence
    result, _, _ = feed(e, at, seq, "forward", seconds=4)
    assert not any(x["type"] == "posture_prompt" for x in result)


def test_confirmed_absence_resets_duration_but_not_just_one_frame():
    e, at, seq = calibrated()
    _, at, seq = feed(e, at, seq, seconds=20)
    presence = e.continuous_presence
    _, at, seq = feed(e, at, seq, seconds=3, person_count=0)
    assert e.continuous_presence == presence
    feed(e, at, seq, seconds=32, person_count=0)
    assert e.continuous_presence == 0


def test_duplicate_stale_and_different_camera_cannot_generate_a_prompt():
    e, at, seq = calibrated()
    e.ingest(frame(at, seq, "forward"), at, "replay", "fixture-boot")
    assert e.ingest(frame(at, seq, "forward"), at + 20, "replay", "fixture-boot") == []
    e.tick(at + 20)
    assert e.status == "unknown"
    e.ingest(frame(at, seq + 1, "forward"), at + 20, "replay", "fixture-boot")
    assert e.reason == "stale_or_out_of_order"
    e.ingest(frame(at + 21, seq + 2, camera_id="moved-camera"), at + 21, "replay", "fixture-boot")
    assert e.status == "uncalibrated"


def test_replay_calibration_is_not_accepted_for_live_input():
    e, at, seq = calibrated()
    e.ingest(frame(at, seq), at, "live", "live-boot")
    assert e.status == "uncalibrated"


def test_pause_snooze_and_restart_do_not_replay_feedback(tmp_path):
    e, at, seq = calibrated()
    e.snooze_until = at + 60
    result, at, seq = feed(e, at, seq, "forward", seconds=20)
    assert not result
    store = Store(tmp_path, password="fixture-only", clock=lambda: datetime.fromtimestamp(at, UTC))
    service = PostureService(store)
    service.engine = e
    with store.connection(write=True) as conn:
        service._save(conn)
    restored = PostureService(store)
    assert len(restored.engine.anchors) == 3
    assert restored.snapshot()["status"] == "not_connected"
    assert restored.snapshot()["feedback"] is None
