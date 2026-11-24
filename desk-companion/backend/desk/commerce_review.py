"""Durable, login/chat-scoped owner reviews for sandbox commerce providers."""

import hashlib
import json
import re
import threading
from contextlib import nullcontext
from typing import Literal

from pydantic import Field

from .calendar import iso
from .conversation import Conversations
from . import quiet_changes
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
    tables = {"FLIGHT": "sandbox_flight_bookings", "SHOP": "sandbox_shop_orders", "LIVE_FLIGHT": "live_flight_checkouts"}

    def __init__(self, runtime, kind):
        self.runtime, self.store = runtime, runtime.store
        self.kind, self.table = kind, self.tables[kind]
        self.lock = threading.RLock()
        with self.store.connection(write=True) as db:
            db.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table}(id TEXT PRIMARY KEY,owner TEXT NOT NULL,chat TEXT NOT NULL,data TEXT NOT NULL,serial INTEGER NOT NULL DEFAULT 0)"
            )
            index = {"FLIGHT": "sandbox_flight_chat", "SHOP": "sandbox_shop_chat", "LIVE_FLIGHT": "live_flight_chat"}[kind]
            db.execute(f"CREATE INDEX IF NOT EXISTS {index} ON {self.table}(owner,chat)")
            db.execute(
                f"CREATE INDEX IF NOT EXISTS {index}_due ON {self.table}"
                "(json_extract(data,'$.state'),json_extract(data,'$.next_read'))"
            )

    def owner(self, principal):
        if (
            not principal
            or not self.store.session_valid(principal.get("session"))
            or not (owner := Conversations.owner(principal))
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        return owner

    def insert(self, row, key, principal, chat, *, state="quoted"):
        owner = self.owner(principal)
        if not chat or chat.owner != owner:
            raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
        ident = hashlib.sha256(key.encode()).hexdigest()[:32]
        row.update(id=ident, task_id=chat.task_id, version=1, state=state)
        with self.store.connection(write=True) as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            db.execute(
                f"INSERT OR IGNORE INTO {self.table}(id,owner,chat,data) VALUES(?,?,?,?)",
                (ident, owner, chat.id, encode(row)),
            )
        return self._get(ident, owner, chat.id, include_unquoted=True)

    def _get(self, ident, owner, chat, *, include_unquoted=False):
        with self.store.connection() as db:
            record = db.execute(
                f"SELECT data,serial FROM {self.table} WHERE id=? AND owner=? AND chat=? "
                "AND (? OR json_type(data,'$.quote')='object')",
                (ident, owner, chat, include_unquoted or self.kind != "FLIGHT"),
            ).fetchone()
        if not record:
            raise DomainError(self.kind + "_NOT_FOUND", 404)
        row = json.loads(record["data"])
        return dict(row, _serial=record["serial"])

    def _follow_scope(self, conn, owner, chat, ident):
        # The same hash identifies the original login and the order. No session
        # cookie is copied into a worker or persisted with an order.
        scope = conn.execute(
            f"""SELECT p.version, s.version, c.epoch FROM {self.table} o
                JOIN sessions l ON l.token_hash=o.owner
                JOIN workspace_preferences p ON p.id=1
                JOIN settings s ON s.id=1
                JOIN personal_settings c ON c.id=1
                WHERE o.id=? AND o.owner=? AND o.chat=? AND o.chat!='' AND l.expires>?
                  AND COALESCE(json_extract(p.data,'$.proactivity'),'normal')!='off'""",
            (ident, owner, chat, iso(self.store.clock())),
        ).fetchone()
        return tuple(scope) if scope and not self.store.settings(conn)["hide_private"] else None

    def follow_one(self):
        """Refresh one already-approved order using its existing read-only reconciliation."""
        if not self.enabled:
            return
        now = self.store.clock()
        states = ",".join("?" for _ in self.follow_states)
        with self.store.connection() as db:
            candidate = db.execute(
                f"""SELECT o.id,o.owner,o.chat FROM {self.table} o JOIN sessions l ON l.token_hash=o.owner
                    WHERE o.chat!='' AND l.expires>? AND json_extract(o.data,'$.approved') IS NOT NULL
                      AND json_extract(o.data,'$.state') IN ({states})
                      AND json_extract(o.data,'$.next_read')<=?
                    ORDER BY json_extract(o.data,'$.next_read'),o.rowid LIMIT 1""",
                (iso(now), *self.follow_states, now.timestamp()),
            ).fetchone()
        if candidate:
            self.read(candidate["id"], candidate["owner"], candidate["chat"], following=True)

    def _read_row(self, ident, owner, chat, following):
        row = self._get(ident, owner, chat)
        if following:
            with self.store.connection() as db:
                scope = self._follow_scope(db, owner, chat, ident)
            if scope is None:
                return None
            row["_follow"] = (owner, chat, scope)
        return row

    def _save(self, row):
        with self.store.connection(write=True) as db:
            self._write_row(db, row)

    def _write_row(self, db, row):
        if "_follow" in row:
            owner, chat, scope = row["_follow"]
            if self._follow_scope(db, owner, chat, row["id"]) != scope:
                raise DomainError("COMMERCE_FOLLOW_SCOPE_CHANGED", 409)
        original = db.execute(
            f"SELECT owner,chat,data FROM {self.table} WHERE id=? AND serial=?",
            (row["id"], row["_serial"]),
        ).fetchone()
        if original and original["chat"]:
            quiet_changes.observe_commerce(self.runtime, db, self.kind, original, row)
        data = {k: v for k, v in row.items() if k not in {"_serial", "_follow"}}
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
        with self.store.connection() as db:
            return self.has_chat(db, owner, chat, task_id, review.id if review else None)

    def has_chat(self, db, owner, chat, task_id, ident=None):
        return db.execute(
            f"SELECT 1 FROM {self.table} WHERE owner=? AND chat=? "
            "AND json_extract(data,'$.task_id') IS ? AND (? IS NULL OR id=?) LIMIT 1",
            (owner, chat, task_id, ident, ident),
        ).fetchone() is not None

    def forget_chat(self, principal, chat, db=None):
        owner = Conversations.owner(principal)
        if owner:
            with nullcontext(db) if db is not None else self.store.connection(write=True) as db:
                db.execute(
                    f"DELETE FROM notice_inbox WHERE source IN "
                    f"(SELECT ? || id FROM {self.table} WHERE owner=? AND chat=?)",
                    (self.kind.lower() + "/", owner, chat),
                )
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
                    f"SELECT id FROM {self.table} WHERE owner=? AND chat=? "
                    "AND (? OR json_type(data,'$.quote')='object') ORDER BY rowid DESC",
                    # Only sandbox flight lists store unquoted menu rows beside their bookings.
                    (owner, chat, self.kind != "FLIGHT"),
                )
            ]
        return [self.read(ident, owner, chat) for ident in ids]

    def pending_reviews(self, db, chat, now, limit):
        """Read current terms in the caller's authorized snapshot, without reconciliation."""
        if not self.enabled:
            return [], False
        milliseconds = int(now.timestamp() * 1000)
        rows = db.execute(
            f"""SELECT data FROM {self.table}
                WHERE owner=? AND chat=? AND json_extract(data,'$.task_id') IS ?
                  AND json_extract(data,'$.state') IN ('quoted','reprice')
                  AND CASE WHEN ?='FLIGHT' AND json_extract(data,'$.state')='reprice'
                           THEN json_extract(data,'$.question.expires')>?
                           ELSE json_extract(data,'$.expires')>? END
                ORDER BY json_extract(data,'$.state')='reprice' DESC,rowid DESC LIMIT ?""",
            (chat.owner, chat.id, chat.task_id, self.kind, milliseconds, iso(now), limit + 1),
        ).fetchall()
        return [
            view for row in rows[:limit]
            if (view := self.review_view(db, json.loads(row["data"]))) is not None
        ], len(rows) > limit
