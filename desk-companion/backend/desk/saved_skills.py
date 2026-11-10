"""Owner-saved checklists. A passed check becomes one immutable skill.

Preparing a run stores the fill and stays pending. Only the owner's decision
writes a local result. Steps and input values are data: nothing here starts a
tool, a model call, mail, a purchase, or a booking. Omitted fields are not
defaults that overwrite or approve.
"""

import hashlib
import json
import re
from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode

_NAME = re.compile(r"^[^\W\d_][\w]{0,31}$")
_ID = re.compile(r"^[0-9a-f]{32}$")
CHECK_LIMIT = 40
SKILL_LIMIT = 40
RUN_LIMIT = 100
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

    def record_check(self, payload: CheckInput, key: str, session: str | None) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if payload.passed is None:
            raise DomainError("CHECK_NOT_PASSED", 422)
        body = _hash(payload.model_dump(mode="json"))
        with self.store.connection(write=True) as conn:
            self._assert_open(conn)
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
            self._assert_open(conn)
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

    def prepare_run(self, skill_id: str, payload: RunPrepare, key: str, session: str | None) -> dict:
        self._gate(session)
        key = self._require_key(key)
        if not _ID.fullmatch(skill_id):
            raise DomainError("SKILL_NOT_FOUND", 404)
        with self.store.connection(write=True) as conn:
            self._assert_open(conn)
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
                conn.execute(
                    "INSERT INTO saved_skill_runs VALUES(?,?,?,?,?,?,?, 'pending', 1, NULL, ?, ?)",
                    (
                        run_id,
                        skill_id,
                        skill["version"],
                        encode(inputs),
                        note,
                        1 if provided else 0,
                        body,
                        now,
                        now,
                    ),
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
            self._assert_open(conn)
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

    def listing(self, session: str | None) -> dict:
        self._gate(session)
        with self.store.connection() as conn:
            self._assert_open(conn)
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
            self._assert_open(conn)
            skill = self._skill(conn, skill_id)
            rows = conn.execute(
                "SELECT id FROM saved_skill_runs WHERE skill_id=? "
                "ORDER BY created_at DESC, id DESC LIMIT 20",
                (skill_id,),
            ).fetchall()
            runs = [self._run(conn, row["id"]) for row in rows]
        return {"skill": skill, "runs": runs}

    def _gate(self, session: str | None) -> None:
        if not session or not self.store.session_valid(session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible({**_OWNER, "session": session})

    def _assert_open(self, conn) -> None:
        if self.store.settings(conn)["hide_private"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)

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

    def _note(self, payload: RunPrepare) -> tuple[bool, str | None]:
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

    return router
