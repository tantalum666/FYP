"""Advisory retained reservations: bounded scalar reads, no recovery or file I/O."""

import re
import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field, model_validator

from .calendar import iso
from .file_store import session_from_request
from .schemas import StrictModel
from .store import DomainError
from .responsibility_retention import watch_accounting
from .work_limits import (
    ARTIFACT_BYTES,
    ARTIFACT_COUNT,
    ARTIFACT_RUN_BYTES,
    ARTIFACT_RUN_COUNT,
    ARTIFACT_TOTAL_BYTES,
    RUN_COUNT,
    SOURCE_BYTES,
    SOURCE_COUNT,
    SOURCE_TOTAL_BYTES,
    WATCH_COUNT,
)

MAX_METADATA_BYTES = 64 * 1024
SafeInteger = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]


class CapacityDimension(StrictModel):
    limit: SafeInteger
    used: SafeInteger | None
    remaining: SafeInteger | None
    state: Literal["known", "over_limit", "unavailable"]

    @model_validator(mode="after")
    def accounting(self):
        if self.used is None:
            if self.remaining is not None or self.state == "known":
                raise ValueError("Unknown usage cannot imply remaining capacity")
        elif (
            self.state == "unavailable"
            or self.remaining != max(0, self.limit - self.used)
            or (self.state == "over_limit") != (self.used > self.limit)
        ):
            raise ValueError("Inconsistent capacity accounting")
        return self


class CountCapacity(StrictModel):
    count: CapacityDimension


class FileCapacity(CountCapacity):
    bytes: CapacityDimension
    file_bytes: SafeInteger


class ArtifactCapacity(FileCapacity):
    per_run_count: SafeInteger
    per_run_bytes: SafeInteger


class WorkCapacityResult(StrictModel):
    basis: Literal["retained_reservations"] = "retained_reservations"
    observed_at: str
    advisory: Literal[True] = True
    sources: FileCapacity
    artifacts: ArtifactCapacity
    runs: CountCapacity
    watches: CountCapacity


def dimension(limit, used=None, *, overflow=False):
    return CapacityDimension(
        limit=limit,
        used=used,
        remaining=None if used is None else max(0, limit - used),
        state="over_limit"
        if overflow or used is not None and used > limit
        else "unavailable"
        if used is None
        else "known",
    )


def scalar_projection(column, field, json_types):
    """Code-owned identifiers only. Nested CASE guards every JSON operation.

    JSON type checks preserve the distinction between integers and booleans.
    Duplicate target keys are ambiguous across SQLite and Python JSON decoders.
    json_each selects only a count, never arbitrary child values into Python.
    """
    return (
        f"CASE WHEN typeof({column})='text' THEN CASE "
        f"WHEN length(CAST({column} AS BLOB))<={MAX_METADATA_BYTES} THEN CASE "
        f"WHEN instr({column},char(0))=0 THEN CASE "
        f"WHEN json_valid({column}) THEN CASE WHEN json_type({column})='object' THEN CASE "
        f"WHEN (SELECT count(*) FROM json_each({column}) WHERE key='{field}')=1 "
        f"THEN CASE WHEN json_type({column},'$.{field}') IN ({json_types}) "
        f"THEN json_extract({column},'$.{field}') END END END END END END END"
    )


BYTE_PROJECTION = scalar_projection("metadata", "byte_count", "'integer'")
HIDDEN_PROJECTION = scalar_projection("data", "hide_private", "'true','false'")


class WorkCapacityService:
    def __init__(self, runtime):
        # Constructing this service does not create tables, directories or workers.
        self.store = runtime.store

    def _authority(self, conn, session_hash):
        if not isinstance(session_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", session_hash):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (session_hash, iso(self.store.clock())),
        ).fetchone():
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        settings = conn.execute(
            f"SELECT version,{HIDDEN_PROJECTION} AS hidden FROM settings WHERE id=1"
        ).fetchone()
        epoch = conn.execute("SELECT epoch FROM personal_settings WHERE id=1").fetchone()
        if (
            settings is None
            or epoch is None
            or type(settings["version"]) is not int
            or settings["version"] < 1
            or type(epoch[0]) is not int
            or epoch[0] < 0
            or settings["hidden"] not in (0, 1)
        ):
            raise DomainError("WORK_CAPACITY_UNAVAILABLE", 409)
        if settings["hidden"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        return settings["version"], epoch[0]

    @staticmethod
    def _count(conn, table, cap):
        # Table is a code-owned literal. A scalar sentinel avoids reading data,
        # IDs, session hashes, goals, statuses or watch bodies.
        rows = conn.execute(f"SELECT 1 FROM {table} LIMIT ?", (cap + 1,)).fetchall()
        return CountCapacity(
            count=dimension(cap, len(rows)) if len(rows) <= cap else dimension(cap, overflow=True)
        )

    @staticmethod
    def _files(conn, kind, cap, byte_cap, file_cap):
        rows = conn.execute(
            f"SELECT {BYTE_PROJECTION} AS byte_count FROM private_files WHERE kind=? LIMIT ?",
            (kind, cap + 1),
        ).fetchall()
        complete = len(rows) <= cap
        valid = complete and all(type(r[0]) is int and 1 <= r[0] <= file_cap for r in rows)
        return dict(
            count=dimension(cap, len(rows)) if complete else dimension(cap, overflow=True),
            bytes=dimension(byte_cap, sum(r[0] for r in rows) if valid else None),
            file_bytes=file_cap,
        )

    @staticmethod
    def _watches(conn):
        usage = watch_accounting(conn, capacity=True)
        return CountCapacity(
            count=dimension(
                WATCH_COUNT, usage["retained_count"], overflow=usage["state"] == "over_limit"
            )
        )

    def _read(self, conn):
        return WorkCapacityResult(
            observed_at=iso(self.store.clock()),
            sources=FileCapacity(
                **self._files(
                    conn,
                    "sources",
                    SOURCE_COUNT,
                    SOURCE_TOTAL_BYTES,
                    SOURCE_BYTES,
                )
            ),
            artifacts=ArtifactCapacity(
                **self._files(
                    conn, "artifacts", ARTIFACT_COUNT, ARTIFACT_TOTAL_BYTES, ARTIFACT_BYTES
                ),
                per_run_count=ARTIFACT_RUN_COUNT,
                per_run_bytes=ARTIFACT_RUN_BYTES,
            ),
            runs=self._count(conn, "agent_runs", RUN_COUNT),
            watches=self._watches(conn),
        )

    def snapshot(self, *, session_hash):
        try:
            with self.store.connection() as conn:
                conn.execute("PRAGMA query_only=ON")
                authority = self._authority(conn, session_hash)
                result = self._read(conn).model_dump()
            # Reopen after closing the observation snapshot. A logout, expiry,
            # hide/show or consent transition cannot revive the old projection.
            with self.store.connection() as conn:
                conn.execute("PRAGMA query_only=ON")
                if self._authority(conn, session_hash) != authority:
                    raise DomainError("WORK_CAPACITY_PRIVACY_CHANGED", 403)
        except sqlite3.Error:
            # Missing/unsupported schema and SQLite failures are never an empty
            # store, partial success or an arbitrary database error disclosure.
            raise DomainError("WORK_CAPACITY_UNAVAILABLE", 409) from None
        return result


def work_capacity_routes(runtime, owner):
    router = APIRouter(prefix="/api/work", dependencies=[Depends(owner)])

    @router.get("/capacity", response_model=WorkCapacityResult)
    def capacity(request: Request):
        return runtime.work_capacity.snapshot(session_hash=session_from_request(request))

    return router
