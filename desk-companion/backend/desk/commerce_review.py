"""Durable, login/chat-scoped owner reviews for sandbox commerce providers."""

import hashlib
import json
import re
import threading
from typing import Literal

from pydantic import Field

from .conversation import Conversations
from .schemas import StrictModel
from .store import DomainError, encode


def language_for(message, language):
    return "zh" if language == "zh" or re.search(r"[\u3400-\u9fff]", message) else "en"


class ReviewRef(StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    version: int = Field(ge=1, strict=True)
    amount_minor: int = Field(gt=0, strict=True)


class ReviewDecision(ReviewRef):
    action: Literal["confirm", "decline"]


class ChatReviews:
    # SQL identifiers are fixed by the application, never supplied by a quote or caller.
    tables = {"FLIGHT": "sandbox_flight_bookings", "SHOP": "sandbox_shop_orders"}

    def __init__(self, runtime, kind):
        self.runtime, self.store = runtime, runtime.store
        self.kind, self.table = kind, self.tables[kind]
        self.lock = threading.RLock()
        with self.store.connection(write=True) as db:
            db.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table}(id TEXT PRIMARY KEY,owner TEXT NOT NULL,chat TEXT NOT NULL,data TEXT NOT NULL,serial INTEGER NOT NULL DEFAULT 0)"
            )
            index = "sandbox_flight_chat" if kind == "FLIGHT" else "sandbox_shop_chat"
            db.execute(f"CREATE INDEX IF NOT EXISTS {index} ON {self.table}(owner,chat)")

    def owner(self, principal):
        if (
            not principal
            or not self.store.session_valid(principal.get("session"))
            or not (owner := Conversations.owner(principal))
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        return owner

    def insert(self, row, key, principal, chat):
        owner = self.owner(principal)
        if not chat or chat.owner != owner:
            raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
        ident = hashlib.sha256(key.encode()).hexdigest()[:32]
        row.update(id=ident, task_id=chat.task_id, version=1, state="quoted")
        with self.store.connection(write=True) as db:
            db.execute(
                f"INSERT OR IGNORE INTO {self.table}(id,owner,chat,data) VALUES(?,?,?,?)",
                (ident, owner, chat.id, encode(row)),
            )
        return self._get(ident, owner, chat.id)

    def _get(self, ident, owner, chat):
        with self.store.connection() as db:
            record = db.execute(
                f"SELECT data,serial FROM {self.table} WHERE id=? AND owner=? AND chat=?",
                (ident, owner, chat),
            ).fetchone()
        if not record:
            raise DomainError(self.kind + "_NOT_FOUND", 404)
        return dict(json.loads(record["data"]), _serial=record["serial"])

    def _save(self, row):
        data = {k: v for k, v in row.items() if k != "_serial"}
        with self.store.connection(write=True) as db:
            updated = db.execute(
                f"UPDATE {self.table} SET data=?,serial=serial+1 WHERE id=? AND serial=?",
                (encode(data), row["id"], row["_serial"]),
            )
            if updated.rowcount != 1:
                raise DomainError(self.kind + "_REVIEW_CHANGED", 409)
        row["_serial"] += 1

    def can_resume(self, principal, chat, review, task_id):
        if not chat or not self.enabled or not self.runtime.personal_context.visible(principal):
            return False
        owner = Conversations.owner(principal)
        if not owner or not self.store.session_valid(principal.get("session")):
            return False
        ident = review.id if review else None
        with self.store.connection() as db:
            return (
                db.execute(
                    f"SELECT 1 FROM {self.table} WHERE owner=? AND chat=? AND json_extract(data,'$.task_id') IS ? AND (? IS NULL OR id=?) LIMIT 1",
                    (owner, chat, task_id, ident, ident),
                ).fetchone()
                is not None
            )

    def forget_chat(self, principal, chat):
        owner = Conversations.owner(principal)
        if owner:
            with self.store.connection(write=True) as db:
                db.execute(
                    f"UPDATE {self.table} SET chat='',serial=serial+1 WHERE owner=? AND chat=?",
                    (owner, chat),
                )

    @staticmethod
    def _state(row, state):
        if state != row["state"]:
            row["state"] = state
            row["version"] += 1

    def listing(self, principal, chat):
        owner = self.owner(principal)
        with self.store.connection() as db:
            ids = [
                r[0]
                for r in db.execute(
                    f"SELECT id FROM {self.table} WHERE owner=? AND chat=? ORDER BY rowid DESC",
                    (owner, chat),
                )
            ]
        return [self.read(ident, owner, chat) for ident in ids]
