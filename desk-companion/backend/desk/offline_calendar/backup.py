"""Portable JSON backup for offline calendar cursor state.

The bundle is the connection, the event-to-task mapping, applied revisions,
conflict pairs, sync attempts, and quiet-hour notice holds. It does not include
an owner session, a draft, or a delivered notice.
"""

import json
import re
from datetime import datetime

from ..calendar import iso
from ..store import DomainError, encode
from .fixture import NAME, TOKEN

CONNECTION_LIMIT = 20
ITEM_LIMIT = 500
REVISION_LIMIT = 2000
CONFLICT_LIMIT = 2000
ATTEMPT_LIMIT = 2000
HOLD_LIMIT = 500
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_NOTICE_ID = re.compile(r"^cal-[0-9a-f]{32}$")
_CURSOR = re.compile(r"^[1-9][0-9]{0,9}$")
_KINDS = {"event", "series"}
_STATES = {"connected", "revoked", "disconnected"}
_REVISION_STATES = {"applied", "skipped"}
_ATTEMPT_STATES = {"open", "applied", "interrupted"}
_NOTICE_KINDS = {
    "calendar_conflict",
    "calendar_deadline",
    "calendar_decision",
    "calendar_cancelled",
}
_NOTICE_FIELDS = (
    "id",
    "kind",
    "title_en",
    "title_zh",
    "body_en",
    "body_zh",
    "reason_en",
    "reason_zh",
)


def empty_offline_calendar_bundle() -> dict:
    return {
        "connections": [],
        "items": [],
        "revisions": [],
        "conflicts": [],
        "attempts": [],
        "notice_holds": [],
    }


_BUNDLE_FIELDS = set(empty_offline_calendar_bundle())
_CONNECTION_FIELDS = {
    "id",
    "provider",
    "account_id",
    "calendar_id",
    "fixture_name",
    "state",
    "history_cursor",
    "next_event",
    "created_at",
    "updated_at",
}
_ITEM_FIELDS = {
    "connection_id",
    "uid",
    "local_event_id",
    "task_id",
    "sequence",
    "fingerprint",
    "kind",
    "deadline_notified_due",
    "cancelled",
}
_REVISION_FIELDS = {
    "connection_id",
    "uid",
    "sequence",
    "fingerprint",
    "observed_at",
    "state",
}
_CONFLICT_FIELDS = {"connection_id", "left_uid", "right_uid"}
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
    "uid",
    "deadline_due",
    "held_until",
    "notice",
}


def export_bundle(store) -> dict:
    with store.connection() as conn:
        connections = [
            {
                "id": row["id"],
                "provider": row["provider"],
                "account_id": row["account_id"],
                "calendar_id": row["calendar_id"],
                "fixture_name": row["fixture_name"],
                "state": row["state"],
                "history_cursor": row["history_cursor"],
                "next_event": row["next_event"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in conn.execute(
                "SELECT * FROM offline_calendar_connections ORDER BY created_at, id"
            )
        ]
        items = [
            {
                "connection_id": row["connection_id"],
                "uid": row["uid"],
                "local_event_id": row["local_event_id"],
                "task_id": row["task_id"],
                "sequence": row["sequence"],
                "fingerprint": row["fingerprint"],
                "kind": row["kind"],
                "deadline_notified_due": row["deadline_notified_due"],
                "cancelled": row["cancelled"],
            }
            for row in conn.execute(
                "SELECT * FROM offline_calendar_items ORDER BY connection_id, uid"
            )
        ]
        revisions = [
            {
                "connection_id": row["connection_id"],
                "uid": row["uid"],
                "sequence": row["sequence"],
                "fingerprint": row["fingerprint"],
                "observed_at": row["observed_at"],
                "state": row["state"],
            }
            for row in conn.execute(
                "SELECT * FROM offline_calendar_revisions ORDER BY connection_id, uid, sequence"
            )
        ]
        conflicts = [
            {
                "connection_id": row["connection_id"],
                "left_uid": row["left_uid"],
                "right_uid": row["right_uid"],
            }
            for row in conn.execute(
                "SELECT * FROM offline_calendar_conflicts "
                "ORDER BY connection_id, left_uid, right_uid"
            )
        ]
        tracked = {(item["connection_id"], item["uid"]) for item in items}
        live_events = {row[0] for row in conn.execute("SELECT id FROM events WHERE deleted=0")}
        # External local appointments can be deleted independently. Their old
        # notification dedup markers are not authoritative calendar data.
        conflicts = [
            pair
            for pair in conflicts
            if all(
                (pair["connection_id"], pair[end]) in tracked or pair[end] in live_events
                for end in ("left_uid", "right_uid")
            )
        ]
        attempts = []
        for row in conn.execute("SELECT * FROM offline_calendar_attempts ORDER BY started_at, id"):
            response = None if row["response"] is None else json.loads(row["response"])
            attempts.append(
                {
                    "id": row["id"],
                    "connection_id": row["connection_id"],
                    "state": row["state"],
                    "cursor_before": row["cursor_before"],
                    "cursor_after": row["cursor_after"],
                    "response": response,
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                }
            )
        holds = []
        for row in conn.execute("SELECT * FROM offline_calendar_notice_holds ORDER BY notice_id"):
            holds.append(
                {
                    "notice_id": row["notice_id"],
                    "connection_id": row["connection_id"],
                    "uid": row["uid"],
                    "deadline_due": row["deadline_due"],
                    "held_until": row["held_until"],
                    "notice": json.loads(row["payload"]),
                }
            )
    return {
        "connections": connections,
        "items": items,
        "revisions": revisions,
        "conflicts": conflicts,
        "attempts": attempts,
        "notice_holds": holds,
    }


def validate_bundle(bundle, *, task_ids: set[str], event_ids: set[str]) -> dict:
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_FIELDS:
        raise ValueError("Invalid calendar backup")
    if (
        len(bundle["connections"]) > CONNECTION_LIMIT
        or len(bundle["items"]) > ITEM_LIMIT
        or len(bundle["revisions"]) > REVISION_LIMIT
        or len(bundle["conflicts"]) > CONFLICT_LIMIT
        or len(bundle["attempts"]) > ATTEMPT_LIMIT
        or len(bundle["notice_holds"]) > HOLD_LIMIT
    ):
        raise ValueError("Invalid calendar backup")
    connections = [_connection(row) for row in bundle["connections"]]
    by_id = {row["id"]: row for row in connections}
    if len(by_id) != len(connections):
        raise ValueError("Invalid calendar backup")
    accounts = {(row["provider"], row["account_id"]) for row in connections}
    if len(accounts) != len(connections):
        raise ValueError("Invalid calendar backup")
    items = []
    item_keys = set()
    for row in bundle["items"]:
        item = _item(row, by_id, task_ids, event_ids)
        key = (item["connection_id"], item["uid"])
        if key in item_keys:
            raise ValueError("Invalid calendar backup")
        item_keys.add(key)
        items.append(item)
    revisions = []
    revision_keys = set()
    for row in bundle["revisions"]:
        revision = _revision(row, by_id)
        key = (revision["connection_id"], revision["uid"], revision["sequence"])
        if key in revision_keys:
            raise ValueError("Invalid calendar backup")
        revision_keys.add(key)
        revisions.append(revision)
    _revisions_match_items(items, revisions)
    conflicts = []
    conflict_keys = set()
    for row in bundle["conflicts"]:
        conflict = _conflict(row, item_keys, event_ids)
        key = (conflict["connection_id"], conflict["left_uid"], conflict["right_uid"])
        if key in conflict_keys:
            raise ValueError("Invalid calendar backup")
        conflict_keys.add(key)
        conflicts.append(conflict)
    attempts = []
    attempt_ids = set()
    for row in bundle["attempts"]:
        attempt = _attempt(row, by_id)
        if attempt["id"] in attempt_ids:
            raise ValueError("Invalid calendar backup")
        attempt_ids.add(attempt["id"])
        attempts.append(attempt)
    holds = []
    hold_ids = set()
    for row in bundle["notice_holds"]:
        hold = _hold(row, item_keys)
        if hold["notice_id"] in hold_ids:
            raise ValueError("Invalid calendar backup")
        hold_ids.add(hold["notice_id"])
        holds.append(hold)
    for connection in connections:
        cursor = connection["history_cursor"]
        if cursor is None:
            continue
        applied = [
            row["sequence"]
            for row in revisions
            if row["connection_id"] == connection["id"] and row["state"] == "applied"
        ]
        # A partial later batch keeps its last completed cursor while retaining
        # the already applied revisions needed for an idempotent restart.
        if int(cursor) not in applied:
            raise ValueError("Invalid calendar backup")
    return {
        "connections": connections,
        "items": items,
        "revisions": revisions,
        "conflicts": conflicts,
        "attempts": attempts,
        "notice_holds": holds,
    }


def restore_bundle(conn, bundle) -> dict:
    """Insert connections that are not already present. Do not rewrite a live cursor."""
    created = 0
    kept = 0
    for connection in bundle["connections"]:
        if conn.execute(
            "SELECT 1 FROM offline_calendar_connections WHERE id=?", (connection["id"],)
        ).fetchone():
            kept += 1
            continue
        if conn.execute(
            "SELECT 1 FROM offline_calendar_connections WHERE provider=? AND account_id=?",
            (connection["provider"], connection["account_id"]),
        ).fetchone():
            raise DomainError("CALENDAR_ALREADY_CONNECTED", 409)
        if (
            conn.execute("SELECT COUNT(*) FROM offline_calendar_connections").fetchone()[0]
            >= CONNECTION_LIMIT
        ):
            raise DomainError("INVALID_BACKUP", 422)
        owned = [row for row in bundle["items"] if row["connection_id"] == connection["id"]]
        for item in owned:
            if not conn.execute("SELECT 1 FROM tasks WHERE id=?", (item["task_id"],)).fetchone():
                raise DomainError("INVALID_BACKUP", 422)
            if (
                not item["cancelled"]
                and not conn.execute(
                    "SELECT 1 FROM events WHERE id=? AND deleted=0", (item["local_event_id"],)
                ).fetchone()
            ):
                raise DomainError("INVALID_BACKUP", 422)
        conn.execute(
            """
            INSERT INTO offline_calendar_connections(
                id, provider, account_id, calendar_id, fixture_name, state,
                history_cursor, next_event, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                connection["id"],
                connection["provider"],
                connection["account_id"],
                connection["calendar_id"],
                connection["fixture_name"],
                connection["state"],
                connection["history_cursor"],
                connection["next_event"],
                connection["created_at"],
                connection["updated_at"],
            ),
        )
        for item in owned:
            conn.execute(
                """
                INSERT INTO offline_calendar_items(
                    connection_id, uid, local_event_id, task_id, sequence, fingerprint,
                    kind, deadline_notified_due, cancelled
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["connection_id"],
                    item["uid"],
                    item["local_event_id"],
                    item["task_id"],
                    item["sequence"],
                    item["fingerprint"],
                    item["kind"],
                    item["deadline_notified_due"],
                    item["cancelled"],
                ),
            )
        for revision in bundle["revisions"]:
            if revision["connection_id"] != connection["id"]:
                continue
            conn.execute(
                """
                INSERT INTO offline_calendar_revisions(
                    connection_id, uid, sequence, fingerprint, observed_at, state
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    revision["connection_id"],
                    revision["uid"],
                    revision["sequence"],
                    revision["fingerprint"],
                    revision["observed_at"],
                    revision["state"],
                ),
            )
        for conflict in bundle["conflicts"]:
            if conflict["connection_id"] != connection["id"]:
                continue
            conn.execute(
                "INSERT INTO offline_calendar_conflicts VALUES(?,?,?)",
                (conflict["connection_id"], conflict["left_uid"], conflict["right_uid"]),
            )
        for attempt in bundle["attempts"]:
            if attempt["connection_id"] != connection["id"]:
                continue
            if conn.execute(
                "SELECT 1 FROM offline_calendar_attempts WHERE id=?", (attempt["id"],)
            ).fetchone():
                raise DomainError("INVALID_BACKUP", 422)
            response = None if attempt["response"] is None else encode(attempt["response"])
            conn.execute(
                """
                INSERT INTO offline_calendar_attempts(
                    id, connection_id, state, cursor_before, cursor_after, response,
                    started_at, finished_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
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
                INSERT INTO offline_calendar_notice_holds(
                    notice_id, connection_id, uid, deadline_due, payload, held_until
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    hold["notice_id"],
                    hold["connection_id"],
                    hold["uid"],
                    hold["deadline_due"],
                    encode(hold["notice"]),
                    hold["held_until"],
                ),
            )
        created += 1
    return {"created": created, "kept": kept}


def _revisions_match_items(items: list[dict], revisions: list[dict]) -> None:
    for item in items:
        matched = [
            row
            for row in revisions
            if row["connection_id"] == item["connection_id"]
            and row["uid"] == item["uid"]
            and row["state"] == "applied"
        ]
        if not matched or max(row["sequence"] for row in matched) != item["sequence"]:
            raise ValueError("Invalid calendar backup")
        current = next(row for row in matched if row["sequence"] == item["sequence"])
        if current["fingerprint"] != item["fingerprint"]:
            raise ValueError("Invalid calendar backup")


def _connection(row) -> dict:
    item = _only(row, _CONNECTION_FIELDS)
    if not _HEX32.fullmatch(_text(item["id"])):
        raise ValueError("Invalid calendar backup")
    if item["provider"] != "offline":
        raise ValueError("Invalid calendar backup")
    if item["state"] not in _STATES:
        raise ValueError("Invalid calendar backup")
    if not re.fullmatch(TOKEN, item["account_id"]) or not re.fullmatch(TOKEN, item["calendar_id"]):
        raise ValueError("Invalid calendar backup")
    if not re.fullmatch(NAME, item["fixture_name"]):
        raise ValueError("Invalid calendar backup")
    return {
        "id": item["id"],
        "provider": "offline",
        "account_id": item["account_id"],
        "calendar_id": item["calendar_id"],
        "fixture_name": item["fixture_name"],
        "state": item["state"],
        "history_cursor": _cursor(item["history_cursor"]),
        "next_event": _integer(item["next_event"], 0, 100_000),
        "created_at": _stamp(item["created_at"]),
        "updated_at": _stamp(item["updated_at"]),
    }


def _item(row, connections: dict, task_ids: set[str], event_ids: set[str]) -> dict:
    item = _only(row, _ITEM_FIELDS)
    connection_id = _known(item["connection_id"], connections)
    uid = _token(item["uid"])
    event_id = item["local_event_id"]
    task_id = item["task_id"]
    if not isinstance(event_id, str) or not _HEX32.fullmatch(event_id):
        raise ValueError("Invalid calendar backup")
    if not isinstance(task_id, str) or task_id not in task_ids or not _HEX32.fullmatch(task_id):
        raise ValueError("Invalid calendar backup")
    if not isinstance(item["fingerprint"], str) or not _HEX64.fullmatch(item["fingerprint"]):
        raise ValueError("Invalid calendar backup")
    if item["kind"] not in _KINDS:
        raise ValueError("Invalid calendar backup")
    cancelled = item["cancelled"]
    if isinstance(cancelled, bool) or cancelled not in {0, 1}:
        raise ValueError("Invalid calendar backup")
    if not cancelled and event_id not in event_ids:
        raise ValueError("Invalid calendar backup")
    return {
        "connection_id": connection_id,
        "uid": uid,
        "local_event_id": event_id,
        "task_id": task_id,
        "sequence": _integer(item["sequence"], 1, 1_000_000_000),
        "fingerprint": item["fingerprint"],
        "kind": item["kind"],
        "deadline_notified_due": _optional_plain(item["deadline_notified_due"], 40),
        "cancelled": cancelled,
    }


def _revision(row, connections: dict) -> dict:
    item = _only(row, _REVISION_FIELDS)
    if not isinstance(item["fingerprint"], str) or not _HEX64.fullmatch(item["fingerprint"]):
        raise ValueError("Invalid calendar backup")
    if item["state"] not in _REVISION_STATES:
        raise ValueError("Invalid calendar backup")
    return {
        "connection_id": _known(item["connection_id"], connections),
        "uid": _token(item["uid"]),
        "sequence": _integer(item["sequence"], 1, 1_000_000_000),
        "fingerprint": item["fingerprint"],
        "observed_at": _stamp(item["observed_at"]),
        "state": item["state"],
    }


def _conflict(row, items: set[tuple[str, str]], event_ids: set[str]) -> dict:
    item = _only(row, _CONFLICT_FIELDS)
    connection_id = item["connection_id"]
    left = _token(item["left_uid"])
    right = _token(item["right_uid"])
    if not isinstance(connection_id, str) or left >= right:
        raise ValueError("Invalid calendar backup")
    left_imported = (connection_id, left) in items
    right_imported = (connection_id, right) in items
    if not (left_imported or right_imported):
        raise ValueError("Invalid calendar backup")
    if not (left_imported or left in event_ids) or not (right_imported or right in event_ids):
        raise ValueError("Invalid calendar backup")
    return {"connection_id": connection_id, "left_uid": left, "right_uid": right}


def _attempt(row, connections: dict) -> dict:
    item = _only(row, _ATTEMPT_FIELDS)
    attempt_id = item["id"]
    if not isinstance(attempt_id, str) or not attempt_id or len(attempt_id) > 100:
        raise ValueError("Invalid calendar backup")
    if item["state"] not in _ATTEMPT_STATES:
        raise ValueError("Invalid calendar backup")
    response = item["response"]
    if item["state"] == "open":
        if response is not None:
            raise ValueError("Invalid calendar backup")
    elif not isinstance(response, dict) or len(encode(response)) > 20000:
        raise ValueError("Invalid calendar backup")
    finished = item["finished_at"]
    return {
        "id": attempt_id,
        "connection_id": _known(item["connection_id"], connections),
        "state": item["state"],
        "cursor_before": _cursor(item["cursor_before"]),
        "cursor_after": _cursor(item["cursor_after"]),
        "response": response,
        "started_at": _stamp(item["started_at"]),
        "finished_at": None if finished is None else _stamp(finished),
    }


def _hold(row, items: set[tuple[str, str]]) -> dict:
    item = _only(row, _HOLD_FIELDS)
    notice = item["notice"]
    if not isinstance(notice, dict) or set(notice) != set(_NOTICE_FIELDS):
        raise ValueError("Invalid calendar backup")
    if item["notice_id"] != notice["id"] or not _NOTICE_ID.fullmatch(item["notice_id"]):
        raise ValueError("Invalid calendar backup")
    if notice["kind"] not in _NOTICE_KINDS:
        raise ValueError("Invalid calendar backup")
    uid = _token(item["uid"])
    connection_id = item["connection_id"]
    if not isinstance(connection_id, str) or (connection_id, uid) not in items:
        raise ValueError("Invalid calendar backup")
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
        "connection_id": connection_id,
        "uid": uid,
        "deadline_due": _optional_plain(item["deadline_due"], 40),
        "held_until": _stamp(item["held_until"]),
        "notice": {key: notice[key] for key in _NOTICE_FIELDS},
    }


def _only(row, fields: set[str]) -> dict:
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("Invalid calendar backup")
    return row


def _known(value, connections: dict) -> str:
    if not isinstance(value, str) or value not in connections:
        raise ValueError("Invalid calendar backup")
    return value


def _token(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(TOKEN, value):
        raise ValueError("Invalid calendar backup")
    return value


def _text(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid calendar backup")
    return value


def _integer(value, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("Invalid calendar backup")
    return value


def _cursor(value):
    if value is None:
        return None
    if not isinstance(value, str) or not _CURSOR.fullmatch(value):
        raise ValueError("Invalid calendar backup")
    return value


def _plain(value, limit: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError("Invalid calendar backup")
    return value


def _optional_plain(value, limit: int):
    if value is None:
        return None
    return _plain(value, limit)


def _stamp(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid calendar backup")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid calendar backup") from None
    if parsed.tzinfo is None or not 2000 <= parsed.year <= 2100:
        raise ValueError("Invalid calendar backup")
    return iso(parsed)
