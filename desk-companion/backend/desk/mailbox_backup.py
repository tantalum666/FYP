"""Portable mailbox data validation and restore; no session or model authority."""

import json
import re
from datetime import datetime

from .mailbox_fixture import NAME, TOKEN
from .notify import Notice
from .store import DomainError, encode


class MailboxBackup:
    def __init__(self, store):
        self.store = store

    def export(self) -> dict:
        """Durable offline ingest state. No message body, snippet, or credential."""
        with self.store.connection() as conn:
            connections = [
                {
                    "id": row["id"],
                    "provider": row["provider"],
                    "account_id": row["account_id"],
                    "address": row["address"],
                    "fixture_name": row["fixture_name"],
                    "state": row["state"],
                    "history_cursor": row["history_cursor"],
                    "next_event": row["next_event"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in conn.execute("SELECT * FROM mailbox_connections ORDER BY id")
            ]
            threads = [
                {
                    "connection_id": row["connection_id"],
                    "thread_id": row["thread_id"],
                    "task_id": row["task_id"],
                    "created_message_id": row["created_message_id"],
                    "deadline_notified_due": row["deadline_notified_due"],
                }
                for row in conn.execute(
                    "SELECT * FROM mailbox_threads ORDER BY connection_id, thread_id"
                )
            ]
            messages = [
                {
                    "connection_id": row["connection_id"],
                    "message_id": row["message_id"],
                    "thread_id": row["thread_id"],
                    "history_id": row["history_id"],
                    "observed_at": row["observed_at"],
                    "fingerprint": row["fingerprint"],
                    "task_id": row["task_id"],
                    "proposal_id": row["proposal_id"],
                    "state": row["state"],
                    "created": row["created"],
                    "effect_version": row["effect_version"],
                }
                for row in conn.execute(
                    "SELECT * FROM mailbox_messages ORDER BY connection_id, message_id"
                )
            ]
            attempts = [
                {
                    "id": row["id"],
                    "connection_id": row["connection_id"],
                    "state": row["state"],
                    "cursor_before": row["cursor_before"],
                    "cursor_after": row["cursor_after"],
                    "response": None if row["response"] is None else json.loads(row["response"]),
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                }
                for row in conn.execute("SELECT * FROM mailbox_attempts ORDER BY id")
            ]
            holds = [
                {
                    "notice_id": row["notice_id"],
                    "connection_id": row["connection_id"],
                    "thread_id": row["thread_id"],
                    "deadline_due": row["deadline_due"],
                    "held_until": row["held_until"],
                    "notice": json.loads(row["payload"]),
                }
                for row in conn.execute("SELECT * FROM mailbox_notice_holds ORDER BY notice_id")
            ]
        return {
            "connections": connections,
            "threads": threads,
            "messages": messages,
            "attempts": attempts,
            "notice_holds": holds,
        }

    def validate_backup(self, bundle, *, task_ids: set[str]) -> dict:
        if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_FIELDS:
            raise ValueError("Invalid mailbox backup")
        if (
            len(bundle["connections"]) > 20
            or len(bundle["threads"]) > 500
            or len(bundle["messages"]) > 2000
            or len(bundle["attempts"]) > 2000
            or len(bundle["notice_holds"]) > 500
        ):
            raise ValueError("Invalid mailbox backup")
        connections = [_connection_record(row) for row in bundle["connections"]]
        by_id = {row["id"]: row for row in connections}
        if len(by_id) != len(connections):
            raise ValueError("Invalid mailbox connection")
        accounts = {(row["provider"], row["account_id"]) for row in connections}
        if len(accounts) != len(connections):
            raise ValueError("Invalid mailbox connection")
        threads = []
        thread_keys = set()
        for row in bundle["threads"]:
            item = _thread_record(row, by_id, task_ids)
            key = (item["connection_id"], item["thread_id"])
            if key in thread_keys:
                raise ValueError("Invalid mailbox thread")
            thread_keys.add(key)
            threads.append(item)
        thread_targets = {
            (item["connection_id"], item["thread_id"]): item["task_id"] for item in threads
        }
        messages = []
        message_keys = set()
        for row in bundle["messages"]:
            item = _message_record(row, thread_targets)
            key = (item["connection_id"], item["message_id"])
            if key in message_keys:
                raise ValueError("Invalid mailbox message")
            message_keys.add(key)
            messages.append(item)
        for connection in connections:
            cursor = connection["history_cursor"]
            applied = {
                int(item["history_id"])
                for item in messages
                if item["connection_id"] == connection["id"] and item["state"] == "applied"
            }
            # An interrupted next batch may already have newer effects while the
            # committed history cursor still denotes the previous full batch.
            if cursor is not None and int(cursor) not in applied:
                raise ValueError("Invalid mailbox cursor")
        attempts = []
        attempt_ids = set()
        for row in bundle["attempts"]:
            item = _attempt_record(row, by_id)
            if item["id"] in attempt_ids:
                raise ValueError("Invalid mailbox attempt")
            attempt_ids.add(item["id"])
            attempts.append(item)
        holds = []
        hold_ids = set()
        for row in bundle["notice_holds"]:
            item = _hold_record(row, thread_keys)
            if item["notice_id"] in hold_ids:
                raise ValueError("Invalid mailbox notice")
            hold_ids.add(item["notice_id"])
            holds.append(item)
        return {
            "connections": connections,
            "threads": threads,
            "messages": messages,
            "attempts": attempts,
            "notice_holds": holds,
        }

    def restore(self, conn, bundle) -> dict:
        """Insert connections that are not already present. Do not rewrite a live cursor."""
        created = 0
        kept = 0
        for connection in bundle["connections"]:
            if conn.execute(
                "SELECT 1 FROM mailbox_connections WHERE id=?", (connection["id"],)
            ).fetchone():
                kept += 1
                continue
            if conn.execute(
                "SELECT 1 FROM mailbox_connections WHERE provider=? AND account_id=?",
                (connection["provider"], connection["account_id"]),
            ).fetchone():
                raise DomainError("MAILBOX_ALREADY_CONNECTED", 409)
            if conn.execute("SELECT COUNT(*) FROM mailbox_connections").fetchone()[0] >= 20:
                raise DomainError("INVALID_BACKUP", 422)
            for thread in bundle["threads"]:
                if (
                    thread["connection_id"] == connection["id"]
                    and not conn.execute(
                        "SELECT 1 FROM tasks WHERE id=?", (thread["task_id"],)
                    ).fetchone()
                ):
                    raise DomainError("INVALID_BACKUP", 422)
            conn.execute(
                """
                INSERT INTO mailbox_connections(
                    id, provider, account_id, address, fixture_name, state,
                    history_cursor, next_event, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    connection["id"],
                    connection["provider"],
                    connection["account_id"],
                    connection["address"],
                    connection["fixture_name"],
                    connection["state"],
                    connection["history_cursor"],
                    connection["next_event"],
                    connection["created_at"],
                    connection["updated_at"],
                ),
            )
            for thread in bundle["threads"]:
                if thread["connection_id"] != connection["id"]:
                    continue
                conn.execute(
                    "INSERT INTO mailbox_threads VALUES(?,?,?,?,?)",
                    (
                        thread["connection_id"],
                        thread["thread_id"],
                        thread["task_id"],
                        thread["created_message_id"],
                        thread["deadline_notified_due"],
                    ),
                )
            for message in bundle["messages"]:
                if message["connection_id"] != connection["id"]:
                    continue
                conn.execute(
                    """
                    INSERT INTO mailbox_messages VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        message["connection_id"],
                        message["message_id"],
                        message["thread_id"],
                        message["history_id"],
                        message["observed_at"],
                        message["fingerprint"],
                        message["task_id"],
                        message["proposal_id"],
                        message["state"],
                        message["created"],
                        message["effect_version"],
                    ),
                )
            for attempt in bundle["attempts"]:
                if attempt["connection_id"] != connection["id"]:
                    continue
                if conn.execute(
                    "SELECT 1 FROM mailbox_attempts WHERE id=?", (attempt["id"],)
                ).fetchone():
                    raise DomainError("INVALID_BACKUP", 422)
                response = None if attempt["response"] is None else encode(attempt["response"])
                conn.execute(
                    "INSERT INTO mailbox_attempts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        attempt["id"],
                        attempt["connection_id"],
                        attempt["state"],
                        attempt["cursor_before"],
                        attempt["cursor_after"],
                        response,
                        attempt["started_at"],
                        attempt["finished_at"],
                    ),
                )
            for hold in bundle["notice_holds"]:
                if hold["connection_id"] != connection["id"]:
                    continue
                conn.execute(
                    """
                    INSERT INTO mailbox_notice_holds(
                        notice_id, connection_id, thread_id, deadline_due, payload, held_until
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        hold["notice_id"],
                        hold["connection_id"],
                        hold["thread_id"],
                        hold["deadline_due"],
                        encode(hold["notice"]),
                        hold["held_until"],
                    ),
                )
            created += 1
        return {"created": created, "kept": kept}


def empty_mailbox_bundle() -> dict:
    return {
        "connections": [],
        "threads": [],
        "messages": [],
        "attempts": [],
        "notice_holds": [],
    }


_BUNDLE_FIELDS = set(empty_mailbox_bundle())
_CONNECTION_FIELDS = {
    "id",
    "provider",
    "account_id",
    "address",
    "fixture_name",
    "state",
    "history_cursor",
    "next_event",
    "created_at",
    "updated_at",
}
_THREAD_FIELDS = {
    "connection_id",
    "thread_id",
    "task_id",
    "created_message_id",
    "deadline_notified_due",
}
_MESSAGE_FIELDS = {
    "connection_id",
    "message_id",
    "thread_id",
    "history_id",
    "observed_at",
    "fingerprint",
    "task_id",
    "proposal_id",
    "state",
    "created",
    "effect_version",
}
_ATTEMPT_FIELDS = {
    "id",
    "connection_id",
    "state",
    "cursor_before",
    "cursor_after",
    "response",
    "started_at",
    "finished_at",
}
_HOLD_FIELDS = {
    "notice_id",
    "connection_id",
    "thread_id",
    "deadline_due",
    "held_until",
    "notice",
}
_NOTICE_FIELDS = {
    "id",
    "kind",
    "title_en",
    "title_zh",
    "body_en",
    "body_zh",
    "reason_en",
    "reason_zh",
}
_RESULT_FIELDS = {
    "success",
    "status",
    "events_read",
    "applied_message_ids",
    "duplicate_message_ids",
    "skipped_message_ids",
    "connection",
    "sent",
}
_VIEW_FIELDS = {
    "id",
    "provider",
    "account_id",
    "address",
    "fixture",
    "state",
    "history_cursor",
    "next_event",
    "threads",
}
_HEX_ID = re.compile(r"^[0-9a-f]{32}$")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_NOTICE_ID = re.compile(r"^mail-[0-9a-f]{32}$")


def notice_document(notice: Notice) -> dict:
    return {
        "id": notice.id,
        "kind": notice.kind,
        "title_en": notice.title_en,
        "title_zh": notice.title_zh,
        "body_en": notice.body_en,
        "body_zh": notice.body_zh,
        "reason_en": notice.reason_en,
        "reason_zh": notice.reason_zh,
    }


def _only(row, allowed: set[str]) -> dict:
    if not isinstance(row, dict) or set(row) != allowed:
        raise ValueError("Invalid mailbox record")
    return row


def _plain(value, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError("Invalid mailbox text")
    if any(char in value for char in "\r\n\x00"):
        raise ValueError("Invalid mailbox text")
    return value


def _optional_plain(value, limit: int) -> str | None:
    if value is None:
        return None
    return _plain(value, limit)


def _timestamp(value, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    text = _plain(value, 40)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or not 2000 <= parsed.year <= 2100:
        raise ValueError("Invalid mailbox time")
    return text


def _cursor(value) -> str | None:
    if value is None:
        return None
    text = _plain(value, 20)
    if not text.isdigit() or not 1 <= int(text) <= 1_000_000_000:
        raise ValueError("Invalid mailbox cursor")
    return text


def _number(value, upper: int) -> int:
    if type(value) is not int or not 0 <= value <= upper:
        raise ValueError("Invalid mailbox number")
    return value


def _token(value) -> str:
    text = _plain(value, 64)
    if not re.fullmatch(TOKEN, text):
        raise ValueError("Invalid mailbox token")
    return text


def _connection_record(row) -> dict:
    item = _only(row, _CONNECTION_FIELDS)
    if not _HEX_ID.fullmatch(item["id"]) or item["provider"] != "offline":
        raise ValueError("Invalid mailbox connection")
    if item["state"] not in {"connected", "revoked", "disconnected"}:
        raise ValueError("Invalid mailbox connection")
    if not re.fullmatch(NAME, item["fixture_name"]):
        raise ValueError("Invalid mailbox connection")
    return {
        "id": item["id"],
        "provider": "offline",
        "account_id": _plain(item["account_id"], 80),
        "address": _plain(item["address"], 200),
        "fixture_name": item["fixture_name"],
        "state": item["state"],
        "history_cursor": _cursor(item["history_cursor"]),
        "next_event": _number(item["next_event"], 100_000),
        "created_at": _timestamp(item["created_at"]),
        "updated_at": _timestamp(item["updated_at"]),
    }


def _thread_record(row, connections: dict, task_ids: set[str]) -> dict:
    item = _only(row, _THREAD_FIELDS)
    if item["connection_id"] not in connections or item["task_id"] not in task_ids:
        raise ValueError("Invalid mailbox thread")
    if not _HEX_ID.fullmatch(item["task_id"]):
        raise ValueError("Invalid mailbox thread")
    return {
        "connection_id": item["connection_id"],
        "thread_id": _token(item["thread_id"]),
        "task_id": item["task_id"],
        "created_message_id": _token(item["created_message_id"]),
        "deadline_notified_due": _optional_plain(item["deadline_notified_due"], 40),
    }


def _message_record(row, threads: dict[tuple[str, str], str]) -> dict:
    item = _only(row, _MESSAGE_FIELDS)
    thread = (item["connection_id"], _token(item["thread_id"]))
    if thread not in threads or item["state"] not in {"pending", "applied"}:
        raise ValueError("Invalid mailbox message")
    if not _FINGERPRINT.fullmatch(item["fingerprint"]):
        raise ValueError("Invalid mailbox message")
    task_id = item["task_id"]
    proposal_id = item["proposal_id"]
    if task_id != threads[thread]:
        raise ValueError("Invalid mailbox message target")
    if task_id is not None and not _HEX_ID.fullmatch(task_id):
        raise ValueError("Invalid mailbox message")
    if proposal_id is not None and not _HEX_ID.fullmatch(proposal_id):
        raise ValueError("Invalid mailbox message")
    effect_version = item["effect_version"]
    if effect_version is not None and (
        type(effect_version) is not int or not 1 <= effect_version <= 1_000_000
    ):
        raise ValueError("Invalid mailbox message")
    return {
        "connection_id": item["connection_id"],
        "message_id": _token(item["message_id"]),
        "thread_id": thread[1],
        "history_id": _cursor(str(item["history_id"])),
        "observed_at": _timestamp(item["observed_at"]),
        "fingerprint": item["fingerprint"],
        "task_id": task_id,
        "proposal_id": proposal_id,
        "state": item["state"],
        "created": _number(item["created"], 1),
        "effect_version": effect_version,
    }


def _attempt_record(row, connections: dict) -> dict:
    item = _only(row, _ATTEMPT_FIELDS)
    if item["connection_id"] not in connections or item["state"] not in {
        "open",
        "applied",
        "interrupted",
    }:
        raise ValueError("Invalid mailbox attempt")
    attempt_id = _plain(item["id"], 100)
    if attempt_id.startswith("assistant-confirm/"):
        raise ValueError("Invalid mailbox attempt")
    response = item["response"]
    if item["state"] == "open":
        if response is not None:
            raise ValueError("Invalid mailbox attempt")
    else:
        response = _attempt_response(response, item["connection_id"])
    finished = _timestamp(item["finished_at"], required=item["state"] != "open")
    if item["state"] == "open" and finished is not None:
        raise ValueError("Invalid mailbox attempt")
    return {
        "id": attempt_id,
        "connection_id": item["connection_id"],
        "state": item["state"],
        "cursor_before": _cursor(item["cursor_before"]),
        "cursor_after": _cursor(item["cursor_after"]),
        "response": response,
        "started_at": _timestamp(item["started_at"]),
        "finished_at": finished,
    }


def _attempt_response(response, connection_id: str) -> dict:
    if not isinstance(response, dict) or set(response) not in (
        _RESULT_FIELDS,
        _RESULT_FIELDS - {"skipped_message_ids"},
    ):
        raise ValueError("Invalid mailbox attempt")
    if response["sent"] is not False or type(response["success"]) is not bool:
        raise ValueError("Invalid mailbox attempt")
    if not re.fullmatch(r"[a-z_]{1,40}", response["status"]):
        raise ValueError("Invalid mailbox attempt")
    _number(response["events_read"], 10_000)
    for key in ("applied_message_ids", "duplicate_message_ids", "skipped_message_ids"):
        values = response.get(key, [])
        if not isinstance(values, list) or len(values) > 1000:
            raise ValueError("Invalid mailbox attempt")
        for message_id in values:
            _token(message_id)
    connection = response["connection"]
    if not isinstance(connection, dict) or set(connection) != _VIEW_FIELDS:
        raise ValueError("Invalid mailbox attempt")
    if connection["id"] != connection_id or connection["provider"] != "offline":
        raise ValueError("Invalid mailbox attempt")
    if connection["state"] not in {"connected", "revoked", "disconnected"}:
        raise ValueError("Invalid mailbox attempt")
    _plain(connection["account_id"], 80)
    _plain(connection["address"], 200)
    if not re.fullmatch(NAME, connection["fixture"]):
        raise ValueError("Invalid mailbox attempt")
    _cursor(connection["history_cursor"])
    _number(connection["next_event"], 100_000)
    if not isinstance(connection["threads"], list) or len(connection["threads"]) > 500:
        raise ValueError("Invalid mailbox attempt")
    for thread in connection["threads"]:
        if not isinstance(thread, dict) or set(thread) != {"thread_id", "task_id", "work_item"}:
            raise ValueError("Invalid mailbox attempt")
        _token(thread["thread_id"])
        if not _HEX_ID.fullmatch(thread["task_id"]):
            raise ValueError("Invalid mailbox attempt")
        work = thread["work_item"]
        if not isinstance(work, dict) or work != {"kind": "task", "id": thread["task_id"]}:
            raise ValueError("Invalid mailbox attempt")
    return response


def _hold_record(row, threads: set[tuple[str, str]]) -> dict:
    item = _only(row, _HOLD_FIELDS)
    notice = item["notice"]
    if not isinstance(notice, dict) or set(notice) != _NOTICE_FIELDS:
        raise ValueError("Invalid mailbox notice")
    if item["notice_id"] != notice["id"] or not _NOTICE_ID.fullmatch(item["notice_id"]):
        raise ValueError("Invalid mailbox notice")
    if notice["kind"] not in {"mailbox_change", "mailbox_deadline"}:
        raise ValueError("Invalid mailbox notice")
    thread = (item["connection_id"], _token(item["thread_id"]))
    if thread not in threads:
        raise ValueError("Invalid mailbox notice")
    for key, limit in (
        ("title_en", 80),
        ("title_zh", 80),
        ("body_en", 500),
        ("body_zh", 500),
        ("reason_en", 500),
        ("reason_zh", 500),
    ):
        _plain(notice[key], limit)
    return {
        "notice_id": item["notice_id"],
        "connection_id": item["connection_id"],
        "thread_id": thread[1],
        "deadline_due": _optional_plain(item["deadline_due"], 40),
        "held_until": _timestamp(item["held_until"]),
        "notice": {key: notice[key] for key in _NOTICE_FIELDS},
    }
