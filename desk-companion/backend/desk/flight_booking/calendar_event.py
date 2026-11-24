"""Build calendar drafts from already scoped sandbox flight receipts."""

import re
from zoneinfo import ZoneInfo

from ..calendar import wall_to_utc
from ..schemas import CreateEvents, EventInput
from ..store import DomainError
from .provider import PNR
from .timetable import flight_window


_AIRPORT = re.compile(r"[A-Z]{3}")
_FLIGHT = re.compile(r"(?:([A-Z]{3}|[A-Z][A-Z0-9]|[0-9][A-Z])[ -]?)?([0-9]{1,4}[A-Z]?)")
_LOST_FRACTION = re.compile(r"[.,][0-9]{6}[0-9]*[1-9]")


def _checked_leg_label(leg, pnr):
    if not isinstance(leg, dict):
        raise ValueError("Invalid segment")
    # datetime.fromisoformat would silently discard these sub-microsecond digits.
    if any(_LOST_FRACTION.search(leg[k]) for k in ("departs", "arrives")):
        raise ValueError("Unsupported flight time precision")

    origin, destination, flight = leg["origin"], leg["destination"], leg["flight"]
    number = _FLIGHT.fullmatch(flight)
    if not (number and _AIRPORT.fullmatch(origin) and _AIRPORT.fullmatch(destination)):
        raise ValueError("Invalid public itinerary codes")
    if pnr in flight:
        # A public designator can coincide with the private six-character locator.
        flight = " ".join(number.groups(""))
    return f"{flight} {origin} → {destination}"


def _verified_itinerary(row):
    if not isinstance(row, dict) or not isinstance(row.get("quote"), dict):
        raise ValueError("Missing flight receipt")
    quote = row["quote"]
    approved, captured, pnr = row["approved"], row["capture"], row["pnr"]
    integers = (approved, captured, quote["adults"], quote["total_minor"])
    if (
        row["state"] != "completed"
        or quote["currency"] != "HKD"
        or not PNR.fullmatch(pnr)
        or not all(type(n) is int and n > 0 for n in integers)
        or approved != captured
    ):
        raise ValueError("Unverified flight receipt")

    legs = quote["segments"]
    if not isinstance(legs, list) or not legs:
        raise ValueError("Missing itinerary")
    labels = [_checked_leg_label(leg, pnr) for leg in legs]
    window = flight_window(legs)
    if window is None:
        raise ValueError("Unresolved itinerary")
    if len(labels) > 5:
        labels = [labels[0], "…", labels[-1]]
    return "Test itinerary: " + " / ".join(labels), window


def _draft_in_zone(title, window, zone):
    # Leave seconds intact: EventInput must reject, not round, a sub-minute bound.
    start, end = (instant.astimezone(zone).replace(tzinfo=None) for instant in window)
    event = EventInput(
        title=title,
        start_local=start,
        end_local=end,
        timezone=zone.key,
        visibility="private",
        busy=True,
        reminder_minutes=[],
    )
    walls = (event.start_local, event.end_local)
    resolved = tuple(wall_to_utc(w, event.timezone, reject_ambiguous=True) for w in walls)
    if resolved != window:
        raise ValueError("Inexact calendar bounds")
    return CreateEvents(event=event)


def build_calendar_event(row: dict, calendar_zone: str) -> CreateEvents:
    """Draft one private itinerary event without changing the booking or the calendar."""
    try:
        title, window = _verified_itinerary(row)
        if not isinstance(calendar_zone, str):
            raise ValueError("Invalid desk timezone")
        zone = ZoneInfo(calendar_zone)  # An unknown preference is not a fallback case.
        try:
            return _draft_in_zone(title, window, zone)
        except (ValueError, OverflowError):
            # The desk walls may not encode this pair of instants (e.g. a DST fold).
            if calendar_zone == "UTC":
                raise
            return _draft_in_zone(title, window, ZoneInfo("UTC"))
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        raise DomainError("FLIGHT_CALENDAR_UNVERIFIED", 409) from None
