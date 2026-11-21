"""Ordinary chat entry and localized, grounded replies for the test shop."""

import re
import unicodedata

from ..commerce_review import ReviewDecision
from ..store import DomainError
from .provider import ShopQuery

TOOL = {
    "name": "sandbox_shop_quote",
    "description": (
        "For a request to buy an item, prepare an order quote from the owner's WooCommerce TEST shop. "
        "Use the requested product name in its original language or its exact SKU and the exact quantity of selling units. "
        "Ask if either is missing or ambiguous. The shop computes delivery to the fictional Hong Kong address and the full HKD total. "
        "For price research on a named real merchant use browser_research_draft instead. No real goods or money. "
        "This function cannot place an order, approve a price or charge a card. The owner confirms the displayed exact cart and each change."
    ),
    "parameters": ShopQuery.model_json_schema(),
}


def language_for(message, language):
    return "zh" if language == "zh" or re.search(r"[\u3400-\u9fff]", message) else "en"


def price(n):
    return f"HK${n // 100:,}.{n % 100:02d}"


def describe(row, language):
    q = row["quote"]
    t = q["terms"]
    zh = language == "zh"
    if row["state"] == "quoted":
        return (
            f"{q['name']} × {t['quantity']}：商品 {price(t['subtotal_minor'])}，运费 {price(t['shipping_minor'])}，测试订单总价 {price(t['total_minor'])}。确认后我才付款。"
            if zh
            else f"{q['name']} × {t['quantity']}. Items {price(t['subtotal_minor'])}, delivery {price(t['shipping_minor'])}, order total {price(t['total_minor'])}. Confirm to make the test payment."
        )
    if row["state"] == "reprice":
        old = row["previous"]["terms"]
        return (
            f"商店更新了结账报价：原总价 {price(old['total_minor'])}，新总价 {price(t['total_minor'])}，其中运费 {price(t['shipping_minor'])}。还没有付款。按新报价继续吗？"
            if zh
            else f"The shop updated checkout from {price(old['total_minor'])} to {price(t['total_minor'])}, including delivery of {price(t['shipping_minor'])}. No payment yet. Accept the new quote?"
        )
    receipt = row.get("receipt") or {}
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
            "正在查回商户撤单和原付款的退款结果。",
            "Checking the merchant cancellation and the refund on the original payment.",
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
        "SHOP_NO_MATCH": (
            "测试店没有找到这个商品，请核对商品名称或 SKU。",
            "No matching product in the test shop. Check the product name or SKU.",
        ),
        "SHOP_AMBIGUOUS": (
            "有多个商品匹配，请指定完整商品名或 SKU。",
            "Several products match. Specify the full name or SKU.",
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
