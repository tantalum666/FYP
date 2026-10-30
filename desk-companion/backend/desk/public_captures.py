"""One explicitly reviewed GET, durable once-only barriers and local-only recovery.

No constructor starts a thread or network request. Retained metadata and sources
have no deletion control. A dispatch marker is possibility, never delivery proof.
"""

from datetime import datetime, timedelta
import json
import re
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request

from .calendar import iso
from .file_store import digest, session_from_request
from .public_capture_policy import (
    CapturePrepare,
    CaptureApprove,
    CaptureVersionInput,
    CaptureIntent,
    CaptureAcquisition,
    extract_static_text,
    validate_url,
)
from .store import DomainError, encode
from .work_capacity import HIDDEN_PROJECTION, source_admission

HISTORY_LIMIT = 200
MAX_INTEGER = 2**53 - 1
_WORKER_SLOT = threading.Lock()
ACTIVE = {"queued", "fetching", "publishing"}
STATES = ACTIVE | {"review", "verified", "expired", "failed", "cancelled", "unknown"}
SCALAR_NAMES = "id,state,version,generation,created_at,updated_at,expires_at,dispatch_possible,cancel_requested,error_code".split(
    ","
)
_TEXT_LIMITS = {
    "id": 32,
    "state": 16,
    "intent_json": 8192,
    "intent_hash": 64,
    "session_hash": 64,
    "privacy_revision": 128,
    "claim": 128,
    "created_at": 64,
    "updated_at": 64,
    "expires_at": 64,
    "approved_at": 64,
    "deadline_at": 64,
    "dispatch_at": 64,
    "source_operation_key": 100,
    "source_id": 32,
    "stage": 64,
    "error_code": 96,
    "acquisition_json": 4096,
}
_INTEGER_NAMES = (
    "version",
    "policy_version",
    "generation",
    "dispatch_possible",
    "cancel_requested",
)
_NULLABLE = {
    "claim",
    "approved_at",
    "deadline_at",
    "dispatch_at",
    "source_id",
    "error_code",
    "acquisition_json",
}


def _bounded_column(name):
    if name in _INTEGER_NAMES:
        return f"CASE WHEN typeof({name})='integer' AND {name} BETWEEN 0 AND {MAX_INTEGER} THEN {name} END AS {name}"
    limit = _TEXT_LIMITS[name]
    null = f"WHEN {name} IS NULL THEN NULL " if name in _NULLABLE else ""
    return (
        f"CASE {null}WHEN typeof({name})='text' AND length(CAST({name} AS BLOB))<={limit} "
        f"AND instr({name},char(0))=0 THEN {name} ELSE x'00' END AS {name}"
    )


SCALAR = ",".join(_bounded_column(name) for name in SCALAR_NAMES)
PRIVATE = ",".join(_bounded_column(name) for name in (*_TEXT_LIMITS, *_INTEGER_NAMES))
BOUNDED_ID = _bounded_column("id")
HEX_ID = re.compile(r"[a-f0-9]{32}")
SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")


def _utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if iso(parsed) != value:
        raise ValueError()
    return parsed


def _json(raw, limit):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result

    if not isinstance(raw, str) or len(raw.encode()) > limit or "\x00" in raw:
        raise ValueError()
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError()
    return value


class PublicCaptureService:
    def __init__(self, runtime, *, enabled=False, client=None, monotonic=time.monotonic):
        if type(enabled) is not bool:
            raise ValueError("Explicit boolean capability required")
        self.runtime, self.store = runtime, runtime.store
        self.enabled, self.client, self.monotonic = enabled, client, monotonic
        self._lock = threading.Lock()
        self._slot = _WORKER_SLOT
        self._wake = threading.Event()
        self._thread = None
        self._stopping = False
        self._worker_error = None
        self._reviews = {}
        self._executions = {}
        # Recovery revokes authority even while disabled, never resumes a GET.
        # Schema creation/upgrade belongs exclusively to Store's offline policy.
        with self.store.connection(write=True) as conn:
            rows = conn.execute(f"SELECT {BOUNDED_ID} FROM public_captures LIMIT 201").fetchall()
            if len(rows) > HISTORY_LIMIT:
                raise DomainError("CAPTURE_RECORD_INVALID", 409)
            for row in rows:
                self._row(conn, row[0])
            conn.execute(
                "UPDATE public_captures SET state=CASE WHEN state='review' THEN 'expired' "
                "WHEN dispatch_possible=1 OR state='publishing' THEN 'unknown' ELSE 'failed' END,"
                "claim=NULL,generation=generation+1,version=version+1,error_code='CAPTURE_RESTARTED',"
                "updated_at=? WHERE state IN ('review','queued','fetching','publishing')",
                (iso(self.store.clock()),),
            )

    def start(self):
        with self._lock:
            if not self.enabled or self._stopping or self._thread is not None:
                return
            self._thread = threading.Thread(target=self._loop, daemon=True, name="public-capture")
            self._thread.start()

    def _loop(self):
        while not self._stopping:
            self._wake.wait(0.5)
            self._wake.clear()
            if not self._stopping:
                try:
                    self.run_one()
                except Exception:
                    # Lost durable control is a blocker, never a replay trigger.
                    self._worker_error = "CAPTURE_WORKER_UNAVAILABLE"
                    return

    def stop(self, timeout=1):
        self._stopping = True
        try:
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "UPDATE public_captures SET state=CASE WHEN dispatch_possible=1 OR state='publishing' "
                    "THEN 'unknown' ELSE 'failed' END,claim=NULL,generation=generation+1,"
                    "version=version+1,error_code='CAPTURE_STOPPED',updated_at=? "
                    "WHERE state IN ('queued','fetching','publishing')",
                    (iso(self.store.clock()),),
                )
        finally:
            self._wake.set()
            if self._thread is not None:
                self._thread.join(timeout=max(0, min(timeout, 3)))

    def _authority(self, conn, session_hash, *, hidden=False):
        if not isinstance(session_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", session_hash):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (session_hash, iso(self.store.clock())),
        ).fetchone():
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        row = conn.execute(
            f"SELECT CASE WHEN typeof(version)='integer' AND version BETWEEN 1 AND {MAX_INTEGER} THEN version END AS version,{HIDDEN_PROJECTION} AS hidden FROM settings WHERE id=1"
        ).fetchone()
        epoch = conn.execute(
            f"SELECT CASE WHEN typeof(epoch)='integer' AND epoch BETWEEN 0 AND {MAX_INTEGER} THEN epoch END FROM personal_settings WHERE id=1"
        ).fetchone()
        if (
            row is None
            or epoch is None
            or type(row["version"]) is not int
            or not 1 <= row["version"] < MAX_INTEGER
            or type(epoch[0]) is not int
            or epoch[0] < 0
            or row["hidden"] not in (0, 1)
        ):
            raise DomainError("CAPTURE_AUTHORITY_UNAVAILABLE", 409)
        if row["hidden"] and not hidden:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        return f"{row['version']}:{epoch[0]}"

    def _fresh(self, session_hash, authority, *, hidden=False, conn=None):
        if conn is not None:
            if self._authority(conn, session_hash, hidden=hidden) != authority:
                raise DomainError("CAPTURE_PRIVACY_CHANGED", 403)
            return
        with self.store.connection() as conn:
            if self._authority(conn, session_hash, hidden=hidden) != authority:
                raise DomainError("CAPTURE_PRIVACY_CHANGED", 403)

    @staticmethod
    def _identity(capture_id):
        if not isinstance(capture_id, str) or not HEX_ID.fullmatch(capture_id):
            raise DomainError("CAPTURE_NOT_FOUND", 404)

    def _row(self, conn, capture_id, *, private=False):
        self._identity(capture_id)
        row = conn.execute(
            f"SELECT {PRIVATE if private else SCALAR} FROM public_captures WHERE id=?",
            (capture_id,),
        ).fetchone()
        if row is None:
            raise DomainError("CAPTURE_NOT_FOUND", 404)
        row = dict(row)
        if (
            row["id"] != capture_id
            or row["state"] not in STATES
            or type(row["version"]) is not int
            or not 1 <= row["version"] < MAX_INTEGER
            or type(row["generation"]) is not int
            or not 0 <= row["generation"] < MAX_INTEGER
            or row["dispatch_possible"] not in (0, 1)
            or row["cancel_requested"] not in (0, 1)
        ):
            raise DomainError("CAPTURE_RECORD_INVALID", 409)
        for name in ("created_at", "updated_at", "expires_at"):
            try:
                _utc(row[name])
            except ValueError:
                raise DomainError("CAPTURE_RECORD_INVALID", 409) from None
        if private:
            try:
                for name in ("approved_at", "deadline_at", "dispatch_at"):
                    if row[name] is not None:
                        _utc(row[name])
            except ValueError:
                raise DomainError("CAPTURE_RECORD_INVALID", 409) from None
        return row

    def _intent(self, row):
        try:
            intent = CaptureIntent.model_validate(_json(row["intent_json"], 8192))
            if (
                intent.digest() != row["intent_hash"]
                or intent.capture_id != row["id"]
                or intent.session_hash != row["session_hash"]
                or intent.privacy_revision != row["privacy_revision"]
                or row["policy_version"] != 1
                or row["source_operation_key"] != f"capture:{row['id']}:source:v1"
            ):
                raise ValueError()
            return intent.model_dump()
        except (ValueError, TypeError, KeyError, RecursionError):
            raise DomainError("CAPTURE_RECORD_INVALID", 409) from None

    def _acquisition(self, row, intent):
        if row["acquisition_json"] is None:
            return None
        try:
            acquisition = _json(row["acquisition_json"], 4096)
            service_fields = {
                name: acquisition.pop(name)
                for name in ("capture_id", "url", "received_at", "http_status", "total_lines")
            }
            core = CaptureAcquisition.model_validate(acquisition).model_dump()
            if (
                service_fields["capture_id"] != row["id"]
                or service_fields["url"] != intent["url"]
                or type(service_fields["http_status"]) is not int
                or service_fields["http_status"] != 200
                or type(service_fields["total_lines"]) is not int
                or not 1 <= service_fields["total_lines"] <= 24576
            ):
                raise ValueError()
            stamp = service_fields["received_at"]
            if not isinstance(stamp, str) or len(stamp) > 40 or not stamp.endswith("Z"):
                raise ValueError()
            _utc(stamp)
            return {**core, **service_fields}
        except (ValueError, TypeError, KeyError, RecursionError):
            raise DomainError("CAPTURE_RECORD_INVALID", 409) from None

    def _receipts(self, conn, row, intent=None):
        columns = ",".join(
            f"CASE WHEN typeof({name})='text' AND length(CAST({name} AS BLOB))<={limit} "
            f"AND instr({name},char(0))=0 THEN {name} END AS {name}"
            for name, limit in (
                ("operation_key", 100),
                ("kind", 7),
                ("request_hash", 64),
                ("capture_id", 32),
            )
        )
        rows = conn.execute(
            f"SELECT {columns} FROM public_capture_operations WHERE capture_id=? LIMIT 4",
            (row["id"],),
        ).fetchall()
        kinds = set()
        for receipt in rows:
            if (
                not isinstance(receipt["operation_key"], str)
                or not receipt["operation_key"]
                or receipt["kind"] not in {"prepare", "approve", "cancel"}
                or receipt["kind"] in kinds
                or receipt["capture_id"] != row["id"]
                or not isinstance(receipt["request_hash"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", receipt["request_hash"])
            ):
                raise DomainError("CAPTURE_RECEIPT_INVALID", 409)
            kinds.add(receipt["kind"])
            if intent is not None and receipt["kind"] == "prepare":
                expected = {k: intent[k] for k in ("url", "label", "retain_capture_record")}
                if receipt["request_hash"] != digest(encode(expected).encode()):
                    raise DomainError("CAPTURE_RECEIPT_INVALID", 409)
            if intent is not None and receipt["kind"] == "approve":
                expected = dict(
                    capture_id=row["id"],
                    expected_version=1,
                    intent_hash=row["intent_hash"],
                    public_only=True,
                    retain_snapshot=True,
                )
                if receipt["request_hash"] != digest(encode(expected).encode()):
                    raise DomainError("CAPTURE_RECEIPT_INVALID", 409)
        if (
            "prepare" not in kinds
            or row["state"] in ACTIVE | {"verified"}
            and "approve" not in kinds
            or row["cancel_requested"]
            and "cancel" not in kinds
            or "approved_at" in row
            and row["approved_at"] is not None
            and "approve" not in kinds
        ):
            raise DomainError("CAPTURE_RECEIPT_INVALID", 409)

    def _projection(self, conn, row, metadata_only):
        value = {
            k: row[k] for k in ("id", "state", "version", "created_at", "updated_at", "expires_at")
        }
        value.update(
            dispatch_possible=bool(row["dispatch_possible"]),
            error_code=row["error_code"]
            if isinstance(row["error_code"], str) and SAFE_CODE.fullmatch(row["error_code"])
            else None,
            cancel_available=row["state"] in ACTIVE | {"review"},
        )
        self._receipts(conn, row)
        if metadata_only:
            return value
        intent = self._intent(row)
        self._receipts(conn, row, intent)
        acquisition = self._acquisition(row, intent)
        source = self._source(conn, row, intent, acquisition)
        value.update({k: intent[k] for k in ("url", "label", "display_name")})
        value.update(
            intent_hash=row["intent_hash"],
            source_id=source["id"] if source else None,
            source_status="verified"
            if source and source["status"] == "verified"
            else "unknown"
            if source
            else "not_reserved",
            acquisition=acquisition,
        )
        return value

    def _source(self, conn, row, intent, acquisition):
        if acquisition is None:
            if (
                row["state"] == "verified"
                or row["source_id"] is not None
                or conn.execute(
                    "SELECT 1 FROM private_files WHERE kind='sources' AND operation_key=?",
                    (row["source_operation_key"],),
                ).fetchone()
            ):
                raise DomainError("CAPTURE_SOURCE_IDENTITY_INVALID", 409)
            return None
        source = self.runtime.sources.public_capture_lookup(
            conn, intent=intent, acquisition=acquisition, key=row["source_operation_key"]
        )
        if (
            row["state"] == "verified"
            and source is None
            or row["source_id"] is not None
            and (source is None or row["source_id"] != source["id"])
        ):
            raise DomainError("CAPTURE_SOURCE_IDENTITY_INVALID", 409)
        return source

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not re.fullmatch(r"[\x21-\x7e]{1,100}", key):
            raise DomainError("OPERATION_ID_REQUIRED", 422)

    def _receipt(self, conn, key, kind, request_hash, capture_id=None):
        self._key(key)
        columns = ",".join(
            f"CASE WHEN typeof({name})='text' AND length(CAST({name} AS BLOB))<={limit} "
            f"AND instr({name},char(0))=0 THEN {name} ELSE x'00' END AS {name}"
            for name, limit in (("kind", 7), ("request_hash", 64), ("capture_id", 32))
        )
        receipt = conn.execute(
            f"SELECT {columns} FROM public_capture_operations WHERE operation_key=?", (key,)
        ).fetchone()
        if receipt is not None:
            if (
                receipt["kind"] != kind
                or receipt["request_hash"] != request_hash
                or capture_id is not None
                and receipt["capture_id"] != capture_id
            ):
                raise DomainError("OPERATION_ID_CONFLICT", 409)
            self._identity(receipt["capture_id"])
            return receipt["capture_id"]
        return None

    @staticmethod
    def _save_receipt(conn, key, kind, request_hash, capture_id):
        conn.execute(
            "INSERT INTO public_capture_operations(operation_key,kind,request_hash,capture_id) VALUES(?,?,?,?)",
            (key, kind, request_hash, capture_id),
        )

    def _capability(self):
        if self._worker_error:
            raise DomainError(self._worker_error, 409)
        if not self.enabled or self._stopping:
            raise DomainError("CAPTURE_DISABLED", 409)

    def capabilities(self, *, session_hash):
        with self.store.connection() as conn:
            authority = self._authority(conn, session_hash, hidden=True)
        result = {
            "enabled": self.enabled and not self._stopping and self._worker_error is None,
            "history_limit": HISTORY_LIMIT,
            "source_cleanup": False,
        }
        self._fresh(session_hash, authority, hidden=True)
        return result

    def prepare(self, payload, key, *, session_hash):
        payload = CapturePrepare.model_validate(payload)
        request_hash = digest(encode(payload.model_dump()).encode())
        with self.store.connection(write=True) as conn:
            initial_authority = self._authority(conn, session_hash)
            existing = self._receipt(conn, key, "prepare", request_hash)
            if existing is None:
                self._capability()
                source_admission(conn)
                count = conn.execute("SELECT 1 FROM public_captures LIMIT 201").fetchall()
                if len(count) >= HISTORY_LIMIT:
                    raise DomainError("CAPTURE_HISTORY_LIMIT", 422)
                capture_id = uuid4().hex
                revision = self._authority(conn, session_hash)
                intent = CaptureIntent(
                    **payload.model_dump(),
                    capture_id=capture_id,
                    session_hash=session_hash,
                    privacy_revision=revision,
                    display_name=f"capture-{capture_id}.txt",
                )
                now = self.store.clock()
                conn.execute(
                    "INSERT INTO public_captures(id,state,version,intent_json,intent_hash,policy_version,session_hash,privacy_revision,claim,generation,created_at,updated_at,expires_at,approved_at,deadline_at,dispatch_possible,dispatch_at,cancel_requested,source_operation_key,source_id,stage,error_code,acquisition_json) "
                    "VALUES(?,'review',1,?,?,1,?,?,NULL,0,?,?,?,NULL,NULL,0,NULL,0,?,NULL,'review',NULL,NULL)",
                    (
                        capture_id,
                        encode(intent.model_dump()),
                        intent.digest(),
                        session_hash,
                        revision,
                        iso(now),
                        iso(now),
                        iso(now + timedelta(minutes=5)),
                        f"capture:{capture_id}:source:v1",
                    ),
                )
                self._save_receipt(conn, key, "prepare", request_hash, capture_id)
                self._reviews[capture_id] = self.monotonic() + 300
                self.store.bump(conn)
            else:
                capture_id = existing
        result = self.detail(capture_id, session_hash=session_hash)
        # The current record remains recoverable when admission is now full/corrupt.
        result["operation_id"] = key
        with self.store.connection() as conn:
            authority = self._authority(conn, session_hash)
            row = self._row(conn, capture_id, private=True)
            intent = self._intent(row)
            review = self._review(conn, row, intent)
        self._fresh(session_hash, authority)
        result["review"] = review
        self._fresh(session_hash, initial_authority)
        return result

    def _review(self, conn, row, intent):
        from .work_capacity import WorkCapacityService, FileCapacity
        from .work_limits import SOURCE_COUNT, SOURCE_TOTAL_BYTES, SOURCE_BYTES

        capacity = FileCapacity(
            **WorkCapacityService._files(
                conn, "sources", SOURCE_COUNT, SOURCE_TOTAL_BYTES, SOURCE_BYTES
            )
        ).model_dump()
        review = {k: v for k, v in intent.items() if k not in {"session_hash", "privacy_revision"}}
        review.update(
            id=row["id"],
            version=row["version"],
            state=row["state"],
            intent_hash=row["intent_hash"],
            expires_at=row["expires_at"],
            host=validate_url(intent["url"]).host,
            destination=intent["url"],
            source_capacity=capacity,
            history_used=len(conn.execute("SELECT 1 FROM public_captures LIMIT 201").fetchall()),
            history_limit=HISTORY_LIMIT,
            observed_at=iso(self.store.clock()),
            advisory=True,
            untrusted=True,
            starts_work=False,
            grants_model_sharing=False,
            disclosure="host/path and connection metadata to website and DNS infrastructure",
            static_text_limitation="Static text may differ from rendered text; sources cannot be deleted in this version",
        )
        return review

    def detail(self, capture_id, *, session_hash, metadata_only=False):
        if type(metadata_only) is not bool:
            raise DomainError("VALIDATION_FAILED", 422)
        with self.store.connection() as conn:
            authority = self._authority(conn, session_hash, hidden=metadata_only)
            row = self._row(conn, capture_id, private=not metadata_only)
            result = {"capture": self._projection(conn, row, metadata_only)}
            if not metadata_only and row["state"] == "review":
                result["review"] = self._review(conn, row, self._intent(row))
        self._fresh(session_hash, authority, hidden=metadata_only)
        return result

    def listing(self, *, session_hash, limit=20, cursor=None, metadata_only=False):
        if type(limit) is not int or not 1 <= limit <= 50 or type(metadata_only) is not bool:
            raise DomainError("VALIDATION_FAILED", 422)
        if cursor is not None:
            self._identity(cursor)
        with self.store.connection() as conn:
            authority = self._authority(conn, session_hash, hidden=metadata_only)
            ids = conn.execute(
                f"SELECT {BOUNDED_ID} FROM public_captures WHERE id>? ORDER BY id LIMIT ?",
                (cursor or "", limit + 1),
            ).fetchall()
            captures = [
                self._projection(
                    conn, self._row(conn, r[0], private=not metadata_only), metadata_only
                )
                for r in ids[:limit]
            ]
        self._fresh(session_hash, authority, hidden=metadata_only)
        return {
            "captures": captures,
            "next_cursor": captures[-1]["id"] if len(ids) > limit else None,
        }

    def approve(self, capture_id, payload, key, *, session_hash):
        payload = CaptureApprove.model_validate(payload)
        request_hash = digest(encode({"capture_id": capture_id, **payload.model_dump()}).encode())
        with self.store.connection(write=True) as conn:
            authority = self._authority(conn, session_hash)
            existing = self._receipt(conn, key, "approve", request_hash, capture_id)
            row = self._row(conn, capture_id, private=True)
            intent = self._intent(row)
            self._receipts(conn, row, intent)
            if existing is None and row["state"] == "review":
                self._capability()
                if (
                    row["version"] != payload.expected_version
                    or row["intent_hash"] != payload.intent_hash
                ):
                    raise DomainError("CAPTURE_VERSION_CONFLICT", 409)
                if (
                    intent["session_hash"] != session_hash
                    or intent["privacy_revision"] != authority
                ):
                    raise DomainError("CAPTURE_APPROVAL_EXPIRED", 409)
                if (
                    capture_id not in self._reviews
                    or self.monotonic() >= self._reviews[capture_id]
                    or self.store.clock() >= _utc(row["expires_at"])
                    or self.store.clock() < _utc(row["created_at"])
                ):
                    raise DomainError("CAPTURE_APPROVAL_EXPIRED", 409)
                if (
                    self._slot.locked()
                    or conn.execute(
                        "SELECT 1 FROM public_captures WHERE state IN ('queued','fetching','publishing') LIMIT 1"
                    ).fetchone()
                ):
                    raise DomainError("CAPTURE_BUSY", 409)
                source_admission(conn)
                now, claim = self.store.clock(), uuid4().hex
                conn.execute(
                    "UPDATE public_captures SET state='queued',version=version+1,generation=generation+1,claim=?,approved_at=?,deadline_at=?,updated_at=?,stage='queued' WHERE id=?",
                    (claim, iso(now), iso(now + timedelta(seconds=60)), iso(now), capture_id),
                )
                self._executions[capture_id] = (claim, self.monotonic() + 60)
                self._save_receipt(conn, key, "approve", request_hash, capture_id)
                self.store.bump(conn)
            elif existing is None:
                # Different-key repetition is a read-only no-op only for the same intent.
                if row["intent_hash"] != payload.intent_hash:
                    raise DomainError("CAPTURE_VERSION_CONFLICT", 409)
        self._wake.set()
        result = {**self.detail(capture_id, session_hash=session_hash), "operation_id": key}
        self._fresh(session_hash, authority)
        return result

    def cancel(self, capture_id, payload, key, *, session_hash):
        payload = CaptureVersionInput.model_validate(payload)
        request_hash = digest(encode({"capture_id": capture_id, **payload.model_dump()}).encode())
        with self.store.connection(write=True) as conn:
            self._authority(conn, session_hash, hidden=True)
            existing = self._receipt(conn, key, "cancel", request_hash, capture_id)
            row = self._row(conn, capture_id)
            self._receipts(conn, row)
            if existing is None and row["state"] in ACTIVE | {"review"}:
                if row["version"] != payload.expected_version:
                    raise DomainError("CAPTURE_VERSION_CONFLICT", 409)
                conn.execute(
                    "UPDATE public_captures SET state='cancelled',cancel_requested=1,claim=NULL,generation=generation+1,version=version+1,updated_at=?,error_code='CAPTURE_CANCELLED' WHERE id=?",
                    (iso(self.store.clock()), capture_id),
                )
                self._save_receipt(conn, key, "cancel", request_hash, capture_id)
                self.store.bump(conn)
        # Always safe scalar response: hidden stop never parses private JSON.
        return {
            **self.detail(capture_id, session_hash=session_hash, metadata_only=True),
            "operation_id": key,
        }

    def _checkpoint(self, capture_id, claim, generation, session_hash, deadline, conn=None):
        if self._stopping or not self.enabled or self.monotonic() >= deadline:
            raise DomainError("CAPTURE_DEADLINE_OR_STOP", 409)
        if conn is None:
            with self.store.connection() as current:
                return self._checkpoint(
                    capture_id, claim, generation, session_hash, deadline, current
                )
        authority = self._authority(conn, session_hash)
        row = self._row(conn, capture_id, private=True)
        intent = self._intent(row)
        self._receipts(conn, row, intent)
        if (
            row["claim"] != claim
            or row["generation"] != generation
            or row["cancel_requested"]
            or row["state"] not in ACTIVE
            or row["session_hash"] != session_hash
            or row["privacy_revision"] != authority
            or row["deadline_at"] is None
            or self.store.clock() >= _utc(row["deadline_at"])
            or row["approved_at"] is None
            or self.store.clock() < _utc(row["approved_at"])
        ):
            raise DomainError("CAPTURE_AUTHORITY_CHANGED", 409)
        return row

    def run_one(self):
        if (
            not self.enabled
            or self._stopping
            or self._worker_error
            or not self._slot.acquire(blocking=False)
        ):
            return False
        capture_id = claim = None
        try:
            with self.store.connection(write=True) as conn:
                queued = conn.execute(
                    f"SELECT {BOUNDED_ID} FROM public_captures WHERE state='queued' ORDER BY created_at,id LIMIT 1"
                ).fetchone()
                if queued is None:
                    return False
                capture_id = queued[0]
                row = self._row(conn, capture_id, private=True)
                claim, deadline = self._executions.get(capture_id, (None, 0))
                generation, session = row["generation"], row["session_hash"]
                self._checkpoint(capture_id, claim, generation, session, deadline, conn)
                source_admission(conn)
                intent = self._intent(row)
                conn.execute(
                    "UPDATE public_captures SET state='fetching',version=version+1,stage='network',updated_at=? WHERE id=?",
                    (iso(self.store.clock()), capture_id),
                )
            acquisition = None

            def checkpoint(conn=None):
                current = self._checkpoint(capture_id, claim, generation, session, deadline, conn)
                if (
                    acquisition is not None
                    and current["state"] == "publishing"
                    and self._acquisition(current, intent) != acquisition
                ):
                    raise DomainError("CAPTURE_SOURCE_IDENTITY_INVALID", 409)
                return current

            def dispatched():
                with self.store.connection(write=True) as conn:
                    current = checkpoint(conn)
                    if current["dispatch_possible"]:
                        raise DomainError("CAPTURE_ALREADY_DISPATCHED", 409)
                    conn.execute(
                        "UPDATE public_captures SET dispatch_possible=1,dispatch_at=?,updated_at=?,version=version+1,stage='dispatched' WHERE id=?",
                        (iso(self.store.clock()), iso(self.store.clock()), capture_id),
                    )

            if self.client is None:
                from .connectors.public_capture_transport import PublicCaptureClient

                self.client = PublicCaptureClient()
            response = self.client.fetch(
                intent["url"],
                checkpoint,
                on_dispatch=dispatched,
                deadline=min(deadline, self.monotonic() + 20),
            )
            if not checkpoint()["dispatch_possible"]:
                raise DomainError("CAPTURE_DISPATCH_RECEIPT_REQUIRED", 409)
            extracted = extract_static_text(response.raw, response.mime_type, checkpoint=checkpoint)
            acquisition = {
                **extracted.acquisition.model_dump(),
                "capture_id": capture_id,
                "url": intent["url"],
                "received_at": iso(self.store.clock()),
                "http_status": 200,
                "total_lines": len(extracted.body.decode().splitlines(keepends=True)),
            }
            with self.store.connection(write=True) as conn:
                checkpoint(conn)
                conn.execute(
                    "UPDATE public_captures SET state='publishing',stage='source_reservation',acquisition_json=?,version=version+1,updated_at=? WHERE id=?",
                    (encode(acquisition), iso(self.store.clock()), capture_id),
                )
            published = self.runtime.sources.ingest_public_capture(
                intent=intent,
                acquisition=acquisition,
                body=extracted.body,
                key=f"capture:{capture_id}:source:v1",
                session_hash=session,
                checkpoint=checkpoint,
            )["source"]
            with self.store.connection(write=True) as conn:
                checkpoint(conn)
                state = "verified" if published["status"] == "verified" else "unknown"
                conn.execute(
                    "UPDATE public_captures SET state=?,source_id=?,claim=NULL,version=version+1,stage='source_readback',error_code=?,updated_at=? WHERE id=?",
                    (
                        state,
                        published["id"],
                        published["error_code"],
                        iso(self.store.clock()),
                        capture_id,
                    ),
                )
        except Exception as failure:
            if capture_id is not None:
                code = (
                    failure.code
                    if isinstance(failure, DomainError) and SAFE_CODE.fullmatch(failure.code)
                    else "CAPTURE_FAILED"
                )
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE public_captures SET state=CASE WHEN dispatch_possible=1 OR state='publishing' THEN 'unknown' ELSE 'failed' END,claim=NULL,version=version+1,error_code=?,updated_at=? WHERE id=? AND state IN ('queued','fetching','publishing')",
                        (code, iso(self.store.clock()), capture_id),
                    )
        finally:
            self._slot.release()
        return capture_id is not None

    def reconcile(self, capture_id, payload, key, *, session_hash):
        payload = CaptureVersionInput.model_validate(payload)
        self._key(key)
        with self.store.connection() as conn:
            authority = self._authority(conn, session_hash)
            # Reconcile has no receipt, but must not reuse a retained mutation key.
            if conn.execute(
                "SELECT 1 FROM public_capture_operations WHERE operation_key=?", (key,)
            ).fetchone():
                raise DomainError("OPERATION_ID_CONFLICT", 409)
            row = self._row(conn, capture_id, private=True)
            if row["version"] != payload.expected_version:
                raise DomainError("CAPTURE_VERSION_CONFLICT", 409)
            if row["state"] in ACTIVE:
                raise DomainError("CAPTURE_BUSY", 409)
            intent = self._intent(row)
            acquisition = self._acquisition(row, intent)
            source = self._source(conn, row, intent, acquisition)

        def fresh(conn=None):
            self._fresh(session_hash, authority, conn=conn)

        if source is not None:
            source = self.runtime.sources.files.reconcile_exact(source, session_hash, fresh)
            with self.store.connection(write=True) as conn:
                if self._authority(conn, session_hash) != authority:
                    raise DomainError("CAPTURE_PRIVACY_CHANGED", 403)
                current = self._row(conn, capture_id, private=True)
                if current["version"] != payload.expected_version:
                    raise DomainError("CAPTURE_VERSION_CONFLICT", 409)
                checked = self._source(
                    conn, current, self._intent(current), self._acquisition(current, intent)
                )
                if checked is None or checked["id"] != source["id"]:
                    raise DomainError("CAPTURE_SOURCE_IDENTITY_INVALID", 409)
                conn.execute(
                    "UPDATE public_captures SET source_id=?,version=version+1,updated_at=? WHERE id=?",
                    (source["id"], iso(self.store.clock()), capture_id),
                )
        fresh()
        verification = (
            "source_verified"
            if source and source["status"] == "verified"
            else "source_unknown"
            if source
            else "no_final_source"
        )
        result = self.detail(capture_id, session_hash=session_hash)
        fresh()
        return {**result, "operation_id": key, "verification": verification}


def public_capture_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/public-research", dependencies=[Depends(owner)])

    @router.get("/capabilities")
    def capabilities(request: Request):
        return runtime.public_captures.capabilities(session_hash=session_from_request(request))

    @router.post("/captures")
    def prepare(payload: CapturePrepare, request: Request, key=Depends(operation_id)):
        return runtime.public_captures.prepare(
            payload, key, session_hash=session_from_request(request)
        )

    @router.get("/captures")
    def listing(
        request: Request,
        limit: int = Query(default=20, ge=1, le=50),
        cursor: str | None = None,
        metadata_only: bool = False,
    ):
        return runtime.public_captures.listing(
            session_hash=session_from_request(request),
            limit=limit,
            cursor=cursor,
            metadata_only=metadata_only,
        )

    @router.get("/captures/{capture_id}")
    def detail(capture_id: str, request: Request, metadata_only: bool = False):
        return runtime.public_captures.detail(
            capture_id, session_hash=session_from_request(request), metadata_only=metadata_only
        )

    @router.post("/captures/{capture_id}/approve", status_code=202)
    def approve(
        capture_id: str, payload: CaptureApprove, request: Request, key=Depends(operation_id)
    ):
        return runtime.public_captures.approve(
            capture_id, payload, key, session_hash=session_from_request(request)
        )

    @router.post("/captures/{capture_id}/cancel")
    def cancel(
        capture_id: str, payload: CaptureVersionInput, request: Request, key=Depends(operation_id)
    ):
        return runtime.public_captures.cancel(
            capture_id, payload, key, session_hash=session_from_request(request)
        )

    @router.post("/captures/{capture_id}/reconcile")
    def reconcile(
        capture_id: str, payload: CaptureVersionInput, request: Request, key=Depends(operation_id)
    ):
        return runtime.public_captures.reconcile(
            capture_id, payload, key, session_hash=session_from_request(request)
        )

    return router
