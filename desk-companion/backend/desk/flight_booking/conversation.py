"""Conversation presentation and explicit owner replies for sandbox flight reviews."""

import re
import unicodedata

from .provider import FlightQuery, minor
from .service import FlightReview


TOOL = {
    "name": "sandbox_flight_quote",
    "description": (
        "For a request to book a flight, prepare a LetsFG TEST booking in this conversation. "
        "Only search for an exact one-way flight and show the owner the itinerary and HKD total. "
        "Use one fictional adult unless the user specifies a different party. Include any requested "
        "flight number, airline, nonstop, price ceiling, return date or checked kg; never drop a "
        "constraint or invent an airport/date. Ask about missing or ambiguous details first. "
        "Set rehearse_price_change=true when asked to demonstrate a mid-booking price rise. "
        "No real card or booking is available. For public real fare research only use the separate "
        "browser_research_draft. The user must confirm on screen or explicitly in this chat; "
        "this function cannot submit an order, accept a price increase or approve a charge."
    ),
    "parameters": FlightQuery.model_json_schema(),
}


def price(cents):
    return f"HK${cents // 100:,}.{cents % 100:02d}"


def describe(row, language):
    zh = language == "zh"
    legs = row["segments"]
    flights = " / ".join(x["flight"] for x in legs)
    route = f"{legs[0]['origin']} → {legs[-1]['destination']}"
    total = price(row["review_minor"])
    state = row["state"]
    if state == "quoted":
        times = f"{legs[0]['departs'].replace('T', ' ')} → {legs[-1]['arrives'].replace('T', ' ')}"
        return (
            f"LetsFG 测试航班 {flights}，{route}，{times}（当地时间）。1 位成人，模拟总价 {total}。确认后我才下测试单。"
            if zh
            else f"LetsFG test flight {flights}, {route}, {times} local. One adult, total {total}. Confirm to place the test booking."
        )
    if state == "reprice":
        old = price(row["previous_minor"])
        return (
            f"{flights} 的模拟总价从 {old} 涨至 {total}。要按新总价继续，还是拒绝加价？"
            if zh
            else f"The test total for {flights} rose from {old} to {total}. Accept the new total or decline the increase?"
        )
    if state == "completed":
        paid = price(row["charged_minor"])
        return (
            f"我已查回 LetsFG 测试订单。订座编号 {row['pnr']}，模拟扣款 {paid}，真实扣款 HK$0。"
            if zh
            else f"I checked the LetsFG test order. Booking reference {row['pnr']}. Simulated charge {paid}. Real charge HK$0."
        )
    if state == "failed" and row["released"]:
        return (
            "测试订单已结束。模拟预授权已释放，没有扣款或订座编号。"
            if zh
            else "The test booking ended. The hold was released, with no charge or booking reference."
        )
    messages = {
        "cancelled": (
            "已取消这份报价，没有提交测试订单。",
            "Quote cancelled. No test order was submitted.",
        ),
        "expired": ("报价已过期，请重新查价。", "This quote expired. Request a fresh fare."),
        "unverified": (
            "供应商回执尚无法核实，订座和扣款待核对。",
            "The provider receipt could not be verified. Booking and charge remain unconfirmed.",
        ),
        "failed": (
            "测试订单未完成，供应商未确认扣款。",
            "The test booking failed. No capture was verified.",
        ),
        "submit_unknown": (
            "提交回执未到。可以用原请求编号恢复这笔测试单。",
            "The submission receipt is missing. Recover this test order using its original request.",
        ),
        "answering": (
            "已记录选择，正在查回原测试订单。",
            "Your choice was recorded. Checking the original test order.",
        ),
    }
    zh_message, en_message = messages.get(
        state,
        (
            "已按你确认的价格提交测试单，正在查回原订单。",
            "Test booking submitted at the approved price. Checking the original order.",
        ),
    )
    return zh_message if zh else en_message


def owner_decision(message):
    text = unicodedata.normalize("NFKC", message).strip().casefold().rstrip(".!。！").strip()
    if re.fullmatch(
        r"(?:确认|确定|同意|可以|确认预订|确认下单|同意新价格|同意新总价|接受新价格|确认加价|confirm|yes|book it|accept the new total|recover this test booking|恢复原测试单)",
        text,
    ):
        return "confirm", None
    if re.fullmatch(
        r"(?:取消|取消预订|不要下单|拒绝|拒绝加价|不接受|cancel|decline|decline the increase)", text
    ):
        return "decline", None
    match = re.fullmatch(
        r"(?:确认(?:按|新总价)?|同意(?:新总价)?|confirm(?: test booking at| new total)?|accept new total)\s*hk\$\s*([0-9]+(?:\.[0-9]{1,2})?)(?:\s*(?:预订测试航班|下单|继续))?",
        text,
    )
    return ("confirm", minor(match.group(1))) if match else None


def turn(runtime, payload, principal, chat):
    if (
        not chat
        or not principal
        or principal["kind"] != "owner"
        or payload.attachment_ids
        or chat.attachment_ids
    ):
        return None
    if not runtime.flight_bookings.enabled or not runtime.personal_context.visible(principal):
        return None
    decision = owner_decision(payload.message)
    ref = payload.flight_review
    if (
        decision
        and not ref
        and any(
            row["state"] in {"quoted", "reprice", "submit_unknown"}
            for row in runtime.flight_bookings.listing(principal, chat.id)
        )
    ):
        msg = (
            "请先核对当前航班和总价，再用这张报价上的确认或拒绝按钮。"
            if payload.language == "zh"
            else "Review the current flight and total, then use its confirm or decline button."
        )
        return {"mode": "local", "kind": "clarify", "message": msg, "saved": False}
    if decision and ref:
        action, spoken = decision
        if spoken is not None and spoken != ref.amount_minor:
            from ..store import DomainError

            raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        row = runtime.flight_bookings.decide(
            FlightReview(**ref.model_dump(), action=action), principal, chat.id
        )
        return {
            "mode": "local",
            "kind": "flight_booking",
            "flight_booking": row,
            "message": describe(row, payload.language),
            "saved": True,
        }
    if re.fullmatch(
        r"(?:查(?:一下|回)?(?:这笔|我的)?(?:测试)?(?:订单|订座编号|扣款结果)|(?:测试)?订单(?:怎么样了|状态|结果)|(?:what is|check|show)(?: my| the)? (?:test )?(?:booking status|booking reference|booking receipt))[？?。.!！]?",
        payload.message.strip(),
        re.I,
    ):
        rows = runtime.flight_bookings.listing(principal, chat.id)
        if len(rows) == 1:
            return {
                "mode": "local",
                "kind": "flight_booking",
                "flight_booking": rows[0],
                "message": describe(rows[0], payload.language),
                "saved": False,
            }
    return None


def failure(code, language):
    messages = {
        "FLIGHT_TEST_SCOPE": (
            "目前可预订一位虚构成人的单程基础票价。能否按这个范围查询？",
            "I can test a one-way base fare for one fictional adult. Would that work?",
        ),
        "FLIGHT_NO_MATCH": (
            "LetsFG 测试库存里没有符合这些条件的航班。可以更改日期或航班号再查。",
            "No test flight matched those details. Try another date or flight number.",
        ),
        "FLIGHT_PAST_DATE": (
            "请提供今天或之后的出发日期。",
            "Please provide a current or future departure date.",
        ),
    }
    zh, en = messages.get(
        code,
        (
            "暂时无法核实 LetsFG 测试报价，请稍后重试。",
            "I could not verify that LetsFG test quote. Please try again later.",
        ),
    )
    return zh if language == "zh" else en
