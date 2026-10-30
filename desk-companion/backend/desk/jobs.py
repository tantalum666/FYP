"""Durable execution intents, owner approval and conservative crash recovery.

One local worker, no model calls. Claim/approval/cancellation are SQLite transactions.
A dispatched write is never retried. Unknown results have a read-only reconciliation
path; a late verified receipt remains truthful even after a cancellation request.
"""

import hashlib
import json
import os
import re
import threading
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Path as ApiPath
from fastapi.responses import Response
from pydantic import Field, ValidationError, model_validator

from .calendar import iso
from .computer import (
    ComputerExecutor,
    ExecutionRejected,
    FolderDropExecutor,
    LocalNotesExecutor,
    VerificationReceipt,
    accept_owner_folder,
)
from .linux_desktop import LinuxDesktopExecutor
from .application_models import (
    APP_ACTIONS,
    ApplicationJobInput,
    ApplicationReceipt,
    ApplicationStateQuery,
    SourceQuery,
)
from .application_executor import (
    ApplicationExecutor,
    application_request,
    validate_application_request,
)
from .application_runtime import read_regular, rooted
from .schemas import StrictModel
from .store import DomainError, encode

TERMINAL = {"succeeded", "failed", "cancelled", "expired"}


NOTE_ACTIONS = {"save_note", "verify_note"}
FOLDER_ACTIONS = {"save_folder_file", "verify_folder_file"}
DESKTOP_ACTIONS = {"linux_note_preview", "verify_linux_file"}
WRITE_ACTIONS = {"save_note", "save_folder_file", "linux_note_preview"}
CHECK_ACTIONS = {"verify_note", "verify_folder_file", "verify_linux_file"}


class JobInput(StrictModel):
    action: Literal[
        "save_note",
        "verify_note",
        "save_folder_file",
        "verify_folder_file",
        "linux_note_preview",
        "verify_linux_file",
    ] = "save_note"
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=8000)
    source_job_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    task_id: str | None = Field(default=None, max_length=64)
    task_version: int | None = Field(default=None, ge=1, strict=True)

    @model_validator(mode="after")
    def intent(self):
        try:
            self.content.encode("utf-8")
            self.title.encode("utf-8")
        except UnicodeError:
            raise ValueError("Use valid Unicode text") from None
        if not self.title.strip() or (self.action in WRITE_ACTIONS and not self.content.strip()):
            raise ValueError("A title and file text are required")
        if (self.task_id is None) != (self.task_version is None):
            raise ValueError("Task ID and version must be supplied together")
        if self.action in WRITE_ACTIONS and self.source_job_id is not None:
            raise ValueError("New files cannot target an existing artifact")
        if self.action in CHECK_ACTIONS and (not self.source_job_id or self.content):
            raise ValueError("Verification requires a saved job, without replacement text")
        return self


def validate_saved_request(request: dict) -> dict:
    """Backups carry completed intents, including verification's adopted content."""
    if request.get("action") in APP_ACTIONS:
        return validate_application_request(request)
    required = set(JobInput.model_fields) | {"artifact_id", "executor", "scope"}
    extras = {"folder_label", "folder_fingerprint"}
    if not required <= request.keys() or set(request) - required - extras:
        raise ValueError("Incomplete job intent")
    public = {key: request[key] for key in JobInput.model_fields}
    if request["action"] in CHECK_ACTIONS:
        public["content"] = ""
    try:
        JobInput.model_validate(public)
    except ValidationError:
        raise ValueError("Invalid job intent") from None
    if (
        not isinstance(request["content"], str)
        or not 1 <= len(request["content"].encode("utf-8")) <= 32000
    ):
        raise ValueError("Invalid job content")
    if not isinstance(request["artifact_id"], str) or not re.fullmatch(
        r"[a-f0-9]{32}", request["artifact_id"]
    ):
        raise ValueError("Invalid artifact id")
    if request["action"] in FOLDER_ACTIONS:
        fingerprint = request.get("folder_fingerprint")
        if (
            not isinstance(fingerprint, str)
            or not re.fullmatch(r"[a-f0-9]{64}", fingerprint)
            or not isinstance(request.get("folder_label"), str)
            or not 1 <= len(request["folder_label"].strip()) <= 80
            or request["executor"] != FolderDropExecutor.identity
            or request["scope"] != "owner_folder:" + fingerprint
        ):
            raise ValueError("Invalid folder intent")
    else:
        executor = (
            LinuxDesktopExecutor if request["action"] in DESKTOP_ACTIONS else LocalNotesExecutor
        )
        if request["executor"] != executor.identity or request["scope"] != executor.scope:
            raise ValueError("Invalid executor intent")
    return dict(request)


class FolderNaming(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    path: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def readable_label(self):
        try:
            self.label.encode("utf-8")
            self.path.encode("utf-8")
        except UnicodeError:
            raise ValueError("Use valid Unicode text") from None
        self.label = " ".join(self.label.split())
        if not self.label or len(self.label) > 80:
            raise ValueError("A folder label is required")
        return self


class JobApproval(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class JobQuery(StrictModel):
    job_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class JobService:
    def __init__(self, runtime, executor: ComputerExecutor | None = None):
        self.runtime, self.store = runtime, runtime.store
        self.executor = executor or LocalNotesExecutor(self.store.directory)
        self.folder = FolderDropExecutor(self.folder_config)
        self.desktop = LinuxDesktopExecutor(self.store.directory)
        self.applications = ApplicationExecutor(self.store.directory)
        self.enabled = os.environ.get("DESK_COMPUTER_ENABLED") == "1"
        self.run_lock = threading.Lock()
        self.stopping = False
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS computer_jobs(
                    id TEXT PRIMARY KEY, request TEXT NOT NULL, intent_hash TEXT NOT NULL,
                    state TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, expires_at TEXT NOT NULL, deadline TEXT,
                    approved_by TEXT, run_id TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    result TEXT, error TEXT);
                CREATE INDEX IF NOT EXISTS computer_jobs_state ON computer_jobs(state, created_at);
                CREATE TABLE IF NOT EXISTS computer_folder(
                    id INTEGER PRIMARY KEY CHECK (id=1), label TEXT NOT NULL,
                    path TEXT NOT NULL, fingerprint TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS computer_job_events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                    at TEXT NOT NULL, state TEXT NOT NULL, code TEXT);
            """)
            for row in conn.execute(
                "SELECT * FROM computer_jobs WHERE state IN ('running','verifying','cancel_requested')"
            ).fetchall():
                # Invalidate the old run token; an old process cannot bless a new run.
                conn.execute("UPDATE computer_jobs SET run_id=NULL WHERE id=?", (row["id"],))
                self._state(conn, row["id"], "unknown", "PROCESS_RESTARTED")

    def capabilities(self):
        cfg = self.folder_config()
        return {
            "applications": self.applications.status(),
            "desktop": self.desktop.status(),
            "enabled": self.enabled,
            "executor": self.executor.identity,
            "scope": self.executor.scope,
            "actions": ["save_note", "verify_note"] if self.enabled else [],
            "folder": {
                "configured": cfg is not None,
                "label": cfg["label"] if cfg else None,
                "actions": ["save_folder_file", "verify_folder_file"] if cfg else [],
            },
        }

    def folder_config(self, conn=None):
        def read(connection):
            row = connection.execute(
                "SELECT label, path, fingerprint FROM computer_folder WHERE id=1"
            ).fetchone()
            if not row:
                return None
            return {"label": row["label"], "path": row["path"], "fingerprint": row["fingerprint"]}

        if conn is not None:
            return read(conn)
        with self.store.connection() as owned:
            return read(owned)

    def folder_status(self):
        cfg = self.folder_config()
        if not cfg:
            return {"configured": False, "label": None, "path": None}
        return {"configured": True, "label": cfg["label"], "path": cfg["path"]}

    def _bindings(self):
        # A later bounded action registers here. It still uses approve, read-back, and cancel.
        return (
            (NOTE_ACTIONS, self._notes_executor),
            (FOLDER_ACTIONS, self._folder_executor),
            (DESKTOP_ACTIONS, self._desktop_executor),
            (APP_ACTIONS, self._application_executor),
        )

    def _application_executor(self, preparing):
        del preparing
        if not self.applications.enabled or not self.applications.bridge.configured:
            raise DomainError("APPLICATION_UNAVAILABLE", 409)
        return self.applications

    def _desktop_executor(self, preparing):
        del preparing
        if not self.desktop.status()["ready"]:
            raise DomainError("LINUX_DESKTOP_UNAVAILABLE", 409)
        return self.desktop

    def _notes_executor(self, preparing):
        del preparing
        if not self.enabled:
            raise DomainError("COMPUTER_DISABLED", 409)
        return self.executor

    def _folder_executor(self, preparing):
        if not self.folder.configured:
            raise DomainError(
                "FOLDER_NOT_CONFIGURED" if preparing else "COMPUTER_SCOPE_CHANGED", 409
            )
        return self.folder

    def _executor(self, request, *, preparing=False):
        action = request["action"]
        executor = None
        for actions, resolve in self._bindings():
            if action in actions:
                executor = resolve(preparing)
                break
        if executor is None:
            raise DomainError("COMPUTER_ACTION_DENIED", 403)
        if request.get("executor") != executor.identity or request.get("scope") != executor.scope:
            raise DomainError("COMPUTER_SCOPE_CHANGED", 409)
        return executor

    def _adopt_source(self, conn, source_job_id, request, expected_action):
        source = self._row(conn, source_job_id)
        original = json.loads(source["request"])
        if source["state"] != "succeeded" or original["action"] != expected_action:
            raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
        if original["executor"] != request["executor"] or original["scope"] != request["scope"]:
            raise DomainError("COMPUTER_SCOPE_CHANGED", 409)
        request.update(artifact_id=original["artifact_id"], content=original["content"])

    @staticmethod
    def _row(conn, job_id):
        row = conn.execute("SELECT * FROM computer_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise DomainError("JOB_NOT_FOUND", 404)
        return row

    @staticmethod
    def _view(row, review=False, describe=False):
        request = json.loads(row["request"])
        view = {
            k: row[k]
            for k in (
                "id",
                "state",
                "version",
                "created_at",
                "updated_at",
                "expires_at",
                "deadline",
                "error",
            )
        }
        view.update(
            action=request["action"],
            task_id=request["task_id"],
            cancel_requested=bool(row["cancel_requested"]),
            result=json.loads(row["result"]) if row["result"] else None,
        )
        if not review and view["result"]:
            view["result"].pop("readback", None)
        if review or describe:
            view["title"] = request["title"]
        if review:
            authority = row["approved_by"] or ""
            authorization = (
                {"mode": "full", "version": int(authority.split(":", 1)[1])}
                if authority.startswith("owner_policy:")
                else {"mode": "once"}
                if authority == "owner"
                else None
            )
            view.update(
                request=request, intent_hash=row["intent_hash"], authorization=authorization
            )
        return view

    def detail(self, job_id, review=False):
        with self.store.connection() as conn:
            view = self._view(self._row(conn, job_id), review)
            view["history"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT at,state,code FROM computer_job_events WHERE job_id=? ORDER BY sequence",
                    (job_id,),
                )
            ]
            return view

    def listing(self, task_id=None, review=False, describe=False):
        with self.store.connection() as conn:
            # Filter before paging: an older task must not disappear behind
            # unrelated history. Unresolved outcomes take priority over history.
            rows = conn.execute(
                "SELECT * FROM computer_jobs "
                + ("WHERE json_extract(request, '$.task_id')=? " if task_id is not None else "")
                + "ORDER BY state IN ('succeeded','failed','cancelled','expired'), "
                "created_at DESC,rowid DESC LIMIT 200",
                (task_id,) if task_id is not None else (),
            )
            return [self._view(r, review, describe) for r in rows]

    def _state(self, conn, job_id, state, code=None, result=None):
        now = iso(self.store.clock())
        conn.execute(
            "UPDATE computer_jobs SET state=?,version=version+1,updated_at=?,error=?,result=COALESCE(?,result) WHERE id=?",
            (state, now, code, encode(result) if result is not None else None, job_id),
        )
        conn.execute(
            "INSERT INTO computer_job_events(job_id,at,state,code) VALUES(?,?,?,?)",
            (job_id, now, state, code),
        )
        self.store.record(
            conn, "computer_job", details={"job_id": job_id, "state": state, "code": code}
        )
        self.store.bump(conn)

    def _task_current(self, conn, request):
        if request["task_id"]:
            task = self.runtime.tasks.get(conn, request["task_id"])
            if task["version"] != request["task_version"] or (
                request["action"] in WRITE_ACTIONS | APP_ACTIONS
                and task["status"] in {"completed", "cancelled"}
            ):
                raise DomainError("JOB_TASK_CHANGED", 409)
        if request["action"] in APP_ACTIONS:
            for dependency in request["dependencies"]:
                row = self._row(conn, dependency["job_id"])
                parent = json.loads(row["request"])
                result = json.loads(row["result"]) if row["result"] else {}
                if (
                    row["state"] != "succeeded"
                    or parent.get("action") != "application"
                    or parent["task_id"] != request["task_id"]
                    or parent["scope"] != request["scope"]
                    or parent["step"]["filename"] != dependency["filename"]
                    or parent["step"]["kind"] != dependency["kind"]
                    or result.get("sha256") != dependency["sha256"]
                ):
                    raise DomainError("JOB_SOURCE_UNVERIFIED", 409)

    def prepare(self, payload: JobInput | ApplicationJobInput, key):
        def apply(conn):
            if conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0] >= 1000:
                raise DomainError("JOB_LIMIT", 429)
            if (
                conn.execute(
                    "SELECT COUNT(*) FROM computer_jobs WHERE state IN ('review','queued')"
                ).fetchone()[0]
                >= 20
            ):
                raise DomainError("TOO_MANY_DRAFTS", 422)
            request = payload.model_dump()
            if payload.action not in APP_ACTIONS:
                self._task_current(conn, request)
            job_id = uuid4().hex
            request["artifact_id"] = job_id
            if payload.action in APP_ACTIONS:
                if not isinstance(payload, ApplicationJobInput):
                    raise DomainError("COMPUTER_ACTION_DENIED", 403)
                request = application_request(payload, conn, self, job_id)
                self._task_current(conn, request)
            elif payload.action in NOTE_ACTIONS:
                if not self.enabled:
                    raise DomainError("COMPUTER_DISABLED", 409)
                request.update(executor=self.executor.identity, scope=self.executor.scope)
                if payload.action == "verify_note":
                    self._adopt_source(conn, payload.source_job_id, request, "save_note")
            elif payload.action in DESKTOP_ACTIONS:
                self._desktop_executor(True)
                request.update(executor=self.desktop.identity, scope=self.desktop.scope)
                if payload.action == "verify_linux_file":
                    self._adopt_source(conn, payload.source_job_id, request, "linux_note_preview")
            elif payload.action in FOLDER_ACTIONS:
                cfg = self.folder_config(conn)
                if not cfg:
                    raise DomainError("FOLDER_NOT_CONFIGURED", 409)
                request.update(
                    executor=self.folder.identity,
                    scope="owner_folder:" + cfg["fingerprint"],
                    folder_label=cfg["label"],
                    folder_fingerprint=cfg["fingerprint"],
                )
                if payload.action == "verify_folder_file":
                    self._adopt_source(conn, payload.source_job_id, request, "save_folder_file")
            else:
                # JobInput's literal is the public contract. Anything else must not
                # fall through into the folder executor.
                raise DomainError("COMPUTER_ACTION_DENIED", 403)
            fingerprint = hashlib.sha256(encode(request).encode()).hexdigest()
            now = iso(self.store.clock())
            conn.execute(
                "INSERT INTO computer_jobs(id,request,intent_hash,state,version,created_at,updated_at,expires_at) VALUES(?,?,?,'review',0,?,?,?)",
                (
                    job_id,
                    encode(request),
                    fingerprint,
                    now,
                    now,
                    iso(self.store.clock() + timedelta(minutes=5)),
                ),
            )
            self._state(conn, job_id, "review")
            return {"job": self._view(self._row(conn, job_id)), "saved": False}

        result = self.store.operation(
            key, {"type": "computer_prepare", **payload.model_dump()}, apply
        )
        # Return live state on retries; an old 'review' response is not current truth.
        return {**result, "job": self.detail(result["job"]["id"])}

    def approve(self, job_id, payload: JobApproval, key, *, permission_version=None):
        def apply(conn):
            row = self._row(conn, job_id)
            if row["state"] != "review" or row["expires_at"] <= iso(self.store.clock()):
                raise DomainError("JOB_NOT_REVIEWABLE", 409)
            if (
                row["version"] != payload.expected_version
                or row["intent_hash"] != payload.intent_hash
            ):
                raise DomainError("VERSION_CONFLICT", 409)
            request = json.loads(row["request"])
            self._task_current(conn, request)
            self._executor(request)
            if request["action"] in APP_ACTIONS:
                self.applications.current(request)
            if permission_version is not None and not self.runtime.permissions.current(
                permission_version, conn
            ):
                raise DomainError("PERMISSION_CHANGED", 409)
            approved_by = (
                "owner" if permission_version is None else f"owner_policy:{permission_version}"
            )
            conn.execute(
                "UPDATE computer_jobs SET approved_by=?,deadline=? WHERE id=?",
                (approved_by, iso(self.store.clock() + timedelta(seconds=60)), job_id),
            )
            self._state(conn, job_id, "queued")
            if permission_version is not None:
                self.store.record(
                    conn,
                    "permission_action",
                    details={
                        "job_id": job_id,
                        "permission_version": permission_version,
                    },
                )
            return {"job_id": job_id}

        self.store.operation(
            key, {"type": "computer_approve", "id": job_id, **payload.model_dump()}, apply
        )
        return {"job": self.detail(job_id), "queued": True}

    def cancel(self, job_id, key, review_only=False):
        def apply(conn):
            row = self._row(conn, job_id)
            if review_only and row["state"] != "review":
                return {"job_id": job_id}
            if row["state"] not in TERMINAL and not row["cancel_requested"]:
                conn.execute("UPDATE computer_jobs SET cancel_requested=1 WHERE id=?", (job_id,))
                state = (
                    "cancelled"
                    if row["state"] in {"review", "queued"}
                    else ("unknown" if row["state"] == "unknown" else "cancel_requested")
                )
                self._state(conn, job_id, state, "USER_CANCELLED")
            return {"job_id": job_id}

        self.store.operation(
            key, {"type": "computer_cancel", "id": job_id, "review_only": review_only}, apply
        )
        return {"job": self.detail(job_id)}

    def expire(self):
        now = iso(self.store.clock())
        with self.store.connection(write=True) as conn:
            for row in conn.execute(
                "SELECT * FROM computer_jobs WHERE (state='review' AND expires_at<=?) OR (state='queued' AND deadline<=?) OR (state IN ('running','verifying','cancel_requested') AND deadline<=?)",
                (now, now, now),
            ).fetchall():
                state = "expired" if row["state"] in {"review", "queued"} else "unknown"
                self._state(conn, row["id"], state, "JOB_DEADLINE_EXCEEDED")

    def _verify(self, request):
        if request["action"] in APP_ACTIONS:
            receipt = ApplicationReceipt.model_validate(
                self._executor(request).verify(request)
            ).model_dump(exclude_none=True)
            if receipt["verified"] and (
                receipt["artifact"] != request["task_id"] + "/" + request["step"]["filename"]
                or receipt["operation_id"] != request["artifact_id"]
                or receipt["executor"] != request["executor"]
                or receipt["scope"] != request["scope"]
            ):
                raise ValueError("Application receipt does not match its authorized intent")
            expected_app = {
                "workbook": "libreoffice_calc",
                "document": "libreoffice_writer",
                "pdf": "libreoffice_writer",
                "text": "local_text",
            }[request["step"]["kind"]]
            if receipt["verified"] and receipt["apps_verified"] != [expected_app]:
                raise ValueError("Application identity does not match the requested operation")
            if receipt["verified"]:
                body = read_regular(self.applications.target(request))
                if receipt["sha256"] != hashlib.sha256(body).hexdigest() or receipt["bytes"] != len(
                    body
                ):
                    raise ValueError("Application receipt does not match the published bytes")
            return receipt
        receipt = VerificationReceipt.model_validate(
            self._executor(request).verify(request)
        ).model_dump(exclude_none=True)
        if receipt["verified"]:
            if request["action"] == "linux_note_preview" and receipt.get("apps_verified") != [
                "mousepad",
                "chromium",
            ]:
                raise ValueError("Both approved applications require observed completion")
            expected = request["content"].encode("utf-8")
            if (
                receipt["artifact"] != request["artifact_id"] + ".txt"
                or receipt["sha256"] != hashlib.sha256(expected).hexdigest()
                or receipt["bytes"] != len(expected)
                or receipt["executor"] != request["executor"]
                or receipt["scope"] != request["scope"]
            ):
                raise ValueError("Receipt does not match the authorized intent")
        return receipt

    def _approval_current(self, conn, row):
        authority = row["approved_by"] or ""
        if authority.startswith("owner_policy:"):
            version = int(authority.split(":", 1)[1])
            if not self.runtime.permissions.current(version, conn):
                raise DomainError("PERMISSION_CHANGED", 409)

    def run_one(self):
        if self.stopping or not self.run_lock.acquire(False):
            return
        try:
            self.expire()
            with self.store.connection(write=True) as conn:
                row = conn.execute(
                    "SELECT * FROM computer_jobs WHERE state='queued' ORDER BY created_at,rowid LIMIT 1"
                ).fetchone()
                if not row:
                    return
                job_id, request, run_id = row["id"], json.loads(row["request"]), uuid4().hex
                try:
                    self._task_current(conn, request)
                    if not row["approved_by"]:
                        raise DomainError("COMPUTER_SCOPE_CHANGED", 409)
                    self._approval_current(conn, row)
                    executor = self._executor(request)
                except DomainError as error:
                    self._state(conn, job_id, "failed", error.code)
                    return
                conn.execute("UPDATE computer_jobs SET run_id=? WHERE id=?", (run_id, job_id))
                self._state(conn, job_id, "running")

            def checkpoint():
                with self.store.connection() as conn:
                    current = self._row(conn, job_id)
                    if self.stopping or current["run_id"] != run_id or current["cancel_requested"]:
                        raise ExecutionRejected("JOB_CANCELLED_BEFORE_DISPATCH", 409)
                    if current["deadline"] <= iso(self.store.clock()):
                        raise ExecutionRejected("JOB_DEADLINE_EXCEEDED", 409)
                    try:
                        self._task_current(conn, request)
                        self._approval_current(conn, current)
                        self._executor(request)
                    except DomainError as error:
                        raise ExecutionRejected(error.code, error.status) from None

            try:
                executor.execute(request, checkpoint)
            except ExecutionRejected as error:
                state = "cancelled" if error.code == "JOB_CANCELLED_BEFORE_DISPATCH" else "failed"
                code, receipt = error.code, None
            except Exception:
                # The adapter may already have written. Never repeat this intent.
                state, code, receipt = "unknown", "EXECUTOR_RESULT_UNKNOWN", None
            else:
                with self.store.connection(write=True) as conn:
                    if self._row(conn, job_id)["run_id"] != run_id:
                        return
                    self._state(conn, job_id, "verifying")
                try:
                    receipt = self._verify(request)
                    state, code = (
                        ("succeeded", None)
                        if receipt.get("verified")
                        else ("unknown", "JOB_VERIFICATION_FAILED")
                    )
                except Exception:
                    # Even an explicit verification rejection says nothing about
                    # the preceding write. Preserve read-only reconciliation.
                    state, code, receipt = "unknown", "JOB_VERIFICATION_FAILED", None
            with self.store.connection(write=True) as conn:
                if self._row(conn, job_id)["run_id"] == run_id:
                    self._state(conn, job_id, state, code, receipt)
        finally:
            self.run_lock.release()

    def shutdown(self):
        self.stopping = True
        with self.store.connection(write=True) as conn:
            for row in conn.execute(
                "SELECT id FROM computer_jobs WHERE state IN ('running','verifying','cancel_requested')"
            ).fetchall():
                conn.execute("UPDATE computer_jobs SET run_id=NULL WHERE id=?", (row["id"],))
                self._state(conn, row["id"], "unknown", "SERVICE_STOPPED")

    def reconcile(self, job_id):
        if not self.run_lock.acquire(False):
            raise DomainError("JOB_STILL_RUNNING", 409)
        try:
            with self.store.connection() as conn:
                row = self._row(conn, job_id)
                if row["state"] != "unknown":
                    return {"job": self._view(row)}
                request = json.loads(row["request"])
                self._executor(request)
            try:
                receipt = self._verify(request)
            except Exception:
                receipt = {"verified": False, "reason": "verification_unavailable"}
            with self.store.connection(write=True) as conn:
                self._state(
                    conn,
                    job_id,
                    "succeeded" if receipt.get("verified") else "unknown",
                    None if receipt.get("verified") else "JOB_VERIFICATION_FAILED",
                    receipt,
                )
            return {"job": self.detail(job_id)}
        finally:
            self.run_lock.release()

    def set_folder(self, payload: FolderNaming, key):
        path, fingerprint = accept_owner_folder(payload.path, self.store.directory)

        def apply(conn):
            now = iso(self.store.clock())
            conn.execute(
                "INSERT INTO computer_folder(id,label,path,fingerprint,updated_at) VALUES(1,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET label=excluded.label, path=excluded.path, "
                "fingerprint=excluded.fingerprint, updated_at=excluded.updated_at",
                (payload.label, path, fingerprint, now),
            )
            self.store.record(conn, "computer_folder", details={"fingerprint": fingerprint})
            return {"configured": True, "label": payload.label, "path": path}

        return self.store.operation(
            key, {"type": "computer_folder", "label": payload.label, "path": path}, apply
        )

    def clear_folder(self, key):
        def apply(conn):
            conn.execute("DELETE FROM computer_folder WHERE id=1")
            self.store.record(conn, "computer_folder_cleared", details={})
            return {"configured": False, "label": None, "path": None}

        return self.store.operation(key, {"type": "computer_folder_clear"}, apply)

    def export(self):
        """Job records and the chosen folder. Run tokens are left out."""
        with self.store.connection() as conn:
            jobs = []
            events = []
            for row in conn.execute("SELECT * FROM computer_jobs ORDER BY created_at, id"):
                request = json.loads(row["request"])
                jobs.append(
                    {
                        "id": row["id"],
                        "request": request,
                        "intent_hash": row["intent_hash"],
                        "state": row["state"],
                        "version": row["version"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "expires_at": row["expires_at"],
                        "deadline": row["deadline"],
                        "error": row["error"],
                        "result": json.loads(row["result"]) if row["result"] else None,
                    }
                )
                events.extend(
                    {
                        "job_id": item["job_id"],
                        "at": item["at"],
                        "state": item["state"],
                        "code": item["code"],
                    }
                    for item in conn.execute(
                        "SELECT job_id, at, state, code FROM computer_job_events "
                        "WHERE job_id=? ORDER BY sequence DESC LIMIT 20",
                        (row["id"],),
                    )
                )
            folder_row = conn.execute(
                "SELECT label, path, fingerprint, updated_at FROM computer_folder WHERE id=1"
            ).fetchone()
        folder = dict(folder_row) if folder_row else None
        return {"jobs": jobs, "events": events, "folder": folder}

    @staticmethod
    def validate_backup(bundle):
        if bundle is None:
            bundle = {"jobs": [], "events": [], "folder": None}
        if not isinstance(bundle, dict):
            raise ValueError("Invalid job backup")
        rows, events = bundle.get("jobs", []), bundle.get("events", [])
        if (
            not isinstance(rows, list)
            or not isinstance(events, list)
            or len(rows) > 1000
            or len(events) > 20000
        ):
            raise ValueError("Invalid job backup")
        known = set(TERMINAL) | {
            "review",
            "queued",
            "running",
            "verifying",
            "unknown",
            "cancel_requested",
        }
        jobs, identifiers = [], set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid job backup")
            job_id = row.get("id")
            request = row.get("request")
            if (
                not isinstance(job_id, str)
                or len(job_id) != 32
                or any(char not in "0123456789abcdef" for char in job_id)
                or job_id in identifiers
                or not isinstance(request, dict)
                or request.get("action")
                not in NOTE_ACTIONS | FOLDER_ACTIONS | DESKTOP_ACTIONS | APP_ACTIONS
                or row.get("state") not in known
                or not isinstance(row.get("intent_hash"), str)
                or len(row["intent_hash"]) != 64
            ):
                raise ValueError("Invalid job backup")
            request = validate_saved_request(request)
            if request["action"] in APP_ACTIONS and row.get("state") == "succeeded":
                ApplicationReceipt.model_validate(row.get("result"))
            if row["intent_hash"] != hashlib.sha256(encode(request).encode()).hexdigest():
                raise ValueError("Invalid job intent hash")
            identifiers.add(job_id)
            jobs.append(
                {
                    "id": job_id,
                    "request": request,
                    "intent_hash": row["intent_hash"],
                    "state": row["state"],
                    "version": row.get("version") if isinstance(row.get("version"), int) else 0,
                    "created_at": str(row.get("created_at") or "")[:40],
                    "updated_at": str(row.get("updated_at") or "")[:40],
                    "expires_at": str(row.get("expires_at") or "")[:40],
                    "deadline": row.get("deadline"),
                    "error": row.get("error") if isinstance(row.get("error"), str) else None,
                    "result": row.get("result") if isinstance(row.get("result"), dict) else None,
                }
            )
        kept_events = []
        for item in events:
            if not isinstance(item, dict):
                raise ValueError("Invalid job backup")
            if item.get("job_id") not in identifiers or item.get("state") not in known:
                raise ValueError("Invalid job backup")
            kept_events.append(
                {
                    "job_id": item["job_id"],
                    "at": str(item.get("at") or "")[:40],
                    "state": item["state"],
                    "code": item.get("code") if isinstance(item.get("code"), str) else None,
                }
            )
        folder = bundle.get("folder")
        if folder is not None:
            if (
                not isinstance(folder, dict)
                or not isinstance(folder.get("label"), str)
                or not isinstance(folder.get("path"), str)
                or not isinstance(folder.get("fingerprint"), str)
                or not 1 <= len(folder["label"]) <= 80
                or not 1 <= len(folder["path"]) <= 4096
                or "\x00" in folder["path"]
                or len(folder["fingerprint"]) != 64
            ):
                raise ValueError("Invalid job backup")
            folder = {
                "label": folder["label"],
                "path": folder["path"],
                "fingerprint": folder["fingerprint"],
                "updated_at": str(folder.get("updated_at") or "")[:40],
            }
        return {"jobs": jobs, "events": kept_events, "folder": folder}

    def restore(self, conn, bundle):
        """Insert missing jobs. A job that was still running comes back as a review."""
        created = []
        kept = 0
        existing = conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0]
        incoming = []
        for row in bundle["jobs"]:
            if conn.execute("SELECT 1 FROM computer_jobs WHERE id=?", (row["id"],)).fetchone():
                kept += 1
                continue
            incoming.append(row)
        if existing + len(incoming) > 1000:
            raise DomainError("JOB_LIMIT", 429)
        for row in incoming:
            state = row["state"] if row["state"] in TERMINAL else "review"
            conn.execute(
                "INSERT INTO computer_jobs("
                "id, request, intent_hash, state, version, created_at, updated_at, expires_at, "
                "deadline, approved_by, run_id, cancel_requested, result, error"
                ") VALUES(?,?,?,?,?,?,?,?,?,NULL,NULL,0,?,?)",
                (
                    row["id"],
                    encode(row["request"]),
                    row["intent_hash"],
                    state,
                    max(row["version"], 0),
                    row["created_at"],
                    row["updated_at"],
                    row["expires_at"],
                    row["deadline"],
                    encode(row["result"]) if row["result"] is not None else None,
                    row["error"],
                ),
            )
            created.append(row["id"])
        created_ids = set(created)
        for item in bundle["events"]:
            if item["job_id"] not in created_ids:
                continue
            conn.execute(
                "INSERT INTO computer_job_events(job_id, at, state, code) VALUES(?,?,?,?)",
                (item["job_id"], item["at"], item["state"], item["code"]),
            )
        folder = bundle.get("folder")
        if folder and not conn.execute("SELECT 1 FROM computer_folder WHERE id=1").fetchone():
            path, fingerprint = accept_owner_folder(folder["path"], self.store.directory)
            if fingerprint != folder["fingerprint"]:
                raise DomainError("COMPUTER_SCOPE_CHANGED", 409)
            conn.execute(
                "INSERT INTO computer_folder(id,label,path,fingerprint,updated_at) VALUES(1,?,?,?,?)",
                (
                    folder["label"],
                    path,
                    fingerprint,
                    folder["updated_at"] or iso(self.store.clock()),
                ),
            )
        return {"created": len(created), "kept": kept}

    def application_state(self, task_id):
        """Stages are projections of existing durable jobs, not another execution queue."""
        with self.store.connection() as conn:
            self.runtime.tasks.get(conn, task_id)
            rows = conn.execute(
                "SELECT * FROM computer_jobs WHERE json_extract(request,'$.task_id')=? "
                "AND json_extract(request,'$.action')='application' ORDER BY rowid DESC",
                (task_id,),
            ).fetchall()
        stages, artifacts = {}, {}
        for row in rows:
            request = json.loads(row["request"])
            if request["stage"] not in stages:
                stages[request["stage"]] = {
                    "stage": request["stage"],
                    "title": request["title"],
                    "job_id": row["id"],
                    "state": row["state"],
                    "error": row["error"],
                    "task_version": request["task_version"],
                    "depends_on": request["depends_on"],
                    "filename": request["step"]["filename"],
                }
            filename = request["step"]["filename"]
            if row["state"] == "succeeded" and filename not in artifacts:
                result = json.loads(row["result"])
                artifacts[filename] = {
                    "filename": filename,
                    "job_id": row["id"],
                    "sha256": result["sha256"],
                    "bytes": result["bytes"],
                    "verified_at": row["updated_at"],
                }
        return {
            "task_id": task_id,
            "stages": list(stages.values()),
            "artifacts": list(artifacts.values()),
            "unresolved_jobs": [s["job_id"] for s in stages.values() if s["state"] not in TERMINAL],
            "task_completion_is_separate": True,
        }

    def application_readback(self, job_id):
        with self.store.connection() as conn:
            row = self._row(conn, job_id)
            request = json.loads(row["request"])
            if request["action"] not in APP_ACTIONS or row["state"] not in {"succeeded", "unknown"}:
                raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
        return {"job_id": job_id, "result": self._verify(request)}

    def application_download(self, job_id):
        with self.store.connection() as conn:
            row = self._row(conn, job_id)
            request = json.loads(row["request"])
            if request.get("action") != "application" or row["state"] != "succeeded":
                raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
            result = json.loads(row["result"])
        filename = request["step"]["filename"]
        path = rooted(self.applications.root, "history/" + job_id + "/" + filename)
        try:
            body = read_regular(path)
        except (OSError, ValueError, DomainError):
            raise DomainError("APPLICATION_ARTIFACT_MISSING", 404) from None
        if hashlib.sha256(body).hexdigest() != result["sha256"]:
            raise DomainError("APPLICATION_ARTIFACT_CHANGED", 409)
        return filename, body


def job_routes(runtime, owner, operation_id):
    # Pairing and model tool access do not grant computer execution approval.
    router = APIRouter(prefix="/api/computer", dependencies=[Depends(owner)])

    @router.get("/sources")
    def sources():
        return runtime.jobs.applications.sources.listing()

    @router.post("/sources/read")
    def source(payload: SourceQuery):
        return runtime.jobs.applications.sources.content(payload.source_id)

    @router.post("/application-jobs")
    def application_prepare(payload: ApplicationJobInput, key=Depends(operation_id)):
        return runtime.jobs.prepare(payload, key)

    @router.get("/application-state/{task_id}")
    def application_state(task_id: str = ApiPath(pattern=r"^[a-f0-9]{32}$")):
        return runtime.jobs.application_state(ApplicationStateQuery(task_id=task_id).task_id)

    @router.get("/jobs/{job_id}/readback")
    def readback(job_id: str):
        return runtime.jobs.application_readback(job_id)

    @router.get("/jobs/{job_id}/artifact")
    def artifact(job_id: str):
        filename, body = runtime.jobs.application_download(job_id)
        media = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "odt": "application/vnd.oasis.opendocument.text",
            "pdf": "application/pdf",
            "txt": "text/plain",
            "md": "text/markdown",
        }
        return Response(
            body,
            media_type=media[filename.rsplit(".", 1)[1]],
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    @router.get("/folder")
    def folder_status():
        return runtime.jobs.folder_status()

    @router.post("/folder")
    def name_folder(payload: FolderNaming, key=Depends(operation_id)):
        return runtime.jobs.set_folder(payload, key)

    @router.post("/folder/clearance")
    def clear_folder(key=Depends(operation_id)):
        return runtime.jobs.clear_folder(key)

    @router.get("/jobs")
    def listing(task_id: str | None = None):
        return {**runtime.jobs.capabilities(), "jobs": runtime.jobs.listing(task_id, review=True)}

    @router.post("/jobs")
    def prepare(payload: JobInput, key=Depends(operation_id)):
        return runtime.jobs.prepare(payload, key)

    @router.get("/jobs/{job_id}")
    def detail(job_id: str):
        return {"job": runtime.jobs.detail(job_id, review=True)}

    @router.post("/jobs/{job_id}/approve")
    def approve(job_id: str, payload: JobApproval, key=Depends(operation_id)):
        return runtime.jobs.approve(job_id, payload, key)

    @router.post("/jobs/{job_id}/cancel")
    def cancel(job_id: str, key=Depends(operation_id)):
        return runtime.jobs.cancel(job_id, key)

    @router.post("/jobs/{job_id}/reconcile")
    def reconcile(job_id: str):
        return runtime.jobs.reconcile(job_id)

    return router
