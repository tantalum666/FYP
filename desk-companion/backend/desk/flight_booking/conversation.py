"""Conversation presentation and explicit owner replies for sandbox flight reviews."""

import re

from ..store import DomainError

from ..commerce_review import ReviewRef, language_for
import unicodedata

from .provider import FlightQuery, minor
from ..commerce_review import ReviewDecision as FlightReview


TOOL = {
    "name": "sandbox_flight_quote",
    "description": (
        "For a request to book a flight, prepare a LetsFG TEST booking in this conversation. "
        "Only search for an exact one-way flight and show the owner the itinerary and HKD total. "
        "Use one fictional adult unless the user specifies a different party. Include any requested "
        "flight number, airline, nonstop, price ceiling, return date or checked kg; never drop a "
        "constraint or invent an airport/date. Ask about missing or ambiguous details first. "
        "Set avoid_calendar_conflicts=true when the owner asks for a flight that fits their schedule. "
        "Set rehearse_price_change=true when asked to demonstrate a mid-booking price rise. "
        "No real card or booking is available. For public real fare research only use the separate "
        "browser_research_draft. The user must confirm on screen or explicitly in this chat; "
        "this function cannot submit an order, accept a price increase or approve a charge."
    ),
    "parameters": FlightQuery.model_json_schema(),
}


def price(cents):
    return f"HK${cents // 100:,}.{cents % 100:02d}"


def describe_alternatives(result, language):
    zh = language == "zh"
    requested = result["unavailable_flight"]
    header = (
        f"当天的 LetsFG 测试库存没有 {requested}。同一航线还有以下选择（当地时间）："
        if zh
        else f"{requested} is unavailable in the test inventory. Other flights on the same route, in local time:"
    )
    reason = result.get("requested_calendar_fit")
    if reason == "conflict":
        header = (
            f"{requested} 查询时和桌面日程冲突。以下航班已错开。"
            if zh
            else f"{requested} overlapped the desk calendar at lookup. These flights fit."
        )
    elif reason == "unknown":
        header = (
            f"{requested} 的时间无法和桌面日历核准。以下航班已错开。"
            if zh
            else f"{requested} could not be checked against the desk calendar. These flights fit."
        )
    elif result.get("avoid_calendar_conflicts"):
        header = (
            f"没有 {requested}，以下航班已错开桌面日程。"
            if zh
            else f"{requested} is unavailable. These alternatives fit your desk calendar."
        )
    lines = [header]
    for option in result["alternatives"]:
        leg = option["segment"]
        lines.append(
            f"{leg['flight']} · {leg['origin']} → {leg['destination']} · {leg['departs'].replace('T', ' ')} → {leg['arrives'].replace('T', ' ')} · {price(option['total_minor'])}"
        )
    lines.append(
        "告诉我想选的航班号，我会重新核价给你确认。目前没有订位或扣款。"
        if zh
        else "Choose a flight number and I will recheck its price for your approval. Nothing has been booked or charged."
    )
    return "\n".join(lines)


def describe(row, language):
    zh = language == "zh"
    legs = row["segments"]
    flights = " / ".join(x["flight"] for x in legs)
    route = f"{legs[0]['origin']} → {legs[-1]['destination']}"
    total = price(row["review_minor"])
    state = row["state"]
    if row.get("calendar_fit") in {"conflict", "unknown"}:
        reason = (
            ("和桌面日程冲突" if row["calendar_fit"] == "conflict" else "的日历匹配暂时无法核准")
            if zh
            else (
                "overlaps a desk calendar event"
                if row["calendar_fit"] == "conflict"
                else "could not be checked against your desk calendar"
            )
        )
        if state == "quoted":
            return (
                f"{flights} {reason}，尚未下单。"
                if zh
                else f"{flights} {reason}. No booking has been submitted."
            )
        if state == "reprice":
            return (
                f"{flights} {reason}，尚未接受新票价。"
                if zh
                else f"{flights} {reason}. The new fare has not been accepted."
            )
        return (
            f"{flights} {reason}，原订座结果仍待核实。"
            if zh
            else f"{flights} {reason}. The original booking is still unverified."
        )
    if state == "stopped":
        return (
            "供应商已停止这笔订票并释放预授权，模拟扣款 HK$0.00，未取得订座编号。"
            if zh
            else "The supplier stopped this booking and released its hold. Test charge HK$0.00. No reservation reference."
        )
    if state == "manual":
        return (
            "供应商正在人工核查。请查询原订单，扣款及订座结果待供应商确认。"
            if zh
            else "The supplier is reviewing the original booking. Payment and reservation await verification."
        )
    if state == "stopping":
        return (
            "已请求停止订票，正在向供应商核实预授权和扣款。"
            if zh
            else "Stop requested. Checking the hold and payment on the original booking."
        )
    if row.get("stop_status") == "too_late":
        if state == "completed":
            return (
                f"供应商已购票，停止订票窗口已过。订座编号 {row['pnr']}，原模拟扣款 {price(row['charged_minor'])}。退票须另查卖家票规，尚无退款回执。"
                if zh
                else f"The supplier already bought the ticket. Reference {row['pnr']}, test charge {price(row['charged_minor'])}. A post-ticket refund depends on seller rules and has not been verified."
            )
        return (
            "供应商已过停止窗口，正在查回原订座和扣款。"
            if zh
            else "The supplier's stop window has passed. Checking the original booking and payment."
        )
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


def prompt_context(runtime, principal, chat):
    """Project only public card fields from this login and conversation."""
    rows = runtime.flight_bookings.listing(principal, chat.id)
    return [
        {
            k: row[k]
            for k in (
                "segments",
                "currency",
                "state",
                "quoted_minor",
                "approved_minor",
                "review_minor",
                "charged_minor",
                "pnr",
                "released",
            )
        }
        for row in rows[:3]
    ]


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
    lang = language_for(payload.message, payload.language)
    if re.fullmatch(
        r"(?:请|帮我|請)?(?:换一班|换个航班|查其他航班|找其他航班|find another flight|check other flights)[。.!！]?",
        payload.message.strip(),
        re.I,
    ):
        service = runtime.flight_bookings
        ref = payload.flight_review if payload.selected_commerce_card else None
        if not ref:
            choices = [r for r in service.listing(principal, chat.id) if r.get("can_find_other")]
            if len(choices) != 1:
                return {
                    "mode": "local",
                    "kind": "clarify",
                    "saved": False,
                    "message": (
                        "请在原报价上选择要重新查的航班。"
                        if lang == "zh"
                        else "Choose the flight to recheck on its original quote."
                    ),
                }
            row = choices[0]
            ref = ReviewRef(id=row["id"], version=row["version"], amount_minor=row["review_minor"])
        try:
            result = service.find_other(principal, chat.id, ref)
        except DomainError as error:
            if error.code not in {
                "FLIGHT_NO_OTHER",
                "FLIGHT_NO_MATCH",
                "FLIGHT_CALENDAR_UNKNOWN",
                "FLIGHT_CALENDAR_BUSY",
                "FLIGHT_PROVIDER_UNAVAILABLE",
                "FLIGHT_PAST_DATE",
            }:
                raise
            return {
                "mode": "local",
                "kind": "clarify",
                "message": failure(error.code, lang),
                "error": error.code,
                "saved": False,
            }
        return {"mode": "local", "kind": "reply", "message": "", "saved": False, **result}
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
            if lang == "zh"
            else "Review the current flight and total, then use its confirm or decline button."
        )
        return {"mode": "local", "kind": "clarify", "message": msg, "saved": False}
    if decision and ref:
        action, spoken = decision
        if spoken is not None and spoken != ref.amount_minor:
            raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        row = runtime.flight_bookings.decide(
            FlightReview(**ref.model_dump(), action=action), principal, chat.id
        )
        return {
            "mode": "local",
            "kind": "flight_booking",
            "flight_booking": row,
            "message": describe(row, lang),
            "saved": True,
        }
    if re.fullmatch(
        r"(?:(?:帮我|请)?查(?:一下|回)?(?:这笔|我的)?(?:测试)?(?:订单(?:的订座编号和扣款结果)?|订座编号(?:和扣款结果)?|扣款结果)|(?:测试)?订单(?:怎么样了|状态|结果)|(?:what is|check|show)(?: my| the)? (?:test )?(?:booking status|booking reference|booking receipt))[？?。.!！]?",
        payload.message.strip(),
        re.I,
    ):
        rows = runtime.flight_bookings.listing(principal, chat.id)
        if len(rows) == 1:
            row = runtime.flight_bookings.reopen(rows[0]["id"], principal, chat.id)
            return {
                "mode": "local",
                "kind": "flight_booking",
                "flight_booking": row,
                "message": describe(row, lang),
                "saved": False,
            }
    return None


def failure(code, language):
    messages = {
        "FLIGHT_TEST_SCOPE": (
            "目前可预订一位虚构成人的单程基础票价。能否按这个范围查询？",
            "I can test a one-way base fare for one fictional adult. Would that work?",
        ),
        "FLIGHT_CHOICE_CHANGED": (
            "新报价和所选航班或预算不符，请重新查价。",
            "The new fare does not match your chosen flight or budget. Please recheck the search.",
        ),
        "FLIGHT_NO_OTHER": (
            "按原路线和预算暂时没有其他测试航班。",
            "There are no other test flights within the original route and budget.",
        ),
        "FLIGHT_CALENDAR_BUSY": (
            "符合条件的测试航班都和桌面日程冲突。可以换个时段。",
            "All matching test flights overlap the desk calendar. Try a different time.",
        ),
        "FLIGHT_CALENDAR_UNKNOWN": (
            "当前没有能核实已避开桌面日程的航班。可以换个时段。",
            "No matching flight could be verified clear on your desk calendar. Try a different time.",
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
