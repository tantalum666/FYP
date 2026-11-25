"""Notification channels: quiet hours, one delivery per channel, device claim once."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.notify import Notice, Notifier
from desk.runtime import Runtime
from desk.store import Store
from desk.tasks import TaskInput
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences


class _Fake:
    name = "fake"

    def __init__(self):
        self.sent = []

    def accept(self, notice, conn, at):
        del conn, at
        self.sent.append(notice.id)


def test_quiet_hours_skip_channels_and_a_second_publish_is_a_duplicate(tmp_path):
    store = Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    fake = _Fake()
    notifier = Notifier(store, channels=[fake])
    notice = Notice(
        "morning_brief-2026-10-02",
        "morning_brief",
        "Morning briefing",
        "早晨简报",
        "1 open task.",
        "1 件事务。",
        "Quiet hours are not in effect.",
        "当前不在安静时段。",
    )
    assert notifier.publish(notice, quiet=True) == [{"channel": "fake", "status": "quiet"}]
    assert fake.sent == []
    assert notifier.publish(notice, quiet=False) == [{"channel": "fake", "status": "delivered"}]
    assert notifier.publish(notice, quiet=False) == [{"channel": "fake", "status": "duplicate"}]
    assert fake.sent == ["morning_brief-2026-10-02"]
    assert notice.payload()["push"]["tag"] == notice.id


def test_check_in_reaches_the_open_inbox_and_one_device(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(daily_brief_enabled=True),
        ),
        "enable",
    )
    runtime.tick()
    inbox = runtime.notify.listing()["notices"]
    assert len(inbox) == 1
    assert inbox[0]["push"]["tag"] == "morning_brief-2026-10-02"
    assert "08:00" in inbox[0]["reason_en"]
    first = runtime.data.claim_announcement("display-one")
    assert first["announcement"]["kind"] == "notice"
    assert "quiet hours" in first["announcement"]["reason_en"]
    assert runtime.data.claim_announcement("display-two")["announcement"] is None
    runtime.tick()
    assert len(runtime.notify.listing()["notices"]) == 1
    clock[0] += timedelta(hours=15)
    assert runtime.data.claim_announcement("display-one")["quiet"] is True


def test_followup_is_delivered_without_a_private_next_step(tmp_path):
    clock = [datetime(2026, 10, 3, 1, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    runtime.tasks.create(
        TaskInput(title="Report", check_in_local="2026-10-03T09:30", next_step="Secret chart"),
        "task",
    )
    clock[0] += timedelta(hours=1)
    runtime.tasks.tick()
    notices = runtime.notify.listing()["notices"]
    assert len(notices) == 1 and notices[0]["kind"] == "followup"
    dumped = str(notices)
    assert "Secret chart" not in dumped
    assert "saved check time" in notices[0]["reason_en"]


def test_display_cannot_read_the_inbox(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    owner = TestClient(app)
    assert (
        owner.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-notices"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/notices").status_code == 403
    assert display.get("/api/notices?open_only=true").status_code == 403


def test_open_notice_pages_keep_history_after_one_dismissal(tmp_path):
    store = Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 11, 24, tzinfo=UTC))
    notifier = Notifier(store)
    for index in range(25):
        notice = Notice(f"same-time-{index:02}", "evening_check", "Evening", "晚间", "Body", "正文", "", "")
        notifier.publish(notice, quiet=False)
    initial = notifier.listing(open_only=True)
    assert initial["total"] == 25 and len(initial["notices"]) == 20
    first_ids = [row["id"] for row in initial["notices"]]
    assert all(row["created_at"] for row in initial["notices"])
    notifier.dismiss(initial["next"], "handled-one")
    last = notifier.listing(open_only=True, before=initial["next"])
    assert last["total"] == 24 and last["next"] is None and len(last["notices"]) == 5
    assert not set(first_ids).intersection(row["id"] for row in last["notices"])
    assert all(row["state"] == "open" for row in notifier.listing(open_only=True)["notices"])
    assert any(row["state"] == "dismissed" for row in notifier.listing()["notices"])


def test_browser_outbox_and_push_service_acceptance_are_distinct(tmp_path):
    from types import SimpleNamespace

    store = Store(tmp_path, password="fixture", clock=lambda: datetime(2026, 11, 25, 4, tzinfo=UTC))
    attempts = []

    def dispatch(payload):
        attempts.append(payload)
        return int(len(attempts) == 2)

    notifier = Notifier(store, push=SimpleNamespace(dispatch=dispatch))
    for ident in ("not-accepted", "accepted", "accepted"):
        notifier.publish(Notice(ident, "initiative", "Update", "动态", "", "", "", ""), quiet=False)
    with store.connection() as db:
        assert len(attempts) == 2
        accepted = db.execute("SELECT notice_id FROM notice_deliveries WHERE channel='web_push_accepted'")
        assert [r[0] for r in accepted] == ["accepted"]
        assert db.execute("SELECT count(*) FROM notice_deliveries WHERE channel='browser'").fetchone()[0] == 2
