"""Budgeted views of the existing session/task-scoped RAM conversation.

No global transcript table. Unauthenticated/internal callers are stateless;
only the server may resolve a Conversation from an authenticated session.
"""

from .calendar import iso

MAX_BODY = 500


def remember_exchange(runtime, operation_id, user_text, assistant_text, *, conversation=None):
    if conversation is None or not operation_id:
        return
    if any(item.get("operation_id") == operation_id for item in conversation.items):
        return
    for role, text in (("user", user_text), ("assistant", assistant_text)):
        conversation.append(
            role, text, created_at=iso(runtime.store.clock()), operation_id=operation_id
        )


def recent_turns(runtime, *, conversation=None, limit=16):
    if conversation is None:
        return []
    return [
        {
            "role": item["role"],
            "body": item["text"][:MAX_BODY],
            "created_at": item.get("created_at", ""),
        }
        for item in reversed(conversation.items[-max(1, min(limit, 40)) :])
    ]
