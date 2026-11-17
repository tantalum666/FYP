"""Small current-evidence projection; provider readers/OAuth remain authoritative."""

import hashlib
import json
from datetime import timedelta

from .app_connection_models import ConnectedAppQuery
from .connected_app_data import query_connected_app
from .store import DomainError, encode


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def compact(value, limit=1200):
    return " ".join(str(value or "").split())[:limit]


class InitiativeSources:
    def __init__(self, runtime):
        self.runtime = runtime
        self.mail = {}
        self.next_refresh = 0
        self.account_versions = None

    def fence(self):
        r = self.runtime
        prefs = r.data.preferences()
        with r.store.connection() as conn:
            if r.store.settings(conn)["hide_private"] or prefs["proactivity"] == "off":
                self.mail = {}
                self.next_refresh = 0
                raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        accounts = {}
        for provider in ("gmail", "outlook"):
            state = r.outbound_mail.auth_for(provider).account()
            accounts[provider] = (state["connected"], state["version"], state.get("email"))
        calendar = r.google.account()
        accounts["google_calendar"] = (
            calendar["connected"],
            calendar["version"],
            calendar.get("email"),
        )
        return (r.personal_context.revision(), prefs["version"], accounts)

    def collect(self, *, refresh=False):
        fence = self.fence()
        if self.account_versions != fence[2]:
            self.mail = {}
            self.next_refresh = 0
            self.account_versions = fence[2]
        now = self.runtime.store.clock().timestamp()
        if refresh and now >= self.next_refresh:
            self.next_refresh = now + 300
            current_mail = {}
            for provider, account in fence[2].items():
                if not account[0]:
                    continue
                try:
                    data = query_connected_app(
                        self.runtime,
                        ConnectedAppQuery(
                            service="outlook_mail" if provider == "outlook" else provider,
                            query="newer_than:7d" if provider == "gmail" else None,
                            start=self.runtime.store.clock()
                            if provider == "google_calendar"
                            else None,
                            end=self.runtime.store.clock() + timedelta(days=7)
                            if provider == "google_calendar"
                            else None,
                            limit=10,
                        ),
                    )
                except DomainError:
                    # No stale email is treated as a fresh successful observation.
                    continue
                if self.fence() != fence:
                    raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
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
                            {"account_version": account[1], "content": body},
                        )
                        continue
                    if provider == "gmail":
                        fields = {
                            h.get("name", "").lower(): h.get("value", "")
                            for h in item.get("headers", [])
                        }
                        body = {
                            "subject": compact(fields.get("subject"), 200),
                            "sender": compact(fields.get("from"), 254),
                            "preview": compact(item.get("snippet")),
                            "date": compact(fields.get("date"), 100),
                            "thread_id": item.get("thread_id"),
                        }
                    else:
                        body = {
                            "subject": compact(item.get("subject"), 200),
                            "sender": compact(
                                item.get("from", {}).get("emailAddress", {}).get("address"), 254
                            ),
                            "preview": compact(item.get("bodyPreview")),
                            "date": compact(item.get("receivedDateTime"), 100),
                        }
                    ref = f"mail:{provider}:{ident}"
                    current_mail[ref] = self.source(
                        ref,
                        "mail",
                        body["subject"],
                        body,
                        {"account_version": account[1], "content": body},
                    )
            self.mail = current_mail
        sources = dict(self.mail)
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
            for row in conn.execute(
                "SELECT id,data,version FROM events ORDER BY rowid DESC LIMIT 20"
            ):
                event = json.loads(row["data"])
                body = {
                    k: event.get(k)
                    for k in ("title", "start_local", "end_local", "timezone", "notes")
                }
                ref = "calendar:" + row["id"]
                sources[ref] = self.source(
                    ref,
                    "calendar",
                    event.get("title", ""),
                    body,
                    {"version": row["version"], "content": body},
                )
        if self.fence() != fence:
            raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
        # Keep a mix of categories under one input budget, rather than letting
        # a long mailbox preview crowd out the facts it should be compared to.
        groups = [
            [s for s in sources.values() if s["kind"] == kind]
            for kind in ("memory", "task", "calendar", "mail")
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
