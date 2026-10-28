"""Owner-visible record of each tool call. Arguments are bounded; secrets are not stored."""

import json

from .calendar import iso
from .store import encode


def channel_for(call_key: object) -> str:
    if isinstance(call_key, str) and call_key.startswith("voice/"):
        return "voice"
    if isinstance(call_key, str) and call_key.startswith("text/"):
        return "text"
    return "local"


class ToolAudit:
    def __init__(self, store):
        self.store = store
        with self.store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tool_calls(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    call_key TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    saved INTEGER NOT NULL,
                    ref_kind TEXT,
                    ref_id TEXT,
                    message TEXT NOT NULL DEFAULT ''
                )"""
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tool_calls)")}
            if "message" not in columns:
                conn.execute("ALTER TABLE tool_calls ADD COLUMN message TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tool_effects(
                    call_key TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    result TEXT NOT NULL
                )"""
            )

    def record(
        self,
        *,
        name,
        arguments,
        call_key,
        outcome,
        result,
        risk="unknown",
        channel=None,
        message="",
    ):
        saved, ref_kind, ref_id = _effect(result)
        with self.store.connection(write=True) as conn:
            conn.execute(
                """INSERT INTO tool_calls(
                    at, channel, call_key, tool, risk, arguments, outcome, saved, ref_kind, ref_id,
                    message
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    iso(self.store.clock()),
                    _clip(channel or channel_for(call_key), 16),
                    _clip(call_key if isinstance(call_key, str) else "", 120),
                    _clip(name if isinstance(name, str) else "", 80),
                    _clip(risk if isinstance(risk, str) else "unknown", 16),
                    _argument_text(arguments),
                    _clip(outcome if isinstance(outcome, str) else "TOOL_FAILED", 80),
                    saved,
                    ref_kind,
                    ref_id,
                    _clip(message if isinstance(message, str) else "", 500),
                ),
            )

    def listing(self, limit: int = 50):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            limit = 50
        limit = min(limit, 100)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tool_calls ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_view(row) for row in rows]


def _argument_text(arguments) -> str:
    if not isinstance(arguments, dict):
        return "{}"
    try:
        raw = encode(arguments)
    except TypeError:
        return encode({"unserializable": True})
    if len(raw) <= 12000:
        return raw
    return encode({"truncated": True, "preview": raw[:4000]})


def _effect(result):
    saved, ref_kind, ref_id = False, None, None
    if not isinstance(result, dict):
        return 0, None, None
    saved = bool(result.get("saved", False))
    proposal, job = result.get("proposal"), result.get("job")
    if isinstance(proposal, dict) and isinstance(proposal.get("id"), str):
        return 0, "proposal", proposal["id"]
    if isinstance(job, dict) and isinstance(job.get("id"), str):
        if job.get("state") == "review":
            saved = False
        return int(saved), "job", job["id"]
    return int(saved), ref_kind, ref_id


def _view(row):
    try:
        arguments = json.loads(row["arguments"])
    except (TypeError, ValueError):
        arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    return {
        "id": row["id"],
        "at": row["at"],
        "channel": row["channel"],
        "call_key": row["call_key"],
        "tool": row["tool"],
        "risk": row["risk"],
        "arguments": arguments,
        "outcome": row["outcome"],
        "saved": bool(row["saved"]),
        "ref_kind": row["ref_kind"],
        "ref_id": row["ref_id"],
        "message": row["message"] or "",
    }


def _clip(value: str, limit: int) -> str:
    return value[:limit]
