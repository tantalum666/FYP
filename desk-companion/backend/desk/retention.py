"""Local copies of text a hosted model already saw.

Forgetting a fact removes it from later model context. This module also drops
the copies this desk stored and could send again: cached replies and proposal
payloads. It does not call a provider and cannot erase that provider's logs.
"""

import json

from .store import encode


def forget_local_copies(conn, *, memory_id: str, phrases: list[str]) -> dict[str, int]:
    """Delete cached replies and redact proposal text that still contain a forgotten fact.

    A short phrase is removed only when a stored string equals it, so a one-word
    fact does not wipe unrelated replies. A longer phrase is removed wherever it
    appears. Pending proposals that still name the fact are cancelled.
    """
    kept = _phrases(phrases)
    replies = 0
    if _table(conn, "assistant_replies"):
        for row in conn.execute("SELECT id, result FROM assistant_replies"):
            parsed = _json(row["result"])
            if _mentions(parsed, memory_id, kept):
                conn.execute("DELETE FROM assistant_replies WHERE id=?", (row["id"],))
                replies += 1
    proposals = 0
    if _table(conn, "assistant_proposals"):
        for row in conn.execute("SELECT id, state, data, result FROM assistant_proposals"):
            data, result = _json(row["data"]), _json(row["result"]) if row["result"] else None
            if not _mentions(data, memory_id, kept) and not _mentions(result, memory_id, kept):
                continue
            state = "cancelled" if row["state"] == "pending" else row["state"]
            conn.execute(
                "UPDATE assistant_proposals SET state=?, data=?, result=? WHERE id=?",
                (
                    state,
                    encode(_redact(data, kept)),
                    encode(_redact(result, kept)) if result is not None else None,
                    row["id"],
                ),
            )
            proposals += 1
    return {"replies_removed": replies, "proposals_cleared": proposals}


def _phrases(phrases: list[str]) -> list[str]:
    unique: list[str] = []
    for phrase in phrases:
        text = " ".join(str(phrase).split())
        if text and text not in unique:
            unique.append(text)
    return unique


def _mentions(value, memory_id: str, phrases: list[str]) -> bool:
    if isinstance(value, str):
        if memory_id and memory_id in value:
            return True
        for phrase in phrases:
            if value.strip() == phrase or (len(phrase) >= 8 and phrase in value):
                return True
        return False
    if isinstance(value, dict):
        return any(_mentions(item, memory_id, phrases) for item in value.values())
    if isinstance(value, list):
        return any(_mentions(item, memory_id, phrases) for item in value)
    return False


def _redact(value, phrases: list[str]):
    if isinstance(value, str):
        updated = value
        for phrase in phrases:
            updated = updated.replace(phrase, "")
        return " ".join(updated.split())
    if isinstance(value, dict):
        return {key: _redact(item, phrases) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, phrases) for item in value]
    return value


def _json(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _table(conn, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )
