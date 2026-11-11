"""Bounded display groups using Live's session timeline, not packet timing.

These are presentation boundaries, never provider-final transcripts or authority.
"""

import math


def transcript_interval(event):
    start, end = event.get("start_ms"), event.get("end_ms")
    if all(type(v) in (int, float) and math.isfinite(v) for v in (start, end)):
        if 0 <= start <= end <= 3_600_000:
            return start, end
    return None


class LiveCaptionGroups:
    def __init__(self):
        self.groups = [{"id": 0, "start": 0, "user_end": None, "assistant": False}]
        self.last_input_at = None

    def observe(self, role, interval, now):
        current = self.groups[-1]
        if interval:
            start, end = interval
            if start < self.groups[0]["start"]:
                return None  # A retired fragment must not resurrect old history.
            group = next(g for g in reversed(self.groups) if g["start"] <= start)
        else:
            group, start, end = current, None, None
        if role == "user":
            gap = (
                start - group["user_end"]
                if start is not None and group["user_end"] is not None
                else (now - self.last_input_at) * 1000
                if self.last_input_at is not None
                else float("inf")
            )
            if group is current and group["assistant"] and gap >= 700:
                group = {
                    "id": current["id"] + 1,
                    "start": start if start is not None else current["start"],
                    "user_end": None,
                    "assistant": False,
                }
                self.groups.append(group)
                self.groups = self.groups[-40:]
            if end is not None:
                group["user_end"] = max(group["user_end"] or 0, end)
            self.last_input_at = now
        else:
            group["assistant"] = True
        return group["id"]
