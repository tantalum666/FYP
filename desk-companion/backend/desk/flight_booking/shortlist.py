"""Resolve an owner's words against the alternatives actually offered in this chat."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import Field

from ..commerce_review import language_for
from ..schemas import StrictModel
from ..store import DomainError
from .conversation import describe, failure
from .provider import FlightNumber, FlightQuery, HKDLimit, minor


class ShortlistQuery(StrictModel):
    option_number: int | None = Field(default=None, ge=1, le=3, strict=True)
    flight_number: FlightNumber | None = None
    check_calendar: bool = False
    max_hkd: HKDLimit | None = None


TOOL = {
    "name": "revisit_flight_shortlist",
    "description": (
        "Show this conversation's original unsubmitted flight options or recheck one for approval. "
        "Leave both selectors empty to show the options. To select, supply only the original "
        "flight number or option number explicitly chosen in this message. Set check_calendar "
        "if requested. Include max_hkd for an explicit HKD ceiling in this message. "
        "The desk binds the selection and its limits to the owner's words and the saved list. "
        "Ask for a separate search for changed travel requirements."
    ),
    "parameters": ShortlistQuery.model_json_schema(),
}


@dataclass(frozen=True)
class Command:
    action: str
    list_number: int | None
    choice: int | str | None = None
    check_calendar: bool = False
    max_hkd: float | None = None


_LIST = re.compile(
    r"(?:\b(?:(?:from|on|in) (?:the )?)?(?:flight )?(?:shortlist|list)\s*#?\s*"
    r"|(?:航班)?(?:清单|列表)\s*#?\s*)([1-9]\d{0,7})(?!\d)\s*的?"
)
_FLIGHT = r"([a-z0-9]{2})\s?(\d{1,4}[a-z]?)"
_ORDINALS = {"first": 1, "second": 2, "third": 3, "一": 1, "二": 2, "三": 3}
_ORDINAL = r"(?:option\s*#?\s*|第\s*)?(first|second|third|[一二三]|[1-9]\d?)(?:st|nd|rd|th)?"
_MENTIONED_ORDINAL = re.compile(
    r"\b(first|second|third)\b|\boption\s*#?\s*(?P<option>[1-9]\d?)\b|"
    r"\b([1-9]\d?)(?:st|nd|rd|th)\b|第\s*([一二三]|[1-9]\d?)"
)
_OPTIONS = (
    r"(?:(?:flight )?(?:options|alternatives|shortlist)|flight list|"
    r"航班(?:备选|选项|清单|列表)|(?:备选|候选|可选)航班)"
)
_CALENDAR = re.compile(
    r"[\s,.。]+(?:(?:仍要|仍需|请)?避开(?:我的)?(?:桌面)?日程|"
    r"(?:could you |please )?(?:check it against|recheck) my (?:desk )?calendar(?: too)?)$"
)
_AMOUNT = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{1,7})(?:\.[0-9]{1,2})?"
_CEILING = re.compile(
    r"(?:\bmy (?:new )?(?:limit|budget|cap) (?:is(?: now)?|(?:just |has )?(?:fell|dropped) to)|"
    r"\b(?:(?:only )?if (?:it (?:is|costs)|the (?:fare|total) is) )?(?:at most|no more than|within)|"
    r"(?:我的?)?(?:新)?(?:预算(?:上限)?|上限|限额)(?:刚刚?|现在|已)?(?:降到|降至|改为|是|为)?|"
    r"(?:只有|只在|如果)?(?:总价|票价)?不超过)\s*"
    rf"(?:(?:hk\$|hkd|港[币元])\s*(?P<prefix>{_AMOUNT})|(?P<suffix>{_AMOUNT})\s*(?:港[币元]|hkd))"
    r"(?!\d|[.,]\d)(?:时?才(?:重新)?(?:报价|核价))?"
)
_WITHIN_NEW_LIMIT = re.compile(
    r"[\s,.。]*(?:only if it fits (?:that|my|the) (?:new )?(?:limit|budget|cap)|"
    r"(?:只有|只在)(?:符合|满足)(?:这个|我的)?新(?:预算|上限|限额)(?:时)?才(?:重新)?(?:报价|核价))$"
)


def _words(message):
    return unicodedata.normalize("NFKC", message).casefold().strip().rstrip(".!?。 ")


def flight_request(message):
    # A four-digit year or a phrase such as "at 2" is not flight context.
    return bool(
        re.search(
            r"\b(?:flights?|flying|fly|airfares?|airline|one[- ]way ticket)\b|航班|机票|订票|"
            r"(?<![a-z0-9])(?=[a-z0-9]?[a-z])[a-z0-9]{2}\d{1,4}[a-z]?(?![a-z0-9])",
            _words(message),
        )
        or re.search(r"(?<!\w)(?=[A-Z0-9]?[A-Z])[A-Z0-9]{2} \d{1,4}[A-Z]?(?!\w)", message)
    )


def refers_to_options(message):
    text = _words(message)
    return bool(
        _LIST.search(text)
        or re.search(
            r"\bshortlist\b|\b(?:original|previous|earlier|those|offered) "
            r"(?:flight )?(?:choices|options|alternatives|flights|offers|fares)\b|"
            r"(?:原来|原始|之前|上次|刚才).*(?:航班|选项|清单)",
            text,
        )
        or any(
            ordinal["option"]
            or re.match(
                r"\s+(?:one|departure|option|flight|offer)\b(?!\s+(?:from|to)\b)|"
                r"\s*(?:[个项班趟]|航班)",
                text[ordinal.end() :],
            )
            for ordinal in _MENTIONED_ORDINAL.finditer(text)
        )
    )


def _ordinal(value):
    return _ORDINALS[value] if value in _ORDINALS else int(value)


def _command(payload, *, conversational=False):
    text = _words(payload.message)
    label = _LIST.search(text)
    number = int(label[1]) if label else None
    if label:
        text = (text[: label.start()] + " " + text[label.end() :]).strip()
    text = re.sub(r"^(?:please |请帮我|帮我|请)", "", text).strip()
    if re.fullmatch(
        rf"(?:(?:show|reopen|revisit|list|what were|what are)(?: me)? "
        rf"(?:(?:my|the|those|original|previous|earlier|other|offered|flight) )*{_OPTIONS}(?: again)?"
        rf"|could i look at (?:those|the) (?:flight )?(?:choices|options) again"
        rf"|(?:再|重新)?(?:看一下|看看|查看|打开|列出|看)?(?:之前的?|原来[的那]*|原始的?|上次的?|我的)?"
        rf"{_OPTIONS}(?:有哪些|有什么)?)",
        text,
    ) or (label and text in {"show", "reopen", "查看", "打开"}):
        return Command("show", number)
    if re.fullmatch(rf"(?:cancel (?:my |the )?|取消|放弃){_OPTIONS}", text) or (
        label and text in {"cancel", "取消", "放弃"}
    ):
        return Command("cancel", number)
    return _pick(text, number, payload.calendar_flight_choice, conversational)


def _pick(text, number, pin, conversational):
    check_calendar = bool(pin or _CALENDAR.search(text))
    text = _CALENDAR.sub("", text).rstrip(" .。")
    # Consume a complete budget clause at either end. Everything else must still
    # form one positive selection, including when a Session supplies a selector.
    max_hkd = None
    if limit := _CEILING.search(text):
        before = text[: limit.start()].rstrip(" ,.。")
        after = text[limit.end() :].lstrip(" ,.。")
        try:
            max_hkd = minor((limit["prefix"] or limit["suffix"]).replace(",", "")) / 100
        except DomainError:
            return None
        if not max_hkd or (before and after):
            return None
        text = _WITHIN_NEW_LIMIT.sub("", before or after)
    if pin and pin.max_hkd is not None:
        max_hkd = pin.max_hkd if max_hkd is None else min(max_hkd, pin.max_hkd)
    text = re.sub(r"^(?:please |请帮我|帮我|请)", "", text).strip()
    if pin and pin.flight_number:
        flight = pin.flight_number.lower()
        route = f"from {pin.origin} to {pin.destination} on {pin.departure}".lower()
        if text in {
            "check this flight again",
            f"recheck test flight {flight} {route} on the same terms and show me the quote",
            f"选 {flight},{pin.departure} 从 {pin.origin.lower()} 到 {pin.destination.lower()},请按原条件重新核价给我确认",
        }:
            return Command("pick", number, flight.replace(" ", "").upper(), True, max_hkd)
    text = re.sub(r"[, ]+(?:请先核价|请重新核价)$", "", text)
    if conversational:
        text = re.sub(
            r"^(?:(?:(?:could|can) you (?:please )?)?(?:get(?: me)?|give me) a (?:fresh |new )?quote for |"
            r"i['’]d like to see whether |(?:给我|给|为))", "", text,
        )
        text = re.sub(r"(?: suits me| still works|\s*重新(?:核价|报价))$", "", text).strip()
    text = re.sub(
        r"^(?:(?:i['’]ll take|i choose|choose|pick|select|take|go with|book|recheck) |"
        r"(?:我想选|我选|选择|就选|我要|选|订))",
        "",
        text,
    ).strip()
    text = re.sub(r"^(?:the )?(?:flight |航班\s*)?", "", text).strip()
    if flight := re.fullmatch(_FLIGHT, text):
        return Command("pick", number, "".join(flight.groups()).upper(), check_calendar, max_hkd)
    ordinal = re.fullmatch(
        _ORDINAL + r"(?: (?:one|option|flight|departure)|\s*[个项班](?:航班|选项)?)?(?:吧)?", text
    )
    if ordinal:
        return Command("pick", number, _ordinal(ordinal[1]), check_calendar, max_hkd)
    return None


def turn(service, payload, principal, chat):
    if not chat or payload.selected_commerce_card or payload.attachment_ids or chat.attachment_ids:
        return None
    command = _command(payload, conversational=payload.calendar_flight_choice is not None)
    if not command and payload.calendar_flight_choice:
        command = Command("clarify", None)
    if (
        not command
        or not service.enabled
        or not service.runtime.personal_context.visible(principal)
    ):
        return None
    return _resolve(service, payload, principal, chat, command, allow_fallback=True)


def from_function(service, payload, principal, chat, arguments):
    query = ShortlistQuery.model_validate(arguments)
    command = _command(payload, conversational=True)
    proposed = query.flight_number.replace(" ", "") if query.flight_number else query.option_number
    # The Function can propose a choice. Only the owner's complete request can
    # authorize it or change its terms. In particular its max_hkd is advisory.
    if not command or command.action == "cancel" or (
        command.action == "pick"
        and (command.choice != proposed or (query.flight_number and query.option_number))
    ):
        command = Command("clarify", command.list_number if command else None)
    return _resolve(service, payload, principal, chat, command)


def _resolve(service, payload, principal, chat, command, *, allow_fallback=False):
    zh = language_for(payload.message, payload.language) == "zh"

    def reply(message, **fields):
        return {
            "mode": "local",
            "kind": "clarify",
            "saved": False,
            "message": message,
            "flight_shortlist_chat": chat.id,
            **fields,
        }

    number, choice = command.list_number, command.choice
    # For a bare selector distinguish a closed list from an unrelated chat. A
    # legacy pinned card carries its own search terms and may predate saved lists.
    lists = service.shortlists(principal, chat.id, include_closed=True)
    pin = payload.calendar_flight_choice
    if pin and allow_fallback:
        pinned_flight = (pin.flight_number or "").replace(" ", "")
        lists = {
            n: row
            for n, row in lists.items()
            if any(
                (seg["flight"], seg["origin"], seg["destination"], seg["departs"][:10])
                == (pinned_flight, pin.origin, pin.destination, pin.departure)
                for seg in (o["segment"] for o in row["shortlist"]["alternatives"])
            )
        }
        if not lists and (choice != pinned_flight or command.max_hkd != pin.max_hkd):
            command = Command("clarify", number)
    if command.action == "clarify":
        return reply(
            "请明确原选项和港币上限。如需更改其他条件，请按新条件单独查询。"
            if zh else "Please specify the original option and your HKD limit. "
            "For other changes, request a separate flight search with the new conditions.",
            flight_shortlist_chat=chat.id if lists else None,
        )
    if (
        not lists
        and allow_fallback
        and number is None
        and (
            command.action == "pick"
            or not re.search(r"flight|shortlist|航班|机票", _words(payload.message))
        )
    ):
        return None
    lists = {n: row for n, row in lists.items() if row["open"] and number in (None, n)}
    if number is None and isinstance(choice, int) and not pin and not flight_request(payload.message):
        if allow_fallback and payload.shopping_review and payload.shopping_review.amount_minor is None:
            return None
        if not payload.flight_review and service.runtime.shop_orders.has_open_choices(principal, chat):
            if not lists and allow_fallback:
                return None
            return reply(
                "请选择购物替代选项，或指明航班清单编号。" if zh else
                "Choose the shopping alternative on its card, or name the flight list number.",
                flight_shortlist_chat=chat.id if lists else None,
            )
    if not lists:
        # An empty conversation has no durable binding to authorize cached replay.
        return reply(
            "这段对话中没有这份待选航班清单。"
            if zh
            else "There is no open flight shortlist matching that request in this conversation.",
            flight_shortlist_chat=None,
        )
    if pin and command.action == "pick":
        # A previous client can send the original card with a stricter ceiling.
        # All its other terms and the selected departure still have to match.
        lists = {
            n: row for n, row in lists.items()
            if any(
                choice in (i, option["segment"]["flight"]) and _matches_pin(option, pin)
                for i, option in enumerate(row["shortlist"]["alternatives"], 1)
            )
        }
    if isinstance(choice, str):
        lists = {
            n: row
            for n, row in lists.items()
            if any(
                o["segment"]["flight"] == choice
                for o in row["shortlist"]["alternatives"]
            )
        }
    if not lists:
        return reply(
            f"{choice} 不在符合这些条件的原选项中。"
            if zh
            else f"{choice} was not offered on those terms in the original shortlist."
        )
    if len(lists) > 1:
        lines = [
            "请指定航班清单，例如“查看航班清单 2”。"
            if zh
            else "Which flight shortlist? For example, say “show flight list 2”."
        ]
        for n, row in lists.items():
            offered = row["shortlist"]
            leg = offered["alternatives"][0]["segment"]
            lines.append(
                f"{n}. {leg['origin']} → {leg['destination']} · {leg['departs'][:10]} · {offered['unavailable_flight']}"
            )
        return reply("\n".join(lines))
    number, row = next(iter(lists.items()))
    offered = row["shortlist"]
    if command.action == "show":
        return reply(
            "", flight_alternatives={**offered, "shortlist_number": number, "original": True}
        )
    request = {"id": row["id"], "version": row["version"]}
    if command.action == "cancel":
        return reply("", flight_shortlist_review=request)
    options = offered["alternatives"]
    if isinstance(choice, str):
        matches = [
            i for i, option in enumerate(options, 1) if option["segment"]["flight"] == choice
        ]
        if len(matches) != 1:
            return reply(
                "这个航班号有多个起飞时间，请按原清单的序号选择。"
                if zh
                else "That flight number has multiple departures. Choose its original option number."
            )
        choice = matches[0]
    if not 1 <= choice <= len(options):
        return reply(
            "原清单里没有这个序号。" if zh else "There is no such option on the original shortlist."
        )
    return reply(
        "",
        flight_shortlist_review={
            **request,
            "option": choice,
            "check_calendar": command.check_calendar or payload.flight_calendar_requested,
            "max_hkd": command.max_hkd,
        },
    )


def _matches_pin(option, pin):
    if not option.get("calendar_choice"):
        return False
    original = FlightQuery.model_validate(option["calendar_choice"])
    return (
        (original.max_hkd is None or (pin.max_hkd is not None and pin.max_hkd <= original.max_hkd))
        and original == pin.model_copy(update={
            "flight_number": (pin.flight_number or "").replace(" ", ""), "max_hkd": original.max_hkd,
        })
    )


def recover_review(service, reply, key, principal, chat, payload):
    """Bind a pre-upgrade receipt to the same owner message on an operation retry."""
    pending = reply.get("flight_shortlist_review")
    booking = reply.get("flight_booking")
    if pending:
        if "option" not in pending or "max_hkd" in pending:
            return reply
    elif not booking or booking["state"] != "quoted":
        return reply
    command = _command(payload, conversational=True)
    if not pending and command and command.max_hkd is None and not command.check_calendar:
        return reply
    checked = _resolve(service, payload, principal, chat, command or Command("clarify", None))
    bound = checked.get("flight_shortlist_review", {})
    original = pending or booking
    same = bound.get("id") == original["id"] and (
        not pending or bound.get("option") == pending["option"]
    )
    row = service.bind_legacy_selection(
        original["id"], key, principal, chat.id, selection=bound.get("option") if same else None,
        ceiling=command.max_hkd if command else None,
        calendar=payload.flight_calendar_requested or bool(command and command.check_calendar),
    )
    if row and row["state"] == "expired":
        return {
            "mode": "local", "kind": "clarify", "saved": False, "flight_shortlist_chat": chat.id,
            "error": "FLIGHT_OPTION_UNAVAILABLE",
        }
    if not pending:
        return reply
    if same:
        # Keep the originally admitted version so a newer selection or cancellation wins.
        bound["version"] = pending["version"]
        return checked
    return _resolve(service, payload, principal, chat, Command("clarify", None))


def apply_review(service, request, key, principal, chat, lang):
    reply = {"mode": "local", "kind": "clarify", "saved": False, "flight_shortlist_chat": chat.id}
    try:
        review = service.review_shortlist(request, key, principal, chat.id)
    except DomainError as error:
        if error.code not in {
            "FLIGHT_OPTION_UNAVAILABLE",
            "FLIGHT_PROVIDER_REFUSED",
            "FLIGHT_RECEIPT_MISMATCH",
            "FLIGHT_TEST_SCOPE",
        }:
            raise
        return {**reply, "message": failure(error.code, lang), "error": error.code}
    if review is None:
        return {
            **reply,
            "message": "已取消这份航班清单。" if lang == "zh" else "Flight shortlist cancelled.",
        }
    return {
        **reply,
        "message": describe(review, lang),
        "kind": "flight_booking",
        "flight_booking": review,
    }
