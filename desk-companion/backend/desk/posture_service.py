"""Persist calibration, latest state and event history without storing camera frames."""

import json
import threading

from .calendar import iso
from .posture import PostureEngine
from .store import DomainError, encode


class PostureService:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        with store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS posture_state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)"
            )
            row = conn.execute("SELECT data FROM posture_state WHERE id=1").fetchone()
        self.engine = PostureEngine.restore(json.loads(row[0])) if row else PostureEngine()
        # Calibration survives a restart; temporal evidence and motion never do.
        self.engine.reset_continuity()
        self.engine.last_received = None
        self.engine.last_captured = None
        self.engine.last_sequence = -1
        self.engine.boot_id = None
        self.engine.samples = []
        self.engine.phase = None
        self.engine.status = "not_connected"
        self.engine.feedback = None
        self.engine.movement_feedback = None
        self.engine.continuous_presence = 0
        self.engine.next_break_at = self.engine.preferences["movement_minutes"] * 60
        self.on_prompt = None

    def _save(self, conn):
        conn.execute(
            "INSERT INTO posture_state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (encode(self.engine.serialise()),),
        )

    def snapshot(self):
        with self.lock:
            return self.engine.snapshot(self.store.clock().timestamp())

    def action(self, payload, key):
        with self.lock:
            before = self.engine.serialise()

            def apply(conn):
                engine = self.engine
                if payload.action == "configure":
                    if payload.preferences is None:
                        raise DomainError("PREFERENCES_REQUIRED", 422)
                    engine.configure(payload.preferences)
                elif payload.action == "calibrate":
                    if not engine.preferences["enabled"] or engine.paused:
                        raise DomainError("ENABLE_MONITORING_FIRST", 409)
                    try:
                        engine.begin_calibration(payload.pose)
                    except ValueError as e:
                        raise DomainError(str(e), 422) from None
                elif payload.action == "cancel_calibration":
                    engine.phase = None
                    engine.samples = []
                    engine.phase_start = None
                    engine.phase_result = "cancelled"
                elif payload.action == "pause":
                    engine.paused = True
                    engine.status = "paused"
                    engine.reset_continuity()
                elif payload.action == "resume":
                    engine.paused = False
                    engine.reset_continuity()
                elif payload.action == "snooze":
                    engine.snooze_until = self.store.clock().timestamp() + payload.minutes * 60
                self._save(conn)
                self.store.record(
                    conn, "posture_" + payload.action, details={"source": engine.source}
                )
                return {"posture": engine.snapshot(self.store.clock().timestamp())}

            try:
                return self.store.operation(
                    key, {"type": "posture_action", **payload.model_dump(mode="json")}, apply
                )
            except Exception:
                self.engine = PostureEngine.restore(before)
                raise

    def ingest(self, batch):
        with self.lock:
            before = self.engine.serialise()
            emitted = []
            try:
                now = self.store.clock().timestamp()
                for observation in batch.observations:
                    emitted.extend(
                        self.engine.ingest(observation, now, batch.source, batch.boot_id)
                    )
                with self.store.connection(write=True) as conn:
                    self._save(conn)
                    for event in emitted:
                        self.store.record(
                            conn,
                            event["type"],
                            details={
                                **event,
                                "source": batch.source,
                                "at": iso(self.store.clock()),
                            },
                        )
                    if emitted or (before["status"], before["source"]) != (
                        self.engine.status,
                        self.engine.source,
                    ):
                        self.store.bump(conn)
            except Exception:
                self.engine = PostureEngine.restore(before)
                raise
            if self.on_prompt:
                for event in emitted:
                    if event["type"] in {"posture_prompt", "movement_prompt"}:
                        self.on_prompt(event)
            return {
                "accepted_sequence": self.engine.last_sequence,
                "posture": self.engine.snapshot(now),
            }

    def tick(self):
        with self.lock:
            before_status = self.engine.status
            emitted = self.engine.tick(self.store.clock().timestamp())
            if emitted or before_status != self.engine.status:
                with self.store.connection(write=True) as conn:
                    self._save(conn)
                    for event in emitted:
                        self.store.record(conn, event["type"], details=event)
                    self.store.bump(conn)
            return emitted
