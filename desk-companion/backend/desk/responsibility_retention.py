"""Watch-only schema, bounded accounting and volatile exact-action previews.

No filesystem cleanup, model entry point, scheduler or global operation ledger.
"""

import hashlib
import json
import secrets
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Literal

from pydantic import Field, model_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode
from .work_limits import WATCH_COUNT

SCHEMA_VERSION = 2
LIFETIME_IDENTITIES = 256
MAX_RECEIPTS = 259
TERMINAL_STATUSES = frozenset({"cancelled", "expired", "budget_exhausted"})
RETENTION_STATES = frozenset({"retained", "trashed", "purged"})
CHARGED_WATCH_PREDICATE = "retention_state IS NOT 'purged'"
TOMBSTONE = '{"kind":"purged_watch_v1"}'
WATCH_TABLES = {
    "responsibilities": (
        "id",
        "data",
        "version",
        "generation",
        "status",
        "created_at",
        "updated_at",
        "baseline_at",
        "expires_at",
        "review_budget",
        "reviews_used",
        "daily_review_budget",
        "budget_day",
        "daily_used",
        "blocked_code",
        "eval_order",
    ),
    "responsibility_sources": (
        "responsibility_id",
        "source_id",
        "dirty_generation",
        "consumed_generation",
        "observed_source_token",
        "field_hashes",
    ),
    "responsibility_reviews": (
        "id",
        "responsibility_id",
        "sequence",
        "version",
        "delivery_state",
        "data",
        "first_observed_at",
        "last_observed_at",
    ),
    "responsibility_operations": ("id", "request_hash", "responsibility_id", "review_id", "kind"),
}
RETENTION_COLUMNS = {
    "retention_state": "TEXT NOT NULL DEFAULT 'retained'",
    "retention_version": "INTEGER NOT NULL DEFAULT 1",
    "trashed_at": "TEXT",
    "restored_at": "TEXT",
    "purged_at": "TEXT",
}

CORE_DDL = (
    """CREATE TABLE responsibilities(
        id TEXT PRIMARY KEY,data TEXT NOT NULL,version INTEGER NOT NULL,
        generation INTEGER NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,baseline_at TEXT NOT NULL,expires_at TEXT NOT NULL,
        review_budget INTEGER NOT NULL,reviews_used INTEGER NOT NULL,
        daily_review_budget INTEGER NOT NULL,budget_day TEXT NOT NULL,
        daily_used INTEGER NOT NULL,blocked_code TEXT,eval_order INTEGER NOT NULL,
        retention_state TEXT NOT NULL DEFAULT 'retained',
        retention_version INTEGER NOT NULL DEFAULT 1,
        trashed_at TEXT,restored_at TEXT,purged_at TEXT)""",
    """CREATE TABLE responsibility_sources(
        responsibility_id TEXT NOT NULL,source_id TEXT NOT NULL,
        dirty_generation INTEGER NOT NULL,consumed_generation INTEGER NOT NULL,
        observed_source_token TEXT NOT NULL,field_hashes TEXT NOT NULL,
        PRIMARY KEY(responsibility_id,source_id),
        FOREIGN KEY(responsibility_id) REFERENCES responsibilities(id))""",
    """CREATE TABLE responsibility_reviews(
        id TEXT PRIMARY KEY,responsibility_id TEXT NOT NULL,sequence INTEGER NOT NULL,
        version INTEGER NOT NULL,delivery_state TEXT NOT NULL,data TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,last_observed_at TEXT NOT NULL,
        FOREIGN KEY(responsibility_id) REFERENCES responsibilities(id),
        UNIQUE(responsibility_id,sequence))""",
    """CREATE TABLE responsibility_operations(
        id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,responsibility_id TEXT NOT NULL,
        review_id TEXT,kind TEXT NOT NULL,
        FOREIGN KEY(responsibility_id) REFERENCES responsibilities(id))""",
)
INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS responsibilities_status ON responsibilities(status,expires_at)",
    "CREATE INDEX IF NOT EXISTS responsibilities_retained ON responsibilities(retention_state,created_at,id)",
    f"CREATE INDEX IF NOT EXISTS responsibilities_charged ON responsibilities(id) WHERE {CHARGED_WATCH_PREDICATE}",
    "CREATE INDEX IF NOT EXISTS responsibility_sources_id ON responsibility_sources(source_id)",
    "CREATE INDEX IF NOT EXISTS responsibility_sources_dirty ON responsibility_sources(responsibility_id) WHERE dirty_generation != consumed_generation",
    "CREATE UNIQUE INDEX IF NOT EXISTS responsibility_one_pending ON responsibility_reviews(responsibility_id) WHERE delivery_state='pending'",
    "CREATE INDEX IF NOT EXISTS responsibility_operations_owner ON responsibility_operations(responsibility_id)",
)


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def validate_store_base(conn):
    """Recognize existing supported Store structures without reading private values."""
    required = {
        "settings": {"id", "data", "version"},
        "owner": {"id", "password_hash"},
        "sessions": {"token_hash", "expires"},
        "events": {"id", "data", "version", "deleted"},
        "exceptions": {"event_id", "occurrence_key", "data"},
        "operations": {"id", "request", "response"},
        "records": {"sequence", "at", "action", "event_id", "details"},
        "reminders": {
            "id",
            "event_id",
            "occurrence_key",
            "early_minutes",
            "due_at",
            "status",
            "snooze_until",
            "version",
        },
        "state": {"id", "revision"},
    }
    present = tables(conn)
    for name, columns in required.items():
        if name not in present or not columns <= {
            r[1] for r in conn.execute(f"PRAGMA table_info({name})")
        }:
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")

    if (
        conn.execute(
            "SELECT COUNT(*) FROM owner WHERE id=1 AND typeof(password_hash)='text' AND length(password_hash)>0"
        ).fetchone()[0]
        != 1
        or conn.execute(
            "SELECT COUNT(*) FROM settings WHERE id=1 AND typeof(version)='integer' AND version>=1 AND typeof(data)='text'"
        ).fetchone()[0]
        != 1
        or conn.execute(
            "SELECT COUNT(*) FROM state WHERE id=1 AND typeof(revision)='integer' AND revision>=1"
        ).fetchone()[0]
        != 1
    ):
        raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")


def validate_watch_schema(conn, *, legacy=False, allow_absent=False):
    present = tables(conn) & WATCH_TABLES.keys()
    if not present and allow_absent:
        return False
    if present != WATCH_TABLES.keys():
        raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    for name, columns in WATCH_TABLES.items():
        expected = set(columns)
        if name == "responsibilities" and not legacy:
            expected |= RETENTION_COLUMNS.keys()
        info = list(conn.execute(f"PRAGMA table_info({name})"))
        if {r[1] for r in info} != expected:
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        integers = {
            "version",
            "generation",
            "review_budget",
            "reviews_used",
            "daily_review_budget",
            "daily_used",
            "eval_order",
            "retention_version",
            "dirty_generation",
            "consumed_generation",
            "sequence",
        }
        for column in info:
            if column[2].upper() != ("INTEGER" if column[1] in integers else "TEXT"):
                raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        primary = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
        if primary != (
            ["responsibility_id", "source_id"] if name == "responsibility_sources" else ["id"]
        ):
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        if name != "responsibilities":
            foreign = list(conn.execute(f"PRAGMA foreign_key_list({name})"))
            if len(foreign) != 1 or foreign[0][2:5] != (
                "responsibilities",
                "responsibility_id",
                "id",
            ):
                raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    if not legacy:
        required_indexes = {statement.split(" ON ")[0].split()[-1] for statement in INDEX_DDL}
        actual_indexes = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        if not required_indexes <= actual_indexes:
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        for trigger in conn.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND (name LIKE 'responsibility_task_%' OR name LIKE 'responsibility_note_%')"
        ):
            if "retention_state='retained'" not in trigger[1]:
                raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    return True


def install_watch_triggers(conn, *, replace=False):
    present = tables(conn)
    if "tasks" in present:
        for operation, source in (("INSERT", "NEW"), ("UPDATE", "NEW"), ("DELETE", "OLD")):
            name = f"responsibility_task_{operation.lower()}"
            if replace:
                conn.execute(f"DROP TRIGGER IF EXISTS {name}")
            conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
                AFTER {operation} ON tasks BEGIN
                UPDATE responsibility_sources SET dirty_generation=dirty_generation+1
                WHERE source_id={source}.id AND responsibility_id IN
                    (SELECT id FROM responsibilities WHERE retention_state='retained'
                     AND status IN ('active','paused','blocked'));
                END""")
    if "task_evidence" in present:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS responsibility_latest_note ON task_evidence(task_id,kind,id)"
        )
        for operation, source in (("INSERT", "NEW"), ("DELETE", "OLD")):
            name = f"responsibility_note_{operation.lower()}"
            if replace:
                conn.execute(f"DROP TRIGGER IF EXISTS {name}")
            conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
                AFTER {operation} ON task_evidence WHEN {source}.kind='note' BEGIN
                UPDATE responsibility_sources SET dirty_generation=dirty_generation+1
                WHERE source_id={source}.task_id AND responsibility_id IN
                    (SELECT id FROM responsibilities WHERE retention_state='retained'
                     AND status IN ('active','paused','blocked'));
                END""")


def initialize_watch_schema(conn, *, legacy=False):
    """Caller owns BEGIN IMMEDIATE; never use executescript inside that transaction."""
    existing = validate_watch_schema(conn, legacy=legacy, allow_absent=True)
    if existing and legacy:
        for name, definition in RETENTION_COLUMNS.items():
            conn.execute(f"ALTER TABLE responsibilities ADD COLUMN {name} {definition}")
        # All old rows stay charged. No body, status, history or receipt is rewritten.
        if conn.execute(
            "SELECT 1 FROM responsibilities WHERE retention_state!='retained' OR retention_version!=1 OR trashed_at IS NOT NULL OR restored_at IS NOT NULL OR purged_at IS NOT NULL LIMIT 1"
        ).fetchone():
            raise DomainError("SCHEMA_MIGRATION_INVALID")
    elif not existing:
        for statement in CORE_DDL:
            conn.execute(statement)
    for statement in INDEX_DDL:
        conn.execute(statement)
    install_watch_triggers(conn, replace=legacy)
    validate_watch_schema(conn)


class RetentionPreviewRequest(StrictModel):
    action: Literal["trash", "restore", "purge"]
    expected_version: int = Field(ge=1, strict=True)
    expected_retention_version: int = Field(ge=1, strict=True)


class RetentionAction(RetentionPreviewRequest):
    preview_id: str = Field(min_length=20, max_length=100, strict=True)
    confirm_permanent_removal: Literal[True] | None = None

    @model_validator(mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if isinstance(value, dict):
            if value.get("action") == "purge":
                if value.get("confirm_permanent_removal") is not True:
                    raise ValueError("Explicit final permanent-removal confirmation is required")
            elif "confirm_permanent_removal" in value:
                raise ValueError("Confirmation is only valid for permanent removal")
        return value


class MaintenanceUsage(StrictModel):
    version: Literal[1] = 1
    retained_count: int | None = Field(default=None, ge=0, le=WATCH_COUNT, strict=True)
    trashed_count: int | None = Field(default=None, ge=0, le=WATCH_COUNT, strict=True)
    lifetime_count: int | None = Field(default=None, ge=0, le=LIFETIME_IDENTITIES, strict=True)
    lifetime_limit: Literal[256] = LIFETIME_IDENTITIES
    lifetime_remaining: int | None = Field(default=None, ge=0, le=LIFETIME_IDENTITIES, strict=True)
    state: Literal["known", "over_limit", "unavailable"]

    @model_validator(mode="after")
    def consistent(self):
        values = (
            self.retained_count,
            self.trashed_count,
            self.lifetime_count,
            self.lifetime_remaining,
        )
        if self.state != "known":
            if any(value is not None for value in values):
                raise ValueError("Unknown maintenance usage cannot advertise partial headroom")
        elif (
            any(value is None for value in values)
            or not self.trashed_count <= self.retained_count <= self.lifetime_count
            or self.lifetime_remaining != self.lifetime_limit - self.lifetime_count
        ):
            raise ValueError("Inconsistent maintenance usage")
        return self


def receipt_count(conn, identity):
    return conn.execute(
        "SELECT COUNT(*) FROM responsibility_operations WHERE responsibility_id=?", (identity,)
    ).fetchone()[0]


def _timestamp(value):
    if value is None:
        return True
    try:
        parsed = datetime.fromisoformat(value)
        return isinstance(value, str) and parsed.tzinfo is not None
    except (ValueError, TypeError):
        return False


def validate_retention_row(row):
    if (
        row["retention_state"] not in RETENTION_STATES
        or type(row["retention_version"]) is not int
        or row["retention_version"] < 1
        or any(not _timestamp(row[k]) for k in ("trashed_at", "restored_at", "purged_at"))
        or row["retention_state"] == "trashed"
        and row["trashed_at"] is None
        or row["retention_state"] != "purged"
        and row["purged_at"] is not None
        or row["retention_state"] in {"trashed", "purged"}
        and row["status"] not in TERMINAL_STATUSES
    ):
        raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE")
    if row["retention_state"] == "purged" and (
        row["data"] != TOMBSTONE or row["purged_at"] is None
    ):
        raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE")


def decode_body(row):
    validate_retention_row(row)
    if row["retention_state"] == "purged":
        raise DomainError("RESPONSIBILITY_REMOVED", 410)
    try:
        raw = row["data"]
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 8192:
            raise ValueError()
        pairs = json.loads(raw, object_pairs_hook=lambda pairs: pairs)
        if not isinstance(pairs, list) or any(
            not isinstance(p, tuple) or len(p) != 2 for p in pairs
        ):
            raise ValueError()
        body = dict(pairs)
        if len(body) != len(pairs) or set(body) != {
            "title",
            "kind",
            "task_ids",
            "fields",
            "retain_change_history",
        }:
            raise ValueError()
        if (
            not isinstance(body["title"], str)
            or not body["title"].strip()
            or len(body["title"]) > 160
        ):
            raise ValueError()
        body["title"].encode("utf-8")
        if body["kind"] != "selected_task_changes" or body["retain_change_history"] is not True:
            raise ValueError()
        ids, fields = body["task_ids"], body["fields"]
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 10
            or any(not isinstance(i, str) or not 1 <= len(i) <= 64 for i in ids)
            or len(set(ids)) != len(ids)
        ):
            raise ValueError()
        if (
            not isinstance(fields, list)
            or not 1 <= len(fields) <= 6
            or any(
                f not in ("status", "due", "next_step", "waiting_for", "steps", "progress")
                for f in fields
            )
            or len(set(fields)) != len(fields)
        ):
            raise ValueError()
        return body
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE") from None


def watch_accounting(conn, cap=WATCH_COUNT, *, capacity=False):
    """Bounded scalar checks; never materialize private watch bodies or receipt hashes.

    Corrupt bodies on charged rows remain charged; admission separately validates
    those bodies. A purported purge must positively prove its shell and no bodies.
    """
    rows = conn.execute(
        """SELECT CASE WHEN typeof(retention_state)='text' AND retention_state IN ('retained','trashed','purged') THEN retention_state ELSE '__invalid__' END retention_state,
        CASE WHEN typeof(retention_version)='integer' AND retention_version BETWEEN 1 AND 9007199254740991 THEN retention_version END retention_version,
        CASE WHEN trashed_at IS NULL THEN NULL WHEN typeof(trashed_at)='text' AND length(CAST(trashed_at AS BLOB))<=64 AND instr(trashed_at,char(0))=0 THEN trashed_at ELSE '' END trashed_at,
        CASE WHEN restored_at IS NULL THEN NULL WHEN typeof(restored_at)='text' AND length(CAST(restored_at AS BLOB))<=64 AND instr(restored_at,char(0))=0 THEN restored_at ELSE '' END restored_at,
        CASE WHEN purged_at IS NULL THEN NULL WHEN typeof(purged_at)='text' AND length(CAST(purged_at AS BLOB))<=64 AND instr(purged_at,char(0))=0 THEN purged_at ELSE '' END purged_at,
        CASE WHEN typeof(version)='integer' AND version>=1 AND typeof(generation)='integer' AND generation>=1 THEN 1 ELSE 0 END valid_versions,
        CASE WHEN status IN ('cancelled','expired','budget_exhausted') THEN 1 ELSE 0 END terminal,
        CASE WHEN typeof(data)='text' AND data=? THEN 1 ELSE 0 END shell,
        EXISTS(SELECT 1 FROM responsibility_sources s WHERE s.responsibility_id=r.id) sources,
        EXISTS(SELECT 1 FROM responsibility_reviews v WHERE v.responsibility_id=r.id) reviews,
        EXISTS(SELECT 1 FROM responsibility_operations o WHERE o.responsibility_id=r.id AND o.kind='purge') purge_receipt,
        (SELECT COUNT(*) FROM (SELECT 1 FROM responsibility_operations o WHERE o.responsibility_id=r.id LIMIT 260)) receipts
        FROM responsibilities r LIMIT 257""",
        (TOMBSTONE,),
    ).fetchall()
    state = "known"
    if len(rows) > LIFETIME_IDENTITIES:
        state = "over_limit"
    for row in rows:
        retention = row["retention_state"]
        if (
            retention not in RETENTION_STATES
            or type(row["retention_version"]) is not int
            or row["retention_version"] < 1
            or not row["valid_versions"]
            or any(not _timestamp(row[k]) for k in ("trashed_at", "restored_at", "purged_at"))
            or retention == "trashed"
            and (not row["terminal"] or row["trashed_at"] is None)
            or retention != "purged"
            and row["purged_at"] is not None
            or retention == "purged"
            and (
                not row["terminal"]
                or not row["shell"]
                or row["sources"]
                or row["reviews"]
                or not row["purge_receipt"]
                or row["purged_at"] is None
            )
        ):
            state = "unavailable"
            break
        if row["receipts"] > MAX_RECEIPTS:
            state = "over_limit"
    charged = conn.execute(
        f"SELECT 1 FROM responsibilities WHERE {CHARGED_WATCH_PREDICATE} LIMIT ?", (cap + 1,)
    ).fetchall()
    count = len(charged) if len(charged) <= cap else None
    if count is None and state == "known":
        state = "over_limit"
    if capacity and state == "over_limit" and count is not None:
        # Metadata exhaustion is not evidence that the twenty body slots overflow.
        state = "unavailable"
    return MaintenanceUsage(
        **{
            "state": state,
            "retained_count": count if state == "known" else None,
            "trashed_count": sum(r["retention_state"] == "trashed" for r in rows)
            if state == "known"
            else None,
            "lifetime_count": len(rows) if state == "known" else None,
            "lifetime_remaining": LIFETIME_IDENTITIES - len(rows) if state == "known" else None,
            "lifetime_limit": LIFETIME_IDENTITIES,
            "version": 1,
        }
    ).model_dump()


class PreviewCache:
    def __init__(self, clock, monotonic=None):
        self.clock, self.monotonic = clock, monotonic or time.monotonic
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def issue(self, binding):
        now, tick = self.clock(), self.monotonic()
        expiry = now + timedelta(minutes=5)
        key = secrets.token_urlsafe(24)
        with self.lock:
            while len(self.entries) >= 32:
                self.entries.popitem(last=False)
            self.entries[key] = (binding, now, expiry, tick, tick + 300)
        return key, iso(expiry)

    def check(self, key, binding):
        with self.lock:
            entry = self.entries.get(key)
            if entry is None:
                raise DomainError("RESPONSIBILITY_PREVIEW_EXPIRED")
            old, issued, expiry, started, end = entry
            now, tick = self.clock(), self.monotonic()
            if not issued <= now < expiry or not started <= tick < end:
                self.entries.pop(key, None)
                raise DomainError("RESPONSIBILITY_PREVIEW_EXPIRED")
            if old != binding:
                raise DomainError("RESPONSIBILITY_PREVIEW_CHANGED")


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def owner_epoch(conn, principal, store):
    """Called after the service verifies the actual session and visible settings."""
    settings = conn.execute("SELECT version FROM settings WHERE id=1").fetchone()
    personal = conn.execute("SELECT epoch FROM personal_settings WHERE id=1").fetchone()
    if (
        settings is None
        or personal is None
        or type(settings[0]) is not int
        or settings[0] < 1
        or type(personal[0]) is not int
        or personal[0] < 0
    ):
        raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE")
    return (hashlib.sha256(principal["session"].encode()).hexdigest(), settings[0], personal[0])
