"""Ordinary chat entry and localized, grounded replies for the test shop."""

import re
import unicodedata

from ..commerce_review import ReviewDecision, language_for
from ..store import DomainError
from .provider import ShopQuery
from .terms import ShopReviewRef

TOOL = {
    "name": "sandbox_shop_quote",
    "description": (
        "Prepare one quote for the owner's entire basket from the WooCommerce TEST shop. "
        "Send every requested product name in its original language or exact SKU and selling-unit quantity "
        "in one items array. Include budget_minor and its original currency, each item's required_attributes "
        "(including any requested color, size or other variant), its same-family alternative_search when known, "
        "and only other quantities the owner explicitly allowed in allowed_quantities. "
        "For one unconstrained product you may send product and quantity instead. "
        "Ask if any item or quantity is missing or ambiguous. The shop computes one full HKD cart with Hong Kong delivery. "
        "For price research on a named real merchant use browser_research_draft instead. No real goods or money. "
        "This function cannot place an order, approve a price or charge a card. The owner confirms the displayed exact cart and each change."
    ),
    "parameters": ShopQuery.model_json_schema(),
}


def price(n):
    return f"HK${n // 100:,}.{n % 100:02d}"


def shop_quote_subject(quote, zh: bool) -> str:
    terms = quote["terms"]
    lines = terms.get("items", [])
    if not isinstance(lines, list):
        raise ValueError("quote terms.items must be a list")
    count = len(lines)
    if count > 1:
        return f"{count} 种商品" if zh else f"{count} products"

    if lines and "name" not in quote:
        name = quote["item_names"][str(lines[0]["product_id"])]
    else:
        name = quote["name"]
    quantity = lines[0]["quantity"] if lines and "quantity" not in terms else terms["quantity"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("quote product name must be nonempty")
    if type(quantity) is not int or quantity < 1:
        raise ValueError("quote quantity must be a positive integer")
    return f"{name} × {quantity}"


def describe(row, language):
    q = row["quote"]
    zh = language == "zh"
    if row["state"] == "choosing":
        product = row["unavailable_product"]
        lines = [f"{product} 无法按原要求购买。可重新核价：" if zh else
                 f"{product} is unavailable as requested. Choose an option to recheck:"]
        if row.get("unavailable_reason"):
            lines[0] = "刚选的方案已不可用。其他可选方案：" if zh else "That choice is no longer available. Other options:"
        for option in row["alternatives"]:
            i = option["number"]
            name = f"{option['name']} ({option['sku']}) × {option['quantity']}"
            shipping, total = price(option["shipping_minor"]), price(option["total_minor"])
            lines.append(f"{i}. {name} · 运费 {shipping} · 整单 {total}" if zh else
                         f"{i}. {name} · delivery {shipping} · basket {total}")
        return "\n".join(lines)
    if row["state"] == "items_changed":
        change = row["checkout_change"]
        removed, added = ", ".join(change["removed"]), ", ".join(change["added"])
        delta = " → ".join([removed or ("无" if zh else "none"), added or ("无" if zh else "none")])
        total = price(change["total_minor"])
        same = change["total_minor"] == row["review_minor"]
        if zh:
            return f"商店在付款前拦下了商品变更：{delta}。总价{'仍为' if same else '变为'} {total}。请重新选购。"
        return f"The shop stopped checkout before payment. {delta}. Total {'still' if same else 'now'} {total}. Request a fresh quote."
    if row["state"] == "unavailable" and row.get("unavailable_reason"):
        return failure(row["unavailable_reason"], language)
    if row["state"] == "quoted":
        t = q["terms"]
        subject = shop_quote_subject(q, zh)
        return (
            f"{subject}，商品 {price(t['subtotal_minor'])}，运费 {price(t['shipping_minor'])}，测试订单总价 {price(t['total_minor'])}。确认后我才付款。"
            if zh
            else f"{subject}. Items {price(t['subtotal_minor'])}, delivery {price(t['shipping_minor'])}, order total {price(t['total_minor'])}. Confirm to make the test payment."
        )
    if row["state"] == "reprice":
        t = q["terms"]
        old = row["previous"]["terms"]
        if old["total_minor"] == t["total_minor"]:
            return (
                f"结账明细已变，总价仍为 {price(t['total_minor'])}。请核对新明细后确认付款。"
                if zh
                else f"Checkout details changed. The total is still {price(t['total_minor'])}. Review the new details before paying."
            )
        return (
            f"商店更新了结账报价：原总价 {price(old['total_minor'])}，新总价 {price(t['total_minor'])}，其中运费 {price(t['shipping_minor'])}。还没有付款。按新报价继续吗？"
            if zh
            else f"The shop updated checkout from {price(old['total_minor'])} to {price(t['total_minor'])}, including delivery of {price(t['shipping_minor'])}. No payment yet. Accept the new quote?"
        )
    receipt = row.get("receipt") or {}
    if receipt.get("last_verified"):
        return (
            f"订单 #{receipt['order']} 的最新付款记录待核实。收据保留上次核实的金额。"
            if zh
            else f"The latest payment records for order #{receipt['order']} could not be verified. The receipt retains the last verified amounts."
        )
    if row["state"] == "partially_refunded":
        return (
            f"WooCommerce 订单 #{receipt['order']} 已部分退款。"
            if zh
            else f"WooCommerce order #{receipt['order']} was partially refunded."
        )
    if row["state"] == "refunded":
        label = (
            ("买家撤单已受理" if zh else "Buyer cancellation accepted")
            if receipt.get("buyer_cancel_requested")
            else ("商户已退款" if zh else "Merchant refund verified")
        )
        return (
            f"WooCommerce 订单 #{receipt['order']}，{label}。Stripe 原模拟扣款 {price(receipt['charged_minor'])}，已全额退回 {price(receipt['refunded_minor'])}，净扣款 {price(receipt['net_minor'])}。"
            if zh
            else f"WooCommerce order #{receipt['order']}. {label}. Stripe captured {price(receipt['charged_minor'])}, refunded {price(receipt['refunded_minor'])}, net {price(receipt['net_minor'])}."
        )
    if row["state"] == "completed" and row.get("cancel_unavailable"):
        return (
            f"商户未接受订单 #{receipt['order']} 的发货前撤单。已核实原模拟扣款 {price(receipt['charged_minor'])}。"
            if zh
            else f"The merchant could not accept pre-dispatch cancellation of order #{receipt['order']}. Verified test capture {price(receipt['charged_minor'])}."
        )
    if row["state"] == "completed":
        receipt = row["receipt"]
        return (
            f"已核对 WooCommerce 订单 #{receipt['order']} 和 Stripe 回执：实际模拟扣款 {price(receipt['charged_minor'])}，真实扣款 HK$0。"
            if zh
            else f"WooCommerce order #{receipt['order']} and Stripe match. Captured test payment {price(receipt['charged_minor'])}. Real charge HK$0."
        )
    messages = {
        "refund_pending": (
            "正在核对原付款的退款进度。",
            "Checking the refund on the original payment.",
        ),
        "refund_retry": (
            "商户尚未确认收到撤单请求。可以对原订单再次请求撤单。",
            "The merchant has not recorded the cancellation. Retry on the original order.",
        ),
        "refund_review": (
            "退款需要商户核查，目前没有已完成的全额退款回执。",
            "The refund needs merchant review. A completed full refund has not been verified.",
        ),
        "cancelled": ("已取消，没有付款。", "Cancelled without payment."),
        "unavailable": (
            "商店无法按原清单供货或配送。请重新询价。",
            "The shop can no longer supply or deliver the whole basket. Request a fresh quote.",
        ),
        "expired": ("报价已过期，请重新查询。", "Quote expired. Request a fresh quote."),
        "checking": (
            "正在查回商店订单和 Stripe 的扣款回执。",
            "Checking the Woo order and Stripe capture.",
        ),
        "submitting": ("正在提交已确认的测试购物订单。", "Submitting the approved test order."),
        "retry": (
            "尚无可核实的付款回执，可按原请求编号恢复。",
            "No verified capture yet. Recover the original request.",
        ),
        "unverified": (
            "商店和支付回执尚未匹配，扣款金额待核对。",
            "The store and payment records could not be matched.",
        ),
        "failed": ("测试付款未完成。", "The test payment failed."),
    }
    a, b = messages[row["state"]]
    return a if zh else b


def owner_decision(message):
    text = unicodedata.normalize("NFKC", message).strip().casefold().rstrip("。！.!").strip()
    if text in {
        "确认",
        "确定",
        "同意",
        "确认支付",
        "确认付款",
        "同意新总价",
        "可以",
        "yes",
        "confirm",
        "pay",
        "恢复原购物订单",
        "recover shop order",
    }:
        return "confirm", None
    if text in {
        "取消",
        "取消购物",
        "拒绝",
        "拒绝新价格",
        "拒绝加价",
        "不要付款",
        "cancel",
        "decline",
        "decline new total",
    }:
        return "decline", None
    match = re.fullmatch(
        r"(?:确认支付|按新总价支付|pay|pay new total)\s*hk\$\s*([0-9]{1,8})(?:\.([0-9]{1,2}))?",
        text,
    )
    if match:
        return "confirm", int(match[1]) * 100 + int((match[2] or "0").ljust(2, "0"))
    return None


def matching_options(text, options):
    """None for ordinary conversation, [] for an unmatched selection."""
    label = re.sub(r"^(?:choose |select |recheck |选择\s*|选\s*)", "", text).strip()
    ordinals = {"first": 1, "second": 2, "third": 3, "一": 1, "二": 2, "三": 3}
    ordinal = re.fullmatch(
        r"(?:the |option |第)?(first|second|third|[一二三0-9])(?: one| option|个|项)?", label
    )
    if ordinal:
        n = int(ordinal[1]) if ordinal[1].isdigit() else ordinals[ordinal[1]]
        return [i for i, option in enumerate(options) if option["number"] == n]
    name, *count = re.split(r"\s*[×]\s*|\s+x\s+(?=\d+$)", label, maxsplit=1)
    named = [
        i for i, option in enumerate(options) if name in {
            unicodedata.normalize("NFKC", option[k]).casefold() for k in ("name", "sku")
        }
    ]
    if named or label != text:
        return [i for i in named if not count or str(options[i]["quantity"]) == count[0]]
    return None


def clarify(code, lang):
    return {"mode": "local", "kind": "clarify", "error": code, "message": failure(code, lang), "saved": False}


def choice_turn(service, ref, action, text, principal, chat, lang):
    if ref:
        if ref.amount_minor is not None:
            return None
        offered = service.read(ref.id, service.owner(principal), chat)
        if offered["version"] != ref.version or offered["state"] != "choosing":
            raise DomainError("SHOP_REVIEW_CHANGED", 409)
    else:
        rows = service.listing(principal, chat)
        offers = [r for r in rows if r["state"] == "choosing"]
        if not offers:
            return None
        if len(offers) > 1 or (action and any(r["state"] in {"quoted", "reprice", "retry"} for r in rows)):
            if action or any(matching_options(text, r["alternatives"]) is not None for r in offers):
                return clarify("SHOP_SELECT_CARD", lang)
            return None
        offered = offers[0]
        ref = ShopReviewRef(id=offered["id"], version=offered["version"], amount_minor=None)

    matches = matching_options(text, offered["alternatives"])
    if action and action[0] == "decline":
        index = None
    elif matches is not None and len(matches) == 1 and not action:
        index = matches[0]
    elif action or matches is not None:
        return clarify("SHOP_CHOICE_AMBIGUOUS", lang)
    else:
        return None
    try:
        row = service.choose(ref, index, principal, chat)
    except DomainError as error:
        if error.code in {"SHOP_REVIEW_CHANGED", "SHOP_NOT_FOUND"}:
            raise
        return clarify(error.code, lang)
    return {
        "mode": "local", "kind": "shopping_order", "shopping_order": row,
        "message": describe(row, lang), "saved": True,
    }


def turn(runtime, payload, principal, chat):
    if (
        not chat
        or not runtime.shop_orders.enabled
        or not principal
        or principal.get("kind") != "owner"
        or payload.attachment_ids
        or chat.attachment_ids
        or not runtime.personal_context.visible(principal)
    ):
        return None
    lang = language_for(payload.message, payload.language)
    ref = payload.shopping_review
    action = owner_decision(payload.message)
    text = unicodedata.normalize("NFKC", payload.message).strip().casefold().rstrip("。.!！")
    service = runtime.shop_orders
    if text in {"find same-store alternatives", "查找同店替代商品"}:
        if not ref:
            rows = service.listing(principal, chat.id)
            if len(rows) != 1 or not rows[0].get("can_search_again"):
                return clarify("SHOP_SELECT_CARD", lang)
            row = rows[0]
            ref = ShopReviewRef(id=row["id"], version=row["version"], amount_minor=row["review_minor"])
        try:
            result = service.search_again(ref, principal, chat.id)
        except DomainError as error:
            if error.code == "SHOP_REVIEW_CHANGED":
                raise
            return clarify(error.code, lang)
        return {"mode": "local", "kind": "reply", "message": "", **result}

    if result := choice_turn(service, ref, action, text, principal, chat.id, lang):
        return result
    if (
        action
        and not ref
        and any(
            r["state"] in {"quoted", "reprice", "retry"}
            for r in runtime.shop_orders.listing(principal, chat.id)
        )
    ):
        message = (
            "请从当前购物报价确认金额或取消。"
            if lang == "zh"
            else "Please confirm the amount on the current shopping quote, or cancel."
        )
        return {"mode": "local", "kind": "clarify", "message": message, "saved": False}
    if action and ref:
        choice, amount = action
        if amount is not None and amount != ref.amount_minor:
            raise DomainError("SHOP_REVIEW_CHANGED", 409)
        row = runtime.shop_orders.decide(
            ReviewDecision(**ref.model_dump(), action=choice), principal, chat.id
        )
    elif re.fullmatch(
        r"(?:(?:帮我|请)?(?:查一下|查回|查看|核对|查)(?:这笔|我的|刚才的)?(?:购物|测试购物|商店|商城|WooCommerce)?订单(?:的?(?:订单号|编号)?(?:和|及)?(?:实际)?(?:模拟)?扣款(?:金额|结果)?)?|(?:check|show)(?: my| the)? (?:shop|shopping|woocommerce) (?:order|receipt)(?: and (?:capture|charge))?)[？?。.!！]?",
        payload.message.strip(),
        re.I,
    ):
        rows = runtime.shop_orders.listing(principal, chat.id)
        if len(rows) != 1:
            return None
        row = runtime.shop_orders.reopen(rows[0]["id"], principal, chat.id)
    else:
        return None
    return {
        "mode": "local",
        "kind": "shopping_order",
        "shopping_order": row,
        "message": describe(row, lang),
        "saved": bool(action and ref),
    }


def failure(code, lang):
    msg = {
        "SHOP_CHOICE_AMBIGUOUS": (
            "请选择一个方案编号，或指定完整 SKU 和数量。",
            "Choose an option number, or specify its exact SKU and quantity.",
        ),
        "SHOP_SELECT_CARD": ("请从对应的购物卡选择。", "Choose from the matching shopping card."),
        "SHOP_CURRENCY_UNAVAILABLE": (
            "这家测试店以港币结账，无法按要求的币种报价。",
            "This test shop checks out in HKD and cannot quote the requested currency.",
        ),
        "SHOP_OVER_BUDGET": ("整单含运费已超出原预算。", "The basket including delivery exceeds the original budget."),
        "SHOP_NO_MATCH": (
            "测试店没有找到这个商品，请核对商品名称或 SKU。",
            "No matching product in the test shop. Check the product name or SKU.",
        ),
        "SHOP_AMBIGUOUS": (
            "有多个商品匹配，请指定完整商品名或 SKU。",
            "Several products match. Specify the full name or SKU.",
        ),
        "SHOP_ITEM_UNAVAILABLE": (
            "购物清单中有商品无法按要求购买，请核对商品和数量。",
            "An item is unavailable in the requested quantity. Check the basket before trying again.",
        ),
        "SHOP_QUANTITY_LIMIT": (
            "同一 SKU 合计最多可购买 99 件，请核对数量。",
            "The combined quantity exceeds 99 for one SKU. Check the requested quantity.",
        ),
        "SHOP_DELIVERY_UNAVAILABLE": (
            "商店未提供已核实的香港配送费，暂时无法报价。",
            "The shop did not provide a verified Hong Kong delivery rate.",
        ),
    }
    a, b = msg.get(
        code,
        ("暂时无法从测试店核实商品和总价。", "The test shop could not verify the item and total."),
    )
    return a if lang == "zh" else b
