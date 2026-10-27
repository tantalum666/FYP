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
