"""Recheck the Gmail evidence behind a dated, previously delivered finding."""

import json
from datetime import datetime, timedelta

from .app_connection_models import ConnectedAppQuery
from .calendar import iso
from .store import DomainError

INBOX = "in:inbox newer_than:7d -category:promotions -category:social"
LOOKBACK = timedelta(days=7)
RECHECK_SECONDS = 1800


class GmailFindingHistory:
    def __init__(self):
        self.checked = {}
        self.windows = {}

    def refresh(self, store, now, recent, read, project, *, connected_at=None):
        # Older releases did not save an account identifier on each citation. Search by
        # time on this owner's current grant, and require its exact content+grant hash.
        # Never send a message ID from a previous account to the newly connected one.
        stamp = now.timestamp()
        with store.connection() as db:
            rows = db.execute(
                """SELECT created_at,data FROM initiative_findings
                   WHERE (state IN ('pending','dismissed') OR (state='obsolete' AND notified=1))
                   AND created_at BETWEEN ? AND ?
                   ORDER BY (state='dismissed'),notified,created_at DESC LIMIT 100""",
                (max(iso(now - LOOKBACK), connected_at or ""), iso(now)),
            ).fetchall()
        windows = {}
        missing = set()
        for row in rows:
            references = {
                (s["ref"], s["fingerprint"])
                for s in json.loads(row["data"])["sources"]
                if s["ref"].startswith("mail:gmail:") and s["ref"] not in recent
            }
            if references:
                end = int(datetime.fromisoformat(row["created_at"]).timestamp()) + 1
                windows.setdefault(end, set()).update(references)
                missing.update(references)
        self.checked = {
            ref: entry
            for ref, entry in self.checked.items()
            if (ref, entry[1]["fingerprint"]) in missing and 0 <= stamp - entry[0] < RECHECK_SECONDS
        }
        self.windows = {end: at for end, at in self.windows.items() if end in windows}
        needed = [
            end
            for end, refs in windows.items()
            if any(ref not in self.checked for ref, _ in refs)
            and (end not in self.windows or not 0 <= stamp - self.windows[end] < RECHECK_SECONDS)
        ]
        if not needed:
            return
        end = min(needed, key=lambda key: self.windows.get(key, 0))
        # At most one extra list of ten per scheduled refresh. The date refers to
        # when this batch was originally read, even across a desk restart.
        self.windows[end] = stamp
        try:
            result = read(
                ConnectedAppQuery(service="gmail", query=f"{INBOX} before:{end}", limit=10)
            )
        except DomainError:
            return
        for item in result["items"]:
            # A fresh contradictory read supersedes any earlier receipt for this message.
            ident = item.get("id")
            if isinstance(ident, str):
                self.checked.pop(f"mail:gmail:{ident}", None)
            source = project(item)
            if source and (source["ref"], source["fingerprint"]) in missing:
                # Only the thread pointer is needed to open a checked historical citation.
                self.checked[source["ref"]] = (
                    stamp,
                    {
                        **source,
                        "historical": True,
                        "body": {"thread_id": source["body"]["thread_id"]},
                    },
                )

    def verified(self, now):
        return {
            ref: item for ref, (at, item) in self.checked.items() if 0 <= now - at < RECHECK_SECONDS
        }
