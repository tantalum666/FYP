"""Calibrated visible-posture cues, not anatomical or clinical measurements.

The engine consumes timestamped features; camera capture never runs in an API thread.
Unknown observations break persistence and never count as a completed break.
"""

import math
import statistics
from dataclasses import asdict, dataclass, field
from typing import Literal

from pydantic import Field

from .schemas import StrictModel


class Landmark(StrictModel):
    x: float = Field(ge=-0.2, le=1.2, allow_inf_nan=False)
    y: float = Field(ge=-0.2, le=1.2, allow_inf_nan=False)
    visibility: float = Field(ge=0, le=1, allow_inf_nan=False)
    presence: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)


class Observation(StrictModel):
    sequence: int = Field(ge=0)
    captured_ms: int = Field(ge=0)
    camera_id: str = Field(min_length=1, max_length=120)
    frame_width: int = Field(ge=160, le=4096)
    frame_height: int = Field(ge=120, le=4096)
    person_count: int = Field(ge=0, le=10)
    brightness: float = Field(ge=0, le=255, allow_inf_nan=False)
    landmarks: dict[str, Landmark] = Field(default_factory=dict, max_length=33)


class PosturePreferences(StrictModel):
    enabled: bool = False
    persistence_seconds: int = Field(default=15, ge=5, le=120)
    reassess_seconds: int = Field(default=10, ge=5, le=60)
    cooldown_seconds: int = Field(default=180, ge=30, le=3600)
    movement_minutes: int = Field(default=60, ge=15, le=180)
    privacy_when_away: bool = True


class PostureAction(StrictModel):
    action: Literal["configure", "calibrate", "cancel_calibration", "pause", "resume", "snooze"]
    preferences: PosturePreferences | None = None
    pose: Literal["reference", "forward", "side"] | None = None
    minutes: int = Field(default=10, ge=1, le=120)


class ObservationBatch(StrictModel):
    boot_id: str = Field(min_length=8, max_length=80)
    source: Literal["live", "replay"]
    observations: list[Observation] = Field(min_length=1, max_length=20)


SCALES = (0.10, 0.10, 0.08, 0.08, 0.08)
PHASES = ("reference", "forward", "side")


def features(sample: Observation):
    if sample.brightness < 30:
        return None, "too_dark"
    if sample.person_count == 0:
        return None, "absent"
    if sample.person_count != 1:
        return None, "multiple_people"
    required = ["nose", "left_shoulder", "right_shoulder", "left_ear", "right_ear"]
    if any(name not in sample.landmarks for name in required):
        return None, "head_shoulders_not_visible"
    points = [sample.landmarks[name] for name in required]
    if any(min(p.visibility, p.presence) < 0.65 for p in points):
        return None, "low_confidence"
    if any(not (0.025 <= p.x <= 0.975 and 0.025 <= p.y <= 0.975) for p in points):
        return None, "outside_frame"
    nose, left, right, ear_l, ear_r = points
    aspect = sample.frame_width / sample.frame_height
    dx, dy = (left.x - right.x) * aspect, left.y - right.y
    width = math.hypot(dx, dy)
    if width < 0.12 or width > 1.3:
        return None, "unsuitable_distance"
    face = math.hypot((ear_l.x - ear_r.x) * aspect, ear_l.y - ear_r.y)
    vector = [
        (nose.x - (left.x + right.x) / 2) * aspect / width,
        (nose.y - (left.y + right.y) / 2) / width,
        dy / width,
        math.log(width),
        face / width,
    ]
    return vector, None


def distance(a, b):
    return math.sqrt(sum(((x - y) / s) ** 2 for x, y, s in zip(a, b, SCALES)))


def classify(vector, anchors):
    """Same instantaneous classifier is retained as the single-frame baseline."""
    if not all(p in anchors for p in PHASES):
        return "uncalibrated"
    scores = []
    for pose, anchor in anchors.items():
        score = distance(vector, anchor)
        if pose == "side":
            mirrored = list(anchor)
            mirrored[0] = 2 * anchors["reference"][0] - anchor[0]
            mirrored[2] = 2 * anchors["reference"][2] - anchor[2]
            score = min(score, distance(vector, mirrored))
        scores.append((score, pose))
    scores.sort()
    best, name = scores[0]
    if best > 3.5 or scores[1][0] - best < 0.7:
        return "unknown"
    return "within_reference" if name == "reference" else name


@dataclass
class PostureEngine:
    preferences: dict = field(default_factory=lambda: PosturePreferences().model_dump())
    anchors: dict = field(default_factory=dict)
    calibration_version: int = 0
    calibration_source: str | None = None
    camera_signature: str | None = None
    phase: str | None = None
    samples: list = field(default_factory=list)
    phase_start: float | None = None
    phase_result: str | None = None
    last_sequence: int = -1
    boot_id: str | None = None
    source: str | None = None
    last_received: float | None = None
    last_captured: float | None = None
    status: str = "not_connected"
    reason: str | None = None
    candidate: str | None = None
    candidate_since: float | None = None
    feedback: dict | None = None
    movement_feedback: dict | None = None
    recovery_since: float | None = None
    absence_since: float | None = None
    continuous_presence: float = 0
    valid_observed: float = 0
    next_break_at: float = 3600
    cooldown_until: float = 0
    snooze_until: float = 0
    paused: bool = False

    @classmethod
    def restore(cls, value):
        return cls(**{k: v for k, v in value.items() if k in cls.__dataclass_fields__})

    def serialise(self):
        return asdict(self)

    def reset_continuity(self):
        self.candidate = None
        self.candidate_since = None
        self.recovery_since = None
        self.absence_since = None

    def begin_calibration(self, phase):
        if phase not in PHASES:
            raise ValueError("CALIBRATION_POSE_REQUIRED")
        if phase != "reference" and "reference" not in self.anchors:
            raise ValueError("CALIBRATE_REFERENCE_FIRST")
        if phase == "reference":
            self.anchors = {}
            self.camera_signature = None
            self.calibration_source = None
            self.feedback = None
        self.phase = phase
        self.samples = []
        self.phase_start = None
        self.phase_result = None
        self.reset_continuity()

    def configure(self, preferences):
        self.preferences = preferences.model_dump()
        self.next_break_at = self.continuous_presence + preferences.movement_minutes * 60
        self.reset_continuity()

    def ingest(self, observation, now, source, boot_id):
        if self.boot_id == boot_id and observation.sequence <= self.last_sequence:
            return []
        if self.boot_id != boot_id or source != self.source:
            self.reset_continuity()
            self.last_captured = None
            self.last_received = None
            self.samples = []
            self.phase_start = None
        self.boot_id, self.source = boot_id, source
        self.last_sequence = observation.sequence
        captured = observation.captured_ms / 1000
        if abs(now - captured) > 2 or (
            self.last_captured is not None and captured <= self.last_captured
        ):
            self.status, self.reason = "unknown", "stale_or_out_of_order"
            self.reset_continuity()
            return self._finish_reassessment(now)
        previous = self.last_received
        previous_status = self.status
        self.last_received, self.last_captured = now, captured
        delta = min(now - previous, 1) if previous is not None and now - previous <= 2 else 0
        if not delta:
            self.reset_continuity()
        signature = f"{observation.camera_id}/{observation.frame_width}x{observation.frame_height}"
        vector, reason = features(observation)
        if self.paused or not self.preferences["enabled"]:
            self.status, self.reason = "paused", "monitoring_disabled"
            self.reset_continuity()
            return []
        if vector is None:
            self.status, self.reason = ("absent" if reason == "absent" else "unknown"), reason
            self.candidate = None
            self.candidate_since = None
            self.recovery_since = None
            if reason == "absent":
                if self.absence_since is None:
                    self.absence_since = now
                if now - self.absence_since >= 30:
                    self.continuous_presence = 0
                    self.next_break_at = self.preferences["movement_minutes"] * 60
                    if self.movement_feedback and self.movement_feedback["outcome"] == "notice":
                        self.movement_feedback.update(outcome="observed_away", assessed_at=now)
                        return [
                            {"type": "movement_reassessment", **self.movement_feedback},
                            *self._finish_reassessment(now),
                        ]
            else:
                self.absence_since = None
            self.samples = []
            self.phase_start = None
            return self._finish_reassessment(now)
        self.absence_since = None
        if previous_status not in {"unknown", "absent", "not_connected", "paused"}:
            self.valid_observed += delta
            self.continuous_presence += delta
        if self.phase:
            if self.calibration_source and self.calibration_source != source:
                self.anchors = {}
                self.phase_result = "source_changed"
                self.phase = None
                self.status = "uncalibrated"
                return []
            if self.camera_signature and self.camera_signature != signature:
                self.anchors = {}
                self.phase_result = "camera_changed"
                self.phase = None
                self.status = "uncalibrated"
                return []
            self.camera_signature, self.calibration_source = signature, source
            if self.phase_start is None:
                self.phase_start = now
            self.samples.append(vector)
            self.samples = self.samples[-80:]
            self.status, self.reason = "calibrating", None
            if len(self.samples) >= 20 and now - self.phase_start >= 5:
                anchor = [statistics.median(values) for values in zip(*self.samples)]
                spread = statistics.median(distance(v, anchor) for v in self.samples)
                distinct = all(
                    distance(anchor, a) >= 2.4 for p, a in self.anchors.items() if p != self.phase
                )
                if spread > 0.65 or not distinct:
                    self.phase_result = "keep_still" if spread > 0.65 else "poses_not_distinct"
                    self.samples = []
                    self.phase_start = now
                    return []
                self.anchors[self.phase] = anchor
                self.phase_result = self.phase + "_saved"
                self.phase = None
                self.samples = []
                self.calibration_version += 1
                self.status = "within_reference" if len(self.anchors) == 3 else "uncalibrated"
                return [{"type": "calibration_saved", "phase": self.phase_result}]
            return []
        if self.camera_signature != signature or self.calibration_source != source:
            self.status, self.reason = "uncalibrated", "calibration_does_not_match"
            self.reset_continuity()
            return self._finish_reassessment(now)
        instantaneous = classify(vector, self.anchors)
        self.status = instantaneous
        self.reason = "outside_calibrated_examples" if instantaneous == "unknown" else None
        if instantaneous == "within_reference":
            if self.recovery_since is None:
                self.recovery_since = now
        else:
            self.recovery_since = None
        events = self._finish_reassessment(now)
        if instantaneous in {"forward", "side"}:
            if self.candidate != instantaneous:
                self.candidate, self.candidate_since = instantaneous, now
            if (
                now - self.candidate_since >= self.preferences["persistence_seconds"]
                and now >= max(self.cooldown_until, self.snooze_until)
                and not (self.feedback and self.feedback["outcome"] == "waiting")
            ):
                self.feedback = {
                    "kind": instantaneous,
                    "created_at": now,
                    "reassess_at": now + self.preferences["reassess_seconds"],
                    "outcome": "waiting",
                    "calibration_version": self.calibration_version,
                    "source": source,
                }
                self.cooldown_until = now + self.preferences["cooldown_seconds"]
                events.append({"type": "posture_prompt", **self.feedback})
        else:
            self.candidate, self.candidate_since = None, None
        if self.continuous_presence >= self.next_break_at and now >= self.snooze_until:
            self.next_break_at = (
                self.continuous_presence + self.preferences["movement_minutes"] * 60
            )
            self.movement_feedback = {
                "kind": "movement",
                "created_at": now,
                "outcome": "notice",
                "source": source,
                "observed_seconds": self.continuous_presence,
            }
            events.append({"type": "movement_prompt", **self.movement_feedback})
        return events

    def _finish_reassessment(self, now):
        if not self.feedback or self.feedback["outcome"] != "waiting":
            return []
        if now < self.feedback["reassess_at"]:
            return []
        fresh = self.last_received is not None and now - self.last_received <= 2
        if (
            fresh
            and self.status == "within_reference"
            and self.recovery_since is not None
            and now - self.recovery_since >= 2
        ):
            outcome = "adjusted"
        elif (
            fresh
            and self.status in {"forward", "side"}
            and self.candidate_since is not None
            and now - self.candidate_since >= 2
        ):
            outcome = "still_deviated"
        else:
            outcome = "unknown"
        self.feedback["outcome"] = outcome
        self.feedback["assessed_at"] = now
        return [{"type": "posture_reassessment", **self.feedback}]

    def tick(self, now):
        if self.last_received is not None and now - self.last_received > 2:
            self.status, self.reason = "unknown", "camera_stream_lost"
            self.reset_continuity()
        return self._finish_reassessment(now)

    def snapshot(self, now):
        connected = self.last_received is not None and now - self.last_received <= 2
        return {
            "connected": connected,
            "source": self.source,
            "status": self.status
            if connected
            else ("not_connected" if self.last_received is None else "unknown"),
            "reason": self.reason if connected else "camera_stream_lost",
            "preferences": self.preferences,
            "paused": self.paused,
            "calibration": {
                "completed": list(self.anchors),
                "phase": self.phase,
                "samples": len(self.samples),
                "result": self.phase_result,
                "version": self.calibration_version,
                "source": self.calibration_source,
            },
            "candidate_seconds": max(0, now - self.candidate_since)
            if connected and self.candidate_since is not None
            else 0,
            "valid_observed_seconds": round(self.valid_observed),
            "continuous_presence_seconds": round(self.continuous_presence),
            "snooze_until": self.snooze_until,
            "feedback": self.feedback,
            "movement_feedback": self.movement_feedback,
        }
