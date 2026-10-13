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
from pydantic import ValidationError

from .agent_run_schemas import (
    RunCreate,
    RunAction,
    AgentDecision,
    RunToolCall,
    ToolObservation,
    ToolReceipt,
)
from .agent_planner import build_plan, compose, decide
from .agent_tools import (
    read_evidence,
    artifact_payloads,
    validate_mutation,
    verify_proposal,
    tool_registry,
    validate_tool_call,
    proposal_confirmation_request,
)
from .calendar import iso
from .agent_context import AgentContextBridge
from .context import fingerprint
from .store import DomainError, encode
from .text_ai import TextDispatchRefused

TERMINAL = {"succeeded", "partial", "failed", "cancelled"}


class AgentRunService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.lock, self.worker_lock = threading.RLock(), threading.Lock()
        self.stopped = False
        self.context_bridge = AgentContextBridge(runtime)
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
                CREATE TABLE IF NOT EXISTS agent_run_tool_intents(operation_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,tool TEXT NOT NULL,arguments TEXT NOT NULL,intent_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_voice_origins(reference_hash TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,run_id TEXT NOT NULL);
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
                "model_call_budget_max": 24,
                "tool_calls": 8,
                "tool_call_budget_max": 16,
                "plan_revisions": 2,
                "model_selected_items": 10,
                "source_bytes": 4194304,
            },
            "business_context_allowed": settings["share_business_context"],
            "browser": self.runtime.browser_jobs.capabilities(),
            "connectors": self._connector_catalog(),
            "personal_context": self.context_bridge.catalog(session_hash=session),
        }
        result["scope_revision"] = fingerprint([result, self.runtime.personal_context.revision()])
        return result

    def _connector_catalog(self):
        service = getattr(self.runtime, "connectors", None)
        return service.catalog_for_run() if service else {"tools": [], "scope_revision": None}

    def _validate_personal(self, run, conn=None):
        self.context_bridge.validate(
            run.get("personal_context_binding"),
            run_id=run["id"],
            session_hash=run["session_hash"],
            provider_destination_id=run.get("provider_destination_id"),
            conn=conn,
        )

    def _get(self, conn, run_id):
        row = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise DomainError("RUN_NOT_FOUND", 404)
        return {
            "browser_source_ids": [],
            "browser_public_only": False,
            "model_call_budget": 8,
            "tool_call_budget": 8,
            "tool_calls": 0,
            "browser_job_ids": [],
            "tool_results": [],
            "pending_tool": None,
            "tool_cancel_errors": [],
            "connector_tool_ids": [],
            "connector_scope_revision": None,
            "personal_context_binding": None,
            "share_connector_results_with_provider": False,
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
                "pending_tool",
                "personal_context_binding",
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
            "browser_jobs": [
                self.runtime.browser_jobs.detail(i, review=True)
                for i in run.get("browser_job_ids", [])
            ],
        }

    def create(self, payload, key, principal):
        session = self.session(principal)
        request_data = payload.model_dump(mode="json")
        if payload.voice_origin_ref is None:
            request_data.pop("voice_origin_ref")  # Preserve existing typed-create receipt hashes.
        request_hash = fingerprint(request_data)
        self._key(key)
        with self.lock:
            with self.store.connection() as conn:
                old = conn.execute(
                    "SELECT * FROM agent_run_operations WHERE id=?", (key,)
                ).fetchone()
                if old:
                    if old["request_hash"] != request_hash:
                        raise DomainError("OPERATION_ID_CONFLICT")
                    self.context_bridge._owner(conn, session)
                    return {"run": self._view(self._get(conn, old["run_id"]))}
                if (
                    payload.voice_origin_ref
                    and conn.execute(
                        "SELECT 1 FROM agent_voice_origins WHERE reference_hash=?",
                        (fingerprint(payload.voice_origin_ref),),
                    ).fetchone()
                ):
                    raise DomainError("VOICE_DRAFT_ALREADY_USED", 409)
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
            connector_ids = {t["tool_id"] for t in scope["connectors"]["tools"]}
            if not set(payload.connector_tool_ids).issubset(connector_ids):
                raise DomainError("RUN_CONNECTOR_NOT_SELECTED", 403)
            browser_ids = {s["id"] for s in scope["browser"]["sources"]}
            if not set(payload.browser_source_ids).issubset(browser_ids):
                raise DomainError("RUN_BROWSER_SOURCE_NOT_SELECTED", 403)
            if payload.browser_source_ids and not scope["browser"]["ready"]:
                raise DomainError(scope["browser"]["reason"] or "BROWSER_UNAVAILABLE", 409)
            selected_sources = [s for s in scope["sources"] if s["id"] in payload.source_ids]
            if sum(s["byte_count"] for s in selected_sources) > 4 * 1024 * 1024:
                raise DomainError("RUN_SOURCE_SIZE_LIMIT", 413)
            mutations = [
                validate_mutation(m, payload.task_ids, payload.event_ids)
                for m in payload.mutation_requests
            ]
            run_id, now = uuid4().hex, iso(self.store.clock())
            run = request_data | {
                "id": run_id,
                "connector_scope_revision": scope["connectors"]["scope_revision"],
                "personal_context_binding": self.context_bridge.bind(
                    payload.personal_context,
                    run_id=run_id,
                    session_hash=session,
                    provider_destination_id=payload.provider_destination_id,
                )
                if payload.personal_context
                else None,
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
                "pending_tool": None,
                "tool_results": [],
                "tool_calls": 0,
                "tool_cancel_errors": [],
                "browser_job_ids": [],
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
            run.pop("voice_origin_ref", None)
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
            run["available_evidence"].extend(
                {
                    "id": "browser:" + i["id"],
                    "kind": "browser",
                    "record_id": i["id"],
                    "label": i["label"],
                    "scope": "one_public_excerpt",
                }
                for i in scope["browser"]["sources"]
                if i["id"] in payload.browser_source_ids
            )
            if payload.mode == "deterministic":
                run["plan"] = [label for _, label in build_plan(mutations)]
            self._authorize(run)
            # Admission is one local transaction after preflight. Lock order matches
            # AgentContextBridge; no provider/network I/O occurs in this boundary.
            with (
                self.runtime.personal_context.lock,
                self.runtime.voice.work.lock,
                self.store.connection(write=True) as conn,
            ):
                self.context_bridge._owner(conn, session)
                revision = [
                    conn.execute("SELECT epoch FROM personal_settings WHERE id=1").fetchone()[0],
                    self.store.settings(conn)["version"],
                    [d["id"] for d in self.runtime.personal_context.destinations()],
                ]
                if run["privacy_revision"] != revision:
                    raise DomainError("RUN_CONTEXT_CHANGED", 403)
                # Scope is a bounded read-only catalog; the write transaction blocks
                # concurrent local source/task/calendar/consent changes until commit.
                if payload.scope_revision != self.scope(principal)["scope_revision"]:
                    raise DomainError("RUN_SCOPE_CHANGED", 409)
                self._validate_personal(run, conn)
                if payload.voice_origin_ref:
                    if conn.execute(
                        "SELECT 1 FROM agent_voice_origins WHERE reference_hash=?",
                        (fingerprint(payload.voice_origin_ref),),
                    ).fetchone():
                        raise DomainError("VOICE_DRAFT_ALREADY_USED", 409)
                    run["voice_origin"] = self.runtime.voice.work.resolve(
                        payload.voice_origin_ref, session_hash=session, goal=payload.goal, conn=conn
                    )
                    conn.execute(
                        "INSERT INTO agent_voice_origins VALUES(?,?,?)",
                        (fingerprint(payload.voice_origin_ref), request_hash, run_id),
                    )
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
        self._validate_personal(run)
        if (
            run.get("connector_tool_ids")
            and run.get("connector_scope_revision") != self._connector_catalog()["scope_revision"]
        ):
            raise DomainError("RUN_CONNECTOR_SCOPE_CHANGED", 403)
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
            if run.get("connector_tool_ids") and not run.get(
                "share_connector_results_with_provider"
            ):
                raise DomainError("RUN_CONNECTOR_SHARING_NOT_APPROVED", 403)
            if run["source_ids"] and not run["share_sources_with_provider"]:
                raise DomainError("RUN_SOURCE_SHARING_NOT_APPROVED", 403)
            if (run["task_ids"] or run["event_ids"]) and not settings["share_business_context"]:
                raise DomainError("PROVIDER_CONTEXT_NOT_APPROVED", 403)

    def publication_checkpoint(self, run, conn):
        """Atomic local publication/effect fence, without nested writes or I/O."""
        current = conn.execute(
            "SELECT generation,state FROM agent_runs WHERE id=?", (run["id"],)
        ).fetchone()
        if (
            self.stopped
            or not current
            or current["generation"] != run["generation"]
            or current["state"] in TERMINAL | {"paused", "blocked"}
        ):
            raise DomainError("RUN_CONTROL_CHANGED", 409)
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (run["session_hash"], iso(self.store.clock())),
        ).fetchone():
            raise DomainError("RUN_SESSION_EXPIRED", 403)
        settings = self.store.settings(conn)
        if settings["hide_private"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        revision = [
            conn.execute("SELECT epoch FROM personal_settings WHERE id=1").fetchone()[0],
            settings["version"],
            [d["id"] for d in self.runtime.personal_context.destinations()],
        ]
        if run["privacy_revision"] != revision:
            raise DomainError("RUN_CONTEXT_CHANGED", 403)
        if iso(self.store.clock()) >= run["deadline"]:
            raise DomainError("RUN_DEADLINE_EXCEEDED", 409)
        self._validate_personal(run, conn)

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
                run["evidence"] = [e for e in run["evidence"] if e["kind"] in {"source", "browser"}]
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
                    if effect.get("kind") != "tool":
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

    def _proposal_runs(self, conn, proposal_id):
        for intent in conn.execute(
            "SELECT operation_key,intent_hash,run_id FROM agent_run_effect_intents"
        ):
            proposal = self._receipt_proposal(conn, intent["operation_key"], intent["intent_hash"])
            if proposal and proposal["id"] == proposal_id:
                yield self._get(conn, intent["run_id"])

    def require_proposal_access(self, proposal_id, principal, *, action="confirm"):
        with self.store.connection() as conn:
            runs = list(self._proposal_runs(conn, proposal_id))
        if runs:
            self.session(principal)
            if action == "confirm":
                for run in runs:
                    self._authorize(run)

    def guard_operation(self, conn, key, request):
        """Installed by Runtime at Store's transaction boundary; legacy work unchanged."""
        prefix = "assistant-confirm/"
        if not key.startswith(prefix):
            return
        for run in self._proposal_runs(conn, key[len(prefix) :]):
            row = conn.execute(
                "SELECT kind,data FROM assistant_proposals WHERE id=?", (key[len(prefix) :],)
            ).fetchone()
            try:
                expected = proposal_confirmation_request(row["kind"], json.loads(row["data"]))
            except (KeyError, ValueError, ValidationError):
                raise DomainError("RUN_EFFECT_RECEIPT_CONFLICT", 409) from None
            if request != expected:
                raise DomainError("RUN_EFFECT_RECEIPT_CONFLICT", 409)
            self.publication_checkpoint(run, conn)

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

        self._cancel_tool_work(run)

    def shutdown(self):
        """Fence work and queued child effects before asynchronous worker cancellation."""
        with self.lock:
            self.stopped = True
            with self.store.connection() as conn:
                rows = [
                    self._get(conn, r[0])
                    for r in conn.execute(
                        "SELECT id FROM agent_runs WHERE state IN ('queued','running','waiting_review','waiting_input')"
                    )
                ]
            for run in rows:
                # Child services own separate SQLite transactions. Never hold a
                # parent write transaction while cancelling their durable work.
                self._cancel_pending(run)
                with self.store.connection(write=True) as conn:
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
            self.publication_checkpoint(run, conn)
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
            if run.get("pending_tool"):
                return self._dispatch_tool(run)
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
        if selected["kind"] not in {"source", "task", "event"}:
            raise DomainError("RUN_REGISTERED_TOOL_REQUIRED", 422)
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
            if run["model_calls"] >= run.get("model_call_budget", 8):
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
            except TextDispatchRefused:
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE agent_attempts SET state='dispatch_refused' WHERE id=?", (attempt,)
                    )
                raise
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
                self.publication_checkpoint(run, conn)
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
        if decision.action == "tool":
            if not decision.tool_call:
                raise DomainError("RUN_TOOL_CALL_REQUIRED", 422)
            return self._propose_tool(run, decision.tool_call)
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

    def _propose_tool(self, run, call):
        adapter, arguments = validate_tool_call(self.runtime, run, call)
        signature = fingerprint({"tool": call.tool, "arguments": arguments})
        key = f"run/{run['id']}/tool/{signature[:32]}"
        existing = next((r for r in run["tool_results"] if r["operation_key"] == key), None)
        if existing:
            # Identical intent never repeats an external action, including an
            # unknown or rejected outcome. Required cannot be downgraded later.
            for effect in run["effects"]:
                if effect.get("operation_key") == key:
                    effect["required"] = effect["required"] or call.required
            return self._checkpoint(
                run, "tool_reused", {"tool": call.tool, "reference_id": existing["reference_id"]}
            )
        if run["tool_calls"] >= run["tool_call_budget"]:
            raise DomainError("RUN_TOOL_BUDGET_EXCEEDED", 422)
        if adapter.effect and len(run["effects"]) >= 3:
            raise DomainError("RUN_EFFECT_BUDGET_EXCEEDED", 422)
        self._authorize(run)
        with self.lock, self.store.connection(write=True) as conn:
            current = self._get(conn, run["id"])
            if current["generation"] != run["generation"]:
                return False
            reserved = conn.execute(
                "SELECT * FROM agent_run_tool_intents WHERE operation_key=?", (key,)
            ).fetchone()
            if reserved and (
                reserved["run_id"] != run["id"] or reserved["intent_hash"] != signature
            ):
                raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
            if not reserved:
                conn.execute(
                    "INSERT INTO agent_run_tool_intents VALUES(?,?,?,?,?)",
                    (key, run["id"], call.tool, encode(arguments), signature),
                )
            run["version"] = current["version"]
            run["pending_tool"] = {
                "operation_key": key,
                "tool": call.tool,
                "arguments": arguments,
                "required": call.required,
            }
            run["tool_calls"] += 1
            self._save(conn, run, "tool_reserved", {"tool": call.tool})
        return self._dispatch_tool(run)

    def _tool_adapter(self, intent, run):
        adapter = tool_registry(self.runtime).get(intent["tool"])
        if adapter is None:
            raise DomainError("RUN_TOOL_UNAVAILABLE", 409)
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_run_tool_intents WHERE operation_key=?",
                (intent["operation_key"],),
            ).fetchone()
        signature = fingerprint({"tool": intent["tool"], "arguments": intent["arguments"]})
        if (
            not row
            or row["run_id"] != run["id"]
            or row["intent_hash"] != signature
            or row["tool"] != intent["tool"]
            or json.loads(row["arguments"]) != intent["arguments"]
        ):
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        return adapter

    def _link_tool(self, run, intent, receipt):
        try:
            receipt = ToolReceipt.model_validate(receipt).model_dump(mode="json")
        except ValidationError:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409) from None
        record = {k: intent[k] for k in ("tool", "arguments", "operation_key")}
        record.update({k: receipt[k] for k in ("reference_id", "state", "result")})
        if len(encode(record).encode()) > 24000:
            raise DomainError("RUN_TOOL_RESULT_LIMIT", 422)
        old = next(
            (r for r in run["tool_results"] if r["operation_key"] == intent["operation_key"]), None
        )
        if old and old["reference_id"] != record["reference_id"]:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        if not old:
            run["tool_results"].append(record)
        adapter = self._tool_adapter(intent, run)
        if adapter.effect and not any(
            e.get("operation_key") == intent["operation_key"] for e in run["effects"]
        ):
            run["effects"].append(
                {
                    **record,
                    "kind": "tool",
                    "state": "pending",
                    "required": intent["required"],
                    "request_index": None,
                }
            )
        browser_id = record["result"].get("browser_job_id")
        if browser_id and browser_id not in run["browser_job_ids"]:
            run["browser_job_ids"].append(browser_id)
        return record

    def _dispatch_tool(self, run):
        intent = run["pending_tool"]
        self._authorize(run)
        adapter = self._tool_adapter(intent, run)
        validate_tool_call(
            self.runtime,
            run,
            RunToolCall(
                tool=intent["tool"], arguments=intent["arguments"], required=intent["required"]
            ),
        )

        def checkpoint():
            self._authorize(run)

        # Preparation is local and serialized against parent cancel. Reads can
        # be slow and run outside the lock with an explicit generation fence.
        if adapter.effect:
            with self.lock:
                checkpoint()
                receipt = adapter.dispatch(
                    self.runtime, run, intent["arguments"], intent["operation_key"], checkpoint
                )
                self._link_tool(run, intent, receipt)
                run["pending_tool"] = None
                run["state"], run["state_reason"] = "waiting_review", "RUN_REVIEW_REQUIRED"
                return self._checkpoint(
                    run,
                    "tool_prepared",
                    {"tool": intent["tool"], "reference_id": receipt["reference_id"]},
                )
        receipt = adapter.dispatch(
            self.runtime, run, intent["arguments"], intent["operation_key"], checkpoint
        )
        checkpoint()
        self._link_tool(run, intent, receipt)
        if receipt.get("evidence"):
            self._adopt_tool_evidence(run, receipt["evidence"])
        run["pending_tool"] = None
        run["state"], run["state_reason"] = "running", None
        return self._checkpoint(
            run, "tool_observed", {"tool": intent["tool"], "state": receipt["state"]}
        )

    def _adopt_tool_evidence(self, run, evidence):
        try:
            value = ToolObservation.model_validate(evidence).model_dump(mode="json")
        except ValidationError:
            raise DomainError("RUN_TOOL_EVIDENCE_INVALID", 422) from None
        selected = (
            run.get("browser_source_ids", [])
            if value["kind"] == "browser"
            else run.get("connector_tool_ids", [])
        )
        if value["record_id"] not in selected:
            raise DomainError("RUN_TOOL_EVIDENCE_NOT_SELECTED", 403)
        if len(encode(value).encode()) > 12000:
            raise DomainError("RUN_TOOL_EVIDENCE_LIMIT", 422)
        prior = next((e for e in run["evidence"] if e["id"] == value["id"]), None)
        if prior:
            if prior != value:
                raise DomainError("RUN_TOOL_EVIDENCE_CHANGED", 409)
            return
        if run["reads"] >= 32:
            raise DomainError("RUN_READ_BUDGET_EXCEEDED", 422)
        run["evidence"].append(value)
        run["reads"] += 1

    def _cancel_tool_work(self, run):
        pending = run.get("pending_tool")
        if pending:
            try:
                adapter = self._tool_adapter(pending, run)
                receipt = adapter.recover(
                    self.runtime, run, pending["arguments"], pending["operation_key"]
                )
                if receipt:
                    self._link_tool(run, pending, receipt)
                run["pending_tool"] = None
            except DomainError as exc:
                run["tool_cancel_errors"] = list(
                    dict.fromkeys([*run["tool_cancel_errors"], exc.code])
                )
        for receipt in run.get("tool_results", []):
            try:
                adapter = self._tool_adapter(receipt, run)
                if adapter.effect:
                    adapter.cancel(self.runtime, run, receipt)
                    result = self._verify_effect(run, receipt)
                    for effect in run["effects"]:
                        if effect.get("operation_key") == receipt["operation_key"]:
                            effect.update(result)
                    self._sync_tool_result(run, receipt, result)
            except DomainError as exc:
                run["tool_cancel_errors"] = list(
                    dict.fromkeys([*run["tool_cancel_errors"], exc.code])
                )

    def _verify_effect(self, run, effect):
        if effect.get("kind") != "tool" and "operation_key" not in effect:
            return verify_proposal(self.runtime, effect["proposal_id"])
        try:
            adapter = self._tool_adapter(effect, run)
            result = adapter.verify(self.runtime, run, effect)
            if (
                result.get("state")
                not in {"pending", "verified", "observed", "unknown", "rejected"}
                or len(encode(result).encode()) > 24000
            ):
                raise DomainError("RUN_TOOL_RESULT_INVALID", 422)
            if result.get("evidence"):
                self._adopt_tool_evidence(run, result["evidence"])
                result = {k: v for k, v in result.items() if k != "evidence"}
            return result
        except DomainError as exc:
            if exc.code in {"BROWSER_BUSY", "CONNECTOR_BUSY"}:
                return {"state": "pending", "code": exc.code}
            return {"state": "unknown", "code": exc.code}

    @staticmethod
    def _sync_tool_result(run, effect, result):
        key = effect.get("operation_key")
        if key is not None:
            for receipt in run["tool_results"]:
                if receipt["operation_key"] == key:
                    receipt["state"] = result["state"]
                    receipt["result"] = {**receipt["result"], **result}

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
            result = self._verify_effect(run, effect)
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
            self._sync_tool_result(run, effect, result)
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
                checkpoint=lambda conn: self.publication_checkpoint(run, conn),
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
                selected["kind"] in {"task", "event"}
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
            result = self._verify_effect(run, effect)
            effect.update(result)
            self._sync_tool_result(run, effect, result)
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
