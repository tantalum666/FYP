"""Owner-initiated order follow-up in the ordinary composer and its existing cards."""

import re
import unicodedata

from .commerce_review import ReviewDecision, ReviewRef, language_for
from .flight_booking.conversation import describe as flight_message
from .shop_checkout.conversation import describe as shop_message


# Only a direct owner command can contact a merchant. Questions and quoted
# instructions stay outside the cancellation route.
_COMMANDS = (
    (
        "shop",
        "follow",
        r"(?:退款(?:到(?:账|賬|帐|了)|有结果)(?:了)?(?:再|就)?(?:告诉我|提醒我)|有退款结果(?:再|就)?(?:告诉我|提醒我)|(?:盯|跟进)一下(?:这笔)?退款|let me know when (?:my |the )?refund (?:arrives|comes through))",
    ),
    (
        "flight",
        "follow",
        r"(?:有(?:订票|出票|航班)结果(?:再|就)?(?:告诉我|提醒我)|票价变了(?:再|就)?(?:告诉我|提醒我)|let me know when (?:my |the )?(?:flight|booking) (?:changes|is confirmed))",
    ),
    (
        "either",
        "follow",
        r"(?:有结果(?:再|就)?告诉我|let me know (?:when there is an update|when it is done))",
    ),
    (
        "either",
        "cancel",
        r"(?:取消(?:这笔|这个|这张|刚才的|我的)?订单(?:[，, ]*(?:并|然后|并申请)?(?:全额)?退款)?|cancel (?:this|my|the) order(?: and (?:request a )?(?:full )?refund)?)",
    ),
    (
        "shop",
        "eligibility",
        r"(?:这(?:笔|个)(?:购物)?订单(?:还)?(?:可以|能)取消吗|can i cancel (?:this|my) shopping order)",
    ),
    (
        "flight",
        "eligibility",
        r"(?:这(?:张|笔)(?:机票|航班订单)(?:还)?(?:可以|能)(?:取消|退票|退)吗|can i cancel (?:this|my) flight)",
    ),
    (
        "shop",
        "cancel",
        r"(?:取消(?:这笔|这个|这张|我的|刚才的)?(?:已付款的?)?(?:测试)?购物订单(?:[，, ]*(?:并|然后|并申请)?(?:全额)?退款)?|cancel (?:this |my |the )?(?:paid )?(?:test )?(?:shop|shopping) order(?: and (?:request a |get a )?(?:full )?refund)?)",
    ),
    (
        "shop",
        "read",
        r"(?:(?:查回|查询|查看|查一下|核对)(?:这笔|我的)?(?:购物订单|购物)(?:的)?(?:退款(?:金额|结果|状态)?|取消结果)|(?:show|check) (?:my |the )?(?:shop|shopping) refund(?: status)?)",
    ),
    (
        "flight",
        "cancel",
        r"(?:停止(?:这笔|这次)?(?:测试)?订票|取消(?:这张|这笔|我的|这次)?(?:测试)?(?:航班订单|机票订单|机票)|(?:stop|cancel) (?:this |my |the )?(?:test )?(?:flight booking|flight order|flight))",
    ),
    (
        "flight",
        "read",
        r"(?:(?:查回|查询|查看|查一下|核对)(?:这张|这笔|我的)?(?:机票|航班订单)(?:的)?(?:取消结果|取消状态|扣款结果|预授权状态)|(?:check|show) (?:my |the )?flight (?:cancellation|hold)(?: status)?)",
    ),
)


def _named_receipt(text):
    """Use a public order number or flight number; provider lookup IDs stay private."""
    shop = re.fullmatch(
        r"(?:查回|查看|查询)购物订单\s*#?(\d{1,12})\s*的?退款(?:结果|状态|金额)|(?:check|show) (?:shopping|shop) order #?(\d{1,12}) refund",
        text.rstrip("?？"),
    )
    if shop:
        return "shop", int(shop[1] or shop[2])
    flight = re.fullmatch(
        r"(?:查回|查看|查询)航班\s*([a-z0-9]{2}\d{1,4}[a-z]?)\s*的?取消(?:结果|状态)|(?:check|show) flight ([a-z0-9]{2}\d{1,4}[a-z]?) cancellation",
        text.rstrip("?？"),
    )
    if flight:
        return "flight", (flight[1] or flight[2]).upper()
    return None


def _matches_target(row, kind, target):
    if kind == "shop":
        return (row.get("receipt") or {}).get("order") == target
    return any(leg["flight"] == target for leg in row["segments"])


def turn(runtime, payload, principal, chat):
    if (
        not chat
        or not principal
        or principal.get("kind") != "owner"
        or payload.attachment_ids
        or chat.attachment_ids
    ):
        return None
    text = (
        unicodedata.normalize("NFKC", payload.message).strip().casefold().rstrip("。.!！").strip()
    )
    text = re.sub(
        r"^(?:(?:我改主意了|不用了)[,， ]*)?(?:请帮我|帮我|请你|请|please )?", "", text, count=1
    )
    match = next(
        (
            (kind, action)
            for kind, action, pattern in _COMMANDS
            if re.fullmatch(pattern, text if action == "cancel" else text.rstrip("?？"))
        ),
        None,
    )
    named = _named_receipt(text)
    if named:
        match = (named[0], "read")
    if not match or not runtime.personal_context.visible(principal):
        return None
    kind, action = match
    lang = language_for(payload.message, payload.language)
    choose_order = {
        "mode": "local",
        "kind": "clarify",
        "saved": False,
        "message": (
            "请在原订单的对话中选择对应的购物或航班订单。"
            if lang == "zh"
            else "Choose the matching shop order or flight booking in its original conversation."
        ),
    }
    if payload.shopping_review and payload.flight_review:
        return choose_order
    if kind == "either":
        matches = [
            (name, row)
            for name, service in (
                ("shop", runtime.shop_orders),
                ("flight", runtime.flight_bookings),
            )
            if service.enabled
            for row in service.listing(principal, chat.id)
            if action != "follow" or row["state"] in service.follow_states
        ]
        # A bare order request never picks one of several orders, even when the
        # composer incidentally attached its only outstanding price review.
        if len(matches) != 1:
            return choose_order
        kind = matches[0][0]
    shop = kind == "shop"
    service = runtime.shop_orders if shop else runtime.flight_bookings
    if not service.enabled:
        return None
    ref = payload.shopping_review if shop else payload.flight_review
    other = payload.flight_review if shop else payload.shopping_review
    owner = service.owner(principal)
    # Typing selects the sole visible price review in the composer. That price
    # shortcut cannot authorize post-payment action on one of several orders.
    card_selected = getattr(payload, "selected_commerce_card", False)
    if other and card_selected:
        return choose_order
    if ref:
        service.read(ref.id, owner, chat.id)
    if named or not (card_selected and ref):
        rows = service.listing(principal, chat.id)
        if named:
            rows = [row for row in rows if _matches_target(row, kind, named[1])]
        elif action == "follow" and len(rows) > 1:
            rows = [row for row in rows if row["state"] in service.follow_states]
        if len(rows) != 1:
            return choose_order
        only = rows[0]
        if not ref or ref.id != only["id"]:
            ref = ReviewRef(
                id=only["id"], version=only["version"], amount_minor=only["review_minor"]
            )
    current = service.read(ref.id, owner, chat.id)
    if action == "follow":
        result = "shopping_order" if shop else "flight_booking"
        if current["state"] not in service.follow_states or current["state"] == "reprice":
            return {
                "mode": "local",
                "kind": result,
                result: current,
                "message": (shop_message if shop else flight_message)(current, lang),
                "saved": False,
            }
        off = runtime.data.preferences()["proactivity"] == "off"
        message = (
            (
                "后台跟进已关闭，可打开原订单查进度。"
                if lang == "zh"
                else "Background follow-up is off. You can check the original order."
            )
            if off
            else (
                "有结果我会在这段对话里告诉你。"
                if lang == "zh"
                else "I’ll let you know here when there’s an update."
            )
        )
        return {
            "mode": "local",
            "kind": result,
            result: current,
            "message": message,
            "commerce_note": True,
            "saved": False,
        }
    if action == "eligibility":
        row = service.reopen(ref.id, principal, chat.id)
        if shop and row["state"] == "completed":
            available = (row["receipt"] or {}).get("can_cancel") is True
            answer = (
                (
                    "商户仍接受发货前撤单，可退回本单全部模拟扣款。"
                    if available
                    else "商户未提供这笔订单的发货前撤单。"
                )
                if lang == "zh"
                else (
                    "The merchant still offers a full pre-dispatch cancellation."
                    if available
                    else "Pre-dispatch cancellation is unavailable on this order."
                )
            )
        elif not shop and row["state"] == "completed":
            answer = (
                "供应商已购票，退票需要卖家票规，目前没有核实可退金额。"
                if lang == "zh"
                else "The supplier bought this ticket. A refund requires seller fare rules. No refundable amount has been verified."
            )
        else:
            answer = (shop_message if shop else flight_message)(row, lang)
        return {
            "mode": "local",
            "kind": "shopping_order" if shop else "flight_booking",
            "shopping_order" if shop else "flight_booking": row,
            "message": answer,
            "commerce_note": True,
            "saved": False,
        }
    if action == "read":
        row = service.reopen(ref.id, principal, chat.id)
    elif current["state"] == "quoted" or (shop and current["state"] == "reprice"):
        row = service.decide(
            ReviewDecision(**ref.model_dump(), action="decline"), principal, chat.id
        )
    elif (
        shop
        and current["state"]
        in {"completed", "refunded", "refund_pending", "refund_retry", "refund_review"}
    ) or (
        not shop
        and current["state"]
        in {
            "processing",
            "reprice",
            "answering",
            "stopping",
            "manual",
            "completed",
            "failed",
            "stopped",
        }
    ):
        row = service.cancel(ref, principal, chat.id)
    else:
        row = current
    result = "shopping_order" if shop else "flight_booking"
    return {
        "mode": "local",
        "kind": result,
        result: row,
        "message": (shop_message if shop else flight_message)(row, lang),
        "saved": action == "cancel",
    }
