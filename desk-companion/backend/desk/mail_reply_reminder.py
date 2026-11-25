"""One reminder after a followed thread receives a reply.

The existing follow-up poll remains the source check. This module does not call
a model, send mail, or start another scheduler. A local sample is a fixture the
owner can complete on this desk; it is not a live mailbox.
"""

import hashlib
import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode
from .tasks import TaskAction, TaskInput


SAMPLE_VERSION = "local-sample-1"
SAMPLE_ACCOUNT = "Local mail sample"
LOCAL_LABEL = "Local mail sample. Not a live mailbox."
CONNECTED_LABEL = "Connected mailbox"

THREADS = {
    "sample-venue": {
        "subject": "Venue for Friday",
        "sender": "Alex",
        "sender_address": "alex@example.com",
        "original_id": "sample-venue-1",
        "original_body": "Can you confirm the venue for Friday?",
        "original_at": "2026-11-25T02:00:00Z",
        "reply_id": "sample-venue-2",
        "reply_body": "Friday after 3 still works for me.",
        "reply_at": "2026-11-25T03:00:00Z",
    },
    "sample-invoice": {
        "subject": "Invoice copy",
        "sender": "Sam",
        "sender_address": "sam@example.com",
        "original_id": "sample-invoice-1",
        "original_body": "The invoice copy is in this sample only.",
        "original_at": "2026-11-25T02:10:00Z",
        "reply_id": "sample-invoice-2",
        "reply_body": "Here is the copy you asked to review.",
        "reply_at": "2026-11-25T03:10:00Z",
    },
}


class SampleFollow(StrictModel):
    thread_id: Literal["sample-venue", "sample-invoice"]


class ReplyRead(StrictModel):
    message_id: str = Field(min_length=1, max_length=512)


class ReplyDraftRequest(StrictModel):
    message_id: str = Field(min_length=1, max_length=512)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    observation_revision: int = Field(ge=0, strict=True)
    summary: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=2000)


def _header(thread_id, spec, *, reply, released):
    if reply and not released:
        return None
    return {
        "id": spec["reply_id"] if reply else spec["original_id"],
        "thread_id": thread_id,
        "subject": spec["subject"],
        "sender": spec["sender"],
        "sender_address": spec["sender_address"],
        "at": spec["reply_at"] if reply else spec["original_at"],
        "outgoing": False,
    }


def _fingerprint(followup_id, revision, message_ids):
    return hashlib.sha256(encode([followup_id, revision, list(message_ids)]).encode()).hexdigest()


def _summary(unread_ids, headers):
    if not unread_ids:
        return "No unreviewed reply"
    last = headers.get(unread_ids[-1])
    text = (
        f"{last['sender']} replied: {last['subject']}"
        if last
        else f"{len(unread_ids)} new replies"
    )
    if len(unread_ids) > 1:
        text = f"{len(unread_ids)} new replies. Latest: {text}"
    return text[:180]


class MailReplyReminders:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS local_mail_sample(
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    state TEXT NOT NULL,
                    released INTEGER NOT NULL,
                    fail INTEGER NOT NULL);
                INSERT OR IGNORE INTO local_mail_sample VALUES(1,'ready',0,0);
                CREATE TABLE IF NOT EXISTS mail_reply_reads(
                    followup_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    read_at TEXT NOT NULL,
                    PRIMARY KEY(followup_id, message_id));
            """)
        self.reload()

    def reload(self):
        row = self._sample()
        self.sample = {
            "state": row["state"],
            "released": bool(row["released"]),
            "fail": bool(row["fail"]),
        }

    def _principal(self, principal):
        try:
            self.runtime.personal_context.require_visible(principal)
        except DomainError as error:
            if error.code == "PRIVATE_CONTEXT_HIDDEN":
                self.conceal()
            raise

    def _sample(self, conn=None):
        if conn is None:
            with self.store.connection() as active:
                return self._sample(active)
        return conn.execute("SELECT * FROM local_mail_sample WHERE id=1").fetchone()

    def require_local(self, definition):
        if (
            definition.get("provider") != "local"
            or definition.get("account_version") != SAMPLE_VERSION
            or definition.get("account_email") != SAMPLE_ACCOUNT
        ):
            raise DomainError("APP_CONNECTION_CHANGED", 409)
        if self.sample["state"] != "ready":
            raise DomainError("APP_NOT_CONNECTED", 409)

    def _messages(self, thread_id, released):
        spec = THREADS.get(thread_id)
        if spec is None:
            raise DomainError("MAIL_THREAD_INVALID", 422)
        rows = []
        for reply in (False, True):
            header = _header(thread_id, spec, reply=reply, released=released)
            if header:
                rows.append(header)
        return rows

    def local_thread(self, definition, checkpoint):
        checkpoint()
        self.require_local(definition)
        checkpoint()
        if self.sample["fail"]:
            raise DomainError("APP_CONNECTION_FAILED", 502)
        checkpoint()
        return self._messages(definition["thread_id"], self.sample["released"])

    def _body(self, thread_id, message_id, released):
        spec = THREADS[thread_id]
        if message_id == spec["original_id"]:
            return spec["original_body"]
        if message_id == spec["reply_id"] and released:
            return spec["reply_body"]
        raise DomainError("APP_ITEM_UNAVAILABLE", 404)

    def catalog(self, principal):
        self._principal(principal)
        sample = self._sample()
        with self.store.connection() as conn:
            followed = {
                json.loads(row["definition"])["thread_id"]
                for row in conn.execute(
                    "SELECT definition FROM mail_followups WHERE state='active' AND json_extract(definition,'$.provider')='local'"
                )
            }
        return {
            "live_mailbox": False,
            "label": LOCAL_LABEL,
            "released": bool(sample["released"]),
            "threads": [
                {
                    "id": thread_id,
                    "subject": spec["subject"],
                    "sender": spec["sender"],
                    "followed": thread_id in followed,
                }
                for thread_id, spec in THREADS.items()
            ],
        }

    def _sync(self):
        for _ in range(4):
            self.runtime.mail_followups.poll_source_once()

    def follow(self, thread_id, key, principal):
        self._principal(principal)
        if thread_id not in THREADS:
            raise DomainError("MAIL_THREAD_INVALID", 422)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            sample = self._sample(conn)
            if sample["state"] != "ready":
                raise DomainError("APP_NOT_CONNECTED", 409)
            spec = THREADS[thread_id]
            visible = self._messages(thread_id, bool(sample["released"]))
            definition = {
                "provider": "local",
                "account_version": SAMPLE_VERSION,
                "account_email": SAMPLE_ACCOUNT,
                "automatic": True,
                "thread_id": thread_id,
                "selected": visible[0],
                "baseline_ids": [m["id"] for m in visible],
                "task_title": spec["subject"][:160],
                "observed_at": iso(self.store.clock()),
                "source_label": LOCAL_LABEL,
                "live_mailbox": False,
                "request": {"message_id": spec["original_id"], "task_id": None},
            }
            scope = hashlib.sha256(
                encode([definition[k] for k in ("provider", "account_version", "thread_id")]).encode()
            ).hexdigest()
            old = conn.execute(
                "SELECT id, task_id FROM mail_followups WHERE scope_hash=? AND state IN ('active','blocked')",
                (scope,),
            ).fetchone()
            if old:
                return {
                    "followup_id": old["id"],
                    "task_id": old["task_id"],
                    "already_following": True,
                    "live_mailbox": False,
                }
            task = self.runtime.tasks.insert_task(
                conn,
                TaskInput(
                    title=spec["subject"][:160],
                    status="waiting",
                    waiting_for="A reply in the selected email thread",
                    next_step="Review the next email update",
                    follow_up_enabled=False,
                ),
                origin="mail_followup",
            )
            now, ident = self.store.clock(), uuid4().hex
            conn.execute(
                """INSERT INTO mail_followups(
                    id,task_id,scope_hash,definition,state,version,created_at,expires_at,
                    next_check_at,snapshot,seen,unread_ids
                ) VALUES(?,?,?,?,'active',1,?,?,?,?,?,?)""",
                (
                    ident,
                    task["id"],
                    scope,
                    encode(definition),
                    iso(now),
                    iso(now + timedelta(days=7)),
                    iso(now),
                    encode(visible),
                    encode([m["id"] for m in visible]),
                    "[]",
                ),
            )
            self.store.record(
                conn, "mail_followup_started", details={"followup_id": ident, "task_id": task["id"]}
            )
            return {
                "followup_id": ident,
                "task_id": task["id"],
                "already_following": False,
                "live_mailbox": False,
            }

        result = self.store.operation(
            key, {"type": "local_mail_follow", "thread_id": thread_id}, apply
        )
        self.reload()
        self._sync()
        return result

    def simulate(self, key, principal):
        self._principal(principal)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            if self._sample(conn)["state"] != "ready":
                raise DomainError("APP_NOT_CONNECTED", 409)
            conn.execute("UPDATE local_mail_sample SET released=1 WHERE id=1")
            return {"released": True, "live_mailbox": False}

        result = self.store.operation(key, {"type": "local_mail_reply"}, apply)
        self.reload()
        with self.store.connection(write=True) as conn:
            conn.execute(
                """UPDATE mail_followups SET next_check_at=?, poll_until=NULL
                   WHERE state='active' AND json_extract(definition,'$.provider')='local'""",
                (iso(self.store.clock()),),
            )
        self._sync()
        return result

    def _row(self, conn, followup_id):
        row = conn.execute("SELECT * FROM mail_followups WHERE id=?", (followup_id,)).fetchone()
        if not row:
            raise DomainError("MAIL_FOLLOWUP_NOT_FOUND", 404)
        return row

    def _binding(self, conn, row):
        definition = json_definition(row)
        unread_ids = json.loads(row["unread_ids"] or "[]")
        headers = {m["id"]: m for m in json.loads(row["snapshot"] or "[]")}
        local = definition["provider"] == "local"
        return {
            "followup_id": row["id"],
            "task_id": row["task_id"],
            "thread_id": definition["thread_id"],
            "provider": definition["provider"],
            "definition": definition,
            "unread_ids": unread_ids,
            "seen": json.loads(row["seen"] or "[]"),
            "observation_revision": row["observation_revision"],
            "fingerprint": _fingerprint(row["id"], row["observation_revision"], unread_ids),
            "summary": _summary(unread_ids, headers),
            "notice_id": row["notice_id"],
            "notice_pending": row["notice_pending"],
            "unread_count": row["unread_count"],
            "state": row["state"],
            "live_mailbox": False,
            "source_label": LOCAL_LABEL if local else CONNECTED_LABEL,
            "headers": headers,
        }

    def _drafts(self, conn, now):
        pending, saved = {}, set()
        rows = conn.execute(
            "SELECT id, state, data, expires_at FROM assistant_proposals WHERE kind='followed_reply_draft'"
        )
        for proposal in rows:
            data = json.loads(proposal["data"] or "{}")
            key = (data.get("followup_id"), data.get("message_id"))
            if proposal["state"] == "pending" and proposal["expires_at"] > now:
                pending[key] = {
                    "id": proposal["id"],
                    "body": data.get("body", ""),
                    "summary": data.get("summary", ""),
                    "fingerprint": data.get("fingerprint", ""),
                    "expires_at": proposal["expires_at"],
                    "send": False,
                }
            elif proposal["state"] == "confirmed":
                saved.add(key)
        return pending, saved

    def reminders(self, principal, task_id=None):
        self._principal(principal)
        now = iso(self.store.clock())
        with self.store.connection() as conn:
            pending, saved = self._drafts(conn, now)
            rows = conn.execute(
                """SELECT * FROM mail_followups
                   WHERE state='active' AND unread_count>0 AND notice_pending=0
                     AND notice_id IS NOT NULL
                   ORDER BY created_at LIMIT 20"""
            ).fetchall()
            items = []
            for row in rows:
                if task_id and row["task_id"] != task_id:
                    continue
                binding = self._binding(conn, row)
                task = self.runtime.tasks.get(conn, row["task_id"])
                draft_key = (row["id"], binding["unread_ids"][-1] if binding["unread_ids"] else None)
                draft = pending.get(draft_key)
                items.append(
                    {
                        "id": row["id"],
                        "task_id": row["task_id"],
                        "task_title": task["title"],
                        "fingerprint": binding["fingerprint"],
                        "observation_revision": binding["observation_revision"],
                        "summary": binding["summary"],
                        "message_ids": binding["unread_ids"],
                        "source_label": binding["source_label"],
                        "live_mailbox": False,
                        "count": len(binding["unread_ids"]),
                        "draft_state": "pending" if draft else ("saved" if draft_key in saved else "none"),
                        "draft": draft,
                    }
                )
        return {"reminders": items, "live_mailbox": False}

    def _original(self, binding, message_id):
        definition = binding["definition"]
        if message_id not in binding["seen"]:
            raise DomainError("MAIL_REPLY_UNRELATED", 409)
        if definition["provider"] == "local":
            if self.sample["fail"]:
                raise DomainError("APP_CONNECTION_FAILED", 502)
            header = next(
                (
                    m
                    for m in self._messages(definition["thread_id"], self.sample["released"])
                    if m["id"] == message_id
                ),
                None,
            )
            if header is None:
                raise DomainError("APP_ITEM_UNAVAILABLE", 404)
            return {
                **header,
                "body": self._body(definition["thread_id"], message_id, self.sample["released"]),
                "body_status": "local_sample",
                "source_label": LOCAL_LABEL,
            }
        privacy = self.runtime.personal_context.revision()

        def current():
            if self.runtime.personal_context.revision() != privacy:
                raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
            self.runtime.mail_followups._account(definition)

        message = self.runtime.mail_followups.reader.original_text(
            definition["provider"], message_id, definition["account_email"], current
        )
        if message.get("thread_id") != definition["thread_id"]:
            raise DomainError("MAIL_REPLY_UNRELATED", 409)
        return {**message, "source_label": CONNECTED_LABEL}

    def read(self, followup_id, message_id, key, principal):
        self._principal(principal)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            binding = self._binding(conn, self._row(conn, followup_id))
            if message_id not in binding["seen"] or binding["state"] != "active":
                raise DomainError("MAIL_REPLY_UNRELATED", 409)
            digest = hashlib.sha256(encode([followup_id, message_id]).encode()).hexdigest()
            conn.execute(
                """INSERT OR IGNORE INTO mail_reply_reads(followup_id,message_id,fingerprint,read_at)
                   VALUES(?,?,?,?)""",
                (followup_id, message_id, digest, iso(self.store.clock())),
            )
            return {
                "opened": True,
                "stored_body": False,
                "followup_id": followup_id,
                "message_id": message_id,
                "sent": False,
            }

        receipt = self.store.operation(
            key, {"type": "mail_reply_read", "followup_id": followup_id, "message_id": message_id}, apply
        )
        with self.store.connection() as conn:
            binding = self._binding(conn, self._row(conn, followup_id))
        try:
            message = self._original(binding, message_id)
        except DomainError as error:
            return {
                **receipt,
                "read_state": "failed",
                "confirmed_reply": False,
                "error": error.code,
                "sent": False,
            }
        shown = {
            k: message[k]
            for k in ("id", "subject", "sender", "at", "body", "body_status", "source_label")
        }
        return {**receipt, "read_state": "read", "confirmed_reply": False, "sent": False, "message": shown}

    def _send_state(self, message_ids):
        if not message_ids:
            return "none"
        marks = ",".join("?" for _ in message_ids)
        with self.store.connection() as conn:
            row = conn.execute(
                f"""SELECT a.state FROM outgoing_mail_attempts a
                    JOIN assistant_proposals p ON p.id=a.proposal_id
                    WHERE json_extract(p.data,'$.reply.message_id') IN ({marks})
                    ORDER BY a.updated_at DESC LIMIT 1""",
                tuple(message_ids),
            ).fetchone()
        if not row:
            return "none"
        if row["state"] in {"sending", "unknown"}:
            return "unknown"
        if row["state"] == "failed":
            return "failed"
        return row["state"]

    def reread(self, followup_id, key, principal):
        self._principal(principal)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            self._row(conn, followup_id)
            return {"checked": True, "followup_id": followup_id, "sent": False}

        receipt = self.store.operation(key, {"type": "mail_reply_reread", "followup_id": followup_id}, apply)
        with self.store.connection() as conn:
            binding = self._binding(conn, self._row(conn, followup_id))
        send_state = self._send_state(binding["unread_ids"])
        try:
            if binding["provider"] == "local":
                messages = self.local_thread(binding["definition"], lambda: self._principal(principal))
            else:
                messages = self.runtime.mail_followups.reader.thread(
                    binding["provider"],
                    binding["thread_id"],
                    binding["definition"]["account_email"],
                    lambda: self.runtime.mail_followups._account(binding["definition"]),
                )
        except DomainError as error:
            return {
                **receipt,
                "state": "failed",
                "confirmed_reply": False,
                "reply_present": False,
                "sent": False,
                "send_state": send_state,
                "error": error.code,
            }
        found = [m["id"] for m in messages if m["id"] in binding["unread_ids"]]
        present = bool(binding["unread_ids"]) and set(found) == set(binding["unread_ids"])
        state = "unknown" if send_state == "unknown" else ("present" if present else "unavailable" if binding["unread_ids"] else "none")
        return {
            **receipt,
            "state": state,
            "confirmed_reply": False,
            "reply_present": present,
            "sent": False,
            "send_state": send_state,
        }

    def draft(self, followup_id, payload, key, principal):
        self._principal(principal)
        body_hash = hashlib.sha256(payload.body.encode()).hexdigest()

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            binding = self._binding(conn, self._row(conn, followup_id))
            if (
                binding["state"] != "active"
                or payload.message_id not in binding["unread_ids"]
                or payload.fingerprint != binding["fingerprint"]
                or payload.summary != binding["summary"]
                or payload.observation_revision != binding["observation_revision"]
            ):
                raise DomainError("MAIL_REPLY_CHANGED", 409)
            if self._send_state([payload.message_id]) == "unknown":
                raise DomainError("EMAIL_SEND_UNKNOWN", 409)
            data = {
                "send": False,
                "followup_id": followup_id,
                "task_id": binding["task_id"],
                "message_id": payload.message_id,
                "thread_id": binding["thread_id"],
                "fingerprint": binding["fingerprint"],
                "observation_revision": binding["observation_revision"],
                "summary": binding["summary"],
                "body": payload.body,
                "provider": binding["provider"],
                "live_mailbox": False,
                "source_label": binding["source_label"],
            }
            now = iso(self.store.clock())
            for old in conn.execute(
                "SELECT id, data FROM assistant_proposals WHERE kind='followed_reply_draft' AND state='pending' AND expires_at>?",
                (now,),
            ):
                old_data = json.loads(old["data"])
                if old_data.get("followup_id") == followup_id and old_data.get("message_id") == payload.message_id:
                    conn.execute("UPDATE assistant_proposals SET state='cancelled' WHERE id=?", (old["id"],))
            active = conn.execute(
                "SELECT COUNT(*) FROM assistant_proposals WHERE state='pending' AND expires_at>?",
                (now,),
            ).fetchone()[0]
            if active >= 20:
                raise DomainError("TOO_MANY_DRAFTS", 422)
            proposal_id = uuid4().hex
            expires = iso(self.store.clock() + timedelta(minutes=30))
            conn.execute(
                "INSERT INTO assistant_proposals VALUES(?,?,?,'pending',?,?,NULL)",
                (proposal_id, "followed_reply_draft", encode(data), expires, now),
            )
            self.store.record(
                conn, "assistant_draft", details={"proposal_id": proposal_id, "kind": "followed_reply_draft"}
            )
            row = conn.execute("SELECT * FROM assistant_proposals WHERE id=?", (proposal_id,)).fetchone()
            return {
                "proposal": {
                    "id": row["id"],
                    "kind": row["kind"],
                    "state": row["state"],
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                    "data": json.loads(row["data"]),
                },
                "saved": False,
                "sent": False,
            }

        return self.store.operation(
            key,
            {
                "type": "followed_reply_prepare",
                "followup_id": followup_id,
                "message_id": payload.message_id,
                "fingerprint": payload.fingerprint,
                "body_sha256": body_hash,
            },
            apply,
        )

    def confirm_draft(self, payload, key, principal):
        if payload.get("send") is not False:
            raise DomainError("MAIL_REPLY_SEND_FORBIDDEN", 409)
        for field in ("followup_id", "task_id", "message_id", "fingerprint", "summary", "body"):
            if not isinstance(payload.get(field), str) or not payload[field]:
                raise DomainError("MAIL_REPLY_DRAFT_INVALID", 422)
        if type(payload.get("observation_revision")) is not int:
            raise DomainError("MAIL_REPLY_DRAFT_INVALID", 422)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            binding = self._binding(conn, self._row(conn, payload["followup_id"]))
            if (
                payload["fingerprint"] != binding["fingerprint"]
                or payload["summary"] != binding["summary"]
                or payload["observation_revision"] != binding["observation_revision"]
                or payload["message_id"] not in binding["unread_ids"]
                or payload["task_id"] != binding["task_id"]
            ):
                raise DomainError("MAIL_REPLY_CHANGED", 409)
            task = self.runtime.tasks.get(conn, payload["task_id"])
            note = f"Reply draft saved for message {payload['message_id']}. Nothing was sent."
            self.runtime.tasks.apply_action(
                conn,
                payload["task_id"],
                TaskAction(action="note", expected_version=task["version"], note=note),
                "assistant_confirmed",
            )
            return {
                "sent": False,
                "saved": True,
                "followup_id": payload["followup_id"],
                "task_id": payload["task_id"],
                "message_id": payload["message_id"],
            }

        return self.store.operation(
            key,
            {
                "type": "followed_reply_draft",
                "followup_id": payload["followup_id"],
                "message_id": payload["message_id"],
                "fingerprint": payload["fingerprint"],
            },
            apply,
        )

    def forget(self, followup_id, key, principal):
        self._principal(principal)

        def apply(conn):
            self.runtime.personal_context.require_owner_transaction(conn, principal)
            row = self._row(conn, followup_id)
            if row["notice_id"]:
                self.runtime.notify.dismiss_pending(conn, row["notice_id"])
            conn.execute(
                "UPDATE mail_followups SET unread_count=0,unread_ids='[]',notice_id=NULL,notice_pending=0 WHERE id=?",
                (followup_id,),
            )
            conn.execute("DELETE FROM mail_reply_reads WHERE followup_id=?", (followup_id,))
            self._redact(conn, followup_id)
            return {"forgotten": True, "followup_id": followup_id, "sent": False}

        return self.store.operation(key, {"type": "mail_reply_forget", "followup_id": followup_id}, apply)

    def conceal(self):
        with self.store.connection(write=True) as conn:
            self._redact(conn, None)
            conn.execute("DELETE FROM mail_reply_reads")
        self.reload()

    def _redact(self, conn, followup_id):
        for proposal in conn.execute("SELECT id, state, data, result FROM assistant_proposals WHERE kind='followed_reply_draft'"):
            data = json.loads(proposal["data"] or "{}")
            if followup_id and data.get("followup_id") != followup_id:
                continue
            data["body"] = ""
            state = "cancelled" if proposal["state"] == "pending" else proposal["state"]
            conn.execute(
                "UPDATE assistant_proposals SET state=?, data=? WHERE id=?",
                (state, encode(data), proposal["id"]),
            )
        for operation in conn.execute("SELECT id, request, response FROM operations"):
            request, response = json.loads(operation["request"]), json.loads(operation["response"])
            if not _mentions_followup(request, response, followup_id):
                continue
            _blank_body(request)
            _blank_body(response)
            conn.execute(
                "UPDATE operations SET request=?, response=? WHERE id=?",
                (encode(request), encode(response), operation["id"]),
            )


def json_definition(row):
    return json.loads(row["definition"])


def _mentions_followup(request, response, followup_id):
    blob = encode([request, response])
    kind = "followed_reply" in blob or "mail_reply_" in blob
    if not kind:
        return False
    if followup_id:
        return followup_id in blob
    return True


def _blank_body(value):
    if isinstance(value, dict):
        if "body" in value and isinstance(value["body"], str):
            value["body"] = ""
        for item in value.values():
            _blank_body(item)
    elif isinstance(value, list):
        for item in value:
            _blank_body(item)
