"""Bind the ordinary desk conversation to the owner's existing opt-in text history.

Only prose is retained. Login-bound live chat IDs and action cards stay ephemeral.
"""

from uuid import uuid4

from .calendar import iso
from .personal_context import fingerprint
from .rank import rank_rows, tokens
from .store import DomainError


class HomeHistory:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS home_conversation (
                    id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL,
                    thread TEXT REFERENCES conversations(id) ON DELETE SET NULL);
                INSERT OR IGNORE INTO home_conversation VALUES(1,1,NULL);
                CREATE TRIGGER IF NOT EXISTS home_conversation_deleted BEFORE DELETE ON conversations
                WHEN OLD.id=(SELECT thread FROM home_conversation WHERE id=1)
                BEGIN UPDATE home_conversation SET thread=NULL,generation=generation+1 WHERE id=1; END;
            """)

    def _state(self, db):
        return db.execute("""SELECT h.generation,h.thread,p.save_text_history,p.save_voice_transcripts,p.epoch
            FROM home_conversation h JOIN personal_settings p ON p.id=h.id WHERE h.id=1""").fetchone()

    def status(self):
        with self.store.connection() as db:
            state = self._state(db)
            return {"enabled": bool(state["save_text_history"]), "generation": state["generation"]}

    def stamp(self, principal, *, spoken=False):
        if not principal or principal.get("kind") != "owner" or not principal.get("session"):
            return None
        with self.store.connection() as db:
            state = self._state(db)
            if (
                state["save_text_history"]
                and (not spoken or state["save_voice_transcripts"])
                and self.store.session_valid(principal["session"], db)
                and not self.store.settings(db)["hide_private"]
            ):
                return state["generation"], state["epoch"]
        return None

    def record(self, stamp, principal, chat, key, payload, reply):
        if (
            not stamp
            or not chat
            or reply.get("kind") != "reply"
            or reply.get("saved")
            or reply.get("proposal")
        ):
            return None
        answer = reply.get("message")
        if not isinstance(answer, str) or not answer.strip():
            return None
        return self.write_pair(
            stamp, principal, chat, key, payload.message, answer, payload.language
        )

    def write_pair(self, stamp, principal, chat, key, question, answer, language, *, spoken=False):
        if (
            not stamp
            or not chat
            or (chat.home_generation is not None and chat.home_generation != stamp[0])
        ):
            return None
        with self.store.connection(write=True) as db:
            state = self._state(db)
            if (
                not state["save_text_history"]
                or stamp != (state["generation"], state["epoch"])
                or (spoken and not state["save_voice_transcripts"])
                or not self.store.session_valid(principal["session"], db)
                or self.store.settings(db)["hide_private"]
            ):
                return None
            thread = state["thread"]
            ids = [fingerprint(["home", key, role]) for role in ("user", "assistant")]
            if db.execute("SELECT 1 FROM conversation_messages WHERE id=?", (ids[0],)).fetchone():
                if spoken:
                    # Late, delivered caption fragments may complete a previously displayed pair.
                    for ident, content in zip(ids, (question, answer)):
                        db.execute(
                            "UPDATE conversation_messages SET content=? WHERE id=? AND conversation_id=? AND context_allowed=1",
                            (content[:8000], ident, thread),
                        )
                return ids
            now = iso(self.store.clock())
            count = db.execute(
                "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id=?", (thread,)
            ).fetchone()[0]
            if not thread or count >= 200:
                if db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] >= 30:
                    return None
                thread = uuid4().hex
                title = " ".join(question.split())[:80]
                db.execute(
                    "INSERT INTO conversations VALUES(?,?,?,1,?,?)",
                    (thread, title, language, now, now),
                )
                db.execute("UPDATE home_conversation SET thread=? WHERE id=1", (thread,))
            for ident, role, body in zip(ids, ("user", "assistant"), (question, answer)):
                db.execute(
                    """INSERT INTO conversation_messages
                    (id,conversation_id,role,content,created_at,mode,context_allowed) VALUES(?,?,?,?,?,?,1)""",
                    (
                        ident,
                        thread,
                        role,
                        body[:8000],
                        now,
                        "voice_transcript" if spoken else "ordinary_text",
                    ),
                )
            db.execute(
                "UPDATE conversations SET updated_at=?,version=version+1 WHERE id=?", (now, thread)
            )
            self.store.bump(db)
        chat.home_generation = stamp[0]
        return ids

    def view(self, principal):
        with self.store.connection() as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            state = self._state(db)
            rows = db.execute(
                """SELECT id,role,content AS body,created_at AS at FROM conversation_messages
                WHERE conversation_id=? ORDER BY rowid DESC LIMIT 40""",
                (state["thread"] if state["save_text_history"] else None,),
            ).fetchall()
        chats = self.runtime.voice.conversations
        active = None
        if state["save_text_history"]:
            with chats.lock:
                chats.prune()
                active = max(
                    (
                        c
                        for c in chats.entries.values()
                        if c.owner == chats.owner(principal)
                        and c.task_id is None
                        and c.home_generation == state["generation"]
                    ),
                    key=lambda c: c.touched,
                    default=None,
                )
        return {
            "enabled": bool(state["save_text_history"]),
            "generation": state["generation"],
            "live_id": active.id if active else None,
            "turns": [dict(r) for r in reversed(rows)],
        }

    def start_new(self, principal, generation, key):
        def apply(db):
            self.runtime.personal_context.require_owner_transaction(db, principal)
            state = self._state(db)
            if state["generation"] != generation:
                raise DomainError("VERSION_CONFLICT", 409)
            db.execute(
                "UPDATE home_conversation SET generation=generation+1,thread=NULL WHERE id=1"
            )
            return {"generation": generation + 1}

        return self.runtime.personal_context.operation(
            key, {"kind": "new_home_conversation", "generation": generation}, apply
        )

    def archive_live(self, db, chat):
        if not chat or chat.task_id or chat.home_generation is None:
            return False
        return bool(
            db.execute(
                """UPDATE home_conversation SET generation=generation+1,thread=NULL
            WHERE id=1 AND generation=? AND thread IS NOT NULL""",
                (chat.home_generation,),
            ).rowcount
        )

    def _permitted_thread(self, db, kind):
        state = self._state(db)
        settings = self.runtime.personal_context.settings(db)
        allowed = any(
            d["kind"] == kind and d["id"] in settings["approved_destinations"]
            for d in settings["destinations"]
        )
        if (
            not (
                state["save_text_history"]
                and state["thread"]
                and allowed
                and settings["use_text_history_in_ai"]
            )
            or self.store.settings(db)["hide_private"]
        ):
            return None
        return state["thread"]

    def permitted(self, db, kind):
        thread = self._permitted_thread(db, kind)
        return self.runtime.conversations.context(db, thread) if thread else []

    def matching(self, db, kind, topic):
        """Search only this saved conversation's eligible owner statements."""
        thread = self._permitted_thread(db, kind)
        common = {
            "the",
            "and",
            "was",
            "what",
            "were",
            "that",
            "with",
            "from",
            "this",
            "please",
            "about",
            "之前",
            "说过",
            "我们",
            "记得",
            "什么",
        }
        anchors = {t for t in tokens(topic) if len(t) >= (3 if t.isascii() else 2)} - common
        if not anchors or not thread:
            return []
        candidates = []
        for row in db.execute(
            """SELECT id,created_at,content FROM conversation_messages
            WHERE conversation_id=? AND role='user' AND context_allowed=1
            ORDER BY rowid DESC LIMIT 100""",
            (thread,),
        ):
            if anchors.intersection(tokens(row["content"])):
                candidates.append(
                    {
                        "text": row["content"],
                        "time": row["created_at"],
                        "id": row["id"],
                        "payload": {
                            "role": "user",
                            "content": row["content"][:350],
                            "at": row["created_at"],
                        },
                    }
                )
        return rank_rows(topic, candidates, limit=3)

    def provider_turns(self, principal, kind):
        if not principal or principal.get("kind") != "owner" or not principal.get("session"):
            return []
        with self.store.connection() as db:
            if not self.store.session_valid(principal["session"], db):
                return []
            return [
                {"role": m["role"], "body": m["content"][:500]}
                for m in reversed(self.permitted(db, kind))
            ]

    def recall_for_question(self, principal, topic):
        if not principal or principal.get("kind") != "owner" or not principal.get("session"):
            return []
        with self.store.connection() as db:
            if not self.store.session_valid(principal["session"], db):
                return []
            return self.matching(db, "text", topic)


class SpokenHomeTurns:
    """Collect only captions actually released to the owner, never audio or raw provider events."""

    def __init__(self, history, principal, chat, session, language):
        self.history, self.principal, self.chat = history, principal, chat
        self.session, self.language = session, language
        self.stamp = history.stamp(principal, spoken=True) if chat and not chat.task_id else None
        self.groups = {}
        self.changed = set()
        self.interrupted_through = -1

    def delivered(self, event):
        if not self.stamp:
            return
        if event["type"] in {"interrupted", "error"}:
            self.interrupted_through = max(self.changed, default=self.interrupted_through)
            for group in self.changed:
                self.groups.pop(group, None)
            self.changed.clear()
        elif event["type"] == "transcript":
            group, role, text = event.get("caption_group"), event.get("role"), event.get("text")
            if (
                type(group) is not int
                or group <= self.interrupted_through
                or role not in ("user", "assistant")
                or not isinstance(text, str)
            ):
                return
            pair = self.groups.setdefault(group, {"user": "", "assistant": ""})
            pair[role] = (
                text if event.get("caption_replace") or event.get("final") else pair[role] + text
            )[:8000]
            self.changed.add(group)
            if len(self.groups) > 40:
                retired = min(self.groups)
                del self.groups[retired]
                self.changed.discard(retired)
        elif event["type"] == "turn_complete":
            for group in sorted(self.changed):
                pair = self.groups[group]
                if pair["user"].strip() and pair["assistant"].strip():
                    self.history.write_pair(
                        self.stamp,
                        self.principal,
                        self.chat,
                        f"voice/{self.session}/{group}",
                        pair["user"],
                        pair["assistant"],
                        self.language,
                        spoken=True,
                    )
            self.changed.clear()
