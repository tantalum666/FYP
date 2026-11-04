"""Portable JSON backup for shopping cursor state.

The bundle is the connection, the subject-to-task mapping, applied event
receipts, and the out-of-order buffer. It does not include the owner session,
a session hash, a draft, a notice, or a Work run row.
"""

import hashlib
import json
import re
from datetime import datetime

from pydantic import ValidationError

from ..calendar import iso
from ..store import DomainError, encode
from .fixtures import FIXTURE_ID, SUBJECT, TOKEN, ShoppingEvent, fingerprint
from .notices import validate_holds

CONNECTION_LIMIT = 20
SUBJECT_LIMIT = 500
APPLIED_LIMIT = 2000
BUFFER_LIMIT = 2000
RESTORED_SESSION_HASH = hashlib.sha256(b"shopping-backup-restore").hexdigest()
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"", "cart_change", "priced", "out_of_stock", "order_shipped", "order_delayed"}


def empty_shopping_bundle() -> dict:
    return {"connections": [], "subjects": [], "applied": [], "buffered": [], "notice_holds": []}


_BUNDLE_FIELDS = set(empty_shopping_bundle())
_CONNECTION_FIELDS = {
    "id",
    "fixture_id",
    "state",
    "cursor_seq",
    "merchant",
    "currency",
    "threshold_bps",
    "created_at",
    "updated_at",
}
_SUBJECT_FIELDS = {
    "connection_id",
    "subject_key",
    "task_id",
    "work_run_id",
    "draft_id",
    "last_price_cents",
    "last_quantity",
    "last_status",
    "last_eta",
}
_APPLIED_FIELDS = {"connection_id", "event_id", "seq", "fingerprint", "applied_at"}
_BUFFER_FIELDS = {"connection_id", "seq", "event_id", "fingerprint", "body"}


def export_bundle(store) -> dict:
    with store.connection() as conn:
        connections = [
            {
                "id": row["id"],
                "fixture_id": row["fixture_id"],
                "state": row["state"],
                "cursor_seq": row["cursor_seq"],
                "merchant": row["merchant"],
                "currency": row["currency"],
                "threshold_bps": row["threshold_bps"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in conn.execute("SELECT * FROM shopping_connections ORDER BY id")
        ]
        subjects = [
            {
                "connection_id": row["connection_id"],
                "subject_key": row["subject_key"],
                "task_id": row["task_id"],
                "work_run_id": row["work_run_id"],
                "draft_id": row["draft_id"],
                "last_price_cents": row["last_price_cents"],
                "last_quantity": row["last_quantity"],
                "last_status": row["last_status"],
                "last_eta": row["last_eta"],
            }
            for row in conn.execute(
                "SELECT * FROM shopping_subjects ORDER BY connection_id, subject_key"
            )
        ]
        applied = [
            {
                "connection_id": row["connection_id"],
                "event_id": row["event_id"],
                "seq": row["seq"],
                "fingerprint": row["fingerprint"],
                "applied_at": row["applied_at"],
            }
            for row in conn.execute("SELECT * FROM shopping_applied ORDER BY connection_id, seq")
        ]
        buffered = []
        for row in conn.execute("SELECT * FROM shopping_buffer ORDER BY connection_id, seq"):
            buffered.append(
                {
                    "connection_id": row["connection_id"],
                    "seq": row["seq"],
                    "event_id": row["event_id"],
                    "fingerprint": row["fingerprint"],
                    "body": json.loads(row["body"]),
                }
            )
        holds = [
            {
                "connection_id": row["connection_id"],
                "event_id": row["event_id"],
                "notice": json.loads(row["payload"]),
            }
            for row in conn.execute("SELECT * FROM shopping_notice_holds ORDER BY notice_id")
        ]
    return {
        "connections": connections,
        "subjects": subjects,
        "applied": applied,
        "buffered": buffered,
        "notice_holds": holds,
    }


def validate_bundle(bundle, *, task_ids: set[str]) -> dict:
    if not isinstance(bundle, dict) or set(bundle) not in (
        _BUNDLE_FIELDS,
        _BUNDLE_FIELDS - {"notice_holds"},
    ):
        raise ValueError("Invalid shopping backup")
    if (
        len(bundle["connections"]) > CONNECTION_LIMIT
        or len(bundle["subjects"]) > SUBJECT_LIMIT
        or len(bundle["applied"]) > APPLIED_LIMIT
        or len(bundle["buffered"]) > BUFFER_LIMIT
    ):
        raise ValueError("Invalid shopping backup")
    connections = [_connection(row) for row in bundle["connections"]]
    by_id = {row["id"]: row for row in connections}
    if len(by_id) != len(connections):
        raise ValueError("Invalid shopping backup")
    holds = validate_holds(bundle.get("notice_holds", []), by_id)
    subjects = []
    subject_keys = set()
    for row in bundle["subjects"]:
        item = _subject(row, by_id, task_ids)
        key = (item["connection_id"], item["subject_key"])
        if key in subject_keys:
            raise ValueError("Invalid shopping backup")
        subject_keys.add(key)
        subjects.append(item)
    applied = []
    applied_ids = set()
    applied_seqs: dict[str, list[int]] = {row["id"]: [] for row in connections}
    for row in bundle["applied"]:
        item = _applied(row, by_id)
        key = (item["connection_id"], item["event_id"])
        if key in applied_ids or item["seq"] in applied_seqs[item["connection_id"]]:
            raise ValueError("Invalid shopping backup")
        applied_ids.add(key)
        applied_seqs[item["connection_id"]].append(item["seq"])
        applied.append(item)
    buffered = []
    buffered_ids = set()
    buffered_seqs: dict[str, set[int]] = {row["id"]: set() for row in connections}
    for row in bundle["buffered"]:
        item = _buffered(row, by_id)
        key = (item["connection_id"], item["event_id"])
        if key in buffered_ids or key in applied_ids:
            raise ValueError("Invalid shopping backup")
        if item["seq"] in buffered_seqs[item["connection_id"]]:
            raise ValueError("Invalid shopping backup")
        buffered_ids.add(key)
        buffered_seqs[item["connection_id"]].add(item["seq"])
        buffered.append(item)
    for connection in connections:
        cursor = connection["cursor_seq"]
        seqs = sorted(applied_seqs[connection["id"]])
        if seqs != list(range(1, cursor + 1)):
            raise ValueError("Invalid shopping backup")
        if cursor > 0 and not any(item["connection_id"] == connection["id"] for item in subjects):
            raise ValueError("Invalid shopping backup")
        if any(seq <= cursor for seq in buffered_seqs[connection["id"]]):
            raise ValueError("Invalid shopping backup")
    return {
        "connections": connections,
        "subjects": subjects,
        "applied": applied,
        "buffered": buffered,
        "notice_holds": holds,
    }


def restore_bundle(conn, bundle) -> dict:
    """Insert connections that are not already present. Do not rewrite a live cursor."""
    created = 0
    kept = 0
    for connection in bundle["connections"]:
        if conn.execute(
            "SELECT 1 FROM shopping_connections WHERE id=?", (connection["id"],)
        ).fetchone():
            kept += 1
            continue
        if (
            conn.execute("SELECT COUNT(*) FROM shopping_connections").fetchone()[0]
            >= CONNECTION_LIMIT
        ):
            raise DomainError("INVALID_BACKUP", 422)
        owned = [row for row in bundle["subjects"] if row["connection_id"] == connection["id"]]
        for subject in owned:
            if not conn.execute("SELECT 1 FROM tasks WHERE id=?", (subject["task_id"],)).fetchone():
                raise DomainError("INVALID_BACKUP", 422)
        conn.execute(
            "INSERT INTO shopping_connections VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                connection["id"],
                connection["fixture_id"],
                connection["state"],
                connection["cursor_seq"],
                connection["merchant"],
                connection["currency"],
                connection["threshold_bps"],
                RESTORED_SESSION_HASH,
                connection["created_at"],
                connection["updated_at"],
            ),
        )
        for subject in owned:
            conn.execute(
                "INSERT INTO shopping_subjects VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    subject["connection_id"],
                    subject["subject_key"],
                    subject["task_id"],
                    subject["work_run_id"],
                    subject["draft_id"],
                    subject["last_price_cents"],
                    subject["last_quantity"],
                    subject["last_status"],
                    subject["last_eta"],
                ),
            )
        for event in bundle["applied"]:
            if event["connection_id"] != connection["id"]:
                continue
            conn.execute(
                "INSERT INTO shopping_applied VALUES(?,?,?,?,?)",
                (
                    event["connection_id"],
                    event["event_id"],
                    event["seq"],
                    event["fingerprint"],
                    event["applied_at"],
                ),
            )
        for event in bundle["buffered"]:
            if event["connection_id"] != connection["id"]:
                continue
            conn.execute(
                "INSERT INTO shopping_buffer VALUES(?,?,?,?,?)",
                (
                    event["connection_id"],
                    event["seq"],
                    event["event_id"],
                    event["fingerprint"],
                    encode(event["body"]),
                ),
            )
        for hold in bundle.get("notice_holds", []):
            if hold["connection_id"] == connection["id"]:
                conn.execute(
                    "INSERT OR IGNORE INTO shopping_notice_holds VALUES(?,?,?,?)",
                    (
                        hold["notice"]["id"],
                        connection["id"],
                        hold["event_id"],
                        encode(hold["notice"]),
                    ),
                )
        created += 1
    return {"created": created, "kept": kept}


def _connection(row) -> dict:
    if not isinstance(row, dict) or set(row) != _CONNECTION_FIELDS:
        raise ValueError("Invalid shopping backup")
    if not _HEX32.fullmatch(_text_id(row["id"])):
        raise ValueError("Invalid shopping backup")
    if not isinstance(row["fixture_id"], str) or not FIXTURE_ID.fullmatch(row["fixture_id"]):
        raise ValueError("Invalid shopping backup")
    if row["state"] not in {"connected", "revoked"}:
        raise ValueError("Invalid shopping backup")
    merchant = row["merchant"]
    if (
        not isinstance(merchant, str)
        or not merchant.strip()
        or len(merchant.strip()) > 80
        or any(ord(char) < 32 for char in merchant)
    ):
        raise ValueError("Invalid shopping backup")
    currency = row["currency"]
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isalpha()
        or not currency.isupper()
    ):
        raise ValueError("Invalid shopping backup")
    return {
        "id": row["id"],
        "fixture_id": row["fixture_id"],
        "state": row["state"],
        "cursor_seq": _integer(row["cursor_seq"], 0, 100000),
        "merchant": merchant.strip(),
        "currency": currency,
        "threshold_bps": _integer(row["threshold_bps"], 0, 10000),
        "created_at": _stamp(row["created_at"]),
        "updated_at": _stamp(row["updated_at"]),
    }


def _subject(row, connections: dict, task_ids: set[str]) -> dict:
    if not isinstance(row, dict) or set(row) != _SUBJECT_FIELDS:
        raise ValueError("Invalid shopping backup")
    connection_id = _known_connection(row["connection_id"], connections)
    if not isinstance(row["subject_key"], str) or not SUBJECT.fullmatch(row["subject_key"]):
        raise ValueError("Invalid shopping backup")
    task_id = row["task_id"]
    if not isinstance(task_id, str) or task_id not in task_ids or not _HEX32.fullmatch(task_id):
        raise ValueError("Invalid shopping backup")
    if not isinstance(row["work_run_id"], str) or not _HEX32.fullmatch(row["work_run_id"]):
        raise ValueError("Invalid shopping backup")
    draft_id = row["draft_id"]
    if draft_id is not None and (not isinstance(draft_id, str) or not _HEX32.fullmatch(draft_id)):
        raise ValueError("Invalid shopping backup")
    status = row["last_status"]
    if not isinstance(status, str) or status not in _STATUSES:
        raise ValueError("Invalid shopping backup")
    eta = row["last_eta"]
    if eta is not None and (
        not isinstance(eta, str)
        or not eta.strip()
        or len(eta) > 80
        or any(ord(char) < 32 for char in eta)
    ):
        raise ValueError("Invalid shopping backup")
    return {
        "connection_id": connection_id,
        "subject_key": row["subject_key"],
        "task_id": task_id,
        "work_run_id": row["work_run_id"],
        "draft_id": draft_id,
        "last_price_cents": _optional_integer(row["last_price_cents"], 0, 100_000_000),
        "last_quantity": _optional_integer(row["last_quantity"], 1, 99),
        "last_status": status,
        "last_eta": None if eta is None else eta.strip(),
    }


def _applied(row, connections: dict) -> dict:
    if not isinstance(row, dict) or set(row) != _APPLIED_FIELDS:
        raise ValueError("Invalid shopping backup")
    event_id = row["event_id"]
    fingerprint_value = row["fingerprint"]
    if not isinstance(event_id, str) or not TOKEN.fullmatch(event_id):
        raise ValueError("Invalid shopping backup")
    if not isinstance(fingerprint_value, str) or not _HEX64.fullmatch(fingerprint_value):
        raise ValueError("Invalid shopping backup")
    return {
        "connection_id": _known_connection(row["connection_id"], connections),
        "event_id": event_id,
        "seq": _integer(row["seq"], 1, 100000),
        "fingerprint": fingerprint_value,
        "applied_at": _stamp(row["applied_at"]),
    }


def _buffered(row, connections: dict) -> dict:
    if not isinstance(row, dict) or set(row) != _BUFFER_FIELDS:
        raise ValueError("Invalid shopping backup")
    event_id = row["event_id"]
    claimed = row["fingerprint"]
    if not isinstance(event_id, str) or not TOKEN.fullmatch(event_id):
        raise ValueError("Invalid shopping backup")
    if not isinstance(claimed, str) or not _HEX64.fullmatch(claimed):
        raise ValueError("Invalid shopping backup")
    if not isinstance(row["body"], dict):
        raise ValueError("Invalid shopping backup")
    try:
        event = ShoppingEvent.model_validate(row["body"])
    except (ValueError, ValidationError):
        raise ValueError("Invalid shopping backup") from None
    seq = _integer(row["seq"], 1, 100000)
    if event.event_id != event_id or event.seq != seq or fingerprint(event) != claimed:
        raise ValueError("Invalid shopping backup")
    return {
        "connection_id": _known_connection(row["connection_id"], connections),
        "seq": seq,
        "event_id": event_id,
        "fingerprint": claimed,
        "body": event.model_dump(mode="json"),
    }


def _known_connection(value, connections: dict) -> str:
    if not isinstance(value, str) or value not in connections:
        raise ValueError("Invalid shopping backup")
    return value


def _text_id(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid shopping backup")
    return value


def _integer(value, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("Invalid shopping backup")
    return value


def _optional_integer(value, low: int, high: int):
    if value is None:
        return None
    return _integer(value, low, high)


def _stamp(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid shopping backup")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid shopping backup") from None
    if parsed.tzinfo is None or not 2000 <= parsed.year <= 2100:
        raise ValueError("Invalid shopping backup")
    return iso(parsed)
