"""Deterministic memory review. No model call.

Exact wording, filler-normalized wording, two statements of the owner's name,
and preferences about the same subject become one suggestion. The owner still
confirms it through the existing draft. Nothing here writes a fact.
"""

import re

_EDGE = ".,;:。，；：!！"
_FILLER = re.compile(
    r"\b(?:always|really|just|very|quite)\b|一直|非常|真的|特别",
    re.I,
)
_PREFERENCE = re.compile(
    r"^(?:i (?:always |really |just |very )?prefer|我(?:一直|非常|真的)?更喜欢|我偏好)\s*(.+)$",
    re.I,
)
_NAME = re.compile(r"^(?:my name is|i am called|我叫|我的名字是)\s*(.+)$", re.I)
_SKIP = {"a", "an", "the"}


def review_suggestions(active, *, fact_key) -> list[dict]:
    """Groups the owner may keep or retire. Each fact is in at most one group."""
    remaining = list(active)
    suggestions: list[dict] = []

    def take(groups, kind: str, reason_en: str, reason_zh: str) -> None:
        nonlocal remaining
        used: set[str] = set()
        for facts in groups:
            if len(facts) < 2:
                continue
            ordered = sorted(facts, key=lambda item: (item["updated_at"], item["id"]), reverse=True)
            suggestions.append(
                {
                    "kind": kind,
                    "reason_en": reason_en,
                    "reason_zh": reason_zh,
                    "keep": ordered[0],
                    "retire": ordered[1:],
                }
            )
            used.update(item["id"] for item in facts)
        remaining = [item for item in remaining if item["id"] not in used]

    take(
        _groups(remaining, lambda item: fact_key(item["body"]), minimum=2),
        "duplicate",
        "These facts use the same wording. You can keep the newest and retire the others.",
        "这些事实文字相同。可以保留最新的一条，并停用其余几条。",
    )
    take(
        [
            group
            for group in _groups(remaining, lambda item: normalized_key(item["body"], fact_key))
            if len({fact_key(item["body"]) for item in group}) > 1
        ],
        "normalized",
        "These facts read as the same statement once filler words such as “always” or “really” are ignored. You can keep the newest.",
        "去掉“一直”“非常”这类填充词后，这些事实说的是同一件事。可以保留最新的一条。",
    )
    named = [(identity_name(item["body"]), item) for item in remaining]
    named = [(name, item) for name, item in named if name]
    if len(named) >= 2:
        same = len({fact_key(name) for name, _ in named}) == 1
        take(
            [[item for _, item in named]],
            "normalized" if same else "identity",
            "Both state the same name. You can keep the newest wording."
            if same
            else "Both state your name. The newer statement can replace the older one.",
            "两者说的是同一个名字。可以保留最新的写法。"
            if same
            else "两者都在说你的名字。较新的一句可以取代较早的一句。",
        )
    clusters = _preference_clusters(remaining)
    for cluster in clusters:
        subject = cluster[0][0]["subject"]
        take(
            [[item for _, item in cluster]],
            "preference",
            (
                f"These preferences are about the same subject (“{subject}”). "
                "The newer one can replace the older."
            ),
            f"这些偏好说的是同一主题（“{subject}”）。较新的一条可以取代较早的。",
        )
    return suggestions


def suggestion_matches(active, keep_id: str, retire_ids: list[str], *, fact_key) -> bool:
    """True when this keep/retire set is still one current suggestion."""
    wanted = set(retire_ids)
    return any(
        item["keep"]["id"] == keep_id and {row["id"] for row in item["retire"]} == wanted
        for item in review_suggestions(active, fact_key=fact_key)
    )


def normalized_key(body: str, fact_key) -> str:
    """fact_key after filler words are removed. The stored sentence is unchanged."""
    text = _FILLER.sub(" ", fact_key(body))
    return fact_key(" ".join(text.split()))


def identity_name(body: str) -> str | None:
    match = _NAME.match(_folded(body))
    if not match:
        return None
    name = match.group(1).strip().strip(_EDGE).strip()
    return name or None


def preference_of(body: str) -> dict | None:
    match = _PREFERENCE.match(_folded(body))
    if not match:
        return None
    raw = match.group(1).strip().strip(_EDGE)
    words = [word.strip(_EDGE) for word in raw.split()]
    words = [word for word in words if word and word not in _SKIP]
    if not words:
        return None
    head = words[0]
    cjk = bool(re.search(r"[\u4e00-\u9fff]", head))
    if not cjk and len(head) < 3:
        return None
    return {"object": " ".join(words), "subject": head}


def _preference_clusters(facts) -> list[list[tuple[dict, dict]]]:
    clusters: list[list[tuple[dict, dict]]] = []
    for fact in facts:
        parsed = preference_of(fact["body"])
        if not parsed:
            continue
        placed = False
        for cluster in clusters:
            if any(_same_subject(parsed, other) for other, _ in cluster):
                cluster.append((parsed, fact))
                placed = True
                break
        if not placed:
            clusters.append([(parsed, fact)])
    return [cluster for cluster in clusters if len(cluster) >= 2]


def _same_subject(left: dict, right: dict) -> bool:
    if left["subject"] == right["subject"]:
        return True
    left_words, right_words = left["object"].split(), right["object"].split()
    if len(left_words) == 1 and len(right_words) == 1:
        short, long = sorted((left["object"], right["object"]), key=len)
        cjk = bool(re.search(r"[\u4e00-\u9fff]", short))
        return bool(cjk and short != long and (long.startswith(short) or long.endswith(short)))
    short, long = (
        (left_words, right_words)
        if len(left_words) <= len(right_words)
        else (right_words, left_words)
    )
    return long[: len(short)] == short or long[-len(short) :] == short


def _groups(facts, key, minimum=2):
    grouped: dict[str, list] = {}
    for fact in facts:
        grouped.setdefault(key(fact), []).append(fact)
    return [group for group in grouped.values() if len(group) >= minimum]


def _folded(body: str) -> str:
    return " ".join(body.casefold().split())
