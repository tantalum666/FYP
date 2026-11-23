"""Recognize a standalone city weather question; other requests keep the normal model route."""

import re
import unicodedata

from .tool_policy import execute_tool
from .weather_places import simplified

EN_QUESTION = re.compile(
    r"(?:(?:please\s+)?(?:can you\s+)?(?:check|tell me|show me)\s+|"
    r"(?:what(?:'s| is)|how(?:'s| is))\s+)?(?:the\s+)?"
    r"(?:weather(?:\s+forecast)?|forecast)(?:\s+like)?\s+(?:in|for|at)\s+"
    r"|will it (?:rain|snow)\s+(?:in|at)\s+",
    re.I,
)
ZH_QUESTION = re.compile(
    r"^(?:请问|请|麻烦)?(?:帮我|给我|替我)?(?:查一下|看一下|查一查|看看|查查|查询|查|看|告诉我)?"
    r"(?P<place>.+?)(?:的)?(?:天气(?:预报)?(?:怎么样|如何|怎样)?|会(?:不会)?下雨|下不下雨|有雨)"
    r"(?:吗|呢)?$"
)
RELATIVE = {
    "today": "today",
    "tomorrow": "tomorrow",
    "the day after tomorrow": "day_after_tomorrow",
    "今天": "today",
    "今日": "today",
    "明天": "tomorrow",
    "后天": "day_after_tomorrow",
}
# Do not send an unparsed second intent, private context reference or arbitrary sentence as a place name.
COMPOUND = re.compile(
    r"然后|再帮|顺便|以及|并且|还是|或者|相比|比较|根据|我的|图片|截图|画面|照片|邮件|日历|日程|\b(?:and|or|compare|my|if|with|where|please|because)\b",
    re.I,
)
CHINESE_NUMBERS = {n: i for i, n in enumerate("零一二三四五六七八九")}
UNPARSED_TIME = re.compile(
    r"下周|上周|星期|下星期|周[一二三四五六日]|未来|过去|(?:晚上|早上|下午)|\b(?:next|last|week|weeks|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|morning|afternoon|evening)\b",
    re.I,
)
PLACE = re.compile(r"[\w\s.,'’ʻ‘()\-]{1,90}", re.UNICODE)
DATE = r"\d{4}-\d{2}-\d{2}"


def direct_query(message):
    text = unicodedata.normalize("NFKC", message).strip().rstrip("。?？!！.").strip()
    if not text or len(text) > 160:
        return None
    count = None
    if "天气" in text or "天氣" in text or "雨" in text:
        match = ZH_QUESTION.fullmatch(simplified(text))
        if not match:
            return None
        language, place = "zh", match["place"].strip()
        span = re.search(
            r"(?:未来|接下来)?([1-9一二三四五六七八九])天$|(?:未来|接下来)?(?:一周|一个星期)$",
            place,
        )
        if span:
            value = span[1] or "七"
            count = int(value) if value.isascii() else CHINESE_NUMBERS[value]
            place = place[: span.start()].strip()
        day = re.match(rf"^(今天|今日|明天|后天|{DATE})", place)
        if day:
            place = place[day.end() :].strip()
        else:
            day = re.search(rf"(今天|今日|明天|后天|{DATE})$", place)
            if day:
                place = place[: day.start()].strip()
    else:
        match = EN_QUESTION.match(text.replace("’", "'"))
        if not match:
            return None
        language, place = "en", text[match.end() :].strip()
        span = re.search(r"\s+(?:for|over) (?:the )?(?:next |coming )?([1-9]) days?$", place, re.I)
        if span:
            count = int(span[1])
            place = place[: span.start()].strip()
        day = re.search(rf"\s+(the day after tomorrow|tomorrow|today|{DATE})$", place, flags=re.I)
        if day:
            place = place[: day.start()].strip()
    if (
        not PLACE.fullmatch(place)
        or COMPOUND.search(place)
        or UNPARSED_TIME.search(place)
        or re.search(r"[\u3400-\u9fff]{2,}[和与][\u3400-\u9fff]{2,}", place)
    ):
        return None
    if place.casefold() in {
        "here",
        "my location",
        "near me",
        "附近",
        "这里",
        "本地",
        "当地",
        "我这边",
    }:
        return None
    args = {"location": place, "language": language, "period": "today"}
    if count:
        args.update(period="forecast", start_date="today", days=count)
    if day:
        value = day[1].lower()
        args.update(start_date=RELATIVE.get(value, value), days=count or 1)
    return args


def answer_city_weather(runtime, payload, key, *, on_event=None):
    args = direct_query(payload.message)
    if args is None:
        return None
    if on_event:
        on_event({"type": "tool", "phase": "started", "tool": "weather_query"})
    result = execute_tool(
        runtime, "weather_query", args, key, scope=key, language=args["language"], channel="text"
    )
    if on_event:
        on_event(
            {
                "type": "tool",
                "phase": "finished",
                "tool": "weather_query",
                "outcome": result.get("error") or result.get("status") or "ok",
                "saved": False,
            }
        )
    message = result.get("summary") or (
        "暂时无法取得该地点的天气资料。"
        if args["language"] == "zh"
        else "I couldn't retrieve weather for that location."
    )
    return {"mode": "local_rules", "kind": "reply", "message": message}
