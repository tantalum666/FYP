"""Single-host durable connector intents. No MCP result is an independent verifier."""

import hashlib
import json
import threading
from datetime import timedelta
from uuid import uuid4

from .contracts import ConnectorCall, ConnectorConfig
from .mcp_transport import McpHttpClient
from .schema import ConnectorError, canonical, check_schema, digest, validate
from ..calendar import iso

MAX_INTENTS = 1000
TERMINAL = {"observed_result", "unknown_effect", "failed", "rejected", "cancelled", "expired"}


class McpConnectorService:
    def __init__(self, runtime, configs=(), *, client_factory=McpHttpClient):
        self.runtime, self.store = runtime, runtime.store
        self.lock = threading.RLock()
        self.worker_lock = threading.Lock()
        self.stopped = False
        self.client_factory = client_factory
        self.configs = {}
        self.grants = {}
        for raw in configs:
            config = ConnectorConfig.model_validate(raw).model_copy(deep=True)
            if config.id in self.configs or len(self.configs) >= 8:
                raise ConnectorError("CONNECTOR_CONFIG_INVALID", 422)
            self.configs[config.id] = config
            for grant in config.tools:
                self.grants[config.grant_id(grant)] = (config, grant)
        with self.store.connection(write=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS connector_intents(
                id TEXT PRIMARY KEY, operation_key TEXT UNIQUE NOT NULL,
                request_hash TEXT NOT NULL, data TEXT NOT NULL)""")
            # Construction is single API process ownership/recovery, not a second live worker.
            for row in conn.execute("SELECT * FROM connector_intents").fetchall():
                data = json.loads(row["data"])
                if data["state"] in {"preflight", "dispatching"}:
                    data.update(
                        state="unknown_effect" if data["dispatched"] else "rejected",
                        code="CONNECTOR_INTERRUPTED",
                        claim=None,
                    )
                    self._save(conn, data)

    def _privacy(self):
        return digest(json.loads(json.dumps(self.runtime.personal_context.revision())))

    def _authority(self, session_hash, *, visible=True, privacy=None):
        with self.store.connection() as conn:
            if not conn.execute(
                "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                (session_hash, iso(self.store.clock())),
            ).fetchone():
                raise ConnectorError("CONNECTOR_SESSION_EXPIRED", 403)
            if visible and self.store.settings(conn)["hide_private"]:
                raise ConnectorError("PRIVATE_CONTEXT_HIDDEN", 403)
        if privacy is not None and self._privacy() != privacy:
            raise ConnectorError("CONNECTOR_PRIVACY_CHANGED", 403)

    def _session(self, principal, *, visible=True):
        if (
            not principal
            or principal.get("kind") != "owner"
            or type(principal.get("session")) is not str
        ):
            raise ConnectorError("OWNER_SIGN_IN_REQUIRED", 403)
        session_hash = hashlib.sha256(principal["session"].encode()).hexdigest()
        self._authority(session_hash, visible=visible)
        return session_hash

    def catalog_for_run(self):
        tools = []
        for tool_id, (config, grant) in sorted(self.grants.items()):
            tools.append(
                {
                    "tool_id": tool_id,
                    "connector_id": config.id,
                    "tool_name": grant.tool_name,
                    "effect": grant.effect,
                    "input_schema": json.loads(canonical(grant.input_schema)),
                    "descriptor_sha256": grant.descriptor_sha256,
                    "grant_sha256": config.fingerprint(grant),
                    "destination_scope": grant.destination_scope,
                    "endpoint": config.endpoint,
                    "data_policy": grant.data_policy,
                    "review_required": True,
                    "live_acceptance": "not_verified_here",
                }
            )
        return {"tools": tools, "scope_revision": digest(tools)}

    def catalog(self, principal):
        self._session(principal)
        return self.catalog_for_run()

    def _resolve(self, tool_id):
        if tool_id not in self.grants:
            raise ConnectorError("CONNECTOR_TOOL_NOT_GRANTED", 403)
        return self.grants[tool_id]

    def discover(self, connector_id, principal):
        session = self._session(principal)
        if connector_id not in self.configs:
            raise ConnectorError("CONNECTOR_NOT_CONFIGURED", 404)
        privacy = self._privacy()

        def checkpoint():
            self._authority(session, privacy=privacy)

        client = self.client_factory(self.configs[connector_id])
        result = client.discover(checkpoint)
        checkpoint()
        return {"connector_id": connector_id, "tools": result, "trusted": False}

    def validate_call(self, tool_id, arguments):
        config, grant = self._resolve(tool_id)
        canonical(arguments)
        validate(grant.input_schema, arguments)
        return config, grant

    def _descriptor(self, client, grant, checkpoint):
        found = client.discover(checkpoint).get(grant.tool_name)
        if not found or found["descriptor_sha256"] != grant.descriptor_sha256:
            raise ConnectorError("CONNECTOR_TOOL_CHANGED", 409)
        descriptor = found["descriptor"]
        check_schema(descriptor.get("inputSchema"))
        if "outputSchema" in descriptor:
            check_schema(descriptor["outputSchema"])
        execution = descriptor.get("execution", {})
        if type(execution) is not dict or execution.get("taskSupport") == "required":
            raise ConnectorError("CONNECTOR_TASKS_UNSUPPORTED", 422)
        return descriptor

    def _get(self, conn, intent_id):
        row = conn.execute("SELECT data FROM connector_intents WHERE id=?", (intent_id,)).fetchone()
        if not row:
            raise ConnectorError("CONNECTOR_INTENT_NOT_FOUND", 404)
        return json.loads(row["data"])

    def _save(self, conn, item):
        item["version"] += 1
        item["updated_at"] = iso(self.store.clock())
        conn.execute(
            "UPDATE connector_intents SET data=? WHERE id=?",
            (canonical(item, limit=131072).decode(), item["id"]),
        )

    @staticmethod
    def _public(item, *, hidden=False):
        keys = (
            "id",
            "state",
            "version",
            "code",
            "created_at",
            "updated_at",
            "expires_at",
            "dispatched",
            "cancel_requested",
            "verified",
        )
        result = {key: item[key] for key in keys}
        if not hidden:
            result.update(
                intent=item["intent"], intent_hash=item["intent_hash"], result=item.get("result")
            )
        return result

    def detail(self, intent_id, principal):
        self._session(principal, visible=False)
        with self.store.connection() as conn:
            item = self._get(conn, intent_id)
            hidden = self.store.settings(conn)["hide_private"]
        return self._public(item, hidden=hidden)

    def _prepare(
        self, tool_id, arguments, operation_id, session, *, run_id=None, provider_destination=None
    ):
        if self.stopped:
            raise ConnectorError("CONNECTOR_STOPPED", 409)
        config, grant = self.validate_call(tool_id, arguments)
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 160:
            raise ConnectorError("CONNECTOR_OPERATION_ID_REQUIRED", 422)
        arguments = json.loads(canonical(arguments))
        request = {
            "tool_id": tool_id,
            "arguments": arguments,
            "session_hash": session,
            "run_id": run_id,
            "grant_sha256": config.fingerprint(grant),
            "provider_destination": provider_destination,
        }
        request_hash = digest(request)
        # Dedupe before any network work, including uncertain/revoked historical receipts.
        with self.store.connection() as conn:
            old = conn.execute(
                "SELECT * FROM connector_intents WHERE operation_key=?", (operation_id,)
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise ConnectorError("CONNECTOR_OPERATION_CONFLICT", 409)
                return self._public(json.loads(old["data"]))
            if conn.execute("SELECT COUNT(*) FROM connector_intents").fetchone()[0] >= MAX_INTENTS:
                raise ConnectorError("CONNECTOR_HISTORY_LIMIT", 409)
        privacy = self._privacy()

        def checkpoint():
            self._authority(session, privacy=privacy)

        checkpoint()
        # Local preparation uses the operator-pinned schema/hash. Network discovery
        # belongs to explicit inspection and execute(), never the run control lock.
        intent = {
            "tool_id": tool_id,
            "connector_id": config.id,
            "tool_name": grant.tool_name,
            "endpoint": config.endpoint,
            "server_name": config.server_name,
            "server_version": config.server_version,
            "destination_scope": grant.destination_scope,
            "effect": grant.effect,
            "arguments": arguments,
            "data_policy": grant.data_policy,
            "descriptor_sha256": grant.descriptor_sha256,
            "grant_sha256": config.fingerprint(grant),
            "provider_destination": provider_destination,
            "notice": "All arguments are sent to this endpoint; server results are untrusted. No independent outcome verification.",
        }
        now = self.store.clock()
        item = {
            "id": uuid4().hex,
            "version": 1,
            "state": "review",
            "code": None,
            "intent": intent,
            "intent_hash": digest(intent),
            "session_hash": session,
            "privacy_revision": privacy,
            "run_id": run_id,
            "operation_key": operation_id,
            "dispatched": False,
            "cancel_requested": False,
            "verified": False,
            "claim": None,
            "result": None,
            "created_at": iso(now),
            "updated_at": iso(now),
            "expires_at": iso(now + timedelta(minutes=5)),
        }
        with self.lock, self.store.connection(write=True) as conn:
            checkpoint()
            old = conn.execute(
                "SELECT * FROM connector_intents WHERE operation_key=?", (operation_id,)
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise ConnectorError("CONNECTOR_OPERATION_CONFLICT", 409)
                return self._public(json.loads(old["data"]))
            if conn.execute("SELECT COUNT(*) FROM connector_intents").fetchone()[0] >= MAX_INTENTS:
                raise ConnectorError("CONNECTOR_HISTORY_LIMIT", 409)
            conn.execute(
                "INSERT INTO connector_intents VALUES(?,?,?,?)",
                (item["id"], operation_id, request_hash, canonical(item, limit=131072).decode()),
            )
        return self._public(item)

    def prepare(self, tool_id, arguments, operation_id, principal, *, public_only):
        ConnectorCall(arguments=arguments, public_only=public_only)
        session = self._session(principal)
        return self._prepare(tool_id, arguments, operation_id, session)

    def prepare_for_run(self, run, tool_id, arguments, operation_id, *, public_only):
        ConnectorCall(arguments=arguments, public_only=public_only)
        self.validate_run(run, tool_id, arguments)
        return self._prepare(
            tool_id,
            arguments,
            operation_id,
            run["session_hash"],
            run_id=run["id"],
            provider_destination=self._provider_destination(run),
        )

    def _provider_destination(self, run):
        settings = self.runtime.personal_context.settings()
        destination = next(
            (
                d
                for d in settings["destinations"]
                if d["kind"] == "text"
                and d["id"] == run.get("provider_destination_id")
                and d["id"] in settings["approved_destinations"]
            ),
            None,
        )
        if not destination:
            raise ConnectorError("CONNECTOR_PROVIDER_DESTINATION_CHANGED", 403)
        return {key: destination[key] for key in ("id", "kind", "provider", "endpoint")}

    def validate_run(self, run, tool_id, arguments):
        if (
            run.get("source_ids")
            or run.get("task_ids")
            or run.get("event_ids")
            or (run.get("personal_context") or {}).get("memory_ids")
            or (run.get("personal_context") or {}).get("conversation_id")
            or not run.get("share_connector_results_with_provider")
        ):
            raise ConnectorError("CONNECTOR_RUN_DATA_SCOPE", 403)
        if (
            tool_id not in run.get("connector_tool_ids", [])
            or run.get("connector_scope_revision") != self.catalog_for_run()["scope_revision"]
        ):
            raise ConnectorError("CONNECTOR_RUN_SCOPE_CHANGED", 403)
        self._authority(run["session_hash"])
        self._provider_destination(run)
        return self.validate_call(tool_id, arguments)

    def _binding(self, item):
        intent = item["intent"]
        destination = intent.get("provider_destination")
        if destination is not None and destination != self._provider_destination(
            {"provider_destination_id": destination["id"]}
        ):
            raise ConnectorError("CONNECTOR_PROVIDER_DESTINATION_CHANGED", 403)
        config, grant = self.validate_call(intent["tool_id"], intent["arguments"])
        if (
            digest(intent) != item["intent_hash"]
            or config.fingerprint(grant) != intent["grant_sha256"]
        ):
            raise ConnectorError("CONNECTOR_GRANT_CHANGED", 409)
        return config, grant

    def approve(self, intent_id, expected_version, intent_hash, principal, *, public_only):
        if public_only is not True:
            raise ConnectorError("CONNECTOR_PUBLIC_ACK_REQUIRED", 422)
        session = self._session(principal)
        with self.lock:
            with self.store.connection() as conn:
                item = self._get(conn, intent_id)
            if session != item["session_hash"]:
                raise ConnectorError("CONNECTOR_OWNER_SESSION_CHANGED", 403)
            self._authority(session, privacy=item["privacy_revision"])
            self._binding(item)
            if item["intent_hash"] != intent_hash:
                raise ConnectorError("CONNECTOR_INTENT_CHANGED", 409)
            if item["state"] != "review":
                # Repeat approval cannot dispatch; only the same exact intent is returned.
                if item["state"] in {
                    "queued",
                    "preflight",
                    "dispatching",
                    "observed_result",
                    "unknown_effect",
                }:
                    return self._public(item)
                raise ConnectorError("CONNECTOR_REVIEW_CLOSED", 409)
            if type(expected_version) is not int or item["version"] != expected_version:
                raise ConnectorError("CONNECTOR_VERSION_CONFLICT", 409)
            if item["expires_at"] <= iso(self.store.clock()):
                raise ConnectorError("CONNECTOR_REVIEW_EXPIRED", 409)
            item.update(state="queued", expires_at=iso(self.store.clock() + timedelta(seconds=60)))
            with self.store.connection(write=True) as conn:
                self._authority(session, privacy=item["privacy_revision"])
                self._binding(item)
                self._save(conn, item)
            return self._public(item)

    def _checkpoint(self, intent_id, claim, external):
        if self.stopped:
            raise ConnectorError("CONNECTOR_STOPPED", 409)
        external()
        with self.store.connection() as conn:
            item = self._get(conn, intent_id)
        if (
            item["claim"] != claim
            or item["cancel_requested"]
            or item["state"] not in {"preflight", "dispatching"}
        ):
            raise ConnectorError("CONNECTOR_CANCELLED", 409)
        if item["expires_at"] <= iso(self.store.clock()):
            raise ConnectorError("CONNECTOR_DEADLINE", 409)
        self._authority(item["session_hash"], privacy=item["privacy_revision"])
        self._binding(item)

    @staticmethod
    def _result(result, descriptor):
        canonical(result, limit=65536)
        content = result.get("content", [])
        if (
            type(content) is not list
            or len(content) > 32
            or type(result.get("isError", False)) is not bool
        ):
            raise ConnectorError("CONNECTOR_RESULT_INVALID", 502)
        texts = []
        for block in content:
            if (
                type(block) is not dict
                or block.get("type") != "text"
                or type(block.get("text")) is not str
            ):
                raise ConnectorError("CONNECTOR_RESULT_TYPE_UNSUPPORTED", 502)
            texts.append(block["text"])
        structured = result.get("structuredContent")
        if structured is not None and type(structured) is not dict:
            raise ConnectorError("CONNECTOR_RESULT_INVALID", 502)
        if "outputSchema" in descriptor:
            validate(descriptor["outputSchema"], structured)
        observed = {
            "text": texts,
            "structured_content": structured,
            "is_error": result.get("isError", False),
            "untrusted": True,
            "verified": False,
            "sha256": digest(result),
        }
        observed["snapshot_sha256"] = digest(observed)
        return observed

    def execute(self, intent_id, checkpoint=lambda: None):
        with self.lock, self.store.connection(write=True) as conn:
            item = self._get(conn, intent_id)
            if self.stopped or item["state"] != "queued":
                return self._public(item)
            claim = uuid4().hex
            item.update(state="preflight", claim=claim)
            self._save(conn, item)

        def fence():
            self._checkpoint(intent_id, claim, checkpoint)

        try:
            fence()
            config, grant = self._binding(item)
            client = self.client_factory(config)
            descriptor = self._descriptor(client, grant, fence)
            validate(descriptor["inputSchema"], item["intent"]["arguments"])
            fence()

            def dispatch():
                fence()
                with self.lock, self.store.connection(write=True) as conn:
                    current = self._get(conn, intent_id)
                    if (
                        current["claim"] != claim
                        or current["state"] != "preflight"
                        or current["cancel_requested"]
                    ):
                        raise ConnectorError("CONNECTOR_CANCELLED", 409)
                    self._authority(current["session_hash"], privacy=current["privacy_revision"])
                    self._binding(current)
                    current.update(state="dispatching", dispatched=True)
                    self._save(conn, current)

            result = client.call(
                grant.tool_name, item["intent"]["arguments"], descriptor, fence, dispatch
            )
            observed = self._result(result, descriptor)
            fence()
            state = (
                ("unknown_effect" if grant.effect == "write" else "failed")
                if observed["is_error"]
                else "observed_result"
            )
            code = "CONNECTOR_TOOL_ERROR" if observed["is_error"] else None
        except Exception as error:
            observed = None
            code = error.code if isinstance(error, ConnectorError) else "CONNECTOR_EXECUTION_FAILED"
            with self.store.connection() as conn:
                current = self._get(conn, intent_id)
            state = (
                "unknown_effect"
                if current["dispatched"]
                else ("cancelled" if current["cancel_requested"] else "rejected")
            )
        with self.lock, self.store.connection(write=True) as conn:
            current = self._get(conn, intent_id)
            if current["claim"] != claim:
                return self._public(current)
            if observed is not None:
                try:
                    self._authority(current["session_hash"], privacy=current["privacy_revision"])
                    self._binding(current)
                except ConnectorError as error:
                    state, observed, code = "unknown_effect", None, error.code
            if current["cancel_requested"]:
                state, observed = ("unknown_effect" if current["dispatched"] else "cancelled"), None
                code = "CONNECTOR_CANCELLED"
            current.update(state=state, result=observed, code=code, claim=None)
            try:
                canonical(current, limit=131072)
            except ConnectorError:
                # The normalized result may fit alone but not the complete ledger.
                # Persist a compact terminal uncertainty rather than strand dispatching.
                current.update(
                    state="unknown_effect" if current["dispatched"] else "rejected",
                    result=None,
                    code="CONNECTOR_RESULT_LIMIT",
                )
            self._save(conn, current)
        return self._public(current)

    def cancel(self, intent_id, principal, *, expected_version=None):
        self._session(principal, visible=False)
        return self.cancel_internal(intent_id, expected_version=expected_version)

    def cancel_internal(self, intent_id, *, expected_version=None):
        with self.lock, self.store.connection(write=True) as conn:
            item = self._get(conn, intent_id)
            if item["state"] not in TERMINAL and not item["cancel_requested"]:
                if expected_version is not None and (
                    type(expected_version) is not int or expected_version != item["version"]
                ):
                    raise ConnectorError("CONNECTOR_VERSION_CONFLICT", 409)
                item["cancel_requested"] = True
                if item["state"] in {"review", "queued"}:
                    item.update(state="cancelled", code="CONNECTOR_CANCELLED")
                self._save(conn, item)
            hidden = self.store.settings(conn)["hide_private"]
        return self._public(item, hidden=hidden)

    def recover_for_run(self, run, tool_id, arguments, operation_id):
        # Exact child matching remains available for cancellation while hidden/revoked.
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT data FROM connector_intents WHERE operation_key=?", (operation_id,)
            ).fetchone()
        if not row:
            return None
        item = json.loads(row[0])
        if (
            item["run_id"] != run["id"]
            or item["intent"]["tool_id"] != tool_id
            or canonical(item["intent"]["arguments"]) != canonical(arguments)
        ):
            raise ConnectorError("CONNECTOR_OPERATION_CONFLICT", 409)
        if digest(item["intent"]) != item["intent_hash"]:
            raise ConnectorError("CONNECTOR_INTENT_CHANGED", 409)
        observed = item.get("result")
        if observed and digest(
            {k: v for k, v in observed.items() if k != "snapshot_sha256"}
        ) != observed.get("snapshot_sha256"):
            raise ConnectorError("CONNECTOR_RESULT_CHANGED", 409)
        return self._public(item)

    def lookup_operation(self, operation_id, *, run_id, session_hash, tool_id, arguments):
        return self.recover_for_run(
            {"id": run_id, "session_hash": session_hash}, tool_id, arguments, operation_id
        )

    def listing(self, principal, *, limit=50, metadata_only=False):
        self._session(principal, visible=False)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ConnectorError("CONNECTOR_LIMIT_INVALID", 422)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT data FROM connector_intents ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
            hidden = metadata_only or self.store.settings(conn)["hide_private"]
        return {"intents": [self._public(json.loads(row[0]), hidden=hidden) for row in rows]}

    def advance_one(self):
        if self.stopped or not self.worker_lock.acquire(blocking=False):
            return False
        try:
            selected = None
            with self.lock, self.store.connection(write=True) as conn:
                for row in conn.execute(
                    "SELECT data FROM connector_intents ORDER BY rowid"
                ).fetchall():
                    item = json.loads(row[0])
                    if item["state"] not in {"review", "queued"}:
                        continue
                    if item["expires_at"] <= iso(self.store.clock()):
                        item.update(state="expired", code="CONNECTOR_REVIEW_EXPIRED")
                        self._save(conn, item)
                    elif item["state"] == "queued":
                        selected = item["id"]
                        break
            if selected:
                self.execute(selected)
                return True
            return False
        finally:
            self.worker_lock.release()

    def shutdown(self):
        with self.lock, self.store.connection(write=True) as conn:
            self.stopped = True
            for row in conn.execute("SELECT data FROM connector_intents").fetchall():
                item = json.loads(row[0])
                if item["state"] in {"queued", "preflight", "dispatching"}:
                    item.update(
                        state="unknown_effect" if item["dispatched"] else "cancelled",
                        cancel_requested=True,
                        claim=None,
                        code="CONNECTOR_STOPPED",
                    )
                    self._save(conn, item)


def build_connector_service(runtime, configs=()):
    return McpConnectorService(runtime, configs)
