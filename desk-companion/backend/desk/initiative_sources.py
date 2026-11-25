"""Small current-evidence projection; provider readers/OAuth remain authoritative."""

import hashlib
import json
import re
from datetime import timedelta
from typing import NamedTuple
from urllib.parse import quote, urlencode

from .app_connection_models import ConnectedAppQuery
from .calendar import iso
from .connected_app_data import query_connected_app
from .initiative_mail_history import INBOX, GmailFindingHistory
from .store import DomainError, encode


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def compact(value, limit=1200):
    return " ".join(str(value or "").split())[:limit]


PRIVATE_CODE = re.compile(r"one[- ]time (?:code|password)|verification code|security code|password reset|reset your password|登录码|登录代码|验证码|驗證碼|一次性密[码碼]|重[置設]密[码碼]", re.I)


class SourceAccount(NamedTuple):
    connected: bool
    version: str | int
    email: str | None
    reconnect_required: bool = False
    connected_at: str | None = None


class InitiativeSources:
    def __init__(self, runtime):
        self.runtime = runtime
        self.mail = {}
        self.mail_check = None
        self.next_refresh = 0
        self.account_versions = None
        self.history = GmailFindingHistory()

    def stopped_threads(self):
        # Reuse existing follow-up decisions. A later explicit start supersedes
        # an older stop; reconnecting the same mailbox does not erase that stop.
        seen, stopped = set(), set()
        with self.runtime.store.connection() as conn:
            rows = conn.execute(
                "SELECT definition,state FROM mail_followups ORDER BY rowid DESC"
            ).fetchall()
        for row in rows:
            definition = json.loads(row["definition"])
            key = (
                definition["provider"],
                definition["account_email"].casefold(),
                definition["thread_id"],
            )
            if key not in seen:
                seen.add(key)
                if row["state"] == "stopped":
                    stopped.add(key)
        return stopped

    def fence(self):
        r = self.runtime
        prefs = r.data.preferences()
        with r.store.connection() as conn:
            if r.store.settings(conn)["hide_private"] or prefs["proactivity"] == "off":
                self.mail = {}
                self.mail_check = None
                self.history = GmailFindingHistory()
                self.next_refresh = 0
                raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        accounts = {}
        for provider in ("gmail", "outlook"):
            state = r.outbound_mail.auth_for(provider).account()
            accounts[provider] = SourceAccount(
                state["connected"], state["version"], state.get("email"),
                bool(state.get("reconnect_required")), state.get("connected_at"),
            )
        calendar = r.google.account()
        accounts["google_calendar"] = SourceAccount(
            calendar["connected"],
            calendar["version"],
            calendar.get("email"),
        )
        return (r.personal_context.revision(), prefs["version"], accounts)

    def collect(self, *, refresh=False, include_history=False):
        fence = self.fence()
        if self.account_versions != fence[2]:
            self.mail = {}
            self.mail_check = None
            self.next_refresh = 0
            self.account_versions = fence[2]
            self.history = GmailFindingHistory()
            if fence[2]["gmail"].reconnect_required:
                self.mail_check = {"at": iso(self.runtime.store.clock()), "available": False,
                                   "error": "APP_RECONNECT_REQUIRED"}
        now = self.runtime.store.clock().timestamp()
        if refresh and now >= self.next_refresh:
            self.next_refresh = now + 300
            current_mail = {}
            recent_gmail_refs = set()
            for provider, account in fence[2].items():
                if not account.connected or account.reconnect_required:
                    continue
                try:
                    data = query_connected_app(
                        self.runtime,
                        ConnectedAppQuery(
                            service="outlook_mail" if provider == "outlook" else provider,
                            query=INBOX if provider == "gmail" else None,
                            start=self.runtime.store.clock()
                            if provider == "google_calendar"
                            else None,
                            end=self.runtime.store.clock() + timedelta(days=7)
                            if provider == "google_calendar"
                            else None,
                            limit=10,
                        ),
                    )
                except DomainError as error:
                    # No stale email is treated as a fresh successful observation.
                    if provider == "gmail":
                        self.history = GmailFindingHistory()
                        self.mail_check = {"at": iso(self.runtime.store.clock()), "available": False, "error": error.code}
                    continue
                if self.fence() != fence:
                    raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
                if provider == "gmail":
                    self.mail_check = {"at": iso(self.runtime.store.clock()), "available": True, "count": len(data["items"])}
                for item in data["items"]:
                    ident = item.get("id")
                    if not isinstance(ident, str) or not 1 <= len(ident) <= 400:
                        continue
                    if provider == "google_calendar":
                        body = {k: item.get(k) for k in ("summary", "start", "end", "status")}
                        ref = f"calendar:google:{ident}"
                        current_mail[ref] = self.source(
                            ref,
                            "calendar",
                            item.get("summary", ""),
                            body,
                            {"account_version": account.version, "content": body},
                        )
                        continue
                    if provider == "gmail":
                        recent_gmail_refs.add(f"mail:gmail:{ident}")
                        source = self.gmail_source(item, account.version)
                        if source:
                            current_mail[source["ref"]] = source
                        continue
                    body = {
                        "subject": compact(item.get("subject"), 200),
                        "sender": compact(
                            item.get("from", {}).get("emailAddress", {}).get("address"), 254
                        ),
                        "preview": compact(item.get("bodyPreview")),
                        "date": compact(item.get("receivedDateTime"), 100),
                        "thread_id": item.get("conversationId"),
                    }
                    if PRIVATE_CODE.search(body["subject"] + " " + body["preview"]):
                        continue
                    ref = f"mail:{provider}:{ident}"
                    current_mail[ref] = self.source(
                        ref,
                        "mail",
                        body["subject"],
                        body,
                        {"account_version": account.version, "content": body},
                    )
            if self.mail_check and self.mail_check["available"] and fence[2]["gmail"].connected:
                history = self.history
                history.refresh(
                    self.runtime.store, self.runtime.store.clock(), recent_gmail_refs,
                    lambda query: query_connected_app(self.runtime, query),
                    lambda item: self.gmail_source(item, fence[2]["gmail"].version),
                    connected_at=fence[2]["gmail"].connected_at,
                )
            if self.fence() != fence:
                raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
            self.mail = current_mail
        stopped = self.stopped_threads()
        sources = {}
        mail = {**self.history.verified(now), **self.mail} if include_history else self.mail
        for ref, source in mail.items():
            provider = "gmail" if ref.startswith("mail:gmail:") else "outlook"
            if source["kind"] == "mail":
                account = fence[2][provider]
                thread = source["body"].get("thread_id")
                if (provider, (account.email or "").casefold(), thread) in stopped:
                    continue
            sources[ref] = source
        r = self.runtime
        for fact in r.memory.for_model()[:20]:
            ref = "memory:" + fact["id"]
            sources[ref] = self.source(
                ref,
                "memory",
                compact(fact["body"], 100),
                {"text": fact["body"]},
                {"version": fact["version"], "text": fact["body"]},
            )
        with r.store.connection() as conn:
            # Only user-authored, explicitly shareable prose can inform a new finding.
            # Fingerprint content so an edit or removal invalidates the citation.
            # Never pass previous action receipts back as authority.
            topic = " ".join(s["label"] + " " + s["body"].get("preview", "")[:100] for s in sources.values() if s["kind"] == "mail")[:1800]
            recent = r.home_history.permitted(conn, "text")[-6:]
            for message in [*r.home_history.matching(conn, "text", topic), *recent]:
                if message["role"] == "user":
                    body = {"text": compact(message["content"], 350)}
                    ref = "conversation:" + fingerprint(body)
                    sources[ref] = self.source(ref, "conversation", "Conversation", body, body)
            rows = conn.execute("SELECT id FROM tasks ORDER BY updated_at DESC LIMIT 20").fetchall()
            for row in rows:
                task = r.tasks.get(conn, row["id"])
                if task["paused"]:
                    continue
                body = {
                    k: task[k]
                    for k in (
                        "title",
                        "status",
                        "next_step",
                        "waiting_for",
                        "due_local",
                        "timezone",
                    )
                }
                progress = conn.execute(
                    "SELECT note FROM task_evidence WHERE task_id=? AND kind='note' ORDER BY id DESC LIMIT 1",
                    (task["id"],),
                ).fetchone()
                body["progress"] = compact(progress[0], 800) if progress else ""
                ref = "task:" + task["id"]
                sources[ref] = self.source(
                    ref, "task", task["title"], body, {"version": task["version"], "content": body}
                )
        # Share the calendar's current occurrence projection: raw event rows
        # include soft deletions and cannot resolve moved/cancelled instances.
        begin = r.store.clock()
        for event in r.store.snapshot(begin, begin + timedelta(days=7))["occurrences"][:20]:
            body = {
                k: event.get(k)
                for k in ("title", "start", "end", "timezone", "notes", "completed")
            }
            ref = f"calendar:{event['id']}:{event['occurrence_key']}"
            sources[ref] = self.source(
                ref,
                "calendar",
                event["title"],
                body,
                {"version": event["version"], "content": body},
            )
        if self.fence() != fence:
            raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
        if include_history:
            return fence, sources
        # Keep a mix of categories under one input budget, rather than letting
        # a long mailbox preview crowd out the facts it should be compared to.
        groups = [
            [s for s in sources.values() if s["kind"] == kind]
            for kind in ("memory", "task", "calendar", "mail", "conversation")
        ]
        bounded, remaining = {}, 26000
        for index in range(20):
            for group in groups:
                if index < len(group):
                    source = group[index]
                    size = len(encode(source))
                    if size <= remaining:
                        bounded[source["ref"]] = source
                        remaining -= size
        return fence, bounded

    def gmail_source(self, item, version):
        ident = item.get("id")
        if not isinstance(ident, str) or not 1 <= len(ident) <= 400:
            return None
        labels = set(item.get("labels") or [])
        if labels & {"SENT", "DRAFT", "SPAM", "TRASH", "CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL"}:
            return None
        fields = {h.get("name", "").lower(): h.get("value", "") for h in item.get("headers", [])}
        body = {
            "subject": compact(fields.get("subject"), 200),
            "sender": compact(fields.get("from"), 254),
            "preview": compact(item.get("snippet")),
            "date": compact(fields.get("date"), 100),
            "thread_id": item.get("thread_id"),
        }
        if PRIVATE_CODE.search(body["subject"] + " " + body["preview"]):
            return None
        return self.source(f"mail:gmail:{ident}", "mail", body["subject"], body,
                           {"account_version": version, "content": body})

    @staticmethod
    def source(ref, kind, label, body, revision):
        return {
            "ref": ref,
            "kind": kind,
            "label": compact(label, 100),
            "body": body,
            "fingerprint": fingerprint(revision),
        }

    def matches(self, references, sources):
        return all(
            ref["ref"] in sources and sources[ref["ref"]]["fingerprint"] == ref["fingerprint"]
            for ref in references
        )

    def display_sources(self, references, current):
        result = []
        for item in references:
            ref = item["ref"]
            link = {}
            if ref.startswith("mail:gmail:") and ref in current:
                thread = current[ref]["body"].get("thread_id")
                acct = (self.account_versions or {}).get("gmail")
                if isinstance(thread, str) and thread and acct and acct[0] and acct[2]:
                    link["href"] = "https://mail.google.com/mail/?" + urlencode({"authuser": acct[2]}) + "#all/" + quote(thread, safe="")
            result.append({**item, **link})
        return result
