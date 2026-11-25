from datetime import UTC, date, datetime, timedelta
import json
from types import SimpleNamespace

from desk.app import create_app
from desk.locked_reminders import LockedReminders, SimulatorReceiver
from desk.notify import Notice


def test_durable_delivery_per_destination_quiet_revoke_and_dismiss(tmp_path, monkeypatch):
    now = [datetime(2026, 11, 25, 5, tzinfo=UTC)]
    monkeypatch.setenv("DESK_WEB_PUSH", "1")
    runtime = create_app(
        tmp_path, clock=lambda: now[0], scheduler=False, password="fixture"
    ).state.runtime
    sim_calls, web_calls = [], []
    sim = SimpleNamespace(udid="fixture", send=lambda ident: sim_calls.append(ident) or "accepted")
    queue = LockedReminders(runtime, date(2027, 5, 24), sim)
    runtime.notify.locked = queue
    with runtime.store.connection(write=True) as db:
        for ident in ("browser-one", "browser-two"):
            db.execute(
                "INSERT INTO push_subscriptions VALUES(?,?,?,?,?,NULL)",
                (ident, "https://example.test/" + ident, "unused", "unused", now[0].isoformat()),
            )

    def send(payload, *, subscription_id):
        assert "private agenda" not in json.dumps(payload)
        web_calls.append(subscription_id)
        return int(subscription_id == "browser-one" or web_calls.count(subscription_id) > 1)

    monkeypatch.setattr(runtime.notify.push, "dispatch", send)

    def notice(ident):
        return Notice(
            ident, "initiative", "private agenda", "私密事项", "details", "", "reason", ""
        )

    runtime.notify.publish(notice("first"), quiet=False)
    now[0] = datetime(2026, 11, 25, 15, tzinfo=UTC)
    queue.tick()
    assert not web_calls and not sim_calls
    now[0] = datetime(2026, 11, 25, 23, 10, tzinfo=UTC)
    for _ in range(4):
        queue.tick()
    assert sim_calls == ["first"] and web_calls == ["browser-one", "browser-two"]
    queue = LockedReminders(runtime, queue.through, sim)
    now[0] += timedelta(minutes=3)
    queue.tick()
    assert web_calls == ["browser-one", "browser-two", "browser-two"]
    runtime.notify.publish(notice("second"), quiet=False)
    runtime.notify.dismiss("second", "owner-handled-second")
    for _ in range(4):
        queue.tick()
    assert sim_calls == ["first"]
    with runtime.store.connection() as db:
        assert {
            r[0]
            for r in db.execute("SELECT channel FROM notice_deliveries WHERE notice_id='first'")
        } >= {"web_push_accepted", "simulator_push_accepted"}


def test_simulator_transport_requires_same_origin_explicit_opt_in_and_fixed_target(tmp_path):
    prefs = tmp_path / "Library/Application Support/alice-lock-reminder-receiver.json"
    prefs.parent.mkdir(parents=True)
    target = "CB0FC414-498F-4E63-839B-33632AB5DA71"
    origin = "http://127.0.0.1:8832"
    sent = []

    def call(argv, **options):
        if "get_app_container" in argv:
            return SimpleNamespace(returncode=0, stdout=str(tmp_path).encode())
        assert argv[-4:] == ["push", target, "dev.group2.deskcompanion", "-"]
        sent.append(json.loads(options["input"]))
        return SimpleNamespace(returncode=0, stdout=b"")

    receiver = SimulatorReceiver(target, origin, runner=call)
    for enabled, bind, expected in (
        (False, origin, "off"),
        (True, "https://different.example", "off"),
        (True, origin, "accepted"),
    ):
        if enabled:
            prefs.write_text(json.dumps({"origin": bind}))
        else:
            prefs.unlink(missing_ok=True)
        assert receiver.send("private agenda") == expected
    assert (
        len(sent) == 1
        and sent[0]["desk_route"] == "assistant"
        and "private agenda" not in json.dumps(sent)
    )
