"""Minimal, private-by-default snapshots for iOS widgets and cached reminders."""

import hashlib
from datetime import timedelta
from zoneinfo import ZoneInfo

from .calendar import expand_all, iso
from .workspace_data import is_quiet


def phone_snapshot(runtime):
    store = runtime.store
    now = store.clock()
    prefs = runtime.data.preferences()
    with store.connection() as conn:
        settings = store.settings(conn)
        events, exceptions = store.data(conn)
        occurrences = expand_all(
            events,
            exceptions,
            now,
            now + timedelta(days=8),
            settings["timezone"],
            include_conflicts=False,
        )
        existing = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM reminders")}
    upcoming, notifications = [], []
    for event in sorted(occurrences, key=lambda e: e["start"]):
        if event["completed"]:
            continue
        hidden = event["visibility"] == "private"
        title = "" if hidden else event["title"]
        upcoming.append(
            {
                "title": title,
                "start": event["start"],
                "end": event["end"],
                "all_day": event["all_day"],
                "redacted": hidden,
            }
        )
        from datetime import datetime

        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
        for early in event["reminder_minutes"]:
            reminder_id = hashlib.sha256(
                f"{event['id']}/{event['occurrence_key']}/{early}".encode()
            ).hexdigest()[:32]
            recorded = existing.get(reminder_id)
            if recorded and recorded["status"] in {"acknowledged", "cancelled"}:
                continue
            due = (
                datetime.fromisoformat(recorded["snooze_until"].replace("Z", "+00:00"))
                if recorded and recorded["snooze_until"]
                else start - timedelta(minutes=early)
            )
            if now + timedelta(seconds=2) < due < now + timedelta(days=7):
                notifications.append(
                    {
                        "id": reminder_id,
                        "at": iso(due),
                        "title": title,
                        "redacted": hidden,
                        "sound": prefs["reminder_strength"] == "chime"
                        and not is_quiet(prefs, due.astimezone(ZoneInfo(settings["timezone"]))),
                        "event_start": event["start"],
                    }
                )
    notifications.sort(key=lambda r: r["at"])
    return {
        "updated_at": iso(now),
        "expires_at": iso(now + timedelta(minutes=20)),
        "timezone": settings["timezone"],
        "items": upcoming[:3],
        "notifications": notifications[:64],
        "notifications_truncated": len(notifications) > 64,
        "source": "local_calendar",
    }
