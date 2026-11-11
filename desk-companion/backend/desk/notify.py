"""Delivery channels for check-ins and reminders.

The owner still pulls history from the nudge list. This module is how a new
nudge is handed to an open page, a browser notification, and the device
surface. Quiet hours suppress every channel. The same notice id is delivered
once per channel. Web Push is sent only when a PushService is attached.
"""

from dataclasses import dataclass
from datetime import timedelta

from fastapi import APIRouter, Depends

from .calendar import iso
from .store import DomainError, encode


@dataclass(frozen=True)
class Notice:
    """One proactive item. Titles are counts or kinds, not private task names."""

    id: str
    kind: str
    title_en: str
    title_zh: str
    body_en: str
    body_zh: str
    reason_en: str
    reason_zh: str

    def payload(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title_en": self.title_en,
            "title_zh": self.title_zh,
            "body_en": self.body_en,
            "body_zh": self.body_zh,
            "reason_en": self.reason_en,
            "reason_zh": self.reason_zh,
            "push": push_payload(self),
        }


def push_payload(notice: Notice) -> dict:
    """JSON a Web Push sender could POST later. This desk does not send it."""
    return {
        "title": notice.title_en,
        "body": notice.body_en,
        "tag": notice.id,
        "data": {"reason_en": notice.reason_en, "reason_zh": notice.reason_zh},
    }


def device_key(notice: Notice) -> str:
    """Id the existing announcement claim already uses, so one event is spoken once."""
    if notice.kind == "morning_brief" and notice.id.startswith("morning_brief-"):
        return "brief/" + notice.id.removeprefix("morning_brief-")
    if notice.kind == "evening_check" and notice.id.startswith("evening_check-"):
        return "evening/" + notice.id.removeprefix("evening_check-")
    if notice.kind == "followup" and notice.id.startswith("followup-"):
        return "task/" + notice.id.removeprefix("followup-")
    return "notify/" + notice.id


class InAppChannel:
    """Inbox for a page that is open. The page reads it; this is not a poll of the model."""

    name = "in_app"

    def accept(self, notice: Notice, conn, at) -> None:
        conn.execute(
            "INSERT INTO notice_inbox(id, created_at, state, content) VALUES(?,?,'open',?)",
            (notice.id, iso(at), encode(notice.payload())),
        )


class BrowserChannel:
    """Stores the Web Push-shaped payload. The open page may show a Notification."""

    name = "browser"

    def accept(self, notice: Notice, conn, at) -> None:
        conn.execute(
            "INSERT INTO browser_notices(id, created_at, content) VALUES(?,?,?)",
            (notice.id, iso(at), encode(push_payload(notice))),
        )


class DeviceChannel:
    """Queues a device-surface announcement until the display claims it."""

    name = "device"

    def accept(self, notice: Notice, conn, at) -> bool:
        # A follow-up is already spoken by the task announcement claim.
        if notice.kind == "followup":
            return False
        # The owner notice cites the facts. The always-on display only says to open Memory.
        if notice.kind == "memory_morning":
            content = {
                "kind": "notice",
                "notice_kind": notice.kind,
                "reason_en": "Open Memory to read the morning check-in.",
                "reason_zh": "请打开记忆页查看早晨核对。",
                "body_en": "Open Memory to read the morning check-in.",
                "body_zh": "请打开记忆页查看早晨核对。",
            }
        else:
            content = {
                "kind": "notice",
                "notice_kind": notice.kind,
                "reason_en": notice.reason_en,
                "reason_zh": notice.reason_zh,
                "body_en": notice.body_en,
                "body_zh": notice.body_zh,
            }
        conn.execute(
            "INSERT INTO device_notices(id, canonical_id, created_at, expires_at, content) "
            "VALUES(?,?,?,?,?)",
            (
                notice.id,
                device_key(notice),
                iso(at),
                iso(at + timedelta(minutes=15)),
                encode(content),
            ),
        )
        return True


class Notifier:
    def __init__(self, store, channels=None, push=None):
        self.store = store
        self.owner_projection = lambda notice: notice
        self.push = push
        self.channels = (
            channels
            if channels is not None
            else [
                InAppChannel(),
                BrowserChannel(),
                DeviceChannel(),
            ]
        )
        with self.store.connection(write=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notice_deliveries(
                    notice_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    delivered_at TEXT NOT NULL,
                    PRIMARY KEY (notice_id, channel)
                );
                CREATE TABLE IF NOT EXISTS notice_inbox(
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS browser_notices(
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_notices(
                    id TEXT PRIMARY KEY,
                    canonical_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    claimed_by TEXT,
                    content TEXT NOT NULL
                );
                """
            )

    def publish(self, notice: Notice, *, quiet: bool) -> list[dict]:
        """Deliver once per channel, or to none of them during quiet hours."""
        if quiet:
            return [{"channel": channel.name, "status": "quiet"} for channel in self.channels]
        if not notice.id or len(notice.id) > 80:
            raise DomainError("NOTICE_ID_INVALID", 422)
        at = self.store.clock()
        results = []
        browser_delivered = False
        with self.store.connection(write=True) as conn:
            wrote = False
            for channel in self.channels:
                seen = conn.execute(
                    "SELECT 1 FROM notice_deliveries WHERE notice_id=? AND channel=?",
                    (notice.id, channel.name),
                ).fetchone()
                if seen:
                    results.append({"channel": channel.name, "status": "duplicate"})
                    continue
                if channel.accept(notice, conn, at) is False:
                    results.append({"channel": channel.name, "status": "skipped"})
                    continue
                conn.execute(
                    "INSERT INTO notice_deliveries VALUES(?,?,?)",
                    (notice.id, channel.name, iso(self.store.clock())),
                )
                results.append({"channel": channel.name, "status": "delivered"})
                wrote = True
                if channel.name == "browser":
                    browser_delivered = True
            if wrote:
                self.store.bump(conn)
        if browser_delivered and self.push is not None:
            self.push.dispatch(notice.payload()["push"])
        return results

    def listing(self) -> dict:
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notice_inbox ORDER BY created_at DESC, id LIMIT 20"
            ).fetchall()
        import json

        return {
            "notices": [
                self.owner_projection({**json.loads(row["content"]), "state": row["state"]})
                for row in rows
            ]
        }

    def dismiss(self, notice_id: str, key: str) -> dict:
        def apply(conn):
            row = conn.execute("SELECT * FROM notice_inbox WHERE id=?", (notice_id,)).fetchone()
            if not row:
                raise DomainError("NOTICE_NOT_FOUND", 404)
            if row["state"] != "dismissed":
                conn.execute("UPDATE notice_inbox SET state='dismissed' WHERE id=?", (notice_id,))
            import json

            return {"notice": {**json.loads(row["content"]), "state": "dismissed"}, "saved": True}

        result = self.store.operation(key, {"type": "notice_dismiss", "id": notice_id}, apply)
        return {**result, "notice": self.owner_projection(result["notice"])}


def claim_device_notice(store, conn, client_id: str, zone: str):
    """Hand the oldest unclaimed device notice to one display, if the table exists."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='device_notices'"
    ).fetchone():
        return None
    now = iso(store.clock())
    row = conn.execute(
        "SELECT * FROM device_notices WHERE claimed_by IS NULL AND expires_at>? "
        "ORDER BY created_at, id LIMIT 1",
        (now,),
    ).fetchone()
    while row:
        taken = conn.execute(
            "SELECT 1 FROM display_announcements WHERE id=?", (row["canonical_id"],)
        ).fetchone()
        conn.execute(
            "UPDATE device_notices SET claimed_by=? WHERE id=? AND claimed_by IS NULL",
            (client_id, row["id"]),
        )
        if not taken:
            import json

            conn.execute(
                "INSERT INTO display_announcements VALUES(?,?,?,?,?)",
                (
                    row["canonical_id"],
                    "notice",
                    now,
                    row["expires_at"],
                    client_id,
                ),
            )
            content = json.loads(row["content"])
            return {"id": row["canonical_id"], "timezone": zone, **content}
        row = conn.execute(
            "SELECT * FROM device_notices WHERE claimed_by IS NULL AND expires_at>? "
            "ORDER BY created_at, id LIMIT 1",
            (now,),
        ).fetchone()
    return None


def notice_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/notices", dependencies=[Depends(owner)])

    @router.get("")
    def listing():
        return runtime.notify.listing()

    @router.post("/{notice_id}/dismissals")
    def dismiss(notice_id: str, key=Depends(operation_id)):
        return runtime.notify.dismiss(notice_id, key)

    return router
