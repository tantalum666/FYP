"""Separate owner-reviewed public-only browser effects; existing note jobs are untouched."""

import hashlib
import json
import os
import re
import threading
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request, Response

from .artifacts import ArtifactInput
from .browser_policy import (
    ADAPTER, ID_PATTERN, MAX_EXPORT_BYTES, SOURCE_CATALOG, STACKEDIT_URL,
    BrowserApproval, BrowserIntent, BrowserJobInput, BrowserReceipt, PublicObservationInput,
    SourceObservation, brief_content, digest, safe_read, source_entry,
)
from .browser_supervisor import BrowserSupervisor
from .calendar import iso
from .file_store import require_access, session_from_request
from .store import DomainError, encode


class BrowserService:
    def __init__(self, runtime, supervisor=None):
        self.runtime, self.store = runtime, runtime.store
        self.supervisor = supervisor or BrowserSupervisor()
        self.enabled = os.environ.get("DESK_BROWSER_ENABLED") == "1"
        self.root = Path(self.store.directory) / "browser-effects"
        self.lock, self.stopping = threading.Lock(), False
        self.environment_id = digest(["owned_local_chromium", self.supervisor.executable, ADAPTER])
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS browser_observations(
                    id TEXT PRIMARY KEY,state TEXT NOT NULL,data TEXT,error TEXT,
                    session_hash TEXT NOT NULL,created_at TEXT NOT NULL,
                    cleanup INTEGER NOT NULL DEFAULT 1,process_id INTEGER,context_revision TEXT,active_token TEXT);
                CREATE TABLE IF NOT EXISTS browser_effects(
                    id TEXT PRIMARY KEY,state TEXT NOT NULL,version INTEGER NOT NULL,
                    request TEXT NOT NULL,intent_hash TEXT NOT NULL,session_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,updated_at TEXT NOT NULL,expires_at TEXT NOT NULL,
                    deadline TEXT,execution_id TEXT,cancel_requested INTEGER NOT NULL DEFAULT 0,
                    dispatched INTEGER NOT NULL DEFAULT 0,cleanup INTEGER NOT NULL DEFAULT 1,
                    process_id INTEGER,result TEXT,error TEXT,active_token TEXT,context_revision TEXT);
                CREATE TABLE IF NOT EXISTS browser_operations(
                    operation_key TEXT PRIMARY KEY,request_hash TEXT NOT NULL,kind TEXT NOT NULL,
                    reference TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS browser_events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,
                    at TEXT NOT NULL,state TEXT NOT NULL,code TEXT);
            """)
            for table, names in {
                "browser_effects": ("active_token", "context_revision"),
                "browser_observations": ("context_revision", "active_token"),
            }.items():
                existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
                for name in names:
                    if name not in existing:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} TEXT")
            conn.execute("UPDATE browser_observations SET state='failed',error='BROWSER_RESTARTED',active_token=NULL "
                         "WHERE state='reading'")
            for row in conn.execute("SELECT id FROM browser_effects WHERE state IN "
                                    "('running','verifying','cancelling')").fetchall():
                self._state(conn, row["id"], "unknown", "BROWSER_RESTARTED")
                conn.execute("UPDATE browser_effects SET active_token=NULL WHERE id=?", (row["id"],))

    def _guard(self, session_hash, revision=None):
        if self.stopping:
            raise DomainError("BROWSER_STOPPED", 409)
        with self.store.connection() as conn:
            require_access(self.store, conn, session_hash)
        if revision is not None and encode(self.runtime.personal_context.revision()) != revision:
            raise DomainError("BROWSER_CONTEXT_CHANGED", 409)

    def capabilities(self):
        reason = "BROWSER_DISABLED" if not self.enabled else self.supervisor.readiness()
        with self.store.connection() as conn:
            dirty = conn.execute("SELECT 1 FROM browser_effects WHERE cleanup=0 AND state NOT IN "
                                 "('running','verifying','cancelling') LIMIT 1").fetchone()
            dirty = dirty or conn.execute("SELECT 1 FROM browser_observations WHERE cleanup=0 "
                                          "AND state!='reading' LIMIT 1").fetchone()
        if dirty:
            reason = "BROWSER_CLEANUP_UNCONFIRMED"
        return {
            "configured": self.enabled, "ready": reason is None, "reason": reason,
            "experimental": True, "scope": "public_synthetic_only",
            "network_boundary": "routing_only", "live_acceptance": "not_verified_here",
            "destination": {"id": ADAPTER, "url": STACKEDIT_URL},
            "sources": [{"id": key, **entry} for key, entry in SOURCE_CATALOG.items()],
            "limits": {"title_chars": 120, "note_chars": 2000,
                       "export_bytes": MAX_EXPORT_BYTES, "review_seconds": 300,
                       "execution_seconds": 180},
        }

    def _available(self):
        reason = self.capabilities()["reason"]
        if reason:
            raise DomainError(reason, 409)

    def _directory(self, record_id, create=False):
        if not re.fullmatch(ID_PATTERN, record_id):
            raise DomainError("BROWSER_TARGET_DENIED", 403)
        if create:
            self.root.mkdir(mode=0o700, exist_ok=True)
        for path in (self.root,):
            info = path.lstat()
            if path.is_symlink() or not path.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise DomainError("BROWSER_DIRECTORY_UNSAFE", 409)
        child = self.root / record_id
        if create:
            child.mkdir(mode=0o700)  # An existing slot is never overwritten or reused.
        info = child.lstat()
        if child.is_symlink() or not child.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise DomainError("BROWSER_DIRECTORY_UNSAFE", 409)
        return child

    @staticmethod
    def _row(conn, job_id):
        row = conn.execute("SELECT * FROM browser_effects WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise DomainError("BROWSER_JOB_NOT_FOUND", 404)
        return row

    def _operation(self, conn, key, payload, kind, create):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        fingerprint = digest(payload)
        old = conn.execute("SELECT * FROM browser_operations WHERE operation_key=?", (key,)).fetchone()
        if old:
            if old["request_hash"] != fingerprint or old["kind"] != kind:
                raise DomainError("OPERATION_ID_CONFLICT", 409)
            return old["reference"], False
        if kind == "cancel":
            # Stop authority survives work-history capacity. Retain at most one
            # cancel receipt per existing job; different-key repeats are no-ops.
            stopped = conn.execute("SELECT reference FROM browser_operations WHERE kind='cancel' "
                                   "AND reference=? LIMIT 1", (payload["id"],)).fetchone()
            if stopped:
                return stopped["reference"], False
        elif conn.execute("SELECT COUNT(*) FROM browser_operations WHERE kind!='cancel'").fetchone()[0] >= 2000:
            raise DomainError("BROWSER_HISTORY_LIMIT", 429)
        reference = create()
        conn.execute("INSERT INTO browser_operations VALUES(?,?,?,?)",
                     (key, fingerprint, kind, reference))
        return reference, True

    @staticmethod
    def _view(row, review=False):
        view = {key: row[key] for key in (
            "id", "state", "version", "created_at", "updated_at", "expires_at", "deadline", "error"
        )}
        view.update(cancel_requested=bool(row["cancel_requested"]),
                    cleanup_confirmed=bool(row["cleanup"]),
                    result=json.loads(row["result"]) if row["result"] else None)
        if review:
            view.update(request=json.loads(row["request"]), intent_hash=row["intent_hash"])
        elif view["result"]:
            view["result"] = {key: value for key, value in view["result"].items() if key in {
                "verified", "adapter", "catalog_version", "byte_count", "sha256", "artifact_id",
                "export_url", "process_cleanup_confirmed", "browser_close_confirmed",
                "export_method", "data_scope", "network_boundary",
            }}
        return view

    def detail(self, job_id, review=False):
        with self.store.connection() as conn:
            view = self._view(self._row(conn, job_id), review)
            view["history"] = [dict(r) for r in conn.execute(
                "SELECT at,state,code FROM browser_events WHERE job_id=? ORDER BY sequence", (job_id,))]
            return view

    def listing(self, review=False, limit=50, cursor=None):
        if not 1 <= limit <= 100 or cursor is not None and not re.fullmatch(ID_PATTERN, cursor):
            raise DomainError("BROWSER_PAGE_INVALID", 422)
        with self.store.connection() as conn:
            rows = conn.execute("SELECT * FROM browser_effects " +
                                ("WHERE id<? " if cursor else "") + "ORDER BY id DESC LIMIT ?",
                                (cursor, limit + 1) if cursor else (limit + 1,)).fetchall()
            return {"jobs": [self._view(row, review) for row in rows[:limit]],
                    "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None}

    def _state(self, conn, job_id, state, error=None, result=None):
        now = iso(self.store.clock())
        conn.execute("UPDATE browser_effects SET state=?,version=version+1,updated_at=?,error=?,"
                     "result=COALESCE(?,result) WHERE id=?",
                     (state, now, error, encode(result) if result is not None else None, job_id))
        conn.execute("INSERT INTO browser_events(job_id,at,state,code) VALUES(?,?,?,?)",
                     (job_id, now, state, error))
        self.store.bump(conn)

    def observe(self, payload: PublicObservationInput, key, *, session_hash, checkpoint=None, publication_checkpoint=None):
        self._guard(session_hash)
        revision = encode(self.runtime.personal_context.revision())
        claim = uuid4().hex
        if not self.lock.acquire(False):
            raise DomainError("BROWSER_BUSY", 409)
        try:
            with self.store.connection(write=True) as conn:
                def reserve():
                    reference = uuid4().hex
                    conn.execute("INSERT INTO browser_observations(id,state,session_hash,created_at,context_revision,active_token) "
                                 "VALUES(?,'reading',?,?,?,?)", (reference, session_hash, iso(self.store.clock()), revision, claim))
                    return reference
                reference, fresh = self._operation(conn, key, payload.model_dump(), "observe", reserve)
                old = conn.execute("SELECT * FROM browser_observations WHERE id=?", (reference,)).fetchone()
            if not fresh:
                if old["state"] == "observed":
                    return {"observation": json.loads(old["data"]), "operation_id": key}
                raise DomainError(old["error"] or "BROWSER_READ_PENDING", 409)
            def fence(_stage):
                if checkpoint is not None:
                    checkpoint()
                self._guard(session_hash, revision)
                with self.store.connection() as conn:
                    current = conn.execute("SELECT state,active_token FROM browser_observations WHERE id=?",
                                           (reference,)).fetchone()
                if not current or current["state"] != "reading" or current["active_token"] != claim:
                    raise DomainError("BROWSER_RESTARTED", 409)
            try:
                fence(None)
                self._available()
                directory = self._directory(reference, create=True)
                def started(pid):
                    with self.store.connection(write=True) as conn:
                        changed = conn.execute("UPDATE browser_observations SET cleanup=0,process_id=? "
                                               "WHERE id=? AND state='reading' AND active_token=?",
                                               (pid, reference, claim)).rowcount
                        if not changed:
                            raise DomainError("BROWSER_RESTARTED", 409)
                outcome = self.supervisor.run(
                    {"operation": "observe", "source_id": payload.source_id}, directory,
                    fence, started, timeout=60)
                with self.store.connection(write=True) as conn:
                    changed = conn.execute("UPDATE browser_observations SET cleanup=? "
                                           "WHERE id=? AND state='reading' AND active_token=?",
                                           (int(outcome.cleanup_confirmed and not outcome.forced_stop), reference, claim)).rowcount
                    if not changed:
                        raise DomainError("BROWSER_RESTARTED", 409)
                fence(None)  # Cleanup evidence is independent from permission to publish content.
                if outcome.error or not outcome.value or not outcome.cleanup_confirmed or outcome.forced_stop:
                    raise DomainError(outcome.error or "BROWSER_CLEANUP_UNCONFIRMED", 409)
                observation = SourceObservation.model_validate({**outcome.value, "id": reference}).model_dump()
                self._validate_observation(observation)
                if observation["source_id"] != payload.source_id:
                    raise DomainError("BROWSER_SOURCE_CHANGED", 409)
                with self.store.connection(write=True) as conn:
                    self._guard(session_hash, revision)
                    if publication_checkpoint is not None:
                        publication_checkpoint(conn)
                    changed = conn.execute("UPDATE browser_observations SET state='observed',data=?,active_token=NULL "
                                           "WHERE id=? AND state='reading' AND active_token=?",
                                           (encode(observation), reference, claim)).rowcount
                    if not changed:
                        raise DomainError("BROWSER_RESTARTED", 409)
                self._guard(session_hash, revision)
                return {"observation": observation, "operation_id": key}
            except Exception as exc:
                code = exc.code if isinstance(exc, DomainError) else "BROWSER_OBSERVATION_FAILED"
                with self.store.connection(write=True) as conn:
                    conn.execute("UPDATE browser_observations SET state='failed',error=?,active_token=NULL "
                                 "WHERE id=? AND state='reading' AND active_token=?", (code, reference, claim))
                raise DomainError(code, 409) from None
        finally:
            self.lock.release()

    @staticmethod
    def _validate_observation(observation):
        snapshot = SourceObservation.model_validate(observation).model_dump()
        expected = {k: snapshot[k] for k in ("source_id", "url", "title", "heading", "excerpt")}
        if snapshot["url"] != source_entry(snapshot["source_id"])["url"] or digest(expected) != snapshot["sha256"]:
            raise DomainError("BROWSER_SOURCE_CHANGED", 409)

    def prepare(self, payload: BrowserJobInput, key, *, session_hash):
        self._guard(session_hash)
        self._available()
        revision = encode(self.runtime.personal_context.revision())
        with self.store.connection(write=True) as conn:
            def create():
                source = conn.execute("SELECT * FROM browser_observations WHERE id=? AND state='observed'",
                                      (payload.observation_id,)).fetchone()
                if not source:
                    raise DomainError("BROWSER_SOURCE_UNAVAILABLE", 409)
                observation = json.loads(source["data"])
                self._validate_observation(observation)
                job_id = uuid4().hex
                intent = BrowserIntent(
                    job_id=job_id, environment_id=self.environment_id, source=observation,
                    title=payload.title, document_name="fyp-source-" + job_id,
                    content=brief_content(observation, payload.title, payload.note), public_only=True,
                ).model_dump()
                now = iso(self.store.clock())
                conn.execute("INSERT INTO browser_effects(id,state,version,request,intent_hash,session_hash,"
                             "created_at,updated_at,expires_at,context_revision) VALUES(?,'review',0,?,?,?,?,?,?,?)",
                             (job_id, encode(intent), digest(intent), session_hash, now, now,
                              iso(self.store.clock() + timedelta(minutes=5)), revision))
                self._state(conn, job_id, "review")
                return job_id
            job_id, _ = self._operation(conn, key, payload.model_dump(), "prepare", create)
        return {"job": self.detail(job_id, review=True), "operation_id": key}

    def lookup_operation(self, payload, key, *, kind):
        """Internal read-only recovery; no authority, new work or client callback.

        Validate both the receipt and its actual child before an orchestration
        parent adopts or cancels it. This remains available when private data is
        hidden so a previously authorized parent can stop its own exact child.
        """
        if kind not in {"observe", "prepare"}:
            raise DomainError("BROWSER_OPERATION_KIND_DENIED", 422)
        with self.store.connection() as conn:
            receipt = conn.execute(
                "SELECT * FROM browser_operations WHERE operation_key=?", (key,)
            ).fetchone()
            if not receipt:
                return None
            if receipt["kind"] != kind or receipt["request_hash"] != digest(payload.model_dump()):
                raise DomainError("BROWSER_OPERATION_RECEIPT_CONFLICT", 409)
            if kind == "observe":
                row = conn.execute("SELECT * FROM browser_observations WHERE id=?",
                                   (receipt["reference"],)).fetchone()
                if not row:
                    raise DomainError("BROWSER_OPERATION_RECEIPT_CONFLICT", 409)
                observation = json.loads(row["data"]) if row["data"] else None
                if observation:
                    self._validate_observation(observation)
                    if observation["id"] != row["id"] or observation["source_id"] != payload.source_id:
                        raise DomainError("BROWSER_OPERATION_RECEIPT_CONFLICT", 409)
                return {"reference_id": row["id"], "state": row["state"],
                        "error": row["error"], "observation": observation}
            row = self._row(conn, receipt["reference"])
            intent = self._intent(row, execution=False)
            if (intent["source"]["id"] != payload.observation_id
                    or intent["title"] != payload.title
                    or intent["content"] != brief_content(intent["source"], payload.title, payload.note)):
                raise DomainError("BROWSER_OPERATION_RECEIPT_CONFLICT", 409)
        return {"reference_id": row["id"], "job": self.detail(row["id"], review=True)}

    def _intent(self, row, execution=True):
        intent = BrowserIntent.model_validate(json.loads(row["request"])).model_dump()
        self._validate_observation(intent["source"])
        if digest(intent) != row["intent_hash"] or intent["job_id"] != row["id"]:
            raise DomainError("BROWSER_INTENT_CHANGED", 409)
        if execution and intent["environment_id"] != self.environment_id:
            raise DomainError("BROWSER_ENVIRONMENT_CHANGED", 409)
        return intent

    def approve(self, job_id, payload: BrowserApproval, key, *, session_hash):
        self._guard(session_hash)
        self._available()
        revision = encode(self.runtime.personal_context.revision())
        with self.store.connection(write=True) as conn:
            def apply():
                row = self._row(conn, job_id)
                if row["state"] != "review" or row["expires_at"] <= iso(self.store.clock()):
                    raise DomainError("BROWSER_REVIEW_EXPIRED", 409)
                if row["version"] != payload.expected_version or row["intent_hash"] != payload.intent_hash:
                    raise DomainError("VERSION_CONFLICT", 409)
                if row["context_revision"] != revision:
                    raise DomainError("BROWSER_CONTEXT_CHANGED", 409)
                self._intent(row)
                conn.execute("UPDATE browser_effects SET session_hash=?,deadline=? WHERE id=?",
                             (session_hash, iso(self.store.clock() + timedelta(seconds=180)), job_id))
                self._state(conn, job_id, "queued")
                return job_id
            self._operation(conn, key, {"id": job_id, **payload.model_dump()}, "approve", apply)
        return {"job": self.detail(job_id, review=True), "operation_id": key}

    def cancel(self, job_id, key):
        with self.store.connection(write=True) as conn:
            def apply():
                row = self._row(conn, job_id)
                if row["state"] not in {"succeeded", "failed", "cancelled", "expired"}:
                    conn.execute("UPDATE browser_effects SET cancel_requested=1 WHERE id=?", (job_id,))
                    state = "cancelled" if row["state"] in {"review", "queued"} else (
                        "unknown" if row["state"] == "unknown" else "cancelling")
                    self._state(conn, job_id, state, "BROWSER_CANCELLED")
                return job_id
            self._operation(conn, key, {"id": job_id}, "cancel", apply)
        return {"job": self.detail(job_id), "operation_id": key}

    def _verify(self, row):
        intent = self._intent(row, execution=False)
        directory = self._directory(row["id"])
        receipt = BrowserReceipt.model_validate(json.loads(safe_read(directory, "receipt.json"))).model_dump()
        body = safe_read(directory, "export.md")
        expected = {
            "job_id": row["id"], "execution_id": row["execution_id"], "intent_hash": row["intent_hash"],
            "source_sha256": intent["source"]["sha256"], "environment_id": intent["environment_id"],
            "document_name": intent["document_name"], "destination": intent["destination"],
            "sha256": hashlib.sha256(body).hexdigest(), "byte_count": len(body),
        }
        if body != intent["content"].encode() or any(receipt[k] != v for k, v in expected.items()):
            raise DomainError("BROWSER_VERIFICATION_MISMATCH", 409)
        return receipt, body

    def _import(self, row, receipt, body, session_hash):
        try:
            self._guard(session_hash)
            artifact = self.runtime.artifacts.import_download(
                ArtifactInput(format="markdown", display_name=receipt["document_name"] + ".md",
                              content=body.decode("utf-8"), authorship="owner"),
                "browser-export/" + row["id"], body=body, expected_sha256=receipt["sha256"],
                session_hash=session_hash, selected_source_ids=[], run_id=None, step_id=row["id"],
            )["artifact"]
            return artifact["id"] if artifact["status"] == "verified" else None
        except (DomainError, AttributeError):
            # Raw independently verified export remains available; no browser replay.
            return None

    def advance_one(self):
        if not self.enabled or self.stopping or not self.lock.acquire(False):
            return
        try:
            with self.store.connection(write=True) as conn:
                row = conn.execute("SELECT * FROM browser_effects WHERE state='queued' ORDER BY created_at LIMIT 1").fetchone()
                if not row:
                    return
                job_id = row["id"]
                if row["deadline"] <= iso(self.store.clock()):
                    self._state(conn, job_id, "expired", "BROWSER_DEADLINE_EXCEEDED")
                    return
                try:
                    intent = self._intent(row)
                except Exception as exc:
                    self._state(conn, job_id, "failed", exc.code if isinstance(exc, DomainError)
                                else "BROWSER_INTENT_CHANGED")
                    return
                execution_id = uuid4().hex
                conn.execute("UPDATE browser_effects SET execution_id=?,active_token=? WHERE id=?",
                             (execution_id, execution_id, job_id))
                self._state(conn, job_id, "running")

            def fence(stage):
                self._guard(row["session_hash"], row["context_revision"])
                with self.store.connection(write=stage is not None) as conn:
                    current = self._row(conn, job_id)
                    if current["active_token"] != execution_id or current["cancel_requested"]:
                        raise DomainError("BROWSER_CANCELLED", 409)
                    if current["deadline"] <= iso(self.store.clock()):
                        raise DomainError("BROWSER_DEADLINE_EXCEEDED", 409)
                    self._intent(current)
                    if stage is not None:
                        conn.execute("UPDATE browser_effects SET dispatched=1 WHERE id=?", (job_id,))

            try:
                fence(None)
                self._available()
                directory = self._directory(job_id, create=True)
                def started(pid):
                    with self.store.connection(write=True) as conn:
                        changed = conn.execute("UPDATE browser_effects SET cleanup=0,process_id=? "
                                               "WHERE id=? AND active_token=?",
                                               (pid, job_id, execution_id)).rowcount
                        if not changed:
                            raise DomainError("BROWSER_RESTARTED", 409)
                outcome = self.supervisor.run(
                    {"operation": "execute", "source_id": intent["source"]["source_id"],
                     "intent": intent, "intent_hash": row["intent_hash"], "execution_id": execution_id},
                    directory, fence, started, timeout=180)
                with self.store.connection(write=True) as conn:
                    if self._row(conn, job_id)["active_token"] != execution_id:
                        return  # A restarted service owns recovery; this old claim is fenced.
                    conn.execute("UPDATE browser_effects SET cleanup=? WHERE id=?",
                                 (int(outcome.cleanup_confirmed and not outcome.forced_stop), job_id))
                    self._state(conn, job_id, "verifying")
                    current = self._row(conn, job_id)
                try:
                    receipt, body = self._verify(current)
                    receipt.update(artifact_id=self._import(current, receipt, body, row["session_hash"]),
                                   export_url=f"/api/browser/jobs/{job_id}/export",
                                   process_cleanup_confirmed=bool(current["cleanup"]))
                    state, error = (("succeeded", None) if current["cleanup"] else
                                    ("unknown", "BROWSER_CLEANUP_UNCONFIRMED"))
                except Exception:
                    receipt = None
                    state = "unknown" if current["dispatched"] else (
                        "cancelled" if current["cancel_requested"] else "failed")
                    error = outcome.error or "BROWSER_VERIFICATION_UNAVAILABLE"
                with self.store.connection(write=True) as conn:
                    if self._row(conn, job_id)["active_token"] == execution_id:
                        self._state(conn, job_id, state, error, receipt)
            except Exception as exc:
                with self.store.connection(write=True) as conn:
                    current = self._row(conn, job_id)
                    if current["active_token"] == execution_id:
                        state = "unknown" if current["dispatched"] else (
                            "cancelled" if current["cancel_requested"] else "failed")
                        self._state(conn, job_id, state,
                                    exc.code if isinstance(exc, DomainError) else "BROWSER_WORKER_FAILED")
        finally:
            self.lock.release()

    def reconcile(self, job_id, *, session_hash=None):
        if not self.lock.acquire(False):
            raise DomainError("BROWSER_BUSY", 409)
        try:
            with self.store.connection() as conn:
                row = self._row(conn, job_id)
            if row["state"] not in {"unknown", "succeeded"}:
                return {"job": self.detail(job_id)}
            try:
                receipt, body = self._verify(row)
                old_result = json.loads(row["result"]) if row["result"] else {}
                receipt.update(artifact_id=self._import(row, receipt, body, session_hash) or old_result.get("artifact_id"),
                               export_url=f"/api/browser/jobs/{job_id}/export",
                               process_cleanup_confirmed=bool(row["cleanup"]))
            except Exception:
                return {"job": self.detail(job_id)}
            with self.store.connection(write=True) as conn:
                current = self._row(conn, job_id)
                if current["version"] != row["version"]:
                    raise DomainError("VERSION_CONFLICT", 409)
                state = "succeeded" if row["cleanup"] else "unknown"
                error = None if row["cleanup"] else "BROWSER_CLEANUP_UNCONFIRMED"
                if state != row["state"] or error != row["error"] or receipt != old_result:
                    self._state(conn, job_id, state, error, result=receipt)
            return {"job": self.detail(job_id)}
        finally:
            self.lock.release()

    def export(self, job_id, *, session_hash):
        self._guard(session_hash)
        with self.store.connection() as conn:
            row = self._row(conn, job_id)
        if row["state"] not in {"succeeded", "unknown"}:
            raise DomainError("BROWSER_EXPORT_UNVERIFIED", 409)
        receipt, body = self._verify(row)
        self._guard(session_hash)
        return body, receipt["document_name"] + ".md"

    def shutdown(self):
        self.stopping = True  # Supervisor's periodic fence initiates bounded owned cleanup.


def browser_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/browser", dependencies=[Depends(owner)])
    service = runtime.browser_jobs

    def visible(request):
        return runtime.personal_context.visible({"kind": "owner", "session": request.cookies.get("desk_companion_session")})

    @router.get("/capabilities")
    def capabilities():
        return service.capabilities()

    @router.post("/observations")
    def observe(payload: PublicObservationInput, request: Request, key=Depends(operation_id)):
        return service.observe(payload, key, session_hash=session_from_request(request))

    @router.post("/jobs")
    def prepare(payload: BrowserJobInput, request: Request, key=Depends(operation_id)):
        return service.prepare(payload, key, session_hash=session_from_request(request))

    @router.get("/jobs")
    def listing(request: Request, limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return service.listing(visible(request), limit, cursor)

    @router.get("/jobs/{job_id}")
    def detail(job_id: str, request: Request):
        return {"job": service.detail(job_id, review=visible(request))}

    @router.post("/jobs/{job_id}/approve")
    def approve(job_id: str, payload: BrowserApproval, request: Request, key=Depends(operation_id)):
        return service.approve(job_id, payload, key, session_hash=session_from_request(request))

    @router.post("/jobs/{job_id}/cancel")
    def cancel(job_id: str, key=Depends(operation_id)):
        return service.cancel(job_id, key)

    @router.post("/jobs/{job_id}/reconcile")
    def reconcile(job_id: str, request: Request, key=Depends(operation_id)):
        # Read-only against the destination: no navigation, typing or export replay.
        return service.reconcile(job_id, session_hash=session_from_request(request))

    @router.get("/jobs/{job_id}/export")
    def export(job_id: str, request: Request):
        body, filename = service.export(job_id, session_hash=session_from_request(request))
        return Response(body, media_type="text/markdown", headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
        })

    return router
