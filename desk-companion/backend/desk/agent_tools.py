"""Code-owned reads, artifact encoding and independent local-effect verification."""

import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation, localcontext
from datetime import datetime

from pydantic import ValidationError

from .assistant import ChangeProposal
from .calendar import iso
from .schemas import CreateEvents, EventInput
from .store import DomainError, encode
from .tasks import TaskChange, TaskInput


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


def verify_proposal(runtime, proposal_id):
    """Read the durable commit receipt and independently inspect actual current rows."""
    with runtime.store.connection() as conn:
        row = conn.execute(
            "SELECT * FROM assistant_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        if not row:
            return {"state": "unknown", "code": "RUN_PROPOSAL_MISSING"}
        receipt = conn.execute(
            "SELECT response FROM operations WHERE id=?", ("assistant-confirm/" + proposal_id,)
        ).fetchone()
        if not receipt:
            if row["state"] == "cancelled":
                return {"state": "rejected", "code": "RUN_CHANGE_REJECTED"}
            if row["state"] == "pending" and row["expires_at"] > iso(runtime.store.clock()):
                return {"state": "pending", "code": "RUN_REVIEW_REQUIRED"}
            return {"state": "unknown", "code": "RUN_REVIEW_EXPIRED"}
        result, payload = json.loads(receipt[0]), json.loads(row["data"])
        try:
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
