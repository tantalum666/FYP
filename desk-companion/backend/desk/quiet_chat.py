"""Read and acknowledge quiet-hour notices in the owner's ordinary conversation."""

import json
import unicodedata
from collections import Counter
from pathlib import Path

from .commerce_review import language_for
from .conversation import Conversations
from .quiet_changes import OUTCOMES, unread
from .store import DomainError, encode


_PHRASES = json.loads((Path(__file__).parent / "data/quiet-chat-phrases.json").read_text("utf-8"))
_PAGE = 3


def intent(payload):
    text = " ".join(unicodedata.normalize("NFKC", payload.message).lower().split())
    text = text.rstrip(".!?。").strip()
    action = next((key for key, phrases in _PHRASES.items() if text in phrases), None)
    if payload.catch_up_ref and action != "ack":
        raise DomainError("CATCH_UP_ACK_REQUIRED", 422)
    return action


def _open_chat(runtime, db, principal, payload, revision, receipt):
    chat_id = payload.conversation_id
    task = payload.task_id
    login = Conversations.owner(principal)
    chats = runtime.voice.conversations
    if receipt is not None:
        scope = receipt.get("quiet_scope") or {}
        if (
            not scope.get("chat")
            or scope.get("login") != login
            or scope.get("task") != task
            or chat_id not in (None, scope["chat"])
        ):
            raise DomainError("CONVERSATION_NOT_FOUND", 404)
        return chats.open(principal, revision, scope["chat"], task_id=task, recover_review=True)
    try:
        return chats.open(principal, revision, chat_id, task_id=task)
    except DomainError as error:
        if error.code != "CONVERSATION_NOT_FOUND":
            raise
        # A restart loses RAM chat. Recover only from evidence of this login and task.
        has_receipt = db.execute(
            """SELECT 1 FROM assistant_replies WHERE json_extract(result,'$.quiet_scope.chat')=?
               AND json_extract(result,'$.quiet_scope.login')=?
               AND json_extract(result,'$.quiet_scope.task') IS ? LIMIT 1""",
            (chat_id, login, task),
        ).fetchone()
        if not has_receipt and not any(
            service.has_chat(db, login, chat_id, task)
            for service in (runtime.shop_orders, runtime.flight_bookings)
        ):
            raise
        return chats.open(principal, revision, chat_id, task_id=task, recover_review=True)


def forget(db, principal, chat_id):
    # Retain a content-free idempotency marker so a late retry cannot reopen the chat.
    db.execute(
        """UPDATE assistant_replies SET result='{}'
           WHERE json_extract(result,'$.quiet_scope.chat')=?
           AND json_extract(result,'$.quiet_scope.login')=?""",
        (chat_id, Conversations.owner(principal)),
    )


def _summary(rows, zh):
    phrases = []
    for code, count in Counter(row["change"] for row in rows).items():
        sentence = OUTCOMES[code][zh]
        if count > 1:
            sentence = f"{count} × {sentence}"
        phrases.append(sentence)
    return ("" if zh else " ").join(phrases)


def _read(db, chat, receipt, ref, zh):
    current = unread(db, chat, limit=_PAGE + 1)
    shown = (
        unread(db, chat, notice_ids=receipt["shown"], limit=_PAGE)
        if "shown" in receipt
        else current[:_PAGE]
    )
    # On a retry, keep the action bound to the original page, even if newer items arrived.
    more = len(current) > len(shown)
    if shown:
        message = _summary(shown, zh)
        if more:
            message += "还有其他未读进展。" if zh else " More updates are unread."
        receipt["shown"] = [row["id"] for row in shown]
        return {"message": message, "catch_up_ref": ref}
    receipt["shown"] = []
    if more:
        message = "这批进展已处理，可以再问一次查看其他进展。" if zh else (
            "This catch-up has no unread items left. Ask again for the other updates."
        )
    else:
        message = "静音期间没有新的未读进展。" if zh else "There are no unread updates from quiet hours."
    return {"message": message}


def _snapshot(db, ref):
    row = db.execute("SELECT result FROM assistant_replies WHERE id=?", ("chat/" + ref,)).fetchone()
    snapshot = json.loads(row["result"]) if row else {}
    if snapshot.get("intent") != "read":
        raise DomainError("CONVERSATION_NOT_FOUND", 404)
    return snapshot


def _ack(db, chat, receipt, snapshot, ref, zh):
    if "count" not in receipt:
        rows = unread(db, chat, notice_ids=snapshot["shown"], limit=_PAGE) if snapshot else []
        db.executemany(
            "UPDATE notice_inbox SET state='dismissed' WHERE id=? AND state='open'",
            [(row["id"],) for row in rows],
        )
        receipt["count"] = len(rows)
    count = receipt["count"]
    if count:
        message = f"已将 {count} 条进展标为已读。" if zh else (
            f"Marked {count} update{'s' if count != 1 else ''} as read."
        )
    elif ref:
        message = "这批进展已没有未读项。" if zh else "None of those updates are still unread."
    else:
        message = "请先查看进展，再选择标为已读。" if zh else (
            "Open a catch-up first, then mark its updates as read."
        )
    return {"message": message, "acknowledged": count, "saved": bool(count)}


def turn(runtime, db, payload, principal, revision, action, cached, key, fingerprint):
    """Called under the same write transaction as the owner check and receipt lookup."""
    ref = payload.catch_up_ref
    snapshot = _snapshot(db, ref) if ref and cached is None else None
    chat = _open_chat(runtime, db, principal, payload, revision, cached if cached is not None else snapshot)
    scope = {"login": chat.owner, "chat": chat.id, "task": chat.task_id}
    receipt = cached if cached is not None else {"quiet_scope": scope, "intent": action}
    zh = language_for(payload.message, payload.language) == "zh"
    if action == "read":
        result = _read(db, chat, receipt, key.removeprefix("chat/"), zh)
    else:
        result = _ack(db, chat, receipt, snapshot, ref, zh)
    if cached is None:
        db.execute("INSERT INTO assistant_replies VALUES(?,?,?)", (key, fingerprint, encode(receipt)))
    return {
        "mode": "local_rules", "kind": "quiet_catch_up", "conversation_id": chat.id,
        "saved": False, **result,
    }
