"""Language-facing entry to the original Kiwi result. No conversational payment tool."""

import json
from pathlib import Path

from ..commerce_review import language_for
from .checkout_source import purchase_intent


_FRESH_QUOTE = json.loads(
    (Path(__file__).parents[1] / "data" / "fresh-flight-quote.json").read_text(encoding="utf-8")
)


def describe(view, zh):
    source = view.get("source") or {}
    request = source.get("request") or {}
    route = f"{request.get('origin', '')} → {request.get('destination', '')}"
    dates = " / ".join(v for v in (request.get("departure"), request.get("return_date")) if v)
    state = view["state"]
    if market := view.get("market"):
        airports = " / ".join(market["destination"])
        if state == "source":
            if not view.get("connected"):
                return "行程已保留，连接 LetsFG 后即可查实时票价。" if zh else "Your itinerary is ready. Connect LetsFG to check live fares."
            return "可以按原行程重新查实时票价。" if zh else "I can search again with the same itinerary."
        if state == "searching":
            return f"正在查飞往 {airports} 的航班。" if zh else f"I’m checking flights to {airports}."
        if state == "market_empty":
            return "这次没有查到可核实的航班。可以原条件重试，或换个日期。" if zh else "I couldn’t verify a fare for this search. Retry it or change the dates."
        if state == "offers":
            return "这是查到的航班。选一班后我会重新核价。" if zh else "Here are the flights I found. Select one and I’ll recheck its fare."
    if state == "choose_source":
        return (
            "选一下你刚才看到的 Kiwi 报价，我会按原行程核价。"
            if zh
            else "Choose the original Kiwi quote so I can recheck that itinerary."
        )
    if state in {"no_source", "source_unavailable", "source_changed"}:
        return _FRESH_QUOTE["zh" if zh else "en"]
    if state == "waiting_source":
        return (
            "原航班查询还在进行，结果回来后我会更新这张卡。"
            if zh
            else "The original search is still running. I’ll update this card when its fare arrives."
        )
    if state == "source":
        if view.get("reason") in {
            "offer_expired_or_changed",
            "offer_changed",
            "price_changed",
            "offer_expired",
        }:
            return (
                "卖方报价已变化，请重新核价后再确认。"
                if zh
                else "The seller’s offer changed. Recheck its current terms before confirming."
            )
        if view.get("connected"):
            return (
                f"已找回 {route}（{dates}）的 Kiwi 报价。可以核对 LetsFG 的同程总价。"
                if zh
                else f"I found the original Kiwi quote for {route} on {dates}. You can check the same itinerary with LetsFG."
            )
        return (
            f"已找回 {route}（{dates}）的 Kiwi 报价。连接 LetsFG 后，我可以核对同一行程的可订总价。"
            if zh
            else f"I found the original Kiwi quote for {route} on {dates}. Connect LetsFG so I can check its bookable total for the same trip."
        )
    if state == "searching":
        return (
            "正在核对同一行程、乘客和行李。"
            if zh
            else "I’m checking the same itinerary, passengers and baggage."
        )
    if state == "offers":
        return (
            "这是 LetsFG 的新报价。选中一项后，我会再核对实际总价和行李。"
            if zh
            else "These are new LetsFG offers. Select one and I’ll recheck its total and baggage."
        )
    if state == "review":
        return (
            (
                "条款有变化，请核对新的总价和行李，再确认。"
                if view.get("reason") in {"terms_changed", "review_expired"}
                else "已核对行程和含行李总价。请查看购票确认。"
            )
            if zh
            else (
                "The terms changed. Review the new total and baggage before confirming."
                if view.get("reason") in {"terms_changed", "review_expired"}
                else "I’ve checked the itinerary and total including baggage. Your purchase review is ready."
            )
        )
    if state == "seller_verification":
        return (
            "我正在只读查看这张卖方报价的全程行李和含费总价，完成后会重新核价。"
            if zh
            else "I’m checking the baggage and all-in price on this exact seller listing, then I’ll reprice the original offer."
        )
    if state == "seller_only":
        return (
            "LetsFG 暂未核实原班次和所需行李的总价。我可以查看这张卖方报价的具体条款，再核对原选项。"
            if zh
            else "LetsFG has not verified the original flights and baggage at a payable total. I can inspect the exact seller listing and recheck the offer."
        )
    receipts = {
        "completed": (
            "卖方已核实订座编号和实扣金额。",
            "The seller confirmed the booking reference and captured total.",
        ),
        "bank_approval": (
            "请在银行页面完成验证，然后查回这笔订单。",
            "Complete the bank’s verification, then check this same booking.",
        ),
        "card_required": (
            "卖方需要有效的钱包付款方式。更新后可以重新核价。",
            "The seller requires a payment method. Update the wallet, then recheck the fare.",
        ),
        "missing_details": (
            "卖方需要补充乘客资料，请查看安全表格。",
            "The seller requires additional passenger details. Check the private form.",
        ),
        "failed": (
            "卖方报告购票失败，请核对付款结果。",
            "The supplier reported a failed booking. Check the payment result.",
        ),
        "held": (
            "付款已预授权，仍在等待订座和实际扣款回执。",
            "The payment is on hold. I’m waiting for the reservation and capture.",
        ),
        "needs_attention": (
            "卖方还需要处理原订单，请查看最新进展。",
            "The original booking needs supplier attention. Check its latest status.",
        ),
    }
    return receipts.get(
        state, ("正在核对原订单回执，请勿重复下单。", "I’m checking the original booking receipt.")
    )[0 if zh else 1]


def reply(view, chat, message, language):
    return {
        "kind": "live_flight_checkout",
        "mode": "local",
        "saved": False,
        "conversation_id": chat.id,
        "message": describe(view, language_for(message, language) == "zh"),
        "live_flight_checkout": view,
    }


def receipt(reply, chat):
    if reply.get("kind") != "live_flight_checkout" or not chat:
        return reply
    return {
        "kind": "live_flight_checkout",
        "live_id": reply["live_flight_checkout"].get("id"),
        "live_scope": {"chat": chat.id, "login": chat.owner, "task": chat.task_id},
        "saved": False,
    }


def replay_scope(runtime, cached, principal, payload):
    if not cached or cached.get("kind") != "live_flight_checkout":
        return None
    from ..conversation import Conversations
    from ..store import DomainError

    scope = cached.get("live_scope") or {}
    if (
        not scope.get("chat")
        or scope.get("login") != Conversations.owner(principal)
        or payload.conversation_id not in (None, scope["chat"])
        or scope.get("task") != payload.task_id
    ):
        raise DomainError("CONVERSATION_NOT_FOUND", 404)
    runtime.personal_context.require_visible(principal)
    return scope["chat"]


def turn(runtime, payload, principal, chat):
    from .shortlist import plain_offer_selection

    if not chat or not principal or principal.get("kind") != "owner":
        return None
    if payload.selected_commerce_card or payload.attachment_ids or payload.flight_review or payload.shopping_review:
        return None
    selector = plain_offer_selection(payload)
    if selector is not None and chat.items and chat.items[-1]["role"] == "assistant":
        with runtime.store.connection() as db:
            saved = db.execute("SELECT result FROM assistant_replies WHERE id=?",
                               (chat.items[-1].get("operation_id"),)).fetchone()
        ref = json.loads(saved[0]) if saved else {}
        if ref.get("live_id") and (ref.get("live_scope") or {}).get("chat") == chat.id:
            service = runtime.live_flight_checkouts
            view = service.view(principal, chat.id, ref["live_id"])
            if view.get("market") and view["state"] in {"offers", "searching"}:
                options = [o for o in view["choices"] if o["number"] == selector or
                           any(leg["flight"] == selector for leg in o["outbound"])]
                if len(options) == 1:
                    view = service.action(principal,chat.id,ref["live_id"],"select",view["version"],options[0]["number"])
                return reply(view,chat,payload.message,payload.language)
    if not purchase_intent(payload.message):
        return None
    return reply(
        runtime.live_flight_checkouts.start(principal, chat),
        chat,
        payload.message,
        payload.language,
    )
