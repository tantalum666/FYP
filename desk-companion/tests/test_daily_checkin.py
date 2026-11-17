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
    r.tasks.create(TaskInput(title="Regular commitment"), "regular")
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


def test_brief_omits_paused_and_opted_out_work(tmp_path):
    r = Runtime(
        Store(tmp_path, password="fixture", clock=lambda: datetime(2026, 11, 16, 2, tzinfo=UTC))
    )
    owner = {"kind": "owner", "id": "owner"}
    r.data.update(
        PreferencesUpdate(
            expected_version=1, preferences=WorkspacePreferences(daily_brief_enabled=True)
        ),
        "on",
    )
    r.tasks.create(TaskInput(title="Historical fixture", follow_up_enabled=False), "fixture")
    r.tick()
    assert r.snapshot(owner)["check_in"] is None
    live = r.tasks.create(TaskInput(title="Current work"), "live")["task"]
    cue = r.snapshot(owner)["check_in"]
    assert cue["open_count"] == 1 and [t["title"] for t in cue["tasks"]] == ["Current work"]
    r.tasks.action(live["id"], TaskAction(action="pause", expected_version=1), "pause")
    assert r.snapshot(owner)["check_in"] is None


def test_today_summary_excludes_paused_work_and_includes_saved_next_steps(tmp_path):
    from desk.owner_lookup import plate_summary

    r = Runtime(
        Store(tmp_path, password="fixture", clock=lambda: datetime(2026, 11, 16, 2, tzinfo=UTC))
    )
    old = r.tasks.create(TaskInput(title="Old acceptance fixture", follow_up_enabled=False), "old")[
        "task"
    ]
    r.tasks.action(old["id"], TaskAction(action="pause", expected_version=1), "pause")
    r.tasks.create(TaskInput(title="Current work", next_step="Review the opening paragraph"), "new")
    items = plate_summary(r, {"window": "today"})["tasks"]
    assert [t["title"] for t in items] == ["Current work"]
    assert items[0]["next_step"] == "Review the opening paragraph"
    r.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True), "hide"
    )
    assert all(
        t["title"] == t["next_step"] == t["waiting_for"] == ""
        for t in plate_summary(r, {"window": "today"})["tasks"]
    )
