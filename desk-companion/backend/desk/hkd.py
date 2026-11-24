"""Render an HKD minor-unit amount for a screen or Chinese speech."""

import re

DIGITS = "零一二三四五六七八九"
SMALL_UNITS = ("千", "百", "十", "")
MAX_MINOR = 10**9


def _group(value):
    out = ""
    for exponent, unit in zip((3, 2, 1, 0), SMALL_UNITS):
        digit, value = divmod(value, 10**exponent)
        if digit:
            out += DIGITS[digit] + unit
        elif out and value and not out.endswith("零"):
            out += "零"
    return out


def _whole(value):
    if not value:
        return "零"
    high, low = divmod(value, 10000)
    text = _group(high) + "万" if high else ""
    if high and 0 < low < 1000:
        text += "零"
    text += _group(low)
    return text[1:] if text.startswith("一十") else text


def amount(minor):
    """Return both presentations from the same validated shop/flight minor units."""
    if type(minor) is not int or not 0 <= minor <= MAX_MINOR:
        return None
    whole, cents = divmod(minor, 100)
    digits = f"{cents:02d}"
    fraction = "".join(DIGITS[int(c)] for c in digits.rstrip("0"))
    return {
        "minor": minor,
        "display": f"HK${whole:,}.{digits}",
        "spoken_zh": _whole(whole) + ("点" + fraction if fraction else "") + "港元",
    }


# Historical assistant captions may have a currency prefix, a second unit and mixed
# fractional units. Only explicitly named HKD is eligible. Preserve verbatim spans.
_CN = "零〇一二两兩三四五六七八九十百千万萬"
_WHOLE = rf"(?:[0-9]{{1,3}}(?:,[0-9]{{3}})+|[0-9]+|[{_CN}]+)"
_DIGIT = "0-9零〇一二两兩三四五六七八九"
_PREFIX = r"(?:港[币幣元]|HK\$|HKD)"
_SUFFIX = r"港[元币幣]"
_PART = rf"[{_DIGIT}][角毫](?:[{_DIGIT}][分仙])?|[{_DIGIT}][分仙]"
_TOKEN = re.compile(
    rf"(?<![A-Za-z0-9,.{_CN}点點])(?:(?P<prefix>{_PREFIX})[ \t]*)?"
    rf"(?P<whole>{_WHOLE})(?:[.点點](?P<decimal>[{_DIGIT}]{{1,2}}))?"
    rf"(?P<unit>{_SUFFIX}|[元圆圓蚊])?(?P<parts>{_PART})?(?![0-9{_CN}点點]|[.,][0-9])",
    re.I,
)
_VERBATIM = re.compile(r'(`[^`]*`|"[^"\n]*"|“[^”]*”|「[^」]*」|『[^』]*』)')
_SIMPLE = str.maketrans({"兩": "二", "两": "二", "〇": "零", "萬": "万"})


def _read_whole(token):
    token = token.translate(_SIMPLE)
    if token[0].isascii():
        digits = token.replace(",", "")
        return int(digits) if len(digits) <= 8 else None
    total = group = digit = 0
    for char in token:
        if char in DIGITS:
            digit = DIGITS.index(char)
        elif char == "万":
            total, group, digit = (group + digit) * 10000, 0, 0
        else:
            group += (digit or 1) * {"千": 1000, "百": 100, "十": 10}[char]
            digit = 0
    value = total + group + digit
    if value > MAX_MINOR // 100:
        return None
    canonical = _whole(value)
    return (
        value
        if token == canonical or (canonical.startswith("十") and token == "一" + canonical)
        else None
    )


def _digit(value):
    return int(value) if value.isascii() else DIGITS.index(value.translate(_SIMPLE))


def present_text(text, *, spoken=False):
    """Normalize assistant-generated, explicitly denominated amounts without changing stored inputs."""
    if not isinstance(text, str) or not any(tag in text.lower() for tag in ("港", "hk")):
        return text

    def replace(match):
        unit, decimal, parts = (match[name] for name in ("unit", "decimal", "parts"))
        if not match["prefix"] and (not unit or not unit.startswith("港")):
            return match[0]
        if parts and (not unit or decimal):
            return match[0]
        whole = _read_whole(match["whole"])
        if whole is None:
            return match[0]
        cents = 0
        if decimal:
            cents = _digit(decimal[0]) * 10 + (_digit(decimal[1]) if len(decimal) == 2 else 0)
        elif parts:
            cents = _digit(parts[0]) * (10 if parts[1] in "角毫" else 1)
            if len(parts) == 4:
                cents += _digit(parts[2])
        value = amount(whole * 100 + cents)
        return value["spoken_zh" if spoken else "display"] if value else match[0]

    pieces = _VERBATIM.split(text)
    return "".join(
        value if index % 2 else _TOKEN.sub(replace, value) for index, value in enumerate(pieces)
    )


def chinese(text):
    return isinstance(text, str) and bool(re.search(r"[\u3400-\u9fff]", text))


def display_message(text, *, streaming=False):
    if not chinese(text):
        return text
    # A partial prefix followed by "三千" is not yet a quote of HK$3,000.
    if streaming:
        partial = re.search(
            rf"(?:港[币幣元]|HK\$|HKD)[ \t.,{_CN}0-9元圆圓蚊点點角毫分仙]*$", text, re.I
        )
        if partial:
            text = text[: partial.start()]
    return present_text(text)


def asks_fare_amount(text):
    """Resolve only a reference to the current fare or a plain price follow-up."""
    if not chinese(text):
        return False
    name = r"(?:机票|機票|票价|票價|报价|報價|价格|價格|價錢|金额|金額|票|飛)"
    query = r"(?:多少钱|多少錢|幾多錢|几多钱|多少|幾多)"
    reference = r"(?:刚才|剛才|之前|上次|这个|這個|这张|這張|这趟|這趟|这班|這班|那张|那張|上一班|呢張|呢班)"
    return bool(
        re.fullmatch(
            rf"(?:请问|請問|所以|那|咁)?[，, ]*(?:{reference}(?:的|嘅)?)?(?:{name}(?:的|嘅)?{name}?)?"
            rf"(?:到底|一共|总共|總共|即係)?(?:是|要|係|系)?{query}[呢啊呀？?。！! ]*"
            rf"|(?:请|請|唔該|麻烦|麻煩)?(?:把|將)?(?:{reference}(?:的|嘅)?)?{name}"
            rf"(?:再念|再讀|再读|读下|讀下|再说|再說|再講)(?:一次|一遍|一下)?[。！! ]*"
            rf"|(?:请|請|唔該|麻烦|麻煩)?(?:再念|再讀|再读|读一下|讀一下|再说|再講|重复|重複)"
            rf"(?:一次|一遍|一下)?(?:{reference}(?:的|嘅)?)?{name}[。！! ]*",
            text.strip(),
        )
    )


def last_spoken_amount(text):
    """One unambiguous HKD amount in an earlier assistant turn, for repeating that turn only."""
    if not isinstance(text, str):
        return None
    found = set()
    for piece in _VERBATIM.split(text)[::2]:
        # Translate explicit legacy money using the same parser as the screen.
        for match in re.finditer(r"HK\$([0-9][0-9,]*)\.([0-9]{2})(?![0-9])", present_text(piece)):
            whole = match[1].replace(",", "")
            if len(whole) <= 8:
                found.add(int(whole) * 100 + int(match[2]))
    return amount(found.pop()) if len(found) == 1 else None


def asks_spoken_readback(text, *, previous_was_fare):
    """A bare 'say it again' refers to the immediately preceding answer."""
    if asks_fare_amount(text):
        return True
    if previous_was_fare and re.fullmatch(
        r"(?:请|請|唔該|麻烦|麻煩)?(?:再说一遍|再說一遍|再念一次|再读一遍|再讀一遍|再講一次)[？?。！! ]*",
        text.strip(),
    ):
        return True
    return bool(
        re.fullmatch(
            r"(?:刚才|剛才)?(?:的|嘅)?(?:机票|機票|航班|Kiwi)(?:的|嘅)?(?:查询|查詢|搜索|搜尋)?"
            r"(?:查到了吗|查好了没|查好了吗|有結果未|有結果嗎|結果點|结果呢|结果怎样)[？?。！! ]*",
            text.strip(),
            re.I,
        )
    )
