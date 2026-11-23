"""Resolve an owner's words against the alternatives actually offered in this chat."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import Field

from ..commerce_review import language_for
from ..schemas import StrictModel
from ..store import DomainError
from .conversation import describe, failure
from .provider import FlightNumber, FlightQuery


class ShortlistQuery(StrictModel):
    option_number: int | None = Field(default=None, ge=1, le=3, strict=True)
    flight_number: FlightNumber | None = None
    check_calendar: bool = False


TOOL = {
    "name": "revisit_flight_shortlist",
    "description": (
        "Show this conversation's original unsubmitted flight options or recheck one for approval. "
        "Leave both selectors empty to show the options. To select, supply only the original "
        "flight number or option number explicitly chosen in this message. Set check_calendar "
        "if requested. The desk resolves any list number and the original search terms locally."
    ),
    "parameters": ShortlistQuery.model_json_schema(),
}


@dataclass(frozen=True)
class Command:
    action: str
    list_number: int | None
    choice: int | str | None = None
    check_calendar: bool = False


_LIST = re.compile(
    r"(?:\b(?:(?:from|on|in) (?:the )?)?(?:flight )?(?:shortlist|list)\s*#?\s*"
    r"|(?:航班)?(?:清单|列表)\s*#?\s*)([1-9]\d{0,7})\s*的?"
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
_CALENDAR = re.compile(r"[, ]+(?:仍要|仍需)避开(?:我的)?(?:桌面)?日程$")


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


def _command(payload):
    text = re.sub(r"^(?:please |请帮我|帮我|请)", "", _words(payload.message)).strip()
    label = _LIST.search(text)
    number = int(label[1]) if label else None
    if label:
        text = (text[: label.start()] + " " + text[label.end() :]).strip()
    if pin := payload.calendar_flight_choice:
        return Command("pick", number, (pin.flight_number or "").replace(" ", ""), True)
    if re.fullmatch(
        rf"(?:(?:show|reopen|revisit|list|what were|what are)(?: me)? "
        rf"(?:(?:my|the|those|original|previous|earlier|other|offered|flight) )*{_OPTIONS}(?: again)?"
        rf"|(?:再|重新)?(?:看一下|看看|查看|打开|列出|看)?(?:之前的?|原来[的那]*|原始的?|上次的?|我的)?"
        rf"{_OPTIONS}(?:有哪些|有什么)?)",
        text,
    ) or (label and text in {"show", "reopen", "查看", "打开"}):
        return Command("show", number)
    if re.fullmatch(rf"(?:cancel (?:my |the )?|取消|放弃){_OPTIONS}", text) or (
        label and text in {"cancel", "取消", "放弃"}
    ):
        return Command("cancel", number)
    # Additional travel requirements are not silently dropped from a selection.
    check_calendar = bool(_CALENDAR.search(text))
    text = re.sub(r"[, ]+(?:请先核价|请重新核价)$", "", _CALENDAR.sub("", text))
    text = re.sub(
        r"^(?:(?:i['’]ll take|i choose|choose|pick|select|take|go with|book|recheck) |"
        r"(?:我想选|我选|选择|就选|我要|选|订))",
        "",
        text,
    ).strip()
    text = re.sub(r"^(?:the )?(?:flight |航班\s*)?", "", text)
    if flight := re.fullmatch(_FLIGHT, text):
        return Command("pick", number, "".join(flight.groups()).upper(), check_calendar)
    ordinal = re.fullmatch(
        _ORDINAL + r"(?: (?:one|option|flight)|\s*[个项班](?:航班)?)?(?:吧)?", text
    )
    if ordinal:
        return Command("pick", number, _ordinal(ordinal[1]), check_calendar)
    return None


def turn(service, payload, principal, chat):
    if not chat or payload.selected_commerce_card or payload.attachment_ids or chat.attachment_ids:
        return None
    command = _command(payload)
    if (
        not command
        or not service.enabled
        or not service.runtime.personal_context.visible(principal)
    ):
        return None
    return _resolve(service, payload, principal, chat, command, allow_fallback=True)


def from_function(service, payload, principal, chat, arguments):
    query = ShortlistQuery.model_validate(arguments)
    text = _words(payload.message)
    labels = _LIST.findall(text)
    number = int(labels[0]) if len(labels) == 1 else None
    text = _LIST.sub(" ", text)
    # A model may interpret intent, but cannot supply a missing selector or decide
    # between two alternatives the owner mentioned together.
    flights = {
        (carrier + num).upper()
        for carrier, num in re.findall(rf"(?<![a-z0-9]){_FLIGHT}(?![a-z0-9])", text)
    }
    ordinals = {_ordinal(match[match.lastindex]) for match in _MENTIONED_ORDINAL.finditer(text)}
    choices = flights | ordinals
    proposed = query.flight_number.replace(" ", "") if query.flight_number else query.option_number
    if (
        len(labels) <= 1
        and not (query.flight_number and query.option_number)
        and choices == {proposed}
    ):
        command = Command("pick", number, proposed, query.check_calendar)
    else:
        command = Command("show", number)
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
        lists = {
            n: row
            for n, row in lists.items()
            if any(
                (seg["flight"], seg["origin"], seg["destination"], seg["departs"][:10])
                == (choice, pin.origin, pin.destination, pin.departure)
                for seg in (o["segment"] for o in row["shortlist"]["alternatives"])
            )
        }
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
    if not lists:
        # An empty conversation has no durable binding to authorize cached replay.
        return reply(
            "这段对话中没有这份待选航班清单。"
            if zh
            else "There is no open flight shortlist matching that request in this conversation.",
            flight_shortlist_chat=None,
        )
    if isinstance(choice, str):
        lists = {
            n: row
            for n, row in lists.items()
            if any(
                o["segment"]["flight"] == choice
                and (
                    not pin
                    or (
                        o.get("calendar_choice")
                        and FlightQuery.model_validate(o["calendar_choice"])
                        == pin.model_copy(update={"flight_number": choice})
                    )
                )
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
        },
    )


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
