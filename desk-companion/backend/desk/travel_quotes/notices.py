"""Trip notices use the existing notifier. Quiet hours keep the same id."""

import hashlib
import json
from dataclasses import asdict

from ..notify import Notice
from ..store import encode


def notice_id(connection_id: str, event_id: str) -> str:
    material = f"{connection_id}/{event_id}".encode()
    return "trip-" + hashlib.sha256(material).hexdigest()[:32]


class TripNotices:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS trip_notice_holds("
                "notice_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL,"
                "event_id TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def publish(self, connection_id: str, event_id: str, notice: Notice, *, quiet: bool):
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO trip_notice_holds VALUES(?,?,?,?)",
                (notice.id, connection_id, event_id, encode(asdict(notice))),
            )
        return self._deliver(notice, quiet=quiet)

    def _deliver(self, notice: Notice, *, quiet: bool):
        results = self.runtime.notify.publish(notice, quiet=quiet)
        delivered = any(row["status"] in {"delivered", "duplicate"} for row in results)
        if delivered:
            with self.store.connection(write=True) as conn:
                conn.execute("DELETE FROM trip_notice_holds WHERE notice_id=?", (notice.id,))
        return delivered

    def release(self, *, quiet: bool):
        if quiet:
            return
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM trip_notice_holds ORDER BY notice_id"
            ).fetchall()
        for row in rows:
            self._deliver(Notice(**json.loads(row["payload"])), quiet=False)
