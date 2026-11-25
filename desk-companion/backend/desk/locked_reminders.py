"""Optional Mac host for enrolled browser and Simulator lock-screen reminders."""

from contextlib import suppress
from datetime import date, timedelta
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
from threading import Lock
from urllib.parse import urlsplit
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from .calendar import iso
from .workspace_data import is_quiet

APP_ID = "dev.group2.deskcompanion"
ZONE = ZoneInfo("Asia/Hong_Kong")


class SimulatorReceiver:
    def __init__(self, udid, origin, device_set=None, runner=subprocess.run):
        self.udid = str(UUID(udid)).upper()
        url = urlsplit(origin)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1"}
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
            or not url.port
        ):
            raise ValueError("The Simulator must be connected to the same local desk")
        self.origin, self.runner = origin, runner
        self.prefix = ["/usr/bin/xcrun", "simctl"]
        if device_set:
            if not Path(device_set).is_absolute():
                raise ValueError("Use an absolute CoreSimulator device set")
            self.prefix += ["--set", device_set]

    def command(self, *args, body=None):
        return self.runner(
            [*self.prefix, *args],
            input=body,
            capture_output=True,
            timeout=12,
            env={
                k: v
                for k, v in os.environ.items()
                if k in {"PATH", "HOME", "TMPDIR", "DEVELOPER_DIR", "LANG"}
            },
        )

    def send(self, notice_id):
        try:
            container = self.command("get_app_container", self.udid, APP_ID, "data")
            if container.returncode:
                return "retry"
            directory = Path(os.fsdecode(container.stdout.strip()))
            if not directory.is_absolute():
                return "retry"
            prefs = directory / "Library/Preferences" / (APP_ID + ".plist")
            if not prefs.is_file():
                return "off"
            if prefs.is_symlink() or prefs.stat().st_size > 1000000:
                return "off"
            values = plistlib.loads(prefs.read_bytes())
            if (
                not values.get("desk.notifications.enabled")
                or values.get("desk.server.origin.v1") != self.origin
                or values.get("desk.locked-reminders.origin.v1") != self.origin
            ):
                return "off"
            alert = {
                "aps": {
                    "alert": {
                        "title": "Alice",
                        "body": "Open Alice to see your update. 打开 Alice 查看动态。",
                    },
                    "thread-id": "alice-updates",
                },
                "desk_route": "assistant",
            }
            # The fixed receiver and bundle come from the operator configuration, never a request.
            try:
                result = self.command(
                    "push", self.udid, APP_ID, "-", body=json.dumps(alert).encode()
                )
            except subprocess.TimeoutExpired:
                return "unknown"
            return "accepted" if result.returncode == 0 else "retry"
        except (OSError, subprocess.TimeoutExpired, ValueError, plistlib.InvalidFileException):
            return "retry"


class LockedReminders:
    @classmethod
    def configured(cls, runtime):
        path = runtime.store.directory / "locked-reminders.json"
        if sys.platform != "darwin" or not path.exists():
            return None
        st = path.lstat()
        if (
            not stat.S_ISREG(st.st_mode)
            or st.st_uid != os.getuid()
            or st.st_mode & 0o077
            or st.st_size > 8192
        ):
            raise ValueError("Invalid private lock-screen configuration")
        config = json.loads(path.read_text())
        receiver = SimulatorReceiver(**config["simulator"]) if config.get("simulator") else None
        return cls(
            runtime,
            date.fromisoformat(config["through"]),
            receiver,
            keep_awake=config.get("keep_awake") is True,
        )

    def __init__(self, runtime, through, simulator=None, *, keep_awake=False):
        self.runtime, self.store = runtime, runtime.store
        self.through, self.simulator, self.keep_awake = through, simulator, keep_awake
        self.assertion = None
        self.closing = False
        self.power_lock = Lock()
        with self.store.connection(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS locked_reminder_outbox (
                notice_id TEXT NOT NULL, destination TEXT NOT NULL, expires_at TEXT NOT NULL,
                due TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                lease TEXT, lease_until TEXT, PRIMARY KEY(notice_id,destination))""")

    def active(self):
        return self.store.clock().astimezone(ZONE).date() <= self.through

    def stop(self):
        with self.power_lock:
            self.closing = True
            self._power(False)

    def power(self, enabled):
        with self.power_lock:
            self._power(enabled and not self.closing)

    def _power(self, enabled):
        if not enabled:
            if self.assertion is not None:
                with suppress(ProcessLookupError):
                    self.assertion.terminate()
                self.assertion.wait(timeout=5)
                self.assertion = None
        elif self.keep_awake and (self.assertion is None or self.assertion.poll() is not None):
            # No display assertion: macOS can still lock and turn off the screen.
            self.assertion = subprocess.Popen(
                ["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def enqueue(self, db, notice, at):
        if not self.active():
            return
        targets = []
        if self.runtime.notify.push:
            targets += [
                "web/" + r[0]
                for r in db.execute("SELECT id FROM push_subscriptions WHERE revoked_at IS NULL")
            ]
        if self.simulator:
            targets.append("sim/" + self.simulator.udid)
        db.executemany(
            """INSERT OR IGNORE INTO locked_reminder_outbox(notice_id,destination,expires_at,due,state)
                       VALUES(?,?,?,?,'pending')""",
            [(notice.id, t, iso(at + timedelta(hours=24)), iso(at)) for t in targets],
        )

    def tick(self):
        now = self.store.clock()
        prefs = self.runtime.data.preferences()
        enabled = not self.closing and self.active() and prefs["proactivity"] != "off"
        self.power(enabled)
        with self.store.connection(write=True) as db:
            db.execute("DELETE FROM locked_reminder_outbox WHERE expires_at<=?", (iso(now),))
            if not enabled or self.store.settings(db)["hide_private"]:
                db.execute("DELETE FROM locked_reminder_outbox")
                return
            if is_quiet(prefs, now.astimezone(ZoneInfo(self.store.settings(db)["timezone"]))):
                return
            db.execute("""DELETE FROM locked_reminder_outbox WHERE NOT EXISTS(
                       SELECT 1 FROM notice_inbox i WHERE i.id=locked_reminder_outbox.notice_id AND i.state='open')""")
            row = db.execute(
                """SELECT * FROM locked_reminder_outbox WHERE state='pending' AND due<=?
                    AND (lease_until IS NULL OR lease_until<=?) ORDER BY due,notice_id,destination LIMIT 1""",
                (iso(now), iso(now)),
            ).fetchone()
            if not row:
                return
            ident, target = row["notice_id"], row["destination"]
            lease = uuid4().hex
            db.execute(
                "UPDATE locked_reminder_outbox SET lease=?,lease_until=? WHERE notice_id=? AND destination=?",
                (lease, iso(now + timedelta(minutes=2)), ident, target),
            )
        if target.startswith("web/") and self.runtime.notify.push:
            payload = {
                "title": "Alice",
                "body": "Open Alice to see your update. 打开 Alice 查看动态。",
                "tag": ident,
            }
            status = (
                "accepted"
                if self.runtime.notify.push.dispatch(payload, subscription_id=target[4:])
                else "retry"
            )
        elif self.simulator and target == "sim/" + self.simulator.udid:
            status = self.simulator.send(ident)
        else:
            status = "off"
        with self.store.connection(write=True) as db:
            attempts = row["attempts"] + 1
            state = "pending" if status == "retry" else status
            if (
                status == "retry"
                and target.startswith("web/")
                and not db.execute(
                    "SELECT 1 FROM push_subscriptions WHERE id=? AND revoked_at IS NULL",
                    (target[4:],),
                ).fetchone()
            ):
                state = "off"
            changed = db.execute(
                """UPDATE locked_reminder_outbox SET state=?,attempts=?,due=?,lease=NULL,lease_until=NULL
                        WHERE notice_id=? AND destination=? AND lease=?""",
                (
                    state,
                    attempts,
                    iso(now + timedelta(seconds=min(300, 15 * 2 ** min(attempts, 5)))),
                    ident,
                    target,
                    lease,
                ),
            )
            if changed.rowcount and status == "accepted":
                channel = (
                    "web_push_accepted" if target.startswith("web/") else "simulator_push_accepted"
                )
                db.execute(
                    "INSERT OR IGNORE INTO notice_deliveries VALUES(?,?,?)",
                    (ident, channel, iso(self.store.clock())),
                )
