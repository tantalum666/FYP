"""Offline quotes for one trip, on the existing task service.

A quote is not a hold. A hold is not a payment. A payment failure is not a
ticket. A fixture receipt is not a live airline ticket. Nothing here calls a
provider, a merchant, or a card.
"""

import hashlib
import json
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from ..calendar import iso
from ..store import DomainError, encode
from ..tasks import TaskInput
from ..workspace_data import is_quiet
from .fixtures import (
    TERMS,
    FixtureCatalog,
    catalog_from_env,
    event_body,
    fingerprint,
    quote_id,
)
from .notices import TripNotices, notice_id
from ..notify import Notice

CONNECTION_LIMIT = 20
PURCHASE = "not_performed"


def _op(prefix: str, *parts: str) -> str:
    material = "/".join(parts)
    return prefix + hashlib.sha256(material.encode()).hexdigest()[:40]


def _instant(local: str, zone: str) -> datetime:
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone))


def _task_fields(event) -> dict:
    provided = {}
    for name in ("next_step", "waiting_for"):
        if name in event.model_fields_set:
            provided[name] = getattr(event, name)
    return provided


def _merge_terms(current: dict | None, event, currency: str) -> dict:
    terms = {key: None for key in TERMS}
    if current:
        terms.update({key: current.get(key) for key in TERMS})
    terms["currency"] = currency
    for key in TERMS:
        if key != "currency" and key in event.model_fields_set:
            terms[key] = getattr(event, key)
    return terms


def _notice_copy(reason: str, route: str, fixture_id: str, stamp: str) -> Notice:
    titles = {
        "quote": ("Fare to review", "票价待核对"),
        "reprice": ("Fare changed", "票价已变化"),
        "schedule_change": ("Itinerary changed", "行程已变化"),
        "payment_failed": ("Payment failed", "付款失败"),
        "ticketed": ("Fixture receipt recorded", "已记下夹具回执"),
        "ticket_blocked": ("Ticket event not applied", "出票事件未生效"),
    }
    details = {
        "quote": ("It is not held or ticketed.", "尚未保留，也未出票。"),
        "reprice": (
            "The earlier approval does not cover this fare.",
            "先前的同意不再覆盖这份票价。",
        ),
        "schedule_change": (
            "Review the new times. The earlier approval does not cover them.",
            "请核对新时间。先前的同意不再覆盖。",
        ),
        "payment_failed": ("This trip is not ticketed.", "这次行程没有出票。"),
        "ticketed": ("This is not a live ticket.", "这不是真实机票。"),
        "ticket_blocked": (
            "The approved quote did not match, so nothing was ticketed.",
            "已同意的报价对不上，因此没有出票。",
        ),
    }
    title = titles[reason]
    detail = details[reason]
    return Notice(
        id="",
        kind="trip",
        title_en=title[0],
        title_zh=title[1],
        body_en=f"{route}. Fixture {fixture_id} at {stamp}. {detail[0]} No card was charged.",
        body_zh=f"{route}。夹具 {fixture_id}，观察时间 {stamp}。{detail[1]}没有扣款。",
        reason_en=f"Trip {reason} from fixture {fixture_id}.",
        reason_zh=f"行程{reason}，来源夹具 {fixture_id}。",
    )


def _event_note(fixture_id: str, event, outcome: str, booking_state: str) -> str:
    if outcome == "blocked":
        detail = "It was not ticketed."
    elif booking_state == "payment_failed":
        detail = "Payment failed. It was not ticketed."
    elif booking_state == "ticketed":
        detail = "A fixture receipt was recorded. This is not a live ticket."
    elif booking_state == "changed":
        detail = "The itinerary changed. An earlier approval does not cover it."
    elif booking_state == "held":
        detail = "The fare is held. No card was charged."
    else:
        detail = "The fare is recorded. It is not held or ticketed."
    stamp = iso(event.observed_at)
    note = (
        f"Source fixture {fixture_id} event {event.event_id} observed at {stamp}. "
        f"{detail} No card was charged."
    )
    return note[:2000]


class TravelQuoteService:
    def __init__(self, runtime, catalog: FixtureCatalog | None = None):
        self.runtime, self.store = runtime, runtime.store
        self.catalog = catalog or catalog_from_env()
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trip_connections (
                    id TEXT PRIMARY KEY,
                    fixture_id TEXT NOT NULL,
                    itinerary_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    cursor_seq INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    session_hash TEXT NOT NULL,
                    task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trip_itinerary (
                    connection_id TEXT PRIMARY KEY,
                    terms TEXT NOT NULL,
                    quote_id TEXT NOT NULL,
                    booking_state TEXT NOT NULL,
                    hold_quote_id TEXT,
                    ticket_receipt TEXT,
                    ticket_quote_id TEXT,
                    payment_failure TEXT
                );
                CREATE TABLE IF NOT EXISTS trip_applied (
                    connection_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    PRIMARY KEY (connection_id, event_id)
                );
                CREATE TABLE IF NOT EXISTS trip_buffer (
                    connection_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    body TEXT NOT NULL,
                    PRIMARY KEY (connection_id, event_id)
                );
                """
            )
        self.notices = TripNotices(runtime)

    def _guard(self, principal) -> None:
        self.runtime.personal_context.require_visible(principal)
        if not self.store.session_valid(principal.get("session")):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)

    def _connection_row(self, conn, connection_id: str):
        row = conn.execute(
            "SELECT * FROM trip_connections WHERE id=?", (connection_id,)
        ).fetchone()
        if row is None:
            raise DomainError("TRIP_CONNECTION_NOT_FOUND", 404)
        return row

    def _connection(self, connection_id: str) -> dict:
        with self.store.connection() as conn:
            return dict(self._connection_row(conn, connection_id))

    def _itinerary_row(self, conn, connection_id: str):
        return conn.execute(
            "SELECT * FROM trip_itinerary WHERE connection_id=?", (connection_id,)
        ).fetchone()

    def _view_itinerary(self, row) -> dict | None:
        if row is None:
            return None
        terms = json.loads(row["terms"])
        receipt = row["ticket_receipt"]
        return {
            "terms": terms,
            "quote_id": row["quote_id"],
            "booking_state": row["booking_state"],
            "held_covers": row["hold_quote_id"] == row["quote_id"]
            and row["booking_state"] == "held",
            "approval_stale": bool(row["hold_quote_id"])
            and row["hold_quote_id"] != row["quote_id"],
            "ticketed": row["booking_state"] == "ticketed",
            "ticket_receipt": receipt,
            "receipt_covers_quote": bool(receipt) and row["ticket_quote_id"] == row["quote_id"],
            "payment_failure": row["payment_failure"],
            "live_ticket": False,
        }

    def _snapshot_body(self, conn, connection_id: str) -> dict:
        connection = dict(self._connection_row(conn, connection_id))
        itinerary = self._view_itinerary(self._itinerary_row(conn, connection_id))
        task_version = None
        if connection["task_id"]:
            task = self.runtime.tasks.get(conn, connection["task_id"])
            task_version = task["version"]
        buffered = [
            {"event_id": row["event_id"], "seq": row["seq"]}
            for row in conn.execute(
                "SELECT event_id, seq FROM trip_buffer WHERE connection_id=? ORDER BY seq",
                (connection_id,),
            )
        ]
        return {
            "connection": {
                "id": connection["id"],
                "fixture_id": connection["fixture_id"],
                "itinerary_id": connection["itinerary_id"],
                "state": connection["state"],
                "cursor_seq": connection["cursor_seq"],
                "currency": connection["currency"],
                "task_id": connection["task_id"],
            },
            "itinerary": itinerary,
            "task_version": task_version,
            "buffered": buffered,
            "purchase": PURCHASE,
        }

    def listing(self, principal) -> dict:
        self._guard(principal)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id, fixture_id, itinerary_id, state, cursor_seq, currency, task_id "
                "FROM trip_connections ORDER BY created_at, id"
            ).fetchall()
        return {"connections": [dict(row) for row in rows], "purchase": PURCHASE}

    def snapshot(self, connection_id: str, principal) -> dict:
        self._guard(principal)
        with self.store.connection() as conn:
            return self._snapshot_body(conn, connection_id)

    def connect(self, fixture_id: str, key: str, principal) -> dict:
        self._guard(principal)
        session_hash = hashlib.sha256(principal["session"].encode()).hexdigest()

        def apply(conn):
            fixture = self.catalog.load(fixture_id)
            existing = conn.execute(
                "SELECT id FROM trip_connections WHERE fixture_id=? AND state='connected'",
                (fixture.fixture_id,),
            ).fetchone()
            if existing:
                body = self._snapshot_body(conn, existing["id"])
                body["saved"] = False
                return body
            count = conn.execute("SELECT COUNT(*) FROM trip_connections").fetchone()[0]
            if count >= CONNECTION_LIMIT:
                raise DomainError("TRIP_CONNECTION_LIMIT", 422)
            now = iso(self.store.clock())
            connection_id = uuid4().hex
            conn.execute(
                "INSERT INTO trip_connections VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    connection_id,
                    fixture.fixture_id,
                    fixture.itinerary_id,
                    "connected",
                    0,
                    fixture.currency,
                    session_hash,
                    None,
                    now,
                    now,
                ),
            )
            self.store.record(conn, "trip_connected", details={"connection_id": connection_id})
            body = self._snapshot_body(conn, connection_id)
            body["saved"] = True
            return body

        return self.store.operation(key, {"type": "trip_connect", "fixture_id": fixture_id}, apply)

    def revoke(self, connection_id: str, key: str, principal) -> dict:
        self._guard(principal)
        self._connection(connection_id)

        def apply(conn):
            row = self._connection_row(conn, connection_id)
            if row["state"] != "revoked":
                conn.execute(
                    "UPDATE trip_connections SET state='revoked', updated_at=? WHERE id=?",
                    (iso(self.store.clock()), connection_id),
                )
            self.store.record(conn, "trip_revoked", details={"connection_id": connection_id})
            return {
                "connection_id": connection_id,
                "state": "revoked",
                "completed": False,
                "purchase": PURCHASE,
            }

        return self.store.operation(
            key, {"type": "trip_revoke", "connection_id": connection_id}, apply
        )

    def sync(self, connection_id: str, principal, disconnect_after: int | None = None) -> dict:
        """Apply the next contiguous fixture events.

        The cursor moves only with a committed event. disconnect_after 0 does
        not open the file and is not a completed sync.
        """
        self._guard(principal)
        connection = self._connection(connection_id)
        if connection["state"] != "connected":
            return self._report(connection_id, completed=False, stopped="revoked", applied=[])
        if disconnect_after == 0:
            return self._report(
                connection_id, completed=False, stopped="disconnected", applied=[]
            )
        fixture = self.catalog.load(connection["fixture_id"])
        if (
            fixture.itinerary_id != connection["itinerary_id"]
            or fixture.currency != connection["currency"]
        ):
            raise DomainError("TRIP_FIXTURE_INVALID", 422)
        pending = self._pending(connection_id, fixture)
        cursor = connection["cursor_seq"]
        applied = []
        while True:
            self._guard(principal)
            if self._connection(connection_id)["state"] != "connected":
                self._flush_buffer(connection_id, pending, cursor)
                return self._report(connection_id, completed=False, stopped="revoked", applied=applied)
            if disconnect_after is not None and len(applied) >= disconnect_after:
                self._flush_buffer(connection_id, pending, cursor)
                return self._report(
                    connection_id, completed=False, stopped="disconnected", applied=applied
                )
            event = pending.get(cursor + 1)
            if event is None:
                self._flush_buffer(connection_id, pending, cursor)
                held = any(seq > cursor for seq in pending)
                return self._report(
                    connection_id,
                    completed=not held,
                    stopped="gap" if held else None,
                    applied=applied,
                )
            applied.append(self._apply_event(connection, fixture, event))
            pending.pop(cursor + 1, None)
            cursor += 1

    def hold(self, connection_id: str, payload, key: str, principal) -> dict:
        """Approve the quote the owner is looking at. This does not pay or ticket."""
        self._guard(principal)
        connection = self._connection(connection_id)
        if connection["state"] != "connected":
            raise DomainError("TRIP_REVOKED", 409)
        provided = {}
        if "next_step" in payload.model_fields_set:
            provided["next_step"] = payload.next_step
        if "waiting_for" in payload.model_fields_set:
            provided["waiting_for"] = payload.waiting_for

        def apply(conn):
            row = self._connection_row(conn, connection_id)
            if row["state"] != "connected":
                raise DomainError("TRIP_REVOKED", 409)
            current = self._itinerary_row(conn, connection_id)
            if current is None or current["quote_id"] != payload.quote_id:
                raise DomainError("TRIP_QUOTE_CHANGED", 409)
            if current["booking_state"] == "ticketed":
                raise DomainError("TRIP_ALREADY_TICKETED", 409)
            if (
                current["booking_state"] == "held"
                and current["hold_quote_id"] == payload.quote_id
                and not provided
            ):
                task = self.runtime.tasks.get(conn, row["task_id"])
                if task["version"] != payload.expected_task_version:
                    raise DomainError("VERSION_CONFLICT")
                body = self._snapshot_body(conn, connection_id)
                body["saved"] = False
                return body
            if not row["task_id"]:
                raise DomainError("TRIP_QUOTE_REQUIRED", 422)
            note = (
                f"Owner approved quote {payload.quote_id} from fixture {row['fixture_id']}. "
                "No card was charged and no ticket was bought."
            )
            self._merge_task(
                conn,
                row["task_id"],
                payload.expected_task_version,
                provided,
                note,
                "travel_hold",
            )
            conn.execute(
                "UPDATE trip_itinerary SET booking_state='held', hold_quote_id=? "
                "WHERE connection_id=?",
                (payload.quote_id, connection_id),
            )
            self.store.record(
                conn,
                "trip_held",
                details={"connection_id": connection_id, "quote_id": payload.quote_id},
            )
            body = self._snapshot_body(conn, connection_id)
            body["saved"] = True
            return body

        return self.store.operation(
            key,
            {
                "type": "trip_hold",
                "connection_id": connection_id,
                "quote_id": payload.quote_id,
                "expected_task_version": payload.expected_task_version,
                "provided": provided,
            },
            apply,
        )

    def release_quiet_notices(self) -> None:
        self.notices.release(quiet=self._quiet())

    def _quiet(self) -> bool:
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(self.runtime.data.preferences(), self.store.clock().astimezone(zone))

    def _report(self, connection_id, *, completed, stopped, applied) -> dict:
        connection = self._connection(connection_id)
        return {
            "connection_id": connection_id,
            "cursor": connection["cursor_seq"],
            "completed": completed,
            "stopped": stopped,
            "applied": applied,
            "purchase": PURCHASE,
        }

    def _pending(self, connection_id: str, fixture) -> dict:
        with self.store.connection() as conn:
            applied = {
                row["event_id"]: row["fingerprint"]
                for row in conn.execute(
                    "SELECT event_id, fingerprint FROM trip_applied WHERE connection_id=?",
                    (connection_id,),
                )
            }
            buffered = [
                json.loads(row["body"])
                for row in conn.execute(
                    "SELECT body FROM trip_buffer WHERE connection_id=? ORDER BY seq",
                    (connection_id,),
                )
            ]
        from .fixtures import TripEvent

        pending, seen = {}, {}
        events = [TripEvent.model_validate(body) for body in buffered]
        events.extend(fixture.events)
        for event in events:
            digest = fingerprint(event)
            previous = seen.get(event.event_id)
            if previous is not None and previous != digest:
                raise DomainError("TRIP_EVENT_CONFLICT", 409)
            stored = applied.get(event.event_id)
            if stored is not None:
                if stored != digest:
                    raise DomainError("TRIP_EVENT_CONFLICT", 409)
                continue
            if event.event_id in seen:
                continue
            if event.seq in pending and pending[event.seq].event_id != event.event_id:
                raise DomainError("TRIP_FIXTURE_INVALID", 422)
            seen[event.event_id] = digest
            pending[event.seq] = event
        return pending

    def _flush_buffer(self, connection_id: str, pending: dict, cursor: int) -> None:
        held = [pending[seq] for seq in sorted(pending) if seq > cursor]
        digest = hashlib.sha256(
            encode(
                [
                    {"event_id": event.event_id, "seq": event.seq, "fp": fingerprint(event)}
                    for event in held
                ]
            ).encode()
        ).hexdigest()

        def apply(conn):
            conn.execute("DELETE FROM trip_buffer WHERE connection_id=?", (connection_id,))
            for event in held:
                conn.execute(
                    "INSERT INTO trip_buffer VALUES(?,?,?,?,?)",
                    (
                        connection_id,
                        event.seq,
                        event.event_id,
                        fingerprint(event),
                        encode(event_body(event)),
                    ),
                )
            return {"buffered": len(held)}

        self.store.operation(
            _op("tb", connection_id, str(cursor), digest),
            {"type": "trip_buffer", "connection_id": connection_id, "cursor": cursor},
            apply,
        )

    def _apply_event(self, connection, fixture, event) -> dict:
        with self.store.connection() as conn:
            current = self._itinerary_row(conn, connection["id"])
            old_terms = json.loads(current["terms"]) if current else None
        terms = _merge_terms(old_terms, event, fixture.currency)
        if any(terms[key] in (None, "") for key in TERMS):
            raise DomainError("TRIP_QUOTE_INCOMPLETE", 422)
        depart = _instant(terms["depart_local"], terms["timezone"])
        arrive = _instant(terms["arrive_local"], terms["arrive_timezone"])
        if arrive <= depart:
            raise DomainError("TRIP_ITINERARY_INVALID", 422)
        new_quote = quote_id(terms)
        old_quote = current["quote_id"] if current else None
        transition = _transition(current, event, old_quote, new_quote)
        route = f"{terms['origin']} to {terms['destination']}"
        note = _event_note(fixture.fixture_id, event, transition["outcome"], transition["state"])
        provided = _task_fields(event)
        provided["title"] = route
        digest = fingerprint(event)
        stamp = iso(event.observed_at)

        def apply(conn):
            existing = conn.execute(
                "SELECT fingerprint FROM trip_applied WHERE connection_id=? AND event_id=?",
                (connection["id"], event.event_id),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != digest:
                    raise DomainError("TRIP_EVENT_CONFLICT", 409)
                return {"event_id": event.event_id, "duplicate": True}
            row = self._connection_row(conn, connection["id"])
            if row["cursor_seq"] + 1 != event.seq:
                raise DomainError("TRIP_CURSOR_CONFLICT", 409)
            task_id = row["task_id"]
            if task_id is None:
                task = self._insert_task(conn, route, terms["timezone"], provided, note)
                task_id = task["id"]
            elif transition["outcome"] != "unchanged" or _task_fields(event):
                task = self.runtime.tasks.get(conn, task_id)
                self._merge_task(conn, task_id, task["version"], provided, note, "travel_fixture")
            now = iso(self.store.clock())
            if current is None:
                conn.execute(
                    "INSERT INTO trip_itinerary VALUES(?,?,?,?,?,?,?,?)",
                    (
                        connection["id"],
                        encode(terms),
                        new_quote,
                        transition["state"],
                        transition["hold"],
                        transition["receipt"],
                        transition["ticket_quote"],
                        transition["failure"],
                    ),
                )
            else:
                conn.execute(
                    "UPDATE trip_itinerary SET terms=?, quote_id=?, booking_state=?, "
                    "hold_quote_id=?, ticket_receipt=?, ticket_quote_id=?, payment_failure=? "
                    "WHERE connection_id=?",
                    (
                        encode(terms),
                        new_quote,
                        transition["state"],
                        transition["hold"],
                        transition["receipt"],
                        transition["ticket_quote"],
                        transition["failure"],
                        connection["id"],
                    ),
                )
            conn.execute(
                "INSERT INTO trip_applied VALUES(?,?,?,?,?,?)",
                (connection["id"], event.event_id, event.seq, digest, transition["outcome"], now),
            )
            conn.execute(
                "DELETE FROM trip_buffer WHERE connection_id=? AND event_id=?",
                (connection["id"], event.event_id),
            )
            conn.execute(
                "UPDATE trip_connections SET cursor_seq=?, task_id=?, updated_at=? WHERE id=?",
                (event.seq, task_id, now, connection["id"]),
            )
            self.store.record(
                conn,
                "trip_event",
                details={
                    "connection_id": connection["id"],
                    "event_id": event.event_id,
                    "outcome": transition["outcome"],
                },
            )
            return {
                "event_id": event.event_id,
                "seq": event.seq,
                "outcome": transition["outcome"],
                "booking_state": transition["state"],
                "quote_id": new_quote,
                "duplicate": False,
            }

        result = self.store.operation(
            _op("te", connection["id"], event.event_id, digest),
            {
                "type": "trip_event",
                "connection_id": connection["id"],
                "event_id": event.event_id,
                "fingerprint": digest,
            },
            apply,
        )
        if transition["notice"] and not result.get("duplicate"):
            notice = _notice_copy(transition["notice"], route, fixture.fixture_id, stamp)
            notice = Notice(
                id=notice_id(connection["id"], event.event_id),
                kind=notice.kind,
                title_en=notice.title_en,
                title_zh=notice.title_zh,
                body_en=notice.body_en,
                body_zh=notice.body_zh,
                reason_en=notice.reason_en,
                reason_zh=notice.reason_zh,
            )
            self.notices.publish(
                connection["id"], event.event_id, notice, quiet=self._quiet()
            )
        return {
            "event_id": event.event_id,
            "seq": event.seq,
            "outcome": result.get("outcome", transition["outcome"]),
            "booking_state": result.get("booking_state", transition["state"]),
            "quote_id": result.get("quote_id", new_quote),
        }

    def _insert_task(self, conn, title: str, timezone: str, provided: dict, note: str):
        payload = {
            "title": title,
            "timezone": timezone,
            "follow_up_enabled": False,
            "visibility": "private",
        }
        payload.update({key: value for key, value in provided.items() if key != "title"})
        data = TaskInput.model_validate(payload).model_dump(mode="json")
        if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] >= 500:
            raise DomainError("TASK_LIMIT", 422)
        task_id = uuid4().hex
        now = iso(self.store.clock())
        conn.execute(
            "INSERT INTO tasks VALUES(?,?,1,?,0,?,?,?)",
            (task_id, encode(data), data["status"], None, now, now),
        )
        self.runtime.tasks.evidence(conn, task_id, 1, "created", note, "travel_fixture")
        return self.runtime.tasks.get(conn, task_id)

    def _merge_task(self, conn, task_id, expected_version, provided, note, source):
        old = self.runtime.tasks.get(conn, task_id)
        if expected_version is not None and old["version"] != expected_version:
            raise DomainError("VERSION_CONFLICT")
        data = {key: old[key] for key in TaskInput.model_fields}
        if "completion_source" in old:
            data["completion_source"] = old["completion_source"]
        changed = False
        for key, value in provided.items():
            if key not in TaskInput.model_fields:
                continue
            if data.get(key) != value:
                data[key] = value
                changed = True
        if changed:
            parsed = TaskInput.model_validate(
                {key: data[key] for key in TaskInput.model_fields}
            ).model_dump(mode="json")
            data.update(parsed)
            if "completion_source" in old:
                data["completion_source"] = old["completion_source"]
            version = old["version"] + 1
            conn.execute(
                "UPDATE tasks SET data=?, version=?, status=?, updated_at=? WHERE id=?",
                (encode(data), version, data["status"], iso(self.store.clock()), task_id),
            )
            self.runtime.tasks.evidence(conn, task_id, version, "update", note, source)
        else:
            self.runtime.tasks.evidence(conn, task_id, old["version"], "note", note, source)
        return self.runtime.tasks.get(conn, task_id)


def _transition(current, event, old_quote, new_quote) -> dict:
    if current is None:
        if event.kind != "quote":
            raise DomainError("TRIP_QUOTE_REQUIRED", 422)
        return {
            "state": "quoted",
            "hold": None,
            "receipt": None,
            "ticket_quote": None,
            "failure": None,
            "outcome": "recorded",
            "notice": "quote",
        }
    state = current["booking_state"]
    hold = current["hold_quote_id"]
    receipt = current["ticket_receipt"]
    ticket_quote = current["ticket_quote_id"]
    failure = current["payment_failure"]
    base = {
        "state": state,
        "hold": hold,
        "receipt": receipt,
        "ticket_quote": ticket_quote,
        "failure": failure,
        "outcome": "unchanged",
        "notice": None,
    }
    if event.kind == "payment_failed":
        if state == "ticketed":
            return {**base, "outcome": "blocked", "notice": "ticket_blocked"}
        return {
            **base,
            "state": "payment_failed",
            "failure": event.reason,
            "outcome": "recorded",
            "notice": "payment_failed",
        }
    if event.kind == "ticketed":
        if (
            event.covers_quote == new_quote
            and hold == new_quote
            and state == "held"
            and receipt is None
        ):
            return {
                **base,
                "state": "ticketed",
                "receipt": event.receipt_id,
                "ticket_quote": new_quote,
                "outcome": "recorded",
                "notice": "ticketed",
            }
        return {**base, "outcome": "blocked", "notice": "ticket_blocked"}
    if old_quote == new_quote:
        return base
    notice = "schedule_change" if event.kind == "schedule_change" else "reprice"
    if event.kind == "quote":
        notice = "quote"
    if state == "ticketed" or (receipt and ticket_quote and ticket_quote != new_quote):
        return {**base, "state": "changed", "outcome": "recorded", "notice": notice}
    return {**base, "state": "quoted", "outcome": "recorded", "notice": notice}
