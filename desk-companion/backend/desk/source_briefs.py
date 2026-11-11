"""Offline comparison of notes the owner already has.

A point quotes one saved note, or it is marked unknown. A missing note stays a
gap. Nothing is fetched and no model is called. Saving needs the owner.
"""

import hashlib
import re
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import ConfigDict, Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode

BRIEF_LIMIT = 8
SOURCE_LIMIT = 4
CLAIM_LIMIT = 6
_ID = re.compile(r"^[0-9a-f]{32}$")


class _In(StrictModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class OpenBrief(_In):
    question: str = Field(max_length=400)
    note: str | None = Field(default=None, max_length=400)


class ReviseBrief(_In):
    question: str | None = Field(default=None, max_length=400)
    note: str | None = Field(default=None, max_length=400)


class AddSource(_In):
    label: str = Field(max_length=160)
    available: bool
    locator: str | None = Field(default=None, max_length=300)
    body: str | None = Field(default=None, max_length=8000)
    gap: str | None = Field(default=None, max_length=400)


class AddClaim(_In):
    kind: Literal["cited", "unknown"]
    text: str = Field(max_length=800)
    source_id: str | None = Field(default=None, max_length=32)
    quote: str | None = Field(default=None, max_length=800)


class ApproveBrief(_In):
    expected_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _plain(value: str, limit: int, *, newlines: bool) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise DomainError("TEXT_REJECTED", 422)
    allowed = "\n\t" if newlines else ""
    if any(ord(ch) < 32 and ch not in allowed for ch in value):
        raise DomainError("TEXT_REJECTED", 422)
    text = value.strip()
    if not text or len(text) > limit:
        raise DomainError("TEXT_REJECTED", 422)
    return text


def _reject_null(model, names) -> None:
    for name in names:
        if name in model.model_fields_set and getattr(model, name) is None:
            raise DomainError("NULL_FIELD", 422)


def _optional(model, name: str, limit: int, *, newlines: bool) -> str | None:
    if name not in model.model_fields_set:
        return None
    return _plain(getattr(model, name), limit, newlines=newlines)


class SourceBriefService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        self._before_commit = None
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_briefs (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    note TEXT,
                    status TEXT NOT NULL,
                    saved_at TEXT,
                    session_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_brief_sources (
                    brief_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    locator TEXT,
                    available INTEGER NOT NULL,
                    gap TEXT,
                    body TEXT,
                    body_sha256 TEXT,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (brief_id, id)
                );
                CREATE TABLE IF NOT EXISTS source_brief_claims (
                    brief_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source_id TEXT,
                    quote TEXT,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (brief_id, id)
                );
                """
            )

    def _owner(self, principal) -> str:
        if (
            not isinstance(principal, dict)
            or principal.get("kind") != "owner"
            or not isinstance(principal.get("session"), str)
            or not principal["session"]
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not self.store.session_valid(principal["session"]):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        return hashlib.sha256(principal["session"].encode()).hexdigest()

    def _commit(self, conn) -> None:
        hook = self._before_commit
        if hook is not None:
            hook(conn)

    def _sources(self, conn, brief_id: str) -> list[dict]:
        rows = conn.execute(
            """
            SELECT id, label, locator, available, gap, body, body_sha256, position
            FROM source_brief_sources WHERE brief_id=? ORDER BY position, id
            """,
            (brief_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "label": row["label"],
                "locator": row["locator"],
                "available": bool(row["available"]),
                "gap": row["gap"],
                "body": row["body"],
                "body_sha256": row["body_sha256"],
                "position": row["position"],
            }
            for row in rows
        ]

    def _claims(self, conn, brief_id: str) -> list[dict]:
        rows = conn.execute(
            """
            SELECT id, kind, text, source_id, quote, position
            FROM source_brief_claims WHERE brief_id=? ORDER BY position, id
            """,
            (brief_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "text": row["text"],
                "source_id": row["source_id"],
                "quote": row["quote"],
                "position": row["position"],
            }
            for row in rows
        ]

    def _digest(self, question: str, note, sources: list[dict], claims: list[dict]) -> str:
        payload = {
            "question": question,
            "note": note,
            "sources": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "locator": item["locator"],
                    "available": item["available"],
                    "gap": item["gap"],
                    "body_sha256": item["body_sha256"],
                }
                for item in sources
            ],
            "claims": [
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "text": item["text"],
                    "source_id": item["source_id"],
                    "quote": item["quote"],
                }
                for item in claims
            ],
        }
        return hashlib.sha256(encode(payload).encode()).hexdigest()

    def _view(self, conn, brief_id: str) -> dict:
        row = conn.execute("SELECT * FROM source_briefs WHERE id=?", (brief_id,)).fetchone()
        if row is None:
            raise DomainError("BRIEF_NOT_FOUND", 404)
        sources = self._sources(conn, brief_id)
        claims = self._claims(conn, brief_id)
        shown = ("id", "label", "locator", "available", "gap", "body", "position")
        public_sources = [{key: item[key] for key in shown} for item in sources]
        return {
            "id": row["id"],
            "question": row["question"],
            "note": row["note"],
            "status": row["status"],
            "sources": public_sources,
            "claims": claims,
            "gaps": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "gap": item["gap"],
                    "locator": item["locator"],
                }
                for item in sources
                if not item["available"]
            ],
            "digest": self._digest(row["question"], row["note"], sources, claims),
            "live_lookup": False,
            "model_call": False,
            "created_at": row["created_at"],
            "saved_at": row["saved_at"],
        }

    def _require(self, conn, brief_id: str) -> dict:
        if not _ID.fullmatch(brief_id or ""):
            raise DomainError("BRIEF_NOT_FOUND", 404)
        row = conn.execute("SELECT * FROM source_briefs WHERE id=?", (brief_id,)).fetchone()
        if row is None:
            raise DomainError("BRIEF_NOT_FOUND", 404)
        return row

    def listing(self, principal) -> dict:
        self._owner(principal)
        with self.store.connection() as conn:
            rows = conn.execute("SELECT id FROM source_briefs ORDER BY created_at, id").fetchall()
            briefs = [self._view(conn, row["id"]) for row in rows]
        return {
            "briefs": briefs,
            "limit": BRIEF_LIMIT,
            "live_lookup": False,
            "model_call": False,
        }

    def read(self, brief_id: str, principal) -> dict:
        self._owner(principal)
        if not _ID.fullmatch(brief_id or ""):
            raise DomainError("BRIEF_NOT_FOUND", 404)
        with self.store.connection() as conn:
            return {"brief": self._view(conn, brief_id)}

    def open(self, payload: OpenBrief, key: str, principal) -> dict:
        session_hash = self._owner(principal)
        _reject_null(payload, ("note",))
        question = _plain(payload.question, 200, newlines=False)
        note = _optional(payload, "note", 200, newlines=False)
        request = {"type": "source_brief_open", **payload.model_dump(exclude_unset=True)}

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            count = conn.execute("SELECT COUNT(*) FROM source_briefs").fetchone()[0]
            if count >= BRIEF_LIMIT:
                raise DomainError("BRIEF_LIMIT", 422)
            now = iso(self.store.clock())
            brief_id = uuid4().hex
            conn.execute(
                """
                INSERT INTO source_briefs
                (id, question, note, status, saved_at, session_hash, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (brief_id, question, note, "draft", None, session_hash, now, now),
            )
            self._commit(conn)
            return {"brief": self._view(conn, brief_id)}

        return self.store.operation(key, request, apply)

    def revise(self, brief_id: str, payload: ReviseBrief, key: str, principal) -> dict:
        self._owner(principal)
        if not payload.model_fields_set:
            raise DomainError("REVISION_EMPTY", 422)
        _reject_null(payload, ("question", "note"))
        question = (
            _plain(payload.question, 200, newlines=False)
            if "question" in payload.model_fields_set
            else None
        )
        note = (
            _plain(payload.note, 200, newlines=False)
            if "note" in payload.model_fields_set
            else None
        )
        request = {
            "type": "source_brief_revise",
            "brief_id": brief_id,
            **payload.model_dump(exclude_unset=True),
        }

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            row = self._require(conn, brief_id)
            if row["status"] != "draft":
                raise DomainError("BRIEF_SAVED", 409)
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE source_briefs SET question=?, note=?, updated_at=? WHERE id=?",
                (
                    question if question is not None else row["question"],
                    note if "note" in payload.model_fields_set else row["note"],
                    now,
                    brief_id,
                ),
            )
            self._commit(conn)
            return {"brief": self._view(conn, brief_id)}

        return self.store.operation(key, request, apply)

    def add_source(self, brief_id: str, payload: AddSource, key: str, principal) -> dict:
        self._owner(principal)
        _reject_null(payload, ("locator", "body", "gap"))
        label = _plain(payload.label, 80, newlines=False)
        locator = _optional(payload, "locator", 200, newlines=False)
        if payload.available:
            if "gap" in payload.model_fields_set:
                raise DomainError("GAP_NOT_ALLOWED", 422)
            if "body" not in payload.model_fields_set:
                raise DomainError("BODY_REQUIRED", 422)
            body = _plain(payload.body, 4000, newlines=True)
            gap = None
            digest = hashlib.sha256(body.encode()).hexdigest()
        else:
            if "body" in payload.model_fields_set:
                raise DomainError("BODY_NOT_ALLOWED", 422)
            if "gap" not in payload.model_fields_set:
                raise DomainError("GAP_REQUIRED", 422)
            body = None
            digest = None
            gap = _plain(payload.gap, 200, newlines=False)
        request = {
            "type": "source_brief_add_source",
            "brief_id": brief_id,
            **payload.model_dump(exclude_unset=True),
        }

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            row = self._require(conn, brief_id)
            if row["status"] != "draft":
                raise DomainError("BRIEF_SAVED", 409)
            count = conn.execute(
                "SELECT COUNT(*) FROM source_brief_sources WHERE brief_id=?", (brief_id,)
            ).fetchone()[0]
            if count >= SOURCE_LIMIT:
                raise DomainError("SOURCE_LIMIT", 422)
            source_id = uuid4().hex
            conn.execute(
                """
                INSERT INTO source_brief_sources
                (brief_id, id, label, locator, available, gap, body, body_sha256, position)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    brief_id,
                    source_id,
                    label,
                    locator,
                    1 if payload.available else 0,
                    gap,
                    body,
                    digest,
                    count + 1,
                ),
            )
            conn.execute(
                "UPDATE source_briefs SET updated_at=? WHERE id=?",
                (iso(self.store.clock()), brief_id),
            )
            self._commit(conn)
            return {"brief": self._view(conn, brief_id)}

        return self.store.operation(key, request, apply)

    def add_claim(self, brief_id: str, payload: AddClaim, key: str, principal) -> dict:
        self._owner(principal)
        _reject_null(payload, ("source_id", "quote"))
        text = _plain(payload.text, 400, newlines=False)
        if payload.kind == "unknown":
            if "source_id" in payload.model_fields_set or "quote" in payload.model_fields_set:
                raise DomainError("UNKNOWN_HAS_NO_SOURCE", 422)
            source_id = None
            quote = None
        else:
            if (
                "source_id" not in payload.model_fields_set
                or "quote" not in payload.model_fields_set
            ):
                raise DomainError("QUOTE_REQUIRED", 422)
            source_id = payload.source_id
            quote = _plain(payload.quote, 400, newlines=True)
            if not _ID.fullmatch(source_id or ""):
                raise DomainError("SOURCE_NOT_IN_BRIEF", 404)
        request = {
            "type": "source_brief_add_claim",
            "brief_id": brief_id,
            **payload.model_dump(exclude_unset=True),
        }

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            row = self._require(conn, brief_id)
            if row["status"] != "draft":
                raise DomainError("BRIEF_SAVED", 409)
            if payload.kind == "cited":
                source = conn.execute(
                    "SELECT available, body FROM source_brief_sources WHERE brief_id=? AND id=?",
                    (brief_id, source_id),
                ).fetchone()
                if source is None:
                    raise DomainError("SOURCE_NOT_IN_BRIEF", 404)
                if not source["available"]:
                    raise DomainError("SOURCE_UNAVAILABLE", 422)
                if not source["body"] or quote not in source["body"]:
                    raise DomainError("QUOTE_NOT_IN_SOURCE", 422)
            count = conn.execute(
                "SELECT COUNT(*) FROM source_brief_claims WHERE brief_id=?", (brief_id,)
            ).fetchone()[0]
            if count >= CLAIM_LIMIT:
                raise DomainError("CLAIM_LIMIT", 422)
            conn.execute(
                """
                INSERT INTO source_brief_claims
                (brief_id, id, kind, text, source_id, quote, position)
                VALUES (?,?,?,?,?,?,?)
                """,
                (brief_id, uuid4().hex, payload.kind, text, source_id, quote, count + 1),
            )
            conn.execute(
                "UPDATE source_briefs SET updated_at=? WHERE id=?",
                (iso(self.store.clock()), brief_id),
            )
            self._commit(conn)
            return {"brief": self._view(conn, brief_id)}

        return self.store.operation(key, request, apply)

    def approve(self, brief_id: str, payload: ApproveBrief, key: str, principal) -> dict:
        self._owner(principal)
        request = {
            "type": "source_brief_approve",
            "brief_id": brief_id,
            "expected_digest": payload.expected_digest,
        }

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            row = self._require(conn, brief_id)
            if row["status"] != "draft":
                raise DomainError("BRIEF_SAVED", 409)
            view = self._view(conn, brief_id)
            if not view["claims"] and not view["gaps"]:
                raise DomainError("NOTHING_TO_SAVE", 422)
            if payload.expected_digest != view["digest"]:
                raise DomainError("BRIEF_CHANGED", 409)
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE source_briefs SET status='saved', saved_at=?, updated_at=? WHERE id=?",
                (now, now, brief_id),
            )
            self._commit(conn)
            return {"brief": self._view(conn, brief_id)}

        return self.store.operation(key, request, apply)


def source_brief_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/source-briefs", dependencies=[Depends(owner)])

    def principal(request: Request):
        token = request.cookies.get("desk_companion_session")
        if not runtime.store.session_valid(token):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"kind": "owner", "id": "owner", "name": "Owner", "session": token}

    @router.get("")
    def listing(request: Request):
        return runtime.source_briefs.listing(principal(request))

    @router.post("")
    def open_brief(payload: OpenBrief, request: Request, key=Depends(operation_id)):
        return runtime.source_briefs.open(payload, key, principal(request))

    @router.get("/{brief_id}")
    def read_brief(brief_id: str, request: Request):
        return runtime.source_briefs.read(brief_id, principal(request))

    @router.post("/{brief_id}/revision")
    def revise_brief(
        brief_id: str, payload: ReviseBrief, request: Request, key=Depends(operation_id)
    ):
        return runtime.source_briefs.revise(brief_id, payload, key, principal(request))

    @router.post("/{brief_id}/sources")
    def add_source(brief_id: str, payload: AddSource, request: Request, key=Depends(operation_id)):
        return runtime.source_briefs.add_source(brief_id, payload, key, principal(request))

    @router.post("/{brief_id}/claims")
    def add_claim(brief_id: str, payload: AddClaim, request: Request, key=Depends(operation_id)):
        return runtime.source_briefs.add_claim(brief_id, payload, key, principal(request))

    @router.post("/{brief_id}/approval")
    def approve(brief_id: str, payload: ApproveBrief, request: Request, key=Depends(operation_id)):
        return runtime.source_briefs.approve(brief_id, payload, key, principal(request))

    return router
