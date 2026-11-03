"""Offline calendar ingest through the existing task, calendar, draft, and notice services.

One fixture event or series maps to one task and one local calendar event.
Later revisions update those same records. Advice stays a draft until the
owner confirms it, and confirmation does not accept an invite or send an RSVP.
"""

import hashlib
import json
import threading
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from ..calendar import iso, wall_to_utc
from ..notify import Notice
from ..schemas import CreateEvents, EventAction, StrictModel
from ..store import DomainError, encode
from ..tasks import OPEN, TaskAction
from ..workspace_data import is_quiet
from .fixture import (
    NAME,
    FixtureItem,
    flatten,
    item_fingerprint,
    load_fixture,
)
from .mapping import (
    advice_payload,
    advice_reasons,
    canonical_event,
    canonical_task,
    citation,
    kind_of,
    merge_event,
    new_event,
    task_for,
)

ADVICE = "calendar_advice"
APPROACHING = timedelta(hours=24)
WINDOW = timedelta(days=40)


class CalendarConnect(StrictModel):
    fixture: str = Field(pattern=NAME, max_length=64)


def _operation_key(prefix: str, material: str) -> str:
    return prefix + hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]


def _notice_id(connection_id: str, uid: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{connection_id}/{uid}/{sequence}".encode()).hexdigest()[:32]
    return "cal-" + digest


def _as_local(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


class OfflineCalendarService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        self.lock = threading.RLock()
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS offline_calendar_connections(
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    fixture_name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    history_cursor TEXT,
                    next_event INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, account_id)
                );
                CREATE TABLE IF NOT EXISTS offline_calendar_items(
                    connection_id TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    local_event_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    deadline_notified_due TEXT,
                    cancelled INTEGER NOT NULL,
                    PRIMARY KEY(connection_id, uid)
                );
                CREATE TABLE IF NOT EXISTS offline_calendar_revisions(
                    connection_id TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    PRIMARY KEY(connection_id, uid, sequence)
                );
                CREATE TABLE IF NOT EXISTS offline_calendar_conflicts(
                    connection_id TEXT NOT NULL,
                    left_uid TEXT NOT NULL,
                    right_uid TEXT NOT NULL,
                    PRIMARY KEY(connection_id, left_uid, right_uid)
                );
                CREATE TABLE IF NOT EXISTS offline_calendar_attempts(
                    id TEXT PRIMARY KEY,
                    connection_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    cursor_before TEXT,
                    cursor_after TEXT,
                    response TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                """
            )

    def _owner(self, session: str | None) -> None:
        if not session or not self.store.session_valid(session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)

    def _require_key(self, key: str) -> str:
        if not isinstance(key, str) or not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        if key.startswith("assistant-confirm/"):
            raise DomainError("RESERVED_OPERATION_ID", 422)
        return key

    def connect(self, fixture_name: str, key: str, session: str | None) -> dict:
        self._owner(session)
        key = self._require_key(key)
        fixture = load_fixture(fixture_name)

        def apply(conn):
            if conn.execute(
                "SELECT 1 FROM offline_calendar_connections WHERE provider='offline' AND account_id=?",
                (fixture.account_id,),
            ).fetchone():
                raise DomainError("CALENDAR_ALREADY_CONNECTED", 409)
            now = iso(self.store.clock())
            connection_id = uuid4().hex
            conn.execute(
                "INSERT INTO offline_calendar_connections("
                "id, provider, account_id, calendar_id, fixture_name, state, "
                "history_cursor, next_event, created_at, updated_at"
                ") VALUES(?,?,?,?,?,'connected',NULL,0,?,?)",
                (
                    connection_id,
                    "offline",
                    fixture.account_id,
                    fixture.calendar_id,
                    fixture_name,
                    now,
                    now,
                ),
            )
            self.store.record(
                conn,
                "offline_calendar_connected",
                details={"connection_id": connection_id, "fixture": fixture_name},
            )
            return {"connection": self._view(conn, connection_id), "saved": True}

        return self.store.operation(
            key, {"type": "offline_calendar_connect", "fixture": fixture_name}, apply
        )

    def revoke(self, connection_id: str, key: str, session: str | None) -> dict:
        return self._stop(connection_id, key, session, "revoked", "offline_calendar_revoked")

    def disconnect(self, connection_id: str, key: str, session: str | None) -> dict:
        return self._stop(
            connection_id, key, session, "disconnected", "offline_calendar_disconnected"
        )

    def _stop(self, connection_id: str, key: str, session: str | None, state: str, action: str):
        self._owner(session)
        key = self._require_key(key)
        with self.lock:
            return self._stop_locked(connection_id, key, state, action)

    def _stop_locked(self, connection_id: str, key: str, state: str, action: str):
        def apply(conn):
            self._row(conn, connection_id)
            conn.execute(
                "UPDATE offline_calendar_connections SET state=?, updated_at=? WHERE id=?",
                (state, iso(self.store.clock()), connection_id),
            )
            self.store.record(conn, action, details={"connection_id": connection_id})
            return {
                "connection": self._view(conn, connection_id),
                "success": True,
                "status": state,
                "reads_stopped": True,
                "saved": True,
            }

        return self.store.operation(
            key, {"type": "offline_calendar_" + state, "connection_id": connection_id}, apply
        )

    def listing(self, session: str | None) -> dict:
        self._owner(session)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id FROM offline_calendar_connections ORDER BY created_at, id"
            ).fetchall()
            return {"connections": [self._view(conn, row["id"]) for row in rows]}

    def detail(self, connection_id: str, session: str | None) -> dict:
        self._owner(session)
        with self.store.connection() as conn:
            return {"connection": self._view(conn, connection_id)}

    def sync(self, connection_id: str, key: str, session: str | None) -> dict:
        """Ingest one fixture batch. A stop, revoke, or disconnect is not success."""
        self._owner(session)
        key = self._require_key(key)
        with self.lock:
            connection = self._connection(connection_id)
            prior = self._attempt(key)
            if prior and prior["connection_id"] != connection_id:
                raise DomainError("OPERATION_ID_CONFLICT")
            if prior and prior["state"] == "applied" and prior["response"]:
                return json.loads(prior["response"])
            self._open_attempt(key, connection)
            if connection["state"] != "connected":
                response = self._result(
                    connection_id,
                    status=connection["state"],
                    success=False,
                    applied=[],
                    duplicates=[],
                    skipped=[],
                    events_read=0,
                )
                self._finish_attempt(key, "interrupted", connection["history_cursor"], response)
                return response
            fixture = load_fixture(connection["fixture_name"])
            if fixture.account_id != connection["account_id"]:
                raise DomainError("FIXTURE_INVALID", 422)
            events = flatten(fixture)
            offset = connection["next_event"]
            if offset > len(events):
                raise DomainError("FIXTURE_INVALID", 422)
            if offset == len(events):
                response = self._result(
                    connection_id,
                    status="idle",
                    success=True,
                    applied=[],
                    duplicates=[],
                    skipped=[],
                    events_read=0,
                )
                self._finish_attempt(key, "applied", connection["history_cursor"], response)
                return response
            batch_id = events[offset].batch_id
            staged = []
            events_read = 0
            index = offset
            stop = None
            pending_state = None
            resume_at = offset
            while index < len(events) and events[index].batch_id == batch_id:
                if self._connection(connection_id)["state"] != "connected":
                    stop = self._connection(connection_id)["state"]
                    resume_at = index
                    break
                events_read += 1
                event = events[index]
                if event.op in {"upsert", "cancel"} and event.item is not None:
                    staged.append(event)
                    index += 1
                    resume_at = index
                    continue
                if event.op == "interrupt":
                    stop = "interrupted"
                    resume_at = index + 1
                elif event.op == "revoke":
                    pending_state = "revoked"
                    stop = "revoked"
                    resume_at = index
                else:
                    pending_state = "disconnected"
                    stop = "disconnected"
                    resume_at = index
                break
            else:
                resume_at = index
            staged.sort(key=lambda event: (event.item.sequence, event.item.id))
            seen: set[tuple[str, int]] = set()
            applied: list[str] = []
            duplicates: list[str] = []
            skipped: list[str] = []
            for event in staged:
                identity = (event.item.id, event.item.sequence)
                if identity in seen:
                    duplicates.append(event.item.id)
                    continue
                seen.add(identity)
                outcome = self._apply(connection_id, event.op, event.item)
                if outcome == "duplicate":
                    duplicates.append(event.item.id)
                elif outcome == "skipped":
                    skipped.append(event.item.id)
                else:
                    applied.append(event.item.id)
            if pending_state:
                self._set_state(connection_id, pending_state)
            self._set_offset(connection_id, resume_at)
            if stop:
                response = self._result(
                    connection_id,
                    status=stop,
                    success=False,
                    applied=applied,
                    duplicates=duplicates,
                    skipped=skipped,
                    events_read=events_read,
                )
                self._finish_attempt(key, "interrupted", None, response)
                return response
            cursor = self._advance_cursor(connection_id)
            response = self._result(
                connection_id,
                status="applied",
                success=True,
                applied=applied,
                duplicates=duplicates,
                skipped=skipped,
                events_read=events_read,
            )
            self._finish_attempt(key, "applied", cursor, response)
            return response

    def _apply(self, connection_id: str, op: str, item: FixtureItem) -> str:
        fingerprint = item_fingerprint(item)
        with self.store.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM offline_calendar_revisions "
                "WHERE connection_id=? AND uid=? AND sequence=?",
                (connection_id, item.id, item.sequence),
            ).fetchone()
        if existing and existing["state"] in {"applied", "skipped"}:
            if existing["fingerprint"] != fingerprint:
                raise DomainError("CALENDAR_REVISION_CONFLICT", 409)
            return "duplicate" if existing["state"] == "applied" else "skipped"
        if existing and existing["fingerprint"] != fingerprint:
            raise DomainError("CALENDAR_REVISION_CONFLICT", 409)
        row = self._item(connection_id, item.id)
        if row and item.sequence < row["sequence"]:
            self._record_revision(connection_id, item, fingerprint, "skipped")
            return "skipped"
        if row and item.sequence == row["sequence"]:
            if row["fingerprint"] != fingerprint:
                raise DomainError("CALENDAR_REVISION_CONFLICT", 409)
            self._record_revision(connection_id, item, fingerprint, "applied")
            return "duplicate"
        if op == "cancel" or item.status == "cancelled":
            self._cancel(connection_id, item, fingerprint, row)
            return "applied"
        self._upsert(connection_id, item, fingerprint, row)
        return "applied"

    def _upsert(self, connection_id: str, item: FixtureItem, fingerprint: str, row) -> None:
        if row and row["cancelled"]:
            raise DomainError("CALENDAR_ITEM_CANCELLED", 409)
        if row is None:
            event = new_event(item)
            created = self._create_records(connection_id, item, event)
            task_id = created["task_id"]
            local_event_id = created["local_event_id"]
        else:
            task_id = row["task_id"]
            local_event_id = row["local_event_id"]
            event, event_changed = self._update_event(connection_id, item, local_event_id)
            self._update_task(
                connection_id, item, task_id, event, event_changed=event_changed
            )
        related, pairs = self._new_conflicts(connection_id, local_event_id, item.id)
        drafted = self._draft(connection_id, item, task_id, related)
        mark = self._notify(
            connection_id,
            item,
            task_id,
            related=related,
            drafted=drafted,
            cancelled=False,
        )
        self._finish_item(
            connection_id,
            item,
            fingerprint,
            local_event_id,
            task_id,
            kind_of(event),
            cancelled=False,
            deadline=mark,
            pairs=pairs,
        )

    def _cancel(self, connection_id: str, item: FixtureItem, fingerprint: str, row) -> None:
        if row is None:
            raise DomainError("CALENDAR_NOT_TRACKED", 404)
        if row["cancelled"]:
            self._record_revision(connection_id, item, fingerprint, "applied")
            return
        self._delete_event(connection_id, item, row["local_event_id"])
        self._cancel_task(connection_id, item, row["task_id"])
        mark = self._notify(
            connection_id,
            item,
            row["task_id"],
            related=[],
            drafted=False,
            cancelled=True,
        )
        self._finish_item(
            connection_id,
            item,
            fingerprint,
            row["local_event_id"],
            row["task_id"],
            row["kind"],
            cancelled=True,
            deadline=mark,
            pairs=[],
        )

    def _create_records(self, connection_id: str, item: FixtureItem, event) -> dict:
        created = self.store.create(
            CreateEvents(event=event),
            _operation_key("oc-new-ev-", f"{connection_id}/{item.id}"),
            origin="offline_calendar",
        )
        local_event_id = created["event_ids"][0]
        task = self.runtime.tasks.create(
            task_for(event, item, None),
            _operation_key("oc-new-tk-", f"{connection_id}/{item.id}"),
            origin="offline_calendar",
        )
        self.runtime.tasks.action(
            task["task"]["id"],
            TaskAction(
                action="note",
                expected_version=task["task"]["version"],
                note=citation(item),
            ),
            _operation_key("oc-new-note-", f"{connection_id}/{item.id}"),
            origin="offline_calendar",
        )
        return {"local_event_id": local_event_id, "task_id": task["task"]["id"]}

    def _update_event(self, connection_id: str, item: FixtureItem, local_event_id: str):
        with self.store.connection() as conn:
            current = self.store.event(conn, local_event_id)
        merged = merge_event(current, item)
        if canonical_event(current) == merged.model_dump(mode="json"):
            return merged, False
        self.store.event_action(
            local_event_id,
            EventAction(
                action="update",
                expected_version=current["version"],
                scope="series",
                event=merged,
            ),
            _operation_key("oc-ev-", f"{connection_id}/{item.id}/{item.sequence}"),
        )
        return merged, True

    def _update_task(
        self,
        connection_id: str,
        item: FixtureItem,
        task_id: str,
        event,
        *,
        event_changed: bool,
    ) -> bool:
        with self.store.connection() as conn:
            current = self.runtime.tasks.get(conn, task_id)
        merged = task_for(event, item, current)
        changed = canonical_task(current) != merged.model_dump(mode="json")
        if not changed and not event_changed:
            return False
        note = citation(item)
        if changed:
            action = TaskAction(
                action="update",
                expected_version=current["version"],
                task=merged,
                note=note,
            )
        else:
            action = TaskAction(action="note", expected_version=current["version"], note=note)
        self.runtime.tasks.action(
            task_id,
            action,
            _operation_key("oc-tk-", f"{connection_id}/{item.id}/{item.sequence}"),
            origin="offline_calendar",
        )
        return changed

    def _delete_event(self, connection_id: str, item: FixtureItem, local_event_id: str) -> None:
        with self.store.connection() as conn:
            current = self.store.event(conn, local_event_id)
        self.store.event_action(
            local_event_id,
            EventAction(action="delete", expected_version=current["version"], scope="series"),
            _operation_key("oc-del-", f"{connection_id}/{item.id}/{item.sequence}"),
        )

    def _cancel_task(self, connection_id: str, item: FixtureItem, task_id: str) -> None:
        with self.store.connection() as conn:
            current = self.runtime.tasks.get(conn, task_id)
        self.runtime.tasks.action(
            task_id,
            TaskAction(
                action="cancel",
                expected_version=current["version"],
                note=citation(item),
            ),
            _operation_key("oc-can-", f"{connection_id}/{item.id}/{item.sequence}"),
            origin="offline_calendar",
        )

    def _draft(self, connection_id: str, item: FixtureItem, task_id: str, related: list[str]) -> bool:
        if not advice_reasons(item, related):
            return False
        self.runtime.assistant.propose(
            ADVICE,
            advice_payload(item, task_id, related),
            _operation_key("oc-dr-", f"{connection_id}/{item.id}/{item.sequence}"),
        )
        return True

    def _notify(
        self,
        connection_id: str,
        item: FixtureItem,
        task_id: str,
        *,
        related: list[str],
        drafted: bool,
        cancelled: bool,
    ) -> str | None:
        with self.store.connection() as conn:
            task = self.runtime.tasks.get(conn, task_id)
        due = task.get("due_local")
        approaching = self._approaching(task)
        already = self._deadline_mark(connection_id, item.id)
        deadline_news = bool(approaching and already != due and not cancelled)
        if cancelled:
            reasons = ["cancelled"]
        else:
            reasons = []
            if related:
                reasons.append("conflict")
            if deadline_news:
                reasons.append("deadline")
            if drafted:
                reasons.append("decision")
        if not reasons:
            return None if not approaching else already
        text = _notice_text(reasons)
        related_en = (" Related events: " + ", ".join(related) + ".") if related else ""
        related_zh = ("相关日程：" + "、".join(related) + "。") if related else ""
        body_en = text["en"] + " " + citation(item) + related_en
        body_zh = text["zh"] + citation(item) + related_zh
        notice = Notice(
            _notice_id(connection_id, item.id, item.sequence),
            text["kind"],
            "Calendar update",
            "日程更新",
            body_en,
            body_zh,
            body_en,
            body_zh,
        )
        results = self.runtime.notify.publish(notice, quiet=self._quiet())
        delivered = any(row["status"] in {"delivered", "duplicate"} for row in results)
        if deadline_news and delivered:
            return due
        if not approaching:
            return None
        return already

    def _finish_item(
        self,
        connection_id: str,
        item: FixtureItem,
        fingerprint: str,
        local_event_id: str,
        task_id: str,
        kind: str,
        *,
        cancelled: bool,
        deadline: str | None,
        pairs: list[tuple[str, str]],
    ) -> None:
        with self.store.connection(write=True) as conn:
            self._insert_revision(conn, connection_id, item, fingerprint, "applied")
            if pairs:
                conn.executemany(
                    "INSERT OR IGNORE INTO offline_calendar_conflicts VALUES(?,?,?)",
                    [(connection_id, left, right) for left, right in pairs],
                )
            current = conn.execute(
                "SELECT 1 FROM offline_calendar_items WHERE connection_id=? AND uid=?",
                (connection_id, item.id),
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO offline_calendar_items("
                    "connection_id, uid, local_event_id, task_id, sequence, fingerprint, "
                    "kind, deadline_notified_due, cancelled"
                    ") VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        connection_id,
                        item.id,
                        local_event_id,
                        task_id,
                        item.sequence,
                        fingerprint,
                        kind,
                        deadline,
                        int(cancelled),
                    ),
                )
            else:
                conn.execute(
                    "UPDATE offline_calendar_items SET local_event_id=?, task_id=?, sequence=?, "
                    "fingerprint=?, kind=?, deadline_notified_due=?, cancelled=? "
                    "WHERE connection_id=? AND uid=?",
                    (
                        local_event_id,
                        task_id,
                        item.sequence,
                        fingerprint,
                        kind,
                        deadline,
                        int(cancelled),
                        connection_id,
                        item.id,
                    ),
                )

    def _record_revision(self, connection_id: str, item: FixtureItem, fingerprint: str, state: str):
        with self.store.connection(write=True) as conn:
            self._insert_revision(conn, connection_id, item, fingerprint, state)

    def _insert_revision(self, conn, connection_id: str, item: FixtureItem, fingerprint: str, state: str):
        conn.execute(
            "INSERT INTO offline_calendar_revisions("
            "connection_id, uid, sequence, fingerprint, observed_at, state"
            ") VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(connection_id, uid, sequence) DO UPDATE SET state=excluded.state",
            (
                connection_id,
                item.id,
                item.sequence,
                fingerprint,
                iso(item.observed_at),
                state,
            ),
        )

    def _new_conflicts(
        self, connection_id: str, local_event_id: str, uid: str
    ) -> tuple[list[str], list[tuple[str, str]]]:
        now = self.store.clock()
        snapshot = self.store.snapshot(now - timedelta(days=1), now - timedelta(days=1) + WINDOW)
        others: set[str] = set()
        for occurrence in snapshot["occurrences"]:
            if occurrence["id"] != local_event_id:
                continue
            for ref in occurrence.get("conflicts") or []:
                others.add(ref.split("/", 1)[0])
        mapping = self._event_uids(connection_id)
        known = self._known_pairs(connection_id)
        found: list[str] = []
        fresh: list[tuple[str, str]] = []
        for other_id in sorted(others):
            other_uid = mapping.get(other_id, other_id)
            if other_uid == uid:
                continue
            pair = tuple(sorted((uid, other_uid)))
            if pair in known:
                continue
            found.append(other_uid)
            fresh.append(pair)
        return found, fresh

    def _event_uids(self, connection_id: str) -> dict[str, str]:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT local_event_id, uid FROM offline_calendar_items WHERE connection_id=?",
                (connection_id,),
            ).fetchall()
        return {row["local_event_id"]: row["uid"] for row in rows}

    def _known_pairs(self, connection_id: str) -> set[tuple[str, str]]:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT left_uid, right_uid FROM offline_calendar_conflicts WHERE connection_id=?",
                (connection_id,),
            ).fetchall()
        return {(row["left_uid"], row["right_uid"]) for row in rows}

    def _approaching(self, task: dict) -> bool:
        if task.get("status") not in OPEN or not task.get("due_local"):
            return False
        due = wall_to_utc(_as_local(task["due_local"]), task["timezone"], reject_ambiguous=True)
        return due - self.store.clock() <= APPROACHING

    def _quiet(self) -> bool:
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(self.runtime.data.preferences(), self.store.clock().astimezone(zone))

    def _deadline_mark(self, connection_id: str, uid: str) -> str | None:
        row = self._item(connection_id, uid)
        return None if row is None else row["deadline_notified_due"]

    def _item(self, connection_id: str, uid: str):
        with self.store.connection() as conn:
            return conn.execute(
                "SELECT * FROM offline_calendar_items WHERE connection_id=? AND uid=?",
                (connection_id, uid),
            ).fetchone()

    def _connection(self, connection_id: str) -> dict:
        with self.store.connection() as conn:
            row = self._row(conn, connection_id)
            return {
                "id": row["id"],
                "state": row["state"],
                "fixture_name": row["fixture_name"],
                "account_id": row["account_id"],
                "history_cursor": row["history_cursor"],
                "next_event": row["next_event"],
            }

    def _row(self, conn, connection_id: str):
        row = conn.execute(
            "SELECT * FROM offline_calendar_connections WHERE id=?", (connection_id,)
        ).fetchone()
        if row is None:
            raise DomainError("CALENDAR_NOT_FOUND", 404)
        return row

    def _view(self, conn, connection_id: str) -> dict:
        row = self._row(conn, connection_id)
        items = []
        for item in conn.execute(
            "SELECT uid, kind, task_id, local_event_id, sequence "
            "FROM offline_calendar_items WHERE connection_id=? ORDER BY uid",
            (connection_id,),
        ):
            items.append(
                {
                    "uid": item["uid"],
                    "kind": item["kind"],
                    "task_id": item["task_id"],
                    "event_id": item["local_event_id"],
                    "sequence": item["sequence"],
                    "work_item": {"kind": "task", "id": item["task_id"]},
                }
            )
        return {
            "id": row["id"],
            "provider": row["provider"],
            "account_id": row["account_id"],
            "calendar_id": row["calendar_id"],
            "fixture": row["fixture_name"],
            "state": row["state"],
            "history_cursor": row["history_cursor"],
            "next_event": row["next_event"],
            "items": items,
        }

    def _result(
        self,
        connection_id: str,
        *,
        status: str,
        success: bool,
        applied: list[str],
        duplicates: list[str],
        skipped: list[str],
        events_read: int,
    ) -> dict:
        with self.store.connection() as conn:
            connection = self._view(conn, connection_id)
        return {
            "success": success,
            "status": status,
            "events_read": events_read,
            "applied_uids": applied,
            "duplicate_uids": duplicates,
            "skipped_uids": skipped,
            "connection": connection,
            "sent": False,
            "accepted": False,
        }

    def _attempt(self, key: str):
        with self.store.connection() as conn:
            return conn.execute(
                "SELECT * FROM offline_calendar_attempts WHERE id=?", (key,)
            ).fetchone()

    def _open_attempt(self, key: str, connection: dict) -> None:
        with self.store.connection(write=True) as conn:
            if conn.execute(
                "SELECT 1 FROM offline_calendar_attempts WHERE id=?", (key,)
            ).fetchone():
                return
            conn.execute(
                "INSERT INTO offline_calendar_attempts("
                "id, connection_id, state, cursor_before, cursor_after, response, "
                "started_at, finished_at"
                ") VALUES(?,?,'open',?,NULL,NULL,?,NULL)",
                (key, connection["id"], connection["history_cursor"], iso(self.store.clock())),
            )

    def _finish_attempt(self, key: str, state: str, cursor_after: str | None, response: dict) -> None:
        with self.store.connection(write=True) as conn:
            current = conn.execute(
                "SELECT state FROM offline_calendar_attempts WHERE id=?", (key,)
            ).fetchone()
            if current and current["state"] == "applied" and state != "applied":
                raise DomainError("OPERATION_ID_CONFLICT")
            conn.execute(
                "UPDATE offline_calendar_attempts SET state=?, cursor_after=?, response=?, "
                "finished_at=? WHERE id=?",
                (state, cursor_after, encode(response), iso(self.store.clock()), key),
            )

    def _set_state(self, connection_id: str, state: str) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE offline_calendar_connections SET state=?, updated_at=? WHERE id=?",
                (state, iso(self.store.clock()), connection_id),
            )

    def _set_offset(self, connection_id: str, offset: int) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE offline_calendar_connections SET next_event=?, updated_at=? WHERE id=?",
                (offset, iso(self.store.clock()), connection_id),
            )

    def _advance_cursor(self, connection_id: str) -> str | None:
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT MAX(sequence) FROM offline_calendar_revisions "
                "WHERE connection_id=? AND state='applied'",
                (connection_id,),
            ).fetchone()
            cursor = None if row[0] is None else str(row[0])
            conn.execute(
                "UPDATE offline_calendar_connections SET history_cursor=?, updated_at=? WHERE id=?",
                (cursor, iso(self.store.clock()), connection_id),
            )
            return cursor


def _notice_text(reasons: list[str]) -> dict:
    phrases = {
        "conflict": ("New schedule conflict.", "出现新的日程冲突。"),
        "deadline": ("Deadline is within 24 hours.", "有一个期限在24小时内。"),
        "decision": ("Needs a decision.", "需要一个决定。"),
        "cancelled": ("Cancelled meeting that had a task.", "已取消一场已有事务的会议。"),
    }
    english = " ".join(phrases[reason][0] for reason in reasons)
    chinese = "".join(phrases[reason][1] for reason in reasons)
    if "cancelled" in reasons:
        kind = "calendar_cancelled"
    elif "conflict" in reasons:
        kind = "calendar_conflict"
    elif "deadline" in reasons:
        kind = "calendar_deadline"
    else:
        kind = "calendar_decision"
    return {"en": english, "zh": chinese, "kind": kind}


def offline_calendar_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/offline-calendar", dependencies=[Depends(owner)])
    service = runtime.offline_calendar

    def session_of(request: Request) -> str | None:
        return request.cookies.get("desk_companion_session")

    @router.get("/connections")
    def listing(request: Request):
        return service.listing(session_of(request))

    @router.post("/connections")
    def connect(payload: CalendarConnect, request: Request, key=Depends(operation_id)):
        return service.connect(payload.fixture, key, session_of(request))

    @router.get("/connections/{connection_id}")
    def detail(connection_id: str, request: Request):
        return service.detail(connection_id, session_of(request))

    @router.post("/connections/{connection_id}/sync")
    def sync(connection_id: str, request: Request, key=Depends(operation_id)):
        return service.sync(connection_id, key, session_of(request))

    @router.post("/connections/{connection_id}/revocation")
    def revoke(connection_id: str, request: Request, key=Depends(operation_id)):
        return service.revoke(connection_id, key, session_of(request))

    @router.post("/connections/{connection_id}/disconnection")
    def disconnect(connection_id: str, request: Request, key=Depends(operation_id)):
        return service.disconnect(connection_id, key, session_of(request))

    return router


def proposal_kind(runtime, proposal_id: str) -> str | None:
    with runtime.store.connection() as conn:
        row = conn.execute(
            "SELECT kind FROM assistant_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
    return None if row is None else row["kind"]


def visible_proposals(proposals: list[dict], principal: dict) -> list[dict]:
    if principal.get("kind") == "owner":
        return proposals
    return [item for item in proposals if item.get("kind") != ADVICE]
