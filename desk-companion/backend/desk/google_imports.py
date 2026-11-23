"""Local provenance for reviewed copies of events on a single Calendar grant."""

import json
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .calendar import iso
from .schemas import EventInput
from .store import DomainError, encode


def initialize(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS google_import_links(
            account_version TEXT NOT NULL, remote_id TEXT NOT NULL,
            event_id TEXT NOT NULL UNIQUE REFERENCES events(id), imported_version INTEGER NOT NULL,
            review_id TEXT NOT NULL,
            PRIMARY KEY(account_version, remote_id))"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS google_refresh_result(
            id INTEGER PRIMARY KEY CHECK(id=1), account_version TEXT NOT NULL, summary TEXT NOT NULL)"""
    )


@dataclass
class ImportedCopy:
    id: str
    version: int
    event: dict
    remote_id: str | None
    imported_version: int
    review_id: str | None
    has_exceptions: bool

    def overlaps(self, begin, end):
        zone = begin.tzinfo if self.event["all_day"] else ZoneInfo(self.event["timezone"])
        start = datetime.fromisoformat(self.event["start_local"]).replace(tzinfo=zone)
        finish = datetime.fromisoformat(self.event["end_local"]).replace(tzinfo=zone)
        return start < end and finish > begin


def imported_copies(conn, account):
    # Old imports hashed primary/id without recording a grant. Only an uninterrupted,
    # sole recorded connection can establish which primary calendar they came from.
    sole_grant = conn.execute(
        """SELECT COUNT(*)=1 AND MIN(action)='google_connected' FROM records
           WHERE action IN ('google_connected','google_disconnected')"""
    ).fetchone()[0]
    rows = conn.execute(
        """SELECT e.id,e.version,e.data,l.remote_id,l.imported_version,l.review_id,
                  EXISTS(SELECT 1 FROM exceptions x WHERE x.event_id=e.id) AS has_exceptions
           FROM events e LEFT JOIN google_import_links l ON l.event_id=e.id
           WHERE e.deleted=0 AND json_extract(e.data,'$.provider')='google'
             AND json_extract(e.data,'$.origin')='import'
             AND (l.account_version=? OR (l.event_id IS NULL AND ?))
           ORDER BY e.id""",
        (account, sole_grant),
    )
    result = {}
    for row in rows:
        event = json.loads(row["data"])
        model = EventInput.model_validate(
            {k: v for k, v in event.items() if k in EventInput.model_fields}
        )
        result[event["external_id"]] = ImportedCopy(
            row["id"],
            row["version"],
            model.model_dump(mode="json"),
            row["remote_id"],
            row["imported_version"] or 1,
            row["review_id"],
            bool(row["has_exceptions"]),
        )
    return result


def review_row(external_id, copy, event=None, status=None):
    if copy is None:
        status = "new"
    elif status is None:
        status = "unchanged" if event == copy.event else "changed"
    if (
        copy
        and status in {"changed", "deleted", "unchanged"}
        and (
            copy.has_exceptions or (copy.version != copy.imported_version and status != "unchanged")
        )
    ):
        status = "conflict"
    return {
        "status": status,
        "event": event if event is not None and status != "conflict" else copy.event,
        "external_id": external_id,
        "existing_id": copy.id if copy else None,
        "expected_version": copy.version if copy else None,
        "exceptions": {},
        **({"previous": copy.event} if status == "changed" else {}),
    }


def apply_import(exchange, conn, kind, preview_id, preview, options):
    store = exchange.store
    refresh = kind == "google_refresh"
    account = preview["google"]["fence"]["account_version"]
    identifiers = preview["google"]["identifiers"]
    rows = preview["rows"]
    copies = imported_copies(conn, account)
    new_count = sum(row["status"] == "new" for row in rows)
    if (
        new_count
        and new_count + conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]
        > 500
    ):
        raise DomainError("EVENT_LIMIT", 422)
    created = updated = removed = 0
    for item in rows:
        status = item["status"]
        replace = status == "changed" and (refresh or options.replace_matching)
        if not refresh and status not in {"new", "unchanged"} and not replace:
            continue
        ext = item["external_id"]
        copy = copies.get(ext)
        if (copy.id if copy else None) != item["existing_id"] or (
            copy
            and (
                copy.version != item["expected_version"]
                or copy.review_id != preview["google"]["last_reviews"].get(copy.id)
            )
        ):
            raise DomainError("VERSION_CONFLICT")
        if refresh and not copy:
            raise DomainError("VERSION_CONFLICT")
        if copy and copy.has_exceptions and (status in {"deleted", "unchanged"} or replace):
            raise DomainError("VERSION_CONFLICT")
        if status == "deleted":
            conn.execute("UPDATE events SET deleted=1,version=version+1 WHERE id=?", (copy.id,))
            store.record(conn, "delete", copy.id, {"scope": "series", "origin": "google_refresh"})
            removed += 1
            continue
        if status == "new" or replace:
            event_id = exchange.save_event(conn, item, "google")
            version = copy.version + 1 if copy else 1
            created += int(copy is None)
            updated += int(copy is not None)
        elif status == "unchanged":
            event_id, version = copy.id, copy.version
        elif ext in identifiers:
            # Preserve the baseline so a later refresh still detects the local edits.
            event_id, version = copy.id, copy.imported_version
        else:
            continue  # No verified Google ID for this older copy.
        conn.execute(
            """INSERT INTO google_import_links(account_version,remote_id,event_id,imported_version,review_id)
               VALUES(?,?,?,?,?)
               ON CONFLICT(account_version,remote_id) DO UPDATE SET
               event_id=excluded.event_id,imported_version=excluded.imported_version,review_id=excluded.review_id""",
            (account, identifiers[ext], event_id, version, preview_id),
        )
    result = {
        "created": created,
        "updated": updated,
        "removed": removed,
        "kept": len(rows) - created - updated - removed,
        "conflicts": sum(row["status"] == "conflict" for row in rows),
        "unresolved": sum(
            row["status"] in {"unresolved", "unsupported", "unavailable"} for row in rows
        ),
    }
    if refresh:
        summary = {
            **result,
            "at": iso(store.clock()),
            "start": preview["metadata"]["start"],
            "end": preview["metadata"]["end"],
        }
        conn.execute(
            "INSERT OR REPLACE INTO google_refresh_result VALUES(1,?,?)", (account, encode(summary))
        )
    return result
