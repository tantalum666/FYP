"""Immutable real report files. Byte verification never claims semantic accuracy."""

import csv
import io
import json
import math
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import Field, field_validator, model_validator

from .file_store import FORMATS, ImmutableFiles, digest, session_from_request
from .schemas import StrictModel
from .sources import SourceInput, validate_json
from .store import DomainError

from .work_limits import (
    ARTIFACT_BYTES, ARTIFACT_COUNT, ARTIFACT_TOTAL_BYTES,
    ARTIFACT_RUN_COUNT, ARTIFACT_RUN_BYTES,
)


class SourceReference(StrictModel):
    source_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    source_revision: int = Field(default=1, ge=1, le=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_line < self.start_line:
            raise ValueError("Invalid source range")
        return self


class ArtifactInput(StrictModel):
    format: Literal["text", "markdown", "csv", "json"]
    display_name: str = Field(min_length=1, max_length=160)
    content: Any
    provenance: list[SourceReference] = Field(default_factory=list, max_length=100)
    authorship: Literal["model", "deterministic", "owner"] = "deterministic"
    supersedes_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @field_validator("display_name")
    @classmethod
    def label(cls, value):
        return SourceInput.clean_name(value)


def csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise DomainError("INVALID_CSV", 422)
        return value
    if not isinstance(value, str) or "\x00" in value:
        raise DomainError("INVALID_CSV", 422)
    # Quoting alone does not prevent spreadsheet formula execution. Preserve
    # actual numeric cells, but prefix dangerous string cells with apostrophe.
    if value.startswith(("\t", "\r", "\n", "\ufeff")) or value.lstrip(
        " \t\r\n\ufeff\u200b"
    ).startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def artifact_bytes(payload):
    if payload.format in {"text", "markdown"}:
        if (
            not isinstance(payload.content, str)
            or not payload.content.strip()
            or "\x00" in payload.content
        ):
            raise DomainError("INVALID_ARTIFACT_TEXT", 422)
        text = payload.content
    elif payload.format == "json":
        validate_json(payload.content)
        try:
            text = json.dumps(payload.content, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        except (ValueError, TypeError, RecursionError):
            raise DomainError("INVALID_JSON", 422) from None
    else:
        content = payload.content
        if not isinstance(content, dict) or set(content) != {"columns", "rows"}:
            raise DomainError("INVALID_CSV", 422)
        columns, rows = content["columns"], content["rows"]
        if (
            not isinstance(columns, list)
            or not 1 <= len(columns) <= 40
            or any(not isinstance(c, str) or not c.strip() for c in columns)
            or len(set(columns)) != len(columns)
            or not isinstance(rows, list)
            or len(rows) > 1000
            or any(not isinstance(r, list) or len(r) != len(columns) for r in rows)
        ):
            raise DomainError("CSV_STRUCTURE_LIMIT", 422)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\r\n")
        writer.writerow([csv_cell(c) for c in columns])
        writer.writerows([csv_cell(v) for v in row] for row in rows)
        text = output.getvalue()
    try:
        body = text.encode("utf-8")
    except UnicodeEncodeError:
        raise DomainError("ARTIFACT_UTF8_REQUIRED", 422) from None
    if not body or len(body) > ARTIFACT_BYTES:
        raise DomainError("ARTIFACT_SIZE_LIMIT", 413)
    return body


class ArtifactService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.files = ImmutableFiles(self.store)

    @staticmethod
    def view(row):
        return {
            **row,
            "status": "unknown" if row["status"] == "reserved" else row["status"],
            "verification": "byte_readback" if row["status"] == "verified" else "unverified",
            "quality": "not_semantically_checked",
        }

    def _provenance(self, payload, selected_source_ids, run_id, session_hash):
        refs = []
        if len(selected_source_ids) > 12:
            raise DomainError("SOURCE_SELECTION_LIMIT", 422)
        for ref in payload.provenance:
            if ref.source_id not in selected_source_ids:
                raise DomainError("SOURCE_NOT_SELECTED", 403)
            source = self.runtime.sources.metadata(ref.source_id, session_hash=session_hash)
            if source["status"] != "verified":
                raise DomainError("SOURCE_UNVERIFIED", 409)
            if ref.end_line > source["total_lines"]:
                raise DomainError("SOURCE_RANGE_INVALID", 422)
            if run_id and not self.runtime.sources.covered(
                ref.source_id,
                ref.start_line,
                ref.end_line,
                run_id,
                payload.authorship,
                session_hash,
            ):
                raise DomainError("SOURCE_RANGE_NOT_OBSERVED", 422)
            refs.append(
                {
                    **ref.model_dump(),
                    "sha256": source["sha256"],
                    "acquired_at": source["created_at"],
                }
            )
        return refs

    def publish(
        self,
        payload,
        key,
        *,
        session_hash,
        selected_source_ids,
        run_id=None,
        step_id=None,
        _origin="generated",
        checkpoint=None,
    ):
        if any(
            value is not None and (not isinstance(value, str) or not 1 <= len(value) <= 100)
            for value in (run_id, step_id)
        ):
            raise DomainError("INVALID_ARTIFACT_SCOPE", 422)
        body = artifact_bytes(payload)
        provenance = self._provenance(payload, selected_source_ids, run_id, session_hash)
        if payload.supersedes_id:
            self.detail(payload.supersedes_id, session_hash=session_hash)
        result = self.files.put(
            kind="artifacts",
            body=body,
            metadata={
                "run_id": run_id,
                "step_id": step_id,
                "format": payload.format,
                "display_name": payload.display_name,
                "mime": FORMATS[payload.format][1],
                "provenance": provenance,
                "authorship": payload.authorship,
                "supersedes_id": payload.supersedes_id,
                "origin": _origin,
                "csv_string_escaping": "apostrophe_prefix" if payload.format == "csv" else None,
            },
            key=key,
            session_hash=session_hash,
            max_bytes=ARTIFACT_BYTES,
            max_count=ARTIFACT_COUNT,
            max_total=ARTIFACT_TOTAL_BYTES,
            checkpoint=checkpoint,
        )
        return {"artifact": self.view(result), "operation_id": key}

    def import_download(
        self,
        payload,
        key,
        *,
        body,
        expected_sha256,
        session_hash,
        selected_source_ids,
        run_id,
        step_id,
    ):
        if payload.format not in {"text", "markdown"} or not isinstance(body, bytes):
            raise DomainError("DOWNLOAD_FORMAT_DENIED", 422)
        if digest(body) != expected_sha256 or artifact_bytes(payload) != body:
            raise DomainError("DOWNLOAD_BYTES_MISMATCH", 409)
        return self.publish(
            payload,
            key,
            session_hash=session_hash,
            selected_source_ids=selected_source_ids,
            run_id=run_id,
            step_id=step_id,
            _origin="browser_download",
        )

    def detail(self, artifact_id, *, session_hash):
        return self.view(self.files.reconcile(artifact_id, "artifacts", session_hash))

    def reconcile(self, artifact_id, *, session_hash):
        return self.detail(artifact_id, session_hash=session_hash)

    def listing(self, *, session_hash, run_id=None, limit=50, cursor=None):
        rows, cursor = self.files.listing(
            "artifacts", session_hash, limit=limit, cursor=cursor, run_id=run_id
        )
        return {
            "artifacts": [self.view(r) for r in rows],
            "next_cursor": cursor,
            "limits": {
                "file_bytes": ARTIFACT_BYTES,
                "per_run_count": ARTIFACT_RUN_COUNT,
                "per_run_bytes": ARTIFACT_RUN_BYTES,
                "count": ARTIFACT_COUNT,
                "total_bytes": ARTIFACT_TOTAL_BYTES,
            },
        }

    def read(self, artifact_id, *, session_hash):
        row, body = self.files.checked(artifact_id, "artifacts", session_hash)
        preview = body[: 32 * 1024].decode("utf-8", errors="ignore")
        return {
            "artifact": self.view(row),
            "content": preview,
            "truncated": len(body) > 32 * 1024,
            "preview_kind": "plain_text",
        }

    def download(self, artifact_id, *, session_hash):
        row, body = self.files.checked(artifact_id, "artifacts", session_hash)
        return self.view(row), body


def artifact_routes(runtime, owner, operation_id=None):
    router = APIRouter(prefix="/api/artifacts", dependencies=[Depends(owner)])

    @router.get("")
    def listing(
        request: Request,
        run_id: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = None,
    ):
        return runtime.artifacts.listing(
            session_hash=session_from_request(request), run_id=run_id, limit=limit, cursor=cursor
        )

    @router.get("/{artifact_id}")
    def detail(artifact_id: str, request: Request):
        return runtime.artifacts.detail(artifact_id, session_hash=session_from_request(request))

    @router.get("/{artifact_id}/content")
    def content(artifact_id: str, request: Request):
        return runtime.artifacts.read(artifact_id, session_hash=session_from_request(request))

    @router.get("/{artifact_id}/download")
    def download(artifact_id: str, request: Request):
        row, body = runtime.artifacts.download(
            artifact_id, session_hash=session_from_request(request)
        )
        return Response(
            body,
            media_type=row["mime"],
            headers={
                "Content-Disposition": 'attachment; filename="'
                + runtime.artifacts.files.filename(row)
                + '"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; sandbox",
            },
        )

    return router
