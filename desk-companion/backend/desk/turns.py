"""Recent text turns for the owner channel. Paired sessions are not stored."""

from .calendar import iso


MAX_STORED = 24
MAX_BODY = 500


def _ensure(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS assistant_turns(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            operation_id TEXT NOT NULL
        )"""
    )


def remember_exchange(runtime, operation_id: str, user_text: str, assistant_text: str) -> None:
    if not operation_id:
        return
    now = iso(runtime.store.clock())
    with runtime.store.connection(write=True) as conn:
        _ensure(conn)
        for role, text in (("user", user_text), ("assistant", assistant_text)):
            conn.execute(
                "INSERT INTO assistant_turns(role,body,created_at,operation_id) VALUES(?,?,?,?)",
                (role, _clip(text), now, operation_id),
            )
        conn.execute(
            "DELETE FROM assistant_turns WHERE id NOT IN ("
            "SELECT id FROM assistant_turns ORDER BY id DESC LIMIT ?)",
            (MAX_STORED,),
        )


def recent_turns(runtime, *, limit: int = 16) -> list[dict]:
    with runtime.store.connection(write=True) as conn:
        _ensure(conn)
        rows = conn.execute(
            "SELECT id, role, body, created_at FROM assistant_turns ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _clip(text: str) -> str:
    body = " ".join(str(text or "").split())
    if len(body) <= MAX_BODY:
        return body
    return body[:MAX_BODY]
