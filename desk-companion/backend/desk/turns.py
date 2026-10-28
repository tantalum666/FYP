"""Recent turns for the owner channel. Paired sessions are not stored.

Text replies and owner voice transcripts share this table. Audio is never
written. The local voice worker counts as the owner's desk. A paired display
does not.
"""

from .calendar import iso


MAX_STORED = 24
MAX_BODY = 500
_ROLES = {"user", "assistant"}


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


def remember_turn(runtime, operation_id: str, role: str, text: str) -> None:
    if not operation_id or role not in _ROLES:
        return
    body = _clip(text)
    if not body:
        return
    now = iso(runtime.store.clock())
    with runtime.store.connection(write=True) as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO assistant_turns(role,body,created_at,operation_id) VALUES(?,?,?,?)",
            (role, body, now, operation_id),
        )
        conn.execute(
            "DELETE FROM assistant_turns WHERE id NOT IN ("
            "SELECT id FROM assistant_turns ORDER BY id DESC LIMIT ?)",
            (MAX_STORED,),
        )


def remember_exchange(runtime, operation_id: str, user_text: str, assistant_text: str) -> None:
    remember_turn(runtime, operation_id, "user", user_text)
    remember_turn(runtime, operation_id, "assistant", assistant_text)


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


class VoiceTranscript:
    """One open voice turn. Deltas concatenate. A final transcript replaces them."""

    def __init__(self, runtime, session_id: str, *, enabled: bool):
        self.runtime = runtime
        self.session_id = session_id
        self.enabled = enabled
        self._parts = {"user": [], "assistant": []}

    def add(self, role: str, text: str, *, final: bool) -> None:
        if not self.enabled or role not in self._parts:
            return
        piece = str(text or "")
        if not piece:
            return
        if final:
            kept = [item for item in self._parts[role] if item[1]]
            self._parts[role] = kept + [(piece, True)]
            return
        self._parts[role].append((piece, False))

    def add_typed(self, text: str) -> None:
        """Text the owner typed into the voice socket. It is already complete."""
        self.add("user", text, final=True)

    def commit(self) -> None:
        if self.enabled:
            for role in ("user", "assistant"):
                body = _render(self._parts[role])
                if body:
                    remember_turn(self.runtime, self.session_id, role, body)
        self._parts = {"user": [], "assistant": []}


def voice_turn_log(runtime, session_id: str, principal: dict) -> VoiceTranscript:
    kind = principal.get("kind") if isinstance(principal, dict) else ""
    return VoiceTranscript(runtime, session_id, enabled=kind in {"owner", "agent"})


def apply_voice_event(log: VoiceTranscript, event: dict) -> None:
    kind = event.get("type")
    if kind == "transcript":
        log.add(
            str(event.get("role") or ""),
            str(event.get("text") or ""),
            final=bool(event.get("final")),
        )
        return
    if kind in {"turn_complete", "interrupted", "cancel_tools"}:
        log.commit()


def _render(parts: list[tuple[str, bool]]) -> str:
    chunks: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        if pending:
            chunks.append("".join(pending))
            pending.clear()

    for text, final in parts:
        if final:
            flush()
            chunks.append(text)
        else:
            pending.append(text)
    flush()
    return "\n".join(piece.strip() for piece in chunks if piece.strip())
