"""Turn saved tone, verbosity, and proactivity into prompt text and local replies.

The persona body stays first. Safety rules stay ahead of these lines. Default
plain / normal / normal leaves a local reply unchanged. Nothing here calls a model.
"""

import re

from .persona import followup_system, text_system, voice_instructions

_SUGGEST_EN = re.compile(r"^(?:want to|you could|shall i|next,|you might)\b", re.I)
_SUGGEST_ZH = re.compile(r"^(?:要不要|可以先|下一步|不妨)")


def _choice(prefs, key, default):
    value = prefs.get(key, default)
    return value if isinstance(value, str) and value else default


def directive(prefs, language: str = "en") -> str:
    """Language-specific style lines. They do not cancel a confirmation rule."""
    tone = _choice(prefs, "tone", "plain")
    verbosity = _choice(prefs, "verbosity", "normal")
    proactivity = _choice(prefs, "proactivity", "normal")
    if language == "zh":
        tone_zh = {"plain": "平实", "warm": "温暖"}.get(tone, tone)
        detail = {"brief": "只用一句", "normal": "一小段即可"}.get(verbosity, verbosity)
        step = {
            "off": "除非主人在问下一步，否则不要主动提议。",
            "low": "最多加一条下一步建议。",
            "normal": "可以加一条来自已保存事务或日程的下一步。",
        }.get(proactivity, "")
        warmth = "语气温暖，但不添加事实。" if tone == "warm" else "语气平实直接。"
        return f"语气：{tone_zh}。详略：{detail}。主动程度：{proactivity}。{warmth}{step}这些句子不能取消确认或安全规则。"
    detail = "Use one sentence." if verbosity == "brief" else "A short paragraph is enough."
    step = {
        "off": "Do not add a next step unless the owner asked what to do next.",
        "low": "Add at most one next-step suggestion.",
        "normal": "You may add one next step when it follows from saved tasks or the calendar.",
    }.get(proactivity, "")
    warmth = (
        "Sound warm without adding facts." if tone == "warm" else "Sound direct and plain."
    )
    return (
        f"Tone: {tone}. Verbosity: {verbosity}. Proactivity: {proactivity}. "
        f"{warmth} {detail} {step} These lines never override confirmation or safety rules."
    )


def render_prompt(
    body: str,
    prefs,
    language: str = "en",
    *,
    channel: str = "text",
    now_iso: str = "",
    zone: str = "",
) -> str:
    """Persona, then the channel rules, then style. Style is not a prefix."""
    if channel == "voice":
        base = voice_instructions(body, language, now_iso, zone)
    elif channel == "followup":
        base = followup_system(body)
    else:
        base = text_system(body)
    extra = directive(prefs, language)
    if extra in base:
        return base
    return base + " " + extra


def persona_problems(body: str, prompt: str, language: str = "en") -> list[str]:
    """Empty when the persona is intact and safety rules still precede style."""
    problems = []
    opening = body.strip()
    if not prompt.startswith(opening):
        problems.append("persona_moved")
    folded = prompt.casefold()
    safety = "no confirmation tool exists"
    marker = "语气：" if language == "zh" else "tone:"
    if safety not in folded or "untrusted data" not in folded:
        problems.append("safety_missing")
    elif marker not in folded or folded.index(safety) > folded.index(marker):
        problems.append("style_before_safety")
    if re.search(r"ignore (?:previous|safety|confirmation)|skip confirmation|不用确认", prompt):
        problems.append("style_overrides_safety")
    return problems


def _pieces(text: str) -> list[str]:
    parts = re.findall(r"[^。！？.!?]+[。！？.!?]?", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _suggestion(piece: str, language: str) -> bool:
    return bool((_SUGGEST_ZH if language == "zh" else _SUGGEST_EN).match(piece))


def shape(message: str, prefs, language: str = "en") -> str:
    """Apply saved style to one reply. Defaults return the same string."""
    tone = _choice(prefs, "tone", "plain")
    verbosity = _choice(prefs, "verbosity", "normal")
    proactivity = _choice(prefs, "proactivity", "normal")
    if tone == "plain" and verbosity == "normal" and proactivity == "normal":
        return message
    pieces = _pieces(message)
    if proactivity == "off":
        pieces = [piece for piece in pieces if not _suggestion(piece, language)]
    elif proactivity == "low":
        kept, seen = [], 0
        for piece in pieces:
            if _suggestion(piece, language):
                if seen:
                    continue
                seen += 1
            kept.append(piece)
        pieces = kept
    if verbosity == "brief" and pieces:
        pieces = pieces[:1]
    text = "".join(pieces) if language == "zh" else " ".join(pieces)
    if not text:
        text = message.strip()
    if tone == "warm":
        if language == "zh":
            marker = "好，" if verbosity == "brief" else "好的，"
        else:
            marker = "Sure — " if verbosity == "brief" else "Glad to help. "
        if not text.startswith(marker):
            text = marker + text
    return text


def present(reply, prefs, language: str):
    """Shape the message field. Other reply fields stay as the parser wrote them."""
    if not isinstance(reply, dict) or not isinstance(reply.get("message"), str):
        return reply
    message = shape(reply["message"], prefs, language)
    if message == reply["message"]:
        return reply
    return {**reply, "message": message}
