import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pwdlib import PasswordHash

from .calendar import expand_all, is_occurrence, iso, redact
from .schemas import EventInput


class DomainError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class Store:
    def __init__(self, directory, clock=None, password=None):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.directory / "desk.sqlite3"
        self.clock = clock or (lambda: datetime.now(UTC))
        self.password_hasher = PasswordHash.recommended()
        # Installed only by the trusted runtime. No HTTP/model callback surface.
        self.operation_guard = None
        with self.connection() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1),
                    data TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS owner (id INTEGER PRIMARY KEY CHECK(id=1),
                    password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, expires TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, data TEXT NOT NULL,
                    version INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS exceptions (event_id TEXT NOT NULL, occurrence_key TEXT NOT NULL,
                    data TEXT NOT NULL, PRIMARY KEY(event_id, occurrence_key));
                CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, request TEXT NOT NULL,
                    response TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS records (sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL, action TEXT NOT NULL, event_id TEXT, details TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reminders (id TEXT PRIMARY KEY, event_id TEXT NOT NULL,
                    occurrence_key TEXT NOT NULL, early_minutes INTEGER NOT NULL, due_at TEXT NOT NULL,
                    status TEXT NOT NULL, snooze_until TEXT, version INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL);
                INSERT OR IGNORE INTO state VALUES(1, 1);
                PRAGMA user_version=1;
            """)
            if not conn.execute("SELECT 1 FROM owner").fetchone():
                actual_password = password or secrets.token_urlsafe(12)
                conn.execute(
                    "INSERT INTO owner VALUES(1,?)", (self.password_hasher.hash(actual_password),)
                )
                if password is None:
                    path = self.directory / "credentials.json"
                    path.write_text(
                        json.dumps({"username": "owner", "password": actual_password}, indent=2)
                    )
                    path.chmod(0o600)
            conn.execute(
                "INSERT OR IGNORE INTO settings VALUES(1,?,1)",
                (encode({"timezone": "Asia/Hong_Kong", "hide_private": False}),),
            )
        os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self, write=False):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=FULL")
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def revision(self, conn=None):
        if conn is not None:
            return conn.execute("SELECT revision FROM state WHERE id=1").fetchone()[0]
        with self.connection() as conn:
            return self.revision(conn)

    def bump(self, conn):
        conn.execute("UPDATE state SET revision=revision+1 WHERE id=1")

    def record(self, conn, action, event_id=None, details=None):
        conn.execute(
            "INSERT INTO records(at,action,event_id,details) VALUES(?,?,?,?)",
            (iso(self.clock()), action, event_id, encode(details or {})),
        )

    def operation(self, key, payload, apply):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        request = encode(payload)
        with self.connection(write=True) as conn:
            if self.operation_guard is not None:
                self.operation_guard(conn, key, payload)
            old = conn.execute("SELECT * FROM operations WHERE id=?", (key,)).fetchone()
            if old:
                if old["request"] != request:
                    raise DomainError("OPERATION_ID_CONFLICT")
                return json.loads(old["response"])
            response = apply(conn)
            self.reconcile_reminders(conn)
            self.bump(conn)
            response["revision"] = self.revision(conn)
            response["operation_id"] = key
            conn.execute("INSERT INTO operations VALUES(?,?,?)", (key, request, encode(response)))
            return response

    def authenticate(self, username, password):
        with self.connection() as conn:
            stored = conn.execute("SELECT password_hash FROM owner WHERE id=1").fetchone()[0]
        valid = self.password_hasher.verify(password, stored)
        if username != "owner" or not valid:
            raise DomainError("INVALID_LOGIN", 401)
        token = secrets.token_urlsafe(32)
        with self.connection(write=True) as conn:
            conn.execute("DELETE FROM sessions WHERE expires<=?", (iso(self.clock()),))
            conn.execute(
                "INSERT INTO sessions VALUES(?,?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    iso(self.clock() + timedelta(hours=8)),
                ),
            )
        return token

    def session_valid(self, token):
        if not token:
            return False
        with self.connection() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (hashlib.sha256(token.encode()).hexdigest(), iso(self.clock())),
                ).fetchone()
            )

    def logout(self, token):
        with self.connection(write=True) as conn:
            conn.execute(
                "DELETE FROM sessions WHERE token_hash=?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )

    def settings(self, conn):
        row = conn.execute("SELECT * FROM settings WHERE id=1").fetchone()
        return {**json.loads(row["data"]), "version": row["version"]}

    def event(self, conn, event_id):
        row = conn.execute("SELECT * FROM events WHERE id=? AND deleted=0", (event_id,)).fetchone()
        if not row:
            raise DomainError("EVENT_NOT_FOUND", 404)
        return {**json.loads(row["data"]), "id": row["id"], "version": row["version"]}

    def data(self, conn):
        events = [
            {**json.loads(r["data"]), "id": r["id"], "version": r["version"]}
            for r in conn.execute("SELECT * FROM events WHERE deleted=0")
        ]
        exceptions = {}
        for r in conn.execute("SELECT * FROM exceptions"):
            exceptions.setdefault(r["event_id"], {})[r["occurrence_key"]] = json.loads(r["data"])
        return events, exceptions

    def snapshot(self, begin, end):
        if (
            begin.tzinfo is None
            or end.tzinfo is None
            or end <= begin
            or end - begin > timedelta(days=62)
        ):
            raise DomainError("INVALID_DATE_RANGE", 422)
        with self.connection() as conn:
            settings = self.settings(conn)
            events, exceptions = self.data(conn)
            try:
                occurrences = expand_all(events, exceptions, begin, end, settings["timezone"])
            except ValueError:
                raise DomainError("NARROW_DATE_RANGE", 422) from None
            return {
                "revision": self.revision(conn),
                "server_time": iso(self.clock()),
                "settings": settings,
                "occurrences": [redact(o, settings["hide_private"]) for o in occurrences],
                "event_count": len(events),
                "has_samples": any(e["origin"] == "sample" for e in events),
                "reminders": self.reminder_list(conn, settings),
                "device": {
                    "camera": "not_connected",
                    "voice": "not_connected",
                    "arm": "not_connected",
                    "weather": "not_connected",
                    "external_calendar": "not_connected",
                    "runtime": "mac_local",
                },
            }

    def create(self, payload, key, origin="manual"):
        base = payload.event
        duration = base.end_local - base.start_local
        dates = [base.start_local.date(), *payload.additional_dates]
        documents = []
        batch_id = uuid4().hex if len(dates) > 1 else None
        for day in dates:
            wall = datetime.combine(day, base.start_local.time())
            try:
                documents.append(
                    EventInput.model_validate(
                        {**base.model_dump(), "start_local": wall, "end_local": wall + duration}
                    ).model_dump(mode="json")
                )
            except ValueError:
                raise DomainError("VALIDATION_FAILED", 422) from None

        def apply(conn):
            count = conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]
            if count + len(documents) > 500:
                raise DomainError("EVENT_LIMIT", 422)
            ids = []
            for document in documents:
                event_id = uuid4().hex
                document.update(origin=origin, batch_id=batch_id, provider=None, external_id=None)
                conn.execute(
                    "INSERT INTO events(id,data,version) VALUES(?,?,1)",
                    (event_id, encode(document)),
                )
                self.record(conn, "created", event_id, {"origin": origin})
                ids.append(event_id)
            return {"event_ids": ids, "batch_id": batch_id}

        return self.operation(key, {"type": "create", **payload.model_dump(mode="json")}, apply)

    def event_action(self, event_id, payload, key):
        def apply(conn):
            event = self.event(conn, event_id)
            if event["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            occurrence_key = payload.occurrence_key
            if payload.scope == "occurrence" and (
                not occurrence_key or not is_occurrence(event, occurrence_key)
            ):
                raise DomainError("INVALID_OCCURRENCE", 422)
            if payload.action in {"complete", "reopen"} and payload.scope != "occurrence":
                raise DomainError("COMPLETE_ONE_OCCURRENCE", 422)
            if payload.action == "update" and payload.event is None:
                raise DomainError("EVENT_REQUIRED", 422)
            if payload.scope == "series":
                if payload.action == "delete":
                    conn.execute(
                        "UPDATE events SET deleted=1,version=version+1 WHERE id=?", (event_id,)
                    )
                else:
                    new = payload.event.model_dump(mode="json")
                    new.update(
                        {k: event[k] for k in ["origin", "batch_id", "provider", "external_id"]}
                    )
                    existing_exceptions = conn.execute(
                        "SELECT occurrence_key FROM exceptions WHERE event_id=?", (event_id,)
                    ).fetchall()
                    if existing_exceptions and (
                        new["start_local"] != event["start_local"]
                        or new["recurrence"] != event["recurrence"]
                    ):
                        raise DomainError("SERIES_HAS_EXCEPTIONS")
                    conn.execute(
                        "UPDATE events SET data=?,version=version+1 WHERE id=?",
                        (encode(new), event_id),
                    )
            else:
                row = conn.execute(
                    "SELECT data FROM exceptions WHERE event_id=? AND occurrence_key=?",
                    (event_id, occurrence_key),
                ).fetchone()
                exception = json.loads(row[0]) if row else {}
                if exception.get("cancelled"):
                    raise DomainError("OCCURRENCE_CANCELLED")
                if payload.action == "delete":
                    exception["cancelled"] = True
                elif payload.action == "update":
                    if payload.event.recurrence.frequency != "none":
                        raise DomainError("OCCURRENCE_CANNOT_REPEAT", 422)
                    exception["override"] = payload.event.model_dump(mode="json")
                else:
                    exception["completed"] = payload.action == "complete"
                conn.execute(
                    "INSERT INTO exceptions VALUES(?,?,?) ON CONFLICT(event_id,occurrence_key) "
                    "DO UPDATE SET data=excluded.data",
                    (event_id, occurrence_key, encode(exception)),
                )
                conn.execute("UPDATE events SET version=version+1 WHERE id=?", (event_id,))
            self.record(
                conn,
                payload.action,
                event_id,
                {"scope": payload.scope, "occurrence_key": occurrence_key},
            )
            return {"event_id": event_id, "version": event["version"] + 1}

        return self.operation(
            key, {"type": "event_action", "id": event_id, **payload.model_dump(mode="json")}, apply
        )

    def update_settings(self, payload, key):
        def apply(conn):
            old = self.settings(conn)
            if old["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            data = payload.model_dump(exclude={"expected_version"})
            conn.execute("UPDATE settings SET data=?,version=version+1 WHERE id=1", (encode(data),))
            self.record(conn, "settings_updated")
            return {"settings": {**data, "version": old["version"] + 1}}

        return self.operation(key, {"type": "settings", **payload.model_dump(mode="json")}, apply)

    def reconcile_reminders(self, conn):
        now = self.clock()
        events, exceptions = self.data(conn)
        occurrences = expand_all(
            events,
            exceptions,
            now - timedelta(days=8),
            now + timedelta(days=8),
            include_conflicts=False,
        )
        expected = {}
        for occ in occurrences:
            if occ["completed"]:
                continue
            start = datetime.fromisoformat(occ["start"].replace("Z", "+00:00"))
            for early in occ["reminder_minutes"]:
                due = start - timedelta(minutes=early)
                rid = hashlib.sha256(
                    f"{occ['id']}/{occ['occurrence_key']}/{early}".encode()
                ).hexdigest()[:32]
                expected[rid] = (occ, early, due)
        rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM reminders")}
        changed = False
        for rid, (occ, early, due) in expected.items():
            old = rows.get(rid)
            due_text = iso(due)
            state = (
                "pending"
                if due > now
                else ("due" if due >= now - timedelta(minutes=15) else "missed")
            )
            if old is None:
                conn.execute(
                    "INSERT INTO reminders(id,event_id,occurrence_key,early_minutes,due_at,status) "
                    "VALUES(?,?,?,?,?,?)",
                    (rid, occ["id"], occ["occurrence_key"], early, due_text, state),
                )
                changed = True
            elif old["due_at"] != due_text or old["status"] == "cancelled":
                conn.execute(
                    "UPDATE reminders SET due_at=?,status=?,snooze_until=NULL,version=version+1 WHERE id=?",
                    (due_text, state, rid),
                )
                changed = True
            elif old["status"] in {"pending", "snoozed"}:
                trigger = old["snooze_until"] or old["due_at"]
                if trigger <= iso(now):
                    target = "due" if trigger >= iso(now - timedelta(minutes=15)) else "missed"
                    conn.execute(
                        "UPDATE reminders SET status=?,version=version+1 WHERE id=?", (target, rid)
                    )
                    changed = True
        for rid, old in rows.items():
            if rid not in expected and old["status"] in {"pending", "due", "snoozed"}:
                conn.execute(
                    "UPDATE reminders SET status='cancelled',version=version+1 WHERE id=?", (rid,)
                )
                changed = True
        return changed

    def tick(self):
        with self.connection(write=True) as conn:
            if self.reconcile_reminders(conn):
                self.bump(conn)

    def reminder_list(self, conn, settings):
        result = []
        for row in conn.execute(
            "SELECT * FROM reminders WHERE status IN ('due','snoozed') ORDER BY due_at DESC LIMIT 100"
        ):
            try:
                event = self.event(conn, row["event_id"])
            except DomainError:
                continue
            exception_row = conn.execute(
                "SELECT data FROM exceptions WHERE event_id=? AND occurrence_key=?",
                (row["event_id"], row["occurrence_key"]),
            ).fetchone()
            exception = json.loads(exception_row[0]) if exception_row else {}
            current = exception.get("override") or event
            hidden = settings["hide_private"] and current["visibility"] == "private"
            result.append(
                {
                    **dict(row),
                    "title": "" if hidden else current["title"],
                    "redacted": hidden,
                    "visibility": current["visibility"],
                }
            )
        return result

    def reminder_action(self, reminder_id, payload, key):
        def apply(conn):
            self.reconcile_reminders(conn)
            row = conn.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone()
            if not row or row["status"] not in {"due", "snoozed"}:
                raise DomainError("REMINDER_NOT_ACTIVE")
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            status = "acknowledged" if payload.action == "acknowledge" else "snoozed"
            until = (
                iso(self.clock() + timedelta(minutes=payload.minutes))
                if status == "snoozed"
                else None
            )
            conn.execute(
                "UPDATE reminders SET status=?,snooze_until=?,version=version+1 WHERE id=?",
                (status, until, reminder_id),
            )
            self.record(conn, payload.action, row["event_id"], {"reminder_id": reminder_id})
            return {"reminder_id": reminder_id, "status": status}

        return self.operation(
            key, {"type": "reminder_action", "id": reminder_id, **payload.model_dump()}, apply
        )

    def records(self, limit=200):
        with self.connection() as conn:
            hidden = self.settings(conn)["hide_private"]
            records = []
            for row in conn.execute(
                "SELECT * FROM records ORDER BY sequence DESC LIMIT ?", (min(10000, max(1, limit)),)
            ):
                title = None
                if row["event_id"]:
                    event = conn.execute(
                        "SELECT data FROM events WHERE id=?", (row["event_id"],)
                    ).fetchone()
                    if event:
                        event = json.loads(event[0])
                        title = (
                            "" if hidden and event["visibility"] == "private" else event["title"]
                        )
                records.append({**dict(row), "details": json.loads(row["details"]), "title": title})
            return records

    def backup(self, path):
        with sqlite3.connect(self.path) as source, sqlite3.connect(path) as target:
            source.backup(target)
