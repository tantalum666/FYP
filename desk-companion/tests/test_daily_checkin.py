from datetime import UTC, datetime, timedelta

from desk.runtime import Runtime
from desk.store import Store
from desk.tasks import TaskInput, TaskAction
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences
from desk.schemas import SettingsInput


def test_late_brief_due_task_explicit_completion_and_quiet_share_existing_state(tmp_path):
    clock = [datetime(2026, 11, 16, 2, tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password="fixture", clock=lambda: clock[0]))
    owner = {"kind": "owner", "id": "owner"}
    r.data.update(
        PreferencesUpdate(
            expected_version=1, preferences=WorkspacePreferences(daily_brief_enabled=True)
        ),
        "on",
    )
    r.tick()
    brief = r.snapshot(owner)["check_in"]
    assert brief["kind"] == "morning_brief"
    r.nudges.dismiss(brief["id"], "read")
    assert r.snapshot(owner)["check_in"] is None
    assert r.notify.listing()["notices"][0]["state"] == "dismissed"
    task = r.tasks.create(
        TaskInput(title="Write outline", next_step="Draft three headings", interval_minutes=15),
        "task",
    )["task"]
    clock[0] += timedelta(minutes=16)
    r.tick()
    cue = r.snapshot(owner)["check_in"]
    assert cue["kind"] == "task" and cue["next_step"] == "Draft three headings"
    assert r.snapshot({"kind": "display", "id": "screen"})["check_in"] is None
    r.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True), "hide"
    )
    assert r.snapshot(owner)["check_in"] is None
    r.store.update_settings(
        SettingsInput(expected_version=2, timezone="Asia/Hong_Kong", hide_private=False), "show"
    )
    r.tasks.action(
        task["id"], TaskAction(action="complete", expected_version=cue["version"]), "complete"
    )
    assert r.snapshot(owner)["check_in"] is None
    assert all(n["state"] == "dismissed" for n in r.notify.listing()["notices"])
    assert r.tasks.detail(task["id"])["task"]["completion_source"] == "user_confirmed"


def test_movement_cue_uses_live_evidence_and_honors_proactivity_off(tmp_path):
    now = datetime(2026, 11, 16, 2, tzinfo=UTC)
    r = Runtime(Store(tmp_path, password="fixture", clock=lambda: now))
    e = r.posture.engine
    e.preferences["enabled"] = True
    e.last_received = now.timestamp()
    e.source = "live"
    e.movement_feedback = {"created_at": now.timestamp(), "outcome": "notice", "source": "live"}
    owner = {"kind": "owner", "id": "owner"}
    assert r.snapshot(owner)["check_in"]["position"] == "movement"
    e.movement_feedback["source"] = "replay"
    assert r.snapshot(owner)["check_in"] is None
    e.movement_feedback["source"] = "live"
    r.data.update(
        PreferencesUpdate(expected_version=1, preferences=WorkspacePreferences(proactivity="off")),
        "off",
    )
    assert r.snapshot(owner)["check_in"] is None
