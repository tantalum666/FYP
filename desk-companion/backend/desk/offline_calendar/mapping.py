"""Map one offline event or series onto the existing task and calendar records.

Omitted notes, location, and reminders stay as they are. A draft cites the
fixture event and the observation time. It never accepts an invite or sends
an RSVP.
"""

from datetime import datetime

from ..calendar import iso
from ..schemas import EventInput
from ..store import DomainError
from ..tasks import TaskInput
from .fixture import FixtureItem


def _as_local(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _event_raw(current: dict) -> dict:
    raw = {key: current[key] for key in EventInput.model_fields}
    raw["start_local"] = _as_local(raw["start_local"])
    raw["end_local"] = _as_local(raw["end_local"])
    return raw


def canonical_event(current: dict) -> dict:
    return EventInput.model_validate(_event_raw(current)).model_dump(mode="json")


def merge_event(current: dict, item: FixtureItem) -> EventInput:
    """Copy the saved event, then apply only fields present on this revision."""
    raw = _event_raw(current)
    provided = item.model_fields_set
    if "title" in provided and item.title:
        raw["title"] = item.title
    if "start_local" in provided and item.start_local is not None:
        raw["start_local"] = item.start_local
    if "end_local" in provided and item.end_local is not None:
        raw["end_local"] = item.end_local
    if "timezone" in provided and item.timezone:
        raw["timezone"] = item.timezone
    if "location" in provided and item.location is not None:
        raw["location"] = item.location
    if "notes" in provided and item.notes is not None:
        raw["notes"] = item.notes
    if "reminder_minutes" in provided and item.reminder_minutes is not None:
        raw["reminder_minutes"] = item.reminder_minutes
    if "busy" in provided and item.busy is not None:
        raw["busy"] = item.busy
    if "recurrence" in provided and item.recurrence is not None:
        raw["recurrence"] = item.recurrence
    return EventInput.model_validate(raw)


def new_event(item: FixtureItem) -> EventInput:
    if not item.title or item.start_local is None or item.end_local is None:
        raise DomainError("CALENDAR_ITEM_INCOMPLETE", 422)
    payload = {
        "title": item.title,
        "start_local": item.start_local,
        "end_local": item.end_local,
        "timezone": item.timezone or "Asia/Hong_Kong",
    }
    provided = item.model_fields_set
    if "location" in provided and item.location is not None:
        payload["location"] = item.location
    if "notes" in provided and item.notes is not None:
        payload["notes"] = item.notes
    if "reminder_minutes" in provided and item.reminder_minutes is not None:
        payload["reminder_minutes"] = item.reminder_minutes
    if "busy" in provided and item.busy is not None:
        payload["busy"] = item.busy
    if "recurrence" in provided and item.recurrence is not None:
        payload["recurrence"] = item.recurrence
    return EventInput.model_validate(payload)


def kind_of(event: EventInput) -> str:
    if event.recurrence.frequency == "none":
        return "event"
    return "series"


def canonical_task(task: dict) -> dict:
    data = {key: task[key] for key in TaskInput.model_fields}
    for key in ("due_local", "check_in_local"):
        data[key] = _as_local(data[key]) if data[key] else None
    return TaskInput.model_validate(data).model_dump(mode="json")


def task_for(event: EventInput, item: FixtureItem, current: dict | None) -> TaskInput:
    """Deadline follows the event start. Other task fields stay unless titled here."""
    if current is None:
        return TaskInput(
            title=event.title,
            timezone=event.timezone,
            due_local=event.start_local,
        )
    raw = {key: current[key] for key in TaskInput.model_fields}
    for key in ("due_local", "check_in_local"):
        raw[key] = _as_local(raw[key]) if raw[key] else None
    provided = item.model_fields_set
    if "title" in provided and item.title:
        raw["title"] = item.title
    if "start_local" in provided and item.start_local is not None:
        raw["due_local"] = item.start_local
    if "timezone" in provided and item.timezone:
        raw["timezone"] = item.timezone
    return TaskInput.model_validate(raw)


def citation(item: FixtureItem) -> str:
    return f"Calendar event {item.id} observed at {iso(item.observed_at)}."


def advice_reasons(item: FixtureItem, related: list[str]) -> list[str]:
    reasons: list[str] = []
    if related:
        reasons.append("conflict")
    if item.prepare or item.needs_decision:
        reasons.append("prepare")
    if item.rsvp == "requested":
        reasons.append("rsvp")
    return reasons


def advice_payload(item: FixtureItem, task_id: str, related: list[str]) -> dict:
    observed = iso(item.observed_at)
    reasons = advice_reasons(item, related)
    cited = ", ".join([item.id, *related])
    summary = (
        f"Source event {cited} observed at {observed}. "
        "This draft does not accept an invite or send an RSVP."
    )
    if "conflict" in reasons:
        summary += " The times overlap."
    if "prepare" in reasons:
        summary += " Prepare for this meeting."
    if "rsvp" in reasons:
        summary += " An RSVP was requested."
    return {
        "task_id": task_id,
        "event_uid": item.id,
        "related_event_uids": list(related),
        "observed_at": observed,
        "send": False,
        "accept": False,
        "reasons": reasons,
        "summary": summary,
    }
