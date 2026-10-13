"""Owner-selected immutable text snapshots; reads do not grant model transmission."""

import csv
import io
import json
import math
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field, field_validator, model_validator

from .file_store import FORMATS, ImmutableFiles, require_access, session_from_request
from .schemas import StrictModel
from .store import DomainError

from .work_limits import SOURCE_BYTES, SOURCE_COUNT, SOURCE_TOTAL_BYTES

CHUNK_BYTES = 12 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def validate_json(value, depth=0, nodes=None):
    nodes = [0] if nodes is None else nodes
    nodes[0] += 1
    if depth > 12 or nodes[0] > 20000:
        raise DomainError("JSON_STRUCTURE_LIMIT", 422)
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise DomainError("INVALID_JSON", 422)
            validate_json(child, depth + 1, nodes)
    elif isinstance(value, list):
        for child in value:
            validate_json(child, depth + 1, nodes)
    elif isinstance(value, float) and not math.isfinite(value):
        raise DomainError("INVALID_JSON", 422)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise DomainError("INVALID_JSON", 422)


class SourceInput(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    format: Literal["text", "markdown", "csv", "json"]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 or c in "/\\" for c in value):
            raise ValueError("Use a display filename, not a path")
        return value

    @model_validator(mode="after")
    def extension(self):
        allowed = {
            "text": (".txt",),
            "markdown": (".md", ".markdown"),
            "csv": (".csv",),
            "json": (".json",),
        }
        if not self.name.lower().endswith(allowed[self.format]):
            raise ValueError("Filename extension must match the selected text format")
        return self


class ArtifactSourceInput(StrictModel):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class SourceService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.files = ImmutableFiles(self.store)
        with self.store.connection(write=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS source_coverage(
                scope_id TEXT NOT NULL,source_id TEXT NOT NULL,reader TEXT NOT NULL,
                start_line INTEGER NOT NULL,end_line INTEGER NOT NULL,
                UNIQUE(scope_id,source_id,reader,start_line,end_line))""")

    @staticmethod
    def view(row):
        return {
            **row,
            "status": "unknown" if row["status"] == "reserved" else row["status"],
            "name": row["display_name"],
            "media_type": row["mime"],
            "revision": 1,
            "untrusted": True,
            "provider_sharing": "not_granted_by_selection",
        }

    def ingest(self, payload, body, key, *, session_hash, _artifact_id=None,
               _capture_metadata=None, _checkpoint=None):
        if not isinstance(body, bytes) or not body or len(body) > SOURCE_BYTES:
            raise DomainError("SOURCE_SIZE_LIMIT", 413)
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            raise DomainError("SOURCE_UTF8_REQUIRED", 422) from None
        if not text.strip() or "\x00" in text:
            raise DomainError("INVALID_SOURCE_TEXT", 422)
        lines = text.splitlines(keepends=True)
        if any(len(line.encode()) > CHUNK_BYTES for line in lines):
            raise DomainError("SOURCE_LINE_LIMIT", 422)
        if payload.format == "json":
            try:
                parsed = json.loads(text, object_pairs_hook=unique_object)
            except (ValueError, RecursionError):
                raise DomainError("INVALID_JSON", 422) from None
            validate_json(parsed)
        if payload.format == "csv":
            try:
                rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
            except csv.Error:
                raise DomainError("INVALID_CSV", 422) from None
            if (
                not rows
                or len(rows) > 10001
                or not 1 <= len(rows[0]) <= 40
                or any(not c.strip() for c in rows[0])
                or len(set(rows[0])) != len(rows[0])
                or any(len(r) != len(rows[0]) for r in rows)
            ):
                raise DomainError("CSV_STRUCTURE_LIMIT", 422)
        result = self.files.put(
            kind="sources",
            body=body,
            metadata={
                "display_name": payload.name,
                "format": payload.format,
                "mime": FORMATS[payload.format][1],
                "total_lines": len(lines),
                "provenance_kind": "artifact_snapshot" if _artifact_id else "owner_selected_file",
                "parent_artifact_id": _artifact_id,
                **(_capture_metadata or {}),
            },
            key=key,
            session_hash=session_hash,
            max_bytes=SOURCE_BYTES,
            max_count=SOURCE_COUNT,
            max_total=SOURCE_TOTAL_BYTES,
            checkpoint=_checkpoint,
        )
        return {"source": self.view(result), "operation_id": key}

    @staticmethod
    def public_capture_metadata(intent, acquisition):
        """Code-owned metadata only; no HTTP upload payload reaches this adapter."""
        return {
            "display_name": intent["display_name"], "format": "text",
            "mime": FORMATS["text"][1], "total_lines": acquisition["total_lines"],
            "provenance_kind": "public_web_snapshot", "parent_artifact_id": None,
            "capture_id": intent["capture_id"], "url": intent["url"],
            "policy_version": intent["policy_version"], "acquisition": acquisition,
        }

    def public_capture_lookup(self, conn, *, intent, acquisition, key):
        expected = {
            **self.public_capture_metadata(intent, acquisition), "kind": "sources",
            "sha256": acquisition["extracted_sha256"],
            "byte_count": acquisition["extracted_byte_count"],
        }
        return self.files.exact_operation(conn, kind="sources", key=key, expected=expected)

    def ingest_public_capture(self, *, intent, acquisition, body, key, session_hash, checkpoint):
        from .file_store import digest
        from .work_capacity import source_admission
        if (key != "capture:" + intent["capture_id"] + ":source:v1"
                or digest(body) != acquisition["extracted_sha256"]
                or len(body) != acquisition["extracted_byte_count"]
                or len(body.decode("utf-8").splitlines(keepends=True)) != acquisition["total_lines"]):
            raise DomainError("CAPTURE_SOURCE_IDENTITY_INVALID", 409)

        def guarded(conn):
            checkpoint(conn)
            old = self.public_capture_lookup(conn, intent=intent, acquisition=acquisition, key=key)
            if old is None:
                source_admission(conn, len(body))

        return self.ingest(
            SourceInput(name=intent["display_name"], format="text"), body, key,
            session_hash=session_hash,
            _capture_metadata=self.public_capture_metadata(intent, acquisition),
            _checkpoint=guarded,
        )

    def from_artifact(self, artifact_id, key, *, session_hash):
        artifact, body = self.runtime.artifacts.download(artifact_id, session_hash=session_hash)
        extension = FORMATS[artifact["format"]][0]
        payload = SourceInput(
            name=artifact["display_name"][:150] + "." + extension, format=artifact["format"]
        )
        return self.ingest(payload, body, key, session_hash=session_hash, _artifact_id=artifact_id)

    def metadata(self, source_id, *, session_hash):
        return self.view(self.files.reconcile(source_id, "sources", session_hash))

    def listing(self, *, session_hash, limit=50, cursor=None):
        rows, cursor = self.files.listing("sources", session_hash, limit=limit, cursor=cursor)
        return {
            "sources": [self.view(r) for r in rows],
            "next_cursor": cursor,
            "limits": {
                "file_bytes": SOURCE_BYTES,
                "count": SOURCE_COUNT,
                "total_bytes": SOURCE_TOTAL_BYTES,
                "chunk_bytes": CHUNK_BYTES,
            },
        }

    def _selected(self, source_id, selected_ids):
        if source_id not in selected_ids:
            raise DomainError("SOURCE_NOT_SELECTED", 403)

    def _coverage(self, source_id, start, end, coverage_id, reader, session_hash):
        if coverage_id is None:
            return
        if not isinstance(coverage_id, str) or not 1 <= len(coverage_id) <= 100:
            raise DomainError("INVALID_COVERAGE_SCOPE", 422)
        with self.store.connection(write=True) as conn:
            require_access(self.store, conn, session_hash)
            count = conn.execute(
                "SELECT COUNT(*) FROM source_coverage WHERE scope_id=?", (coverage_id,)
            ).fetchone()[0]
            if count >= 1000:
                raise DomainError("SOURCE_COVERAGE_LIMIT", 422)
            conn.execute(
                "INSERT OR IGNORE INTO source_coverage VALUES(?,?,?,?,?)",
                (coverage_id, source_id, reader, start, end),
            )

    def read(
        self,
        source_id,
        *,
        session_hash,
        selected_ids,
        start_line=1,
        max_lines=200,
        max_bytes=CHUNK_BYTES,
        coverage_id=None,
    ):
        self._selected(source_id, selected_ids)
        if not 1 <= max_lines <= 1000 or start_line < 1 or not 1 <= max_bytes <= CHUNK_BYTES:
            raise DomainError("VALIDATION_FAILED", 422)
        row, body = self.files.checked(source_id, "sources", session_hash)
        lines = body.decode("utf-8").splitlines(keepends=True)
        if start_line > len(lines):
            raise DomainError("SOURCE_RANGE_INVALID", 422)
        chosen, size = [], 0
        for line in lines[start_line - 1 : start_line - 1 + max_lines]:
            length = len(line.encode())
            if size + length > max_bytes:
                break
            chosen.append(line)
            size += length
        end = start_line + len(chosen) - 1
        if not chosen:
            raise DomainError("SOURCE_LINE_EXCEEDS_READ_BUDGET", 422)
        self._coverage(source_id, start_line, end, coverage_id, "source_read", session_hash)
        return {
            **self.view(row),
            "content": "".join(chosen),
            "start_line": start_line,
            "end_line": end,
            "truncated": start_line > 1 or end < len(lines),
            "reader": "source_read",
        }

    def read_all(self, source_id, *, session_hash, selected_ids, coverage_id=None):
        self._selected(source_id, selected_ids)
        row, body = self.files.checked(source_id, "sources", session_hash)
        self._coverage(source_id, 1, row["total_lines"], coverage_id, "local_parser", session_hash)
        return {
            **self.view(row),
            "content": body.decode("utf-8"),
            "start_line": 1,
            "end_line": row["total_lines"],
            "truncated": False,
            "reader": "local_parser",
            "provider_ready": False,
        }

    def covered(self, source_id, start, end, coverage_id, authorship, session_hash):
        with self.store.connection() as conn:
            require_access(self.store, conn, session_hash)
            ranges = conn.execute(
                "SELECT start_line,end_line,reader FROM source_coverage WHERE source_id=? AND scope_id=? ORDER BY start_line,end_line",
                (source_id, coverage_id),
            ).fetchall()
            position = start
            for low, high, reader in ranges:
                if authorship == "model" and reader != "source_read":
                    continue
                if low <= position <= high:
                    position = high + 1
                if position > end:
                    return True
            return False


def sources_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/sources", dependencies=[Depends(owner)])

    @router.post("/from-artifact")
    def from_artifact(payload: ArtifactSourceInput, request: Request, key=Depends(operation_id)):
        return runtime.sources.from_artifact(
            payload.artifact_id, key, session_hash=session_from_request(request)
        )

    @router.post("/upload")
    async def upload(
        request: Request,
        name: str = Query(max_length=160),
        format: Literal["text", "markdown", "csv", "json"] = "text",
        key=Depends(operation_id),
    ):
        session = session_from_request(request)
        with runtime.store.connection() as conn:
            require_access(runtime.store, conn, session)
        body = bytearray()
        async for part in request.stream():
            if len(body) + len(part) > SOURCE_BYTES:
                raise DomainError("SOURCE_SIZE_LIMIT", 413)
            body.extend(part)
        try:
            payload = SourceInput(name=name, format=format)
        except ValueError:
            raise DomainError("VALIDATION_FAILED", 422) from None
        return runtime.sources.ingest(payload, bytes(body), key, session_hash=session)

    @router.get("")
    def listing(
        request: Request, limit: int = Query(default=50, ge=1, le=100), cursor: str | None = None
    ):
        return runtime.sources.listing(
            session_hash=session_from_request(request), limit=limit, cursor=cursor
        )

    @router.get("/{source_id}")
    def metadata(source_id: str, request: Request):
        return runtime.sources.metadata(source_id, session_hash=session_from_request(request))

    @router.get("/{source_id}/content")
    def content(
        source_id: str,
        request: Request,
        start_line: int = Query(default=1, ge=1),
        max_lines: int = Query(default=200, ge=1, le=1000),
    ):
        return runtime.sources.read(
            source_id,
            session_hash=session_from_request(request),
            selected_ids=[source_id],
            start_line=start_line,
            max_lines=max_lines,
        )

    return router
