"""Match complete itineraries to busy desk occurrences without disclosing event details."""

from datetime import timedelta
from zoneinfo import ZoneInfoNotFoundError

from ..calendar import expand_all, is_busy, iso
from ..store import DomainError
from .timetable import flight_window


def _bounds(offer):
    window = flight_window(offer["segments"])
    if window is None:
        return None
    start, end = window
    duration = offer.get("duration_seconds")
    if duration is None:
        return start, end, end
    if type(duration) is not int or not 0 < duration <= 62 * 86400:
        return None
    try:
        elapsed_end = start + timedelta(seconds=duration)
    except OverflowError:
        return None
    # Some sandbox offers compute duration from the two wall clocks. If the
    # evidence disagrees, only claim a fit when either end would be clear.
    return start, min(end, elapsed_end), max(end, elapsed_end)


def check_itineraries(store, db, itineraries):
    settings = store.settings(db)
    if settings["hide_private"]:
        raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
    windows = [_bounds(offer) for offer in itineraries]
    valid = [window for window in windows if window]
    if not valid:
        return ["unknown"] * len(windows)
    events, exceptions = store.data(db)
    try:
        occurrences = expand_all(
            events,
            exceptions,
            min(w[0] for w in valid),
            max(w[2] for w in valid),
            settings["timezone"],
            include_conflicts=False,
        )
        busy = [(o["start"], o["end"]) for o in occurrences if is_busy(o)]
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        return ["unknown"] * len(windows)

    def check(window):
        if window is None:
            return "unknown"
        start, earliest, latest = map(iso, window)
        if any(begin < earliest and finish > start for begin, finish in busy):
            return "conflict"
        if latest != earliest and any(begin < latest and finish > start for begin, finish in busy):
            return "unknown"
        return "clear"

    return [check(window) for window in windows]
