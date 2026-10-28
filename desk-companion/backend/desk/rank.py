"""Deterministic overlap ranking. No extra packages.

Latin words are casefolded. A run of Chinese characters contributes each
character and each adjacent pair. Newer rows win ties. A row with more query
tokens still beats a newer row with fewer.
"""

import re


_TOKEN = re.compile(r"[A-Za-z0-9]+|[\u3400-\u9fff]+")


def tokens(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for match in _TOKEN.finditer(text or ""):
        piece = match.group()
        if "\u3400" <= piece[0] <= "\u9fff":
            found.extend(piece)
            found.extend(piece[index : index + 2] for index in range(len(piece) - 1))
        else:
            found.append(piece.casefold())
    return tuple(found)


def rank_rows(query: str, rows: list[dict], *, limit: int) -> list[dict]:
    """Return payloads, best first.

    Each row has ``text``, ``time`` (ISO text or empty), ``id``, and ``payload``.
    Score 0 is dropped. The order is stable for the same inputs.
    """
    unique = list(dict.fromkeys(tokens(query)))
    if not unique or limit < 1:
        return []
    ordered = sorted(
        rows,
        key=lambda row: (str(row.get("time") or ""), str(row.get("id") or "")),
        reverse=True,
    )
    scored = []
    for age, row in enumerate(ordered):
        counts: dict[str, int] = {}
        for token in tokens(str(row.get("text") or "")):
            counts[token] = counts.get(token, 0) + 1
        matched = [token for token in unique if token in counts]
        if not matched:
            continue
        overlap = len(matched) * 1000 + sum(min(counts[token] - 1, 3) for token in matched)
        score = overlap + 200 // (1 + age)
        scored.append((score, age, str(row.get("id") or ""), row["payload"]))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in scored[:limit]]
