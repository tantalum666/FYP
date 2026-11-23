"""The owner's on-demand, local view of original commerce and Work reviews."""

import json
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass

from .calendar import iso
from .commerce_review import language_for
from .conversation import Conversations
from .flight_booking.conversation import owner_decision as flight_decision
from .shop_checkout.conversation import owner_decision as shop_decision, price, shop_quote_subject
from .store import DomainError
from .work_limits import RUN_COUNT


DISPLAY_LIMIT = 3
_SOURCE_LIMIT = 12
_SOURCE_TIMEOUT_MS = 250
_ASKS = {"what needs my approval", "现在有什么需要我确认", "有什么需要我确认"}
_ASSENT_SEP = r"[\s,.!;:。、–—-]"
_EN_ACK = r"(?:yes|yeah|yep|ok(?:ay)?|sure)"
_EN_REF = r"(?:it|this|that|(?:both|all)(?:\s+of\s+them)?|them(?:\s+(?:all|both))?)"
_EN_ASSENT = re.compile(
    rf"(?:{_EN_ACK}{_ASSENT_SEP}+(?:and\s+)?)?(?:(?:please|kindly){_ASSENT_SEP}+)?"
    rf"(?:{_EN_ACK}|both|all\s+of\s+them|go\s+ahead|"
    rf"(?:go\s+ahead{_ASSENT_SEP}+(?:and\s+)?)?"
    rf"(?:(?:confirm|approve|accept)(?:\s+{_EN_REF})?|do\s+(?:{_EN_REF}|so)|proceed))"
    rf"(?:{_ASSENT_SEP}+(?:please|thanks|thank\s+you))?{_ASSENT_SEP}*"
)
_ZH_ACK = r"(?:(?:好[的啊呀]?|可以的?|行|同意)[吧了]?|是的?|对的?|嗯|没问题)"
_ZH_ASSENT = re.compile(
    rf"(?:{_ZH_ACK}{_ASSENT_SEP}*)?(?:那?就)?"
    rf"(?:(?:请|麻烦)[你您]?{_ASSENT_SEP}*)?(?:(?:帮我|帮忙){_ASSENT_SEP}*)?"
    rf"(?:全部(?:都)?|全?都|一起)?(?:{_ZH_ACK}|"
    r"(?:确认|确定|批准|接受|同意)(?:一?下)?(?:它们?|[这那]个|全部)?[吧了]?)"
    rf"(?:{_ASSENT_SEP}*谢谢)?{_ASSENT_SEP}*"
)


def is_unbound_assent(wording: str) -> bool:
    """Match a normalized, target-free reply for clarification only."""
    return bool(_EN_ASSENT.fullmatch(wording) or _ZH_ASSENT.fullmatch(wording))


@dataclass(frozen=True)
class _Item:
    title: str
    reason: str
    revised: bool = False
    commerce_ref: tuple | None = None


def asks_approval_status(message):
    return message.strip().rstrip("？?。.!！").strip().casefold() in _ASKS


def clarify_decision(runtime, payload, principal, chat):
    """An inferred composer reference does not choose between several owner decisions."""
    ref = payload.shopping_review or payload.flight_review
    if not chat or (payload.selected_commerce_card and ref):
        return None
    decision = shop_decision(payload.message) or flight_decision(payload.message)
    wording = unicodedata.normalize("NFKC", payload.message).strip().casefold()
    if not decision and not is_unbound_assent(wording):
        return None
    if ref and wording.rstrip(".!。") in {
        "恢复原购物订单", "recover shop order", "恢复原测试单", "recover this test booking"
    }:
        return None
    previous = next((i["text"] for i in reversed(chat.items) if i["role"] == "user"), "")
    amount = decision[1] if decision else None
    zh = language_for(payload.message, payload.language) == "zh"
    if not asks_approval_status(previous) or (ref and amount is not None):
        if not runtime.personal_context.visible(principal):
            return None
        items, complete = _pending(runtime, principal, chat, zh)
        if complete:
            if not items:
                return None
            if ref:
                kind = "SHOP" if payload.shopping_review else "FLIGHT"
                # Amount-bearing replies still need an unambiguous original quote.
                if amount is not None:
                    items = [i for i in items if i.commerce_ref and i.commerce_ref[0] == kind
                             and i.commerce_ref[2] == amount]
                    if not items:
                        return None  # The original card reports changed terms.
                if len(items) == 1 and items[0].commerce_ref == (kind, ref.id, ref.amount_minor):
                    return None
    return {
        "mode": "local_rules", "kind": "clarify", "saved": False, "acted": False,
        "message": ("请在对应的报价、草稿或「工作」中选择要处理的一项。"
                    if zh else "Choose the specific quote, draft or step in Work to review."),
    }


def _short(value):
    return " ".join((value or "").split())[:80]


def _commerce(service, db, chat, now, zh):
    rows, limited = service.pending_reviews(db, chat, now, _SOURCE_LIMIT)
    items = []
    for row in rows:
        shop = service.kind == "SHOP"
        if shop:
            quote = row["quote"]
            title = _short(shop_quote_subject(quote, zh))
            previous = (row["previous"] or {}).get("terms", {}).get("total_minor")
        else:
            title = " / ".join(leg["flight"] for leg in row["segments"])
            previous = row["previous_minor"]
        total = price(row["review_minor"])
        revised = row["state"] == "reprice"
        if shop and revised and previous == row["review_minor"]:
            reason = (
                f"结算内容有变化，总价仍为 {total}，请重新核对"
                if zh else f"review the changed checkout terms at the same {total} total"
            )
        elif revised and previous is not None:
            amounts = f"{price(previous)} → {total}"
            reason = f"请核对新总价 {amounts}" if zh else f"review the revised total {amounts}"
        elif shop:
            reason = f"付款前请核对总价 {total}" if zh else f"review the {total} total before payment"
        else:
            reason = f"订票前请核对总价 {total}" if zh else f"review the {total} fare before booking"
        items.append(_Item(title, reason, revised, (service.kind, row["id"], row["review_minor"])))
    return items, limited


def _draft(proposal, zh, goal=None):
    data = proposal["data"]
    title = next((
        value["title"] for name in ("task", "original_task", "event", "original", "browser")
        if isinstance(value := data.get(name), dict) and value.get("title")
    ), None)
    title = _short(title or data.get("subject") or data.get("title") or goal)
    if not title:
        kind = proposal["kind"]
        if kind.startswith("memory_"):
            title = "记忆草稿" if zh else "Memory draft"
        elif kind == "output":
            title = "设备预设" if zh else "Device preset"
        else:
            title = "待核对草稿" if zh else "Pending draft"
    return _Item(title, "请核对原草稿" if zh else "review the original draft")


def _child_in_review(db, effect, now):
    # A parent may still say waiting_review after the child was approved or cancelled.
    result = effect.get("result") or {}
    if ident := result.get("application_job_id"):
        query = "SELECT state,expires_at FROM computer_jobs WHERE id=?"
    elif ident := result.get("browser_job_id"):
        query = "SELECT state,expires_at FROM browser_effects WHERE id=?"
    elif ident := result.get("connector_intent_id"):
        query = "SELECT data->>'$.state',data->>'$.expires_at' FROM connector_intents WHERE id=?"
    else:
        return False
    row = db.execute(query, (ident,)).fetchone()
    return row is not None and row[0] == "review" and row[1] is not None and row[1] > now


def _work(runtime, db, chat, now, zh):
    # The same bounded, unexpired, uncommitted drafts as the original proposal cards.
    proposals = {p["id"]: p for p in runtime.assistant.pending_proposals(db)}
    items = []
    for row in db.execute(
        """SELECT id,state,session_hash,data->'$.proposal_ids' AS proposals,
                  (SELECT response->>'$.proposal.id' FROM operations
                   WHERE id=agent_runs.data->>'$.pending_effect.key') AS unlinked
           FROM agent_runs
           ORDER BY updated_at DESC,id LIMIT ?""", (RUN_COUNT,)
    ):
        linked = {pid: proposals.pop(pid) for pid in json.loads(row["proposals"] or "[]")
                  if pid in proposals}
        # A crash can leave an original draft receipt just before Work links the effect.
        proposals.pop(row["unlinked"], None)
        if row["session_hash"] != chat.owner or row["state"] not in {"waiting_input", "waiting_review"}:
            continue
        service = runtime.agent_runs
        run = service._get(db, row["id"])
        if chat.task_id and chat.task_id not in run["task_ids"]:
            continue
        try:
            service.publication_checkpoint(run, db)
        except DomainError as error:
            if error.status not in {403, 409}:
                raise
            continue
        goal = _short(run["goal"])
        if row["state"] == "waiting_input" and run.get("question"):
            question = _short(run["question"])
            reason = f"请在「工作」中回答：{question}" if zh else f"answer in Work: {question}"
            items.append(_Item(goal, reason))
        elif row["state"] == "waiting_review":
            for effect in run["effects"]:
                if effect["state"] != "pending":
                    continue
                if proposal := linked.get(effect.get("proposal_id")):
                    items.append(_draft(proposal, zh, goal))
                elif _child_in_review(db, effect, iso(now)):
                    reason = "请在「工作」中核对此步骤" if zh else "review this step in Work"
                    items.append(_Item(goal, reason))
    for proposal in proposals.values():
        items.append(_draft(proposal, zh))
    return items, False


def _pending(runtime, principal, chat, zh):
    now = runtime.store.clock()
    items = []
    complete = True
    with runtime.store.connection() as db:
        db.execute(f"PRAGMA busy_timeout={_SOURCE_TIMEOUT_MS}")
        runtime.personal_context.require_owner_transaction(db, principal)
        for read, source in (
            (_commerce, runtime.flight_bookings), (_commerce, runtime.shop_orders), (_work, runtime)
        ):
            deadline = time.monotonic() + _SOURCE_TIMEOUT_MS / 1000
            db.set_progress_handler(lambda: time.monotonic() >= deadline, 1000)
            try:
                found, limited = read(source, db, chat, now, zh)
                items.extend(found)
                complete = complete and not limited
            except TimeoutError:
                complete = False
            except sqlite3.OperationalError as error:
                if getattr(error, "sqlite_errorcode", 0) & 255 not in {
                    sqlite3.SQLITE_INTERRUPT, sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED
                }:
                    raise
                complete = False
            finally:
                db.set_progress_handler(None, 0)
    # Recheck visibility after reading the snapshot, including on a replay of the same ask.
    with runtime.store.connection() as db:
        runtime.personal_context.require_owner_transaction(db, principal)
    return items, complete


def answer(runtime, payload, principal, chat):
    zh = language_for(payload.message, payload.language) == "zh"
    base = {"mode": "local_rules", "kind": "approval_status", "saved": False, "acted": False}
    if not chat or chat.owner != Conversations.owner(principal) or not runtime.personal_context.visible(principal):
        message = "请在可查看私人内容的本人对话中核对。" if zh else "Open your private conversation to check approvals."
        return {**base, "message": message, "items": [], "total": None, "complete": False}
    items, complete = _pending(runtime, principal, chat, zh)
    count = len(items)
    displayed = [{"title": i.title, "reason": i.reason}
                 for i in sorted(items, key=lambda item: not item.revised)[:DISPLAY_LIMIT]]
    if count:
        number = (("至少" if zh else "At least ") if not complete else "") + str(count)
        headline = (f"{number} 项等你核对。" if zh else
                    f"{number} {'item needs' if count == 1 else 'items need'} your review.")
    elif complete:
        headline = "现在没有需要你确认的事项。" if zh else "Nothing needs your approval right now."
    else:
        headline = "暂时无法核对全部待确认事项。" if zh else "I couldn’t check all pending reviews."
    lines = [headline, *(f"• {item['title']} — {item['reason']}" for item in displayed)]
    if count and not complete:
        lines.append("还有部分记录未核对。" if zh else "Some records weren’t checked.")
    return {**base, "approval_summary": headline, "message": "\n".join(lines),
            "items": displayed, "total": count if complete else None, "complete": complete}


def receipt(chat):
    marker = {"kind": "approval_status"}
    if chat is not None:
        marker["approval_scope"] = {"chat": chat.id, "login": chat.owner, "task": chat.task_id}
    return marker


def cached_chat(cached, principal, payload):
    if not cached or cached.get("kind") != "approval_status":
        return None
    if cached.get("forgotten"):
        raise DomainError("CONVERSATION_NOT_FOUND", 404)
    scope = cached.get("approval_scope")
    if scope is None:
        return None  # Earlier receipts retained only the operation type.
    if (
        not principal
        or scope["login"] != Conversations.owner(principal)
        or scope["task"] != payload.task_id
        or payload.conversation_id not in (None, scope["chat"])
    ):
        raise DomainError("CONVERSATION_NOT_FOUND", 404)
    return scope["chat"]


def can_reopen(runtime, principal, payload):
    with runtime.store.connection() as db:
        runtime.personal_context.require_owner_transaction(db, principal)
        return db.execute(
            """SELECT 1 FROM assistant_replies WHERE json_extract(result,'$.approval_scope.chat')=?
               AND json_extract(result,'$.approval_scope.login')=?
               AND json_extract(result,'$.approval_scope.task') IS ? LIMIT 1""",
            (payload.conversation_id, Conversations.owner(principal), payload.task_id),
        ).fetchone() is not None


def forget(db, principal, chat_id):
    db.execute(
        """UPDATE assistant_replies SET result='{"kind":"approval_status","forgotten":true}'
           WHERE json_extract(result,'$.approval_scope.chat')=?
           AND json_extract(result,'$.approval_scope.login')=?""",
        (chat_id, Conversations.owner(principal)),
    )
