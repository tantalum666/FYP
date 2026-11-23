"""Language-facing entry to the original Kiwi result. No conversational payment tool."""

from ..commerce_review import language_for
from .checkout_source import purchase_intent


def describe(view, zh):
    source = view.get("source") or {}
    request = source.get("request") or {}
    route = f"{request.get('origin', '')} → {request.get('destination', '')}"
    dates = " / ".join(v for v in (request.get("departure"), request.get("return_date")) if v)
    state = view["state"]
    if state == "choose_source":
        return (
            "选一下你刚才看到的 Kiwi 报价，我会按原行程核价。"
            if zh
            else "Choose the original Kiwi quote so I can recheck that itinerary."
        )
    if state == "no_source":
        return (
            "请打开原来那张 Kiwi 航班结果，点「准备购买」，我会接着核价。"
            if zh
            else "Open the original Kiwi result and choose Prepare purchase so I can recheck that flight."
        )
    if state == "waiting_source":
        return (
            "原航班查询还在进行，结果回来后我会更新这张卡。"
            if zh
            else "The original search is still running. I’ll update this card when its fare arrives."
        )
    if state in {"source_unavailable", "source_changed"}:
        return (
            "原报价已失效或无法核对。请重新查看原查询，再选择可用航班。"
            if zh
            else "The original fare is no longer verifiable. Reopen the original search to choose a current flight."
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
    if state == "seller_only":
        return (
            "暂时没有能核实原班次、往返和所需行李总价的 LetsFG 报价。可以打开 Kiwi 的原报价，查看卖方条款。"
            if zh
            else "LetsFG has no verified payable match for the original flights and baggage. Open the original Kiwi offer to check the seller’s terms."
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
    if (
        not purchase_intent(payload.message)
        or not chat
        or not principal
        or principal.get("kind") != "owner"
    ):
        return None
    if payload.selected_commerce_card or payload.attachment_ids:
        return None
    return reply(
        runtime.live_flight_checkouts.start(principal, chat),
        chat,
        payload.message,
        payload.language,
    )
