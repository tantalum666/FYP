"""One local answer when the owner asks whether a time is open.

The question is read from the saved calendar in the owner timezone. An opening
is a gap on that calendar, not a claim the owner is actually free. Nothing is
created, moved, or booked, and no model is called. Quiet hours and a low
proactivity setting still answer, because the owner asked.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MIN_OPEN = timedelta(minutes=30)
_PARTS = {
    "morning": ((8, 0), (12, 0)),
    "afternoon": ((12, 0), (18, 0)),
    "evening": ((18, 0), (21, 0)),
}
_ZH_PARTS = {"上午": "morning", "下午": "afternoon", "晚上": "evening"}
_EN_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_ZH_WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_WEEKDAY_EN = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_END = r"\s*[.!?。！？?]*$"
_WD = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_PART = r"morning|afternoon|evening"


def parse_ask(text: str):
    """A day, an optional part of the day, and an optional clock, or None.

    Trailing punctuation is not part of the question. A clock or a day word
    must not swallow it, or "tomorrow?" would miss the calendar day.
    """
    raw = text.strip()
    raw = re.sub(r"[\s.!?。！？?]+$", "", raw).strip()
    if not raw:
        return None
    for parser in (_en_point, _zh_point, _en_window, _zh_window):
        found = parser(raw)
        if found is not None:
            return found
    return None


def answer_open_time(runtime, request, *, owner: bool = True):
    """A spoken opening, or None when this message is a different request."""
    parsed = parse_ask(request.message)
    if parsed is None:
        return None
    zh = request.language == "zh"
    zone = _zone(runtime)
    now = runtime.store.clock().astimezone(zone).replace(second=0, microsecond=0)
    day = _resolve_day(now.date(), parsed)
    start, end = _window(day, parsed["part"], zone)
    instant = None
    if parsed["instant"] is not None:
        hour, minute = parsed["instant"]
        instant = start.replace(hour=hour, minute=minute)
    body = _answer(runtime, zone, now, day, start, end, instant, owner=owner, zh=zh)
    return {
        "mode": "local_rules",
        "kind": "open_time",
        "saved": False,
        "acted": False,
        "message": body["message"],
        "open_time": body["open_time"],
    }


def _en_point(raw: str):
    patterns = (
        rf"^when am i free\s+(.+?)\s+at\s+(.+?){_END}",
        rf"^am i free\s+(.+?)\s+at\s+(.+?){_END}",
        rf"^does\s+(.+?)\s+at\s+(.+?)\s+work{_END}",
        rf"^is\s+(.+?)\s+(.+?)\s+open{_END}",
        rf"^can i meet\s+(.+?)\s+at\s+(.+?){_END}",
    )
    for index, pattern in enumerate(patterns):
        match = re.fullmatch(pattern, raw, re.I)
        if not match:
            continue
        if index == 3:
            clock, when = match.group(1), match.group(2)
        else:
            when, clock = match.group(1), match.group(2)
        parsed = _en_when(when)
        instant = _en_clock(clock)
        if parsed is None or instant is None:
            return None
        return {**parsed, "instant": instant}
    return None


def _en_window(raw: str):
    match = re.fullmatch(rf"(?:when am i free|am i free)(?:\s+(.+))?{_END}", raw, re.I)
    if not match or not match.group(1):
        if match:
            return {"relative": "today", "part": None, "weekday": None, "nxt": False, "instant": None}
        return None
    parsed = _en_when(match.group(1))
    if parsed is None:
        return None
    return {**parsed, "instant": None}


def _en_when(text: str):
    folded = " ".join(text.strip().lower().split())
    if folded in {"today", "tomorrow"}:
        return {"relative": folded, "part": None, "weekday": None, "nxt": False}
    match = re.fullmatch(rf"(today|tomorrow|this)\s+({_PART})", folded)
    if match:
        relative = "today" if match.group(1) == "this" else match.group(1)
        return {"relative": relative, "part": match.group(2), "weekday": None, "nxt": False}
    match = re.fullmatch(rf"(?:on\s+)?(?:(next)\s+)?({_WD})(?:\s+({_PART}))?", folded)
    if match:
        return {
            "relative": "weekday",
            "part": match.group(3),
            "weekday": _EN_WEEKDAYS[match.group(2)],
            "nxt": bool(match.group(1)),
        }
    return None


def _en_clock(text: str):
    token = "".join(text.strip().lower().split())
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", token)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.fullmatch(r"([1-9]|1[0-2])(?::([0-5]\d))?(am|pm)", token)
    if not match:
        return None
    hour = int(match.group(1)) % 12
    if match.group(3) == "pm":
        hour += 12
    return hour, int(match.group(2) or 0)


def _zh_point(raw: str):
    match = re.fullmatch(
        rf"^(今天|明天|(下周|下星期|下礼拜)?(?:周|星期|礼拜)([一二三四五六日天]))"
        rf"(上午|下午|晚上)?\s*"
        rf"(\d{{1,2}})(?::([0-5]\d)|点(?:([0-5]\d)分?)?)?"
        rf"\s*(?:可以吗|行吗|有空吗){_END}",
        raw,
    )
    if not match:
        return None
    day, nxt, weekday, part, hour_text, minute_colon, minute_dian = match.groups()
    hour = int(hour_text)
    minute = int(minute_colon or minute_dian or 0)
    if part in {"下午", "晚上"} and hour < 12:
        hour += 12
    elif part == "上午" and hour == 12:
        hour = 0
    if hour > 23:
        return None
    if day == "今天":
        relative, weekday_index, nxt_flag = "today", None, False
    elif day == "明天":
        relative, weekday_index, nxt_flag = "tomorrow", None, False
    else:
        relative, weekday_index, nxt_flag = "weekday", _ZH_WEEKDAYS[weekday], bool(nxt)
    return {
        "relative": relative,
        "part": _ZH_PARTS.get(part),
        "weekday": weekday_index,
        "nxt": nxt_flag,
        "instant": (hour, minute),
    }


def _zh_relative(token: str | None) -> str:
    return {"今天": "today", "明天": "tomorrow"}.get(token or "", "today")


def _zh_window(raw: str):
    match = re.fullmatch(rf"^我(今天|明天)?什么时候有空{_END}", raw)
    if match:
        return {
            "relative": _zh_relative(match.group(1)),
            "part": None,
            "weekday": None,
            "nxt": False,
            "instant": None,
        }
    match = re.fullmatch(rf"^(今天|明天)有空吗{_END}", raw)
    if match:
        return {
            "relative": _zh_relative(match.group(1)),
            "part": None,
            "weekday": None,
            "nxt": False,
            "instant": None,
        }
    match = re.fullmatch(rf"^(今天|明天)(上午|下午|晚上)有空吗{_END}", raw)
    if match:
        return {
            "relative": _zh_relative(match.group(1)),
            "part": _ZH_PARTS[match.group(2)],
            "weekday": None,
            "nxt": False,
            "instant": None,
        }
    match = re.fullmatch(
        rf"^(下周|下星期|下礼拜)?(?:周|星期|礼拜)([一二三四五六日天])(?:什么时候有空|有空吗){_END}",
        raw,
    )
    if match:
        return {
            "relative": "weekday",
            "part": None,
            "weekday": _ZH_WEEKDAYS[match.group(2)],
            "nxt": bool(match.group(1)),
            "instant": None,
        }
    return None


def _resolve_day(today, parsed):
    if parsed["relative"] == "tomorrow":
        return today + timedelta(days=1)
    if parsed["relative"] == "weekday":
        ahead = (parsed["weekday"] - today.weekday()) % 7
        soonest = today + timedelta(days=ahead)
        if parsed["nxt"]:
            return soonest + timedelta(days=7)
        return soonest
    return today


def _window(day, part, zone: ZoneInfo):
    start_hm, end_hm = _PARTS.get(part, ((8, 0), (21, 0)))
    start = datetime(day.year, day.month, day.day, start_hm[0], start_hm[1], tzinfo=zone)
    end = datetime(day.year, day.month, day.day, end_hm[0], end_hm[1], tzinfo=zone)
    return start, end


def _zone(runtime) -> ZoneInfo:
    with runtime.store.connection() as conn:
        return ZoneInfo(runtime.store.settings(conn)["timezone"])


def _answer(runtime, zone, now, day, start, end, instant, *, owner: bool, zh: bool):
    if instant is not None and (instant < start or instant >= end):
        return _outside(day, now, zone, start, end, instant, zh)
    if instant is not None and instant < now:
        return _passed_instant(day, now, zone, instant, zh)
    if instant is None and end <= now:
        return _passed_window(day, now, zone, start, end, zh)
    search_start = start
    if instant is None and start < now < end:
        search_start = now
    blocks = _blocks(runtime, zone, start, end, owner=owner)
    if instant is not None:
        return _instant_answer(day, now, zone, instant, end, blocks, zh)
    return _window_answer(day, now, zone, start, end, search_start, blocks, zh)


def _blocks(runtime, zone, start, end, *, owner: bool):
    occurrences = runtime.store.snapshot(start, end)["occurrences"]
    raw = []
    for occurrence in occurrences:
        if occurrence.get("completed") or occurrence.get("busy", True) is False:
            continue
        block_start = _parse(occurrence["start"]).astimezone(zone)
        block_end = _parse(occurrence["end"]).astimezone(zone)
        if block_end <= start or block_start >= end:
            continue
        label, private = _label(occurrence, owner)
        raw.append(
            {
                "start": max(block_start, start),
                "end": min(block_end, end),
                "label": label,
                "private": private,
                "all_day": bool(occurrence.get("all_day")),
            }
        )
    raw.sort(key=lambda block: (block["start"], block["end"]))
    merged = []
    for block in raw:
        if block["end"] <= block["start"]:
            continue
        if merged and block["start"] <= merged[-1]["end"]:
            current = merged[-1]
            current["end"] = max(current["end"], block["end"])
            current["all_day"] = current["all_day"] or block["all_day"]
            current["names"].extend(_names(block))
        else:
            merged.append({**block, "names": _names(block)})
    return merged


def _label(occurrence, owner: bool):
    private = occurrence.get("visibility") == "private" or bool(occurrence.get("redacted"))
    if private and (occurrence.get("redacted") or not owner):
        return "", True
    title = " ".join(str(occurrence.get("title") or "").split())
    return title, False


def _names(block):
    if block["private"] or not block["label"]:
        return ["private"]
    return [block["label"]]


def _window_answer(day, now, zone, start, end, search_start, blocks, zh):
    covering = [
        block
        for block in blocks
        if block["all_day"] and block["start"] <= search_start and block["end"] >= end
    ]
    if covering:
        return _payload(
            day,
            now,
            zone,
            start,
            end,
            None,
            [],
            covering,
            _all_day_sentence(day, now, zone, covering, zh),
            zh,
            filled=True,
        )
    openings, shorts = _gaps(search_start, end, blocks)
    if openings:
        return _payload(
            day,
            now,
            zone,
            start,
            end,
            None,
            openings,
            [],
            _open_sentence(day, now, zone, openings, zh),
            zh,
            filled=False,
        )
    return _payload(
        day,
        now,
        zone,
        start,
        end,
        None,
        [],
        blocks,
        _filled_sentence(day, now, zone, end, search_start, blocks, shorts, zh),
        zh,
        filled=True,
    )


def _instant_answer(day, now, zone, instant, end, blocks, zh):
    hit = [block for block in blocks if block["start"] <= instant < block["end"]]
    if hit:
        until = max(block["end"] for block in hit)
        return _payload(
            day,
            now,
            zone,
            instant,
            end,
            instant,
            [],
            hit,
            _overlap_sentence(day, now, zone, instant, until, hit, zh),
            zh,
            filled=True,
        )
    until = end
    for block in blocks:
        if block["start"] > instant:
            until = block["start"]
            break
    return _payload(
        day,
        now,
        zone,
        instant,
        end,
        instant,
        [(instant, until)],
        [],
        _point_open_sentence(day, now, zone, instant, until, zh),
        zh,
        filled=False,
    )


def _gaps(search_start, end, blocks):
    openings, shorts = [], []
    cursor = search_start
    for block in blocks:
        if block["end"] <= cursor:
            continue
        if block["start"] > cursor:
            _keep_gap(openings, shorts, cursor, block["start"])
        cursor = max(cursor, block["end"])
    if cursor < end:
        _keep_gap(openings, shorts, cursor, end)
    return openings, shorts


def _keep_gap(openings, shorts, start, end):
    if end - start >= MIN_OPEN:
        openings.append((start, end))
    elif end - start >= timedelta(minutes=1):
        shorts.append((start, end))


def _payload(day, _now, zone, start, end, instant, openings, overlaps, message, _zh, *, filled):
    return {
        "message": message,
        "open_time": {
            "date": day.isoformat(),
            "timezone": zone.key,
            "window": {"start": _hm(start), "end": _hm(end)},
            "query": "instant" if instant is not None else "window",
            "instant": None if instant is None else _hm(instant),
            "openings": [{"start": _hm(item[0]), "end": _hm(item[1])} for item in openings],
            "overlaps": [_overlap(block) for block in overlaps],
            "booked": False,
            "filled": filled,
        },
    }


def _overlap(block):
    # A merged block can mix a private event with a named one. The private
    # title is never copied out.
    labels = [name for name in _unique(block.get("names", [])) if name != "private"]
    hidden = "private" in block.get("names", [])
    return {
        "start": _hm(block["start"]),
        "end": _hm(block["end"]),
        "private": hidden and not labels,
        "labels": labels,
    }


def _open_sentence(day, now, zone, openings, zh):
    spans = _span_list(openings, zh)
    named = _named(day, now.date(), zh)
    if zh:
        return (
            f"{named}（{zone.key}）在已保存的日历上有空 {spans}；"
            "空档不等于你本人有空，也没有写入任何日程。"
        )
    return (
        f"{named} ({zone.key}) is open {spans} on the saved calendar; "
        "an open stretch is not a claim that you are free, and nothing was booked."
    )


def _point_open_sentence(day, now, zone, instant, until, zh):
    named = _named(day, now.date(), zh)
    if zh:
        return (
            f"{named}（{zone.key}）的 {_hm(instant)} 在已保存的日历上有空，直到 {_hm(until)}；"
            "空档不等于你本人有空，也没有写入任何日程。"
        )
    return (
        f"{named} ({zone.key}) at {_hm(instant)} is open on the saved calendar until {_hm(until)}; "
        "an open time is not a claim that you are free, and nothing was booked."
    )


def _overlap_sentence(day, now, zone, instant, until, blocks, zh):
    named = _named(day, now.date(), zh)
    labels = _spoken([name for block in blocks for name in block["names"]], zh)
    if zh:
        return (
            f"{named}（{zone.key}）的 {_hm(instant)} 与{labels}重叠，直到 {_hm(until)}；"
            "没有写入任何日程。"
        )
    return (
        f"{named} ({zone.key}) at {_hm(instant)} overlaps {labels}, which runs until {_hm(until)}; "
        "nothing was booked."
    )


def _filled_sentence(day, now, zone, end, search_start, blocks, shorts, zh):
    named = _named(day, now.date(), zh)
    labels = _spoken([name for block in blocks for name in block["names"]], zh)
    if shorts:
        longest = max(shorts, key=lambda item: item[1] - item[0])
        span = f"{_hm(longest[0])}–{_hm(longest[1])}"
        if zh:
            return (
                f"{named}（{zone.key}）在已保存的日历上没有至少30分钟的空档，"
                f"最长的一段是 {span}（{labels}）；空档不等于你本人有空，也没有写入任何日程。"
            )
        return (
            f"{named} ({zone.key}) has no opening of at least 30 minutes on the saved calendar; "
            f"the longest open stretch is {span} ({labels}); "
            "an open stretch is not a claim that you are free, and nothing was booked."
        )
    if zh:
        return (
            f"{named}（{zone.key}）在已保存的日历上 {_hm(search_start)}–{_hm(end)} 已排满"
            f"（{labels}）；没有写入任何日程。"
        )
    return (
        f"{named} ({zone.key}) is filled {_hm(search_start)}–{_hm(end)} on the saved calendar "
        f"({labels}); nothing was booked."
    )


def _all_day_sentence(day, now, zone, blocks, zh):
    named = _named(day, now.date(), zh)
    labels = _spoken([name for block in blocks for name in block["names"]], zh)
    if zh:
        return f"{named}（{zone.key}）在已保存的日历上被{labels}占满全天；没有写入任何日程。"
    return (
        f"{named} ({zone.key}) is blocked all day by {labels} on the saved calendar; "
        "nothing was booked."
    )


def _passed_window(day, now, zone, start, end, zh):
    message = (
        f"{_named(day, now.date(), zh)}（{zone.key}）的 {_part_name(start, end, zh)} "
        f"{_hm(start)}–{_hm(end)} 已经过去；没有写入任何日程。"
        if zh
        else (
            f"{_named(day, now.date(), zh)} ({zone.key}), {_hm(start)}–{_hm(end)}, "
            "has already passed, and nothing was booked."
        )
    )
    return _payload(day, now, zone, start, end, None, [], [], message, zh, filled=True)


def _passed_instant(day, now, zone, instant, zh):
    message = (
        f"{_named(day, now.date(), zh)}（{zone.key}）的 {_hm(instant)} 已经过去；没有写入任何日程。"
        if zh
        else (
            f"{_hm(instant)} on {_named(day, now.date(), zh)} ({zone.key}) "
            "has already passed, and nothing was booked."
        )
    )
    return _payload(day, now, zone, instant, instant, instant, [], [], message, zh, filled=True)


def _outside(day, now, zone, start, end, instant, zh):
    message = (
        f"{_hm(instant)} 不在 {_named(day, now.date(), zh)}（{zone.key}）的 "
        f"{_part_name(start, end, zh)} {_hm(start)}–{_hm(end)} 里；没有写入任何日程。"
        if zh
        else (
            f"{_hm(instant)} is outside {_hm(start)}–{_hm(end)} on "
            f"{_named(day, now.date(), zh)} ({zone.key}), and nothing was booked."
        )
    )
    return _payload(day, now, zone, start, end, instant, [], [], message, zh, filled=False)


def _part_name(start, end, zh):
    key = ((start.hour, start.minute), (end.hour, end.minute))
    names = {
        ((8, 0), (12, 0)): ("上午", "the morning"),
        ((12, 0), (18, 0)): ("下午", "the afternoon"),
        ((18, 0), (21, 0)): ("晚上", "the evening"),
    }
    zh_name, en_name = names.get(key, ("这段时间", "that window"))
    return zh_name if zh else en_name


def _named(day, today, zh: bool) -> str:
    if zh:
        absolute = f"{day.year}年{day.month}月{day.day}日"
        if day == today:
            head = "今天"
        elif day == today + timedelta(days=1):
            head = "明天"
        else:
            head = "周" + "一二三四五六日"[day.weekday()]
        return f"{head} {absolute}"
    absolute = f"{day.day} {_MONTHS[day.month - 1]} {day.year}"
    if day == today:
        head = "Today"
    elif day == today + timedelta(days=1):
        head = "Tomorrow"
    else:
        head = _WEEKDAY_EN[day.weekday()]
    return f"{head} {absolute}"


def _spoken(names, zh: bool) -> str:
    unique = _unique(names)
    private = "private" in unique
    shown = [name for name in unique if name != "private"][:3]
    if private:
        shown.append("一项私人日程" if zh else "a private event")
    if not shown:
        return "一项日程" if zh else "an event"
    if len(shown) == 1:
        return shown[0]
    if zh:
        return "、".join(shown)
    return ", ".join(shown[:-1]) + " and " + shown[-1]


def _span_list(openings, zh: bool) -> str:
    spans = [f"{_hm(start)}–{_hm(end)}" for start, end in openings]
    if len(spans) == 1:
        return spans[0]
    if zh:
        return "、".join(spans[:-1]) + " 和 " + spans[-1]
    if len(spans) == 2:
        return f"{spans[0]} and {spans[1]}"
    return ", ".join(spans[:-1]) + ", and " + spans[-1]


def _unique(names):
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def _hm(value: datetime) -> str:
    return value.strftime("%H:%M")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
