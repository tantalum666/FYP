"""One opt-in, API-controlled application adapter. No arbitrary navigation or shell.

The operator selects an exact IPv4 loopback origin. Every immutable job additionally
pins the application's persisted instance identity. HTTP writes are attempted once;
only a separate GET can establish the result, including after a missing receipt.
"""

import hashlib
import json
import re
import time
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator

from .computer import ExecutionRejected, MAX_BYTES
from .schemas import StrictModel
from .store import encode

APP_ID = "desk_companion_demo_records"
ADAPTER_VERSION = 1
SCHEMA_VERSION = 1
MAX_RESPONSE_BYTES = 64_000


def canonical_origin(value):
    """No DNS, default port, alias, path, userinfo, query or ambiguous spelling."""
    if not isinstance(value, str) or not re.fullmatch(
        r"http://127\.0\.0\.1:[1-9][0-9]{3,4}", value
    ):
        raise ValueError("Use an exact http://127.0.0.1:<1024-65535> origin")
    parts = urlsplit(value)
    if not 1024 <= parts.port <= 65535:
        raise ValueError("Use a non-privileged loopback port")
    return value


class DemoStatus(StrictModel):
    application: str
    instance_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    schema_version: int = Field(strict=True)


class RecordInput(StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    instance_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=8000)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_content(self):
        try:
            body = self.content.encode("utf-8")
            self.title.encode("utf-8")
        except UnicodeError:
            raise ValueError("Use valid Unicode text") from None
        if not self.title.strip() or not self.content.strip() or len(body) > MAX_BYTES:
            raise ValueError("A bounded title and content are required")
        if hashlib.sha256(body).hexdigest() != self.content_sha256:
            raise ValueError("Content hash mismatch")
        return self


class RecordView(RecordInput):
    schema_version: int = Field(strict=True)


class ApplicationReceipt(StrictModel):
    verified: bool = Field(strict=True)
    reason: str
    artifact: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}\.json$")
    bytes: int | None = Field(default=None, ge=0, le=MAX_BYTES, strict=True)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    executor: str | None = None
    scope: str | None = None
    target_origin: str | None = None
    app_instance_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    adapter_version: int | None = Field(default=None, strict=True)
    schema_version: int | None = Field(default=None, strict=True)
    title_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    record_intent_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def complete_evidence(self):
        if self.reason not in {
            "read_back_matches",
            "artifact_missing",
            "target_denied",
            "content_mismatch",
            "verification_unavailable",
        }:
            raise ValueError("Unknown verification reason")
        if self.verified and (
            self.reason != "read_back_matches"
            or any(value is None for key, value in self.model_dump().items() if key != "reason")
        ):
            raise ValueError("Success requires complete independent application evidence")
        return self


class ApplicationRecordsExecutor:
    identity = "demo_records_api_v1"
    scope = "isolated_demo_records_only"

    def __init__(self, origin, *, transport=None):
        self.origin = canonical_origin(origin)
        # Explicit injected transport is only a testing seam; production uses HTTP.
        self.transport = transport

    def _request(self, method, path, payload=None):
        # Callers supply only fixed routes and validated generated record IDs.
        deadline = time.monotonic() + 5.0
        with httpx.Client(
            timeout=httpx.Timeout(2.0),
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        ) as client:
            with client.stream(
                method,
                self.origin + path,
                headers={"X-Desk-Demo": "1", "Accept": "application/json"},
                json=payload,
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if time.monotonic() > deadline:
                        raise TimeoutError("Application response exceeded time budget")
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ValueError("Application response exceeds limit")
                # Never follow or expose Location or exception strings.
                if response.status_code == 404 and method == "GET":
                    return None
                response.raise_for_status()
                return json.loads(body)

    def metadata(self):
        try:
            status = DemoStatus.model_validate(self._request("GET", "/api/status"))
            if status.application != APP_ID or status.schema_version != SCHEMA_VERSION:
                raise ValueError("Wrong application")
        except Exception:
            raise ExecutionRejected("APPLICATION_UNAVAILABLE", 409) from None
        return {
            "target_origin": self.origin,
            "app_instance_id": status.instance_id,
            "adapter_version": ADAPTER_VERSION,
            "schema_version": SCHEMA_VERSION,
        }

    def validate(self, job):
        if (
            job["action"] not in {"create_record", "verify_record"}
            or job.get("target_origin") != self.origin
            or job.get("adapter_version") != ADAPTER_VERSION
            or job.get("schema_version") != SCHEMA_VERSION
            or not re.fullmatch(r"[a-f0-9]{32}", job.get("artifact_id", ""))
            or not re.fullmatch(r"[a-f0-9]{32}", job.get("app_instance_id", ""))
            or job.get("content_sha256") != hashlib.sha256(job["content"].encode()).hexdigest()
        ):
            raise ExecutionRejected("COMPUTER_SCOPE_CHANGED", 409)

    @staticmethod
    def record_intent_hash(job):
        return job.get("record_intent_hash") or hashlib.sha256(encode(job).encode()).hexdigest()

    def execute(self, job, checkpoint):
        self.validate(job)
        if self.metadata()["app_instance_id"] != job["app_instance_id"]:
            raise ExecutionRejected("APPLICATION_INSTANCE_CHANGED", 409)
        if job["action"] == "verify_record":
            checkpoint()
            return
        payload = RecordInput(
            id=job["artifact_id"],
            instance_id=job["app_instance_id"],
            title=job["record_title"],
            content=job["content"],
            content_sha256=job["content_sha256"],
            intent_hash=self.record_intent_hash(job),
        )
        checkpoint()  # Last local cancellation/deadline fence before the HTTP write.
        # Any exception from this point is uncertain, even a non-2xx response.
        # A remote server may have committed before the connection/receipt failed.
        self._request("POST", "/api/records", payload.model_dump())

    def verify(self, job):
        self.validate(job)
        raw = self._request("GET", "/api/records/" + job["artifact_id"])
        if raw is None:
            return {"verified": False, "reason": "artifact_missing"}
        record = RecordView.model_validate(raw)
        body = record.content.encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        matches = (
            record.id == job["artifact_id"]
            and record.instance_id == job["app_instance_id"]
            and record.schema_version == SCHEMA_VERSION
            and record.title == job["record_title"]
            and record.content == job["content"]
            and digest == job["content_sha256"]
            and record.intent_hash == self.record_intent_hash(job)
        )
        return {
            "verified": matches,
            "reason": "read_back_matches" if matches else "content_mismatch",
            "artifact": record.id + ".json",
            "bytes": len(body),
            "sha256": digest,
            "executor": self.identity,
            "scope": self.scope,
            "target_origin": self.origin,
            "app_instance_id": record.instance_id,
            "adapter_version": ADAPTER_VERSION,
            "schema_version": record.schema_version,
            "title_sha256": hashlib.sha256(record.title.encode()).hexdigest(),
            "record_intent_hash": record.intent_hash,
        }
