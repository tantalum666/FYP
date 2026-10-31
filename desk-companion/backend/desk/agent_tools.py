"""Code-owned reads, artifact encoding and independent local-effect verification."""

import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation, localcontext
from datetime import datetime

from typing import Protocol

from pydantic import ValidationError, Field

from .assistant import ChangeProposal
from .calendar import iso
from .schemas import CreateEvents, EventInput, EventAction, StrictModel
from .browser_policy import BrowserJobInput, PublicObservationInput, SOURCE_CATALOG
from .store import DomainError, encode
from .tasks import TaskChange, TaskInput, TaskAction


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def validate_mutation(mutation, task_ids, event_ids):
    schemas = {
        "task_create_draft": TaskInput,
        "task_change_draft": TaskChange,
        "calendar_create_draft": CreateEvents,
        "calendar_change_draft": ChangeProposal,
    }
    try:
        value = schemas[mutation.tool].model_validate(mutation.arguments).model_dump(mode="json")
    except (ValidationError, KeyError):
        raise DomainError("RUN_MUTATION_INVALID", 422) from None
    if mutation.tool == "task_change_draft" and value["task_id"] not in task_ids:
        raise DomainError("RUN_TARGET_NOT_SELECTED", 403)
    if mutation.tool == "calendar_change_draft" and value["event_id"] not in event_ids:
        raise DomainError("RUN_TARGET_NOT_SELECTED", 403)
    return {"tool": mutation.tool, "arguments": value, "required": mutation.required}


def table_stats(text):
    """Local bounded CSV counts/sums; no expressions, coercive mixed-unit inference or code."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {"rows": 0, "columns": []}
    columns, records = rows[0], rows[1:]
    if (
        len(columns) > 80
        or len(records) > 10000
        or any(len(row) != len(columns) for row in records)
    ):
        raise DomainError("RUN_CSV_SHAPE_UNSUPPORTED", 422)
    sums = {}
    for index, name in enumerate(columns):
        values = [row[index].strip() for row in records if row[index].strip()]
        try:
            numbers = [Decimal(v) for v in values]
            if values and all(
                n.is_finite() and abs(n) <= Decimal("1e30") and n.as_tuple().exponent >= -20
                for n in numbers
            ):
                # At most 10,000 terms of <=31 integer and20 fractional digits;
                # 64 decimal digits preserves the exact admitted sum.
                with localcontext() as context:
                    context.prec = 64
                    sums[name] = str(sum(numbers))
        except InvalidOperation:
            continue
    return {
        "rows": len(records),
        "columns": columns,
        "numeric_column_sums": sums,
        "notice": "Unweighted sums of entirely numeric nonempty cells within absolute 1e30 and20 decimal places; other columns omitted. Units are not inferred.",
    }


def read_evidence(runtime, run, kind, item_id, start_line=1, max_lines=200):
    now = iso(runtime.store.clock())
    if kind == "source":
        args = dict(
            session_hash=run["session_hash"], selected_ids=run["source_ids"], coverage_id=run["id"]
        )
        source = runtime.sources.read(
            item_id,
            **args,
            start_line=start_line,
            max_lines=max_lines,
            max_bytes=1800 if run["mode"] == "model" else 12288,
        )
        full = runtime.sources.read_all(item_id, **args) if run["mode"] == "deterministic" else None
        text = full["content"] if full else source["content"]
        stats = table_stats(text) if full and source["format"] == "csv" else None
        return {
            "id": "source:" + item_id + (f":L{start_line}" if start_line != 1 else ""),
            "kind": kind,
            "record_id": item_id,
            "label": source["name"],
            "sha256": source["sha256"],
            "version": 1,
            "at": now,
            "excerpt": source["content"],
            "coverage": {
                "start_line": source["start_line"],
                "end_line": source["end_line"],
                "total_lines": source["total_lines"],
                "excerpt_characters": len(source["content"]),
                "truncated": source["truncated"],
            },
            "statistics": stats,
            "local_parser_coverage": {"start_line": 1, "end_line": full["total_lines"]}
            if full
            else None,
            "provenance": {
                "source_id": item_id,
                "source_revision": 1,
                "start_line": source["start_line"],
                "end_line": source["end_line"],
            },
        }
    with runtime.store.connection() as conn:
        if kind == "task":
            data = runtime.tasks.get(conn, item_id)
            # Evidence notes are bounded independently of old task-history length.
            notes = [
                dict(r)
                for r in conn.execute(
                    "SELECT kind,note,task_version,source FROM task_evidence WHERE task_id=? ORDER BY id DESC LIMIT 10",
                    (item_id,),
                )
            ]
            body = {"task": data, "recent_evidence": notes}
        else:
            data = runtime.store.event(conn, item_id)
            exceptions = [
                dict(r)
                for r in conn.execute(
                    "SELECT occurrence_key,data FROM exceptions WHERE event_id=? ORDER BY occurrence_key LIMIT 20",
                    (item_id,),
                )
            ]
            body = {"event": data, "exceptions": exceptions}
    text = encode(body)
    return {
        "id": kind + ":" + item_id,
        "kind": kind,
        "record_id": item_id,
        "label": data["title"],
        "sha256": sha(text),
        "version": data["version"],
        "at": now,
        "excerpt": text[:1800],
        "coverage": {"truncated": len(text) > 1800, "excerpt_characters": min(len(text), 1800)},
        "statistics": None,
        "provenance": None,
    }


def artifact_payloads(run, evidence, report):
    from .artifacts import ArtifactInput

    by_id = {e["id"]: e for e in evidence}
    lines = [
        "# Work package",
        "",
        "Goal: " + run["goal"],
        "",
        "Mode: " + run["mode"],
        "",
        report["summary"],
        "",
    ]
    for section in report["sections"]:
        lines.extend(
            [
                "## " + section["title"],
                "",
                section["text"],
                "",
                "Evidence: " + ", ".join(section["evidence_ids"]),
                "",
            ]
        )
    lines.extend(["## Evidence register", ""])
    for e in evidence:
        lines.append(
            f"- {e['id']} | {e['label']} | observed {e['at']} | SHA-256 {e['sha256']} | coverage {encode(e['coverage'])}"
        )
        if e["statistics"]:
            lines.append("  Deterministic CSV statistics: " + encode(e["statistics"]))
    lines.extend(
        [
            "",
            "## Limits",
            *["- " + s for s in report["limitations"]],
            "- File byte verification does not establish factual accuracy or completion of the owner's broader goal.",
            "- Requested application changes are reviewed separately; inspect the run's verification results.",
        ]
    )
    used = {i for s in report["sections"] for i in s["evidence_ids"]}
    if not used.issubset(by_id):
        raise DomainError("RUN_CITATION_INVALID", 422)
    provenance = [
        e["provenance"]
        for e in evidence
        if e["provenance"] and e["provenance"]["end_line"] >= e["provenance"]["start_line"]
    ]
    common = dict(
        provenance=provenance, authorship="model" if run["mode"] == "model" else "deterministic"
    )
    return [
        ArtifactInput(
            format="markdown",
            display_name=f"Work report v{run['plan_revision']}",
            content="\n".join(lines),
            **common,
        ),
        ArtifactInput(
            format="csv",
            display_name=f"Evidence register v{run['plan_revision']}",
            content={
                "columns": [
                    "evidence_id",
                    "kind",
                    "label",
                    "sha256",
                    "observed_at",
                    "coverage",
                    "statistics",
                ],
                "rows": [
                    [
                        e["id"],
                        e["kind"],
                        e["label"],
                        e["sha256"],
                        e["at"],
                        encode(e["coverage"]),
                        encode(e["statistics"]),
                    ]
                    for e in evidence
                ],
            },
            provenance=provenance,
            authorship="deterministic",
        ),
    ]


def proposal_confirmation_request(kind, payload):
    """Canonical request to the existing service, bound to the exact reviewed draft."""
    if kind == "task_create":
        return {
            "type": "task_create",
            "data": TaskInput.model_validate(payload["task"]).model_dump(mode="json"),
        }
    if kind == "task_change":
        return {
            "type": "task_action",
            "id": payload["task_id"],
            **TaskAction.model_validate(payload["change"]).model_dump(mode="json"),
        }
    if kind == "create":
        return {"type": "create", **CreateEvents.model_validate(payload).model_dump(mode="json")}
    if kind == "change":
        return {
            "type": "event_action",
            "id": payload["event_id"],
            **EventAction.model_validate(payload["change"]).model_dump(mode="json"),
        }
    raise DomainError("RUN_EFFECT_RECEIPT_CONFLICT", 409)


def verify_proposal(runtime, proposal_id):
    """Read the durable commit receipt and independently inspect actual current rows."""
    with runtime.store.connection() as conn:
        row = conn.execute(
            "SELECT * FROM assistant_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        if not row:
            return {"state": "unknown", "code": "RUN_PROPOSAL_MISSING"}
        receipt = conn.execute(
            "SELECT response,request FROM operations WHERE id=?",
            ("assistant-confirm/" + proposal_id,),
        ).fetchone()
        if not receipt:
            if row["state"] == "cancelled":
                return {"state": "rejected", "code": "RUN_CHANGE_REJECTED"}
            if row["state"] == "pending" and row["expires_at"] > iso(runtime.store.clock()):
                return {"state": "pending", "code": "RUN_REVIEW_REQUIRED"}
            return {"state": "unknown", "code": "RUN_REVIEW_EXPIRED"}
        result, payload = json.loads(receipt["response"]), json.loads(row["data"])
        try:
            if json.loads(receipt["request"]) != proposal_confirmation_request(
                row["kind"], payload
            ):
                return {"state": "unknown", "code": "RUN_EFFECT_RECEIPT_CONFLICT"}
            if row["kind"] in {"task_create", "task_change"}:
                saved = result["task"]
                actual = runtime.tasks.get(conn, saved["id"])
                if any(actual.get(k) != v for k, v in saved.items()):
                    return {"state": "unknown", "code": "RUN_SAVED_RESULT_CHANGED"}
                if row["kind"] == "task_change" and payload["change"]["action"] == "note":
                    found = conn.execute(
                        "SELECT 1 FROM task_evidence WHERE task_id=? AND task_version=? AND note=?",
                        (saved["id"], saved["version"], payload["change"]["note"].strip()),
                    ).fetchone()
                    if not found:
                        return {"state": "unknown", "code": "RUN_RESULT_NOT_VERIFIED"}
                return {
                    "state": "verified",
                    "record_id": saved["id"],
                    "version": saved["version"],
                    "sha256": sha(encode(actual)),
                }
            if row["kind"] == "create":
                # Calendar creation receipts are IDs; compare requested canonical fields.
                ids = result["event_ids"]
                request = CreateEvents.model_validate(payload)
                base = request.event
                dates = [base.start_local.date(), *request.additional_dates]
                if len(ids) != len(dates):
                    raise ValueError()
                for eid, day in zip(ids, dates, strict=True):
                    actual = runtime.store.event(conn, eid)
                    start = datetime.combine(day, base.start_local.time())
                    expected = EventInput.model_validate(
                        {
                            **base.model_dump(),
                            "start_local": start,
                            "end_local": start + (base.end_local - base.start_local),
                        }
                    ).model_dump(mode="json")
                    if actual["version"] != 1 or any(
                        actual.get(k) != v for k, v in expected.items()
                    ):
                        return {"state": "unknown", "code": "RUN_SAVED_RESULT_CHANGED"}
                return {"state": "verified", "record_ids": ids, "receipt_hash": sha(encode(result))}
            if row["kind"] == "change":
                eid, change = payload["event_id"], payload["change"]
                current = conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
                if not current or current["version"] != result["version"]:
                    return {"state": "unknown", "code": "RUN_SAVED_RESULT_CHANGED"}
                if change["scope"] == "series":
                    if change["action"] == "delete" and not current["deleted"]:
                        raise ValueError()
                    if change["action"] == "update" and current["deleted"]:
                        raise ValueError()
                    if change["action"] == "update" and any(
                        json.loads(current["data"]).get(k) != v for k, v in change["event"].items()
                    ):
                        raise ValueError()
                else:
                    ex = conn.execute(
                        "SELECT data FROM exceptions WHERE event_id=? AND occurrence_key=?",
                        (eid, change["occurrence_key"]),
                    ).fetchone()
                    if not ex:
                        raise ValueError()
                    ex = json.loads(ex[0])
                    expected = {
                        "delete": ("cancelled", True),
                        "complete": ("completed", True),
                        "reopen": ("completed", False),
                        "update": ("override", change.get("event")),
                    }[change["action"]]
                    if ex.get(expected[0]) != expected[1]:
                        raise ValueError()
                return {
                    "state": "verified",
                    "record_id": eid,
                    "version": current["version"],
                    "receipt_hash": sha(encode(result)),
                }
        except (KeyError, ValueError, DomainError):
            return {"state": "unknown", "code": "RUN_RESULT_NOT_VERIFIED"}
    return {"state": "unknown", "code": "RUN_RESULT_NOT_VERIFIED"}


# The registry is code-owned. Providers may select a registered name and strictly
# validated arguments; they never register callbacks, schemas, targets or grants.


class AgentToolAdapter(Protocol):
    name: str
    effect: bool
    schema: type[StrictModel]

    def available(self, runtime, run) -> bool: ...
    def validate(self, runtime, run, arguments: dict) -> dict: ...
    def dispatch(self, runtime, run, arguments: dict, key: str, checkpoint) -> dict: ...
    def recover(self, runtime, run, arguments: dict, key: str) -> dict | None: ...
    def verify(self, runtime, run, receipt: dict) -> dict: ...
    def cancel(self, runtime, run, receipt: dict) -> dict | None: ...


class PublicSourceArguments(StrictModel):
    source_id: str = Field(min_length=1, max_length=64)


class PublicBriefArguments(StrictModel):
    observation_id: str = Field(pattern=r"^[a-f0-9]{32}$")


def _browser_selected(runtime, run):
    return bool(
        getattr(runtime, "browser_jobs", None)
        and run.get("browser_public_only")
        and run.get("browser_source_ids")
    )


class PublicObserveTool:
    name, effect, schema = "browser_public_observe", False, PublicSourceArguments

    def available(self, runtime, run):
        return _browser_selected(runtime, run)

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump()
        if (
            not self.available(runtime, run)
            or value["source_id"] not in run["browser_source_ids"]
            or value["source_id"] not in SOURCE_CATALOG
        ):
            raise DomainError("RUN_BROWSER_SOURCE_NOT_SELECTED", 403)
        return value

    @staticmethod
    def payload(arguments):
        return PublicObservationInput(source_id=arguments["source_id"], public_only=True)

    def recover(self, runtime, run, arguments, key):
        value = runtime.browser_jobs.lookup_operation(self.payload(arguments), key, kind="observe")
        if value is None:
            return None
        if value["state"] != "observed" or not value["observation"]:
            return {
                "reference_id": value["reference_id"],
                "state": "unknown",
                "result": {"code": value["error"] or "BROWSER_READ_PENDING"},
            }
        observation = value["observation"]
        evidence = {
            "id": "browser:" + observation["source_id"],
            "kind": "browser",
            "record_id": observation["source_id"],
            "observation_id": observation["id"],
            "label": SOURCE_CATALOG[observation["source_id"]]["label"],
            "sha256": observation["sha256"],
            "version": observation["version"],
            "at": observation["observed_at"],
            "excerpt": observation["excerpt"],
            "url": observation["url"],
            "heading": observation["heading"],
            "coverage": {
                "scope": "one_public_excerpt",
                "truncated": True,
                "excerpt_characters": len(observation["excerpt"]),
            },
            "statistics": None,
            "provenance": None,
        }
        return {
            "reference_id": observation["id"],
            "state": "observed",
            "evidence": evidence,
            "result": {
                "source_id": observation["source_id"],
                "sha256": observation["sha256"],
                "url": observation["url"],
                "scope": "one_public_excerpt",
            },
        }

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        # Existing receipts are recovered without another browser read.
        existing = self.recover(runtime, run, arguments, key)
        if existing is not None:
            return existing
        checkpoint()
        runtime.browser_jobs.observe(
            self.payload(arguments),
            key,
            session_hash=run["session_hash"],
            checkpoint=checkpoint,
            publication_checkpoint=lambda conn: runtime.agent_runs.publication_checkpoint(
                run, conn
            ),
        )
        return self.recover(runtime, run, arguments, key)

    def verify(self, runtime, run, receipt):
        return {"state": receipt["state"], **receipt.get("result", {})}

    def cancel(self, runtime, run, receipt):
        # In-progress reads check the parent's generation via the observe hook.
        return None


class PublicBriefTool:
    name, effect, schema = "browser_public_brief", True, PublicBriefArguments

    def available(self, runtime, run):
        return _browser_selected(runtime, run)

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump()
        evidence = next(
            (
                e
                for e in run["evidence"]
                if e["kind"] == "browser"
                and e.get("observation_id") == value["observation_id"]
                and e["record_id"] in run.get("browser_source_ids", [])
            ),
            None,
        )
        if not self.available(runtime, run) or evidence is None:
            raise DomainError("RUN_BROWSER_OBSERVATION_NOT_SELECTED", 403)
        return value

    @staticmethod
    def payload(run, arguments):
        evidence = next(
            (
                e
                for e in run["evidence"]
                if e["kind"] == "browser" and e.get("observation_id") == arguments["observation_id"]
            ),
            None,
        )
        if evidence is None or evidence["record_id"] not in SOURCE_CATALOG:
            raise DomainError("RUN_BROWSER_OBSERVATION_NOT_SELECTED", 403)
        # There is deliberately no model-supplied title/note/body/URL. A run may
        # contain private evidence, goals or answers; none reaches this payload.
        return BrowserJobInput(
            observation_id=arguments["observation_id"],
            title=SOURCE_CATALOG[evidence["record_id"]]["label"],
            note="Public documentation excerpt prepared for exact owner review.",
            public_only=True,
        )

    def recover(self, runtime, run, arguments, key):
        value = runtime.browser_jobs.lookup_operation(
            self.payload(run, arguments), key, kind="prepare"
        )
        if value is None:
            return None
        job = value["job"]
        return {
            "reference_id": job["id"],
            "state": "pending",
            "result": {
                "review_kind": "browser",
                "browser_job_id": job["id"],
                "intent_hash": job["intent_hash"],
                "destination": job["request"]["destination"],
            },
        }

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        existing = self.recover(runtime, run, arguments, key)
        if existing is not None:
            return existing
        checkpoint()
        runtime.browser_jobs.prepare(
            self.payload(run, arguments), key, session_hash=run["session_hash"]
        )
        return self.recover(runtime, run, arguments, key)

    def verify(self, runtime, run, receipt):
        recovered = self.recover(runtime, run, receipt["arguments"], receipt["operation_key"])
        if recovered is None or recovered["reference_id"] != receipt["reference_id"]:
            return {"state": "unknown", "code": "RUN_TOOL_RECEIPT_CONFLICT"}
        job = runtime.browser_jobs.detail(receipt["reference_id"])
        state = job["state"]
        if state == "review" and job["expires_at"] <= iso(runtime.store.clock()):
            return {"state": "rejected", "code": "BROWSER_REVIEW_EXPIRED"}
        if state in {"review", "queued", "running", "verifying", "cancelling"}:
            return {"state": "pending", "child_state": state}
        if state in {"failed", "cancelled", "expired"}:
            return {"state": "rejected", "code": job["error"] or "BROWSER_EFFECT_NOT_COMPLETED"}
        # Reconciliation is read-only with respect to the browser. Always re-open
        # the actual export bytes: an old success flag alone is not current proof.
        job = runtime.browser_jobs.reconcile(job["id"], session_hash=run["session_hash"])["job"]
        result = job.get("result") or {}
        try:
            body, _ = runtime.browser_jobs.export(job["id"], session_hash=run["session_hash"])
        except DomainError as exc:
            return {"state": "unknown", "code": exc.code}
        except (OSError, ValueError, ValidationError):
            return {"state": "unknown", "code": "BROWSER_VERIFICATION_UNAVAILABLE"}
        digest = hashlib.sha256(body).hexdigest()
        verified = (
            job["state"] == "succeeded"
            and job["cleanup_confirmed"]
            and result.get("process_cleanup_confirmed") is True
            and result.get("verified") is True
            and result.get("sha256") == digest
            and result.get("byte_count") == len(body)
        )
        return {
            "state": "verified" if verified else "unknown",
            "code": None if verified else (job["error"] or "BROWSER_RESULT_NOT_VERIFIED"),
            "sha256": digest,
            "byte_count": len(body),
            "artifact_id": result.get("artifact_id"),
            "cleanup_confirmed": job["cleanup_confirmed"],
            "export_url": result.get("export_url"),
            "scope": "public_synthetic_only",
        }

    def cancel(self, runtime, run, receipt):
        recovered = self.recover(runtime, run, receipt["arguments"], receipt["operation_key"])
        if recovered is None or recovered["reference_id"] != receipt["reference_id"]:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        runtime.browser_jobs.cancel(
            receipt["reference_id"], "run-cancel/" + receipt["reference_id"]
        )


def tool_registry(runtime):
    builtins = {a.name: a for a in (PublicObserveTool(), PublicBriefTool())}
    extensions = getattr(runtime, "agent_tool_adapters", {})
    if set(builtins) & set(extensions):
        raise DomainError("RUN_TOOL_REGISTRY_CONFLICT", 409)
    return {**builtins, **extensions}


def tool_catalog(runtime, run):
    return [
        {
            "tool": name,
            "arguments": (
                adapter.argument_schema(runtime)
                if hasattr(adapter, "argument_schema")
                else adapter.schema.model_json_schema()
            ),
            "owner_review_required": adapter.effect,
        }
        for name, adapter in tool_registry(runtime).items()
        if adapter.available(runtime, run)
    ]


def validate_tool_call(runtime, run, call):
    adapter = tool_registry(runtime).get(call.tool)
    if adapter is None or not adapter.available(runtime, run):
        raise DomainError("RUN_TOOL_NOT_ALLOWED", 403)
    try:
        arguments = adapter.validate(runtime, run, call.arguments)
        # Adapters may canonicalize but must not weaken their advertised schema.
        arguments = adapter.schema.model_validate(arguments).model_dump(mode="json")
    except ValidationError:
        raise DomainError("RUN_TOOL_ARGUMENTS_INVALID", 422) from None
    if len(encode(arguments).encode()) > 16000:
        raise DomainError("RUN_TOOL_ARGUMENTS_LIMIT", 422)
    return adapter, arguments
