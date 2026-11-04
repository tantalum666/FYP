"""Offline authorized-mailbox ingest through the existing task, draft, and notice services.

A thread maps to one TaskService task. Reply text stays an assistant draft until the
owner confirms it. Confirmation records a review note and does not send mail.
"""

import hashlib
import json
import threading
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from .calendar import iso, wall_to_utc
from .mailbox_backup import MailboxBackup, notice_document
from .mailbox_fixture import (
    NAME,
    FixtureMessage,
    flatten,
    load_fixture,
    message_fingerprint,
)
from .notify import Notice
from .schemas import StrictModel
from .store import DomainError, encode
from .tasks import OPEN, TaskAction, TaskInput
from .workspace_data import quiet_until

DRAFT_TTL = timedelta(days=7)
APPROACHING = timedelta(hours=24)


class MailboxConnect(StrictModel):
    fixture: str = Field(pattern=NAME, max_length=64)


def _operation_key(prefix: str, material: str) -> str:
    return prefix + hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]


def _notice_id(connection_id: str, message_id: str) -> str:
    digest = hashlib.sha256(f"{connection_id}/{message_id}".encode()).hexdigest()[:32]
    return "mail-" + digest


def _citation(message: FixtureMessage) -> str:
    return f"Mailbox message {message.id} observed at {iso(message.observed_at)}."


def _as_local(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _canonical(task: dict) -> dict:
    data = {key: task[key] for key in TaskInput.model_fields}
    for key in ("due_local", "check_in_local"):
        data[key] = _as_local(data[key]) if data[key] else None
    return TaskInput.model_validate(data).model_dump(mode="json")


def _initial_task(message: FixtureMessage) -> TaskInput:
    provided = message.model_fields_set
    waiting = message.waiting_for if "waiting_for" in provided and message.waiting_for else ""
    status = "todo"
    if message.await_reply is True or ("waiting_for" in provided and waiting.strip()):
        status = "waiting"
        if not waiting.strip():
            waiting = f"Reply to {message.sender}"
    return TaskInput(
        title=message.subject.strip(),
        timezone=message.timezone or "Asia/Hong_Kong",
        due_local=message.deadline_local if "deadline_local" in provided else None,
        status=status,
        next_step=message.next_step if "next_step" in provided and message.next_step else "",
        waiting_for=waiting,
    )


def merge_task(current: dict, message: FixtureMessage) -> TaskInput:
    """Copy the saved task, then apply only fields present on this message."""
    raw = {key: current[key] for key in TaskInput.model_fields}
    for key in ("due_local", "check_in_local"):
        raw[key] = _as_local(raw[key]) if raw[key] else None
    provided = message.model_fields_set
    if "deadline_local" in provided:
        raw["due_local"] = message.deadline_local
    if "timezone" in provided and message.timezone:
        raw["timezone"] = message.timezone
    if "next_step" in provided and message.next_step is not None:
        raw["next_step"] = message.next_step
    if "waiting_for" in provided and message.waiting_for is not None:
        raw["waiting_for"] = message.waiting_for
        if message.waiting_for.strip():
            raw["status"] = "waiting"
        elif raw["status"] == "waiting":
            raw["status"] = "in_progress"
    if "await_reply" in provided and message.await_reply is True:
        raw["status"] = "waiting"
        if not str(raw["waiting_for"]).strip():
            raw["waiting_for"] = f"Reply to {message.sender}"
    if "await_reply" in provided and message.await_reply is False and raw["status"] == "waiting":
        raw["status"] = "in_progress"
    return TaskInput.model_validate(raw)


def advice_payload(message: FixtureMessage, task_id: str) -> dict:
    observed = iso(message.observed_at)
    summary = (
        f"Source message {message.id} observed at {observed}. "
        "This is a review draft. Sending is not available and will not happen automatically."
    )
    if "deadline_local" in message.model_fields_set and message.deadline_local is not None:
        summary += " Deadline noted: " + message.deadline_local.strftime("%Y-%m-%d %H:%M") + "."
    reply = None
    if message.await_reply is True:
        reply = (
            f"Thanks for your message about {message.subject}. "
            "I am reviewing it and will reply only after this draft is approved. "
            f"Source {message.id} observed at {observed}."
        )
    return {
        "task_id": task_id,
        "mail_id": message.id,
        "title": message.subject,
        "thread_id": message.thread_id,
        "observed_at": observed,
        "send": False,
        "summary": summary,
        "reply_draft": reply,
    }


def wants_draft(message: FixtureMessage) -> bool:
    return bool(message.needs_decision or message.await_reply is True)


class MailboxService:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        self.backup = MailboxBackup(self.store)
        self.lock = threading.RLock()
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS mailbox_connections(
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    address TEXT NOT NULL,
                    fixture_name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    history_cursor TEXT,
                    next_event INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, account_id)
                );
                CREATE TABLE IF NOT EXISTS mailbox_threads(
                    connection_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    created_message_id TEXT NOT NULL,
                    deadline_notified_due TEXT,
                    PRIMARY KEY(connection_id, thread_id)
                );
                CREATE TABLE IF NOT EXISTS mailbox_messages(
                    connection_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    history_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    task_id TEXT,
                    proposal_id TEXT,
                    state TEXT NOT NULL,
                    created INTEGER NOT NULL,
                    effect_version INTEGER,
                    PRIMARY KEY(connection_id, message_id)
                );
                CREATE TABLE IF NOT EXISTS mailbox_attempts(
                    id TEXT PRIMARY KEY,
                    connection_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    cursor_before TEXT,
                    cursor_after TEXT,
                    response TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS mailbox_notice_holds(
                    notice_id TEXT PRIMARY KEY,
                    connection_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    deadline_due TEXT,
                    payload TEXT NOT NULL,
                    held_until TEXT NOT NULL
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
                "SELECT 1 FROM mailbox_connections WHERE provider='offline' AND account_id=?",
                (fixture.account_id,),
            ).fetchone():
                raise DomainError("MAILBOX_ALREADY_CONNECTED", 409)
            now = iso(self.store.clock())
            connection_id = uuid4().hex
            conn.execute(
                "INSERT INTO mailbox_connections VALUES(?,?,?,?,?,'connected',NULL,0,?,?)",
                (
                    connection_id,
                    "offline",
                    fixture.account_id,
                    fixture.address,
                    fixture_name,
                    now,
                    now,
                ),
            )
            self.store.record(
                conn,
                "mailbox_connected",
                details={"connection_id": connection_id, "fixture": fixture_name},
            )
            return {"connection": self._view(conn, connection_id), "saved": True}

        return self.store.operation(
            key, {"type": "mailbox_connect", "fixture": fixture_name}, apply
        )

    def revoke(self, connection_id: str, key: str, session: str | None) -> dict:
        return self._stop(connection_id, key, session, "revoked", "mailbox_revoked")

    def disconnect(self, connection_id: str, key: str, session: str | None) -> dict:
        return self._stop(connection_id, key, session, "disconnected", "mailbox_disconnected")

    def _stop(self, connection_id: str, key: str, session: str | None, state: str, action: str):
        self._owner(session)
        key = self._require_key(key)
        # Revocation must not wait behind a complete multi-message sync.
        return self._stop_locked(connection_id, key, state, action)

    def _stop_locked(self, connection_id: str, key: str, state: str, action: str):
        def apply(conn):
            self._row(conn, connection_id)
            conn.execute(
                "UPDATE mailbox_connections SET state=?, updated_at=? WHERE id=?",
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
            key, {"type": "mailbox_" + state, "connection_id": connection_id}, apply
        )

    def listing(self, session: str | None) -> dict:
        self._owner(session)
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT id FROM mailbox_connections ORDER BY created_at, id"
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
                return json_response(prior["response"])
            self._open_attempt(key, connection)
            if connection["state"] != "connected":
                response = self._result(
                    connection_id,
                    status=connection["state"],
                    success=False,
                    applied=[],
                    duplicates=[],
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
                    events_read=0,
                )
                self._finish_attempt(key, "applied", connection["history_cursor"], response)
                return response
            batch_id = events[offset].batch_id
            staged: list[FixtureMessage] = []
            duplicates: list[str] = []
            events_read = 0
            index = offset
            stop: str | None = None
            pending_state: str | None = None
            resume_at = offset
            while index < len(events) and events[index].batch_id == batch_id:
                if self._connection(connection_id)["state"] != "connected":
                    stop = self._connection(connection_id)["state"]
                    resume_at = index
                    break
                events_read += 1
                event = events[index]
                if event.op == "message" and event.message is not None:
                    staged.append(event.message)
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
            seen: set[str] = set()
            ordered: list[FixtureMessage] = []
            for message in sorted(staged, key=lambda item: (item.history_id, item.id)):
                if message.id in seen:
                    duplicates.append(message.id)
                    continue
                seen.add(message.id)
                ordered.append(message)
            applied: list[str] = []
            skipped: list[str] = []
            for message in ordered:
                self._owner(session)
                state = self._connection(connection_id)["state"]
                if state != "connected":
                    stop, resume_at = state, offset
                    break
                outcome = self._apply_message(connection_id, message)
                if outcome == "duplicate":
                    duplicates.append(message.id)
                elif outcome == "skipped":
                    skipped.append(message.id)
                else:
                    applied.append(message.id)
            if pending_state:
                self._set_state(connection_id, pending_state)
            if stop:
                self._set_offset(connection_id, resume_at)
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
            self._set_offset(connection_id, resume_at)
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

    def _apply_message(self, connection_id: str, message: FixtureMessage) -> str:
        fingerprint = message_fingerprint(message)
        with self.store.connection() as conn:
            existing = conn.execute(
                "SELECT * FROM mailbox_messages WHERE connection_id=? AND message_id=?",
                (connection_id, message.id),
            ).fetchone()
        if existing and existing["state"] == "applied":
            if existing["fingerprint"] != fingerprint:
                raise DomainError("MAILBOX_MESSAGE_CONFLICT", 409)
            return "duplicate"
        # A delayed batch may contain an earlier message from this same thread.
        # Its presence must not rewind a newer accepted deadline/status.
        with self.store.connection() as conn:
            newest = conn.execute(
                "SELECT MAX(CAST(history_id AS INTEGER)) FROM mailbox_messages "
                "WHERE connection_id=? AND thread_id=? AND state='applied'",
                (connection_id, message.thread_id),
            ).fetchone()[0]
        if newest is not None and message.history_id < newest:
            return "skipped"
        if existing:
            task_id = existing["task_id"]
            created = bool(existing["created"])
            effect_version = existing["effect_version"]
            if existing["fingerprint"] != fingerprint:
                raise DomainError("MAILBOX_MESSAGE_CONFLICT", 409)
        else:
            task_id, created = self._ensure_thread(connection_id, message)
            with self.store.connection() as conn:
                effect_version = self.runtime.tasks.get(conn, task_id)["version"]
            self._insert_pending(
                connection_id, message, fingerprint, task_id, created, effect_version
            )
        changed = False
        if created:
            self._effect(connection_id, task_id, message, effect_version, update=None)
            changed = True
        else:
            with self.store.connection() as conn:
                current = self.runtime.tasks.get(conn, task_id)
            merged = merge_task(current, message)
            if _canonical(current) != merged.model_dump(mode="json"):
                self._effect(connection_id, task_id, message, effect_version, update=merged)
                changed = True
        proposal_id = None
        drafted = wants_draft(message)
        if drafted:
            proposal_id = self._draft(connection_id, task_id, message)
        with self.store.connection() as conn:
            task = self.runtime.tasks.get(conn, task_id)
        self._notify(
            connection_id,
            task,
            message,
            created=created,
            changed=changed,
            drafted=drafted,
        )
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE mailbox_messages SET state='applied', task_id=?, proposal_id=? "
                "WHERE connection_id=? AND message_id=?",
                (task_id, proposal_id, connection_id, message.id),
            )
        return "applied"

    def _ensure_thread(self, connection_id: str, message: FixtureMessage) -> tuple[str, bool]:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT task_id, created_message_id FROM mailbox_threads "
                "WHERE connection_id=? AND thread_id=?",
                (connection_id, message.thread_id),
            ).fetchone()
        if row:
            return row["task_id"], row["created_message_id"] == message.id
        created = self.runtime.tasks.create(
            _initial_task(message),
            _operation_key("mb-new-", f"{connection_id}/{message.thread_id}"),
            origin="mailbox",
        )
        task_id = created["task"]["id"]
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT task_id, created_message_id FROM mailbox_threads "
                "WHERE connection_id=? AND thread_id=?",
                (connection_id, message.thread_id),
            ).fetchone()
            if row:
                return row["task_id"], row["created_message_id"] == message.id
            conn.execute(
                "INSERT INTO mailbox_threads VALUES(?,?,?,?,NULL)",
                (connection_id, message.thread_id, task_id, message.id),
            )
        return task_id, True

    def _insert_pending(
        self,
        connection_id: str,
        message: FixtureMessage,
        fingerprint: str,
        task_id: str,
        created: bool,
        effect_version: int,
    ) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO mailbox_messages VALUES(?,?,?,?,?,?,?,NULL,'pending',?,?)",
                (
                    connection_id,
                    message.id,
                    message.thread_id,
                    str(message.history_id),
                    iso(message.observed_at),
                    fingerprint,
                    task_id,
                    int(created),
                    effect_version,
                ),
            )

    def _effect(
        self,
        connection_id: str,
        task_id: str,
        message: FixtureMessage,
        effect_version: int,
        update: TaskInput | None,
    ) -> None:
        note = _citation(message)
        if update is None:
            action = TaskAction(action="note", expected_version=effect_version, note=note)
            key = _operation_key("mb-note-", f"{connection_id}/{message.id}")
        else:
            action = TaskAction(
                action="update", expected_version=effect_version, task=update, note=note
            )
            key = _operation_key("mb-upd-", f"{connection_id}/{message.id}")
        try:
            self.runtime.tasks.action(task_id, action, key, origin="mailbox")
        except DomainError as error:
            if error.code != "OPERATION_ID_CONFLICT":
                raise

    def _draft(self, connection_id: str, task_id: str, message: FixtureMessage) -> str:
        proposed = self.runtime.assistant.propose(
            "mailbox_reply",
            advice_payload(message, task_id),
            _operation_key("mb-draft-", f"{connection_id}/{message.id}"),
            ttl=DRAFT_TTL,
        )
        return proposed["proposal"]["id"]

    def _notify(
        self,
        connection_id: str,
        task: dict,
        message: FixtureMessage,
        *,
        created: bool,
        changed: bool,
        drafted: bool,
    ) -> None:
        due = task.get("due_local")
        approaching = self._approaching(task)
        already = self._deadline_mark(connection_id, message.thread_id)
        deadline_news = bool(approaching and already != due)
        if not created and not changed and not drafted and not deadline_news:
            return
        observed = iso(message.observed_at)
        reasons_en: list[str] = []
        reasons_zh: list[str] = []
        if created:
            reasons_en.append("A mailbox thread is now a tracked task.")
            reasons_zh.append("一条邮件线程已成为跟踪事务。")
        elif changed:
            reasons_en.append("A tracked mailbox thread changed.")
            reasons_zh.append("已跟踪的邮件线程有变化。")
        if deadline_news:
            reasons_en.append("A deadline is within 24 hours.")
            reasons_zh.append("有一个期限在24小时内。")
        if drafted:
            reasons_en.append("A reply draft needs a decision.")
            reasons_zh.append("有一份回复草稿需要决定。")
        body_en = " ".join(reasons_en) + f" Message {message.id} observed at {observed}."
        body_zh = "".join(reasons_zh) + f"邮件 {message.id}，观察时间 {observed}。"
        kind = (
            "mailbox_deadline"
            if deadline_news and not created and not changed
            else "mailbox_change"
        )
        notice = Notice(
            _notice_id(connection_id, message.id),
            kind,
            "Mailbox update",
            "邮箱更新",
            body_en,
            body_zh,
            body_en,
            body_zh,
        )
        quiet = self._quiet_end() is not None
        results = self.runtime.notify.publish(notice, quiet=quiet)
        delivered = any(item["status"] in {"delivered", "duplicate"} for item in results)
        if not delivered and any(item["status"] == "quiet" for item in results):
            self._defer_notice(
                connection_id,
                message.thread_id,
                notice,
                due if deadline_news else None,
            )
            return
        if deadline_news and delivered:
            self._mark_deadline(connection_id, message.thread_id, due)

    def _approaching(self, task: dict) -> bool:
        if task.get("status") not in OPEN or not task.get("due_local"):
            return False
        due = wall_to_utc(_as_local(task["due_local"]), task["timezone"], reject_ambiguous=True)
        return due - self.store.clock() <= APPROACHING

    def _quiet_end(self):
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return quiet_until(self.runtime.data.preferences(), self.store.clock().astimezone(zone))

    def _defer_notice(
        self,
        connection_id: str,
        thread_id: str,
        notice: Notice,
        deadline_due: str | None,
    ) -> None:
        """Keep one notice until the existing rules tick sees quiet hours end."""
        until = self._quiet_end()
        if until is None:
            return
        with self.store.connection(write=True) as conn:
            conn.execute(
                """
                INSERT INTO mailbox_notice_holds(
                    notice_id, connection_id, thread_id, deadline_due, payload, held_until
                ) VALUES(?,?,?,?,?,?)
                ON CONFLICT(notice_id) DO NOTHING
                """,
                (
                    notice.id,
                    connection_id,
                    thread_id,
                    deadline_due,
                    encode(notice_document(notice)),
                    iso(until),
                ),
            )

    def release_quiet_notices(self) -> None:
        """Deliver held mailbox notices once quiet hours have ended.

        Called from Runtime.tick, the same rules loop that releases task quiet holds.
        The hold row stays until Notifier has accepted the notice, so a crash retry
        publishes the same id and the inbox dedupes it.
        """
        until = self._quiet_end()
        if until is not None:
            self._refresh_holds(iso(until))
            return
        with self.lock:
            with self.store.connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM mailbox_notice_holds ORDER BY notice_id"
                ).fetchall()
            for row in rows:
                if self._quiet_end() is not None:
                    return
                payload = json.loads(row["payload"])
                notice = Notice(
                    payload["id"],
                    payload["kind"],
                    payload["title_en"],
                    payload["title_zh"],
                    payload["body_en"],
                    payload["body_zh"],
                    payload["reason_en"],
                    payload["reason_zh"],
                )
                results = self.runtime.notify.publish(notice, quiet=False)
                if not any(item["status"] in {"delivered", "duplicate"} for item in results):
                    continue
                with self.store.connection(write=True) as conn:
                    if row["deadline_due"]:
                        self._mark_deadline(
                            row["connection_id"], row["thread_id"], row["deadline_due"], conn
                        )
                    conn.execute(
                        "DELETE FROM mailbox_notice_holds WHERE notice_id=?",
                        (row["notice_id"],),
                    )

    def _refresh_holds(self, until: str) -> None:
        with self.store.connection() as conn:
            stale = conn.execute(
                "SELECT 1 FROM mailbox_notice_holds WHERE held_until!=? LIMIT 1", (until,)
            ).fetchone()
        if not stale:
            return
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE mailbox_notice_holds SET held_until=? WHERE held_until!=?",
                (until, until),
            )

    def _mark_deadline(self, connection_id: str, thread_id: str, due: str, conn=None) -> None:
        statement = (
            "UPDATE mailbox_threads SET deadline_notified_due=? "
            "WHERE connection_id=? AND thread_id=?"
        )
        if conn is None:
            with self.store.connection(write=True) as owned:
                owned.execute(statement, (due, connection_id, thread_id))
            return
        conn.execute(statement, (due, connection_id, thread_id))

    def _deadline_mark(self, connection_id: str, thread_id: str) -> str | None:
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT deadline_notified_due FROM mailbox_threads "
                "WHERE connection_id=? AND thread_id=?",
                (connection_id, thread_id),
            ).fetchone()
        return None if row is None else row["deadline_notified_due"]

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
            "SELECT * FROM mailbox_connections WHERE id=?", (connection_id,)
        ).fetchone()
        if row is None:
            raise DomainError("MAILBOX_NOT_FOUND", 404)
        return row

    def _view(self, conn, connection_id: str) -> dict:
        row = self._row(conn, connection_id)
        threads = []
        for item in conn.execute(
            "SELECT thread_id, task_id FROM mailbox_threads WHERE connection_id=? ORDER BY thread_id",
            (connection_id,),
        ):
            threads.append(
                {
                    "thread_id": item["thread_id"],
                    "task_id": item["task_id"],
                    "work_item": {"kind": "task", "id": item["task_id"]},
                }
            )
        return {
            "id": row["id"],
            "provider": row["provider"],
            "account_id": row["account_id"],
            "address": row["address"],
            "fixture": row["fixture_name"],
            "state": row["state"],
            "history_cursor": row["history_cursor"],
            "next_event": row["next_event"],
            "threads": threads,
        }

    def _result(
        self,
        connection_id: str,
        *,
        status: str,
        success: bool,
        applied: list[str],
        duplicates: list[str],
        events_read: int,
        skipped: list[str] | None = None,
    ) -> dict:
        with self.store.connection() as conn:
            connection = self._view(conn, connection_id)
        return {
            "success": success,
            "status": status,
            "events_read": events_read,
            "applied_message_ids": applied,
            "duplicate_message_ids": duplicates,
            "skipped_message_ids": skipped or [],
            "connection": connection,
            "sent": False,
        }

    def _attempt(self, key: str):
        with self.store.connection() as conn:
            return conn.execute("SELECT * FROM mailbox_attempts WHERE id=?", (key,)).fetchone()

    def _open_attempt(self, key: str, connection: dict) -> None:
        with self.store.connection(write=True) as conn:
            if conn.execute("SELECT 1 FROM mailbox_attempts WHERE id=?", (key,)).fetchone():
                return
            conn.execute(
                "INSERT INTO mailbox_attempts VALUES(?,?, 'open', ?, NULL, NULL, ?, NULL)",
                (key, connection["id"], connection["history_cursor"], iso(self.store.clock())),
            )

    def _finish_attempt(
        self, key: str, state: str, cursor_after: str | None, response: dict
    ) -> None:
        with self.store.connection(write=True) as conn:
            current = conn.execute(
                "SELECT state FROM mailbox_attempts WHERE id=?", (key,)
            ).fetchone()
            if current and current["state"] == "applied" and state != "applied":
                raise DomainError("OPERATION_ID_CONFLICT")
            conn.execute(
                "UPDATE mailbox_attempts SET state=?, cursor_after=?, response=?, finished_at=? "
                "WHERE id=?",
                (state, cursor_after, encode(response), iso(self.store.clock()), key),
            )

    def _set_state(self, connection_id: str, state: str) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE mailbox_connections SET state=?, updated_at=? WHERE id=?",
                (state, iso(self.store.clock()), connection_id),
            )

    def _set_offset(self, connection_id: str, offset: int) -> None:
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE mailbox_connections SET next_event=?, updated_at=? WHERE id=?",
                (offset, iso(self.store.clock()), connection_id),
            )

    def _advance_cursor(self, connection_id: str) -> str | None:
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT MAX(CAST(history_id AS INTEGER)) FROM mailbox_messages "
                "WHERE connection_id=? AND state='applied'",
                (connection_id,),
            ).fetchone()
            cursor = None if row[0] is None else str(row[0])
            conn.execute(
                "UPDATE mailbox_connections SET history_cursor=?, updated_at=? WHERE id=?",
                (cursor, iso(self.store.clock()), connection_id),
            )
            return cursor

    def export(self) -> dict:
        return self.backup.export()

    def validate_backup(self, bundle, *, task_ids: set[str]) -> dict:
        return self.backup.validate_backup(bundle, task_ids=task_ids)

    def restore(self, conn, bundle) -> dict:
        return self.backup.restore(conn, bundle)


def json_response(payload: str) -> dict:
    return json.loads(payload)


def mailbox_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/mailbox", dependencies=[Depends(owner)])
    service = runtime.mailbox

    def session_of(request: Request) -> str | None:
        return request.cookies.get("desk_companion_session")

    @router.get("/connections")
    def listing(request: Request):
        return service.listing(session_of(request))

    @router.post("/connections")
    def connect(payload: MailboxConnect, request: Request, key=Depends(operation_id)):
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
    return [item for item in proposals if item.get("kind") != "mailbox_reply"]
