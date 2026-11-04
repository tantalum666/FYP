"""Durable shopping delivery through the existing Notifier and rules tick."""

from dataclasses import asdict
import hashlib
import json

from ..notify import Notice
from ..store import encode


def notice_id(connection_id: str, event_id: str) -> str:
    return "shop-" + hashlib.sha256(f"{connection_id}/{event_id}".encode()).hexdigest()[:32]


class ShoppingNotices:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS shopping_notice_holds("
                "notice_id TEXT PRIMARY KEY,connection_id TEXT NOT NULL,"
                "event_id TEXT NOT NULL,payload TEXT NOT NULL)"
            )

    def publish(self, connection_id: str, event_id: str, notice: Notice, *, quiet: bool):
        # Persist before handing off: a crash/restart retries the same notice ID.
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO shopping_notice_holds VALUES(?,?,?,?)",
                (notice.id, connection_id, event_id, encode(asdict(notice))),
            )
        return self._deliver(notice, quiet=quiet)

    def _deliver(self, notice: Notice, *, quiet: bool):
        results = self.runtime.notify.publish(notice, quiet=quiet)
        delivered = any(row["status"] in {"delivered", "duplicate"} for row in results)
        if delivered:
            with self.store.connection(write=True) as conn:
                conn.execute("DELETE FROM shopping_notice_holds WHERE notice_id=?", (notice.id,))
        return delivered

    def release(self, *, quiet: bool):
        if quiet:
            return
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM shopping_notice_holds ORDER BY notice_id"
            ).fetchall()
        for row in rows:
            self._deliver(Notice(**json.loads(row["payload"])), quiet=False)


def validate_holds(rows, connections: dict) -> list[dict]:
    if not isinstance(rows, list) or len(rows) > 500:
        raise ValueError("Invalid shopping notice backup")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"connection_id", "event_id", "notice"}:
            raise ValueError("Invalid shopping notice backup")
        cid, eid, payload = row["connection_id"], row["event_id"], row["notice"]
        if (
            not isinstance(cid, str)
            or cid not in connections
            or not isinstance(eid, str)
            or not 1 <= len(eid) <= 64
        ):
            raise ValueError("Invalid shopping notice backup")
        if not isinstance(payload, dict) or set(payload) != set(Notice.__dataclass_fields__):
            raise ValueError("Invalid shopping notice backup")
        if any(
            not isinstance(value, str) or not value or len(value) > 2000
            for value in payload.values()
        ):
            raise ValueError("Invalid shopping notice backup")
        if (
            payload["id"] != notice_id(cid, eid)
            or payload["kind"] != "shopping"
            or payload["id"] in seen
        ):
            raise ValueError("Invalid shopping notice backup")
        seen.add(payload["id"])
        result.append({"connection_id": cid, "event_id": eid, "notice": dict(payload)})
    return result
