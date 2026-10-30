"""Durable, deterministic responsibilities over local read-only information.

Only definitions, occurrence receipts and delivery state are written here. Skills
cannot call providers, execute scripts, or change tasks, events or computer jobs.
"""

import json
from datetime import UTC, datetime, time, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator, model_validator

from .calendar import expand_all, is_occurrence, iso, wall_to_utc
from .schemas import EventInput, StrictModel
from .store import DomainError, encode

MAX_ROUTINES = 50
MAX_PENDING = 20
HISTORY_PER_ROUTINE = 50


class RoutineInput(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    skill: Literal["day_briefing", "task_review"]
    frequency: Literal["once", "daily", "weekly"]
    start_local: datetime
    timezone: str = "Asia/Hong_Kong"

    @field_validator("title")
    @classmethod
    def title_value(cls, value):
        return EventInput.title_not_blank(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        return EventInput.valid_zone(value)

    @field_validator("start_local")
    @classmethod
    def local(cls, value):
        return EventInput.local_datetime(value)

    @model_validator(mode="after")
    def valid_first_time(self):
        wall_to_utc(self.start_local, self.timezone, reject_ambiguous=True)
        return self


class RoutineAction(StrictModel):
    action: Literal["pause", "resume", "cancel"]
    expected_version: int = Field(ge=1)


class DeliveryClaim(StrictModel):
    limit: int = Field(default=10, ge=1, le=MAX_PENDING)


def occurrence(data, at, *, next_after=False):
    """Find a neighboring occurrence without iterating over a missed backlog.

    A gap in civil time is skipped. A repeated hour uses fold=0 only, as the
    calendar does. Local dates remain anchored rather than adding 24 UTC hours.
    """
    anchor = datetime.fromisoformat(data["start_local"])
    if data["frequency"] == "once":
        due = wall_to_utc(anchor, data["timezone"])
        return (anchor, due) if (due > at if next_after else due <= at) else None
    days = 1 if data["frequency"] == "daily" else 7
    local = at.astimezone(ZoneInfo(data["timezone"])).replace(tzinfo=None)
    index = max(0, (local.date() - anchor.date()).days // days)
    step = 1 if next_after else -1
    # TZDB civil-time gaps can skip a local day. A year is a defensive bound,
    # independent of how long the service was offline.
    for _ in range(370):
        if index < 0:
            return None
        try:
            wall = anchor + timedelta(days=index * days)
        except OverflowError:
            return None
        if wall.year > 2100:
            return None
        try:
            due = wall_to_utc(wall, data["timezone"])
        except ValueError:
            index += step
            continue
        matches = due > at if next_after else due <= at
        if matches:
            return wall, due
        index += step
    return None


class RoutineService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS routines(
                    id TEXT PRIMARY KEY,data TEXT NOT NULL,version INTEGER NOT NULL,
                    status TEXT NOT NULL,next_run_at TEXT,last_scheduled_at TEXT,
                    created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS routines_due ON routines(status,next_run_at);
                CREATE TABLE IF NOT EXISTS routine_runs(
                    id TEXT PRIMARY KEY,routine_id TEXT NOT NULL,
                    occurrence_key TEXT NOT NULL,scheduled_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,result TEXT NOT NULL,
                    delivery_state TEXT NOT NULL,
                    UNIQUE(routine_id,occurrence_key),
                    FOREIGN KEY(routine_id) REFERENCES routines(id));
                CREATE UNIQUE INDEX IF NOT EXISTS routine_one_pending
                    ON routine_runs(routine_id) WHERE delivery_state='pending';
            """)

    @staticmethod
    def view(row):
        return {
            **json.loads(row["data"]),
            **{
                key: row[key]
                for key in (
                    "id",
                    "version",
                    "status",
                    "next_run_at",
                    "last_scheduled_at",
                    "created_at",
                    "updated_at",
                )
            },
        }

    def get(self, conn, routine_id):
        row = conn.execute("SELECT * FROM routines WHERE id=?", (routine_id,)).fetchone()
        if not row:
            raise DomainError("ROUTINE_NOT_FOUND", 404)
        return self.view(row)

    def create(self, payload, key):
        data = payload.model_dump(mode="json")

        def apply(conn):
            if conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0] >= MAX_ROUTINES:
                raise DomainError("ROUTINE_LIMIT", 422)
            now = self.store.clock()
            first = wall_to_utc(payload.start_local, payload.timezone)
            if first <= now:
                raise DomainError("ROUTINE_START_IN_PAST", 422)
            routine_id = uuid4().hex
            conn.execute(
                "INSERT INTO routines VALUES(?,?,1,'active',?,NULL,?,?)",
                (routine_id, encode(data), iso(first), iso(now), iso(now)),
            )
            self.store.record(conn, "routine_created", details={"routine_id": routine_id})
            return {"routine": self.get(conn, routine_id), "saved": True}

        return self.store.operation(key, {"type": "routine_create", "data": data}, apply)

    def action(self, routine_id, payload, key):
        def apply(conn):
            old = self.get(conn, routine_id)
            if old["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if old["status"] in {"cancelled", "completed"}:
                raise DomainError("ROUTINE_CLOSED")
            now = self.store.clock()
            state, next_at = old["status"], old["next_run_at"]
            if payload.action == "pause":
                if state != "active":
                    raise DomainError("ROUTINE_ALREADY_PAUSED")
                state, next_at = "paused", None
            elif payload.action == "cancel":
                state, next_at = "cancelled", None
            else:
                if state != "paused":
                    raise DomainError("ROUTINE_ALREADY_ACTIVE")
                # Paused recurring occurrences are skipped, not replayed on resume.
                # A paused one-off stays due once, even if its original time passed.
                floor = max(
                    now,
                    datetime.fromisoformat(old["last_scheduled_at"])
                    if old["last_scheduled_at"]
                    else now,
                )
                upcoming = occurrence(old, floor, next_after=True)
                if old["frequency"] == "once":
                    upcoming = (
                        None,
                        wall_to_utc(datetime.fromisoformat(old["start_local"]), old["timezone"]),
                    )
                state = "active" if upcoming else "completed"
                next_at = iso(upcoming[1]) if upcoming else None
            conn.execute(
                "UPDATE routines SET version=version+1,status=?,next_run_at=?,updated_at=? "
                "WHERE id=?",
                (state, next_at, iso(now), routine_id),
            )
            if payload.action in {"pause", "cancel"}:
                conn.execute(
                    "UPDATE routine_runs SET delivery_state='dismissed' "
                    "WHERE routine_id=? AND delivery_state='pending'",
                    (routine_id,),
                )
            self.store.record(conn, "routine_" + payload.action, details={"routine_id": routine_id})
            return {"routine": self.get(conn, routine_id), "saved": True}

        return self.store.operation(
            key,
            {"type": "routine_action", "id": routine_id, **payload.model_dump(mode="json")},
            apply,
        )

    def _result(self, conn, routine, now):
        """Persist only source IDs and measured state, never copied user notes."""
        zone = ZoneInfo(routine["timezone"])
        day = now.astimezone(zone).date()
        begin = datetime.combine(day, time.min, zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
        tasks = []
        for row in conn.execute(
            "SELECT * FROM tasks WHERE status IN ('todo','in_progress','waiting')"
        ):
            data = json.loads(row["data"])
            due = (
                wall_to_utc(datetime.fromisoformat(data["due_local"]), data["timezone"])
                if data.get("due_local")
                else None
            )
            if routine["skill"] == "day_briefing" and (due is None or due >= end):
                continue
            tasks.append(
                {
                    "kind": "task",
                    "id": row["id"],
                    "status": row["status"],
                    "due_at": iso(due) if due else None,
                    "overdue": bool(due and due <= now),
                    "visibility": data["visibility"],
                }
            )
        tasks.sort(
            key=lambda task: (
                not task["overdue"],
                task["status"] != "waiting",
                task["due_at"] or "9999",
                task["id"],
            )
        )
        events = []
        if routine["skill"] == "day_briefing":
            definitions, exceptions = self.store.data(conn)
            for item in expand_all(
                definitions, exceptions, begin, end, routine["timezone"], include_conflicts=False
            ):
                if item["completed"] or item["end"] <= iso(now):
                    continue
                events.append(
                    {
                        "kind": "event",
                        "id": item["id"],
                        "start": item["start"],
                        "end": item["end"],
                        "occurrence_key": item["occurrence_key"],
                        "visibility": item["visibility"],
                    }
                )
        return {
            "status": "ready",
            "skill": routine["skill"],
            "source": "local_rules",
            "as_of": iso(now),
            "timezone": routine["timezone"],
            "local_date": day.isoformat(),
            "counts": {
                "events": len(events),
                "tasks": len(tasks),
                "overdue_tasks": sum(t["overdue"] for t in tasks),
                "waiting_tasks": sum(t["status"] == "waiting" for t in tasks),
            },
            "items": events[:20] + tasks[:20],
            "truncated": len(events) > 20 or len(tasks) > 20,
            "suggested_action": "review_calendar_and_tasks"
            if routine["skill"] == "day_briefing"
            else "review_tasks",
        }

    def tick(self):
        now = self.store.clock()
        with self.store.connection(write=True) as conn:
            rows = conn.execute(
                "SELECT * FROM routines WHERE status='active' AND next_run_at<=? "
                "ORDER BY next_run_at,id",
                (iso(now),),
            ).fetchall()
            pending = conn.execute(
                "SELECT COUNT(*) FROM routine_runs WHERE delivery_state='pending'"
            ).fetchone()[0]
            changed = False
            for row in rows:
                routine = self.view(row)
                due = occurrence(routine, now)
                if due is None:
                    continue
                wall, scheduled = due
                next_due = occurrence(routine, now, next_after=True)
                already_pending = conn.execute(
                    "SELECT 1 FROM routine_runs WHERE routine_id=? AND delivery_state='pending'",
                    (routine["id"],),
                ).fetchone()
                delivery = (
                    "pending" if not already_pending and pending < MAX_PENDING else "suppressed"
                )
                try:
                    result = self._result(conn, routine, now)
                except (ValueError, KeyError, TypeError, DomainError):
                    # Invalid legacy source data must not repeatedly block the
                    # scheduler or leak source text through exception strings.
                    result = {
                        "status": "failed",
                        "error_code": "ROUTINE_SOURCE_UNAVAILABLE",
                        "skill": routine["skill"],
                        "source": "local_rules",
                        "as_of": iso(now),
                        "timezone": routine["timezone"],
                        "local_date": now.astimezone(ZoneInfo(routine["timezone"]))
                        .date()
                        .isoformat(),
                        "counts": {"events": 0, "tasks": 0, "overdue_tasks": 0, "waiting_tasks": 0},
                        "items": [],
                        "truncated": False,
                        "suggested_action": "check_local_sources",
                    }
                result["catch_up"] = iso(scheduled) != routine["next_run_at"]
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO routine_runs VALUES(?,?,?,?,?,?,?)",
                    (
                        uuid4().hex,
                        routine["id"],
                        wall.isoformat(timespec="minutes"),
                        iso(scheduled),
                        iso(now),
                        encode(result),
                        delivery,
                    ),
                )
                if cursor.rowcount:
                    pending += int(delivery == "pending")
                    self.store.record(
                        conn,
                        "routine_result",
                        details={"routine_id": routine["id"], "skill": routine["skill"]},
                    )
                conn.execute(
                    "UPDATE routines SET next_run_at=?,last_scheduled_at=?,status=?,updated_at=? "
                    "WHERE id=?",
                    (
                        iso(next_due[1]) if next_due else None,
                        iso(scheduled),
                        "active" if next_due else "completed",
                        iso(now),
                        routine["id"],
                    ),
                )
                # The forward schedule and watermark prevent old replay even after
                # bounded history pruning. Preserve an older pending inbox entry.
                conn.execute(
                    "DELETE FROM routine_runs WHERE routine_id=? AND delivery_state!='pending' "
                    "AND id NOT IN (SELECT id FROM routine_runs WHERE routine_id=? "
                    "ORDER BY scheduled_at DESC LIMIT ?)",
                    (routine["id"], routine["id"], HISTORY_PER_ROUTINE),
                )
                changed = True
            if changed:
                self.store.bump(conn)

    def _run_view(self, conn, row):
        result = json.loads(row["result"])
        hidden = self.store.settings(conn)["hide_private"]
        for item in result["items"]:
            table = "tasks" if item["kind"] == "task" else "events"
            source = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item["id"],)).fetchone()
            current = json.loads(source["data"]) if source else None
            unavailable = source is None or (table == "events" and source["deleted"])
            if current and table == "events":
                exception = conn.execute(
                    "SELECT data FROM exceptions WHERE event_id=? AND occurrence_key=?",
                    (item["id"], item["occurrence_key"]),
                ).fetchone()
                exception = json.loads(exception["data"]) if exception else {}
                unavailable = (
                    unavailable
                    or exception.get("cancelled", False)
                    or not (
                        exception.get("override") or is_occurrence(current, item["occurrence_key"])
                    )
                )
                current = exception.get("override") or current
            private = item["visibility"] == "private" or (
                current and current["visibility"] == "private"
            )
            item["redacted"] = bool(hidden and private)
            item["available"] = not unavailable
            item["title"] = "" if unavailable or item["redacted"] else current["title"]
            item["title_source"] = "current_record"
        return {
            **{
                key: row[key]
                for key in (
                    "id",
                    "routine_id",
                    "occurrence_key",
                    "scheduled_at",
                    "created_at",
                    "delivery_state",
                )
            },
            "result": result,
        }

    def listing(self):
        with self.store.connection() as conn:
            items = [
                self.view(row)
                for row in conn.execute("SELECT * FROM routines ORDER BY created_at DESC,id")
            ]
            return {
                "routines": items,
                "pending_count": conn.execute(
                    "SELECT COUNT(*) FROM routine_runs WHERE delivery_state='pending'"
                ).fetchone()[0],
                "revision": self.store.revision(conn),
                "server_time": iso(self.store.clock()),
                "limits": {"routines": MAX_ROUTINES, "pending_deliveries": MAX_PENDING},
            }

    def detail(self, routine_id):
        with self.store.connection() as conn:
            return {
                "routine": self.get(conn, routine_id),
                "runs": [
                    self._run_view(conn, row)
                    for row in conn.execute(
                        "SELECT * FROM routine_runs WHERE routine_id=? "
                        "ORDER BY scheduled_at DESC LIMIT ?",
                        (routine_id, HISTORY_PER_ROUTINE),
                    )
                ],
                "revision": self.store.revision(conn),
            }

    def claim(self, payload, key):
        def apply(conn):
            rows = conn.execute(
                "SELECT id,routine_id FROM routine_runs WHERE delivery_state='pending' "
                "ORDER BY scheduled_at,id LIMIT ?",
                (payload.limit,),
            ).fetchall()
            ids = [row["id"] for row in rows]
            references = [
                {
                    "delivery_id": row["id"],
                    "run_id": conn.execute(
                        "SELECT id FROM routine_runs WHERE routine_id=? "
                        "ORDER BY scheduled_at DESC LIMIT 1",
                        (row["routine_id"],),
                    ).fetchone()[0],
                }
                for row in rows
            ]
            conn.executemany(
                "UPDATE routine_runs SET delivery_state='claimed' WHERE id=?",
                [(i,) for i in ids],
            )
            # Store only stable IDs in idempotency replies. Privacy is reapplied
            # below even when the same request is retried after settings change.
            return {"delivery_ids": ids, "delivery_refs": references, "claimed": len(ids)}

        response = self.store.operation(
            key,
            {"type": "routine_delivery_claim", **payload.model_dump(mode="json")},
            apply,
        )
        with self.store.connection() as conn:
            deliveries = []
            unavailable = []
            for reference in response["delivery_refs"]:
                row = conn.execute(
                    "SELECT * FROM routine_runs WHERE id=?",
                    (reference["run_id"],),
                ).fetchone()
                if row:
                    deliveries.append(
                        {
                            **self._run_view(conn, row),
                            "id": reference["delivery_id"],
                            "result_run_id": row["id"],
                            "delivery_state": "claimed",
                            "coalesced_delivery": reference["delivery_id"] != row["id"],
                        }
                    )
                else:
                    unavailable.append(reference["delivery_id"])
            return {**response, "deliveries": deliveries, "unavailable_delivery_ids": unavailable}


def routine_routes(runtime, owner, operation_id):
    def visible_owner(principal=Depends(owner)):
        runtime.personal_context.require_visible(principal)

    router = APIRouter(prefix="/api/routines", dependencies=[Depends(visible_owner)])

    @router.get("")
    def listing():
        return runtime.routines.listing()

    @router.post("")
    def create(payload: RoutineInput, key=Depends(operation_id)):
        return runtime.routines.create(payload, key)

    @router.post("/deliveries/claim")
    def claim(payload: DeliveryClaim, key=Depends(operation_id)):
        return runtime.routines.claim(payload, key)

    @router.get("/{routine_id}")
    def detail(routine_id: str):
        return runtime.routines.detail(routine_id)

    @router.post("/{routine_id}/actions")
    def action(routine_id: str, payload: RoutineAction, key=Depends(operation_id)):
        return runtime.routines.action(routine_id, payload, key)

    return router
