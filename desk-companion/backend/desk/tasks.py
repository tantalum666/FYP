"""Persistent commitments and follow-ups, separate from scheduled calendar time."""

import json
from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator, model_validator

from .calendar import iso, wall_to_utc
from .schemas import EventInput, StrictModel
from .store import DomainError, encode
from .workspace_data import quiet_until

OPEN = {"todo", "in_progress", "waiting"}
# One tick must not surface every overdue task at once. The rest wait a minute each.
MAX_NEW_FOLLOWUPS = 3


class TaskStep(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    done: bool = False

    @field_validator("title")
    @classmethod
    def title_value(cls, value):
        return EventInput.title_not_blank(value)


class TaskInput(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    timezone: str = "Asia/Hong_Kong"
    due_local: datetime | None = None
    status: Literal["todo", "in_progress", "waiting"] = "todo"
    next_step: str = Field(default="", max_length=500)
    waiting_for: str = Field(default="", max_length=500)
    steps: list[TaskStep] = Field(default_factory=list, max_length=20)
    visibility: Literal["private", "displayable"] = "private"
    follow_up_enabled: bool = True
    check_in_local: datetime | None = None
    interval_minutes: int = Field(default=1440, ge=15, le=10080)

    @field_validator("title")
    @classmethod
    def title_value(cls, value):
        return EventInput.title_not_blank(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        return EventInput.valid_zone(value)

    @field_validator("due_local", "check_in_local")
    @classmethod
    def local(cls, value):
        return EventInput.local_datetime(value) if value else None

    @model_validator(mode="after")
    def dates(self):
        for value in (self.due_local, self.check_in_local):
            if value:
                wall_to_utc(value, self.timezone, reject_ambiguous=True)
        if self.status == "waiting" and not self.waiting_for.strip():
            raise ValueError("Explain what you are waiting for")
        return self


class TaskAction(StrictModel):
    action: Literal["update", "note", "complete", "reopen", "cancel", "pause", "resume", "snooze"]
    expected_version: int = Field(ge=1)
    task: TaskInput | None = None
    note: str = Field(default="", max_length=2000)
    minutes: int = Field(default=60, ge=15, le=10080)


class TaskChange(StrictModel):
    task_id: str = Field(min_length=1, max_length=64)
    change: TaskAction


class TaskQuery(StrictModel):
    query: str = Field(default="", max_length=160)
    include_closed: bool = False


class TaskService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,data TEXT NOT NULL,
                    version INTEGER NOT NULL,status TEXT NOT NULL,paused INTEGER NOT NULL,
                    next_check_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS tasks_next ON tasks(next_check_at);
                CREATE TABLE IF NOT EXISTS task_evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,at TEXT NOT NULL,kind TEXT NOT NULL,note TEXT NOT NULL,
                    task_version INTEGER NOT NULL,source TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS task_followups(id TEXT PRIMARY KEY,task_id TEXT NOT NULL,
                    task_version INTEGER NOT NULL,created_at TEXT NOT NULL,state TEXT NOT NULL,
                    content TEXT NOT NULL,ai_status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(task_id,task_version));
            """)
            # Never retry an interrupted model request automatically after a restart.
            conn.execute("UPDATE task_followups SET ai_status='failed' WHERE ai_status='running'")

    def get(self, conn, task_id):
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise DomainError("TASK_NOT_FOUND", 404)
        return self.view(row)

    @staticmethod
    def view(row):
        return {
            **json.loads(row["data"]),
            **{
                k: row[k]
                for k in ("id", "version", "status", "next_check_at", "created_at", "updated_at")
            },
            "paused": bool(row["paused"]),
        }

    def schedule(self, data, *, explicit=True):
        if not data["follow_up_enabled"]:
            return None
        now = self.store.clock()
        if explicit and data.get("check_in_local"):
            at = wall_to_utc(
                datetime.fromisoformat(data["check_in_local"]),
                data["timezone"],
                reject_ambiguous=True,
            )
            if at <= now:
                raise DomainError("CHECK_IN_IN_PAST", 422)
            return iso(at)
        at = now + timedelta(minutes=data["interval_minutes"])
        if data.get("due_local"):
            due = wall_to_utc(
                datetime.fromisoformat(data["due_local"]), data["timezone"], reject_ambiguous=True
            )
            if due > now:
                at = min(at, due)
        return iso(at)

    def evidence(self, conn, task_id, version, kind, note, source):
        conn.execute(
            "INSERT INTO task_evidence(task_id,at,kind,note,task_version,source) VALUES(?,?,?,?,?,?)",
            (task_id, iso(self.store.clock()), kind, note, version, source),
        )
        self.store.record(conn, "task_" + kind, details={"task_id": task_id, "source": source})

    def create(self, payload, key, origin="manual"):
        data = payload.model_dump(mode="json")

        def apply(conn):
            if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] >= 500:
                raise DomainError("TASK_LIMIT", 422)
            task_id, now = uuid4().hex, iso(self.store.clock())
            conn.execute(
                "INSERT INTO tasks VALUES(?,?,1,?,0,?,?,?)",
                (task_id, encode(data), data["status"], self.schedule(data), now, now),
            )
            self.evidence(conn, task_id, 1, "created", "", origin)
            return {"task": self.get(conn, task_id), "saved": True}

        return self.store.operation(key, {"type": "task_create", "data": data}, apply)

    def action(self, task_id, payload, key, origin="manual"):
        def apply(conn):
            old = self.get(conn, task_id)
            if old["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            action = payload.action
            if old["status"] not in OPEN and action != "reopen":
                raise DomainError("TASK_CLOSED", 409)
            if action == "reopen" and old["status"] in OPEN:
                raise DomainError("TASK_ALREADY_OPEN", 409)
            data = {k: old[k] for k in TaskInput.model_fields}
            status, paused, next_at = old["status"], old["paused"], old["next_check_at"]
            if action == "update":
                if not payload.task:
                    raise DomainError("TASK_INPUT_REQUIRED", 422)
                data = payload.task.model_dump(mode="json")
                status = data["status"]
                next_at = self.schedule(data) if not paused else None
            elif action == "note":
                if not payload.note.strip():
                    raise DomainError("TASK_NOTE_REQUIRED", 422)
                next_at = self.schedule(data, explicit=False) if not paused else None
                data["check_in_local"] = None
            elif action in {"complete", "cancel"}:
                status, next_at = ("completed" if action == "complete" else "cancelled"), None
            elif action == "reopen":
                status, paused = "todo", False
                data["status"] = "todo"
                data["check_in_local"] = None
                next_at = self.schedule(data, explicit=False)
            elif action == "pause":
                paused, next_at = True, None
            elif action in {"resume", "snooze"}:
                paused = False
                data["follow_up_enabled"] = True
                data["check_in_local"] = None
                next_at = iso(self.store.clock() + timedelta(minutes=payload.minutes))
            data["completion_source"] = (
                "user_confirmed"
                if action == "complete"
                else None
                if action == "reopen"
                else old.get("completion_source")
            )
            version = old["version"] + 1
            conn.execute(
                "UPDATE tasks SET data=?,version=?,status=?,paused=?,next_check_at=?,updated_at=? WHERE id=?",
                (
                    encode(data),
                    version,
                    status,
                    int(paused),
                    next_at,
                    iso(self.store.clock()),
                    task_id,
                ),
            )
            conn.execute(
                "UPDATE task_followups SET state='resolved' WHERE task_id=? AND state='pending'",
                (task_id,),
            )
            self.evidence(
                conn,
                task_id,
                version,
                action,
                payload.note.strip(),
                "user_confirmed" if action == "complete" else origin,
            )
            return {"task": self.get(conn, task_id), "saved": True}

        return self.store.operation(
            key, {"type": "task_action", "id": task_id, **payload.model_dump(mode="json")}, apply
        )

    def listing(self, query="", include_closed=False, display=False):
        with self.store.connection() as conn:
            hide = self.store.settings(conn)["hide_private"]
            if display:
                posture = self.runtime.posture.snapshot()
                hide = hide or (
                    posture["preferences"]["enabled"]
                    and posture["preferences"]["privacy_when_away"]
                    and (
                        not posture["connected"]
                        or posture["status"] in {"absent", "unknown", "paused"}
                    )
                )
            rows = conn.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
            followups = {
                r["task_id"]: dict(r)
                for r in conn.execute("SELECT * FROM task_followups WHERE state='pending'")
            }
            items = []
            for row in rows:
                task = self.view(row)
                if not include_closed and task["status"] not in OPEN:
                    continue
                redacted = bool(hide and task["visibility"] == "private")
                if query and (redacted or query.casefold() not in task["title"].casefold()):
                    continue
                task["due_at"] = (
                    iso(wall_to_utc(datetime.fromisoformat(task["due_local"]), task["timezone"]))
                    if task["due_local"]
                    else None
                )
                task["overdue"] = bool(
                    task["due_at"]
                    and task["due_at"] <= iso(self.store.clock())
                    and task["status"] in OPEN
                )
                task["redacted"] = redacted
                alert = followups.get(task["id"])
                task["followup"] = (
                    {
                        **{k: alert[k] for k in ("id", "created_at", "ai_status")},
                        **json.loads(alert["content"]),
                    }
                    if alert
                    else None
                )
                if redacted:
                    task.update(title="", next_step="", waiting_for="", steps=[])
                    if task["followup"]:
                        task["followup"] = {
                            **task["followup"],
                            "en": "A private task needs an update.",
                            "zh": "一项私人事务需要更新进展。",
                            "mode": "local_rules",
                        }
                items.append(task)
            items.sort(
                key=lambda x: (
                    x["status"] not in OPEN,
                    not bool(x["followup"]),
                    x["due_at"] or "9999",
                    x["created_at"],
                )
            )
            return {
                "tasks": items,
                "revision": self.store.revision(conn),
                "server_time": iso(self.store.clock()),
                "timezone": self.store.settings(conn)["timezone"],
            }

    def detail(self, task_id, display=False):
        projected = next(
            (
                t
                for t in self.listing(include_closed=True, display=display)["tasks"]
                if t["id"] == task_id
            ),
            None,
        )
        if projected and projected["redacted"]:
            raise DomainError("PRIVATE_TASK_HIDDEN", 403)
        with self.store.connection() as conn:
            task = self.get(conn, task_id)
            if self.store.settings(conn)["hide_private"] and task["visibility"] == "private":
                raise DomainError("PRIVATE_TASK_HIDDEN", 403)
            rows = conn.execute(
                "SELECT * FROM task_evidence WHERE task_id=? ORDER BY id DESC LIMIT 100", (task_id,)
            ).fetchall()
        return {
            "task": projected,
            "evidence": [dict(r) for r in rows],
            "jobs": self.runtime.jobs.listing(task_id),
        }

    def tick(self):
        now_at = self.store.clock()
        now = iso(now_at)
        prefs = self.runtime.data.preferences()
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        quiet_end = quiet_until(prefs, now_at.astimezone(zone))
        with self.store.connection(write=True) as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('todo','in_progress','waiting') AND paused=0 AND next_check_at<=? ORDER BY next_check_at,rowid",
                (now,),
            ).fetchall()
            changed = False
            made = 0
            waiting = 0
            for row in rows:
                data = self.view(row)
                if not data["follow_up_enabled"]:
                    conn.execute("UPDATE tasks SET next_check_at=NULL WHERE id=?", (data["id"],))
                    changed = True
                    continue
                if quiet_end is not None:
                    conn.execute(
                        "UPDATE tasks SET next_check_at=? WHERE id=?",
                        (iso(quiet_end), data["id"]),
                    )
                    changed = True
                    continue
                if made >= MAX_NEW_FOLLOWUPS:
                    waiting += 1
                    conn.execute(
                        "UPDATE tasks SET next_check_at=? WHERE id=?",
                        (iso(now_at + timedelta(minutes=waiting)), data["id"]),
                    )
                    changed = True
                    continue
                en, zh = (
                    "Any progress to record? Choose your next step.",
                    "有新的进展吗？更新后继续安排下一步。",
                )
                if data["status"] == "waiting":
                    en, zh = (
                        "Has the item you are waiting for arrived?",
                        "你等待的事项有结果了吗？",
                    )
                if data["next_step"]:
                    en += " Next step: " + data["next_step"]
                    zh += " 下一步：" + data["next_step"]
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO task_followups(id,task_id,task_version,created_at,state,content) VALUES(?,?,?,?,'pending',?)",
                    (
                        uuid4().hex,
                        data["id"],
                        data["version"],
                        now,
                        encode({"en": en, "zh": zh, "mode": "local_rules"}),
                    ),
                )
                conn.execute("UPDATE tasks SET next_check_at=NULL WHERE id=?", (data["id"],))
                if cursor.rowcount:
                    self.evidence(conn, data["id"], data["version"], "followup", "", "local_rules")
                    made += 1
                    changed = True
            if changed:
                self.store.bump(conn)

    def snapshot(self):
        result = self.listing(display=True)
        active = result["tasks"]
        return {
            "active_count": len(active),
            "due_count": sum(bool(t["followup"]) for t in active),
            "attention": [t for t in active if t["followup"]][:3],
        }

    def export(self):
        # Business snapshot: task definitions plus the latest 20 progress records per task.
        with self.store.connection() as conn:
            tasks = [self.view(r) for r in conn.execute("SELECT * FROM tasks")]
            evidence = []
            for task in tasks:
                evidence.extend(
                    dict(r)
                    for r in conn.execute(
                        "SELECT * FROM task_evidence WHERE task_id=? ORDER BY id DESC LIMIT 20",
                        (task["id"],),
                    )
                )
            return {"tasks": tasks, "evidence": evidence, "history_scope": "latest_20_per_task"}

    @staticmethod
    def validate_backup(bundle):
        if (
            not isinstance(bundle, dict)
            or len(bundle.get("tasks", [])) > 500
            or len(bundle.get("evidence", [])) > 10000
        ):
            raise ValueError("Invalid task backup")
        items, identifiers = [], set()
        for row in bundle.get("tasks", []):
            task_id = row["id"]
            if (
                not isinstance(task_id, str)
                or not 1 <= len(task_id) <= 64
                or task_id in identifiers
            ):
                raise ValueError("Invalid task ID")
            identifiers.add(task_id)
            status = row["status"]
            if status not in OPEN | {"completed", "cancelled"}:
                raise ValueError("Invalid task state")
            source = {k: v for k, v in row.items() if k in TaskInput.model_fields}
            source["status"] = status if status in OPEN else "todo"
            model = TaskInput.model_validate(source)
            items.append({"id": task_id, "status": status, "data": model.model_dump(mode="json")})
        evidence = []
        for row in bundle.get("evidence", []):
            if (
                row["task_id"] not in identifiers
                or not isinstance(row["note"], str)
                or len(row["note"]) > 2000
            ):
                raise ValueError("Invalid evidence")
            at = datetime.fromisoformat(row["at"].replace("Z", "+00:00"))
            if not at.tzinfo or not 2000 <= at.year <= 2100:
                raise ValueError("Invalid evidence date")
            evidence.append({"task_id": row["task_id"], "at": iso(at), "note": row["note"]})
        return {"tasks": items, "evidence": evidence}

    def restore(self, conn, bundle):
        missing = [
            t
            for t in bundle["tasks"]
            if not conn.execute("SELECT 1 FROM tasks WHERE id=?", (t["id"],)).fetchone()
        ]
        if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] + len(missing) > 500:
            raise DomainError("TASK_LIMIT", 422)
        now = iso(self.store.clock())
        for task in missing:
            data = task["data"]
            data["check_in_local"] = None
            data["completion_source"] = "backup" if task["status"] == "completed" else None
            conn.execute(
                "INSERT INTO tasks VALUES(?,?,1,?,1,NULL,?,?)",
                (task["id"], encode(data), task["status"], now, now),
            )
            for evidence in bundle["evidence"]:
                if evidence["task_id"] == task["id"]:
                    conn.execute(
                        "INSERT INTO task_evidence(task_id,at,kind,note,task_version,source) VALUES(?,?,'restored',?,1,'backup')",
                        (task["id"], evidence["at"], evidence["note"]),
                    )
            self.evidence(conn, task["id"], 1, "restored", "", "backup")
        return {"created": len(missing), "kept": len(bundle["tasks"]) - len(missing)}


def task_routes(runtime, authenticated, operation_id):
    router = APIRouter(prefix="/api/tasks", dependencies=[Depends(authenticated)])

    @router.get("")
    def listing(query: str = "", include_closed: bool = False, display: bool = False):
        return runtime.tasks.listing(query[:160], include_closed, display)

    @router.post("")
    def create(payload: TaskInput, key=Depends(operation_id)):
        return runtime.tasks.create(payload, key)

    @router.get("/{task_id}")
    def detail(task_id: str, display: bool = False):
        return runtime.tasks.detail(task_id, display=display)

    @router.post("/{task_id}/actions")
    def action(task_id: str, payload: TaskAction, key=Depends(operation_id)):
        return runtime.tasks.action(task_id, payload, key)

    return router
