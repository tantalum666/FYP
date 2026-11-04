"""Real application writes on the existing job queue, with staged atomic publishing.

Application helpers edit only owned staging copies. Current permission and input
versions are checked again before publishing. A lost result is reconciled by
reopening the published artifact; an unknown write is never re-executed.
"""

import hashlib
import json
import math
import os
import re
from pathlib import Path

from .application_models import ApplicationJobInput, SavedApplicationIntent, MAX_APP_BYTES
from .application_runtime import ApplicationBridge, ApplicationSources, read_regular, rooted
from .computer import ExecutionRejected, exclusive_write, open_owner_directory
from .store import DomainError, encode


def semantic_cells(snapshot):
    return {(s["sheet"], c["cell"]): c for s in snapshot.get("sheets", []) for c in s["cells"]}


def formula(value):
    parts = re.split(r'("(?:[^"]|"")*")', value)
    normalized = []
    for index, part in enumerate(parts):
        if index % 2:
            normalized.append(part)
            continue
        part = re.sub(r"\s+", "", part).upper().replace(",", ";").replace("!", ".")
        # XLSX reload makes sheet names absolute. Cell anchors still matter.
        part = re.sub(r"\$([A-Z_][A-Z_0-9]*)\.", r"\1.", part)
        normalized.append(part)
    return "".join(normalized)


def content(blocks):
    result = []
    for block in blocks:
        values = (
            [cell for row in block["rows"] for cell in row]
            if block["kind"] == "table"
            else [block.get("text", "")]
        )
        result.extend(" ".join(v.split()) for v in values if v.strip())
    return result


def pdf_matches(readback, expected, operation_id):
    """Compare ordered content, retaining cell boundaries in the PDF stream order."""
    marker = "Desk Companion operation " + operation_id
    subject = re.search(r"^Subject:\s*(.+)$", readback["info"], re.MULTILINE)
    return bool(
        subject
        and subject.group(1).strip() == marker
        and " ".join(readback["text"].split()) == " ".join(expected)
    )


def matches(step, current, previous=None):
    if not current.get("visible"):
        return False
    if step["kind"] == "workbook":
        actual = semantic_cells(current)
        edits = {(s["sheet"], c["cell"]): c for s in step["sheets"] for c in s["cells"]}
        for address, edit in edits.items():
            cell = actual.get(address)
            if edit["kind"] == "text" and edit["value"] == "" and cell is None:
                continue
            if cell is None or cell.get("error"):
                return False
            if edit["kind"] == "text" and (cell["kind"] != "TEXT" or cell["text"] != edit["value"]):
                return False
            if edit["kind"] == "number" and (
                cell["kind"] != "VALUE"
                or not math.isclose(cell["value"], edit["value"], abs_tol=1e-8)
            ):
                return False
            if edit["kind"] == "formula" and (
                cell["kind"] != "FORMULA" or formula(cell["formula"]) != formula(edit["value"])
            ):
                return False
        original = semantic_cells(previous or {})
        for address, old in original.items():
            if address in edits:
                continue
            new = actual.get(address)
            if new is None or new["kind"] != old["kind"] or new.get("error"):
                return False
            if old["kind"] == "FORMULA":
                if formula(new["formula"]) != formula(old["formula"]):
                    return False
            elif new["value"] != old["value"] or new["text"] != old["text"]:
                return False
        return set(actual) <= set(original) | set(edits)
    expected = content(step["blocks"])
    if step.get("mode") == "append":
        expected = (previous or {}).get("content", []) + expected
    return current.get("content") == expected


class ApplicationExecutor:
    identity = "office_applications_v1"

    def __init__(self, runtime_directory):
        self.enabled = os.environ.get("DESK_APPLICATION_ENABLED") == "1"
        self.root = Path(
            os.environ.get("DESK_APPLICATION_WORKSPACE", str(runtime_directory / "applications"))
        ).absolute()
        self.bridge = ApplicationBridge()
        self.sources = ApplicationSources(self.bridge)
        self.scope = (
            "applications:"
            + hashlib.sha256(
                encode(
                    {
                        "root": str(self.root),
                        "inputs": self.sources.fingerprint,
                        "context": self.bridge.context,
                        "container": self.bridge.container,
                    }
                ).encode()
            ).hexdigest()
        )

    def status(self):
        return {
            "enabled": self.enabled,
            "configured": self.bridge.configured,
            "apps": ["LibreOffice Calc", "LibreOffice Writer", "Chromium"],
            "actions": ["workbook", "document", "pdf", "text"] if self.enabled else [],
        }

    def target(self, request):
        return rooted(
            self.root, "artifacts/" + request["task_id"] + "/" + request["step"]["filename"]
        )

    def _write_private(self, path, body):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = open_owner_directory(path.parent)
        try:
            exclusive_write(directory, path.name, body)
        finally:
            os.close(directory)

    def current(self, request):
        self.sources.check(request["sources"])
        for item in request["dependencies"]:
            path = rooted(self.root, "artifacts/" + request["task_id"] + "/" + item["filename"])
            try:
                digest = hashlib.sha256(read_regular(path, MAX_APP_BYTES)).hexdigest()
            except (OSError, ValueError):
                raise ExecutionRejected("APPLICATION_ARTIFACT_CHANGED", 409) from None
            if digest != item["sha256"]:
                raise ExecutionRejected("APPLICATION_ARTIFACT_CHANGED", 409)
        target = self.target(request)
        previous = request.get("previous")
        if previous is None and (target.exists() or target.is_symlink()):
            raise ExecutionRejected("COMPUTER_TARGET_EXISTS", 409)
        if previous is not None:
            try:
                digest = hashlib.sha256(read_regular(target, MAX_APP_BYTES)).hexdigest()
            except (OSError, ValueError):
                raise ExecutionRejected("APPLICATION_ARTIFACT_CHANGED", 409) from None
            if digest != previous["sha256"]:
                raise ExecutionRejected("APPLICATION_ARTIFACT_CHANGED", 409)

    def execute(self, request, checkpoint):
        if not self.enabled:
            raise ExecutionRejected("APPLICATION_UNAVAILABLE", 409)
        self.current(request)
        checkpoint()
        step = request["step"]
        stage = rooted(self.root, "staging/" + request["artifact_id"])
        stage.mkdir(mode=0o700, parents=True, exist_ok=False)
        staged = stage / step["filename"]
        cancel = stage / "cancel"
        source = None
        if request.get("base"):
            base = request["base"]
            source = stage / ("base." + base["filename"].split(".")[-1])
            body = read_regular(
                rooted(self.root, "artifacts/" + request["task_id"] + "/" + base["filename"]),
                MAX_APP_BYTES,
            )
            if hashlib.sha256(body).hexdigest() != base["sha256"]:
                raise ExecutionRejected("APPLICATION_ARTIFACT_CHANGED", 409)
            self._write_private(source, body)
        if step["kind"] == "text":
            self._write_private(staged, step["text"].encode())
        else:
            payload = {
                "mode": "edit",
                "path": str(staged.relative_to(self.root)),
                "source": str(source.relative_to(self.root)) if source else None,
                "step": (
                    {
                        **step,
                        "sheets": [
                            {
                                **sheet,
                                "cells": [
                                    {**cell, "value": formula(cell["value"])}
                                    if cell["kind"] == "formula"
                                    else cell
                                    for cell in sheet["cells"]
                                ],
                            }
                            for sheet in step["sheets"]
                        ],
                    }
                    if step["kind"] == "workbook"
                    else step
                ),
                "operation_id": request["artifact_id"],
                "cancel": str(cancel.relative_to(self.root)),
                "screenshot": str((stage / "edited.png").relative_to(self.root)),
            }
            self.bridge.run(payload, checkpoint, cancel)
        receipt = self._inspect(request, staged)
        if not receipt["verified"]:
            raise ExecutionRejected("APPLICATION_CONTENT_MISMATCH", 409)
        checkpoint()
        self.current(request)
        body = read_regular(staged, MAX_APP_BYTES)
        archive = rooted(self.root, "history/" + request["artifact_id"] + "/" + step["filename"])
        self._write_private(archive, body)
        target = self.target(request)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = target.parent / (".publish-" + request["artifact_id"])
        self._write_private(temporary, body)
        checkpoint()
        self.current(request)
        # From this point a failure may leave a published file: use reconciliation.
        directory = open_owner_directory(target.parent)
        try:
            os.replace(temporary.name, target.name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            os.close(directory)

    def _inspect(self, request, path):
        step = request["step"]
        try:
            body = read_regular(path, MAX_APP_BYTES)
        except FileNotFoundError:
            return {"verified": False, "reason": "artifact_missing"}
        except (OSError, ValueError):
            return {"verified": False, "reason": "target_denied"}
        if step["kind"] == "text":
            readback = {"text": body.decode(), "operation_id": request["artifact_id"]}
            correct, app = body == step["text"].encode(), "local_text"
        elif step["kind"] == "pdf":
            readback = self.bridge.run(
                {"mode": "pdf_inspect", "path": str(path.relative_to(self.root))}
            )
            expected = request["base_snapshot"].get("content", [])
            correct = pdf_matches(readback, expected, request["artifact_id"])
            app = "libreoffice_writer"
        else:
            readback = self.bridge.run(
                {"mode": "inspect", "path": str(path.relative_to(self.root))}
            )
            correct = readback.get("operation_id") == request["artifact_id"] and matches(
                step, readback, request.get("base_snapshot")
            )
            app = "libreoffice_calc" if step["kind"] == "workbook" else "libreoffice_writer"
        if len(encode(readback).encode()) > 256000:
            raise ValueError("APPLICATION_READBACK_LIMIT")
        if read_regular(path, MAX_APP_BYTES) != body:
            correct = False
        return {
            "verified": bool(correct),
            "reason": "read_back_matches" if correct else "content_mismatch",
            "artifact": request["task_id"] + "/" + step["filename"],
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "executor": self.identity,
            "scope": self.scope,
            "operation_id": request["artifact_id"],
            "apps_verified": [app],
            "readback": readback,
        }

    def version_target(self, request):
        return rooted(
            self.root, "history/" + request["artifact_id"] + "/" + request["step"]["filename"]
        )

    def verify(self, request, *, archived=False):
        # Historical versions are independently reopened too; this is never a write.
        return self._inspect(
            request, self.version_target(request) if archived else self.target(request)
        )


def application_request(payload, conn, jobs, artifact_id):
    """Bind dependencies and source versions inside the existing prepare transaction."""
    request = payload.model_dump(mode="json")
    executor = jobs.applications
    if not executor.enabled or not executor.bridge.configured:
        raise DomainError("APPLICATION_UNAVAILABLE", 409)
    request.update(
        artifact_id=artifact_id,
        executor=executor.identity,
        scope=executor.scope,
        content=f"{payload.step.kind}: {payload.step.filename}",
        dependencies=[],
        base=None,
        previous=None,
        base_snapshot=None,
    )
    step = request["step"]
    ids = list(payload.depends_on)
    base_id = step.get("source_job_id")
    previous_id = step.get("replace_job_id") if step["kind"] == "pdf" else base_id
    for key in (base_id, previous_id):
        if key and key not in ids:
            ids.append(key)
    for dependency in ids:
        row = jobs._row(conn, dependency)
        origin = json.loads(row["request"])
        if (
            row["state"] != "succeeded"
            or origin.get("action") != "application"
            or origin["task_id"] != payload.task_id
            or origin["scope"] != executor.scope
        ):
            raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
        result = json.loads(row["result"])
        ref = {
            "job_id": dependency,
            "filename": origin["step"]["filename"],
            "sha256": result["sha256"],
            "kind": origin["step"]["kind"],
        }
        request["dependencies"].append(ref)
        if dependency == base_id:
            if step["kind"] == "pdf":
                if ref["kind"] != "document":
                    raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
            elif ref["kind"] != step["kind"] or ref["filename"] != step["filename"]:
                raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
            request["base"], request["base_snapshot"] = ref, result.get("readback")
        if dependency == previous_id:
            if ref["filename"] != step["filename"]:
                raise DomainError("JOB_SOURCE_UNVERIFIED", 409)
            request["previous"] = ref
    for row in conn.execute(
        "SELECT request,state FROM computer_jobs WHERE state IN ('review','queued','running','verifying','unknown','cancel_requested')"
    ):
        active = json.loads(row["request"])
        if (
            active.get("action") == "application"
            and active["task_id"] == payload.task_id
            and active["step"]["filename"] == step["filename"]
        ):
            if row["state"] != "review" or active["task_version"] == payload.task_version:
                raise DomainError("APPLICATION_ARTIFACT_BUSY", 409)
    executor.current(request)
    return request


def validate_application_request(request):
    allowed = set(ApplicationJobInput.model_fields) | {
        "artifact_id",
        "executor",
        "scope",
        "content",
        "dependencies",
        "base",
        "previous",
        "base_snapshot",
    }
    if not isinstance(request, dict) or set(request) != allowed:
        raise ValueError("Invalid application intent")
    SavedApplicationIntent.model_validate(request)
    if request["executor"] != ApplicationExecutor.identity or not re.fullmatch(
        r"applications:[a-f0-9]{64}", request["scope"]
    ):
        raise ValueError("Invalid application scope")
    if not isinstance(request["dependencies"], list) or len(request["dependencies"]) > 14:
        raise ValueError("Invalid application dependencies")
    for ref in request["dependencies"]:
        if (
            not isinstance(ref, dict)
            or set(ref) != {"job_id", "filename", "sha256", "kind"}
            or not re.fullmatch(r"[a-f0-9]{32}", ref["job_id"])
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(xlsx|odt|pdf|txt|md)", ref["filename"]
            )
            or not re.fullmatch(r"[a-f0-9]{64}", ref["sha256"])
            or ref["kind"] not in {"workbook", "document", "pdf", "text"}
        ):
            raise ValueError("Invalid application dependency")
    if request["base"] not in [None, *request["dependencies"]] or request["previous"] not in [
        None,
        *request["dependencies"],
    ]:
        raise ValueError("Invalid application base")
    step = request["step"]
    base_id = step.get("source_job_id")
    previous_id = step.get("replace_job_id") if step["kind"] == "pdf" else base_id
    expected_ids = set(request["depends_on"]) | {i for i in (base_id, previous_id) if i}
    if {r["job_id"] for r in request["dependencies"]} != expected_ids or len(expected_ids) != len(
        request["dependencies"]
    ):
        raise ValueError("Application dependency identity mismatch")
    for name, expected_id in (("base", base_id), ("previous", previous_id)):
        actual = request[name]
        if (actual or {}).get("job_id") != expected_id:
            raise ValueError("Application base identity mismatch")
    if request["previous"] and request["previous"]["filename"] != step["filename"]:
        raise ValueError("Application target mismatch")
    if base_id:
        base = request["base"]
        if (step["kind"] == "pdf" and base["kind"] != "document") or (
            step["kind"] != "pdf"
            and (base["kind"] != step["kind"] or base["filename"] != step["filename"])
        ):
            raise ValueError("Application source kind mismatch")
        if (
            not isinstance(request["base_snapshot"], dict)
            or len(encode(request["base_snapshot"]).encode()) > 256000
        ):
            raise ValueError("Application base observation missing")
    elif request["base_snapshot"] is not None:
        raise ValueError("Unexpected base observation")
    if request["content"] != f"{step['kind']}: {step['filename']}":
        raise ValueError("Application summary mismatch")
    return request
