"""Named, expiring output commands. Queued/claimed is never physical success."""

import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode


class OutputHeartbeat(StrictModel):
    source: Literal["live", "replay"]
    capabilities: list[Literal["light", "arm", "screen_brightness", "speaker"]] = Field(
        default_factory=list, max_length=4
    )
    hardware_verified: bool = False
    stopped: bool = True


class OutputRequest(StrictModel):
    kind: Literal["light", "arm", "screen_brightness", "speaker"]
    preset: str = Field(min_length=1, max_length=40)


class OutputReceipt(StrictModel):
    status: Literal["executed", "failed"]
    detail: Literal[
        "driver_completed", "not_verified", "stopped", "driver_error", "unsupported", "simulation"
    ]


PRESETS = {
    "light": {"off", "attention", "calm"},
    "arm": {"rest", "attention", "point_calendar"},
    "screen_brightness": {"low", "medium", "high"},
    "speaker": {"posture_forward", "posture_side", "movement_break", "next_event"},
}


class OutputService:
    def __init__(self, store):
        self.store = store
        self.heartbeat_data = None
        self.last_seen = None
        self.stop_latched = True
        with store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS output_commands (id TEXT PRIMARY KEY, data TEXT NOT NULL, state TEXT NOT NULL, expires_at TEXT NOT NULL, receipt TEXT)"
            )
            conn.execute(
                "UPDATE output_commands SET state='expired' WHERE state IN ('queued','claimed')"
            )

    def heartbeat(self, payload):
        self.heartbeat_data = payload.model_dump()
        self.last_seen = self.store.clock()
        if payload.stopped:
            self.stop_latched = True
        return self.snapshot()

    def snapshot(self):
        connected = bool(
            self.last_seen and self.store.clock() - self.last_seen <= timedelta(seconds=5)
        )
        return {
            "connected": connected,
            "last_seen": iso(self.last_seen) if self.last_seen else None,
            "source": self.heartbeat_data["source"] if self.heartbeat_data else None,
            "capabilities": self.heartbeat_data["capabilities"] if connected else [],
            "hardware_verified": bool(connected and self.heartbeat_data["hardware_verified"]),
            "stopped": self.stop_latched,
        }

    def emergency_stop(self, key):
        # Latch before any database work: even a busy calendar must not permit new commands.
        self.stop_latched = True

        def apply(conn):
            conn.execute(
                "UPDATE output_commands SET state='cancelled' WHERE state IN ('queued','claimed')"
            )
            self.store.record(conn, "outputs_stopped")
            return {"stopped": True, "physical_stop_confirmed": False}

        return self.store.operation(key, {"type": "outputs_stop"}, apply)

    def enable(self, key):
        state = self.snapshot()
        if (
            not state["connected"]
            or not state["hardware_verified"]
            or self.heartbeat_data["stopped"]
        ):
            raise DomainError("HARDWARE_NOT_READY", 409)

        def apply(conn):
            self.stop_latched = False
            self.store.record(conn, "outputs_enabled", details={"source": state["source"]})
            return {"stopped": False, "source": state["source"]}

        return self.store.operation(key, {"type": "outputs_enable"}, apply)

    def request(self, payload, key):
        if payload.preset not in PRESETS[payload.kind]:
            raise DomainError("PRESET_NOT_ALLOWED", 422)
        state = self.snapshot()
        if not state["connected"] or payload.kind not in state["capabilities"]:
            raise DomainError("HARDWARE_NOT_READY", 409)
        if self.stop_latched or not state["hardware_verified"]:
            raise DomainError("HARDWARE_STOPPED", 409)

        def apply(conn):
            if self.stop_latched or not self.snapshot()["connected"]:
                raise DomainError("HARDWARE_STOPPED", 409)
            command_id = uuid4().hex
            data = {
                **payload.model_dump(),
                "source": state["source"],
                "created_at": iso(self.store.clock()),
            }
            expires = iso(self.store.clock() + timedelta(seconds=5))
            conn.execute(
                "INSERT INTO output_commands VALUES(?,?,'queued',?,NULL)",
                (command_id, encode(data), expires),
            )
            self.store.record(conn, "output_queued", details={"command_id": command_id, **data})
            return {
                "command_id": command_id,
                "state": "queued",
                "expires_at": expires,
                "source": state["source"],
            }

        return self.store.operation(key, {"type": "output_request", **payload.model_dump()}, apply)

    def claim(self):
        with self.store.connection(write=True) as conn:
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE output_commands SET state='expired' WHERE state IN ('queued','claimed') AND expires_at<=?",
                (now,),
            )
            if self.stop_latched or not self.snapshot()["connected"]:
                return {"stopped": True, "commands": []}
            rows = conn.execute(
                "SELECT * FROM output_commands WHERE state='queued' ORDER BY expires_at LIMIT 10"
            ).fetchall()
            for row in rows:
                conn.execute("UPDATE output_commands SET state='claimed' WHERE id=?", (row["id"],))
            return {
                "stopped": False,
                "commands": [
                    {"id": r["id"], "expires_at": r["expires_at"], **json.loads(r["data"])}
                    for r in rows
                ],
            }

    def receipt(self, command_id, payload):
        with self.store.connection(write=True) as conn:
            row = conn.execute("SELECT * FROM output_commands WHERE id=?", (command_id,)).fetchone()
            if not row:
                raise DomainError("COMMAND_NOT_FOUND", 404)
            if row["state"] in {"executed", "failed", "simulated"}:
                if row["receipt"] != encode(payload.model_dump()):
                    raise DomainError("COMMAND_ALREADY_FINISHED", 409)
                return {"state": row["state"]}
            if (
                row["state"] != "claimed"
                or row["expires_at"] <= iso(self.store.clock())
                or self.stop_latched
            ):
                raise DomainError("COMMAND_EXPIRED", 410)
            data = json.loads(row["data"])
            state = "simulated" if data["source"] == "replay" else payload.status
            if data["source"] == "live" and payload.detail == "simulation":
                raise DomainError("SOURCE_MISMATCH", 422)
            conn.execute(
                "UPDATE output_commands SET state=?,receipt=? WHERE id=?",
                (state, encode(payload.model_dump()), command_id),
            )
            self.store.record(
                conn,
                "output_" + state,
                details={"command_id": command_id, **data, "receipt": payload.model_dump()},
            )
            self.store.bump(conn)
            return {"state": state, "source": data["source"]}

    def history(self):
        with self.store.connection() as conn:
            return [
                {
                    "id": r["id"],
                    "state": r["state"],
                    "expires_at": r["expires_at"],
                    **json.loads(r["data"]),
                }
                for r in conn.execute("SELECT * FROM output_commands ORDER BY rowid DESC LIMIT 30")
            ]
