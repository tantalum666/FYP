"""Small synonym groups for recall. Built-in pairs plus rows the owner adds.

Matching is exact after case-folding and collapsed spaces. Overlapping groups
are one group at match time. No model call.
"""

from uuid import uuid4

from pydantic import Field, field_validator

from .schemas import StrictModel
from .store import DomainError

BUILTIN = (
    ("tea", "茶"),
    ("coffee", "咖啡"),
    ("report", "报告"),
    ("meeting", "会议"),
    ("name", "名字"),
)
_EDGE = ".,;:。，；：!！？?"


def normalize(value: str) -> str:
    return " ".join(str(value).casefold().split()).strip(_EDGE)


class AliasInput(StrictModel):
    terms: list[str] = Field(min_length=2, max_length=8)

    @field_validator("terms")
    @classmethod
    def readable(cls, value):
        cleaned = []
        for item in value:
            term = normalize(item)
            if not term or len(term) > 40:
                raise ValueError("Alias term is required")
            cleaned.append(term)
        if len(set(cleaned)) < 2:
            raise ValueError("Two different terms are required")
        return cleaned


def ensure(store) -> None:
    with store.connection(write=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_alias_terms("
            "term TEXT PRIMARY KEY, group_id TEXT NOT NULL)"
        )


def _merge(groups: list[set[str]]) -> list[set[str]]:
    pending = [set(group) for group in groups if group]
    merged: list[set[str]] = []
    while pending:
        current = pending.pop()
        changed = True
        while changed:
            changed = False
            rest = []
            for other in pending:
                if current & other:
                    current |= other
                    changed = True
                else:
                    rest.append(other)
            pending = rest
        merged.append(current)
    return merged


def stored_groups(store) -> list[dict]:
    with store.connection() as conn:
        rows = conn.execute(
            "SELECT term, group_id FROM memory_alias_terms ORDER BY group_id, term"
        ).fetchall()
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["group_id"], []).append(row["term"])
    return [{"id": group_id, "terms": terms, "builtin": False} for group_id, terms in grouped.items()]


def listing(store) -> dict:
    builtin = [
        {"id": "builtin:" + terms[0], "terms": list(terms), "builtin": True} for terms in BUILTIN
    ]
    return {"groups": builtin + stored_groups(store)}


def match_groups(store) -> list[set[str]]:
    custom = [set(group["terms"]) for group in stored_groups(store)]
    return _merge([set(terms) for terms in BUILTIN] + custom)


def _covers(token: str, term: str) -> bool:
    return token == term or token in term.split(" ")


def equivalents(token: str, groups: list[set[str]]) -> set[str]:
    """Exact terms, plus a word inside a multi-word term such as “earl grey”."""
    folded = normalize(token)
    found: set[str] = set()
    for group in groups:
        if any(_covers(folded, term) for term in group):
            found |= group
    if found:
        return found
    return {folded} if folded else set()


def add(store, terms: list[str], key: str) -> dict:
    def apply(conn):
        existing = {
            row["term"]: row["group_id"]
            for row in conn.execute("SELECT term, group_id FROM memory_alias_terms")
        }
        found = sorted({existing[term] for term in terms if term in existing})
        group_id = found[0] if found else uuid4().hex
        if found:
            marks = ",".join("?" for _ in found)
            conn.execute(
                f"UPDATE memory_alias_terms SET group_id=? WHERE group_id IN ({marks})",
                (group_id, *found),
            )
        for term in terms:
            conn.execute(
                "INSERT INTO memory_alias_terms(term, group_id) VALUES(?, ?) "
                "ON CONFLICT(term) DO UPDATE SET group_id=excluded.group_id",
                (term, group_id),
            )
        store.record(conn, "memory_alias_saved", details={"group_id": group_id})
        return {"group_id": group_id}

    saved = store.operation(key, {"type": "memory_alias", "terms": terms}, apply)
    return {**listing(store), **saved}


def remove(store, group_id: str, key: str) -> dict:
    if group_id.startswith("builtin:"):
        raise DomainError("ALIAS_BUILTIN", 422)

    def apply(conn):
        found = conn.execute(
            "SELECT 1 FROM memory_alias_terms WHERE group_id=?", (group_id,)
        ).fetchone()
        if not found:
            raise DomainError("ALIAS_NOT_FOUND", 404)
        conn.execute("DELETE FROM memory_alias_terms WHERE group_id=?", (group_id,))
        store.record(conn, "memory_alias_removed", details={"group_id": group_id})
        return {"removed": group_id}

    removed = store.operation(key, {"type": "memory_alias_remove", "group_id": group_id}, apply)
    return {**listing(store), **removed}
