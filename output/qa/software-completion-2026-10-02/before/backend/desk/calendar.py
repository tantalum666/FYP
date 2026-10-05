"""Calendar expansion is server-owned; clients only lay out returned occurrences."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.rrule import DAILY, MONTHLY, WEEKLY, YEARLY, rrule


FREQUENCIES = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY, "yearly": YEARLY}


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def wall_to_utc(wall, zone, reject_ambiguous=False):
    tz = ZoneInfo(zone)
    early, late = wall.replace(tzinfo=tz, fold=0), wall.replace(tzinfo=tz, fold=1)
    if early.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != wall:
        raise ValueError("This local time does not exist because the clocks change")
    if reject_ambiguous and early.utcoffset() != late.utcoffset():
        raise ValueError("This time occurs twice; choose a different time or UTC")
    return early.astimezone(UTC)


def local_key(value):
    return value.isoformat(timespec="minutes")


def recurrence_rule(event):
    rule = event["recurrence"]
    if rule["frequency"] == "none":
        return None
    until = (
        datetime.fromisoformat(rule["until"]) + timedelta(days=1, microseconds=-1)
        if rule["until"]
        else None
    )
    return rrule(
        FREQUENCIES[rule["frequency"]],
        dtstart=datetime.fromisoformat(event["start_local"]),
        interval=rule["interval"],
        until=until,
        wkst=0,
    )


def is_occurrence(event, key):
    try:
        wall = datetime.fromisoformat(key)
        if wall.tzinfo or local_key(wall) != key:
            return False
        start = datetime.fromisoformat(event["start_local"])
        if event["recurrence"]["frequency"] == "none":
            return wall == start
        return recurrence_rule(event).before(wall, inc=True) == wall
    except (ValueError, OverflowError):
        return False


def expand_event(event, exceptions, begin, end, display_zone=None):
    start = datetime.fromisoformat(event["start_local"])
    duration = datetime.fromisoformat(event["end_local"]) - start
    zone = ZoneInfo(display_zone if event["all_day"] and display_zone else event["timezone"])
    low = begin.astimezone(zone).replace(tzinfo=None) - duration
    high = end.astimezone(zone).replace(tzinfo=None)
    rule = recurrence_rule(event)
    starts = rule.between(low, high, inc=True) if rule else [start]
    # An edited occurrence can move into a window from outside the original range.
    starts_by_key = {local_key(w): w for w in starts}
    for key, exception in exceptions.items():
        if exception.get("override"):
            starts_by_key.setdefault(key, datetime.fromisoformat(key))
    result = []
    for key, wall in starts_by_key.items():
        exception = exceptions.get(key, {})
        if exception.get("cancelled"):
            continue
        current = exception.get("override") or {
            **event,
            "start_local": wall.isoformat(),
            "end_local": (wall + duration).isoformat(),
        }
        try:
            effective_zone = (
                display_zone if current["all_day"] and display_zone else current["timezone"]
            )
            current_start = wall_to_utc(
                datetime.fromisoformat(current["start_local"]), effective_zone
            )
            current_end = wall_to_utc(datetime.fromisoformat(current["end_local"]), effective_zone)
        except ValueError:
            continue  # Invalid DST occurrences are not shifted to another time.
        if current_end <= begin or current_start >= end:
            continue
        result.append(
            {
                **current,
                "id": event["id"],
                "version": event["version"],
                "origin": event["origin"],
                "batch_id": event.get("batch_id"),
                "occurrence_key": key,
                "start": iso(current_start),
                "end": iso(current_end),
                "completed": exception.get("completed", False),
                "is_exception": bool(exception.get("override")),
                "series_recurrence": event["recurrence"],
                "conflicts": [],
            }
        )
    return result


def expand_all(events, exceptions, begin, end, display_zone=None, include_conflicts=True):
    result = [
        occ
        for event in events
        for occ in expand_event(event, exceptions.get(event["id"], {}), begin, end, display_zone)
    ]
    result.sort(key=lambda o: (o["start"], o["end"], o["title"], o["id"]))
    if not include_conflicts:
        return result
    if len(result) > 3000:
        raise ValueError("Too many occurrences; use a narrower window")
    active = []
    for occurrence in result:
        active = [o for o in active if o["end"] > occurrence["start"]]
        if occurrence["busy"] and not occurrence["completed"]:
            for previous in active:
                occurrence["conflicts"].append(previous["id"] + "/" + previous["occurrence_key"])
                previous["conflicts"].append(occurrence["id"] + "/" + occurrence["occurrence_key"])
            active.append(occurrence)
    return result


def redact(occurrence, hidden):
    if not hidden or occurrence["visibility"] != "private":
        return occurrence
    return {**occurrence, "title": "", "location": "", "notes": "", "redacted": True}
