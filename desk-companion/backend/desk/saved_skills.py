"""Owner-saved checklists. A passed check becomes one immutable skill.

Preparing a run stores the fill and stays pending. Only the owner's decision
writes a local result. Steps and input values are data: nothing here starts a
tool, a model call, mail, a purchase, or a booking. Omitted fields are not
defaults that overwrite or approve.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Callable, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator, model_validator

from .calendar import iso, wall_to_utc
from .routines import occurrence
from .schemas import EventInput, StrictModel
from .store import DomainError, encode
from .workspace_data import WorkspacePreferences, is_quiet

_NAME = re.compile(r"^[^\W\d_][\w]{0,31}$")
_ID = re.compile(r"^[0-9a-f]{32}$")
CHECK_LIMIT = 40
SKILL_LIMIT = 40
RUN_LIMIT = 100
SCHEDULE_LIMIT = 20
OCCURRENCE_WINDOW_SECONDS = 120
OCCURRENCE_HISTORY = 20
_OWNER = {"kind": "owner", "id": "owner", "name": "Owner"}


def _hash(body: dict) -> str:
    return hashlib.sha256(encode(body).encode()).hexdigest()


def _loads(value: str):
    return json.loads(value)


class CheckInput(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    steps: list[str] = Field(min_length=1, max_length=6)
    input_names: list[str] = Field(min_length=1, max_length=6)
    validation: str = "required_inputs"
    passed: bool | None = None

    @field_validator("title")
    @classmethod
    def title_text(cls, value: str) -> str:
        text = value.strip()
        if not text or len(text) > 160 or any(ord(ch) < 32 for ch in text):
            raise ValueError("title")
        return text

    @field_validator("steps")
    @classmethod
    def step_text(cls, value: list[str]) -> list[str]:
        steps = []
        for raw in value:
            text = raw.strip()
            if not text or len(text) > 120 or any(ord(ch) < 32 for ch in text):
                raise ValueError("step")
            steps.append(text)
        return steps

    @field_validator("input_names")
    @classmethod
    def names(cls, value: list[str]) -> list[str]:
        names = []
        for raw in value:
            name = raw.strip()
            if not _NAME.fullmatch(name) or name in names:
                raise ValueError("input name")
            names.append(name)
        return names

    @field_validator("validation")
    @classmethod
    def known_validation(cls, value: str) -> str:
        if value != "required_inputs":
            raise ValueError("validation")
        return value


class RunPrepare(StrictModel):
    inputs: dict[str, str]
    note: str | None = Field(default=None, max_length=280)


class RunDecision(StrictModel):
    action: str
    expected_version: int = Field(ge=1, le=1_000_000)
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("action")
    @classmethod
    def known_action(cls, value: str) -> str:
        if value not in {"approve", "reject"}:
            raise ValueError("action")
        return value


class ScheduleInput(StrictModel):
    frequency: Literal["once", "daily", "weekly"]
    start_local: datetime
    timezone: str = "Asia/Hong_Kong"
    inputs: dict[str, str]
    note: str | None = Field(default=None, max_length=280)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value: str) -> str:
        return EventInput.valid_zone(value)

    @field_validator("start_local")
    @classmethod
    def local(cls, value: datetime) -> datetime:
        return EventInput.local_datetime(value)

    @model_validator(mode="after")
    def valid_first_time(self):
        wall_to_utc(self.start_local, self.timezone, reject_ambiguous=True)
        return self


class ScheduleAction(StrictModel):
    action: Literal["pause", "resume", "cancel"]
    expected_version: int = Field(ge=1, le=1_000_000)


class SavedSkillService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        self._before_commit: Callable | None = None
        with self.store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skill_checks(
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    input_names TEXT NOT NULL,
                    validation TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    skill_id TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skills(
                    id TEXT PRIMARY KEY,
                    check_id TEXT NOT NULL UNIQUE,
                    version INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    input_names TEXT NOT NULL,
                    validation TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skill_runs(
                    id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    skill_version INTEGER NOT NULL,
                    inputs TEXT NOT NULL,
                    note TEXT,
                    note_provided INTEGER NOT NULL,
                    input_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skill_operations(
                    id TEXT PRIMARY KEY,
                    body_hash TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(saved_skill_runs)")}
            if "origin" not in columns:
                conn.execute(
                    "ALTER TABLE saved_skill_runs ADD COLUMN origin TEXT NOT NULL DEFAULT 'owner'"
                )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skill_schedules(
                    id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    skill_version INTEGER NOT NULL,
                    frequency TEXT NOT NULL,
                    start_local TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    inputs TEXT NOT NULL,
                    note TEXT,
                    note_provided INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    next_run_at TEXT,
                    last_scheduled_at TEXT,
                    last_outcome TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE INDEX IF NOT EXISTS saved_skill_schedules_due
                   ON saved_skill_schedules(status, next_run_at)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS saved_skill_occurrences(
                    id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    occurrence_key TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    run_id TEXT,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(schedule_id, occurrence_key),
                    FOREIGN KEY(schedule_id) REFERENCES saved_skill_schedules(id)
                )"""
            )

    def record_check(self, payload: CheckInput, key: str, session: str | None) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if payload.passed is None:
            raise DomainError("CHECK_NOT_PASSED", 422)
        body = _hash(payload.model_dump(mode="json"))
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            replay = self._replay(conn, key, body)
            if replay:
                check_id = replay
            else:
                self._room_for_check(conn)
                if payload.passed:
                    self._room_for_skill(conn)
                check_id = uuid4().hex
                now = iso(self.store.clock())
                conn.execute(
                    "INSERT INTO saved_skill_checks VALUES(?,?,?,?,?,?,NULL,?)",
                    (
                        check_id,
                        payload.title,
                        encode(payload.steps),
                        encode(payload.input_names),
                        payload.validation,
                        1 if payload.passed else 0,
                        now,
                    ),
                )
                if payload.passed:
                    self._insert_skill(conn, check_id, now)
                self._remember(conn, key, body, "check", check_id)
                self.store.record(conn, "skill_check_recorded", details={"check_id": check_id})
                self.store.bump(conn)
                self._barrier(conn)
        return self._check_response(check_id, key, replayed=replay is not None)

    def save_check(self, check_id: str, key: str, session: str | None) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(check_id):
            raise DomainError("CHECK_NOT_FOUND", 404)
        body = _hash({"check_id": check_id})
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            replay = self._replay(conn, key, body)
            if replay:
                skill_id = replay
            else:
                check = self._check(conn, check_id)
                if not check["passed"]:
                    raise DomainError("CHECK_NOT_PASSED", 422)
                if check["skill_id"]:
                    skill_id = check["skill_id"]
                else:
                    self._room_for_skill(conn)
                    skill_id = self._insert_skill(conn, check_id, iso(self.store.clock()))
                self._remember(conn, key, body, "save", skill_id)
                self.store.record(conn, "skill_saved", details={"skill_id": skill_id})
                self.store.bump(conn)
                self._barrier(conn)
        return self._skill_response(skill_id, key, replayed=replay is not None)

    def prepare_run(
        self, skill_id: str, payload: RunPrepare, key: str, session: str | None
    ) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(skill_id):
            raise DomainError("SKILL_NOT_FOUND", 404)
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            skill = self._skill(conn, skill_id)
            provided, note = self._note(payload)
            inputs = self._inputs(skill["input_names"], payload.inputs)
            canonical = {
                "skill_id": skill_id,
                "inputs": inputs,
                "note_provided": provided,
            }
            if provided:
                canonical["note"] = note
            body = _hash(canonical)
            replay = self._replay(conn, key, body)
            if replay:
                run_id = replay
            else:
                count = conn.execute("SELECT COUNT(*) FROM saved_skill_runs").fetchone()[0]
                if count >= RUN_LIMIT:
                    raise DomainError("RUN_LIMIT", 422)
                run_id = uuid4().hex
                now = iso(self.store.clock())
                self._insert_run(
                    conn,
                    run_id,
                    skill_id,
                    skill["version"],
                    inputs,
                    note,
                    provided,
                    body,
                    now,
                    "owner",
                )
                self._remember(conn, key, body, "run", run_id)
                self.store.record(
                    conn, "skill_run_prepared", details={"run_id": run_id, "skill_id": skill_id}
                )
                self.store.bump(conn)
                self._barrier(conn)
        return self._run_response(run_id, key, replayed=replay is not None)

    def decide(self, run_id: str, payload: RunDecision, key: str, session: str | None) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(run_id):
            raise DomainError("RUN_NOT_FOUND", 404)
        body = _hash(payload.model_dump(mode="json"))
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            replay = self._replay(conn, key, body)
            if replay:
                if replay != run_id:
                    raise DomainError("OPERATION_ID_CONFLICT", 409)
                run_id = replay
            else:
                run = self._run(conn, run_id)
                if run["status"] != "pending":
                    raise DomainError("RUN_CLOSED", 409)
                if run["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
                if run["input_hash"] != payload.input_hash:
                    raise DomainError("SKILL_INPUT_CHANGED", 409)
                now = iso(self.store.clock())
                if payload.action == "reject":
                    conn.execute(
                        "UPDATE saved_skill_runs SET status='rejected', version=version+1, "
                        "updated_at=? WHERE id=?",
                        (now, run_id),
                    )
                    action = "skill_run_rejected"
                else:
                    skill = self._skill(conn, run["skill_id"])
                    self._inputs(skill["input_names"], run["inputs"])
                    result = {
                        "basis": "owner_approved_local_check",
                        "system_verified": False,
                        "external_receipt": False,
                        "validation": skill["validation"],
                        "steps_checked": skill["steps"],
                        "inputs": run["inputs"],
                        "note_provided": run["note_provided"],
                    }
                    if run["note_provided"]:
                        result["note"] = run["note"]
                    conn.execute(
                        "UPDATE saved_skill_runs SET status='succeeded', version=version+1, "
                        "result=?, updated_at=? WHERE id=?",
                        (encode(result), now, run_id),
                    )
                    action = "skill_run_approved"
                self._remember(conn, key, body, "decision", run_id)
                self.store.record(conn, action, details={"run_id": run_id})
                self.store.bump(conn)
                self._barrier(conn)
        return self._run_response(run_id, key, replayed=replay is not None)

    def schedule(
        self, skill_id: str, payload: ScheduleInput, key: str, session: str | None
    ) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(skill_id):
            raise DomainError("SKILL_NOT_FOUND", 404)
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            skill = self._skill(conn, skill_id)
            provided, note = self._note(payload)
            inputs = self._inputs(skill["input_names"], payload.inputs)
            start_local = payload.start_local.isoformat(timespec="minutes")
            canonical = {
                "skill_id": skill_id,
                "frequency": payload.frequency,
                "start_local": start_local,
                "timezone": payload.timezone,
                "inputs": inputs,
                "note_provided": provided,
            }
            if provided:
                canonical["note"] = note
            body = _hash(canonical)
            replay = self._replay(conn, key, body)
            if replay:
                schedule_id = replay
            else:
                first = wall_to_utc(payload.start_local, payload.timezone)
                if first <= self.store.clock():
                    raise DomainError("SCHEDULE_START_IN_PAST", 422)
                count = conn.execute("SELECT COUNT(*) FROM saved_skill_schedules").fetchone()[0]
                if count >= SCHEDULE_LIMIT:
                    raise DomainError("SCHEDULE_LIMIT", 422)
                schedule_id = uuid4().hex
                now = iso(self.store.clock())
                conn.execute(
                    """INSERT INTO saved_skill_schedules(
                        id, skill_id, skill_version, frequency, start_local, timezone,
                        inputs, note, note_provided, version, status, next_run_at,
                        last_scheduled_at, last_outcome, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,1,'active',?,NULL,NULL,?,?)""",
                    (
                        schedule_id,
                        skill_id,
                        skill["version"],
                        payload.frequency,
                        start_local,
                        payload.timezone,
                        encode(inputs),
                        note,
                        1 if provided else 0,
                        iso(first),
                        now,
                        now,
                    ),
                )
                self._remember(conn, key, body, "schedule", schedule_id)
                self.store.record(
                    conn,
                    "skill_schedule_saved",
                    details={"schedule_id": schedule_id, "skill_id": skill_id},
                )
                self.store.bump(conn)
                self._barrier(conn)
        return self._schedule_response(schedule_id, key, replayed=replay is not None)

    def schedule_action(
        self, schedule_id: str, payload: ScheduleAction, key: str, session: str | None
    ) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(schedule_id):
            raise DomainError("SCHEDULE_NOT_FOUND", 404)
        body = _hash({"schedule_id": schedule_id, **payload.model_dump(mode="json")})
        with self.store.connection(write=True) as conn:
            self._assert_open(conn, session)
            replay = self._replay(conn, key, body)
            if replay:
                if replay != schedule_id:
                    raise DomainError("OPERATION_ID_CONFLICT", 409)
            else:
                schedule = self._schedule(conn, schedule_id)
                if schedule["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
                if schedule["status"] in {"cancelled", "completed"}:
                    raise DomainError("SCHEDULE_CLOSED", 409)
                now = self.store.clock()
                status, next_at = schedule["status"], schedule["next_run_at"]
                if payload.action == "pause":
                    if status != "active":
                        raise DomainError("SCHEDULE_ALREADY_PAUSED", 409)
                    status, next_at = "paused", None
                elif payload.action == "cancel":
                    status, next_at = "cancelled", None
                else:
                    if status != "paused":
                        raise DomainError("SCHEDULE_ALREADY_ACTIVE", 409)
                    upcoming = self._resume_at(schedule, now)
                    status = "active" if upcoming else "completed"
                    next_at = iso(upcoming) if upcoming else None
                conn.execute(
                    "UPDATE saved_skill_schedules SET version=version+1, status=?, "
                    "next_run_at=?, updated_at=? WHERE id=?",
                    (status, next_at, iso(now), schedule_id),
                )
                self._remember(conn, key, body, "schedule_action", schedule_id)
                self.store.record(
                    conn,
                    "skill_schedule_" + payload.action,
                    details={"schedule_id": schedule_id},
                )
                self.store.bump(conn)
                self._barrier(conn)
        return self._schedule_response(schedule_id, key, replayed=replay is not None)

    def release_due(self, conn) -> bool:
        """Prepare or skip due schedules on the routine clock.

        The caller owns the write transaction and the revision bump. An
        occurrence outside the short window is missed. Quiet hours and
        proactive off consume the occurrence as well. Neither case prepares
        a run later.
        """
        now = self.store.clock()
        rows = conn.execute(
            "SELECT * FROM saved_skill_schedules WHERE status='active' AND next_run_at<=? "
            "ORDER BY next_run_at, id",
            (iso(now),),
        ).fetchall()
        if not rows:
            return False
        prefs = self._preferences(conn)
        local_now = now.astimezone(ZoneInfo(self.store.settings(conn)["timezone"]))
        proactive_off = prefs.get("proactivity") == "off"
        quiet = is_quiet(prefs, local_now)
        changed = False
        for row in rows:
            schedule = self._schedule_row(row)
            try:
                changed = self._release_one(conn, schedule, now, proactive_off, quiet) or changed
            except (ValueError, KeyError, TypeError, OverflowError):
                self._stop_schedule(conn, schedule["id"], now, "skipped_invalid")
                changed = True
        return changed

    def listing(self, session: str | None) -> dict:
        self._gate(session)
        with self.store.connection() as conn:
            self._assert_open(conn, session)
            rows = conn.execute(
                "SELECT id FROM saved_skills ORDER BY created_at DESC, id DESC"
            ).fetchall()
            skills = [self._skill(conn, row["id"]) for row in rows]
            revision = self.store.revision(conn)
        return {"skills": skills, "revision": revision, "limits": {"skills": SKILL_LIMIT}}

    def detail(self, skill_id: str, session: str | None) -> dict:
        self._gate(session)
        if not _ID.fullmatch(skill_id):
            raise DomainError("SKILL_NOT_FOUND", 404)
        with self.store.connection() as conn:
            self._assert_open(conn, session)
            skill = self._skill(conn, skill_id)
            rows = conn.execute(
                "SELECT id FROM saved_skill_runs WHERE skill_id=? "
                "ORDER BY created_at DESC, id DESC LIMIT 20",
                (skill_id,),
            ).fetchall()
            runs = [self._run(conn, row["id"]) for row in rows]
            schedules = [
                self._schedule_row(row)
                for row in conn.execute(
                    "SELECT * FROM saved_skill_schedules WHERE skill_id=? "
                    "ORDER BY created_at DESC, id DESC",
                    (skill_id,),
                )
            ]
        return {"skill": skill, "runs": runs, "schedules": schedules}

    def _gate(self, session: str | None) -> None:
        if not session or not self.store.session_valid(session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible({**_OWNER, "session": session})

    def _assert_open(self, conn, session) -> None:
        self.runtime.personal_context.require_owner_transaction(
            conn, {**_OWNER, "session": session}
        )

    def _require_key(self, key: str) -> str:
        if not isinstance(key, str) or not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        if key.startswith("assistant-confirm/"):
            raise DomainError("RESERVED_OPERATION_ID", 422)
        return key

    def _replay(self, conn, key: str, body: str) -> str | None:
        row = conn.execute(
            "SELECT body_hash, resource_id FROM saved_skill_operations WHERE id=?",
            (key,),
        ).fetchone()
        if not row:
            return None
        if row["body_hash"] != body:
            raise DomainError("OPERATION_ID_CONFLICT", 409)
        return row["resource_id"]

    def _remember(self, conn, key: str, body: str, kind: str, resource_id: str) -> None:
        conn.execute(
            "INSERT INTO saved_skill_operations VALUES(?,?,?,?,?)",
            (key, body, kind, resource_id, iso(self.store.clock())),
        )

    def _room_for_check(self, conn) -> None:
        if conn.execute("SELECT COUNT(*) FROM saved_skill_checks").fetchone()[0] >= CHECK_LIMIT:
            raise DomainError("SKILL_LIMIT", 422)

    def _room_for_skill(self, conn) -> None:
        if conn.execute("SELECT COUNT(*) FROM saved_skills").fetchone()[0] >= SKILL_LIMIT:
            raise DomainError("SKILL_LIMIT", 422)

    def _insert_skill(self, conn, check_id: str, now: str) -> str:
        check = self._check(conn, check_id)
        skill_id = uuid4().hex
        conn.execute(
            "INSERT INTO saved_skills VALUES(?,?,1,?,?,?,?,?)",
            (
                skill_id,
                check_id,
                check["title"],
                encode(check["steps"]),
                encode(check["input_names"]),
                check["validation"],
                now,
            ),
        )
        conn.execute("UPDATE saved_skill_checks SET skill_id=? WHERE id=?", (skill_id, check_id))
        return skill_id

    def _note(self, payload: RunPrepare | ScheduleInput) -> tuple[bool, str | None]:
        if "note" not in payload.model_fields_set:
            return False, None
        if payload.note is None or not payload.note.strip():
            raise DomainError("SKILL_NOTE_EMPTY", 422)
        text = payload.note.strip()
        if len(text) > 280 or any(ord(ch) < 32 for ch in text):
            raise DomainError("SKILL_NOTE_EMPTY", 422)
        return True, text

    def _inputs(self, names: list[str], provided: dict) -> dict[str, str]:
        if not isinstance(provided, dict) or any(not isinstance(key, str) for key in provided):
            raise DomainError("SKILL_INPUT_UNKNOWN", 422)
        unknown = sorted(key for key in provided if key not in names)
        if unknown:
            raise DomainError("SKILL_INPUT_UNKNOWN", 422)
        missing = [name for name in names if name not in provided]
        if missing:
            raise DomainError("SKILL_INPUT_MISSING", 422)
        values = {}
        for name in names:
            raw = provided[name]
            if not isinstance(raw, str):
                raise DomainError("SKILL_INPUT_INVALID", 422)
            text = raw.strip()
            if not text or len(text) > 200 or any(ord(ch) < 32 for ch in text):
                raise DomainError("SKILL_INPUT_INVALID", 422)
            values[name] = text
        return values

    def _barrier(self, conn) -> None:
        if self._before_commit is not None:
            self._before_commit(conn)

    def _insert_run(
        self,
        conn,
        run_id: str,
        skill_id: str,
        skill_version: int,
        inputs: dict,
        note: str | None,
        provided: bool,
        body: str,
        now: str,
        origin: str,
    ) -> None:
        conn.execute(
            """INSERT INTO saved_skill_runs(
                id, skill_id, skill_version, inputs, note, note_provided, input_hash,
                status, version, result, created_at, updated_at, origin
            ) VALUES(?,?,?,?,?,?,?,'pending',1,NULL,?,?,?)""",
            (
                run_id,
                skill_id,
                skill_version,
                encode(inputs),
                note,
                1 if provided else 0,
                body,
                now,
                now,
                origin,
            ),
        )

    def _preferences(self, conn) -> dict:
        row = conn.execute("SELECT data FROM workspace_preferences WHERE id=1").fetchone()
        stored = _loads(row["data"]) if row else {}
        known = WorkspacePreferences.model_fields
        merged = {
            **WorkspacePreferences().model_dump(),
            **{key: value for key, value in stored.items() if key in known},
        }
        return WorkspacePreferences.model_validate(merged).model_dump()

    def _release_one(self, conn, schedule: dict, now, proactive_off: bool, quiet: bool) -> bool:
        due = occurrence(schedule, now)
        if due is None:
            self._stop_schedule(conn, schedule["id"], now, "skipped_invalid")
            return True
        wall, scheduled = due
        key = wall.isoformat(timespec="minutes")
        next_due = occurrence(schedule, now, next_after=True)
        if self._occurrence_exists(conn, schedule["id"], key) or self._already_consumed(
            schedule, scheduled
        ):
            self._move_schedule(conn, schedule, now, scheduled, next_due, None)
            return True
        lateness = (now - scheduled).total_seconds()
        if lateness >= OCCURRENCE_WINDOW_SECONDS:
            outcome, run_id = "skipped_missed", None
        elif proactive_off:
            outcome, run_id = "skipped_off", None
        elif quiet:
            outcome, run_id = "skipped_quiet", None
        else:
            outcome, run_id = self._prepare_scheduled(conn, schedule, now)
        self._store_occurrence(conn, schedule["id"], key, scheduled, run_id, outcome, now)
        self._move_schedule(conn, schedule, now, scheduled, next_due, outcome)
        self._prune_occurrences(conn, schedule["id"])
        self.store.record(
            conn,
            "skill_schedule_prepared" if outcome == "prepared" else "skill_schedule_skipped",
            details={"schedule_id": schedule["id"], "outcome": outcome},
        )
        return True

    def _prepare_scheduled(self, conn, schedule: dict, now) -> tuple[str, str | None]:
        try:
            skill = self._skill(conn, schedule["skill_id"])
        except DomainError:
            return "skipped_changed", None
        if skill["version"] != schedule["skill_version"]:
            return "skipped_changed", None
        try:
            inputs = self._inputs(skill["input_names"], schedule["inputs"])
        except DomainError:
            return "skipped_changed", None
        count = conn.execute("SELECT COUNT(*) FROM saved_skill_runs").fetchone()[0]
        if count >= RUN_LIMIT:
            return "skipped_limit", None
        canonical = {
            "skill_id": schedule["skill_id"],
            "inputs": inputs,
            "note_provided": schedule["note_provided"],
        }
        if schedule["note_provided"]:
            canonical["note"] = schedule["note"]
        run_id = uuid4().hex
        self._insert_run(
            conn,
            run_id,
            schedule["skill_id"],
            skill["version"],
            inputs,
            schedule["note"] if schedule["note_provided"] else None,
            schedule["note_provided"],
            _hash(canonical),
            iso(now),
            "schedule",
        )
        return "prepared", run_id

    def _already_consumed(self, schedule: dict, scheduled) -> bool:
        if not schedule["last_scheduled_at"]:
            return False
        last = datetime.fromisoformat(schedule["last_scheduled_at"].replace("Z", "+00:00"))
        return scheduled <= last

    def _occurrence_exists(self, conn, schedule_id: str, key: str) -> bool:
        return (
            conn.execute(
                "SELECT 1 FROM saved_skill_occurrences WHERE schedule_id=? AND occurrence_key=?",
                (schedule_id, key),
            ).fetchone()
            is not None
        )

    def _store_occurrence(self, conn, schedule_id, key, scheduled, run_id, outcome, now) -> None:
        conn.execute(
            "INSERT INTO saved_skill_occurrences VALUES(?,?,?,?,?,?,?)",
            (
                uuid4().hex,
                schedule_id,
                key,
                iso(scheduled),
                run_id,
                outcome,
                iso(now),
            ),
        )

    def _move_schedule(self, conn, schedule, now, scheduled, next_due, outcome: str | None) -> None:
        status = "active" if next_due else "completed"
        values = [
            iso(next_due[1]) if next_due else None,
            iso(scheduled),
            status,
            iso(now),
        ]
        if outcome is None:
            conn.execute(
                "UPDATE saved_skill_schedules SET next_run_at=?, last_scheduled_at=?, "
                "status=?, updated_at=? WHERE id=?",
                (*values, schedule["id"]),
            )
            return
        conn.execute(
            "UPDATE saved_skill_schedules SET next_run_at=?, last_scheduled_at=?, "
            "status=?, updated_at=?, last_outcome=? WHERE id=?",
            (*values, outcome, schedule["id"]),
        )

    def _prune_occurrences(self, conn, schedule_id: str) -> None:
        conn.execute(
            "DELETE FROM saved_skill_occurrences WHERE schedule_id=? AND id NOT IN ("
            "SELECT id FROM saved_skill_occurrences WHERE schedule_id=? "
            "ORDER BY scheduled_at DESC LIMIT ?)",
            (schedule_id, schedule_id, OCCURRENCE_HISTORY),
        )

    def _stop_schedule(self, conn, schedule_id: str, now, outcome: str) -> None:
        conn.execute(
            "UPDATE saved_skill_schedules SET status='paused', next_run_at=NULL, "
            "last_outcome=?, updated_at=? WHERE id=?",
            (outcome, iso(now), schedule_id),
        )
        self.store.record(
            conn,
            "skill_schedule_skipped",
            details={"schedule_id": schedule_id, "outcome": outcome},
        )

    def _resume_at(self, schedule: dict, now):
        if schedule["frequency"] == "once":
            due = wall_to_utc(datetime.fromisoformat(schedule["start_local"]), schedule["timezone"])
            return None if due <= now else due
        last = None
        if schedule["last_scheduled_at"]:
            last = datetime.fromisoformat(schedule["last_scheduled_at"].replace("Z", "+00:00"))
        floor = max(now, last) if last else now
        upcoming = occurrence(schedule, floor, next_after=True)
        return upcoming[1] if upcoming else None

    def _schedule_row(self, row) -> dict:
        return {
            "id": row["id"],
            "skill_id": row["skill_id"],
            "skill_version": row["skill_version"],
            "frequency": row["frequency"],
            "start_local": row["start_local"],
            "timezone": row["timezone"],
            "inputs": _loads(row["inputs"]),
            "note": row["note"] if row["note_provided"] else None,
            "note_provided": bool(row["note_provided"]),
            "version": row["version"],
            "status": row["status"],
            "next_run_at": row["next_run_at"],
            "last_scheduled_at": row["last_scheduled_at"],
            "last_outcome": row["last_outcome"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _schedule(self, conn, schedule_id: str) -> dict:
        row = conn.execute(
            "SELECT * FROM saved_skill_schedules WHERE id=?", (schedule_id,)
        ).fetchone()
        if not row:
            raise DomainError("SCHEDULE_NOT_FOUND", 404)
        return self._schedule_row(row)

    def _schedule_response(self, schedule_id: str, key: str, *, replayed: bool) -> dict:
        with self.store.connection() as conn:
            schedule = self._schedule(conn, schedule_id)
        return {"schedule": schedule, "operation_id": key, "replayed": replayed}

    def _check(self, conn, check_id: str) -> dict:
        row = conn.execute("SELECT * FROM saved_skill_checks WHERE id=?", (check_id,)).fetchone()
        if not row:
            raise DomainError("CHECK_NOT_FOUND", 404)
        return {
            "id": row["id"],
            "title": row["title"],
            "steps": _loads(row["steps"]),
            "input_names": _loads(row["input_names"]),
            "validation": row["validation"],
            "passed": bool(row["passed"]),
            "skill_id": row["skill_id"],
            "created_at": row["created_at"],
        }

    def _skill(self, conn, skill_id: str) -> dict:
        row = conn.execute("SELECT * FROM saved_skills WHERE id=?", (skill_id,)).fetchone()
        if not row:
            raise DomainError("SKILL_NOT_FOUND", 404)
        return {
            "id": row["id"],
            "check_id": row["check_id"],
            "version": row["version"],
            "title": row["title"],
            "steps": _loads(row["steps"]),
            "input_names": _loads(row["input_names"]),
            "validation": row["validation"],
            "created_at": row["created_at"],
        }

    def _run(self, conn, run_id: str) -> dict:
        row = conn.execute("SELECT * FROM saved_skill_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise DomainError("RUN_NOT_FOUND", 404)
        return {
            "id": row["id"],
            "skill_id": row["skill_id"],
            "skill_version": row["skill_version"],
            "inputs": _loads(row["inputs"]),
            "note": row["note"] if row["note_provided"] else None,
            "note_provided": bool(row["note_provided"]),
            "input_hash": row["input_hash"],
            "status": row["status"],
            "version": row["version"],
            "result": _loads(row["result"]) if row["result"] else None,
            "origin": row["origin"] if "origin" in row.keys() else "owner",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _check_response(self, check_id: str, key: str, *, replayed: bool) -> dict:
        with self.store.connection() as conn:
            check = self._check(conn, check_id)
            skill = self._skill(conn, check["skill_id"]) if check["skill_id"] else None
        return {
            "check": check,
            "skill": skill,
            "saved": skill is not None,
            "operation_id": key,
            "replayed": replayed,
        }

    def _skill_response(self, skill_id: str, key: str, *, replayed: bool) -> dict:
        with self.store.connection() as conn:
            skill = self._skill(conn, skill_id)
        return {"skill": skill, "saved": True, "operation_id": key, "replayed": replayed}

    def _run_response(self, run_id: str, key: str, *, replayed: bool) -> dict:
        with self.store.connection() as conn:
            run = self._run(conn, run_id)
        return {"run": run, "operation_id": key, "replayed": replayed}


def saved_skill_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/saved-skills", dependencies=[Depends(owner)])
    service = runtime.saved_skills

    def session_of(request: Request) -> str | None:
        return request.cookies.get("desk_companion_session")

    @router.get("")
    def listing(request: Request):
        return service.listing(session_of(request))

    @router.post("/checks")
    def record(payload: CheckInput, request: Request, key=Depends(operation_id)):
        return service.record_check(payload, key, session_of(request))

    @router.post("/checks/{check_id}/save")
    def save(check_id: str, request: Request, key=Depends(operation_id)):
        return service.save_check(check_id, key, session_of(request))

    @router.get("/{skill_id}")
    def detail(skill_id: str, request: Request):
        return service.detail(skill_id, session_of(request))

    @router.post("/{skill_id}/runs")
    def prepare(skill_id: str, payload: RunPrepare, request: Request, key=Depends(operation_id)):
        return service.prepare_run(skill_id, payload, key, session_of(request))

    @router.post("/runs/{run_id}/decision")
    def decision(run_id: str, payload: RunDecision, request: Request, key=Depends(operation_id)):
        return service.decide(run_id, payload, key, session_of(request))

    @router.post("/{skill_id}/schedules")
    def schedule(
        skill_id: str, payload: ScheduleInput, request: Request, key=Depends(operation_id)
    ):
        return service.schedule(skill_id, payload, key, session_of(request))

    @router.post("/schedules/{schedule_id}/actions")
    def schedule_action(
        schedule_id: str, payload: ScheduleAction, request: Request, key=Depends(operation_id)
    ):
        return service.schedule_action(schedule_id, payload, key, session_of(request))

    return router
