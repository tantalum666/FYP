"""Server-sent events for one assistant turn.

Tool progress is a name and a phase. Arguments stay in the owner audit row.
The final message is split into short pieces with no artificial delay.
"""

import json


CHUNK = 24


def text_chunks(text: str, size: int = CHUNK) -> list[str]:
    if not isinstance(text, str) or size < 1 or not text:
        return []
    return [text[index : index + size] for index in range(0, len(text), size)]


def sse_encode(event: dict) -> str:
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return "data: " + payload + "\n\n"


def audit_events(rows: list[dict]) -> list[dict]:
    """Started and finished events for audit rows, oldest first. No arguments."""
    events = []
    for row in rows:
        tool = row.get("tool") if isinstance(row.get("tool"), str) else "tool"
        events.append({"type": "tool", "phase": "started", "tool": tool})
        events.append(
            {
                "type": "tool",
                "phase": "finished",
                "tool": tool,
                "outcome": row.get("outcome") or "ok",
                "saved": bool(row.get("saved")),
            }
        )
    return events
