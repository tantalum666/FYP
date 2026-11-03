"""Incremental offline shopping ingest onto TaskService, Work and notices.

One tracked product or order keeps one task and one paused Work run. Later
fixture events update that same pair. Advice is an owner-confirmed draft.
Nothing in this module places an order or calls a store.
"""

import hashlib
import json
from uuid import uuid4
from zoneinfo import ZoneInfo

from ..agent_run_schemas import RunAction, RunCreate
from ..calendar import iso
from ..notify import Notice
from ..store import DomainError, encode
from ..tasks import TaskAction, TaskInput
from ..workspace_data import is_quiet
from .fixtures import (
    FixtureCatalog,
    ShoppingEvent,
    advice_note,
    catalog_from_env,
    display_title,
    fingerprint,
    observed_stamp,
    subject_key,
)

PROVIDED_FIELDS = frozenset({"status", "waiting_for", "next_step", "title"})
CONNECTION_LIMIT = 20


def _op(prefix: str, *parts: str) -> str:
    material = "/".join(parts)
    return prefix + hashlib.sha256(material.encode()).hexdigest()[:32]


def is_shopping_proposal(data) -> bool:
    return isinstance(data, dict) and isinstance(data.get("shopping"), dict)


def prepare_shopping_confirmation(runtime, payload: dict) -> dict:
    """Merge only fields the fixture event provided onto the live task.

    Omitted task fields stay as they are at confirmation time. The draft does
    not carry a second copy that could blank them.
    """
    shopping = payload.get("shopping")
    if not is_shopping_proposal(payload):
        raise DomainError("SHOPPING_DRAFT_REQUIRED", 422)
    provided = shopping.get("provided_fields") or {}
    if not isinstance(provided, dict) or any(key not in PROVIDED_FIELDS for key in provided):
        raise DomainError("SHOPPING_DRAFT_REQUIRED", 422)
    note = shopping.get("note")
    if not isinstance(note, str) or not note.strip():
        raise DomainError("SHOPPING_DRAFT_REQUIRED", 422)
    with runtime.store.connection() as conn:
        task = runtime.tasks.get(conn, payload["task_id"])
    if provided:
        base = {name: task[name] for name in TaskInput.model_fields if name in task}
        base.update(provided)
        change = {
            "action": "update",
            "expected_version": task["version"],
            "note": note,
            "task": base,
        }
        TaskInput.model_validate(base)
    else:
        change = {"action": "note", "expected_version": task["version"], "note": note}
    TaskAction.model_validate(change)
    return {**payload, "task_id": task["id"], "change": change}


class ShoppingService:
    def __init__(self, runtime, catalog: FixtureCatalog | None = None):
        self.runtime, self.store = runtime, runtime.store
        self.catalog = catalog or catalog_from_env()
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS shopping_connections (
                    id TEXT PRIMARY KEY,
                    fixture_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    cursor_seq INTEGER NOT NULL,
                    merchant TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    threshold_bps INTEGER NOT NULL,
                    created_session_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shopping_subjects (
                    connection_id TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    work_run_id TEXT NOT NULL,
                    draft_id TEXT,
                    last_price_cents INTEGER,
                    last_quantity INTEGER,
                    last_status TEXT NOT NULL,
                    last_eta TEXT,
                    PRIMARY KEY (connection_id, subject_key)
                );
                CREATE TABLE IF NOT EXISTS shopping_applied (
                    connection_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    PRIMARY KEY (connection_id, event_id)
                );
                CREATE TABLE IF NOT EXISTS shopping_buffer (
                    connection_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    body TEXT NOT NULL,
                    PRIMARY KEY (connection_id, event_id)
                );
                """
            )

    def _owner(self, principal) -> str:
        if (
            not isinstance(principal, dict)
            or principal.get("kind") != "owner"
            or not isinstance(principal.get("session"), str)
            or not principal["session"]
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not self.store.session_valid(principal["session"]):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return hashlib.sha256(principal["session"].encode()).hexdigest()

    def _connection(self, connection_id: str) -> dict:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM shopping_connections WHERE id=?", (connection_id,)
            ).fetchone()
        if row is None:
            raise DomainError("SHOPPING_CONNECTION_NOT_FOUND", 404)
        return dict(row)

    def _subjects(self, connection_id: str) -> list[dict]:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM shopping_subjects WHERE connection_id=? ORDER BY subject_key",
                (connection_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _buffered(self, connection_id: str) -> list[dict]:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT event_id, seq FROM shopping_buffer WHERE connection_id=? ORDER BY seq",
                (connection_id,),
            ).fetchall()
        return [{"event_id": row["event_id"], "seq": row["seq"]} for row in rows]

    def snapshot(self, connection_id: str, principal) -> dict:
        self._owner(principal)
        connection = self._connection(connection_id)
        return {
            "connection": connection,
            "subjects": self._subjects(connection_id),
            "buffered": self._buffered(connection_id),
            "checkout": "not_performed",
        }

    def listing(self, principal) -> dict:
        self._owner(principal)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM shopping_connections ORDER BY created_at, id"
            ).fetchall()
        return {"connections": [dict(row) for row in rows], "checkout": "not_performed"}

    def connect(self, fixture_id: str, key: str, principal) -> dict:
        session_hash = self._owner(principal)

        def apply(conn):
            fixture = self.catalog.load(fixture_id)
            count = conn.execute("SELECT COUNT(*) FROM shopping_connections").fetchone()[0]
            if count >= CONNECTION_LIMIT:
                raise DomainError("SHOPPING_CONNECTION_LIMIT", 422)
            now = iso(self.store.clock())
            connection_id = uuid4().hex
            conn.execute(
                "INSERT INTO shopping_connections VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    connection_id,
                    fixture.fixture_id,
                    "connected",
                    0,
                    fixture.merchant,
                    fixture.currency,
                    fixture.price_drop_threshold_bps,
                    session_hash,
                    now,
                    now,
                ),
            )
            self.store.record(
                conn, "shopping_connected", details={"connection_id": connection_id}
            )
            return {
                "connection": dict(
                    conn.execute(
                        "SELECT * FROM shopping_connections WHERE id=?", (connection_id,)
                    ).fetchone()
                ),
                "checkout": "not_performed",
            }

        return self.store.operation(
            key, {"type": "shopping_connect", "fixture_id": fixture_id}, apply
        )

    def revoke(self, connection_id: str, key: str, principal) -> dict:
        self._owner(principal)
        self._connection(connection_id)

        def apply(conn):
            row = conn.execute(
                "SELECT state FROM shopping_connections WHERE id=?", (connection_id,)
            ).fetchone()
            if row is None:
                raise DomainError("SHOPPING_CONNECTION_NOT_FOUND", 404)
            if row["state"] != "revoked":
                conn.execute(
                    "UPDATE shopping_connections SET state='revoked', updated_at=? WHERE id=?",
                    (iso(self.store.clock()), connection_id),
                )
            self.store.record(
                conn, "shopping_revoked", details={"connection_id": connection_id}
            )
            return {"connection_id": connection_id, "state": "revoked", "checkout": "not_performed"}

        return self.store.operation(
            key, {"type": "shopping_revoke", "connection_id": connection_id}, apply
        )

    def sync(self, connection_id: str, principal, disconnect_after: int | None = None) -> dict:
        """Commit one contiguous fixture event at a time.

        The cursor moves only after that event's task, draft and receipt are
        stored. A disconnect stops the loop and leaves later events unread.
        Already stored operation receipts are not deleted.
        """
        self._owner(principal)
        connection = self._connection(connection_id)
        if connection["state"] != "connected":
            raise DomainError("SHOPPING_REVOKED", 409)
        if disconnect_after == 0:
            return self._report(
                connection_id, completed=False, stopped="disconnected", applied=[]
            )
        fixture = self.catalog.load(connection["fixture_id"])
        pending = self._pending(connection_id, fixture)
        cursor = connection["cursor_seq"]
        applied = []
        while True:
            if disconnect_after is not None and len(applied) >= disconnect_after:
                self._flush_buffer(connection_id, pending, cursor)
                return self._report(
                    connection_id, completed=False, stopped="disconnected", applied=applied
                )
            if self._connection(connection_id)["state"] != "connected":
                self._flush_buffer(connection_id, pending, cursor)
                return self._report(
                    connection_id, completed=False, stopped="revoked", applied=applied
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
            applied.append(self._apply_event(connection, fixture, event, principal))
            pending.pop(cursor + 1, None)
            cursor += 1

    def _report(self, connection_id, *, completed, stopped, applied) -> dict:
        connection = self._connection(connection_id)
        return {
            "connection_id": connection_id,
            "cursor": connection["cursor_seq"],
            "completed": completed,
            "stopped": stopped,
            "applied": applied,
            "checkout": "not_performed",
        }

    def _pending(self, connection_id: str, fixture) -> dict:
        applied = self._applied_fingerprints(connection_id)
        pending = {}
        seen = {}
        for event in self._buffered_events(connection_id) + list(fixture.events):
            digest = fingerprint(event)
            previous = seen.get(event.event_id)
            if previous is not None and previous != digest:
                raise DomainError("SHOPPING_EVENT_CONFLICT", 409)
            stored = applied.get(event.event_id)
            if stored is not None:
                if stored != digest:
                    raise DomainError("SHOPPING_EVENT_CONFLICT", 409)
                continue
            if event.event_id in seen:
                continue
            if event.seq in pending and pending[event.seq].event_id != event.event_id:
                raise DomainError("SHOPPING_FIXTURE_INVALID", 422)
            seen[event.event_id] = digest
            pending[event.seq] = event
        return pending

    def _applied_fingerprints(self, connection_id: str) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT event_id, fingerprint FROM shopping_applied WHERE connection_id=?",
                (connection_id,),
            ).fetchall()
        return {row["event_id"]: row["fingerprint"] for row in rows}

    def _buffered_events(self, connection_id: str):
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT body FROM shopping_buffer WHERE connection_id=? ORDER BY seq",
                (connection_id,),
            ).fetchall()
        return [ShoppingEvent.model_validate(json.loads(row["body"])) for row in rows]

    def is_proposal(self, proposal_id: str) -> bool:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT kind, data FROM assistant_proposals WHERE id=?", (proposal_id,)
            ).fetchone()
        if row is None:
            return False
        if row["kind"] == "shopping_advice":
            return True
        try:
            return is_shopping_proposal(json.loads(row["data"]))
        except ValueError:
            return False

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
            conn.execute("DELETE FROM shopping_buffer WHERE connection_id=?", (connection_id,))
            for event in held:
                conn.execute(
                    "INSERT INTO shopping_buffer VALUES(?,?,?,?,?)",
                    (
                        connection_id,
                        event.seq,
                        event.event_id,
                        fingerprint(event),
                        encode(event.model_dump(mode="json")),
                    ),
                )
            return {"buffered": len(held)}

        self.store.operation(
            _op("sb", connection_id, str(cursor), digest),
            {"type": "shopping_buffer", "connection_id": connection_id, "cursor": cursor},
            apply,
        )

    def _apply_event(self, connection, fixture, event, principal) -> dict:
        connection_id = connection["id"]
        key_name = subject_key(event)
        subject = self._subject(connection_id, key_name)
        if subject is None:
            task, run = self._open_work(connection, fixture, event, key_name, principal)
            subject = {
                "connection_id": connection_id,
                "subject_key": key_name,
                "task_id": task["id"],
                "work_run_id": run["id"],
                "draft_id": None,
                "last_price_cents": None,
                "last_quantity": None,
                "last_status": "",
                "last_eta": None,
            }
        reason = self._reason(event, subject, fixture.price_drop_threshold_bps)
        draft_id = subject.get("draft_id")
        if reason:
            draft_id = self._replace_draft(connection, fixture, event, subject, reason)
            self._notify(connection, fixture, event, reason)
        price, quantity, eta, status = self._next_observation(event, subject)
        self._commit(
            connection_id,
            event,
            subject,
            draft_id,
            price,
            quantity,
            eta,
            status,
        )
        return {
            "event_id": event.event_id,
            "seq": event.seq,
            "subject_key": key_name,
            "task_id": subject["task_id"],
            "work_run_id": subject["work_run_id"],
            "notified": bool(reason),
            "reason": reason,
            "draft_id": draft_id if reason else None,
        }

    def _subject(self, connection_id: str, key_name: str):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM shopping_subjects WHERE connection_id=? AND subject_key=?",
                (connection_id, key_name),
            ).fetchone()
        return dict(row) if row else None

    def _open_work(self, connection, fixture, event, key_name, principal):
        task = self.runtime.tasks.create(
            TaskInput(
                title=display_title(event),
                follow_up_enabled=False,
                visibility="private",
            ),
            _op("st", connection["id"], key_name),
            origin="shopping_fixture",
        )["task"]
        scope = self.runtime.agent_runs.scope(principal)
        run = self.runtime.agent_runs.create(
            RunCreate(
                goal=(
                    f"Track {key_name} from fixture {fixture.fixture_id}. "
                    "Do not buy or check out."
                ),
                mode="deterministic",
                task_ids=[task["id"]],
                retain=True,
                scope_revision=scope["scope_revision"],
                allow_mutation_proposals=False,
            ),
            _op("sw", connection["id"], key_name),
            principal,
        )["run"]
        if run["state"] not in {"paused", "cancelled", "succeeded", "failed"}:
            run = self.runtime.agent_runs.action(
                run["id"],
                RunAction(action="pause", expected_version=run["version"]),
                _op("sp", connection["id"], key_name),
                principal,
            )["run"]
        return task, run

    def _reason(self, event, subject, threshold: int):
        previous_price = subject.get("last_price_cents")
        if event.kind == "price_drop":
            if previous_price is None:
                return None
            if event.unit_price_cents >= previous_price or previous_price == 0:
                return None
            drop = (previous_price - event.unit_price_cents) * 10000 // previous_price
            return "price_drop" if drop >= threshold else None
        if event.kind == "cart_change":
            if not subject.get("last_status"):
                return "needs_decision"
            changed = False
            if event.quantity is not None and event.quantity != subject.get("last_quantity"):
                changed = True
            if (
                event.unit_price_cents is not None
                and event.unit_price_cents != previous_price
            ):
                changed = True
            return "needs_decision" if changed else None
        if event.kind == "out_of_stock":
            return None if subject.get("last_status") == "out_of_stock" else "needs_decision"
        if event.kind == "order_shipped":
            return None if subject.get("last_status") == "order_shipped" else "shipped"
        if subject.get("last_status") == "order_delayed" and subject.get("last_eta") == event.eta:
            return None
        return "ship_delay"

    def _next_observation(self, event, subject):
        price = subject.get("last_price_cents")
        quantity = subject.get("last_quantity")
        eta = subject.get("last_eta")
        if event.unit_price_cents is not None:
            price = event.unit_price_cents
        if event.quantity is not None:
            quantity = event.quantity
        if event.eta is not None:
            eta = event.eta
        if event.kind == "price_drop":
            status = subject.get("last_status") or "priced"
        else:
            status = event.kind
        return price, quantity, eta, status

    def _replace_draft(self, connection, fixture, event, subject, reason: str) -> str:
        previous = subject.get("draft_id")
        if previous:
            self._cancel_pending(connection["id"], previous)
        note = advice_note(fixture.fixture_id, event, reason)
        provided = self._provided_fields(event)
        with self.store.connection() as conn:
            task_version = self.runtime.tasks.get(conn, subject["task_id"])["version"]
        payload = {
            "task_id": subject["task_id"],
            "change": {
                "action": "note",
                "expected_version": task_version,
                "note": note,
            },
            "shopping": {
                "fixture_id": fixture.fixture_id,
                "event_id": event.event_id,
                "observed_at": observed_stamp(event),
                "connection_id": connection["id"],
                "subject_key": subject["subject_key"],
                "provided_fields": provided,
                "note": note,
                "reason": reason,
            },
        }
        proposal = self.runtime.assistant.propose(
            "shopping_advice",
            payload,
            _op("sd", connection["id"], event.event_id),
        )
        return proposal["proposal"]["id"]

    @staticmethod
    def _provided_fields(event) -> dict:
        if event.kind == "order_shipped":
            return {
                "status": "waiting",
                "waiting_for": f"Shipment {event.order_id}",
            }
        if event.kind == "order_delayed":
            return {
                "status": "waiting",
                "waiting_for": (event.delay_reason or "Shipment delayed")[:500],
            }
        if event.kind == "out_of_stock":
            return {
                "status": "waiting",
                "waiting_for": "Out of stock; choose a substitute or wait",
            }
        return {}

    def _cancel_pending(self, connection_id: str, draft_id: str) -> None:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT state FROM assistant_proposals WHERE id=?", (draft_id,)
            ).fetchone()
        if row and row["state"] == "pending":
            self.runtime.assistant.decide(
                draft_id, "cancel", _op("sx", connection_id, draft_id)
            )

    def _notify(self, connection, fixture, event, reason: str) -> None:
        title = {
            "price_drop": ("Price drop", "价格下降"),
            "ship_delay": ("Shipment delayed", "发货延迟"),
            "shipped": ("Shipment update", "发货更新"),
            "needs_decision": ("Purchase decision", "购买待决定"),
        }[reason]
        stamp = observed_stamp(event)
        notice = Notice(
            id="shop-" + event.event_id,
            kind="shopping",
            title_en=title[0],
            title_zh=title[1],
            body_en=(
                f"Fixture {fixture.fixture_id} at {stamp}. "
                "No purchase or checkout was performed."
            ),
            body_zh=f"夹具 {fixture.fixture_id}，观察时间 {stamp}。没有下单或结账。",
            reason_en=f"Shopping {reason} from fixture {fixture.fixture_id}.",
            reason_zh=f"购物{reason}，来源夹具 {fixture.fixture_id}。",
        )
        self.runtime.notify.publish(notice, quiet=self._quiet())

    def _quiet(self) -> bool:
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(self.runtime.data.preferences(), self.store.clock().astimezone(zone))

    def _commit(
        self, connection_id, event, subject, draft_id, price, quantity, eta, status
    ) -> None:
        digest = fingerprint(event)

        def apply(conn):
            existing = conn.execute(
                "SELECT fingerprint FROM shopping_applied WHERE connection_id=? AND event_id=?",
                (connection_id, event.event_id),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != digest:
                    raise DomainError("SHOPPING_EVENT_CONFLICT", 409)
                return {"event_id": event.event_id, "duplicate": True}
            current = conn.execute(
                "SELECT cursor_seq FROM shopping_connections WHERE id=?", (connection_id,)
            ).fetchone()
            if current is None or current["cursor_seq"] + 1 != event.seq:
                raise DomainError("SHOPPING_CURSOR_CONFLICT", 409)
            now = iso(self.store.clock())
            conn.execute(
                "INSERT INTO shopping_applied VALUES(?,?,?,?,?)",
                (connection_id, event.event_id, event.seq, digest, now),
            )
            conn.execute(
                "UPDATE shopping_connections SET cursor_seq=?, updated_at=? WHERE id=?",
                (event.seq, now, connection_id),
            )
            conn.execute(
                """
                INSERT INTO shopping_subjects VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(connection_id, subject_key) DO UPDATE SET
                    task_id=excluded.task_id,
                    work_run_id=excluded.work_run_id,
                    draft_id=excluded.draft_id,
                    last_price_cents=excluded.last_price_cents,
                    last_quantity=excluded.last_quantity,
                    last_status=excluded.last_status,
                    last_eta=excluded.last_eta
                """,
                (
                    connection_id,
                    subject["subject_key"],
                    subject["task_id"],
                    subject["work_run_id"],
                    draft_id,
                    price,
                    quantity,
                    status,
                    eta,
                ),
            )
            conn.execute(
                "DELETE FROM shopping_buffer WHERE connection_id=? AND event_id=?",
                (connection_id, event.event_id),
            )
            self.store.record(
                conn,
                "shopping_event_applied",
                details={"connection_id": connection_id, "event_id": event.event_id},
            )
            return {"event_id": event.event_id, "duplicate": False}

        self.store.operation(
            _op("sc", connection_id, event.event_id),
            {
                "type": "shopping_event",
                "connection_id": connection_id,
                "event_id": event.event_id,
                "fingerprint": digest,
            },
            apply,
        )
