"""Durable, session-bound work packages and a bounded adaptive model coordinator.

One host owns this SQLite store. Every model attempt is reserved before dispatch;
interrupted paid calls are never replayed without a new explicit owner action.
"""

import hashlib
import json
import threading
from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from .agent_run_schemas import RunCreate, RunAction, AgentDecision
from .agent_planner import build_plan, compose, decide
from .agent_tools import read_evidence, artifact_payloads, validate_mutation, verify_proposal
from .calendar import iso
from .context import fingerprint
from .store import DomainError, encode

TERMINAL = {"succeeded", "partial", "failed", "cancelled"}


class AgentRunService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.lock, self.worker_lock = threading.RLock(), threading.Lock()
        self.stopped = False
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY,state TEXT NOT NULL,
                    version INTEGER NOT NULL,generation INTEGER NOT NULL,lease_until TEXT,
                    session_hash TEXT NOT NULL,data TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_steps(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,
                    plan_revision INTEGER NOT NULL,kind TEXT NOT NULL,label TEXT NOT NULL,
                    state TEXT NOT NULL,result TEXT NOT NULL,error TEXT);
                CREATE TABLE IF NOT EXISTS agent_attempts(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,
                    created_at TEXT NOT NULL,error TEXT);
                CREATE TABLE IF NOT EXISTS agent_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,kind TEXT NOT NULL,at TEXT NOT NULL,details TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_run_effect_intents(operation_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,intent_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_run_operations(id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,run_id TEXT NOT NULL);
            """)
            if "intent_hash" not in {
                r[1] for r in conn.execute("PRAGMA table_info(agent_run_effect_intents)")
            }:
                conn.execute(
                    "ALTER TABLE agent_run_effect_intents ADD COLUMN intent_hash TEXT NOT NULL DEFAULT ''"
                )

    def session(self, principal, *, visible=True):
        if not principal or principal.get("kind") != "owner" or not principal.get("session"):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        digest = hashlib.sha256(principal["session"].encode()).hexdigest()
        self.authority(digest, visible=visible)
        return digest

    def authority(self, session_hash, *, visible=True):
        with self.store.connection() as conn:
            if not conn.execute(
                "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                (session_hash, iso(self.store.clock())),
            ).fetchone():
                raise DomainError("RUN_SESSION_EXPIRED", 403)
            if visible and self.store.settings(conn)["hide_private"]:
                raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)

    def scope(self, principal):
        session = self.session(principal)
        sources = self.runtime.sources.listing(session_hash=session, limit=100)
        sources = sources.get("sources", []) if isinstance(sources, dict) else sources
        with self.store.connection() as conn:
            tasks = [
                {k: v[k] for k in ("id", "title", "version")}
                for row in conn.execute("SELECT * FROM tasks ORDER BY updated_at DESC LIMIT 100")
                for v in [self.runtime.tasks.view(row)]
            ]
            events = [
                {
                    "id": r["id"],
                    "version": r["version"],
                    **{
                        k: json.loads(r["data"])[k]
                        for k in ("title", "start_local", "end_local", "timezone")
                    },
                }
                for r in conn.execute("SELECT * FROM events WHERE deleted=0 ORDER BY id LIMIT 100")
            ]
        settings = self.runtime.personal_context.settings()
        destinations = [
            d
            for d in settings["destinations"]
            if d["kind"] == "text" and d["id"] in settings["approved_destinations"]
        ]
        modes = ["deterministic"] + (["model"] if destinations else [])
        result = {
            "sources": sources,
            "tasks": tasks,
            "events": events,
            "destinations": destinations,
            "modes": modes,
            "limits": {
                "sources": 12,
                "tasks": 10,
                "events": 10,
                "mutations": 3,
                "model_calls": 8,
                "plan_revisions": 2,
                "model_selected_items": 10,
                "source_bytes": 4194304,
            },
            "business_context_allowed": settings["share_business_context"],
        }
        result["scope_revision"] = fingerprint([result, self.runtime.personal_context.revision()])
        return result

    def _get(self, conn, run_id):
        row = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise DomainError("RUN_NOT_FOUND", 404)
        return {
            **json.loads(row["data"]),
            **{
                k: row[k]
                for k in (
                    "id",
                    "state",
                    "version",
                    "generation",
                    "lease_until",
                    "session_hash",
                    "updated_at",
                )
            },
        }

    def _save(self, conn, run, kind, details=None):
        run["version"] += 1
        run["updated_at"] = iso(self.store.clock())
        data = {
            k: v
            for k, v in run.items()
            if k
            not in {
                "id",
                "state",
                "version",
                "generation",
                "lease_until",
                "session_hash",
                "updated_at",
            }
        }
        conn.execute(
            "UPDATE agent_runs SET state=?,version=?,generation=?,lease_until=?,session_hash=?,data=?,updated_at=? WHERE id=?",
            (
                run["state"],
                run["version"],
                run["generation"],
                run["lease_until"],
                run["session_hash"],
                encode(data),
                run["updated_at"],
                run["id"],
            ),
        )
        conn.execute(
            "INSERT INTO agent_events(run_id,kind,at,details) VALUES(?,?,?,?)",
            (run["id"], kind, run["updated_at"], encode(details or {})),
        )
        self.store.bump(conn)

    @staticmethod
    def _view(run, hidden=False):
        if hidden:
            return {
                k: run[k]
                for k in ("id", "state", "version", "plan_revision", "created_at", "updated_at")
            } | {"private_hidden": True}
        return {
            k: v
            for k, v in run.items()
            if k
            not in {
                "session_hash",
                "privacy_revision",
                "lease_until",
                "generation",
                "available_evidence",
                "report",
                "report_evidence",
                "pending_decision",
                "pending_effect",
            }
        } | {"private_hidden": False, "evidence_count": len(run["evidence"])}

    def listing(self, principal):
        # Authenticated owner metadata remains inspectable when private details are hidden.
        self.session(principal, visible=False)
        hidden = not self.runtime.personal_context.visible(principal)
        with self.store.connection() as conn:
            return {
                "runs": [
                    self._view(self._get(conn, r[0]), hidden)
                    for r in conn.execute(
                        "SELECT id FROM agent_runs ORDER BY updated_at DESC LIMIT 100"
                    )
                ]
            }

    def detail(self, run_id, principal):
        session = self.session(principal)
        with self.store.connection() as conn:
            run = self._get(conn, run_id)
            steps = [
                {**dict(r), "result": json.loads(r["result"])}
                for r in conn.execute(
                    "SELECT * FROM agent_steps WHERE run_id=? ORDER BY rowid", (run_id,)
                )
            ]
            events = [
                {**dict(r), "details": json.loads(r["details"])}
                for r in conn.execute(
                    "SELECT * FROM agent_events WHERE run_id=? ORDER BY sequence", (run_id,)
                )
            ]
            proposals = [
                self.runtime.assistant._view(r)
                for pid in run["proposal_ids"]
                for r in conn.execute("SELECT * FROM assistant_proposals WHERE id=?", (pid,))
            ]
        artifacts = self.runtime.artifacts.listing(session_hash=session, run_id=run_id)
        artifacts = artifacts.get("artifacts", []) if isinstance(artifacts, dict) else artifacts
        return {
            "run": self._view(run),
            "steps": steps,
            "events": events,
            "artifacts": artifacts,
            "proposals": proposals,
        }

    def create(self, payload, key, principal):
        session = self.session(principal)
        request_hash = fingerprint(payload.model_dump(mode="json"))
        self._key(key)
        with self.lock:
            with self.store.connection() as conn:
                old = conn.execute(
                    "SELECT * FROM agent_run_operations WHERE id=?", (key,)
                ).fetchone()
                if old:
                    if old["request_hash"] != request_hash:
                        raise DomainError("OPERATION_ID_CONFLICT")
                    return {"run": self._view(self._get(conn, old["run_id"]))}
            scope = self.scope(principal)
            if payload.scope_revision != scope["scope_revision"]:
                raise DomainError("RUN_SCOPE_CHANGED")
            for field, options in [
                ("source_ids", "sources"),
                ("task_ids", "tasks"),
                ("event_ids", "events"),
            ]:
                if not set(getattr(payload, field)).issubset({x["id"] for x in scope[options]}):
                    raise DomainError("RUN_SOURCE_NOT_SELECTED", 403)
            selected_sources = [s for s in scope["sources"] if s["id"] in payload.source_ids]
            if sum(s["byte_count"] for s in selected_sources) > 4 * 1024 * 1024:
                raise DomainError("RUN_SOURCE_SIZE_LIMIT", 413)
            mutations = [
                validate_mutation(m, payload.task_ids, payload.event_ids)
                for m in payload.mutation_requests
            ]
            run_id, now = uuid4().hex, iso(self.store.clock())
            run = payload.model_dump(mode="json") | {
                "id": run_id,
                "state": "queued",
                "version": 1,
                "generation": 1,
                "lease_until": None,
                "session_hash": session,
                "created_at": now,
                "updated_at": now,
                "deadline": iso(self.store.clock() + timedelta(hours=24)),
                "plan_revision": 1,
                "state_reason": None,
                "question": None,
                "pending_decision": None,
                "pending_effect": None,
                "pending_reads": [],
                "outcome_requirements": {
                    "formats": ["markdown", "csv"],
                    "selected_source_coverage": "complete",
                    "required_sections": payload.required_sections,
                },
                "unmet_requirements": [],
                "plan": [],
                "answers": [],
                "evidence": [],
                "report": None,
                "report_evidence": [],
                "artifact_ids": [],
                "current_artifact_ids": [],
                "proposal_ids": [],
                "effects": [],
                "model_calls": 0,
                "reads": 0,
                "mutation_requests": mutations,
                "privacy_revision": self._revision(),
                "available_evidence": [],
                "phase": "collect" if payload.mode == "deterministic" else "decide",
            }
            for field, options, kind in [
                ("source_ids", "sources", "source"),
                ("task_ids", "tasks", "task"),
                ("event_ids", "events", "event"),
            ]:
                run["available_evidence"].extend(
                    {
                        "id": kind + ":" + i["id"],
                        "kind": kind,
                        "record_id": i["id"],
                        "label": i.get("name", i.get("title", "")),
                    }
                    for i in scope[options]
                    if i["id"] in getattr(payload, field)
                )
            if payload.mode == "deterministic":
                run["plan"] = [label for _, label in build_plan(mutations)]
            self._authorize(run)
            with self.store.connection(write=True) as conn:
                if conn.execute("SELECT count(*) FROM agent_runs").fetchone()[0] >= 100:
                    raise DomainError("RUN_LIMIT_REACHED", 422)
                conn.execute(
                    "INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?)",
                    (run_id, run["state"], 1, 1, None, session, "{}", now),
                )
                self._save(conn, run, "created", {"mode": payload.mode})
                conn.execute(
                    "INSERT INTO agent_run_operations VALUES(?,?,?)", (key, request_hash, run_id)
                )
            return {"run": self._view(run)}

    @staticmethod
    def _key(key):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)

    def _revision(self):
        return json.loads(encode(self.runtime.personal_context.revision()))

    def _authorize(self, run):
        if self.stopped:
            raise DomainError("RUN_RUNTIME_STOPPED", 409)
        with self.store.connection() as conn:
            current = conn.execute(
                "SELECT generation FROM agent_runs WHERE id=?", (run["id"],)
            ).fetchone()
            if current and current[0] != run["generation"]:
                raise DomainError("RUN_CONTROL_CHANGED", 409)
        self.authority(run["session_hash"])
        for source_id in run["source_ids"]:
            source = self.runtime.sources.metadata(source_id, session_hash=run["session_hash"])
            if source["status"] != "verified":
                raise DomainError("RUN_SOURCE_UNAVAILABLE", 409)
        if run["privacy_revision"] != self._revision():
            raise DomainError("RUN_CONTEXT_CHANGED", 403)
        if iso(self.store.clock()) >= run["deadline"]:
            raise DomainError("RUN_DEADLINE_EXCEEDED", 409)
        if run["mode"] == "model":
            settings = self.runtime.personal_context.settings()
            ids = {d["id"] for d in settings["destinations"] if d["kind"] == "text"}
            if (
                run["provider_destination_id"] not in ids
                or run["provider_destination_id"] not in settings["approved_destinations"]
            ):
                raise DomainError("PROVIDER_CONTEXT_NOT_APPROVED", 403)
            if run["source_ids"] and not run["share_sources_with_provider"]:
                raise DomainError("RUN_SOURCE_SHARING_NOT_APPROVED", 403)
            if (run["task_ids"] or run["event_ids"]) and not settings["share_business_context"]:
                raise DomainError("PROVIDER_CONTEXT_NOT_APPROVED", 403)

    def action(self, run_id, payload, key, principal):
        session = self.session(principal, visible=payload.action not in {"pause", "cancel"})
        hidden = not self.runtime.personal_context.visible(principal)
        self._key(key)
        req = fingerprint([run_id, payload.model_dump()])
        with self.lock:
            with self.store.connection() as conn:
                old = conn.execute(
                    "SELECT * FROM agent_run_operations WHERE id=?", (key,)
                ).fetchone()
                run = self._get(conn, run_id)
                if old:
                    if old["request_hash"] != req:
                        raise DomainError("OPERATION_ID_CONFLICT")
                    return {"run": self._view(run, hidden)}
            if run["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            action = payload.action
            with self.store.connection() as conn:
                control_count = conn.execute(
                    "SELECT count(*) FROM agent_run_operations WHERE run_id=?", (run_id,)
                ).fetchone()[0]
            if action != "cancel" and control_count >= 64:
                raise DomainError("RUN_CONTROL_LIMIT_REACHED", 422)
            if action in {"pause", "cancel"}:
                if run["state"] in TERMINAL:
                    raise DomainError("RUN_ALREADY_TERMINAL")
                # Serialize pending draft cancellation with existing approval decisions.
                self._cancel_pending(run)
                run["state"] = "cancelled" if action == "cancel" else "paused"
                run["state_reason"] = (
                    "RUN_CANCELLED_NO_ROLLBACK" if action == "cancel" else "RUN_PAUSED"
                )
            elif action == "steer":
                if (
                    not payload.goal
                    or not payload.goal.strip()
                    or run["plan_revision"] >= 2
                    or run["state"] == "cancelled"
                ):
                    raise DomainError("RUN_STEER_NOT_AVAILABLE", 422)
                self._cancel_pending(run)
                run["goal"], run["plan_revision"] = payload.goal.strip(), run["plan_revision"] + 1
                run["current_artifact_ids"], run["report"], run["question"] = [], None, None
                run["pending_decision"] = None
                run["report_evidence"] = []
                run["pending_reads"] = []
                # Immutable files stay reusable; refresh changing application records.
                run["evidence"] = [e for e in run["evidence"] if e["kind"] == "source"]
                run["phase"] = "collect" if run["mode"] == "deterministic" else "decide"
                run["plan"] = [] if run["mode"] == "model" else run["plan"]
                run["state"], run["state_reason"] = "queued", None
            elif action == "answer":
                if (
                    run["state"] != "waiting_input"
                    or not payload.answer
                    or not payload.answer.strip()
                    or len(run["answers"]) >= 4
                ):
                    raise DomainError("RUN_ANSWER_NOT_EXPECTED", 422)
                run["answers"].append(payload.answer.strip())
                run["question"], run["state"], run["state_reason"] = None, "queued", None
            else:
                if run["state"] not in {"paused", "blocked"}:
                    raise DomainError("RUN_RESUME_NOT_AVAILABLE")
                if (
                    run["state_reason"] == "RUN_PROVIDER_OUTCOME_UNKNOWN"
                    and action != "retry_model"
                ):
                    raise DomainError("RUN_EXPLICIT_MODEL_RETRY_REQUIRED")
                run["state"], run["state_reason"] = "queued", None
            run["session_hash"], run["privacy_revision"] = session, self._revision()
            if action not in {"pause", "cancel"}:
                self._authorize(run)
            if action in {"cancel", "pause"}:
                for effect in run["effects"]:
                    effect.update(verify_proposal(self.runtime, effect["proposal_id"]))
            run["generation"] += 1
            run["lease_until"] = None
            with self.store.connection(write=True) as conn:
                self._save(conn, run, action)
                if action == "retry_model":
                    conn.execute(
                        "UPDATE agent_attempts SET state='interrupted' WHERE run_id=? AND state='running'",
                        (run_id,),
                    )
                conn.execute("INSERT INTO agent_run_operations VALUES(?,?,?)", (key, req, run_id))
            return {"run": self._view(run, hidden)}

    @staticmethod
    def _intent_hash(mutation):
        return fingerprint({"tool": mutation["tool"], "arguments": mutation["arguments"]})

    def _receipt_proposal(self, conn, key, intent_hash, *, strict=False):
        receipt = conn.execute(
            "SELECT response,request FROM operations WHERE id=?", (key,)
        ).fetchone()
        if not receipt:
            return None
        try:
            result = json.loads(receipt["response"])
            request = json.loads(receipt["request"])
            if request.get("type") != "assistant_draft":
                raise ValueError()
            proposal_id = result["proposal"]["id"]
            row = conn.execute(
                "SELECT * FROM assistant_proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if not row:
                raise ValueError()
            proposal = self.runtime.assistant._view(row)
            if proposal["kind"] != request["kind"] or proposal["data"] != request["data"]:
                raise ValueError()
            data = proposal["data"]
            mapping = {
                "task_create": ("task_create_draft", data.get("task")),
                "task_change": (
                    "task_change_draft",
                    {k: data.get(k) for k in ("task_id", "change")},
                ),
                "create": ("calendar_create_draft", data),
                "change": (
                    "calendar_change_draft",
                    {k: data.get(k) for k in ("event_id", "change")},
                ),
            }
            tool, arguments = mapping[proposal["kind"]]
            if fingerprint({"tool": tool, "arguments": arguments}) != intent_hash:
                raise ValueError()
            return proposal
        except (ValueError, KeyError, TypeError):
            if strict:
                raise DomainError("RUN_EFFECT_RECEIPT_CONFLICT", 409) from None
            return None

    def is_run_proposal(self, proposal_id):
        """Classify only canonical matching intents, including unlinked children."""
        with self.store.connection() as conn:
            intents = list(
                conn.execute("SELECT operation_key,intent_hash FROM agent_run_effect_intents")
            )
            for intent in intents:
                proposal = self._receipt_proposal(conn, intent[0], intent[1])
                if proposal and proposal["id"] == proposal_id:
                    return True
        return False

    def require_proposal_access(self, proposal_id, principal):
        if self.is_run_proposal(proposal_id):
            self.session(principal)

    def filter_proposals(self, proposals, principal):
        try:
            self.session(principal)
            visible = True
        except DomainError:
            visible = False
        return [p for p in proposals if visible or not self.is_run_proposal(p["id"])]

    def _cancel_pending(self, run):
        with self.runtime.assistant.lock, self.store.connection(write=True) as conn:
            intent = run.get("pending_effect")
            if intent:
                proposal = self._receipt_proposal(
                    conn, intent["key"], self._intent_hash(intent["mutation"])
                )
                if proposal:
                    pid = proposal["id"]
                    if pid not in run["proposal_ids"]:
                        run["proposal_ids"].append(pid)
                        run["effects"].append(
                            {
                                "proposal_id": pid,
                                "request_index": intent["request_index"],
                                "required": intent["mutation"]["required"],
                                "state": "pending",
                                "tool": intent["mutation"]["tool"],
                            }
                        )
                run["pending_effect"] = None
            for pid in run["proposal_ids"]:
                receipt = conn.execute(
                    "SELECT 1 FROM operations WHERE id=?", ("assistant-confirm/" + pid,)
                ).fetchone()
                if not receipt:
                    conn.execute(
                        "UPDATE assistant_proposals SET state='cancelled' WHERE id=? AND state='pending'",
                        (pid,),
                    )

    def shutdown(self):
        """Fence to_thread work before the application cancels its asyncio workers."""
        with self.lock:
            self.stopped = True
            with self.store.connection(write=True) as conn:
                rows = list(
                    conn.execute(
                        "SELECT id FROM agent_runs WHERE state IN ('queued','running','waiting_review','waiting_input')"
                    )
                )
                for row in rows:
                    run = self._get(conn, row[0])
                    active = conn.execute(
                        "SELECT 1 FROM agent_attempts WHERE run_id=? AND state='running'",
                        (run["id"],),
                    ).fetchone()
                    run["generation"] += 1
                    run["lease_until"] = None
                    run["state"] = "blocked" if active else "paused"
                    run["state_reason"] = (
                        "RUN_PROVIDER_OUTCOME_UNKNOWN" if active else "RUN_RUNTIME_STOPPED"
                    )
                    self._save(conn, run, "shutdown")

    def _checkpoint(self, run, kind, result=None):
        self._authorize(run)
        with self.lock, self.store.connection(write=True) as conn:
            current = self._get(conn, run["id"])
            if current["generation"] != run["generation"]:
                return False
            run["version"] = current["version"]
            run["pending_decision"] = None
            run["lease_until"] = None
            self._save(conn, run, kind)
            conn.execute(
                "INSERT INTO agent_steps VALUES(?,?,?,?,?,?,?,NULL)",
                (
                    uuid4().hex,
                    run["id"],
                    run["plan_revision"],
                    kind,
                    kind.replace("_", " "),
                    "succeeded",
                    encode(result or {}),
                ),
            )
            return True

    def advance_one(self):
        if self.stopped or not self.worker_lock.acquire(blocking=False):
            return False
        run = None
        try:
            with self.lock, self.store.connection(write=True) as conn:
                now = iso(self.store.clock())
                row = conn.execute(
                    "SELECT id FROM agent_runs WHERE state IN ('queued','running','waiting_review') AND (lease_until IS NULL OR lease_until<=?) ORDER BY updated_at,id LIMIT 1",
                    (now,),
                ).fetchone()
                if not row:
                    return False
                run = self._get(conn, row[0])
                if run["lease_until"] is not None:
                    # Reclaim fences a late worker whose lease expired; stable
                    # artifact/draft operation keys still reconcile its effects.
                    run["generation"] += 1
                interrupted = conn.execute(
                    "SELECT kind FROM agent_attempts WHERE run_id=? AND state='running'",
                    (run["id"],),
                ).fetchall()
                if interrupted:
                    conn.execute(
                        "UPDATE agent_attempts SET state='interrupted',error='restart' WHERE run_id=? AND state='running'",
                        (run["id"],),
                    )
                    if any(r[0] == "model" for r in interrupted):
                        run["state"], run["state_reason"] = (
                            "blocked",
                            "RUN_PROVIDER_OUTCOME_UNKNOWN",
                        )
                        run["lease_until"] = None
                        self._save(conn, run, "interrupted")
                        return True
                run["lease_until"] = iso(self.store.clock() + timedelta(seconds=60))
                conn.execute(
                    "UPDATE agent_runs SET lease_until=?,generation=? WHERE id=?",
                    (run["lease_until"], run["generation"], run["id"]),
                )
            self._authorize(run)
            if run.get("pending_effect"):
                return self._dispatch_effect(run)
            if run.get("pending_reads"):
                return self._batch_read(run)
            if run["state"] == "waiting_review":
                return self._review(run)
            if run["phase"] == "publish":
                return self._publish(run)
            if run["mode"] == "deterministic":
                return self._deterministic(run)
            return self._model(run)
        except DomainError as error:
            if run:
                self._block(run, error.code)
                return True
            raise
        except Exception:
            if run:
                self._block(run, "RUN_WORKER_ERROR")
            raise
        finally:
            self.worker_lock.release()

    def _block(self, run, code):
        with self.lock:
            with self.store.connection() as conn:
                current = self._get(conn, run["id"])
            if current["generation"] != run["generation"]:
                return
            self._cancel_pending(current)
            with self.store.connection(write=True) as conn:
                current["state"] = "blocked"
                current["state_reason"] = code
                current["lease_until"] = None
                self._save(conn, current, "blocked", {"code": code})

    def _read(self, run, selected, start_line=1, max_lines=200):
        evidence_id = selected["id"] + (
            f":L{start_line}" if start_line != 1 and selected["kind"] == "source" else ""
        )
        if any(e["id"] == evidence_id for e in run["evidence"]):
            raise DomainError("RUN_EVIDENCE_ALREADY_READ", 422)
        if run["reads"] >= 32:
            raise DomainError("RUN_READ_BUDGET_EXCEEDED", 422)
        evidence = read_evidence(
            self.runtime, run, selected["kind"], selected["record_id"], start_line, max_lines
        )
        run["evidence"].append(evidence)
        run["reads"] += 1
        run["state"] = "running"
        return self._checkpoint(
            run, "read", {"evidence_id": evidence["id"], "sha256": evidence["sha256"]}
        )

    def _deterministic(self, run):
        if run["phase"] == "collect":
            done = {e["id"] for e in run["evidence"]}
            remaining = [e for e in run["available_evidence"] if e["id"] not in done]
            if remaining:
                return self._read(run, remaining[0])
            run["report"] = compose(self.runtime, run, run["evidence"])
            run["report_evidence"] = json.loads(encode(run["evidence"]))
            run["phase"] = "publish"
            return self._checkpoint(run, "compose", {"mode": "deterministic"})
        for index, mutation in enumerate(run["mutation_requests"]):
            if not any(e.get("request_index") == index for e in run["effects"]):
                return self._propose(run, mutation, index)
        return self._finish(run)

    def _model(self, run):
        if run.get("pending_decision"):
            decision = AgentDecision.model_validate(run["pending_decision"])
        else:
            if run["model_calls"] >= 8:
                raise DomainError("RUN_MODEL_BUDGET_EXCEEDED", 422)
            self._authorize(run)
            attempt = uuid4().hex
            with self.lock, self.store.connection(write=True) as conn:
                current = self._get(conn, run["id"])
                if current["generation"] != run["generation"]:
                    return False
                run["version"] = current["version"]
                run["model_calls"] += 1
                run["state"] = "running"
                self._save(conn, run, "model_reserved", {"attempt_id": attempt})
                conn.execute(
                    "INSERT INTO agent_attempts VALUES(?,?,?,'model','running',?,NULL)",
                    (attempt, run["id"], run["generation"], iso(self.store.clock())),
                )
            try:
                decision = decide(self.runtime, run)
            except BaseException:
                raise DomainError("RUN_PROVIDER_OUTCOME_UNKNOWN", 409) from None
            self._authorize(run)
            with self.lock, self.store.connection(write=True) as conn:
                current = self._get(conn, run["id"])
                if current["generation"] != run["generation"]:
                    conn.execute(
                        "UPDATE agent_attempts SET state='discarded' WHERE id=?", (attempt,)
                    )
                    return False
                # Commit the returned structured decision with its attempt receipt.
                # Restart can apply this decision without another paid call.
                run["version"] = current["version"]
                run["pending_decision"] = decision.model_dump(mode="json")
                self._save(conn, run, "model_returned", {"attempt_id": attempt})
                conn.execute("UPDATE agent_attempts SET state='returned' WHERE id=?", (attempt,))
        if not run["plan"] and decision.action != "plan":
            raise DomainError("RUN_PLAN_REQUIRED", 422)
        if decision.action == "plan":
            if not decision.plan or any(not p.strip() or len(p) > 240 for p in decision.plan):
                raise DomainError("RUN_PLAN_INVALID", 422)
            run["plan"] = decision.plan
            return self._checkpoint(run, "plan", {"step_count": len(run["plan"])})
        if decision.action == "read":
            ids = decision.evidence_ids or ([decision.evidence_id] if decision.evidence_id else [])
            if not ids or len(set(ids)) != len(ids):
                raise DomainError("RUN_READ_INVALID", 422)
            available = {e["id"]: e for e in run["available_evidence"]}
            if not set(ids).issubset(available):
                raise DomainError("RUN_SOURCE_NOT_SELECTED", 403)
            run["pending_reads"] = [
                {
                    "selected": available[i],
                    "start_line": decision.start_line,
                    "max_lines": decision.max_lines,
                }
                for i in ids
            ]
            return self._checkpoint(run, "read_batch", {"count": len(ids)})
        if decision.action == "ask":
            if not decision.question:
                raise DomainError("RUN_QUESTION_REQUIRED", 422)
            run["question"], run["state"], run["state_reason"] = (
                decision.question,
                "waiting_input",
                "RUN_INPUT_REQUIRED",
            )
            return self._checkpoint(run, "question")
        if decision.action == "report":
            if not decision.report or not run["evidence"] or run["current_artifact_ids"]:
                raise DomainError("RUN_REPORT_NOT_AVAILABLE", 422)
            ids = {e["id"] for e in run["evidence"]}
            if any(not set(s.evidence_ids).issubset(ids) for s in decision.report.sections):
                raise DomainError("RUN_CITATION_INVALID", 422)
            run["report"], run["phase"] = decision.report.model_dump(), "publish"
            run["report_evidence"] = json.loads(encode(run["evidence"]))
            return self._checkpoint(run, "compose", {"mode": "model"})
        if decision.action == "propose":
            if not run["allow_mutation_proposals"] or not decision.mutation:
                raise DomainError("RUN_MUTATION_NOT_ALLOWED", 403)
            mutation = validate_mutation(decision.mutation, run["task_ids"], run["event_ids"])
            if mutation["tool"].endswith("change_draft"):
                target = mutation["arguments"].get("task_id", mutation["arguments"].get("event_id"))
                found = next(
                    (
                        e
                        for e in run["evidence"]
                        if e["record_id"] == target and e["kind"] in {"task", "event"}
                    ),
                    None,
                )
                if (
                    not found
                    or found["version"] != mutation["arguments"]["change"]["expected_version"]
                ):
                    raise DomainError("RUN_OBSERVED_VERSION_REQUIRED", 409)
            index = next(
                (
                    i
                    for i, m in enumerate(run["mutation_requests"])
                    if m == mutation
                    and not any(e.get("request_index") == i for e in run["effects"])
                ),
                None,
            )
            return self._propose(run, mutation, index)
        return self._finish(run)

    def _batch_read(self, run):
        entry = run["pending_reads"].pop(0)
        return self._read(run, entry["selected"], entry["start_line"], entry["max_lines"])

    def _propose(self, run, mutation, index):
        if len(run["effects"]) >= 3:
            raise DomainError("RUN_EFFECT_BUDGET_EXCEEDED", 422)
        self._authorize(run)
        with self.lock, self.store.connection(write=True) as conn:
            current = self._get(conn, run["id"])
            if current["generation"] != run["generation"]:
                return False
            run["version"] = current["version"]
            run["pending_effect"] = {
                "key": f"run/{run['id']}/effect/{uuid4().hex}",
                "mutation": mutation,
                "request_index": index,
            }
            # Intent and stable key precede the child draft. Recovery never asks a
            # model for a replacement decision after an uncertain local draft.
            self._save(conn, run, "effect_reserved")
            conn.execute(
                "INSERT INTO agent_run_effect_intents VALUES(?,?,?)",
                (run["pending_effect"]["key"], run["id"], self._intent_hash(mutation)),
            )
        return self._dispatch_effect(run)

    def _dispatch_effect(self, run):
        intent = run["pending_effect"]
        self._authorize(run)
        with self.lock:
            with self.store.connection() as conn:
                if self._get(conn, run["id"])["generation"] != run["generation"]:
                    return False
            mutation = intent["mutation"]
            with self.store.connection() as conn:
                proposal = self._receipt_proposal(
                    conn, intent["key"], self._intent_hash(mutation), strict=True
                )
            if proposal is None:
                self.runtime.assistant.tool(mutation["tool"], mutation["arguments"], intent["key"])
                with self.store.connection() as conn:
                    proposal = self._receipt_proposal(
                        conn, intent["key"], self._intent_hash(mutation), strict=True
                    )
                if proposal is None:
                    raise DomainError("RUN_EFFECT_RECEIPT_CONFLICT", 409)
            run["proposal_ids"].append(proposal["id"])
            run["effects"].append(
                {
                    "proposal_id": proposal["id"],
                    "request_index": intent["request_index"],
                    "required": mutation["required"],
                    "state": "pending",
                    "tool": mutation["tool"],
                }
            )
            run["pending_effect"] = None
            run["state"], run["state_reason"] = "waiting_review", "RUN_REVIEW_REQUIRED"
            return self._checkpoint(run, "proposal", {"proposal_id": proposal["id"]})

    def _review(self, run):
        changed = False
        for effect in run["effects"]:
            if effect["state"] != "pending":
                continue
            result = verify_proposal(self.runtime, effect["proposal_id"])
            if result["state"] == "pending":
                # Polling is read-only except the lease; no model calls or event flood.
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE agent_runs SET lease_until=? WHERE id=? AND generation=?",
                        (
                            iso(self.store.clock() + timedelta(seconds=1)),
                            run["id"],
                            run["generation"],
                        ),
                    )
                return False
            effect.update(result)
            changed = True
        if changed:
            run["state"], run["state_reason"] = "running", None
            run["phase"] = "decide" if run["mode"] == "model" else "effects"
            return self._checkpoint(
                run, "review_observed", {"states": [e["state"] for e in run["effects"]]}
            )
        return False

    def _publish(self, run):
        payloads = artifact_payloads(run, run["report_evidence"], run["report"])
        for index, payload in enumerate(payloads):
            self._authorize(run)
            result = self.runtime.artifacts.publish(
                payload,
                f"run/{run['id']}/v{run['plan_revision']}/artifact/{index}",
                session_hash=run["session_hash"],
                selected_source_ids=run["source_ids"],
                run_id=run["id"],
                step_id=None,
            )
            artifact = result["artifact"]
            if artifact["status"] != "verified":
                raise DomainError("RUN_ARTIFACT_OUTCOME_UNKNOWN", 409)
            if artifact["id"] not in run["artifact_ids"]:
                run["artifact_ids"].append(artifact["id"])
            if artifact["id"] not in run["current_artifact_ids"]:
                run["current_artifact_ids"].append(artifact["id"])
        run["phase"] = "decide" if run["mode"] == "model" else "effects"
        run["state"] = "running"
        return self._checkpoint(run, "artifacts", {"artifact_ids": run["current_artifact_ids"]})

    @staticmethod
    def _unmet(run):
        unmet = []
        for selected in run["available_evidence"]:
            matches = [
                e
                for e in run["report_evidence"]
                if e["kind"] == selected["kind"] and e["record_id"] == selected["record_id"]
            ]
            if not matches:
                unmet.append(
                    {"code": "RUN_SELECTED_EVIDENCE_UNREAD", "evidence_id": selected["id"]}
                )
                continue
            if (
                selected["kind"] != "source"
                and run["mode"] == "model"
                and any(e["coverage"].get("truncated") for e in matches)
            ):
                unmet.append({"code": "RUN_APP_EVIDENCE_PARTIAL", "evidence_id": selected["id"]})
            if selected["kind"] == "source":
                ranges = []
                for e in matches:
                    coverage = (
                        e.get("local_parser_coverage") if run["mode"] == "deterministic" else None
                    )
                    coverage = coverage or e["coverage"]
                    ranges.append((coverage["start_line"], coverage["end_line"]))
                end = 0
                for start, stop in sorted(ranges):
                    if start > end + 1:
                        break
                    end = max(end, stop)
                if end < matches[0]["coverage"]["total_lines"]:
                    unmet.append(
                        {
                            "code": "RUN_SOURCE_PARTIAL_COVERAGE",
                            "evidence_id": selected["id"],
                            "covered_through_line": end,
                            "total_lines": matches[0]["coverage"]["total_lines"],
                        }
                    )
        titles = {
            s["title"].strip().casefold() for s in (run.get("report") or {}).get("sections", [])
        }
        for required in run["outcome_requirements"]["required_sections"]:
            if required.strip().casefold() not in titles:
                unmet.append({"code": "RUN_REQUIRED_SECTION_MISSING", "section": required})
        return unmet

    def _finish(self, run):
        if len(run["current_artifact_ids"]) != 2:
            raise DomainError("RUN_REQUIRED_OUTPUT_MISSING", 409)
        for artifact_id in run["current_artifact_ids"]:
            artifact = self.runtime.artifacts.detail(artifact_id, session_hash=run["session_hash"])
            artifact = artifact.get("artifact", artifact)
            if artifact["status"] != "verified" or artifact["verification"] != "byte_readback":
                raise DomainError("RUN_ARTIFACT_OUTCOME_UNKNOWN", 409)
        for index, mutation in enumerate(run["mutation_requests"]):
            if mutation["required"] and not any(
                e.get("request_index") == index for e in run["effects"]
            ):
                raise DomainError("RUN_REQUIRED_EFFECT_MISSING", 409)
        for effect in run["effects"]:
            effect.update(verify_proposal(self.runtime, effect["proposal_id"]))
        run["unmet_requirements"] = self._unmet(run)
        if any(e["state"] == "pending" for e in run["effects"]):
            run["state"], run["state_reason"] = "waiting_review", "RUN_REVIEW_REQUIRED"
        elif run["unmet_requirements"]:
            run["state"], run["state_reason"] = "partial", "RUN_REQUIRED_EVIDENCE_UNMET"
        elif any(e["required"] and e["state"] != "verified" for e in run["effects"]):
            run["state"], run["state_reason"] = "partial", "RUN_REQUIRED_CHANGE_UNMET"
        else:
            run["state"], run["state_reason"] = (
                "succeeded",
                "RUN_OUTPUTS_VERIFIED_QUALITY_UNASSESSED",
            )
        return self._checkpoint(
            run, "outcome", {"state": run["state"], "quality": "not_semantically_checked"}
        )


def agent_run_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/agent-runs", dependencies=[Depends(owner)])

    def principal(request, authenticated):
        return {**authenticated, "session": request.cookies.get("desk_companion_session")}

    @router.get("/scope")
    def scope(request: Request, authenticated=Depends(owner)):
        return runtime.agent_runs.scope(principal(request, authenticated))

    @router.get("")
    def listing(request: Request, authenticated=Depends(owner)):
        return runtime.agent_runs.listing(principal(request, authenticated))

    @router.post("")
    def create(
        payload: RunCreate,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.agent_runs.create(payload, key, principal(request, authenticated))

    @router.get("/{run_id}")
    def detail(run_id: str, request: Request, authenticated=Depends(owner)):
        return runtime.agent_runs.detail(run_id, principal(request, authenticated))

    @router.post("/{run_id}/actions")
    def action(
        run_id: str,
        payload: RunAction,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.agent_runs.action(run_id, payload, key, principal(request, authenticated))

    return router
