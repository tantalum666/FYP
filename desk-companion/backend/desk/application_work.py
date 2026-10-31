"""Durable Work adapters for the existing, independently verified application queue.

No new executor, credentials, task store or model confirmation capability. Scope
is selected at admission; existing software permission is captured then, not on
resume. Receipts are joined to exact public intent before recovery or approval.
"""

import hashlib
import json

from pydantic import Field

from .application_models import ApplicationJobInput, HEX_ID
from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode

JOB_TOOL = "application_job_draft"


def catalog(runtime):
    executor = runtime.jobs.applications
    ready = executor.enabled and executor.bridge.configured
    return {
        **executor.status(),
        "scope": executor.scope,
        "sources": executor.sources.listing()["sources"] if ready else [],
        "permission_mode": runtime.permissions.snapshot()["mode"],
    }


def bind(runtime, payload, available):
    if not payload.allow_application_jobs:
        return None
    if not available["enabled"] or not available["configured"]:
        raise DomainError("APPLICATION_EXECUTOR_UNAVAILABLE", 409)
    items = {s["source_id"]: s for s in available["sources"]}
    if not set(payload.application_source_ids) <= items.keys():
        raise DomainError("RUN_APPLICATION_SOURCE_NOT_SELECTED", 403)
    policy = runtime.permissions.snapshot()
    return {
        "scope": available["scope"],
        "sources": [items[i] for i in payload.application_source_ids],
        "permission_version": policy["version"] if policy["mode"] == "full" else None,
    }


def authorize(runtime, run):
    binding = run.get("application_binding")
    if not run.get("allow_application_jobs"):
        return
    executor = runtime.jobs.applications
    if (
        not binding
        or binding["scope"] != executor.scope
        or not executor.enabled
        or not executor.bridge.configured
    ):
        raise DomainError("RUN_APPLICATION_SCOPE_CHANGED", 409)
    current = {s["source_id"]: s["sha256"] for s in executor.sources.listing()["sources"]}
    if any(current.get(s["source_id"]) != s["sha256"] for s in binding["sources"]):
        raise DomainError("RUN_APPLICATION_SOURCE_CHANGED", 409)


def selected_id(source_id):
    return "application:" + hashlib.sha256(source_id.encode()).hexdigest()[:24]


def _public(request):
    return ApplicationJobInput.model_validate(
        {k: request[k] for k in ApplicationJobInput.model_fields}
    ).model_dump(mode="json")


def lookup(runtime, arguments, key, conn=None):
    """A response or child ID alone is insufficient to adopt an existing job."""
    if conn is None:
        with runtime.store.connection() as owned:
            return lookup(runtime, arguments, key, owned)
    receipt = conn.execute("SELECT request,response FROM operations WHERE id=?", (key,)).fetchone()
    if receipt is None:
        return None
    try:
        if json.loads(receipt["request"]) != {"type": "computer_prepare", **arguments}:
            raise ValueError()
        job_id = json.loads(receipt["response"])["job"]["id"]
        row = runtime.jobs._row(conn, job_id)
        request = json.loads(row["request"])
        if (
            _public(request) != arguments
            or hashlib.sha256(encode(request).encode()).hexdigest() != row["intent_hash"]
        ):
            raise ValueError()
        return runtime.jobs._view(row, review=True)
    except (KeyError, ValueError, TypeError):
        raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409) from None


def guard_job(runtime, conn, job_id):
    """Join only exact reserved Work intents, including the unlinked crash window."""
    intents = conn.execute(
        "SELECT i.* FROM agent_run_tool_intents i JOIN operations o ON o.id=i.operation_key "
        "WHERE i.tool=? AND json_extract(o.response,'$.job.id')=?",
        (JOB_TOOL, job_id),
    ).fetchall()
    for intent in intents:
        arguments = json.loads(intent["arguments"])
        expected = hashlib.sha256(
            encode({"tool": JOB_TOOL, "arguments": arguments}).encode()
        ).hexdigest()
        if expected != intent["intent_hash"]:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        child = lookup(runtime, arguments, intent["operation_key"], conn)
        if not child or child["id"] != job_id:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        run = runtime.agent_runs._get(conn, intent["run_id"])
        runtime.agent_runs.publication_checkpoint(run, conn)


def guard_prepare(runtime, conn, key, request):
    intent = conn.execute(
        "SELECT * FROM agent_run_tool_intents WHERE operation_key=?", (key,)
    ).fetchone()
    if intent is None:
        return
    arguments = json.loads(intent["arguments"])
    expected = hashlib.sha256(
        encode({"tool": JOB_TOOL, "arguments": arguments}).encode()
    ).hexdigest()
    if (
        intent["tool"] != JOB_TOOL
        or expected != intent["intent_hash"]
        or request != {"type": "computer_prepare", **arguments}
    ):
        raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
    run = runtime.agent_runs._get(conn, intent["run_id"])
    runtime.agent_runs.publication_checkpoint(run, conn)


def _available(runtime, run):
    return bool(run.get("allow_application_jobs") and run.get("application_binding"))


def _slice(text, start, count):
    lines = text.splitlines(keepends=True) or [""]
    if start > len(lines):
        raise DomainError("RUN_SOURCE_RANGE_INVALID", 422)
    chosen = []
    for line in lines[start - 1 : start - 1 + count]:
        if len(("".join(chosen) + line).encode()) > 1800:
            break
        chosen.append(line)
    if not chosen:
        raise DomainError("RUN_SOURCE_LINE_TOO_LARGE", 422)
    end = start + len(chosen) - 1
    return "".join(chosen), {
        "start_line": start,
        "end_line": end,
        "total_lines": len(lines),
        "truncated": start != 1 or end < len(lines),
    }


class SourceRead(StrictModel):
    source_id: str = Field(min_length=1, max_length=150)
    start_line: int = Field(default=1, ge=1, le=1000000, strict=True)
    max_lines: int = Field(default=100, ge=1, le=200, strict=True)


class ApplicationSourceTool:
    name, effect, schema = "application_source_read", False, SourceRead
    available = staticmethod(_available)

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump()
        if value["source_id"] not in run.get("application_source_ids", []):
            raise DomainError("RUN_APPLICATION_SOURCE_NOT_SELECTED", 403)
        return value

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        checkpoint()
        source = runtime.jobs.applications.sources.content(arguments["source_id"])
        checkpoint()
        excerpt, coverage = _slice(
            source["observation"]["text"], arguments["start_line"], arguments["max_lines"]
        )
        eid = selected_id(source["source_id"]) + f":L{arguments['start_line']}"
        return {
            "reference_id": hashlib.sha256(key.encode()).hexdigest()[:32],
            "state": "observed",
            "result": {
                "source_id": source["source_id"],
                "sha256": source["sha256"],
                "untrusted_source": True,
            },
            "evidence": {
                "id": eid,
                "kind": "application",
                "record_id": source["source_id"],
                "label": source["source_id"],
                "sha256": source["sha256"],
                "version": 1,
                "at": iso(runtime.store.clock()),
                "excerpt": excerpt,
                "coverage": coverage,
            },
        }

    def recover(self, runtime, run, arguments, key):
        return None  # Safe re-read only; the parent fences late observations.

    def verify(self, runtime, run, receipt):
        return {"state": "observed"}

    def cancel(self, runtime, run, receipt):
        return None


class ApplicationJobTool:
    name, effect, schema = JOB_TOOL, True, ApplicationJobInput
    available = staticmethod(_available)

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump(mode="json")
        if value["task_id"] not in run["task_ids"] or not any(
            e["kind"] == "task"
            and e["record_id"] == value["task_id"]
            and e["version"] == value["task_version"]
            for e in run["evidence"]
        ):
            raise DomainError("RUN_OBSERVED_VERSION_REQUIRED", 409)
        sources = {s["source_id"]: s["sha256"] for s in run["application_binding"]["sources"]}
        if any(sources.get(s["source_id"]) != s["sha256"] for s in value["sources"]):
            raise DomainError("RUN_APPLICATION_SOURCE_NOT_SELECTED", 403)
        # Every selected input remains bound at queue execution/publication even
        # if a planner omitted its reference from a particular proposed step.
        value["sources"] = [
            {"source_id": source_id, "sha256": digest} for source_id, digest in sources.items()
        ]
        refs = [
            *value["depends_on"],
            value["step"].get("source_job_id"),
            value["step"].get("replace_job_id"),
        ]
        if any(i and i not in run.get("application_job_ids", []) for i in refs):
            raise DomainError("RUN_APPLICATION_JOB_NOT_SELECTED", 403)
        for job_id in run.get("application_job_ids", []):
            job = runtime.jobs.detail(job_id, review=True)
            if job["state"] == "unknown" and _public(job["request"]) != value:
                raise DomainError("RUN_APPLICATION_RESULT_UNKNOWN", 409)
        return value

    def recover(self, runtime, run, arguments, key):
        job = lookup(runtime, arguments, key)
        if job is None:
            return None
        return {
            "reference_id": job["id"],
            "state": "pending",
            "result": {
                "application_job_id": job["id"],
                "task_id": arguments["task_id"],
                "filename": arguments["step"]["filename"],
                "review_kind": "application",
                "child_state": job["state"],
            },
        }

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        old = self.recover(runtime, run, arguments, key)
        if old is not None:
            return old  # Recovery never upgrades a previous review into authorization.
        checkpoint()
        job = runtime.jobs.prepare(self.schema.model_validate(arguments), key)["job"]
        checkpoint()
        version = run["application_binding"].get("permission_version")
        if version is not None and runtime.permissions.current(version):
            from .jobs import JobApproval

            review = runtime.jobs.detail(job["id"], review=True)
            runtime.jobs.approve(
                job["id"],
                JobApproval(expected_version=review["version"], intent_hash=review["intent_hash"]),
                "permission/" + job["id"],
                permission_version=version,
            )
        return self.recover(runtime, run, arguments, key)

    def verify(self, runtime, run, receipt):
        job = lookup(runtime, receipt["arguments"], receipt["operation_key"])
        if not job or job["id"] != receipt["reference_id"]:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        state = job["state"]
        if state == "review" and job["expires_at"] <= iso(runtime.store.clock()):
            return {"state": "rejected", "code": "JOB_EXPIRED"}
        if state in {"review", "queued", "running", "verifying", "cancel_requested"}:
            return {"state": "pending", "child_state": state}
        if state in {"failed", "cancelled", "expired"}:
            return {"state": "rejected", "code": job["error"] or "APPLICATION_NOT_COMPLETED"}
        if state == "unknown":
            runtime.jobs.reconcile(job["id"])
        superseded = any(
            other["id"] != job["id"]
            and other["state"] == "succeeded"
            and other["request"]["task_id"] == job["request"]["task_id"]
            and other["request"]["step"]["filename"] == job["request"]["step"]["filename"]
            and (other["request"].get("previous") or {}).get("job_id") == job["id"]
            for other in (
                runtime.jobs.detail(i, review=True) for i in run.get("application_job_ids", [])
            )
        )
        proof = runtime.jobs.application_readback(job["id"], archived=superseded)["result"]
        if proof.get("verified") is not True:
            return {"state": "unknown", "code": "APPLICATION_RESULT_NOT_VERIFIED"}
        filename, body = runtime.jobs.application_download(job["id"])
        if hashlib.sha256(body).hexdigest() != proof["sha256"]:
            return {"state": "unknown", "code": "APPLICATION_ARTIFACT_CHANGED"}
        readback = proof.get("readback")
        if isinstance(readback, dict) and "sheets" in readback:
            # Preserve computed values/errors/formulas without duplicating Calc's
            # formatted numeric strings and application metadata in every turn.
            readback = {
                "sheets": [
                    {
                        "sheet": sheet["sheet"],
                        "cells": [
                            {
                                "cell": cell["cell"],
                                "kind": cell["kind"],
                                "error": cell.get("error", 0),
                                **(
                                    {"text": cell.get("text", "")}
                                    if cell["kind"] == "TEXT"
                                    else {
                                        "value": cell.get("value"),
                                        **(
                                            {"formula": cell["formula"]}
                                            if str(cell.get("formula", "")).startswith("=")
                                            else {}
                                        ),
                                    }
                                ),
                            }
                            for cell in sheet["cells"]
                        ],
                    }
                    for sheet in readback["sheets"]
                ]
            }
        small = len(encode(readback).encode()) <= 8000
        return {
            "state": "verified",
            "sha256": proof["sha256"],
            "bytes": len(body),
            "filename": filename,
            "apps_verified": proof["apps_verified"],
            "readback": readback if small else None,
            "readback_truncated": not small,
            "version_scope": "superseded_history" if superseded else "current",
            "download_url": f"/api/computer/jobs/{job['id']}/artifact",
        }

    def cancel(self, runtime, run, receipt):
        job = lookup(runtime, receipt["arguments"], receipt["operation_key"])
        if not job or job["id"] != receipt["reference_id"]:
            raise DomainError("RUN_TOOL_RECEIPT_CONFLICT", 409)
        current = runtime.jobs.cancel(job["id"], "run-cancel/" + job["id"])["job"]
        # Parent control holds its lock here. Do not reopen an office program or
        # reconcile an uncertain save while the owner is trying to stop work.
        if current["state"] in {"failed", "cancelled", "expired"}:
            return {"state": "rejected", "code": current["error"] or "APPLICATION_NOT_COMPLETED"}
        if current["state"] == "succeeded" and receipt["state"] == "verified":
            return {"state": "verified", "verification": "previously_recorded"}
        return {
            "state": "unknown",
            "code": "RUN_CANCELLED_RESULT_NOT_RECHECKED",
            "child_state": current["state"],
        }


class ArtifactRead(StrictModel):
    job_id: str = Field(pattern=HEX_ID)
    start_line: int = Field(default=1, ge=1, le=1000000, strict=True)
    max_lines: int = Field(default=100, ge=1, le=200, strict=True)


class ApplicationArtifactTool:
    name, effect, schema = "application_artifact_read", False, ArtifactRead
    available = staticmethod(_available)

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump()
        if value["job_id"] not in run.get("application_job_ids", []):
            raise DomainError("RUN_APPLICATION_JOB_NOT_SELECTED", 403)
        return value

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        checkpoint()
        job = runtime.jobs.detail(arguments["job_id"])
        archived = job["state"] == "succeeded"
        result = runtime.jobs.application_readback(arguments["job_id"], archived=archived)["result"]
        result = {
            **result,
            "version_scope": "immutable_history" if archived else "current_unresolved",
        }
        checkpoint()
        text, coverage = _slice(
            json.dumps(result, ensure_ascii=False, indent=2),
            arguments["start_line"],
            arguments["max_lines"],
        )
        return {
            "reference_id": arguments["job_id"],
            "state": "observed",
            "result": {"content": text, "coverage": coverage, "untrusted_source": True},
        }

    def recover(self, runtime, run, arguments, key):
        return None

    def verify(self, runtime, run, receipt):
        return {"state": "observed"}

    def cancel(self, runtime, run, receipt):
        return None


def adapters():
    return {
        tool.name: tool
        for tool in (ApplicationSourceTool(), ApplicationJobTool(), ApplicationArtifactTool())
    }
