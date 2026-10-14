import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.runtime import Runtime
from desk.store import DomainError, Store
from desk.schemas import SettingsInput
from desk.tasks import TaskInput, TaskAction
from desk.text_ai import TextAssistant, TextConfig


@pytest.fixture
def desk(tmp_path):
    clock = [datetime(2026, 10, 3, 1, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    return runtime, clock


def create(runtime, **fields):
    return runtime.tasks.create(TaskInput(title="Report", **fields), uuid4().hex)["task"]


def act(runtime, task, action, **fields):
    return runtime.tasks.action(
        task["id"],
        TaskAction(action=action, expected_version=task["version"], **fields),
        uuid4().hex,
    )["task"]


def test_task_followup_persists_and_restart_does_not_duplicate(desk):
    r, c = desk
    t = create(r, check_in_local="2026-10-03T09:01", next_step="Prepare charts")
    assert r.tasks.listing()["tasks"][0]["followup"] is None
    c[0] += timedelta(minutes=2)
    r.tick()
    r.tick()
    first = r.tasks.listing()["tasks"][0]
    assert first["followup"] and first["next_check_at"] is None
    r2 = Runtime(r.store)
    r2.tick()
    second = r2.tasks.listing()["tasks"][0]
    assert first["followup"]["id"] == second["followup"]["id"]
    assert len(r2.tasks.detail(t["id"])["evidence"]) == 2


def test_progress_invalidates_old_reminder_and_keeps_evidence(desk):
    r, c = desk
    t = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    t = act(r, t, "note", note="Data received; charts pending")
    value = r.tasks.detail(t["id"])
    assert value["task"]["status"] == "todo" and value["task"]["followup"] is None
    assert value["evidence"][0]["note"] == "Data received; charts pending"
    assert t["next_check_at"]
    r.tick()
    assert not r.tasks.snapshot()["due_count"]


def test_pause_snooze_completion_cancel_and_reopen(desk):
    r, c = desk
    t = create(r, interval_minutes=15)
    t = act(r, t, "pause")
    c[0] += timedelta(days=2)
    r.tick()
    assert not r.tasks.snapshot()["due_count"]
    t = act(r, t, "resume", minutes=60)
    c[0] += timedelta(minutes=61)
    r.tick()
    assert r.tasks.snapshot()["due_count"] == 1
    t = act(r, t, "snooze", minutes=120)
    r.tick()
    assert not r.tasks.snapshot()["due_count"]
    t = act(r, t, "complete", note="Submitted by me")
    c[0] += timedelta(days=30)
    r.tick()
    assert not r.tasks.listing()["tasks"]
    assert r.tasks.detail(t["id"])["evidence"][0]["source"] == "user_confirmed"
    t = act(r, t, "reopen")
    assert t["status"] == "todo"
    t = act(r, t, "cancel")
    assert not r.tasks.listing()["tasks"]
    assert len(r.tasks.listing(include_closed=True)["tasks"]) == 1


def test_duplicate_creation_and_version_conflict_do_not_overwrite(desk):
    r, c = desk
    payload = TaskInput(title="Report")
    first = r.tasks.create(payload, "same")
    second = r.tasks.create(payload, "same")
    assert first == second
    t = act(r, first["task"], "note", note="New progress")
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        act(r, first["task"], "complete")
    assert r.tasks.detail(t["id"])["task"]["status"] == "todo"


def test_due_time_and_explicit_snooze_have_distinct_meaning(desk):
    r, c = desk
    t = create(r, due_local="2026-10-03T10:00")
    assert datetime.fromisoformat(t["next_check_at"].replace("Z", "+00:00")) == datetime(
        2026, 10, 3, 2, tzinfo=UTC
    )
    t = act(r, t, "snooze", minutes=120)
    c[0] += timedelta(minutes=61)
    r.tick()
    assert r.tasks.listing()["tasks"][0]["overdue"] and not r.tasks.snapshot()["due_count"]
    c[0] += timedelta(hours=1)
    r.tick()
    assert r.tasks.snapshot()["due_count"] == 1


def test_dates_waiting_and_invalid_fields_are_rejected(desk):
    r, c = desk
    with pytest.raises(ValidationError):
        TaskInput(title=" ", status="waiting")
    with pytest.raises(ValidationError):
        TaskInput(title="Report", status="waiting")
    with pytest.raises(ValidationError):
        TaskInput(title="Report", due_local="2026-11-01T01:30", timezone="America/New_York")
    with pytest.raises(DomainError, match="CHECK_IN_IN_PAST"):
        create(r, check_in_local="2026-10-03T08:00")


def test_private_projection_and_model_query_do_not_leak_hidden_facts(desk):
    r, c = desk
    t = create(r, next_step="Secret next step", waiting_for="Secret person")
    r.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True), "hide"
    )
    result = r.tasks.listing()
    assert result["tasks"][0]["redacted"] and "Secret" not in json.dumps(result)
    with pytest.raises(DomainError, match="PRIVATE_TASK_HIDDEN"):
        r.tasks.detail(t["id"])
    assert not r.tasks.listing(query="Report")["tasks"]


def test_assistant_drafts_need_confirmation_and_selected_task_progress_persists(desk):
    r, c = desk
    p = r.assistant.local_message(
        AssistantMessage(message="跟进：报告", language="zh"), "create-draft"
    )["proposal"]
    assert not r.tasks.listing()["tasks"]
    saved = r.assistant.decide(p["id"], "confirm", "confirm")
    t = saved["result"]["task"]
    r.assistant.decide(p["id"], "confirm", "confirm-again")
    assert len(r.tasks.listing()["tasks"]) == 1
    p = r.assistant.local_message(
        AssistantMessage(message="数据到了，图还没做", task_id=t["id"], language="zh"), "note-draft"
    )["proposal"]
    assert p["data"]["change"]["action"] == "note"
    r.assistant.decide(p["id"], "confirm", "note-confirm")
    assert r.tasks.detail(t["id"])["task"]["status"] == "todo"
    p = r.assistant.local_message(
        AssistantMessage(message="已提交", task_id=t["id"], language="zh"), "done-draft"
    )["proposal"]
    r.assistant.decide(p["id"], "cancel", "done-cancel")
    assert r.tasks.detail(t["id"])["task"]["status"] == "todo"


@pytest.mark.parametrize("provider", ["qwen", "gemini"])
def test_text_provider_protocol_proposes_without_mutating_and_caches_retry(desk, provider):
    r, c = desk
    calls = []

    def response(request):
        calls.append(json.loads(request.content))
        plan = {
            "message": "Review this task",
            "tool": "task_create_draft",
            "arguments": {"title": "Model report"},
        }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(plan)}}],
                "usage": {"prompt_tokens": 30},
            }
            if provider == "qwen"
            else {
                "candidates": [{"content": {"parts": [{"text": json.dumps(plan)}]}}],
                "usageMetadata": {"promptTokenCount": 30},
            },
        )

    cfg = TextConfig(
        provider=provider,
        model="test-model",
        api_key="fixture-key",
        endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        if provider == "qwen"
        else "",
    )
    service = TextAssistant(r, cfg, httpx.MockTransport(response))
    payload = AssistantMessage(message="Please track my report")
    one = service.message(payload, "request")
    two = service.message(payload, "request")
    assert one == two and len(calls) == 1 and not r.tasks.listing()["tasks"]
    assert one["mode"] == "ai" and one["proposal"]["kind"] == "task_create"
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        service.message(AssistantMessage(message="Different"), "request")


def test_malformed_model_response_cannot_execute_or_claim_completion(desk):
    r, c = desk

    def response(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"message": "Done", "tool": "confirm", "arguments": {}}
                            )
                        }
                    }
                ]
            },
        )

    config = TextConfig(
        "qwen",
        "test-model",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "fixture",
    )
    service = TextAssistant(r, config, httpx.MockTransport(response))
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        service.message(AssistantMessage(message="Create"), "invalid")
    assert not r.tasks.listing()["tasks"]


def test_background_advice_does_not_overwrite_progress_changed_during_request(desk):
    r, c = desk
    t = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()

    def response(request):
        act(r, t, "complete")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"en": "Any progress?", "zh": "有进展吗？"})
                        }
                    }
                ]
            },
        )

    service = TextAssistant(
        r,
        TextConfig(
            "qwen",
            "test-model",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "fixture",
            True,
        ),
        httpx.MockTransport(response),
    )
    service.enrich_one()
    assert (
        not r.tasks.snapshot()["due_count"]
        and r.tasks.detail(t["id"])["task"]["status"] == "completed"
    )


def test_task_api_requires_auth_and_returns_real_saved_state(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        assert client.get("/api/tasks").status_code == 401
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        )
        response = client.post(
            "/api/tasks",
            json={"title": "API task"},
            headers={"X-Desk-Request": "1", "X-Operation-Id": "new-task"},
        )
        assert response.status_code == 200
        task_id = response.json()["task"]["id"]
        assert client.get("/api/tasks/" + task_id).json()["task"]["title"] == "API task"
        assert client.get("/api/workspace").json()["tasks"]["active_count"] == 1


def test_backup_restores_tasks_paused_and_never_overwrites_current_progress(desk, tmp_path):
    from desk.exchange import BackupInput, ImportApply

    r, c = desk
    t = create(r, next_step="Write results")
    t = act(r, t, "note", note="Measurements received")
    document = r.exchange.backup()
    fresh = Runtime(Store(tmp_path / "restored", password="fixture-only", clock=lambda: c[0]))
    preview = fresh.exchange.preview_backup(BackupInput(content=json.dumps(document)), "preview")
    result = fresh.exchange.apply(preview["preview_id"], ImportApply(), "apply")
    assert result["tasks_created"] == 1
    task = fresh.tasks.detail(t["id"])
    assert task["task"]["paused"] and task["task"]["next_check_at"] is None
    assert any(
        e["note"] == "Measurements received" and e["source"] == "backup" for e in task["evidence"]
    )
    current = act(fresh, task["task"], "note", note="Newer progress")
    preview = fresh.exchange.preview_backup(
        BackupInput(content=json.dumps(document)), "preview-again"
    )
    result = fresh.exchange.apply(preview["preview_id"], ImportApply(), "apply-again")
    assert result["tasks_kept"] == 1
    assert fresh.tasks.detail(current["id"])["evidence"][0]["note"] == "Newer progress"


def test_task_sound_respects_quiet_hours_and_is_claimed_only_once(desk):
    from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

    r, c = desk
    create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    prefs = r.data.preferences()
    r.data.update(
        PreferencesUpdate(
            expected_version=prefs["version"],
            preferences=WorkspacePreferences(
                reminder_strength="chime",
                quiet_enabled=True,
                quiet_start="00:00",
                quiet_end="23:59",
            ),
        ),
        "quiet",
    )
    tasks = r.tasks.listing(display=True)["tasks"]
    assert r.data.claim_announcement("display-one", tasks=tasks)["quiet"]
    prefs = r.data.preferences()
    r.data.update(
        PreferencesUpdate(
            expected_version=prefs["version"],
            preferences=WorkspacePreferences(reminder_strength="chime", quiet_enabled=False),
        ),
        "sound",
    )
    assert r.data.claim_announcement("display-one", tasks=tasks)["announcement"]["kind"] == "task"
    assert r.data.claim_announcement("display-two", tasks=tasks)["announcement"] is None


def test_background_failed_attempts_count_toward_daily_limit(desk):
    r, c = desk
    for i in range(22):
        r.tasks.create(TaskInput(title=f"Report {i}", interval_minutes=15), uuid4().hex)
    c[0] += timedelta(minutes=16)
    # Reminders leave the queue a few at a time, so advance until 20 are pending.
    for _ in range(20):
        r.tick()
        c[0] += timedelta(minutes=1)
    calls = []

    def response(request):
        calls.append(True)
        return httpx.Response(503, json={"error": "unavailable"})

    service = TextAssistant(
        r,
        TextConfig(
            "qwen",
            "test-model",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "fixture",
            True,
        ),
        httpx.MockTransport(response),
    )
    for i in range(25):
        service.enrich_one()
    assert len(calls) == 20


def _advice_service(runtime):
    calls = []

    def response(request):
        calls.append(True)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"en": "Check in?", "zh": "要更新吗？"})}}
                ]
            },
        )

    service = TextAssistant(
        runtime,
        TextConfig(
            "qwen",
            "test-model",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "fixture",
            True,
        ),
        httpx.MockTransport(response),
    )
    return service, calls


def test_turning_followup_off_keeps_the_task_and_skips_queued_advice(desk):
    r, c = desk
    task = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    saved = r.tasks.action(
        task["id"],
        TaskAction(
            action="update",
            expected_version=task["version"],
            task=TaskInput(title="Report", follow_up_enabled=False, interval_minutes=15),
        ),
        "quiet-followup",
    )["task"]
    service, calls = _advice_service(r)
    service.enrich_one()
    current = r.tasks.detail(saved["id"])["task"]
    assert calls == []
    assert current["status"] == "todo" and current["follow_up_enabled"] is False
    with r.store.connection() as conn:
        row = conn.execute(
            "SELECT state FROM task_followups WHERE task_id=?", (saved["id"],)
        ).fetchone()
    assert row["state"] == "resolved"


def test_queued_advice_is_skipped_when_followup_is_disabled_without_resolving(desk):
    r, c = desk
    task = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    with r.store.connection(write=True) as conn:
        raw = json.loads(conn.execute("SELECT data FROM tasks WHERE id=?", (task["id"],)).fetchone()[0])
        raw["follow_up_enabled"] = False
        conn.execute("UPDATE tasks SET data=? WHERE id=?", (json.dumps(raw), task["id"]))
    service, calls = _advice_service(r)
    service.enrich_one()
    assert calls == []
    assert r.tasks.detail(task["id"])["task"]["title"] == "Report"
    with r.store.connection() as conn:
        row = conn.execute(
            "SELECT state, ai_status FROM task_followups WHERE task_id=?", (task["id"],)
        ).fetchone()
    assert row["state"] == "pending" and row["ai_status"] == "skipped"


def test_quiet_hours_defer_followups_until_the_window_ends(desk):
    r, c = desk
    # 15:00 UTC is 23:00 in Asia/Hong_Kong, inside the default 22:00–07:00 quiet window.
    c[0] = datetime(2026, 10, 3, 15, tzinfo=UTC)
    task = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    saved = r.tasks.detail(task["id"])["task"]
    assert saved["followup"] is None
    assert saved["next_check_at"].startswith("2026-10-03T23:00:00")
    c[0] = datetime(2026, 10, 3, 23, 1, tzinfo=UTC)
    r.tick()
    assert r.tasks.detail(task["id"])["task"]["followup"]


def test_overdue_followups_are_released_a_few_at_a_time(desk):
    r, c = desk
    tasks = [
        r.tasks.create(TaskInput(title=f"Report {i}", interval_minutes=15), uuid4().hex)["task"]
        for i in range(5)
    ]
    c[0] += timedelta(minutes=16)
    r.tick()
    due = [t for t in r.tasks.listing()["tasks"] if t["followup"]]
    waiting = [t for t in r.tasks.listing()["tasks"] if t["next_check_at"]]
    assert len(due) == 3 and len(waiting) == 2
    c[0] += timedelta(minutes=1)
    r.tick()
    due = [t for t in r.tasks.listing()["tasks"] if t["followup"]]
    assert len(due) == 4
    assert all(item["status"] == "todo" for item in r.tasks.listing()["tasks"])
    assert len(tasks) == 5


def test_quiet_hours_do_not_send_queued_text_advice(desk):
    r, c = desk
    task = create(r, interval_minutes=15)
    c[0] += timedelta(minutes=16)
    r.tick()
    service, calls = _advice_service(r)
    c[0] = datetime(2026, 10, 3, 15, tzinfo=UTC)
    service.enrich_one()
    assert calls == []
    c[0] = datetime(2026, 10, 3, 23, 30, tzinfo=UTC)
    service.enrich_one()
    assert calls == [True]
    assert r.tasks.detail(task["id"])["task"]["status"] == "todo"


def test_private_task_detail_uses_away_projection(desk, monkeypatch):
    r, _ = desk
    task = create(r, next_step="Private next step")
    observation = r.posture.snapshot()
    observation["preferences"].update(enabled=True, privacy_when_away=True)
    observation.update(connected=False, status="unknown")
    monkeypatch.setattr(r.posture, "snapshot", lambda: observation)
    assert r.tasks.listing(display=True)["tasks"][0]["redacted"]
    with pytest.raises(DomainError, match="PRIVATE_TASK_HIDDEN"):
        r.tasks.detail(task["id"], display=True)
    assert r.tasks.detail(task["id"])["task"]["next_step"] == "Private next step"
