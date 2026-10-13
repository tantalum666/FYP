"""Exact schema-3 capture ledger, created only by Store's explicit migration gate.

This module performs no capture, service startup, owner creation or file recovery.
Private JSON is deliberately not decoded by structural/identity validation.
"""

import re
import sqlite3
from contextlib import closing

from .store import DomainError

SCHEMA_VERSION = 3
CAPTURE_TABLES = frozenset({"public_captures", "public_capture_operations"})
CAPTURE_STATES = (
    "review",
    "queued",
    "fetching",
    "publishing",
    "verified",
    "expired",
    "failed",
    "cancelled",
    "unknown",
)


def _hex(name, size):
    return (
        f"typeof({name})='text' AND length({name})={size} "
        f"AND length(CAST({name} AS BLOB))={size} "
        f"AND {name} NOT GLOB '*[^0-9a-f]*'"
    )


CAPTURE_DDL = (
    f"""CREATE TABLE public_captures(
        id TEXT PRIMARY KEY NOT NULL CHECK({_hex("id", 32)}),
        state TEXT NOT NULL CHECK(state IN {CAPTURE_STATES}),
        version INTEGER NOT NULL CHECK(typeof(version)='integer' AND version BETWEEN 1 AND 9007199254740991),
        intent_json TEXT NOT NULL CHECK(typeof(intent_json)='text' AND length(CAST(intent_json AS BLOB)) BETWEEN 1 AND 8192),
        intent_hash TEXT NOT NULL CHECK({_hex("intent_hash", 64)}),
        policy_version INTEGER NOT NULL CHECK(typeof(policy_version)='integer' AND policy_version=1),
        session_hash TEXT NOT NULL CHECK({_hex("session_hash", 64)}),
        privacy_revision TEXT NOT NULL CHECK(typeof(privacy_revision)='text' AND length(privacy_revision) BETWEEN 1 AND 200),
        claim TEXT CHECK(claim IS NULL OR (typeof(claim)='text' AND length(claim) BETWEEN 1 AND 100)),
        generation INTEGER NOT NULL CHECK(typeof(generation)='integer' AND generation BETWEEN 0 AND 9007199254740991),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        approved_at TEXT, deadline_at TEXT,
        dispatch_possible INTEGER NOT NULL DEFAULT 0 CHECK(typeof(dispatch_possible)='integer' AND dispatch_possible IN(0,1)),
        dispatch_at TEXT,
        cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(typeof(cancel_requested)='integer' AND cancel_requested IN(0,1)),
        source_operation_key TEXT NOT NULL UNIQUE CHECK(typeof(source_operation_key)='text' AND length(source_operation_key) BETWEEN 1 AND 100),
        source_id TEXT CHECK(source_id IS NULL OR ({_hex("source_id", 32)})),
        stage TEXT NOT NULL CHECK(typeof(stage)='text' AND length(stage) BETWEEN 1 AND 100),
        error_code TEXT CHECK(error_code IS NULL OR (typeof(error_code)='text' AND length(error_code) BETWEEN 1 AND 100)),
        acquisition_json TEXT CHECK(acquisition_json IS NULL OR (typeof(acquisition_json)='text' AND length(CAST(acquisition_json AS BLOB)) BETWEEN 1 AND 4096))
    )""",
    f"""CREATE TABLE public_capture_operations(
        operation_key TEXT PRIMARY KEY NOT NULL CHECK(typeof(operation_key)='text' AND length(operation_key) BETWEEN 1 AND 100),
        kind TEXT NOT NULL CHECK(kind IN('prepare','approve','cancel')),
        request_hash TEXT NOT NULL CHECK({_hex("request_hash", 64)}),
        capture_id TEXT NOT NULL CHECK({_hex("capture_id", 32)}),
        FOREIGN KEY(capture_id) REFERENCES public_captures(id),
        UNIQUE(capture_id,kind)
    )""",
)
CAPTURE_INDEX_DDL = (
    "CREATE INDEX public_captures_created ON public_captures(created_at,id)",
    "CREATE INDEX public_capture_operations_capture ON public_capture_operations(capture_id)",
)


def initialize_public_capture_schema(conn):
    """Caller owns one transaction containing these statements and user_version."""
    for statement in (*CAPTURE_DDL, *CAPTURE_INDEX_DDL):
        conn.execute(statement)


def _structures(conn):
    rows = conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE "
        "tbl_name IN ('public_captures','public_capture_operations') "
        "OR name IN ('public_captures','public_capture_operations',"
        "'public_captures_created','public_capture_operations_capture')"
    )
    # Exact code-owned SQL captures CHECK/FK/default/unique/index predicates, not
    # merely column names. Do not normalize whitespace inside quoted values.
    return sorted((r[0], r[1], r[2], r[3]) for r in rows)


def validate_public_capture_schema(conn, *, absent=False):
    actual = _structures(conn)
    if absent:
        if actual:
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        return
    with closing(sqlite3.connect(":memory:")) as expected:
        initialize_public_capture_schema(expected)
        if actual != _structures(expected):
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    # Read scalar identity/control fields only. Invalid private JSON must not
    # prevent hidden cancellation; its semantic validation belongs to the service.
    rows = conn.execute(
        "SELECT "
        + ",".join(
            (
                _bounded_text("id", 32),
                _bounded_text("state", 20),
                _bounded_int("version", 1),
                _bounded_text("intent_hash", 64),
                _bounded_int("policy_version", 1, 1),
                _bounded_text("session_hash", 64),
                _bounded_int("generation", 0),
                _bounded_int("dispatch_possible", 0, 1),
                _bounded_int("cancel_requested", 0, 1),
                _bounded_text("source_operation_key", 100),
                _bounded_text("source_id", 32, nullable=True),
            )
        )
        + " FROM public_captures LIMIT 201"
    ).fetchall()
    if len(rows) > 200:
        raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    identities = set()
    source_keys = set()
    for row in rows:
        cid, state, version, digest, policy, session, generation, dispatch, cancel, key, source = (
            row
        )
        if (
            not _valid_hex(cid, 32)
            or cid in identities
            or state not in CAPTURE_STATES
            or type(version) is not int
            or not 1 <= version <= 9007199254740991
            or not _valid_hex(digest, 64)
            or type(policy) is not int
            or policy != 1
            or not _valid_hex(session, 64)
            or type(generation) is not int
            or not 0 <= generation <= 9007199254740991
            or type(dispatch) is not int
            or dispatch not in (0, 1)
            or type(cancel) is not int
            or cancel not in (0, 1)
            or not isinstance(key, str)
            or not 1 <= len(key) <= 100
            or key in source_keys
            or (source is not None and not _valid_hex(source, 32))
        ):
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        identities.add(cid)
        source_keys.add(key)
    operations = conn.execute(
        "SELECT "
        + ",".join(
            (
                _bounded_text("operation_key", 100),
                _bounded_text("kind", 10),
                _bounded_text("request_hash", 64),
                _bounded_text("capture_id", 32),
            )
        )
        + " FROM public_capture_operations LIMIT 601"
    ).fetchall()
    seen_keys, seen_kinds = set(), set()
    if len(operations) > 600:
        raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
    for key, kind, digest, cid in operations:
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 100
            or key in seen_keys
            or kind not in {"prepare", "approve", "cancel"}
            or not _valid_hex(digest, 64)
            or not _valid_hex(cid, 32)
            or cid not in identities
            or (cid, kind) in seen_kinds
        ):
            raise DomainError("SCHEMA_STRUCTURE_UNSUPPORTED")
        seen_keys.add(key)
        seen_kinds.add((cid, kind))


def _bounded_int(column, low, high=9007199254740991):
    return (
        f"CASE WHEN typeof({column})='integer' AND {column} BETWEEN {low} AND {high} "
        f"THEN {column} ELSE NULL END"
    )


def _bounded_text(column, limit, *, nullable=False):
    # Avoid materializing an unbounded corrupt scalar in Python. SQL checks byte
    # length before projection; the invalid marker cannot be a valid identity.
    null = f"WHEN {column} IS NULL THEN NULL " if nullable else ""
    return (
        f"CASE {null}WHEN typeof({column})='text' AND "
        f"length({column}) BETWEEN 1 AND {limit} AND "
        f"length(CAST({column} AS BLOB)) BETWEEN 1 AND {limit * 4} "
        f"AND instr({column},char(0))=0 THEN {column} "
        "ELSE x'00' END"
    )


def _valid_hex(value, size):
    return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{size}}}", value) is not None
