"""Local ownership and cleanup receipts for temporary provider sessions. No transcript or tokens."""

from datetime import timedelta
from uuid import uuid4

from .calendar import iso
from .store import DomainError, encode


class TextSessionStore:
    def __init__(self, store):
        self.store = store
        self.instance = uuid4().hex
        with store.connection(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS text_provider_sessions(
                marker TEXT PRIMARY KEY, destination TEXT NOT NULL, instance TEXT NOT NULL,
                chat TEXT, authority TEXT NOT NULL, binding TEXT NOT NULL, sid TEXT, last_turn TEXT, last_operation TEXT, first_operation TEXT,
                state TEXT NOT NULL, expires TEXT NOT NULL, retry_after TEXT NOT NULL DEFAULT ''
            )""")

    def claim(self, key, request_hash, fallback, destination, chat, binding, authority):
        now = self.store.clock()
        expiry = iso(now + timedelta(seconds=100))
        with self.store.connection(write=True) as db:
            # If a process dies after dispatch, a repeat cannot gain a second run or a new grant.
            claimed = db.execute(
                "INSERT OR IGNORE INTO assistant_replies VALUES(?,?,?)",
                (key, request_hash, encode(fallback)),
            ).rowcount
            if not claimed:
                raise DomainError("OPERATION_ID_CONFLICT", 409)
            if chat:
                row = db.execute(
                    """SELECT * FROM text_provider_sessions WHERE chat=? AND
                    destination=? AND instance=? AND binding=? AND state='idle' AND expires>?
                    ORDER BY expires DESC LIMIT 1""",
                    (chat.id, destination, self.instance, binding, iso(now)),
                ).fetchone()
                db.execute(
                    "UPDATE text_provider_sessions SET state='closing' WHERE chat=? AND state='idle'",
                    (chat.id,),
                )
                history = {item.get("operation_id") for item in chat.items[-16:]}
                if row and {row["first_operation"], row["last_operation"]} <= history:
                    db.execute(
                        "UPDATE text_provider_sessions SET state='active',expires=? WHERE marker=?",
                        (expiry, row["marker"]),
                    )
                    return dict(row)
            marker = uuid4().hex
            db.execute(
                """INSERT INTO text_provider_sessions
                (marker,destination,instance,chat,binding,authority,first_operation,state,expires) VALUES(?,?,?,?,?,?,?,'active',?)""",
                (
                    marker,
                    destination,
                    self.instance,
                    chat.id if chat else None,
                    binding,
                    authority,
                    next(
                        (v["operation_id"] for v in chat.items[-16:] if v.get("operation_id")), key
                    )
                    if chat
                    else key,
                    expiry,
                ),
            )
            return {"marker": marker, "sid": None, "last_turn": None, "last_operation": None}

    def replace_missing(self, marker, first_operation):
        new_marker = uuid4().hex
        with self.store.connection(write=True) as db:
            db.execute(
                """UPDATE text_provider_sessions SET marker=?,sid=NULL,last_turn=NULL,
                       last_operation=NULL,first_operation=? WHERE marker=? AND state='active'""",
                (new_marker, first_operation, marker),
            )
        return {"marker": new_marker, "sid": None, "last_turn": None, "last_operation": None}

    def identified(self, marker, sid):
        with self.store.connection(write=True) as db:
            db.execute("UPDATE text_provider_sessions SET sid=? WHERE marker=?", (sid, marker))

    def finish(self, marker, turn, key, keep):
        with self.store.connection(write=True) as db:
            db.execute(
                """UPDATE text_provider_sessions SET state=?,last_turn=?,last_operation=?,expires=?
                       WHERE marker=?""",
                (
                    "idle" if keep else "closing",
                    turn,
                    key,
                    iso(self.store.clock() + timedelta(minutes=30)),
                    marker,
                ),
            )

    def retire_idle(self):
        with self.store.connection(write=True) as db:
            db.execute(
                "UPDATE text_provider_sessions SET state='closing' WHERE state='idle' AND instance=?",
                (self.instance,),
            )

    def forget(self, marker):
        with self.store.connection(write=True) as db:
            db.execute("DELETE FROM text_provider_sessions WHERE marker=?", (marker,))

    def has_resources(self, destination):
        with self.store.connection() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM text_provider_sessions WHERE destination=? LIMIT 1",
                    (destination,),
                ).fetchone()
            )

    def due(self, destination, live_chats, authority):
        now = iso(self.store.clock())
        with self.store.connection(write=True) as db:
            rows = db.execute(
                """SELECT * FROM text_provider_sessions WHERE destination=?
                AND retry_after<=? ORDER BY retry_after,expires""",
                (destination, now),
            ).fetchall()
            for row in rows:
                expired = row["expires"] <= now or row["state"] == "closing"
                detached = (
                    row["instance"] == self.instance
                    and row["state"] == "idle"
                    and (row["chat"] not in live_chats or row["authority"] != authority)
                )
                if expired or detached:
                    db.execute(
                        """UPDATE text_provider_sessions SET state='closing',retry_after=?
                               WHERE marker=?""",
                        (iso(self.store.clock() + timedelta(minutes=2)), row["marker"]),
                    )
                    return dict(row)
        return None
