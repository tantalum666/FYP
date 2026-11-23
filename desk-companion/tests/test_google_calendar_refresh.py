"""Calendar settings HTTP journey against an in-memory, read-only Google transport."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Barrier, Event
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import COOKIE, create_app
from desk.calendar import iso
from desk import google_calendar
from desk.store import encode

RANGE = {"start": "2026-10-01", "end": "2026-10-15"}
PATH = "/calendar/v3/calendars/primary/events"


def event(remote_id, title=None, day="2026-10-03", **fields):
    return {
        "id": remote_id,
        "summary": title or remote_id,
        "start": {"dateTime": day + "T09:30:00+08:00"},
        "end": {"dateTime": day + "T10:30:00+08:00"},
        **fields,
    }


def provider_error(status, reason):
    return httpx.Response(status, json={"error": {"errors": [{"reason": reason}]}})


class Desk:
    def __init__(self, app, client):
        self.app, self.client = app, client
        self.runtime = app.state.runtime
        self.store = self.runtime.store
        self.pages = [[]]
        self.events = {}
        self.calls = []
        self.hook = None
        self.session = self.store.create_owner_session()
        self.client.cookies.set(COOKIE, self.session)
        self.client.headers["X-Desk-Request"] = "1"
        self.runtime.google.transport = httpx.MockTransport(self.provider)
        self.connect("first")

    def connect(self, account):
        self.version = account
        tokens = {
            "connection_id": account,
            "access_token": account,
            "expires_at": iso(self.store.clock() + timedelta(hours=1)),
        }
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO google_connection VALUES(1,?,?,NULL)",
                (self.runtime.google.vault.encrypt(encode(tokens)), iso(self.store.clock())),
            )
            self.store.record(conn, "google_connected")

    def provider(self, request):
        if request.method == "POST" and str(request.url) == "https://oauth2.googleapis.com/revoke":
            return httpx.Response(200, json={})
        assert request.method == "GET" and request.url.host == "www.googleapis.com"
        assert request.headers["authorization"] == "Bearer " + self.version
        path, params = request.url.path, dict(request.url.params)
        assert "syncToken" not in params
        self.calls.append((path, params))
        if self.hook:
            response = self.hook(path, params)
            if response is not None:
                return response
        if path == PATH:
            page = int(params.get("pageToken", "0"))
            items = self.pages[page]
            if params["fields"] == "nextPageToken,items(id)":
                assert params["showDeleted"] == "true"
                items = [{"id": row["id"]} for row in items]
            else:
                assert params["showDeleted"] == "false"
            assert params["singleEvents"] == "true"
            return httpx.Response(
                200,
                json={
                    "items": items,
                    **(
                        {"nextPageToken": str(page + 1)}
                        if page + 1 < len(self.pages)
                        else {"nextSyncToken": "must-never-be-used-with-this-range"}
                    ),
                },
            )
        assert path.startswith(PATH + "/") and set(params) == {"fields"}
        result = self.events[path.removeprefix(PATH + "/")]
        return result if isinstance(result, httpx.Response) else httpx.Response(200, json=result)

    def post(self, path, body, key=None):
        return self.client.post(
            "/api" + path, json=body, headers={"X-Operation-Id": key or uuid4().hex}
        )

    def ok(self, path, body, key=None):
        response = self.post(path, body, key)
        assert response.status_code == 200, response.text
        return response.json()

    def refresh(self, key=None):
        return self.ok("/google/refresh", {**RANGE, "expected_version": self.version}, key)

    def apply(self, preview, key=None):
        return self.ok(f"/exchange/{preview['preview_id']}/apply", {"replace_matching": False}, key)

    def import_events(self, *items):
        self.pages = [[item] for item in items]
        self.events.update({item["id"]: item for item in items})
        preview = self.ok("/google/preview", RANGE)
        assert self.apply(preview)["created"] == len(items)
        self.calls.clear()

    def calendar(self, end="2026-10-31"):
        response = self.client.get(
            "/api/calendar",
            params={
                "start": "2026-10-01T00:00:00Z",
                "end": end + "T00:00:00Z",
            },
        )
        assert response.status_code == 200
        return {item["title"]: item for item in response.json()["occurrences"]}

    def status(self):
        return self.client.get("/api/google/status").json()["last_refresh"]


@pytest.fixture
def desk(tmp_path):
    clock = datetime(2026, 10, 1, tzinfo=UTC)
    app = create_app(tmp_path, password="fixture-only", scheduler=False, clock=lambda: clock)
    with TestClient(app) as client:
        yield Desk(app, client)


def statuses(preview):
    return {row["event"]["title"]: row["status"] for row in preview["rows"]}


def test_two_grants_and_a_legacy_copy_roundtrip_through_owner_backup(desk, tmp_path):
    desk.import_events(event("occurrence", "First grant"), event("old", "Pre-upgrade copy"))
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links WHERE remote_id='old'")
    desk.ok("/google/disconnect", {})
    desk.connect("second")
    desk.import_events(event("occurrence", "Second grant"), event("old", "New grant copy"))
    original = desk.calendar()
    with desk.store.connection() as conn:
        live_keys = {
            title: desk.store.event(conn, row["id"])["external_id"]
            for title, row in original.items()
        }
    assert (
        live_keys["First grant"]
        == live_keys["Second grant"]
        == "google/" + sha256(b"primary/occurrence").hexdigest()
    )
    assert (
        live_keys["Pre-upgrade copy"]
        == live_keys["New grant copy"]
        == "google/" + sha256(b"primary/old").hexdigest()
    )
    backup = desk.client.get("/api/exchange/backup.json").json()
    restore = {"content": encode(backup)}
    app = create_app(tmp_path / "destination", password="fixture", scheduler=False)
    with TestClient(app) as client:
        other = Desk(app, client)
        preview = other.ok("/exchange/backup/preview", restore)
        assert set(statuses(preview).values()) == {"new"}
        receipt = other.apply(preview, "restore")
        assert receipt["created"] == 4 and other.apply(preview, "restore") == receipt
        assert {k: v["id"] for k, v in other.calendar().items()} == {
            k: v["id"] for k, v in original.items()
        }
        assert other.apply(other.ok("/exchange/backup/preview", restore))["kept"] == 4
        # Portable backup rows have no local grant authority, even on this sole grant.
        assert other.refresh()["rows"] == [] and other.calls == []
        other.import_events(event("occurrence", "Authenticated import"))
        other.events["occurrence"] = event("occurrence", "Authenticated update")
        refresh = other.refresh()
        assert statuses(refresh) == {"Authenticated update": "changed"}
        assert [path for path, _ in other.calls] == [PATH + "/occurrence"]
        assert other.apply(refresh)["updated"] == 1
        assert set(other.calendar()) == {*original, "Authenticated update"}
        # Re-exporting after an authentic reimport beside a detached copy is portable too.
        copies = other.client.get("/api/exchange/backup.json").json()["payload"]["events"]
        assert len({row["external_id"] for row in copies}) == len(copies) == 5

    # Merging on the source preserves the authentic links and local IDs.
    assert desk.apply(desk.ok("/exchange/backup/preview", restore))["kept"] == 4
    desk.events["occurrence"] = event("occurrence", "Only second grant changes")
    assert desk.apply(desk.refresh())["updated"] == 1
    assert desk.calendar()["Only second grant changes"]["id"] == original["Second grant"]["id"]
    assert desk.calendar()["First grant"]["version"] == 1


def test_old_backup_cannot_claim_google_provenance_or_bypass_duplicate_check(desk):
    desk.import_events(event("provider-id"))
    authentic_id = desk.calendar()["provider-id"]["id"]
    backup = desk.client.get("/api/exchange/backup.json").json()
    entry = backup["payload"]["events"][0]
    old_id = "google/" + sha256(b"primary/legacy-from-file").hexdigest()
    entry.update(id="first-backup-copy", external_id=old_id)
    backup["payload"]["events"].append({**entry, "id": "another-backup-copy"})
    backup["sha256"] = sha256(encode(backup["payload"]).encode()).hexdigest()
    preview = desk.ok("/exchange/backup/preview", {"content": encode(backup)})
    rejected = desk.post(f"/exchange/{preview['preview_id']}/apply", {})
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "VERSION_CONFLICT"
    assert set(desk.calendar()) == {"provider-id"}
    backup["payload"]["events"].pop()
    backup["sha256"] = sha256(encode(backup["payload"]).encode()).hexdigest()
    assert (
        desk.apply(desk.ok("/exchange/backup/preview", {"content": encode(backup)}))["created"] == 1
    )
    with desk.store.connection() as conn:
        restored = desk.store.event(conn, "first-backup-copy")
    assert (restored["origin"], restored["provider"], restored["external_id"]) == (
        "backup",
        None,
        old_id,
    )
    assert [row["existing_id"] for row in desk.refresh()["rows"]] == [authentic_id]
    assert [path for path, _ in desk.calls] == [PATH + "/provider-id"]


def test_legacy_replacement_baseline_needs_an_applied_exact_version_or_individual_consent(desk):
    names = ["verified", "uncertain", "also-uncertain", "manual"]
    desk.import_events(*(event(name) for name in names))
    desk.pages = [[event(name, name + " v2") for name in ("verified", "manual")]]
    previous = desk.ok("/google/preview", RANGE, "previous-range")
    desk.ok(
        f"/exchange/{previous['preview_id']}/apply", {"replace_matching": True}, "previous-apply"
    )
    desk.pages = [[event(name, name + " v2") for name in ("uncertain", "also-uncertain")]]
    declined = desk.ok("/google/preview", RANGE, "declined-range")
    assert desk.apply(declined)["updated"] == 0
    without_history = desk.ok("/google/preview", RANGE, "missing-range")
    desk.ok(
        f"/exchange/{without_history['preview_id']}/apply",
        {"replace_matching": True},
        "missing-apply",
    )
    original = desk.calendar()
    edited = original["manual v2"]
    desk.ok(
        f"/events/{edited['id']}/actions",
        {
            "action": "update",
            "scope": "series",
            "expected_version": 2,
            "event": {
                **next(r["event"] for r in previous["rows"] if r["existing_id"] == edited["id"]),
                "title": "Owner revision",
            },
        },
    )
    # Pre-upgrade Exchange stored the full preview in its operation receipt.
    # For the second batch, only a preview whose replacement was declined survives.
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links")
        conn.execute("DELETE FROM import_previews")
        conn.execute(
            "UPDATE operations SET response=? WHERE id='previous-range'", (encode(previous),)
        )
        conn.execute(
            "UPDATE operations SET response=? WHERE id='declined-range'", (encode(declined),)
        )
        conn.execute("DELETE FROM operations WHERE id='missing-range'")
        conn.execute(
            "UPDATE operations SET request=? WHERE id='previous-apply'",
            (
                encode(
                    {
                        "type": "import_apply",
                        "preview_id": previous["preview_id"],
                        "replace_matching": True,
                    }
                ),
            ),
        )
    desk.events.update({name: event(name, name + " v3") for name in names})
    desk.pages = [list(desk.events.values())]
    preview = desk.refresh()
    assert statuses(preview) == {
        "verified v3": "changed",
        "uncertain v3": "unverified",
        "also-uncertain v3": "unverified",
        "Owner revision": "conflict",
    }
    assert desk.apply(preview)["updated"] == 1
    assert set(desk.calendar()) == {
        "verified v3",
        "uncertain v2",
        "also-uncertain v2",
        "Owner revision",
    }

    review = desk.refresh()
    path = f"/exchange/{review['preview_id']}/apply"
    assert desk.post(path, {"resolve_event_ids": [edited["id"]]}).status_code == 422
    selected = original["uncertain v2"]["id"]
    assert desk.post(path, {"resolve_event_ids": [selected, selected]}).status_code == 422
    choices = {"resolve_event_ids": [selected]}
    receipt = desk.ok(path, choices, "selected")
    assert desk.ok(path, choices, "selected") == receipt
    assert (receipt["updated"], receipt["unresolved"], receipt["conflicts"]) == (1, 1, 1)
    assert desk.calendar()["uncertain v3"]["id"] == selected
    assert desk.calendar()["also-uncertain v2"]["version"] == 2
    assert desk.calendar()["Owner revision"]["version"] == 3
    desk.events["uncertain"] = event("uncertain", "Later Google change")
    assert statuses(desk.refresh())["Later Google change"] == "changed"

    # A verified cancellation still requires an explicit choice for an unknown baseline.
    desk.events["also-uncertain"] = {"id": "also-uncertain", "status": "cancelled"}
    review = desk.refresh()
    row = next(r for r in review["rows"] if r["event"]["title"] == "also-uncertain v2")
    assert (row["status"], row["proposed_status"], row["confirmed_cancellation"]) == (
        "unverified",
        "deleted",
        True,
    )
    assert desk.apply(review)["removed"] == 0
    review = desk.refresh()
    assert (
        desk.ok(
            f"/exchange/{review['preview_id']}/apply", {"resolve_event_ids": [row["existing_id"]]}
        )["removed"]
        == 1
    )
    assert desk.calendar()["Owner revision"]["version"] == 3


def test_confirmed_refresh_updates_same_entry_removes_only_reviewed_copies_and_replays(desk):
    desk.import_events(
        event("same"), event("move"), event("cancel"), event("missing"), event("gone")
    )
    local = desk.ok(
        "/events",
        {
            "event": {
                "title": "Manual",
                "start_local": "2026-10-04T08:00",
                "end_local": "2026-10-04T09:00",
            }
        },
    )["event_ids"][0]
    before = desk.calendar()
    desk.pages = [[event("unrelated", "Other private appointment")]]
    desk.events.update(
        {
            "move": event(
                "move", "New time", "2026-10-23", location="Room B", description="Agenda"
            ),
            "cancel": {"id": "cancel", "status": "cancelled"},
            "gone": provider_error(410, "deleted"),
            "missing": provider_error(404, "notFound"),
        }
    )
    preview = desk.refresh("read")
    assert statuses(preview) == {
        "same": "unchanged",
        "New time": "changed",
        "cancel": "deleted",
        "gone": "deleted",
        "missing": "unavailable",
    }
    assert {path for path, _ in desk.calls} == {PATH + "/" + k for k in desk.events}
    assert desk.calendar() == before and desk.status() is None
    # Lost preview response: return the identical reviewed snapshot, with no second read.
    desk.events["move"] = provider_error(503, "backendError")
    assert desk.refresh("read") == preview and len(desk.calls) == 5
    receipt = desk.apply(preview, "apply")
    assert (receipt["updated"], receipt["removed"], receipt["kept"], receipt["unresolved"]) == (
        1,
        2,
        2,
        1,
    )
    assert desk.apply(preview, "apply") == receipt
    after = desk.calendar()
    assert set(after) == {"same", "New time", "Manual", "missing"}
    assert after["Manual"]["id"] == local
    missing = before["missing"]
    assert after["same"] == {
        **before["same"],
        "conflicts": [f"{missing['id']}/{missing['occurrence_key']}"],
    }
    assert after["New time"]["id"] == before["move"]["id"] and after["New time"]["version"] == 2
    assert (
        after["New time"]["start_local"],
        after["New time"]["notes"],
        after["New time"]["location"],
    ) == ("2026-10-23T01:30:00", "Agenda", "Room B")
    assert desk.status()["removed"] == 2
    desk.events["missing"] = event("missing")  # Access returns to the same copy.
    again = desk.refresh()
    assert statuses(again) == {"same": "unchanged", "missing": "unchanged"}
    assert desk.apply(again)["updated"] == 0


def test_pending_pre_upgrade_404_review_cannot_be_recovered_or_applied(desk):
    desk.import_events(event("inaccessible"), event("rescheduled"))
    before = desk.calendar()
    desk.events.update(
        {
            "inaccessible": provider_error(404, "notFound"),
            "rescheduled": event("rescheduled", "New date", "2026-10-09"),
        }
    )
    old = desk.refresh("pending-before-upgrade")
    # Persist the original failing snapshot: the old reader represented a 404
    # exactly like a cancellation, with no positive evidence in the review.
    with desk.store.connection(write=True) as conn:
        saved = json.loads(
            conn.execute(
                "SELECT data FROM import_previews WHERE id=?", (old["preview_id"],)
            ).fetchone()[0]
        )
        row = next(
            row for row in saved["rows"] if row["existing_id"] == before["inaccessible"]["id"]
        )
        row["status"] = "deleted"
        row.pop("confirmed_cancellation", None)
        conn.execute(
            "UPDATE import_previews SET data=? WHERE id=?", (encode(saved), old["preview_id"])
        )
    recovered = desk.post(
        "/google/refresh", {**RANGE, "expected_version": desk.version}, "pending-before-upgrade"
    )
    applied = desk.post(f"/exchange/{old['preview_id']}/apply", {})
    for response in (recovered, applied):
        assert (response.status_code, response.json().get("error", {}).get("code")) == (
            410,
            "IMPORT_EXPIRED",
        )
    assert desk.calendar() == before and desk.status() is None
    fresh = desk.refresh()
    assert statuses(fresh) == {"inaccessible": "unavailable", "New date": "changed"}
    receipt = desk.apply(fresh)
    assert (receipt["updated"], receipt["removed"], receipt["unresolved"]) == (1, 0, 1)
    assert desk.calendar()["inaccessible"]["id"] == before["inaccessible"]["id"]


def test_blocked_last_google_read_times_out_without_publishing_a_partial_cancellation(
    desk, monkeypatch
):
    desk.import_events(event("one"), event("two"))
    before = desk.calendar()
    last_read = desk.client.get("/api/google/status").json()["last_read"]
    entered, release, finished = Event(), Event(), Event()
    monkeypatch.setattr(google_calendar, "READ_BUDGET_SECONDS", 0.35, raising=False)

    def stall(path, params):
        if len(desk.calls) == 2:
            entered.set()
            try:
                assert release.wait(4)
            finally:
                finished.set()
        return httpx.Response(200, json={"id": path.split("/")[-1], "status": "cancelled"})

    desk.hook = stall
    body = {**RANGE, "expected_version": desk.version}
    with ThreadPoolExecutor(1) as pool:
        response = pool.submit(desk.post, "/google/refresh", body, "interrupted")
        try:
            assert entered.wait(2)
            assert response.result(timeout=2).status_code == 504
        finally:
            release.set()
        assert finished.wait(2)
    desk.hook = None
    assert desk.calendar() == before and desk.status() is None
    assert desk.client.get("/api/google/status").json()["last_read"] == last_read
    retry = desk.refresh("interrupted")
    assert statuses(retry) == {"one": "unchanged", "two": "unchanged"}
    with desk.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM import_previews WHERE kind='google_refresh'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("path", ["/google/preview", "/google/refresh"])
def test_pages_and_point_reads_spend_one_elapsed_budget(desk, monkeypatch, path):
    desk.import_events(event("older"), event("linked"))
    before = desk.calendar()
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links WHERE remote_id='older'")
    desk.pages = (
        [[event("older")]]
        if path == "/google/refresh"
        else [[event("a")], [event("b")], [event("c")]]
    )
    elapsed = [0.0]
    monkeypatch.setattr(google_calendar, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(google_calendar, "READ_BUDGET_SECONDS", 5)

    def spend_time(url, params):
        elapsed[0] += 2
        if url != PATH:
            return httpx.Response(200, json={"id": url.split("/")[-1], "status": "cancelled"})

    desk.hook = spend_time
    response = desk.post(path, {**RANGE, "expected_version": desk.version}, "over-budget")
    assert (response.status_code, response.json()["error"]["code"]) == (504, "GOOGLE_READ_TIMEOUT")
    assert len(desk.calls) == 3
    with desk.store.connection() as conn:
        assert not conn.execute("SELECT 1 FROM operations WHERE id='over-budget'").fetchone()
    assert desk.calendar() == before and desk.status() is None


def test_failed_read_publishes_nothing_same_key_retries_and_discard_prevents_apply(desk):
    desk.import_events(event("one"), event("two"))
    desk.events = {k: event(k, "Revised " + k) for k in desk.events}
    old = desk.calendar()

    def fail_second(path, params):
        if len(desk.calls) == 2:
            return provider_error(503, "backendError")

    desk.hook = fail_second
    response = desk.post("/google/refresh", {**RANGE, "expected_version": desk.version}, "refresh")
    assert response.status_code == 502 and len(desk.calls) == 2
    assert desk.calendar() == old and desk.status() is None
    with desk.store.connection() as conn:
        assert not conn.execute(
            "SELECT 1 FROM import_previews WHERE kind='google_refresh'"
        ).fetchone()
    desk.hook = None
    recovered = desk.refresh("refresh")
    assert len(desk.calls) == 4
    discard = f"/google/{recovered['preview_id']}/discard"
    assert desk.ok(discard, {}, "discard") == desk.ok(discard, {}, "discard")
    assert desk.post(f"/exchange/{recovered['preview_id']}/apply", {}).status_code == 410
    assert desk.calendar() == old and desk.status() is None
    assert desk.apply(desk.refresh())["updated"] == 2
    confirmed = desk.status()
    desk.events["one"] = provider_error(429, "rateLimitExceeded")
    retry = desk.post("/google/refresh", {**RANGE, "expected_version": desk.version})
    assert retry.status_code == 502 and desk.status() == confirmed


def test_all_day_copy_keeps_its_identity_when_google_changes_it_to_a_timed_event(desk):
    desk.import_events(
        {
            "id": "trip",
            "summary": "Trip",
            "start": {"date": "2026-10-03"},
            "end": {"date": "2026-10-05"},
        }
    )
    before = desk.calendar()["Trip"]
    assert before["all_day"] and before["end_local"] == "2026-10-05T00:00:00"
    old_end = {"start": "2026-10-05", "end": "2026-10-06", "expected_version": desk.version}
    assert not desk.ok("/google/refresh", old_end)["rows"] and not desk.calls
    desk.events["trip"] = event("trip", "Shorter trip", "2026-10-20", transparency="transparent")
    preview = desk.refresh()
    assert preview["rows"][0]["previous"]["all_day"] and desk.apply(preview)["updated"] == 1
    after = desk.calendar()["Shorter trip"]
    assert after["id"] == before["id"] and not after["all_day"] and not after["busy"]
    assert (after["start_local"], after["timezone"]) == ("2026-10-20T01:30:00", "UTC")


def test_owner_edits_before_and_after_review_are_preserved_atomically(desk):
    desk.import_events(event("a"), event("b"), event("c"))
    before = desk.calendar()

    def edit(title, value, version=1):
        item = before[title]
        return desk.ok(
            f"/events/{item['id']}/actions",
            {
                "action": "update",
                "scope": "series",
                "expected_version": version,
                "event": {
                    "title": value,
                    "start_local": item["start_local"],
                    "end_local": item["end_local"],
                    "timezone": item["timezone"],
                    "notes": "Keep this local edit",
                },
            },
        )

    edit("b", "My version")
    desk.ok(
        f"/events/{before['c']['id']}/actions",
        {
            "action": "complete",
            "scope": "occurrence",
            "expected_version": 1,
            "occurrence_key": before["c"]["occurrence_key"],
        },
    )
    desk.events.update(
        {
            "a": event("a", "Changed remotely"),
            "b": {"id": "b", "status": "cancelled"},
            "c": event("c", "Updated remotely"),
        }
    )
    preview = desk.refresh()
    assert statuses(preview) == {
        "Changed remotely": "changed",
        "My version": "conflict",
        "c": "conflict",
    }
    edit("a", "Edited after review")
    rejected = desk.post(f"/exchange/{preview['preview_id']}/apply", {})
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "VERSION_CONFLICT"
    assert desk.status() is None
    assert desk.apply(desk.refresh())["conflicts"] == 3
    after = desk.calendar()
    assert after["My version"]["notes"] == "Keep this local edit" and after["c"]["completed"]
    assert after["Edited after review"]["version"] == 2


def test_legacy_hashed_imports_use_only_ids_in_selected_pages_and_keep_absent(desk):
    desk.import_events(event("older"), event("absent"))
    # This is the persisted representation written by the pre-refresh importer.
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links")
        conn.execute("DELETE FROM import_previews")
        # Old grants had no connection_id and old imports retained only primary/id digests.
        tokens = {
            "access_token": "first",
            "expires_at": iso(desk.store.clock() + timedelta(hours=1)),
        }
        conn.execute(
            "UPDATE google_connection SET encrypted_tokens=?",
            (desk.runtime.google.vault.encrypt(encode(tokens)),),
        )
        assert {
            r[0] for r in conn.execute("SELECT json_extract(data,'$.external_id') FROM events")
        } == {
            "google/" + sha256(("primary/" + rid).encode()).hexdigest()
            for rid in ("older", "absent")
        }
    # The same opaque binding is used by the settings status and both import endpoints.
    version = desk.client.get("/api/google/status").json()["version"]
    older_id = desk.calendar()["older"]["id"]
    desk.pages = [[event("private", "Unrelated secret")], [event("older")]]
    desk.events["older"] = event("older", "Reviewed older copy")
    desk.hook = lambda path, params: (
        provider_error(410, "fullSyncRequired") if params.get("pageToken") == "1" else None
    )
    assert (
        desk.post("/google/refresh", {**RANGE, "expected_version": version}, "legacy").status_code
        == 502
    )
    assert set(desk.calendar()) == {"older", "absent"} and desk.status() is None
    desk.hook = None
    desk.calls.clear()
    preview = desk.ok("/google/refresh", {**RANGE, "expected_version": version}, "legacy")
    assert [(p, v.get("pageToken")) for p, v in desk.calls] == [
        (PATH, None),
        (PATH, "1"),
        (PATH + "/older", None),
    ]
    assert all(v["fields"] == "nextPageToken,items(id)" for p, v in desk.calls if p == PATH)
    assert "Unrelated secret" not in str(preview)
    assert statuses(preview) == {"Reviewed older copy": "changed", "absent": "unresolved"}
    assert desk.apply(preview)["unresolved"] == 1
    assert desk.calendar()["Reviewed older copy"]["id"] == older_id
    desk.pages = [[]]
    desk.events["older"] = {"id": "older", "status": "cancelled"}
    assert (
        desk.apply(desk.ok("/google/refresh", {**RANGE, "expected_version": version}))["removed"]
        == 1
    )
    assert set(desk.calendar()) == {"absent"}


def test_switching_grants_never_adopts_another_account_or_replays_its_preview(desk):
    desk.import_events(event("shared-id", "Account A"), event("old", "Ambiguous legacy"))
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links WHERE remote_id='old'")
    pending = desk.refresh("account-a")
    desk.connect("second")
    desk.calls.clear()
    assert (
        desk.post(
            "/google/refresh", {**RANGE, "expected_version": "first"}, "account-a"
        ).status_code
        == 409
    )
    assert desk.post(f"/exchange/{pending['preview_id']}/apply", {}).status_code == 409
    assert not desk.refresh()["rows"] and not desk.calls and desk.status() is None
    desk.import_events(event("shared-id", "Account B"), event("old", "B copy of ID"))
    desk.events["shared-id"] = {"id": "shared-id", "status": "cancelled"}
    assert desk.apply(desk.refresh())["removed"] == 1
    assert set(desk.calendar()) == {"Account A", "Ambiguous legacy", "B copy of ID"}


@pytest.mark.parametrize("change", ["signout", "hidden", "reconnect"])
def test_authority_lost_during_read_stops_before_next_call_or_publication(desk, change):
    desk.import_events(event("one"), event("two"))

    def invalidate(path, params):
        if change == "signout":
            desk.store.logout(desk.session)
        elif change == "hidden":
            desk.ok(
                "/settings",
                {"expected_version": 1, "timezone": "Asia/Hong_Kong", "hide_private": True},
            )
        else:
            desk.connect("other")

    desk.hook = invalidate
    rejected = desk.post("/google/refresh", {**RANGE, "expected_version": "first"})
    assert rejected.status_code == (409 if change == "reconnect" else 403)
    assert len(desk.calls) == 1
    with desk.store.connection() as conn:
        assert not conn.execute(
            "SELECT 1 FROM import_previews WHERE kind='google_refresh'"
        ).fetchone()
        assert not conn.execute("SELECT 1 FROM google_refresh_result").fetchone()


def test_owner_session_device_and_privacy_fence_cached_receipts(desk):
    desk.import_events(event("private"))
    preview = desk.refresh("original-read")
    review_version = preview["metadata"]["review_version"]
    assert desk.client.get("/api/google/status").json()["review_version"] == review_version
    path = f"/exchange/{preview['preview_id']}/apply"
    desk.apply(preview, "original-apply")
    # A different valid owner session, then an authenticated paired screen.
    desk.client.cookies.clear()
    desk.client.cookies.set(COOKIE, desk.store.create_owner_session())
    assert desk.client.get("/api/google/status").json()["review_version"] != review_version
    assert desk.post(path, {"replace_matching": False}, "original-apply").status_code == 403
    assert (
        desk.post(
            "/google/refresh", {**RANGE, "expected_version": "first"}, "original-read"
        ).status_code
        == 409
    )
    desk.client.cookies.clear()
    device = desk.runtime.access.enrol_display("Fixture display", "enrol-fixture-display")
    desk.client.headers["Authorization"] = "Bearer " + device["token"]
    assert desk.post("/google/refresh", {**RANGE, "expected_version": "first"}).status_code == 403
    assert desk.post(path, {"replace_matching": False}, "original-apply").status_code == 403
    assert desk.client.get("/api/google/status").status_code == 403
    desk.client.cookies.set(COOKIE, desk.session)
    desk.ok(
        "/settings", {"expected_version": 1, "timezone": "Asia/Hong_Kong", "hide_private": True}
    )
    assert desk.post(path, {"replace_matching": False}, "original-apply").status_code == 403
    assert (
        desk.post(
            "/google/refresh", {**RANGE, "expected_version": "first"}, "original-read"
        ).status_code
        == 403
    )
    assert desk.status() is None
    assert desk.client.get("/api/google/status").json()["review_version"] is None
    desk.ok(
        "/settings", {"expected_version": 2, "timezone": "Asia/Hong_Kong", "hide_private": False}
    )
    assert desk.post(path, {"replace_matching": False}, "original-apply").status_code == 410


def test_concurrent_confirmations_have_one_winner_and_one_receipt_on_retry(desk):
    desk.import_events(event("id"))
    desk.events["id"] = event("id", "Moved once")
    previews = [desk.refresh(), desk.refresh()]
    barrier = Barrier(2)

    def confirm(pair):
        i, preview = pair
        barrier.wait(5)
        return desk.post(f"/exchange/{preview['preview_id']}/apply", {}, "apply" + str(i))

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(confirm, enumerate(previews)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert desk.calendar()["Moved once"]["version"] == 2
    winner = next(i for i, r in enumerate(responses) if r.is_success)
    assert (
        desk.ok(f"/exchange/{previews[winner]['preview_id']}/apply", {}, "apply" + str(winner))
        == responses[winner].json()
    )


def test_a_newer_unchanged_review_invalidates_only_overlapping_copies(desk):
    desk.import_events(event("first-day"), event("later", day="2026-10-10"))

    def review(start, end):
        return desk.ok(
            "/google/refresh", {"start": start, "end": end, "expected_version": desk.version}
        )

    desk.events["first-day"] = {"id": "first-day", "status": "cancelled"}
    old = review("2026-10-03", "2026-10-04")
    assert statuses(old) == {"first-day": "deleted"}
    desk.events["first-day"] = event("first-day")
    desk.events["later"] = event("later", "Later moved", day="2026-10-11")
    separate = review("2026-10-10", "2026-10-11")
    current = review("2026-10-03", "2026-10-04")
    assert desk.apply(current)["kept"] == 1
    assert (
        desk.post(f"/exchange/{old['preview_id']}/apply", {}).json()["error"]["code"]
        == "VERSION_CONFLICT"
    )
    assert desk.apply(separate)["updated"] == 1
    assert desk.calendar()["first-day"]["version"] == 1


def test_a_late_same_key_read_cannot_reopen_a_discarded_review(desk):
    desk.import_events(event("only", "Private fixture"))
    reading, release = Event(), Event()

    def hold_first(path, params):
        if not reading.is_set():
            reading.set()
            assert release.wait(5)

    desk.hook = hold_first
    body = {**RANGE, "expected_version": desk.version}
    with ThreadPoolExecutor(1) as pool:
        delayed = pool.submit(desk.post, "/google/refresh", body, "overlap")
        try:
            assert reading.wait(5)
            preview = desk.refresh("overlap")
            path = f"/google/{preview['preview_id']}/discard"
            receipt = desk.ok(path, {}, "discard-won")
        finally:
            release.set()
        assert delayed.result().status_code == 410
    with desk.store.connection(write=True) as conn:
        assert (
            "Private fixture"
            not in conn.execute("SELECT response FROM operations WHERE id='overlap'").fetchone()[0]
        )
        conn.execute("DELETE FROM import_previews")
    assert desk.ok(path, {}, "discard-won") == receipt
    desk.client.cookies.set(COOKIE, desk.store.create_owner_session())
    assert desk.post(path, {}, "discard-won").status_code == 403


def test_unrecognized_replies_cannot_remove_or_overwrite_imports(desk):
    desk.import_events(event("entry"))
    before = desk.calendar()
    for reply in (
        httpx.Response(410, json={}),
        provider_error(410, "fullSyncRequired"),
        provider_error(404, "forbidden"),
        {"id": "different", "status": "cancelled"},
    ):
        desk.events["entry"] = reply
        failed = desk.post(
            "/google/refresh", {**RANGE, "expected_version": desk.version}, "review-again"
        )
        assert failed.status_code == 502
    for reply in (
        {"id": "entry", "start": {}},
        event("entry", "Recurring series", recurrence=["RRULE:FREQ=DAILY"]),
        event("entry", "Unknown state", status="unexpected"),
    ):
        desk.events["entry"] = reply
        preview = desk.refresh()
        assert statuses(preview) == {"entry": "unsupported"}
        assert desk.apply(preview)["unresolved"] == 1
    assert desk.calendar() == before


def test_expired_page_restarts_same_range_without_keeping_partial_matches(desk):
    desk.import_events(event("before"), event("after"))
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM google_import_links")
    desk.pages = [[event("before")], [event("other")]]

    def expire_once(path, params):
        if params.get("pageToken") == "1":
            desk.pages = [[event("after")]]
            return provider_error(410, "fullSyncRequired")

    desk.hook = expire_once
    preview = desk.refresh()
    assert statuses(preview) == {"before": "unresolved", "after": "unchanged"}
    assert [p for p, _ in desk.calls] == [PATH, PATH, PATH, PATH + "/after"]
    assert desk.calls[0][1] == desk.calls[2][1]  # Same fields, dates and first page.
    assert desk.apply(preview)["kept"] == 2


def test_restart_and_pruned_preview_preserve_bound_receipt_and_last_result(desk):
    desk.import_events(event("repeat_20261003T013000Z"))
    desk.events["repeat_20261003T013000Z"] = event("repeat_20261003T013000Z", "New location")
    preview = desk.refresh()
    receipt = desk.apply(preview, "saved-apply")
    clock = desk.store.clock() + timedelta(minutes=16)
    app = create_app(desk.store.directory, scheduler=False, clock=lambda: clock)
    app.state.runtime.google.transport = httpx.MockTransport(desk.provider)
    with TestClient(app, headers={"X-Desk-Request": "1"}) as client:
        client.cookies.set(COOKIE, desk.session)
        assert client.get("/api/google/status").json()["last_refresh"]["updated"] == 1
        next_preview = client.post(
            "/api/google/refresh",
            json={**RANGE, "expected_version": "first"},
            headers={"X-Operation-Id": "after-restart"},
        )
        assert next_preview.status_code == 200 and statuses(next_preview.json()) == {
            "New location": "unchanged"
        }
        with desk.store.connection() as conn:
            assert not conn.execute(
                "SELECT 1 FROM import_previews WHERE id=?", (preview["preview_id"],)
            ).fetchone()
        path = f"/api/exchange/{preview['preview_id']}/apply"
        headers = {"X-Operation-Id": "saved-apply"}
        assert client.post(path, json={}, headers=headers).json() == receipt
        client.cookies.set(COOKIE, desk.store.create_owner_session())
        assert client.post(path, json={}, headers=headers).status_code == 403


def test_local_deletion_and_oversized_refresh_do_not_read_or_revive_unselected_events(desk):
    # The existing range importer supports more entries than a single point-read refresh.
    desk.pages = [[event("entry" + str(i)) for i in range(51)]]
    desk.apply(desk.ok("/google/preview", RANGE))
    desk.calls.clear()
    large = desk.post("/google/refresh", {**RANGE, "expected_version": "first"})
    assert large.status_code == 422 and large.json()["error"]["code"] == "GOOGLE_REFRESH_TOO_LARGE"
    assert not desk.calls
    for item in desk.calendar().values():
        desk.ok(
            f"/events/{item['id']}/actions",
            {"action": "delete", "scope": "series", "expected_version": item["version"]},
        )
    assert not desk.refresh()["rows"] and not desk.calls


def test_late_oauth_token_rotation_cannot_replace_the_new_connection(desk):
    desk.import_events(event("one"))
    google = desk.runtime.google
    with desk.store.connection(write=True) as conn:
        old = {
            "connection_id": "first",
            "access_token": "expired-fixture",
            "refresh_token": "fixture",
            "expires_at": iso(desk.store.clock()),
        }
        conn.execute(
            "UPDATE google_connection SET encrypted_tokens=?", (google.vault.encrypt(encode(old)),)
        )
    calls = []

    def rotate(request):
        calls.append(request.url.path)
        assert request.method == "POST" and str(request.url) == google.token_url
        desk.connect("replacement")
        return httpx.Response(200, json={"access_token": "stale-fixture", "expires_in": 3600})

    google.transport = httpx.MockTransport(rotate)
    response = desk.post("/google/refresh", {**RANGE, "expected_version": "first"})
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "APP_CONNECTION_CHANGED"
    )
    assert (
        calls == ["/token"]
        and google.account()["version"] == "replacement"
        and desk.status() is None
    )
