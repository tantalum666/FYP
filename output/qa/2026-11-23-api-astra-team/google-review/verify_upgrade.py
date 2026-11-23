"""Use each revision's backend with the same SQLite desk and only a synthetic Google transport."""

import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from google_desk_fixture import Desk, event, provider_error
from desk.app import create_app


class ReopenedDesk(Desk):
    def connect(self, account):
        # Keep the exact pre-upgrade grant, audit records and operation receipts.
        self.version = account


def seed(desk):
    desk.import_events(
        event("remote", "Google A1"), event("manual", "Google B1"),
        event("missing", "Unavailable appointment"), event("cancel", "Cancelled appointment"),
    )
    previous = desk.calendar()
    desk.pages = [[event("remote", "Google A2")]]
    reviewed = desk.ok("/google/preview", {"start": "2026-10-01", "end": "2026-10-15"})
    result = desk.ok("/exchange/" + reviewed["preview_id"] + "/apply", {"replace_matching": True})
    assert result["updated"] == 1
    manual = previous["Google B1"]
    desk.ok("/events/" + manual["id"] + "/actions", {
        "action": "update", "scope": "series", "expected_version": 1,
        "event": {
            "title": "Owner B2", "start_local": manual["start_local"],
            "end_local": manual["end_local"], "timezone": manual["timezone"],
            "notes": "Keep the owner's notes", "reminder_minutes": [],
        },
    })
    before = desk.calendar()
    assert before["Google A2"]["id"] == previous["Google A1"]["id"]
    assert before["Google A2"]["version"] == before["Owner B2"]["version"] == 2
    with desk.store.connection() as conn:
        assert not conn.execute(
            "SELECT name FROM sqlite_master WHERE name='google_import_links'"
        ).fetchone()
    print("Historical HTTP writes produced one Google-derived v2 and one owner-edited v2.")


def verify(desk):
    before = desk.calendar()
    desk.pages = [[event(key) for key in ("remote", "manual", "missing", "cancel", "unrelated")]]
    desk.events = {
        "remote": event("remote", "Google A3"),
        "manual": event("manual", "Google B3"),
        "missing": provider_error(404, "notFound"),
        "cancel": {"id": "cancel", "status": "cancelled"},
    }
    preview = desk.refresh()
    expected = {
        "Google A3": "changed", "Owner B2": "conflict",
        "Unavailable appointment": "unavailable", "Cancelled appointment": "deleted",
    }
    statuses = {row["event"]["title"]: row["status"] for row in preview["rows"]}
    assert statuses == expected, statuses
    assert desk.calendar() == before
    path = "/exchange/" + preview["preview_id"] + "/apply"
    rejected = desk.post(path, {"resolve_event_ids": [before["Owner B2"]["id"]]})
    assert rejected.status_code == 422 and desk.calendar() == before
    result = desk.ok(path, {"replace_matching": False}, "confirm-synthetic-mixed-batch")
    assert {key: result[key] for key in ("updated", "removed", "kept", "conflicts", "unresolved")} == {
        "updated": 1, "removed": 1, "kept": 2, "conflicts": 1, "unresolved": 1,
    }
    after = desk.calendar()
    assert set(after) == {"Google A3", "Owner B2", "Unavailable appointment"}
    assert (after["Google A3"]["id"], after["Google A3"]["version"]) == (before["Google A2"]["id"], 3)
    assert after["Owner B2"]["id"] == before["Owner B2"]["id"]
    assert (after["Owner B2"]["version"], after["Owner B2"]["notes"]) == (2, "Keep the owner's notes")
    assert (after["Unavailable appointment"]["id"], after["Unavailable appointment"]["version"]) == (
        before["Unavailable appointment"]["id"], 1,
    )
    assert all(not url.endswith("/unrelated") for url, _ in desk.calls)
    assert desk.ok(path, {"replace_matching": False}, "confirm-synthetic-mixed-batch") == result
    assert desk.calendar() == after
    desk.events["missing"] = event("missing", "Accessible again")
    retry = desk.refresh()
    recovered = next(row for row in retry["rows"] if row["event"]["title"] == "Accessible again")
    assert (recovered["status"], recovered["existing_id"]) == ("changed", before["Unavailable appointment"]["id"])
    assert desk.calendar() == after
    assert desk.apply(retry)["updated"] == 1
    assert desk.calendar()["Accessible again"]["id"] == before["Unavailable appointment"]["id"]
    print("The preview made zero changes. Confirmation updated one, removed the cancellation, kept two, "
          "and replayed without a second write.")


if __name__ == "__main__":
    phase, location = sys.argv[1:]
    assert phase in {"seed", "verify"}
    app = create_app(
        Path(location), password="fixture-only", scheduler=False, connector_configs=(),
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
    )
    with TestClient(app) as client:
        if phase == "seed":
            seed(Desk(app, client))
        else:
            verify(ReopenedDesk(app, client))
