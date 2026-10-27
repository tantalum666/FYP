"""A short profile built only from confirmed memory and open goals.

The text is deterministic: same facts, same lines, no model call. It stops at
a character budget. The owner can leave a fact out of this summary without
deleting it.
"""

import re

from fastapi import APIRouter, Depends
from pydantic import Field

from .schemas import StrictModel

BUDGET = 800
MAX_LINES = 12
_ORDER = ("identity", "preferences", "people", "routines", "projects")
_LABELS = {
    "identity": "Identity",
    "preferences": "Preferences",
    "people": "People",
    "routines": "Routines",
    "projects": "Projects",
}
_PEOPLE = re.compile(
    r"\b(sister|brother|mother|father|friend|colleague|partner)\b",
    re.I,
)


def classify(fact: dict) -> str:
    """Which profile line a confirmed fact belongs on. Empty means leave it out."""
    note = fact.get("note") or ""
    body = fact.get("body") or ""
    low = body.casefold()
    if note == "identity" or low.startswith("my name is") or body.startswith("我叫"):
        return "identity"
    if note == "preference" or "prefer" in low or "喜欢" in body:
        return "preferences"
    if note == "person" or _PEOPLE.search(body) or any(word in body for word in ("妈妈", "爸爸", "同事", "朋友")):
        return "people"
    if note == "routine" or low.startswith("every ") or "每天" in body or "每个" in body:
        return "routines"
    if note == "project" or "project" in low or "项目" in body:
        return "projects"
    return ""


def assemble(facts: list[dict], goals: list[dict], omitted: set[str]) -> dict:
    """Stable lines inside the budget. Later groups are dropped before earlier ones."""
    groups = {key: [] for key in _ORDER}
    included = []
    for fact in sorted(facts, key=lambda item: item["id"]):
        if fact["id"] in omitted:
            continue
        kind = classify(fact)
        if not kind:
            continue
        groups[kind].append(fact["body"])
        included.append({"id": fact["id"], "body": fact["body"], "group": kind})
    for goal in sorted(goals, key=lambda item: (item.get("title") or "", item.get("id") or "")):
        if goal.get("state") == "closed":
            continue
        title = goal.get("title") or ""
        if title:
            groups["projects"].append(title)
    lines = []
    for key in _ORDER:
        if not groups[key]:
            continue
        lines.append(_LABELS[key] + ": " + "; ".join(groups[key]))
    kept = []
    for line in lines:
        candidate = "\n".join(kept + [line])
        if len(kept) >= MAX_LINES or len(candidate) > BUDGET:
            break
        kept.append(line)
    text = "\n".join(kept)
    return {"text": text, "lines": kept, "included": included, "budget": BUDGET}


class ProfileOmission(StrictModel):
    memory_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class ProfileService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS profile_omissions(memory_id TEXT PRIMARY KEY)"
            )

    def _omitted(self, conn) -> set[str]:
        return {row["memory_id"] for row in conn.execute("SELECT memory_id FROM profile_omissions")}

    def view(self) -> dict:
        facts = self.runtime.memory.listing()["memories"]
        goals = self.runtime.goals.listing()["goals"]
        with self.store.connection() as conn:
            omitted = self._omitted(conn)
        summary = assemble(facts, goals, omitted)
        summary["omitted"] = sorted(omitted)
        return summary

    def text(self) -> str:
        return self.view()["text"]

    def omit(self, memory_id: str, key: str) -> dict:
        def apply(conn):
            conn.execute("INSERT OR IGNORE INTO profile_omissions VALUES(?)", (memory_id,))
            self.store.record(conn, "profile_omit", details={"memory_id": memory_id})
            return {"saved": True}

        self.store.operation(key, {"type": "profile_omit", "id": memory_id}, apply)
        return self.view()

    def restore(self, memory_id: str, key: str) -> dict:
        def apply(conn):
            conn.execute("DELETE FROM profile_omissions WHERE memory_id=?", (memory_id,))
            self.store.record(conn, "profile_restore", details={"memory_id": memory_id})
            return {"saved": True}

        self.store.operation(key, {"type": "profile_restore", "id": memory_id}, apply)
        return self.view()


def profile_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/profile", dependencies=[Depends(owner)])

    @router.get("")
    def view():
        return runtime.profile.view()

    @router.post("/omissions")
    def omit(payload: ProfileOmission, key=Depends(operation_id)):
        return runtime.profile.omit(payload.memory_id, key)

    @router.post("/omissions/{memory_id}/restorations")
    def restore(memory_id: str, key=Depends(operation_id)):
        return runtime.profile.restore(memory_id, key)

    return router
