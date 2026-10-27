"""Cite a saved fact by the day the owner saved it.

"Forget that" points at the one fact just cited. It prepares the existing
delete draft and does not delete. A question that is not about saved facts
returns None so the other local parsers still run.
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

_FORGET = re.compile(
    r"^(?:please\s+)?(?:forget\s+(?:that|this|it)|忘掉那个|忘掉这个|忘记那个|忘记这个)"
    r"\s*[.!?。！？]*$",
    re.I,
)
_RECALL_EN = re.compile(
    r"^(?:please\s+)?"
    r"(?:what do you remember(?: about)?"
    r"|what did i tell you(?: about)?"
    r"|what did i say(?: to you)?(?: about)?"
    r"|do you remember(?: about)?)"
    r"\s*(.*?)\s*[.!?]*$",
    re.I | re.S,
)
_RECALL_ZH = re.compile(
    r"^(?:请问)?(?:你还记得|你记得|我告诉过你|我说过什么)\s*(.*?)\s*[吗呢啊？?！!。]*$"
)
_STOP_EN = {"about", "the", "and", "you", "that", "this", "what", "please", "your"}
_STOP_ZH = {"什么", "关于", "那个", "这个", "一下", "吗", "呢"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SHOWN = 3


def ensure(store) -> None:
    with store.connection(write=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS recall_focus("
            "id INTEGER PRIMARY KEY CHECK(id=1), memory_id TEXT NOT NULL, cited_at TEXT NOT NULL)"
        )


def classify(text: str):
    """A forget-that or recall question, or None when another parser should run."""
    raw = text.strip()
    if _FORGET.match(raw):
        return {"name": "forget"}
    match = _RECALL_EN.match(raw) or _RECALL_ZH.match(raw)
    if not match:
        return None
    return {"name": "recall", "tokens": _tokens(match.group(1) or "")}


def _tokens(remainder: str) -> list[str]:
    text = re.sub(r"^(?:about|regarding|什么|关于|一下)\s*", "", remainder.strip(), flags=re.I)
    found = []
    for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text):
        low = word.casefold()
        if low not in _STOP_EN:
            found.append(low)
    for run in re.findall(r"[\u4e00-\u9fff]{1,16}", text):
        if run not in _STOP_ZH:
            found.append(run)
    return found


def zone_of(runtime) -> ZoneInfo:
    with runtime.store.connection() as conn:
        return ZoneInfo(runtime.store.settings(conn)["timezone"])


def spoken_day(created_at: str, zone: ZoneInfo, zh: bool) -> str:
    instant = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(zone)
    if zh:
        return f"{instant.year}年{instant.month}月{instant.day}日"
    return f"{instant.day} {_MONTHS[instant.month - 1]} {instant.year}"


def matching(runtime, tokens: list[str]) -> list[dict]:
    """Active facts whose wording contains every topic token. Newest first."""
    rows = runtime.memory.listing()["memories"]
    if not tokens:
        return rows
    chosen = []
    for row in rows:
        body = row["body"].casefold()
        if all(token.casefold() in body for token in tokens):
            chosen.append(row)
    return chosen


def render(rows: list[dict], tokens: list[str], zone: ZoneInfo, zh: bool) -> str:
    shown = rows[:_SHOWN]
    if not rows:
        if tokens:
            return "我没有保存过关于这件事的事实。" if zh else "I do not have a saved fact about that."
        return "还没有保存过事实。" if zh else "I do not have any saved facts yet."
    if len(rows) == 1:
        day = spoken_day(rows[0]["created_at"], zone, zh)
        if zh:
            return f"你在{day}告诉我：{rows[0]['body']}"
        return f"You told me on {day}: {rows[0]['body']}"
    lines = [
        f"- {spoken_day(row['created_at'], zone, zh)}：{row['body']}"
        if zh
        else f"- {spoken_day(row['created_at'], zone, zh)}: {row['body']}"
        for row in shown
    ]
    if zh:
        head = "你告诉过我不止一件事：" if tokens else "你告诉过我："
        extra = "其余的在记忆页。" if len(rows) > len(shown) else "请指出要忘掉的原文，或打开记忆页。"
    else:
        head = "You told me more than one fact about that:" if tokens else "You told me:"
        extra = (
            "Open Memory for the rest."
            if len(rows) > len(shown)
            else "Say which exact wording to forget, or open Memory."
        )
    return head + "\n" + "\n".join(lines) + "\n" + extra


def cited_id(store) -> str | None:
    with store.connection() as conn:
        row = conn.execute("SELECT memory_id FROM recall_focus WHERE id=1").fetchone()
    return row["memory_id"] if row else None


def set_focus(store, memory_id: str | None, at: str) -> None:
    """Remember the single cited fact. Several matches clear the pointer."""
    with store.connection(write=True) as conn:
        if memory_id is None:
            conn.execute("DELETE FROM recall_focus WHERE id=1")
            return
        conn.execute(
            "INSERT INTO recall_focus(id, memory_id, cited_at) VALUES(1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET memory_id=excluded.memory_id, cited_at=excluded.cited_at",
            (memory_id, at),
        )
