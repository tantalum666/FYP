"""Previewed file exchange and revocable, minimal calendar projections."""

import json
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events
from pydantic import Field, ValidationError, model_validator

from .access import digest
from .calendar import expand_all, iso, wall_to_utc
from .schemas import EventInput, StrictModel
from .store import DomainError, encode
from .vault import Vault


class ImportFile(StrictModel):
    content: str = Field(min_length=1, max_length=1_000_000)
    start: date
    end: date
    source_name: str = Field(default="Imported calendar", min_length=1, max_length=80)

    @model_validator(mode="after")
    def range(self):
        if not 0 < (self.end - self.start).days <= 62:
            raise ValueError("Choose at most 62 days, with an exclusive end date")
        return self


class ImportApply(StrictModel):
    replace_matching: bool = False


class BackupInput(StrictModel):
    content: str = Field(min_length=1, max_length=100_000_000)


class ShareInput(StrictModel):
    start: date
    end: date
    mode: Literal["busy", "displayable"] = "busy"
    expires_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def range(self):
        if not 0 < (self.end - self.start).days <= 31:
            raise ValueError("Share at most 31 days")
        return self


class ExchangeService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.vault = Vault(self.store.directory)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS import_previews(id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,expires_at TEXT NOT NULL,state TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS calendar_shares(id TEXT PRIMARY KEY,token_hash TEXT UNIQUE NOT NULL,data TEXT NOT NULL,expires_at TEXT NOT NULL,revoked INTEGER NOT NULL DEFAULT 0)"
            )

    def _preview(self, kind, rows, warnings, key, metadata=None):
        def apply(conn):
            conn.execute(
                "DELETE FROM import_previews WHERE expires_at<=?", (iso(self.store.clock()),)
            )
            documents, _ = self.store.data(conn)
            existing = {e.get("external_id"): e for e in documents if e.get("external_id")}
            by_id = {e["id"]: e for e in documents}
            for row in rows:
                match = (
                    by_id.get(row.get("restore_id"))
                    if kind == "backup"
                    else existing.get(row["external_id"])
                )
                row.update(
                    existing_id=match["id"] if match else None,
                    expected_version=match["version"] if match else None,
                )
                same = match and all(match.get(k) == v for k, v in row["event"].items())
                row["status"] = "unchanged" if same else "changed" if match else "new"
            preview_id = uuid4().hex
            expires = iso(self.store.clock() + timedelta(minutes=15))
            document = {"rows": rows, "warnings": warnings, "metadata": metadata or {}}
            conn.execute(
                "INSERT INTO import_previews VALUES(?,?,?,?,'pending')",
                (preview_id, kind, encode(document), expires),
            )
            return {"preview_id": preview_id, "kind": kind, "expires_at": expires, **document}

        return self.store.operation(
            key,
            {
                "type": "preview",
                "kind": kind,
                "data_hash": digest(encode([rows, warnings, metadata])),
            },
            apply,
        )

    def preview_ics(self, payload, key):
        with self.store.connection() as conn:
            zone = self.store.settings(conn)["timezone"]
        try:
            calendar = icalendar.Calendar.from_ical(payload.content)
            components = calendar.walk("VEVENT")
            if len(components) > 100:
                raise DomainError("IMPORT_TOO_LARGE", 422)
            for event in components:
                rule = event.get("RRULE", {})
                if rule and (
                    str(rule.get("FREQ", [""])[0]) not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
                    or any(k in rule for k in ["BYHOUR", "BYMINUTE", "BYSECOND"])
                ):
                    raise DomainError("IMPORT_RULE_UNSUPPORTED", 422)
                if not event.get("UID") or len(str(event["UID"])) > 512:
                    raise DomainError("IMPORT_UID_REQUIRED", 422)
            expanded = recurring_ical_events.of(calendar).between(payload.start, payload.end)
            if len(expanded) > 500:
                raise DomainError("IMPORT_TOO_LARGE", 422)
        except DomainError:
            raise
        except (ValueError, TypeError, KeyError, OverflowError):
            raise DomainError("INVALID_ICS", 422) from None
        rows, warnings, identifiers = [], [], set()
        for index, event in enumerate(expanded):
            try:
                if str(event.get("STATUS", "")) == "CANCELLED":
                    continue
                start = event.decoded("DTSTART")
                finish = (
                    event.decoded("DTEND")
                    if event.get("DTEND")
                    else start
                    + (
                        event.decoded("DURATION")
                        if event.get("DURATION")
                        else timedelta(days=1)
                        if isinstance(start, date) and not isinstance(start, datetime)
                        else timedelta(hours=1)
                    )
                )
                if isinstance(start, datetime):
                    if start.tzinfo is None:
                        start = wall_to_utc(
                            start.replace(second=0, microsecond=0), zone, reject_ambiguous=True
                        )
                    if finish.tzinfo is None:
                        finish = wall_to_utc(
                            finish.replace(second=0, microsecond=0), zone, reject_ambiguous=True
                        )
                    start, finish = (
                        start.astimezone(UTC).replace(tzinfo=None),
                        finish.astimezone(UTC).replace(tzinfo=None),
                    )
                    event_zone, all_day = "UTC", False
                else:
                    start, finish = (
                        datetime.combine(start, datetime.min.time()),
                        datetime.combine(finish, datetime.min.time()),
                    )
                    event_zone, all_day = zone, True
                if start.second or finish.second:
                    warnings.append(f"Item {index + 1}: times rounded to minute precision.")
                model = EventInput(
                    title=str(event.get("SUMMARY", "Untitled event")),
                    start_local=start.replace(second=0, microsecond=0),
                    end_local=finish.replace(second=0, microsecond=0),
                    timezone=event_zone,
                    all_day=all_day,
                    location=str(event.get("LOCATION", "")),
                    notes=str(event.get("DESCRIPTION", "")),
                    visibility="private",
                    busy=str(event.get("TRANSP", "OPAQUE")) != "TRANSPARENT",
                    reminder_minutes=[],
                )
                recurrence_id = (
                    str(event.get("RECURRENCE-ID").dt)
                    if event.get("RECURRENCE-ID")
                    else str(event.decoded("DTSTART"))
                )
                external_id = "ics/" + digest(str(event["UID"]) + "/" + recurrence_id)
                if external_id in identifiers:
                    warnings.append(f"Item {index + 1}: duplicate UID and occurrence; skipped.")
                    continue
                identifiers.add(external_id)
                rows.append(
                    {
                        "event": model.model_dump(mode="json"),
                        "external_id": external_id,
                        "exceptions": {},
                    }
                )
            except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
                warnings.append(f"Item {index + 1}: unsupported or invalid fields; skipped.")
        return self._preview(
            "ics",
            rows,
            warnings,
            key,
            {
                "source_name": payload.source_name,
                "start": str(payload.start),
                "end": str(payload.end),
                "recurrence_mode": "individual_occurrences_in_selected_range",
                "reminders": "disabled_for_imports",
            },
        )

    def apply(self, preview_id, payload, key, *, allow_backup=True):
        # Check before Store.operation can return a cached private restore receipt.
        with self.store.connection() as conn:
            source = conn.execute(
                "SELECT kind FROM import_previews WHERE id=?", (preview_id,)
            ).fetchone()
            if source and source["kind"] == "backup" and not allow_backup:
                raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)

        def apply(conn):
            row = conn.execute("SELECT * FROM import_previews WHERE id=?", (preview_id,)).fetchone()
            if not row or row["expires_at"] <= iso(self.store.clock()) or row["state"] != "pending":
                raise DomainError("IMPORT_EXPIRED", 410)
            preview = json.loads(row["data"])
            rows = preview["rows"]
            if row["kind"] == "backup" and payload.replace_matching:
                raise DomainError("RESTORE_KEEP_EXISTING", 422)
            selected = [
                r
                for r in rows
                if r["status"] == "new" or r["status"] == "changed" and payload.replace_matching
            ]
            if (
                conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]
                + sum(r["status"] == "new" for r in selected)
                > 500
            ):
                raise DomainError("EVENT_LIMIT", 422)
            created, updated = 0, 0
            for item in selected:
                document = EventInput.model_validate(item["event"]).model_dump(mode="json")
                document.update(
                    origin="import" if row["kind"] in {"ics", "google"} else "backup",
                    batch_id=None,
                    provider=row["kind"] if row["kind"] in {"ics", "google"} else None,
                    external_id=item["external_id"],
                )
                if item["existing_id"]:
                    current = self.store.event(conn, item["existing_id"])
                    if current["version"] != item["expected_version"]:
                        raise DomainError("VERSION_CONFLICT")
                    event_id = item["existing_id"]
                    # Local occurrence edits would be lost on replacement: require a new preview after resolving them.
                    if conn.execute(
                        "SELECT 1 FROM exceptions WHERE event_id=?", (event_id,)
                    ).fetchone():
                        raise DomainError("SERIES_HAS_EXCEPTIONS")
                    conn.execute(
                        "UPDATE events SET data=?,version=version+1 WHERE id=?",
                        (encode(document), event_id),
                    )
                    updated += 1
                else:
                    # A concurrently imported identical source must not create a duplicate.
                    for current in conn.execute("SELECT data FROM events WHERE deleted=0"):
                        if (
                            item["external_id"]
                            and json.loads(current[0]).get("external_id") == item["external_id"]
                        ):
                            raise DomainError("VERSION_CONFLICT")
                    event_id = item.get("restore_id") or uuid4().hex
                    if conn.execute("SELECT 1 FROM events WHERE id=?", (event_id,)).fetchone():
                        raise DomainError("VERSION_CONFLICT")
                    conn.execute(
                        "INSERT INTO events(id,data,version) VALUES(?,?,1)",
                        (event_id, encode(document)),
                    )
                    for occurrence, exception in item["exceptions"].items():
                        conn.execute(
                            "INSERT INTO exceptions VALUES(?,?,?)",
                            (event_id, occurrence, encode(exception)),
                        )
                    created += 1
            task_result = (
                self.runtime.tasks.restore(
                    conn, preview["metadata"].get("task_bundle", {"tasks": [], "evidence": []})
                )
                if row["kind"] == "backup"
                else {"created": 0, "kept": 0}
            )
            memory_result = (
                self.runtime.memory.restore(
                    conn,
                    preview["metadata"].get("memory_bundle", {"memories": [], "revisions": []}),
                )
                if row["kind"] == "backup"
                else {"created": 0, "kept": 0}
            )
            persona_result = (
                self.runtime.persona.restore(
                    conn, preview["metadata"].get("persona_bundle", {"persona": None})
                )
                if row["kind"] == "backup"
                else {"created": 0, "kept": 0}
            )
            job_result = (
                self.runtime.jobs.restore(
                    conn,
                    preview["metadata"].get(
                        "job_bundle", {"jobs": [], "events": [], "folder": None}
                    ),
                )
                if row["kind"] == "backup"
                else {"created": 0, "kept": 0}
            )
            conn.execute("UPDATE import_previews SET state='applied' WHERE id=?", (preview_id,))
            self.store.record(
                conn,
                "calendar_imported",
                details={"kind": row["kind"], "created": created, "updated": updated},
            )
            return {
                "created": created,
                "updated": updated,
                "kept": len(rows) - len(selected),
                "tasks_created": task_result["created"],
                "tasks_kept": task_result["kept"],
                "memories_created": memory_result["created"],
                "memories_kept": memory_result["kept"],
                "persona_created": persona_result["created"],
                "persona_kept": persona_result["kept"],
                "jobs_created": job_result["created"],
                "jobs_kept": job_result["kept"],
                "applied": True,
            }

        return self.store.operation(
            key, {"type": "import_apply", "preview_id": preview_id, **payload.model_dump()}, apply
        )

    def export_ics(self):
        calendar = icalendar.Calendar()
        calendar.add("prodid", "-//Group 2//Desk Companion//EN")
        calendar.add("version", "2.0")

        def component(event, key=None, exception=None):
            entry = icalendar.Event()
            current = (exception or {}).get("override") or event
            entry.add("uid", event["id"] + "@desk-companion.local")
            entry.add("dtstamp", self.store.clock())
            for field, source in [("dtstart", "start_local"), ("dtend", "end_local")]:
                value = datetime.fromisoformat(current[source])
                entry.add(
                    field,
                    value.date()
                    if current["all_day"]
                    else value.replace(tzinfo=ZoneInfo(current["timezone"])),
                )
            entry.add("summary", current["title"])
            entry.add("location", current["location"])
            entry.add("description", current["notes"])
            entry.add("class", "PRIVATE" if current["visibility"] == "private" else "PUBLIC")
            entry.add("transp", "OPAQUE" if current["busy"] else "TRANSPARENT")
            if key:
                original = datetime.fromisoformat(key)
                entry.add(
                    "recurrence-id",
                    original.date()
                    if event["all_day"]
                    else original.replace(tzinfo=ZoneInfo(event["timezone"])),
                )
                if exception.get("cancelled"):
                    entry.add("status", "CANCELLED")
                entry.add("x-desk-completed", "TRUE" if exception.get("completed") else "FALSE")
            elif event["recurrence"]["frequency"] != "none":
                rule = {
                    "freq": event["recurrence"]["frequency"].upper(),
                    "interval": event["recurrence"]["interval"],
                }
                if event["recurrence"]["until"]:
                    until = datetime.fromisoformat(event["recurrence"]["until"]).replace(
                        hour=23, minute=59, second=59
                    )
                    rule["until"] = (
                        until.date()
                        if event["all_day"]
                        else until.replace(tzinfo=ZoneInfo(event["timezone"])).astimezone(UTC)
                    )
                entry.add("rrule", rule)
            return entry

        with self.store.connection() as conn:
            events, exceptions = self.store.data(conn)
        for event in events:
            calendar.add_component(component(event))
            for key, exception in exceptions.get(event["id"], {}).items():
                calendar.add_component(component(event, key, exception))
        return calendar.to_ical()

    def backup(self):
        with self.store.connection() as conn:
            events, exceptions = self.store.data(conn)
            # Allowlist business data. Never include sessions, credentials, pairing,
            # provider secrets, the vault key, recordings or raw camera landmarks.
            payload = {
                "events": events,
                "exceptions": exceptions,
                "calendar_settings": self.store.settings(conn),
                "workspace_preferences": self.runtime.data.preferences(),
                "task_bundle": self.runtime.tasks.export(),
                "memory_bundle": self.runtime.memory.export(),
                "persona_bundle": self.runtime.persona.export(),
                "job_bundle": self.runtime.jobs.export(),
            }
        return {
            "format": "desk-companion-backup",
            "version": 1,
            "created_at": iso(self.store.clock()),
            "payload": payload,
            "sha256": digest(encode(payload)),
        }

    def preview_backup(self, payload, key):
        try:
            document = json.loads(payload.content)
            if document.get("format") != "desk-companion-backup" or document.get("version") != 1:
                raise ValueError()
            content = document["payload"]
            if not secrets.compare_digest(str(document["sha256"]), digest(encode(content))):
                raise ValueError()
            if len(content["events"]) > 500:
                raise ValueError()
            task_bundle = self.runtime.tasks.validate_backup(content.get("task_bundle", {}))
            memory_bundle = self.runtime.memory.validate_backup(
                content.get("memory_bundle", {"memories": [], "revisions": []})
            )
            persona_bundle = self.runtime.persona.validate_backup(
                content.get("persona_bundle", {"persona": None})
            )
            job_bundle = self.runtime.jobs.validate_backup(
                content.get("job_bundle", {"jobs": [], "events": [], "folder": None})
            )
            rows, ids = [], set()
            from .calendar import is_occurrence

            for event in content["events"]:
                event_id = event["id"]
                if not isinstance(event_id, str) or len(event_id) > 64 or event_id in ids:
                    raise ValueError()
                ids.add(event_id)
                allowed = {k: v for k, v in event.items() if k in EventInput.model_fields}
                model = EventInput.model_validate(allowed).model_dump(mode="json")
                exceptions = content.get("exceptions", {}).get(event_id, {})
                if len(exceptions) > 1000:
                    raise ValueError()
                for occurrence, exception in exceptions.items():
                    if not is_occurrence(model, occurrence) or set(exception) - {
                        "cancelled",
                        "completed",
                        "override",
                    }:
                        raise ValueError()
                    if "override" in exception:
                        exception["override"] = EventInput.model_validate(
                            exception["override"]
                        ).model_dump(mode="json")
                rows.append(
                    {
                        "restore_id": event_id,
                        "external_id": event.get("external_id"),
                        "event": model,
                        "exceptions": exceptions,
                    }
                )
        except (ValueError, KeyError, TypeError, AttributeError):
            raise DomainError("INVALID_BACKUP", 422) from None
        return self._preview(
            "backup",
            rows,
            [],
            key,
            {
                "created_at": document.get("created_at"),
                "restore_mode": "merge_keep_existing",
                "preferences": "kept_current",
                "task_bundle": task_bundle,
                "tasks_count": len(task_bundle["tasks"]),
                "task_followups": "restored_paused",
                "memory_bundle": memory_bundle,
                "memories_count": len(memory_bundle["memories"]),
                "memory_restore": "merge_keep_existing",
                "persona_bundle": persona_bundle,
                "persona_restore": "merge_keep_existing",
                "job_bundle": job_bundle,
                "jobs_count": len(job_bundle["jobs"]),
                "job_restore": "merge_keep_existing_running_becomes_review",
            },
        )

    def create_share(self, payload, key):
        def apply(conn):
            count = conn.execute(
                "SELECT COUNT(*) FROM calendar_shares WHERE revoked=0 AND expires_at>?",
                (iso(self.store.clock()),),
            ).fetchone()[0]
            if count >= 20:
                raise DomainError("SHARE_LIMIT", 422)
            token, share_id = secrets.token_urlsafe(32), uuid4().hex
            expires = iso(self.store.clock() + timedelta(days=payload.expires_days))
            conn.execute(
                "INSERT INTO calendar_shares VALUES(?,?,?,?,0)",
                (share_id, digest(token), encode(payload.model_dump(mode="json")), expires),
            )
            self.store.record(
                conn, "share_created", details={"share_id": share_id, "mode": payload.mode}
            )
            return {
                "id": share_id,
                "encrypted_token": self.vault.encrypt(token),
                "expires_at": expires,
            }

        result = self.store.operation(
            key, {"type": "share_create", **payload.model_dump(mode="json")}, apply
        )
        return {
            "id": result["id"],
            "token": self.vault.decrypt(result["encrypted_token"]),
            "expires_at": result["expires_at"],
        }

    def shares(self):
        with self.store.connection() as conn:
            return [
                {"id": r["id"], "expires_at": r["expires_at"], **json.loads(r["data"])}
                for r in conn.execute(
                    "SELECT * FROM calendar_shares WHERE revoked=0 AND expires_at>?",
                    (iso(self.store.clock()),),
                )
            ]

    def revoke(self, share_id, key):
        def apply(conn):
            conn.execute("UPDATE calendar_shares SET revoked=1 WHERE id=?", (share_id,))
            self.store.record(conn, "share_revoked", details={"share_id": share_id})
            return {"revoked": True}

        return self.store.operation(key, {"type": "share_revoke", "id": share_id}, apply)

    def shared(self, token):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM calendar_shares WHERE token_hash=? AND revoked=0 AND expires_at>?",
                (digest(token), iso(self.store.clock())),
            ).fetchone()
            if not row:
                raise DomainError("SHARE_UNAVAILABLE", 404)
            config, zone = json.loads(row["data"]), self.store.settings(conn)["timezone"]
            begin = datetime.fromisoformat(config["start"]).replace(tzinfo=ZoneInfo(zone))
            end = datetime.fromisoformat(config["end"]).replace(tzinfo=ZoneInfo(zone))
            events, exceptions = self.store.data(conn)
            occurrences = expand_all(events, exceptions, begin, end, zone)
        if config["mode"] == "busy":
            ranges = sorted(
                [
                    (max(o["start"], iso(begin)), min(o["end"], iso(end)))
                    for o in occurrences
                    if o["busy"] and not o["completed"]
                ]
            )
            items = []
            for start, finish in ranges:
                if items and start <= items[-1]["end"]:
                    items[-1]["end"] = max(items[-1]["end"], finish)
                else:
                    items.append({"start": start, "end": finish})
        else:
            items = [
                {k: o[k] for k in ("title", "start", "end", "all_day")}
                for o in occurrences
                if o["visibility"] == "displayable"
            ]
        return {
            "mode": config["mode"],
            "start": config["start"],
            "end": config["end"],
            "timezone": zone,
            "expires_at": row["expires_at"],
            "items": items,
        }
