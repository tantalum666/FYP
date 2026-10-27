"""Owner-scoped read tools. Nothing here writes or approves a draft.

Search covers saved notes, tasks, calendar titles, and memory facts.
The plate is today's or this week's open work in the owner timezone.
The clock uses that same timezone and the runtime clock.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator

from .schemas import StrictModel
from .store import DomainError


Source = Literal["notes", "tasks", "calendar", "memory"]
_SOURCES: tuple[Source, ...] = ("notes", "tasks", "calendar", "memory")
_LIMIT = 8


class OwnerSearch(StrictModel):
    query: str = Field(min_length=1, max_length=80)
    sources: list[Source] = Field(default_factory=lambda: list(_SOURCES), min_length=1, max_length=4)

    @field_validator("query")
    @classmethod
    def compact_query(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("A search query is required")
        return text

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Name each source once")
        return value


class PlateQuery(StrictModel):
    window: Literal["today", "week"]


class OwnerClockArgs(StrictModel):
    pass


def owner_clock(runtime) -> dict:
    return {"saved": False, **_public(_bounds(runtime))}


def plate_summary(runtime, arguments: dict) -> dict:
    window = PlateQuery.model_validate(arguments).window
    bounds = _bounds(runtime)
    start, end = (bounds["today_start"], bounds["today_end"]) if window == "today" else (
        bounds["week_start_at"],
        bounds["week_end_at"],
    )
    snapshot = runtime.store.snapshot(start, end)
    tasks = _plate_tasks(runtime, start, end)
    occurrences = [
        {
            "id": item.get("id"),
            "title": item.get("title") or "",
            "start": item.get("start"),
            "end": item.get("end"),
            "redacted": bool(item.get("redacted")),
        }
        for item in snapshot["occurrences"][:12]
    ]
    return {
        "saved": False,
        "window": window,
        "timezone": bounds["timezone"],
        "start": bounds["today"] if window == "today" else bounds["week_start"],
        "end": bounds["today"] if window == "today" else bounds["week_end"],
        "tasks": tasks,
        "occurrences": occurrences,
    }


def owner_search(runtime, arguments: dict, *, allow_memory: bool = True) -> dict:
    parsed = OwnerSearch.model_validate(arguments)
    if "memory" in parsed.sources and not allow_memory:
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    matches = []
    if "notes" in parsed.sources:
        matches.extend(_notes(runtime, parsed.query))
    if "tasks" in parsed.sources:
        matches.extend(_tasks(runtime, parsed.query))
    if "calendar" in parsed.sources:
        matches.extend(_calendar(runtime, parsed.query))
    if "memory" in parsed.sources:
        matches.extend(_memory(runtime, parsed.query))
    return {"saved": False, "query": parsed.query, "matches": matches}


def _bounds(runtime) -> dict:
    with runtime.store.connection() as conn:
        name = runtime.store.settings(conn)["timezone"]
    zone = ZoneInfo(name)
    now = runtime.store.clock().astimezone(zone)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=today.weekday())
    return {
        "timezone": name,
        "now": now.isoformat(timespec="seconds"),
        "today": today.date().isoformat(),
        "weekday": now.strftime("%A"),
        "week_start": week.date().isoformat(),
        "week_end": (week + timedelta(days=6)).date().isoformat(),
        "today_start": today,
        "today_end": today + timedelta(days=1),
        "week_start_at": week,
        "week_end_at": week + timedelta(days=7),
    }


def _public(bounds: dict) -> dict:
    return {
        key: bounds[key]
        for key in ("timezone", "now", "today", "weekday", "week_start", "week_end")
    }


def _contains(value, query: str) -> bool:
    return query.casefold() in str(value or "").casefold()


def _snippet(value: str, limit: int = 80) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _notes(runtime, query: str) -> list[dict]:
    hits = []
    with runtime.store.connection() as conn:
        rows = conn.execute(
            "SELECT id, state, request FROM computer_jobs ORDER BY created_at DESC"
        ).fetchall()
    for row in rows:
        request = json.loads(row["request"])
        if request.get("action") != "save_note":
            continue
        title, content = request.get("title") or "", request.get("content") or ""
        if not (_contains(title, query) or _contains(content, query)):
            continue
        hits.append(
            {
                "source": "notes",
                "id": row["id"],
                "state": row["state"],
                "title": title,
                "snippet": _snippet(content),
            }
        )
        if len(hits) >= _LIMIT:
            break
    return hits


def _tasks(runtime, query: str) -> list[dict]:
    hits = []
    for task in runtime.tasks.listing(include_closed=True)["tasks"]:
        if task.get("redacted"):
            continue
        blob = " ".join(
            str(task.get(key) or "") for key in ("title", "next_step", "waiting_for")
        )
        if not _contains(blob, query):
            continue
        hits.append(
            {
                "source": "tasks",
                "id": task["id"],
                "title": task["title"],
                "status": task["status"],
                "due_local": task.get("due_local"),
            }
        )
        if len(hits) >= _LIMIT:
            break
    return hits


def _calendar(runtime, query: str) -> list[dict]:
    bounds = _bounds(runtime)
    start = bounds["today_start"] - timedelta(days=14)
    end = bounds["today_end"] + timedelta(days=45)
    hits = []
    for item in runtime.store.snapshot(start, end)["occurrences"]:
        if item.get("redacted"):
            continue
        blob = " ".join(str(item.get(key) or "") for key in ("title", "location", "notes"))
        if not _contains(blob, query):
            continue
        hits.append(
            {
                "source": "calendar",
                "id": item.get("id"),
                "title": item.get("title") or "",
                "start": item.get("start"),
                "end": item.get("end"),
            }
        )
        if len(hits) >= _LIMIT:
            break
    return hits


def _memory(runtime, query: str) -> list[dict]:
    hits = []
    for row in runtime.memory.for_model():
        if not _contains(row.get("body"), query):
            continue
        hits.append(
            {
                "source": "memory",
                "id": row["id"],
                "version": row["version"],
                "snippet": _snippet(row["body"], 160),
            }
        )
        if len(hits) >= _LIMIT:
            break
    return hits


def _plate_tasks(runtime, start: datetime, end: datetime) -> list[dict]:
    chosen = []
    for task in runtime.tasks.listing()["tasks"]:
        due = task.get("due_at")
        undated = due is None
        in_window = False
        if due:
            due_at = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(UTC)
            in_window = start.astimezone(UTC) <= due_at < end.astimezone(UTC)
        if not (in_window or task.get("overdue") or undated):
            continue
        chosen.append(
            {
                "id": task["id"],
                "title": "" if task.get("redacted") else task["title"],
                "due_at": due,
                "overdue": bool(task.get("overdue")),
                "undated": undated,
                "redacted": bool(task.get("redacted")),
            }
        )
        if len(chosen) >= 12:
            break
    return chosen
