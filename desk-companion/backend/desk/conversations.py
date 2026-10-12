"""Opt-in local text history and content-free repeat receipts. Never stores voice."""

from typing import Literal
from uuid import uuid4

from pydantic import Field

from .calendar import iso
from .context import fingerprint
from .schemas import StrictModel
from .store import DomainError


class ConversationInput(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    language: Literal["en", "zh"] = "en"


class ConversationAction(StrictModel):
    action: Literal["rename", "delete"]
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ConversationService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.personal = runtime.personal_context
        self.active_conversations = set()
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,
                    language TEXT NOT NULL,version INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conversation_messages(id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL,mode TEXT,
                    proposal_id TEXT,proposal_kind TEXT,context_allowed INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS conversation_sends(id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,
                    state TEXT NOT NULL,epoch INTEGER NOT NULL,conversation_id TEXT,user_id TEXT,assistant_id TEXT);
            """)

    @staticmethod
    def view(conn, row):
        return {
            **dict(row),
            "message_count": conn.execute(
                "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id=?", (row["id"],)
            ).fetchone()[0],
        }

    def get(self, conn, conversation_id):
        row = conn.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if not row:
            raise DomainError("CONVERSATION_NOT_FOUND", 404)
        return row

    def listing(self):
        with self.store.connection() as conn:
            return [
                self.view(conn, r)
                for r in conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_at DESC,id LIMIT 30"
                )
            ]

    def messages(self, conn, conversation_id):
        return [
            dict(row)
            for row in conn.execute(
                """SELECT m.id,m.role,m.content,m.created_at,m.mode,
            m.proposal_id,m.proposal_kind,p.state AS proposal_state FROM conversation_messages m
            LEFT JOIN assistant_proposals p ON m.proposal_id=p.id WHERE conversation_id=? ORDER BY m.rowid""",
                (conversation_id,),
            )
        ]

    def detail(self, conversation_id):
        with self.store.connection() as conn:
            return {
                "conversation": self.view(conn, self.get(conn, conversation_id)),
                "messages": self.messages(conn, conversation_id),
            }

    def render(self, conn, receipt):
        row = conn.execute(
            "SELECT * FROM conversations WHERE id=?", (receipt["conversation_id"],)
        ).fetchone()
        return {**receipt, "conversation": self.view(conn, row) if row else None}

    def create(self, payload, key):
        def apply(conn):
            if not self.personal.settings(conn)["save_text_history"]:
                raise DomainError("TEXT_HISTORY_DISABLED", 409)
            if conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] >= 30:
                raise DomainError("CONVERSATION_LIMIT_REACHED", 422)
            if not payload.title.strip():
                raise DomainError("CONVERSATION_TITLE_REQUIRED", 422)
            conversation_id, now = uuid4().hex, iso(self.store.clock())
            conn.execute(
                "INSERT INTO conversations VALUES(?,?,?,1,?,?)",
                (conversation_id, payload.title.strip(), payload.language, now, now),
            )
            return {"conversation_id": conversation_id}

        return self.personal.operation(
            key, {"kind": "conversation_create", **payload.model_dump()}, apply, self.render
        )

    def action(self, conversation_id, payload, key):
        def apply(conn):
            row = self.get(conn, conversation_id)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if payload.action == "delete":
                conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
                self.personal.invalidate(conn, exclude_history=False)
            else:
                if not payload.title or not payload.title.strip():
                    raise DomainError("CONVERSATION_TITLE_REQUIRED", 422)
                conn.execute(
                    "UPDATE conversations SET title=?,version=version+1,updated_at=? WHERE id=?",
                    (payload.title.strip(), iso(self.store.clock()), conversation_id),
                )
            return {"conversation_id": conversation_id, "deleted": payload.action == "delete"}

        return self.personal.operation(
            key,
            {"kind": "conversation_action", "id": conversation_id, **payload.model_dump()},
            apply,
            self.render,
        )

    def context(self, conn, conversation_id):
        self.get(conn, conversation_id)
        rows = list(
            conn.execute(
                "SELECT role,content FROM conversation_messages WHERE conversation_id=? AND context_allowed=1 ORDER BY rowid DESC LIMIT 12",
                (conversation_id,),
            )
        )
        selected, size = [], 0
        for row in rows:
            if size + len(row["content"]) > 12000:
                break
            selected.append(dict(row))
            size += len(row["content"])
        return list(reversed(selected))

    def send(self, payload, key, reply_fn, principal=None):
        self.runtime.memories.expire()
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        digest = fingerprint(
            {
                "payload": payload.model_dump(),
                "principal": {k: (principal or {}).get(k) for k in ("kind", "id")},
            }
        )
        conversation_id = payload.conversation_id
        with self.personal.lock:
            visible_at_start = self.personal.visible(principal)
            if conversation_id:
                self.personal.require_visible(principal)
            with self.store.connection(write=True) as conn:
                settings = self.personal.settings(conn)
                epoch = fingerprint(self.personal.revision())
                previous = conn.execute(
                    "SELECT * FROM conversation_sends WHERE id=?", (key,)
                ).fetchone()
                if previous:
                    if previous["request_hash"] != digest:
                        raise DomainError("OPERATION_ID_CONFLICT")
                    cached = self.personal.replies.get(key)
                    if (
                        cached
                        and previous["epoch"] == epoch
                        and (not principal or principal.get("kind") != "owner" or visible_at_start)
                    ):
                        return cached
                    if (
                        previous["state"] == "complete"
                        and previous["epoch"] == epoch
                        and conversation_id
                        and visible_at_start
                    ):
                        row = conn.execute(
                            "SELECT * FROM conversation_messages WHERE id=? AND conversation_id=?",
                            (previous["assistant_id"], conversation_id),
                        ).fetchone()
                        if row:
                            return {
                                "mode": row["mode"],
                                "kind": "reply",
                                "message": row["content"],
                                "conversation_id": conversation_id,
                                "history_saved": True,
                                "user_message_id": previous["user_id"],
                                "assistant_message_id": row["id"],
                                "reply_recovered": True,
                                "proposal_id": row["proposal_id"],
                                "proposal_kind": row["proposal_kind"],
                            }
                    # A durable receipt prevents uncertain retries from rerunning tools/provider calls.
                    raise DomainError("ASSISTANT_REPLY_NOT_RETAINED", 410)
                if conversation_id:
                    if conversation_id in self.active_conversations:
                        raise DomainError("CONVERSATION_BUSY", 409)
                    if not settings["save_text_history"]:
                        raise DomainError("TEXT_HISTORY_DISABLED", 409)
                    thread = self.get(conn, conversation_id)
                    if self.view(conn, thread)["message_count"] >= 200:
                        raise DomainError("CONVERSATION_FULL", 422)
                conn.execute(
                    "INSERT INTO conversation_sends VALUES(?,?,'pending',?,?,NULL,NULL)",
                    (key, digest, epoch, conversation_id),
                )
            if conversation_id:
                self.active_conversations.add(conversation_id)
        # Network/model work must not delay owner revoke, forget or context edits.
        try:
            reply = reply_fn(payload, key, principal=principal)
            with self.personal.lock:
                if visible_at_start and not self.personal.visible(principal):
                    self.personal.replies.clear()
                    raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
                if fingerprint(self.personal.revision()) != epoch:
                    self.personal.replies.clear()
                    raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
                with self.store.connection(write=True) as conn:
                    # A concurrent privacy toggle never causes a late reply to be saved.
                    if conversation_id and (
                        self.store.settings(conn)["hide_private"]
                        or not self.personal.settings(conn)["save_text_history"]
                    ):
                        raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
                    result = {
                        **reply,
                        "conversation_id": conversation_id,
                        "history_saved": bool(conversation_id),
                    }
                    user_id = assistant_id = None
                    if conversation_id:
                        thread = self.get(conn, conversation_id)
                        if self.view(conn, thread)["message_count"] >= 200:
                            raise DomainError("CONVERSATION_FULL", 422)
                        user_id, assistant_id, now = (
                            uuid4().hex,
                            uuid4().hex,
                            iso(self.store.clock()),
                        )
                        proposal = reply.get("proposal", {})
                        for message_id, role, content, mode in [
                            (user_id, "user", payload.message, None),
                            (
                                assistant_id,
                                "assistant",
                                str(reply.get("message", ""))[:4000],
                                reply.get("mode"),
                            ),
                        ]:
                            conn.execute(
                                "INSERT INTO conversation_messages VALUES(?,?,?,?,?,?,?,?,1)",
                                (
                                    message_id,
                                    conversation_id,
                                    role,
                                    content,
                                    now,
                                    mode,
                                    proposal.get("id") if role == "assistant" else None,
                                    proposal.get("kind") if role == "assistant" else None,
                                ),
                            )
                        conn.execute(
                            "UPDATE conversations SET version=version+1,updated_at=? WHERE id=?",
                            (now, conversation_id),
                        )
                        self.store.bump(conn)
                        result |= {"user_message_id": user_id, "assistant_message_id": assistant_id}
                    conn.execute(
                        "UPDATE conversation_sends SET state='complete',user_id=?,assistant_id=? WHERE id=?",
                        (user_id, assistant_id, key),
                    )
                # Deliberately volatile. Clear on correction/forget/settings change, process restart, or capacity.
                if len(self.personal.replies) >= 100:
                    self.personal.replies.clear()
                self.personal.replies[key] = result
                return result
        finally:
            with self.personal.lock:
                self.active_conversations.discard(conversation_id)
