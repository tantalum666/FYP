"""Owner-approved follow-up for one saved memory, and one morning check-in.

A draft does not write. Approval arms one check at a local time. The same rules
tick raises it once, after quiet hours and after proactive reminders are on.
An individual notice names the time, not the fact. The morning check-in is one
approved row on that tick: it cites every still-active follow-up that is due by
its time, and those follow-ups do not each raise again. Deleting or expiring a
memory drops it and does not repeat the wording. No model call and no mailbox,
calendar, or task write.
"""

import re
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import Field, field_validator

from .calendar import iso, wall_to_utc
from .notify import Notice
from .schemas import EventInput, StrictModel
from .store import DomainError
from .workspace_data import is_quiet, quiet_until

MAX_OPEN = 50
MAX_RAISES = 3
MIN_CITATIONS = 2
SNOOZE = timedelta(hours=1)
OPEN_STATES = ("pending", "held", "raised")
CHECKIN_OPEN = ("pending", "held", "raised")
_ID = re.compile(r"^[a-f0-9]{32}$")


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _flat(body: str) -> str:
    return " ".join(body.split())


def _cite_line(bodies: list[str], language: str) -> str:
    line = " · ".join(bodies)
    count = len(bodies)
    if language == "zh":
        return f"Alice 提起这 {count} 条记忆：{line}"
    return f"Alice is citing {count}: {line}"


def morning_reason(
    state: str,
    *,
    due_local: str,
    timezone: str,
    hold_reason: str | None,
    quiet_delayed: bool,
    left_out: int,
) -> dict[str, str]:
    """Why the morning check-in is waiting or sent. Fact text stays in the notice body."""
    when = f"{due_local} ({timezone})"
    omitted = ""
    omitted_zh = ""
    if left_out and state == "raised":
        omitted = (
            " Memories that are no longer active were left out, "
            "and their wording is not repeated."
        )
        omitted_zh = "不再有效的记忆已略去，这里不再重复那些文字。"
    if state == "pending":
        text = (
            f"Alice will cite the due follow-ups at {when} because you approved "
            "one morning check-in. Quiet hours can hold that notice.",
            f"你已批准在 {when} 做一次早晨核对。Alice 会把到期的跟进合成一条；"
            "如果正好在安静时段，会等到结束再发出。",
        )
    elif state == "held" and hold_reason == "quiet":
        text = (
            "This morning check-in is waiting because quiet hours are in effect. "
            f"You approved it for {when}.",
            f"现在是安静时段，所以这次早晨核对先不发出。你批准的时间是 {when}。",
        )
    elif state == "held":
        text = (
            "This morning check-in is waiting because proactive reminders are off. "
            f"You approved it for {when}.",
            f"主动提醒已关闭，所以这次早晨核对先不发出。你批准的时间是 {when}。",
        )
    elif state == "raised" and quiet_delayed:
        text = (
            f"Morning check-in fired because you approved it for {when}, "
            "that time has passed, and quiet hours have ended.",
            f"早晨核对现在发出，因为你批准的时间 {when} 已过，而且安静时段已经结束。",
        )
    elif state == "raised":
        text = (
            f"Morning check-in fired because you approved it for {when}, "
            "that time has arrived, and quiet hours are not in effect.",
            f"早晨核对现在发出，因为你批准的时间 {when} 已到，而且现在不是安静时段。",
        )
    else:
        text = (
            "You dismissed this morning check-in. Alice will not send it again.",
            "你已关闭这次早晨核对。Alice 不会再发出。",
        )
        omitted = omitted_zh = ""
    return {"reason_en": text[0] + omitted, "reason_zh": text[1] + omitted_zh}


def reason_for(
    state: str,
    *,
    due_local: str,
    timezone: str,
    hold_reason: str | None,
    quiet_delayed: bool,
    memory_active: bool,
    memory_updated: bool,
    bundled: bool = False,
) -> dict[str, str]:
    """Why this follow-up is waiting, raised, or closed. The fact text stays out."""
    when = f"{due_local} ({timezone})"
    if state == "cancelled" or not memory_active:
        if state == "cancelled":
            return {
                "reason_en": (
                    "Alice cancelled this follow-up because the memory is no longer active. "
                    "The saved wording is not repeated."
                ),
                "reason_zh": "Alice 取消了这次跟进，因为这条记忆已经不再有效。这里不再重复原来的文字。",
            }
        return {
            "reason_en": (
                "This follow-up will not be raised because the memory is no longer active. "
                "The saved wording is not repeated."
            ),
            "reason_zh": "这条记忆已经不再有效，所以不会提醒。这里不再重复原来的文字。",
        }
    updated = ""
    updated_zh = ""
    if memory_updated and state in OPEN_STATES:
        updated = " The memory was updated after approval; this uses the current wording."
        updated_zh = "批准之后这条记忆更新过，这里使用当前文字。"
    if state == "pending":
        text = (
            f"Alice will raise this at {when} because you approved a follow-up for this memory. "
            "Quiet hours can hold it until they end.",
            f"你已批准在 {when} 跟进这条记忆。Alice 会到时提醒；如果正好在安静时段，会等到结束再提醒。",
        )
    elif state == "held" and hold_reason == "quiet":
        text = (
            f"This follow-up is waiting because quiet hours are in effect. You approved it for {when}.",
            f"现在是安静时段，所以这次跟进先不提醒。你批准的时间是 {when}。",
        )
    elif state == "held" and hold_reason == "morning":
        text = (
            "This follow-up waits for the morning check-in you approved. "
            "Alice will cite it there once, not as its own reminder.",
            "这次跟进会并进你批准的早晨核对。Alice 只在那里提起一次，不会单独提醒。",
        )
    elif state == "held":
        text = (
            "This follow-up is waiting because proactive reminders are off. "
            f"You approved it for {when}.",
            f"主动提醒已关闭，所以这次跟进先不提醒。你批准的时间是 {when}。",
        )
    elif state == "raised" and bundled:
        text = (
            "Alice cited this in the morning check-in, so it does not raise a separate reminder.",
            "Alice 已在早晨核对里提起这条，不会再单独提醒。",
        )
    elif state == "raised" and quiet_delayed:
        text = (
            f"Alice raised this because the approved time {when} has passed and quiet hours have ended.",
            f"Alice 现在提醒你，因为批准的时间 {when} 已过，而且安静时段已经结束。",
        )
    elif state == "raised":
        text = (
            f"Alice raised this because the approved time {when} has arrived "
            "and quiet hours are not in effect.",
            f"Alice 现在提醒你，因为批准的时间 {when} 已到，而且现在不是安静时段。",
        )
    elif state == "handled":
        text = (
            "You marked this follow-up handled. Alice will not raise it again.",
            "你已标为处理完。Alice 不会再次提醒。",
        )
        updated = updated_zh = ""
    else:
        text = (
            "You dismissed this follow-up. Alice will not raise it again.",
            "你已关闭这次跟进。Alice 不会再次提醒。",
        )
        updated = updated_zh = ""
    return {"reason_en": text[0] + updated, "reason_zh": text[1] + updated_zh}


class FollowUpTime(StrictModel):
    memory_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    due_local: datetime
    timezone: str | None = None

    @field_validator("due_local")
    @classmethod
    def local(cls, value):
        return EventInput.local_datetime(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        if value is None:
            return None
        return EventInput.valid_zone(value)


class FollowUpApprove(FollowUpTime):
    memory_version: int = Field(ge=1, strict=True)


class FollowUpRevision(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    due_local: datetime | None = None
    timezone: str | None = None

    @field_validator("due_local")
    @classmethod
    def local(cls, value):
        if value is None:
            return None
        return EventInput.local_datetime(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        if value is None:
            return None
        return EventInput.valid_zone(value)


class FollowUpResolution(StrictModel):
    action: str
    expected_version: int = Field(ge=1, strict=True)

    @field_validator("action")
    @classmethod
    def known(cls, value):
        if value not in {"handled", "dismissed", "snooze"}:
            raise ValueError("Use handled, dismissed, or snooze")
        return value


class MorningTime(StrictModel):
    due_local: datetime
    timezone: str | None = None

    @field_validator("due_local")
    @classmethod
    def local(cls, value):
        return EventInput.local_datetime(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        if value is None:
            return None
        return EventInput.valid_zone(value)


class MorningRevision(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    due_local: datetime | None = None
    timezone: str | None = None

    @field_validator("due_local")
    @classmethod
    def local(cls, value):
        if value is None:
            return None
        return EventInput.local_datetime(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        if value is None:
            return None
        return EventInput.valid_zone(value)


class MorningDismiss(StrictModel):
    expected_version: int = Field(ge=1, strict=True)


class MemoryFollowUpService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_followups(
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    due_local TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    hold_reason TEXT,
                    hold_until TEXT,
                    not_before TEXT,
                    quiet_delayed INTEGER NOT NULL,
                    raise_generation INTEGER NOT NULL,
                    notice_id TEXT,
                    raised_at TEXT,
                    approved_memory_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    bundle_id TEXT
                );
                CREATE INDEX IF NOT EXISTS memory_followups_due
                    ON memory_followups(state, due_at);
                CREATE UNIQUE INDEX IF NOT EXISTS memory_followups_one_open
                    ON memory_followups(memory_id)
                    WHERE state IN ('pending', 'held', 'raised');
                CREATE TABLE IF NOT EXISTS memory_morning_checkins(
                    id TEXT PRIMARY KEY,
                    due_at TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    due_local TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    hold_reason TEXT,
                    hold_until TEXT,
                    quiet_delayed INTEGER NOT NULL,
                    raise_generation INTEGER NOT NULL,
                    notice_id TEXT,
                    raised_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS memory_morning_one_open
                    ON memory_morning_checkins(
                        (CASE WHEN state IN ('pending', 'held', 'raised') THEN 1 END)
                    );
                """
            )
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(memory_followups)")
            }
            if "bundle_id" not in columns:
                conn.execute("ALTER TABLE memory_followups ADD COLUMN bundle_id TEXT")

    def _memory_row(self, conn, memory_id):
        return conn.execute(
            "SELECT * FROM owner_memories WHERE id=?", (memory_id,)
        ).fetchone()

    def _usable(self, row, now: str) -> bool:
        if not row or row["state"] != "active":
            return False
        return not (row["expires_at"] and row["expires_at"] <= now)

    def _active(self, conn, memory_id):
        row = self._memory_row(conn, memory_id)
        if not self._usable(row, iso(self.store.clock())):
            raise DomainError("MEMORY_NOT_FOUND", 404)
        return row

    def _followup(self, conn, followup_id):
        if not _ID.fullmatch(followup_id or ""):
            raise DomainError("FOLLOWUP_NOT_FOUND", 404)
        row = conn.execute(
            "SELECT * FROM memory_followups WHERE id=?", (followup_id,)
        ).fetchone()
        if not row:
            raise DomainError("FOLLOWUP_NOT_FOUND", 404)
        return row

    def _resolve_time(self, conn, due_local: datetime, timezone: str | None):
        zone = timezone or self.store.settings(conn)["timezone"]
        try:
            ZoneInfo(zone)
            due = wall_to_utc(due_local, zone, reject_ambiguous=True)
        except (ValueError, KeyError):
            raise DomainError("FOLLOWUP_TIME_INVALID", 422) from None
        if due <= self.store.clock():
            raise DomainError("FOLLOWUP_TIME_PAST", 422)
        return due, zone

    def _view(self, conn, row) -> dict:
        now = iso(self.store.clock())
        memory = self._memory_row(conn, row["memory_id"])
        active = self._usable(memory, now)
        updated = bool(active and memory["version"] != row["approved_memory_version"])
        bundled = bool(row["bundle_id"])
        copy = reason_for(
            row["state"],
            due_local=row["due_local"],
            timezone=row["timezone"],
            hold_reason=row["hold_reason"],
            quiet_delayed=bool(row["quiet_delayed"]),
            memory_active=active,
            memory_updated=updated,
            bundled=bundled,
        )
        return {
            "id": row["id"],
            "memory_id": row["memory_id"],
            "state": row["state"],
            "version": row["version"],
            "due_at": row["due_at"],
            "due_local": row["due_local"],
            "timezone": row["timezone"],
            "body": memory["body"] if active else None,
            "memory_active": active,
            "memory_version": memory["version"] if memory and active else None,
            "memory_updated": updated,
            "hold_reason": row["hold_reason"],
            "hold_until": row["hold_until"],
            "raised_at": row["raised_at"],
            "notice_id": row["notice_id"],
            "bundled": bundled,
            "armed": row["state"] in OPEN_STATES,
            **copy,
        }

    def listing(self) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_followups ORDER BY due_at, id"
            ).fetchall()
            opened = [row for row in rows if row["state"] in OPEN_STATES]
            closed = [row for row in rows if row["state"] not in OPEN_STATES][:20]
            return {"followups": [self._view(conn, row) for row in opened + closed]}

    def draft(self, payload: FollowUpTime) -> dict:
        with self.store.connection() as conn:
            memory = self._active(conn, payload.memory_id)
            due, zone = self._resolve_time(conn, payload.due_local, payload.timezone)
            self._reject_extra(conn, payload.memory_id)
            return {
                "draft": {
                    "memory_id": memory["id"],
                    "memory_version": memory["version"],
                    "body": memory["body"],
                    "due_at": iso(due),
                    "due_local": _stamp(payload.due_local),
                    "timezone": zone,
                    "armed": False,
                },
                "saved": False,
                "armed": False,
            }

    def approve(self, payload: FollowUpApprove, key: str) -> dict:
        due_local = _stamp(payload.due_local)

        def apply(conn):
            memory = self._active(conn, payload.memory_id)
            if memory["version"] != payload.memory_version:
                raise DomainError("VERSION_CONFLICT")
            due, zone = self._resolve_time(conn, payload.due_local, payload.timezone)
            self._reject_extra(conn, payload.memory_id)
            now = iso(self.store.clock())
            followup_id = uuid4().hex
            try:
                conn.execute(
                    "INSERT INTO memory_followups("
                    "id, memory_id, due_at, timezone, due_local, state, version, "
                    "hold_reason, hold_until, not_before, quiet_delayed, raise_generation, "
                    "notice_id, raised_at, approved_memory_version, created_at, updated_at"
                    ") VALUES(?,?,?,?,?,'pending',1,NULL,NULL,NULL,0,0,NULL,NULL,?,?,?)",
                    (
                        followup_id,
                        payload.memory_id,
                        iso(due),
                        zone,
                        due_local,
                        memory["version"],
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                raise DomainError("MEMORY_FOLLOWUP_OPEN", 409) from None
            self.store.record(
                conn,
                "memory_followup_approved",
                details={"id": followup_id, "memory_id": payload.memory_id},
            )
            row = self._followup(conn, followup_id)
            return {"followup": self._view(conn, row), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_followup_approve",
                "memory_id": payload.memory_id,
                "due_local": due_local,
                "timezone": payload.timezone,
                "memory_version": payload.memory_version,
            },
            apply,
        )

    def revise(self, followup_id: str, payload: FollowUpRevision, key: str) -> dict:
        provided = set(payload.model_fields_set)
        if "due_local" in provided and payload.due_local is None:
            raise DomainError("FOLLOWUP_TIME_REQUIRED", 422)
        if "timezone" in provided and payload.timezone is None:
            raise DomainError("FOLLOWUP_TIME_REQUIRED", 422)
        due_text = _stamp(payload.due_local) if "due_local" in provided else None

        def apply(conn):
            row = self._followup(conn, followup_id)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["state"] not in {"pending", "held"}:
                raise DomainError("FOLLOWUP_CLOSED", 409)
            if "due_local" not in provided and "timezone" not in provided:
                return {"followup": self._view(conn, row), "saved": True}
            due_local = payload.due_local if "due_local" in provided else datetime.fromisoformat(
                row["due_local"]
            )
            timezone = payload.timezone if "timezone" in provided else row["timezone"]
            due, zone = self._resolve_time(conn, due_local, timezone)
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE memory_followups SET due_at=?, timezone=?, due_local=?, state='pending', "
                "hold_reason=NULL, hold_until=NULL, not_before=NULL, quiet_delayed=0, "
                "version=version+1, updated_at=? WHERE id=?",
                (iso(due), zone, _stamp(due_local), now, followup_id),
            )
            self.store.record(
                conn, "memory_followup_revised", details={"id": followup_id}
            )
            return {"followup": self._view(conn, self._followup(conn, followup_id)), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_followup_revise",
                "id": followup_id,
                "expected_version": payload.expected_version,
                "fields": sorted(provided),
                "due_local": due_text,
                "timezone": payload.timezone if "timezone" in provided else None,
            },
            apply,
        )

    def resolve(self, followup_id: str, payload: FollowUpResolution, key: str) -> dict:
        def apply(conn):
            row = self._followup(conn, followup_id)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if payload.action == "snooze":
                if row["state"] != "raised":
                    raise DomainError("FOLLOWUP_NOT_RAISED", 409)
                due = self.store.clock() + SNOOZE
                local = due.astimezone(ZoneInfo(row["timezone"]))
                now = iso(self.store.clock())
                conn.execute(
                    "UPDATE memory_followups SET due_at=?, due_local=?, state='pending', "
                    "hold_reason=NULL, hold_until=NULL, not_before=NULL, quiet_delayed=0, "
                    "bundle_id=NULL, version=version+1, updated_at=? WHERE id=?",
                    (iso(due), local.strftime("%Y-%m-%dT%H:%M"), now, followup_id),
                )
                self.store.record(
                    conn, "memory_followup_snoozed", details={"id": followup_id}
                )
            elif row["state"] == payload.action:
                return {"followup": self._view(conn, row), "saved": True}
            elif row["state"] not in OPEN_STATES:
                raise DomainError("FOLLOWUP_CLOSED", 409)
            else:
                now = iso(self.store.clock())
                conn.execute(
                    "UPDATE memory_followups SET state=?, hold_reason=NULL, hold_until=NULL, "
                    "not_before=NULL, version=version+1, updated_at=? WHERE id=?",
                    (payload.action, now, followup_id),
                )
                self.store.record(
                    conn,
                    "memory_followup_resolved",
                    details={"id": followup_id, "action": payload.action},
                )
            return {"followup": self._view(conn, self._followup(conn, followup_id)), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_followup_resolve",
                "id": followup_id,
                "action": payload.action,
                "expected_version": payload.expected_version,
            },
            apply,
        )

    def _reject_extra(self, conn, memory_id: str) -> None:
        existing = conn.execute(
            "SELECT id FROM memory_followups WHERE memory_id=? "
            "AND state IN ('pending','held','raised')",
            (memory_id,),
        ).fetchone()
        if existing:
            raise DomainError("MEMORY_FOLLOWUP_OPEN", 409)
        open_count = conn.execute(
            "SELECT COUNT(*) FROM memory_followups WHERE state IN ('pending','held','raised')"
        ).fetchone()[0]
        if open_count >= MAX_OPEN:
            raise DomainError("MEMORY_FOLLOWUP_LIMIT", 422)

    def _cancel(self, conn, row, now: str) -> bool:
        conn.execute(
            "UPDATE memory_followups SET state='cancelled', hold_reason=NULL, hold_until=NULL, "
            "not_before=NULL, version=version+1, updated_at=? WHERE id=? AND state!=?",
            (now, row["id"], "cancelled"),
        )
        self.store.record(conn, "memory_followup_cancelled", details={"id": row["id"]})
        return True

    def _hold(self, conn, row, now, prefs, now_local, quiet: bool) -> bool:
        if quiet:
            until = quiet_until(prefs, now_local)
            until_iso = iso(until) if until else None
            reason = "quiet"
            delayed = 1
        else:
            until_iso = None
            reason = "proactivity"
            delayed = row["quiet_delayed"]
        if (
            row["state"] == "held"
            and row["hold_reason"] == reason
            and row["hold_until"] == until_iso
            and row["quiet_delayed"] == delayed
        ):
            return False
        conn.execute(
            "UPDATE memory_followups SET state='held', hold_reason=?, hold_until=?, "
            "quiet_delayed=?, not_before=NULL, version=version+1, updated_at=? WHERE id=?",
            (reason, until_iso, delayed, now, row["id"]),
        )
        self.store.record(
            conn, "memory_followup_held", details={"id": row["id"], "reason": reason}
        )
        return True

    def _defer(self, conn, row, now: datetime) -> bool:
        if row["not_before"] and _parse(row["not_before"]) > now:
            return False
        later = iso(now + timedelta(minutes=1))
        conn.execute(
            "UPDATE memory_followups SET not_before=?, version=version+1, updated_at=? WHERE id=?",
            (later, iso(now), row["id"]),
        )
        return True

    def _notice(self, conn, row) -> Notice:
        view = self._view(conn, row)
        return Notice(
            row["notice_id"],
            "memory_followup",
            "Alice remembered",
            "Alice 记得这件事",
            "Open Memory to review it.",
            "请打开记忆页查看。",
            view["reason_en"],
            view["reason_zh"],
        )

    def _raise(self, conn, row, now: str):
        memory = self._memory_row(conn, row["memory_id"])
        if not self._usable(memory, now):
            self._cancel(conn, row, now)
            return None
        generation = row["raise_generation"] + 1
        notice_id = f"memory-followup-{row['id']}-{generation}"
        conn.execute(
            "UPDATE memory_followups SET state='raised', raise_generation=?, notice_id=?, "
            "raised_at=?, hold_reason=NULL, hold_until=NULL, not_before=NULL, bundle_id=NULL, "
            "version=version+1, updated_at=? WHERE id=?",
            (generation, notice_id, now, now, row["id"]),
        )
        self.store.record(conn, "memory_followup_raised", details={"id": row["id"]})
        updated = self._followup(conn, row["id"])
        return self._notice(conn, updated)

    def _cancel_inactive(self, conn, now: str) -> bool:
        wrote = False
        rows = conn.execute(
            "SELECT * FROM memory_followups WHERE state IN ('pending','held','raised')"
        ).fetchall()
        for row in rows:
            if not self._usable(self._memory_row(conn, row["memory_id"]), now):
                wrote = self._cancel(conn, row, now) or wrote
        return wrote

    def _due(self, conn, now: str):
        return conn.execute(
            "SELECT * FROM memory_followups WHERE state IN ('pending','held') AND due_at<=? "
            "AND (not_before IS NULL OR not_before<=?) ORDER BY due_at, id",
            (now, now),
        ).fetchall()

    def _undelivered(self, conn, skip: set[str]) -> list[Notice]:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notice_deliveries'"
        ).fetchone():
            return []
        notices = []
        rows = conn.execute(
            "SELECT * FROM memory_followups WHERE state='raised' AND notice_id IS NOT NULL"
        ).fetchall()
        for row in rows:
            if row["notice_id"] in skip:
                continue
            seen = conn.execute(
                "SELECT 1 FROM notice_deliveries WHERE notice_id=? AND channel='in_app'",
                (row["notice_id"],),
            ).fetchone()
            if not seen:
                notices.append(self._notice(conn, row))
        return notices

    def _checkin(self, conn, checkin_id):
        if not _ID.fullmatch(checkin_id or ""):
            raise DomainError("MORNING_CHECKIN_NOT_FOUND", 404)
        row = conn.execute(
            "SELECT * FROM memory_morning_checkins WHERE id=?", (checkin_id,)
        ).fetchone()
        if not row:
            raise DomainError("MORNING_CHECKIN_NOT_FOUND", 404)
        return row

    def _open_checkin(self, conn):
        return conn.execute(
            "SELECT * FROM memory_morning_checkins WHERE state IN ('pending','held','raised') "
            "ORDER BY due_at, id LIMIT 1"
        ).fetchone()

    def _reject_open_checkin(self, conn) -> None:
        if self._open_checkin(conn):
            raise DomainError("MORNING_CHECKIN_OPEN", 409)

    def _preview_pairs(self, conn, due_at: str, now: str):
        rows = conn.execute(
            "SELECT * FROM memory_followups WHERE state IN ('pending','held') AND due_at<=? "
            "ORDER BY due_at, id",
            (due_at,),
        ).fetchall()
        pairs = []
        for row in rows:
            memory = self._memory_row(conn, row["memory_id"])
            if self._usable(memory, now):
                pairs.append((row, memory))
        return pairs

    def _stored_citations(self, conn, checkin, now: str):
        rows = conn.execute(
            "SELECT * FROM memory_followups WHERE bundle_id=? ORDER BY due_at, id",
            (checkin["id"],),
        ).fetchall()
        citations = []
        left_out = 0
        for row in rows:
            memory = self._memory_row(conn, row["memory_id"])
            if row["state"] == "raised" and self._usable(memory, now) and _flat(memory["body"]):
                citations.append(
                    {
                        "followup_id": row["id"],
                        "memory_id": row["memory_id"],
                        "body": memory["body"],
                    }
                )
            else:
                left_out += 1
        return citations, left_out

    def _morning_view(self, conn, row) -> dict:
        now = iso(self.store.clock())
        if row["state"] in {"pending", "held"}:
            citations = [
                {
                    "followup_id": item["id"],
                    "memory_id": item["memory_id"],
                    "body": memory["body"],
                }
                for item, memory in self._preview_pairs(conn, row["due_at"], now)
            ]
            left_out = 0
        else:
            citations, left_out = self._stored_citations(conn, row, now)
            if row["state"] != "raised":
                left_out = 0
        copy = morning_reason(
            row["state"],
            due_local=row["due_local"],
            timezone=row["timezone"],
            hold_reason=row["hold_reason"],
            quiet_delayed=bool(row["quiet_delayed"]),
            left_out=left_out if row["state"] == "raised" else 0,
        )
        return {
            "id": row["id"],
            "state": row["state"],
            "version": row["version"],
            "due_at": row["due_at"],
            "due_local": row["due_local"],
            "timezone": row["timezone"],
            "hold_reason": row["hold_reason"],
            "hold_until": row["hold_until"],
            "raised_at": row["raised_at"],
            "notice_id": row["notice_id"],
            "citations": citations,
            "left_out": left_out if row["state"] == "raised" else 0,
            "armed": row["state"] in CHECKIN_OPEN,
            **copy,
        }

    def _latest_checkin(self, conn):
        open_row = self._open_checkin(conn)
        if open_row:
            return open_row
        return conn.execute(
            "SELECT * FROM memory_morning_checkins ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()

    def morning_listing(self) -> dict:
        with self.store.connection() as conn:
            row = self._latest_checkin(conn)
            return {"checkin": self._morning_view(conn, row) if row else None}

    def morning_draft(self, payload: MorningTime) -> dict:
        with self.store.connection() as conn:
            self._reject_open_checkin(conn)
            due, zone = self._resolve_time(conn, payload.due_local, payload.timezone)
            citations = [
                {
                    "followup_id": item["id"],
                    "memory_id": item["memory_id"],
                    "body": memory["body"],
                }
                for item, memory in self._preview_pairs(conn, iso(due), iso(self.store.clock()))
            ]
            return {
                "draft": {
                    "due_at": iso(due),
                    "due_local": _stamp(payload.due_local),
                    "timezone": zone,
                    "citations": citations,
                    "ready": len(citations) >= MIN_CITATIONS,
                    "armed": False,
                },
                "saved": False,
                "armed": False,
            }

    def morning_approve(self, payload: MorningTime, key: str) -> dict:
        due_local = _stamp(payload.due_local)

        def apply(conn):
            self._reject_open_checkin(conn)
            due, zone = self._resolve_time(conn, payload.due_local, payload.timezone)
            pairs = self._preview_pairs(conn, iso(due), iso(self.store.clock()))
            if len(pairs) < MIN_CITATIONS:
                raise DomainError("MORNING_CHECKIN_NEEDS_SEVERAL", 422)
            now = iso(self.store.clock())
            checkin_id = uuid4().hex
            try:
                conn.execute(
                    "INSERT INTO memory_morning_checkins("
                    "id, due_at, timezone, due_local, state, version, hold_reason, hold_until, "
                    "quiet_delayed, raise_generation, notice_id, raised_at, created_at, updated_at"
                    ") VALUES(?,?,?,?,'pending',1,NULL,NULL,0,0,NULL,NULL,?,?)",
                    (checkin_id, iso(due), zone, due_local, now, now),
                )
            except sqlite3.IntegrityError:
                raise DomainError("MORNING_CHECKIN_OPEN", 409) from None
            self.store.record(conn, "memory_morning_approved", details={"id": checkin_id})
            return {"checkin": self._morning_view(conn, self._checkin(conn, checkin_id)), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_morning_approve",
                "due_local": due_local,
                "timezone": payload.timezone,
            },
            apply,
        )

    def morning_revise(self, checkin_id: str, payload: MorningRevision, key: str) -> dict:
        provided = set(payload.model_fields_set)
        if "due_local" in provided and payload.due_local is None:
            raise DomainError("FOLLOWUP_TIME_REQUIRED", 422)
        if "timezone" in provided and payload.timezone is None:
            raise DomainError("FOLLOWUP_TIME_REQUIRED", 422)
        due_text = _stamp(payload.due_local) if "due_local" in provided else None

        def apply(conn):
            row = self._checkin(conn, checkin_id)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["state"] not in {"pending", "held"}:
                raise DomainError("MORNING_CHECKIN_CLOSED", 409)
            if "due_local" not in provided and "timezone" not in provided:
                return {"checkin": self._morning_view(conn, row), "saved": True}
            due_local = (
                payload.due_local
                if "due_local" in provided
                else datetime.fromisoformat(row["due_local"])
            )
            timezone = payload.timezone if "timezone" in provided else row["timezone"]
            due, zone = self._resolve_time(conn, due_local, timezone)
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE memory_morning_checkins SET due_at=?, timezone=?, due_local=?, "
                "state='pending', hold_reason=NULL, hold_until=NULL, quiet_delayed=0, "
                "version=version+1, updated_at=? WHERE id=?",
                (iso(due), zone, _stamp(due_local), now, checkin_id),
            )
            self.store.record(conn, "memory_morning_revised", details={"id": checkin_id})
            keep = {
                item["id"]
                for item, _memory in self._preview_pairs(conn, iso(due), now)
            }
            self._release_morning(conn, now, keep)
            updated = self._checkin(conn, checkin_id)
            return {"checkin": self._morning_view(conn, updated), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_morning_revise",
                "id": checkin_id,
                "expected_version": payload.expected_version,
                "fields": sorted(provided),
                "due_local": due_text,
                "timezone": payload.timezone if "timezone" in provided else None,
            },
            apply,
        )

    def morning_dismiss(self, checkin_id: str, payload: MorningDismiss, key: str) -> dict:
        def apply(conn):
            row = self._checkin(conn, checkin_id)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["state"] == "dismissed":
                return {"checkin": self._morning_view(conn, row), "saved": True}
            if row["state"] not in CHECKIN_OPEN:
                raise DomainError("MORNING_CHECKIN_CLOSED", 409)
            now = iso(self.store.clock())
            conn.execute(
                "UPDATE memory_morning_checkins SET state='dismissed', hold_reason=NULL, "
                "hold_until=NULL, version=version+1, updated_at=? WHERE id=?",
                (now, checkin_id),
            )
            self.store.record(conn, "memory_morning_dismissed", details={"id": checkin_id})
            self._release_morning(conn, now, None)
            updated = self._checkin(conn, checkin_id)
            return {"checkin": self._morning_view(conn, updated), "saved": True}

        return self.store.operation(
            key,
            {
                "type": "memory_morning_dismiss",
                "id": checkin_id,
                "expected_version": payload.expected_version,
            },
            apply,
        )

    def _release_morning(self, conn, now: str, keep: set[str] | None) -> bool:
        rows = conn.execute(
            "SELECT id FROM memory_followups WHERE state='held' AND hold_reason='morning'"
        ).fetchall()
        wrote = False
        for row in rows:
            if keep is not None and row["id"] in keep:
                continue
            conn.execute(
                "UPDATE memory_followups SET state='pending', hold_reason=NULL, hold_until=NULL, "
                "not_before=NULL, version=version+1, updated_at=? WHERE id=?",
                (now, row["id"]),
            )
            wrote = True
        return wrote

    def _hold_for_morning(self, conn, row, now: str, until: str) -> bool:
        if (
            row["state"] == "held"
            and row["hold_reason"] == "morning"
            and row["hold_until"] == until
            and not row["bundle_id"]
        ):
            return False
        conn.execute(
            "UPDATE memory_followups SET state='held', hold_reason='morning', hold_until=?, "
            "not_before=NULL, bundle_id=NULL, version=version+1, updated_at=? WHERE id=?",
            (until, now, row["id"]),
        )
        self.store.record(
            conn, "memory_followup_held", details={"id": row["id"], "reason": "morning"}
        )
        return True

    def _hold_checkin(self, conn, row, now, prefs, now_local, quiet: bool) -> bool:
        if quiet:
            until = quiet_until(prefs, now_local)
            until_iso = iso(until) if until else None
            reason = "quiet"
            delayed = 1
        else:
            until_iso = None
            reason = "proactivity"
            delayed = row["quiet_delayed"]
        if (
            row["state"] == "held"
            and row["hold_reason"] == reason
            and row["hold_until"] == until_iso
            and row["quiet_delayed"] == delayed
        ):
            return False
        conn.execute(
            "UPDATE memory_morning_checkins SET state='held', hold_reason=?, hold_until=?, "
            "quiet_delayed=?, version=version+1, updated_at=? WHERE id=?",
            (reason, until_iso, delayed, now, row["id"]),
        )
        self.store.record(
            conn, "memory_morning_held", details={"id": row["id"], "reason": reason}
        )
        return True

    def _morning_notice(self, conn, checkin) -> Notice | None:
        if not checkin["notice_id"]:
            return None
        citations, _left = self._stored_citations(conn, checkin, iso(self.store.clock()))
        bodies = [_flat(item["body"]) for item in citations]
        bodies = [body for body in bodies if body]
        if not bodies:
            return None
        view = self._morning_view(conn, checkin)
        return Notice(
            checkin["notice_id"],
            "memory_morning",
            "Morning check-in",
            "早晨核对",
            _cite_line(bodies, "en"),
            _cite_line(bodies, "zh"),
            view["reason_en"],
            view["reason_zh"],
        )

    def _cite(self, conn, checkin, pairs, now: str) -> Notice | None:
        if not pairs:
            conn.execute(
                "UPDATE memory_morning_checkins SET state='raised', notice_id=NULL, "
                "raised_at=?, hold_reason=NULL, hold_until=NULL, version=version+1, "
                "updated_at=? WHERE id=?",
                (now, now, checkin["id"]),
            )
            self.store.record(
                conn, "memory_morning_raised", details={"id": checkin["id"], "cited": 0}
            )
            return None
        generation = checkin["raise_generation"] + 1
        notice_id = f"memory-morning-{checkin['id']}-{generation}"
        conn.execute(
            "UPDATE memory_morning_checkins SET state='raised', raise_generation=?, "
            "notice_id=?, raised_at=?, hold_reason=NULL, hold_until=NULL, "
            "version=version+1, updated_at=? WHERE id=?",
            (generation, notice_id, now, now, checkin["id"]),
        )
        for row, _memory in pairs:
            conn.execute(
                "UPDATE memory_followups SET state='raised', bundle_id=?, notice_id=NULL, "
                "raised_at=?, hold_reason=NULL, hold_until=NULL, not_before=NULL, "
                "version=version+1, updated_at=? WHERE id=?",
                (checkin["id"], now, now, row["id"]),
            )
            self.store.record(
                conn,
                "memory_morning_cited",
                details={"id": checkin["id"], "followup_id": row["id"]},
            )
        self.store.record(
            conn,
            "memory_morning_raised",
            details={"id": checkin["id"], "cited": len(pairs)},
        )
        return self._morning_notice(conn, self._checkin(conn, checkin["id"]))

    def _advance_checkin(self, conn, checkin, now, now_dt, prefs, now_local, quiet, proactive):
        pairs = self._preview_pairs(conn, checkin["due_at"], now)
        covered = {row["id"] for row, _memory in pairs}
        wrote = self._release_morning(conn, now, covered)
        if _parse(checkin["due_at"]) > now_dt:
            for row, _memory in pairs:
                current = self._followup(conn, row["id"])
                wrote = self._hold_for_morning(conn, current, now, checkin["due_at"]) or wrote
            return wrote, covered, []
        if quiet or not proactive:
            wrote = self._hold_checkin(conn, checkin, now, prefs, now_local, quiet) or wrote
            for row, _memory in pairs:
                current = self._followup(conn, row["id"])
                wrote = self._hold_for_morning(conn, current, now, checkin["due_at"]) or wrote
            return wrote, covered, []
        notice = self._cite(conn, checkin, pairs, now)
        wrote = self._release_morning(conn, now, set()) or True
        return wrote, covered, [notice] if notice is not None else []

    def _undelivered_morning(self, conn, skip: set[str]) -> Notice | None:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notice_deliveries'"
        ).fetchone():
            return None
        row = conn.execute(
            "SELECT * FROM memory_morning_checkins WHERE state='raised' AND notice_id IS NOT NULL"
        ).fetchone()
        if not row or row["notice_id"] in skip:
            return None
        seen = conn.execute(
            "SELECT 1 FROM notice_deliveries WHERE notice_id=? AND channel='in_app'",
            (row["notice_id"],),
        ).fetchone()
        if seen:
            return None
        return self._morning_notice(conn, row)

    def tick(self) -> None:
        prefs = self.runtime.data.preferences()
        now_dt = self.store.clock()
        now = iso(now_dt)
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        now_local = now_dt.astimezone(zone)
        quiet = is_quiet(prefs, now_local)
        proactive = prefs.get("proactivity") != "off"
        pending: list[Notice] = []
        with self.store.connection(write=True) as conn:
            wrote = self._cancel_inactive(conn, now)
            checkin = self._open_checkin(conn)
            covered: set[str] = set()
            if checkin and checkin["state"] in {"pending", "held"}:
                advanced, covered, morning = self._advance_checkin(
                    conn, checkin, now, now_dt, prefs, now_local, quiet, proactive
                )
                wrote = advanced or wrote
                pending.extend(morning)
            else:
                wrote = self._release_morning(conn, now, None) or wrote
            raised = 0
            for row in self._due(conn, now):
                if row["id"] in covered or row["hold_reason"] == "morning" or row["bundle_id"]:
                    continue
                if quiet or not proactive:
                    wrote = self._hold(conn, row, now, prefs, now_local, quiet) or wrote
                    continue
                if raised >= MAX_RAISES:
                    wrote = self._defer(conn, row, now_dt) or wrote
                    continue
                notice = self._raise(conn, row, now)
                wrote = True
                if notice is not None:
                    pending.append(notice)
                    raised += 1
            pending.extend(self._undelivered(conn, {notice.id for notice in pending}))
            retry = self._undelivered_morning(conn, {notice.id for notice in pending})
            if retry is not None:
                pending.append(retry)
            if wrote:
                self.store.bump(conn)
        # A raised row can be waiting out a crash. Quiet hours and proactivity off
        # still keep every channel silent; the memory page can show the card.
        if proactive and not quiet:
            notifier = getattr(self.runtime, "notify", None)
            if notifier:
                for notice in pending:
                    notifier.publish(notice, quiet=False)


def memory_followup_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/memory-followups", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.memory_followups.listing()

    @router.get("/morning")
    def morning_listing():
        return runtime.memory_followups.morning_listing()

    @router.post("/morning/drafts")
    def morning_draft(payload: MorningTime):
        return runtime.memory_followups.morning_draft(payload)

    @router.post("/morning")
    def morning_approve(payload: MorningTime, key=Depends(operation_id)):
        return runtime.memory_followups.morning_approve(payload, key)

    @router.post("/morning/{checkin_id}/revisions")
    def morning_revise(checkin_id: str, payload: MorningRevision, key=Depends(operation_id)):
        return runtime.memory_followups.morning_revise(checkin_id, payload, key)

    @router.post("/morning/{checkin_id}/dismissals")
    def morning_dismiss(checkin_id: str, payload: MorningDismiss, key=Depends(operation_id)):
        return runtime.memory_followups.morning_dismiss(checkin_id, payload, key)

    @router.post("/drafts")
    def draft(payload: FollowUpTime):
        return runtime.memory_followups.draft(payload)

    @router.post("")
    def approve(payload: FollowUpApprove, key=Depends(operation_id)):
        return runtime.memory_followups.approve(payload, key)

    @router.post("/{followup_id}/revisions")
    def revise(followup_id: str, payload: FollowUpRevision, key=Depends(operation_id)):
        return runtime.memory_followups.revise(followup_id, payload, key)

    @router.post("/{followup_id}/resolutions")
    def resolve(followup_id: str, payload: FollowUpResolution, key=Depends(operation_id)):
        return runtime.memory_followups.resolve(followup_id, payload, key)

    return router
