"""Published airport-local flight times and absolute itinerary bounds."""

from datetime import UTC, datetime, timedelta
from functools import cache
import json
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..calendar import wall_to_utc


@cache
def _airport_zones():
    data = Path(__file__).resolve().parents[1] / "data/airport-timezones.json"
    groups = json.loads(data.read_text(encoding="utf-8"))
    return {code: zone for zone, codes in groups.items() for code in codes.split()}


def _zone(airport):
    try:
        return _airport_zones().get(airport)
    except (OSError, ValueError):
        # A missing or unreadable local index cannot justify a guessed zone.
        return None


def departure_day(now, airport):
    """The supplier accepts a departure date in the departure airport's local time."""
    zone = _zone(airport)
    try:
        return now.astimezone(ZoneInfo(zone or "Asia/Hong_Kong")).date()
    except ZoneInfoNotFoundError:
        return now.astimezone(ZoneInfo("Asia/Hong_Kong")).date()


def published_time(value, airport):
    if not isinstance(value, str) or len(value) < 16 or value[10] not in "Tt ":
        raise ValueError("Missing flight time")
    local = datetime.fromisoformat(value)
    if local.tzinfo is not None and (zone := _zone(airport)):
        try:
            local = local.astimezone(ZoneInfo(zone))
        except ZoneInfoNotFoundError:
            pass  # The explicit offset still identifies an instant.
    precision = "microseconds" if local.microsecond else "seconds" if local.second else "minutes"
    return local.isoformat(timespec=precision)


def _instant(value, airport):
    if not isinstance(value, str) or len(value) < 16 or value[10] not in "Tt ":
        raise ValueError("Missing flight time")
    local = datetime.fromisoformat(value)
    if local.tzinfo is not None:
        return local.astimezone(UTC)
    zone = _zone(airport)
    if not zone:
        raise ValueError("Unknown airport time zone")
    return wall_to_utc(local, zone, reject_ambiguous=True)


def flight_window(segments):
    """Include connections. Local date changes, folds and gaps are resolved per airport."""
    if not segments:
        return None
    start = previous_end = previous_airport = None
    try:
        for leg in segments:
            departure = _instant(leg["departs"], leg["origin"])
            arrival = _instant(leg["arrives"], leg["destination"])
            if arrival <= departure or (
                previous_end is not None
                and (departure < previous_end or leg["origin"] != previous_airport)
            ):
                return None
            start = start or departure
            previous_end, previous_airport = arrival, leg["destination"]
        if previous_end - start <= timedelta(days=62):
            return start, previous_end
    except (ValueError, TypeError, KeyError, OverflowError, ZoneInfoNotFoundError):
        pass
    return None
