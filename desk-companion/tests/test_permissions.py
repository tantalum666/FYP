"""Standing owner permission is not a tool, a paired grant, or retrospective approval."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.jobs import JobApproval
from desk.store import DomainError
from desk.text_ai import TextPlan
from desk.tool_dispatch import ToolDispatcher

from test_task_job_journey import write
from test_text_conversation_scope import owner_client, send


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = owner_client(app)
    principal = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    return app, client, principal


def mode(client, value, key):
    version = client.get("/api/permissions").json()["version"]
    return write(client, "/api/permissions", {"mode": value, "expected_version": version}, key)


def test_permissions_are_owner_only_versioned_and_not_model_tools(tmp_path, monkeypatch):
    app, owner, _ = setup(tmp_path, monkeypatch)
    assert owner.get("/api/permissions").json()["mode"] == "ask"
    mode(owner, "full", "full")
    assert owner.get("/api/workspace").json()["permissions"]["mode"] == "full"
    assert owner.post("/api/permissions", json={"mode": "full", "expected_version": 1},
                      headers={"X-Desk-Request": "1", "X-Operation-Id": "stale"}).status_code == 409
    write(owner, "/api/devices/enrol-display", {"name": "Fixture screen"}, "pair")
    paired = TestClient(app, headers={
        "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
        "X-Desk-Request": "1",
    })
    assert paired.get("/api/permissions").status_code == 403
    assert paired.post("/api/permissions", json={"mode": "full", "expected_version": 2},
                       headers={"X-Operation-Id": "paired"}).status_code == 403
    assert "permissions" not in paired.get("/api/workspace").json()
    for name in ("permission_change", "grant_full_access", "computer_job_approve"):
        with pytest.raises(DomainError, match="TOOL_NOT_ALLOWED"):
            app.state.runtime.assistant.tool(name, {}, name)


@pytest.mark.parametrize("language", ["en", "zh"])
def test_full_access_applies_new_owner_facts_and_forgetting_cannot_replay_them(tmp_path, monkeypatch, language):
    app, client, _ = setup(tmp_path, monkeypatch)
    runtime = app.state.runtime
    mode(client, "full", "enable")
    reply = send(client, "Remember: Fictional orchid code", key="remember", language=language).json()
    assert reply["saved"] is True and reply["proposal"] is None
    assert reply["authorization"]["mode"] == "full"
    assert runtime.memory.for_model()[0]["source"] == "owner_policy"
    forgotten = send(client, "Forget: Fictional orchid code", key="forget", language=language).json()
    assert forgotten["saved"] is True and runtime.memory.for_model() == []
    replay = send(client, "Remember: Fictional orchid code", key="remember", language=language).json()
    assert "Fictional orchid code" not in str(replay)
    assert ("已清除" if language == "zh" else "was cleared") in replay["message"]
    assert runtime.memory.for_model() == []
    recovered_chat = runtime.voice.conversations.entries[replay["conversation_id"]]
    assert "Fictional orchid code" not in str(recovered_chat.items)
    # Retired request identities survive restarts, without retaining their body.
    restarted = create_app(tmp_path, password="fixture", scheduler=False)
    next_client = owner_client(restarted)
    replay = send(next_client, "Remember: Fictional orchid code", key="remember", language=language).json()
    assert replay["saved"] is False
    assert restarted.state.runtime.memory.for_model() == []
    assert restarted.state.runtime.voice.conversations.entries[replay["conversation_id"]].items == []
    assert send(next_client, "Remember: Different fact", key="remember", language=language).status_code == 409
    # A deliberate new request can still remember the fact again.
    assert send(next_client, "Remember: Fictional orchid code", key="remember-again", language=language).json()["saved"]


def test_pending_ask_first_action_does_not_auto_run_after_mode_change(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    first = send(client, "Remember: Still needs review", key="pending").json()
    assert first["saved"] is False
    mode(client, "full", "enable")
    same = send(client, "Remember: Still needs review", key="pending").json()
    assert same["saved"] is False and same["proposal"]["id"] == first["proposal"]["id"]
    assert app.state.runtime.memory.for_model() == []
    write(client, f"/api/assistant/proposals/{first['proposal']['id']}/decisions",
          {"action": "confirm"}, "allow-once")
    assert len(app.state.runtime.memory.for_model()) == 1


@pytest.mark.parametrize("principal", [None, {"kind": "agent"}, {"kind": "display"},
                                    {"kind": "owner", "session": "expired"}])
def test_internal_paired_and_expired_callers_cannot_capture_owner_grant(tmp_path, monkeypatch, principal):
    app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    assert app.state.runtime.permissions.capture(principal) is None
    internal = app.state.runtime.text_ai.message(
        AssistantMessage(message="Remember: Internal candidate"), "internal"
    )
    assert internal["saved"] is False and app.state.runtime.memory.for_model() == []


def test_permission_change_during_generation_leaves_action_for_review(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    started, release = Event(), Event()
    runtime = app.state.runtime
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return TextPlan(message="Prepare a fact", tool="memory_save_draft", arguments={"body": "Fixture during change"})

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(send, client, "Please prepare the requested action", key="in-flight")
        assert started.wait(5)
        mode(owner_client(app), "ask", "revoke")
        release.set()
        reply = future.result(timeout=5).json()
    assert reply["saved"] is False and reply["proposal"]["state"] == "pending"
    assert runtime.memory.for_model() == []


def test_revocation_stops_queued_automatic_job_but_preserves_manual_approval(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    jobs = app.state.runtime.jobs
    manual = send(client, "Save note: Manual fixture", key="manual").json()["job"]
    current = jobs.detail(manual["id"], review=True)
    jobs.approve(manual["id"], JobApproval(expected_version=current["version"],
                 intent_hash=current["intent_hash"]), "manual-approval")
    mode(client, "full", "enable")
    automatic = send(client, "Save note: Automatic fixture", key="auto").json()["job"]
    assert automatic["state"] == "queued"
    mode(client, "ask", "revoke")
    jobs.run_one()
    jobs.run_one()
    assert jobs.detail(manual["id"])["state"] == "succeeded"
    assert jobs.detail(automatic["id"])["error"] == "PERMISSION_CHANGED"
    assert not (jobs.executor.root / (automatic["id"] + ".txt")).exists()


def test_full_access_file_receipt_recovers_after_restart_without_rewriting(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    first = send(client, "Save note: One authorised file", key="file-request").json()
    job_id = first["job"]["id"]
    assert first["queued"] is True and first["saved"] is False
    app.state.runtime.jobs.run_one()
    path = app.state.runtime.jobs.executor.root / (job_id + ".txt")
    stamp = path.stat().st_mtime_ns
    restarted = create_app(tmp_path, password="fixture", scheduler=False)
    fresh = owner_client(restarted)
    assert fresh.get("/api/permissions").json()["mode"] == "full"
    recovered = send(fresh, "Save note: One authorised file", key="file-request").json()
    assert recovered["job"]["state"] == "succeeded" and recovered["saved"] is True
    restarted.state.runtime.jobs.run_one()
    assert path.stat().st_mtime_ns == stamp and len(list(path.parent.glob("*.txt"))) == 1


def test_effect_committed_before_confirmation_receipt_recovers_without_another_write(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    runtime = app.state.runtime
    original = runtime.memory.create

    def crash_after_commit(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("fixture process loss after committed effect")

    monkeypatch.setattr(runtime.memory, "create", crash_after_commit)
    payload = AssistantMessage(message="Remember: Committed fixture")
    with pytest.raises(RuntimeError, match="fixture process loss"):
        runtime.text_ai.message(payload, "same-request", principal=principal)
    assert len(runtime.memory.for_model()) == 1
    restarted = create_app(tmp_path, password="fixture", scheduler=False)
    fresh = owner_client(restarted)
    recovered = send(fresh, payload.message, key="same-request").json()
    assert recovered["saved"] is True and recovered["proposal"] is None
    assert len(restarted.state.runtime.memory.for_model()) == 1
    assert restarted.state.runtime.assistant.proposals() == []
    with restarted.state.store.connection() as conn:
        proposal_id = conn.execute("SELECT id FROM assistant_proposals").fetchone()[0]
    restarted.state.runtime.assistant.decide(proposal_id, "confirm", "receipt-repair")
    with restarted.state.store.connection() as conn:
        assert conn.execute("SELECT state FROM assistant_proposals").fetchone()[0] == "confirmed"


def test_automatic_task_completion_records_standing_permission_not_a_manual_click(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    created = send(client, "Track: Review a fictional note", key="task").json()
    assert created["saved"] is True
    task = app.state.runtime.tasks.listing()["tasks"][0]
    completed = send(client, "done", task_id=task["id"], key="complete").json()
    assert completed["saved"] is True
    detail = app.state.runtime.tasks.detail(task["id"])
    assert detail["task"]["completion_source"] == "owner_policy"
    assert detail["evidence"][0]["source"] == "owner_policy"


def test_calendar_full_access_is_applied_once_and_ask_first_still_prepares_a_draft(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    message = "Tomorrow 14:00–15:00 Calendar permission fixture"
    first = send(client, message, key="same-calendar").json()
    assert first["saved"] is True and first["proposal"] is None
    again = send(client, message, key="same-calendar").json()
    assert again["saved"] is True
    with app.state.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    mode(client, "ask", "revoke")
    pending = send(client, "Tomorrow 16:00–17:00 Review this event", key="ask-calendar").json()
    assert pending["saved"] is False and pending["proposal"]["state"] == "pending"
    with app.state.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_full_access_does_not_automatically_run_physical_output_proposals(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    runtime = app.state.runtime
    draft = runtime.assistant.propose("output", {"output": {"kind": "arm", "preset": "attention"}}, "physical")
    result = runtime.permissions.apply_reply(draft, runtime.permissions.capture(principal))
    assert result["saved"] is False and result["proposal"]["state"] == "pending"
    with pytest.raises(DomainError, match="OWNER_APPROVAL_REQUIRED"):
        runtime.assistant.decide(draft["proposal"]["id"], "confirm", "blocked-output",
                                 permission_version=runtime.permissions.snapshot()["version"])


def test_lost_permission_response_recovery_cannot_restore_an_old_full_access_mode(tmp_path, monkeypatch):
    _app, client, _ = setup(tmp_path, monkeypatch)
    request = {"mode": "full", "expected_version": 1}
    write(client, "/api/permissions", request, "same-permission-request")
    mode(client, "ask", "revoke")
    receipt = write(client, "/api/permissions", request, "same-permission-request")
    assert receipt["permissions"]["mode"] == "ask" and receipt["permissions"]["version"] == 3


def test_revocation_from_stale_screen_fences_delayed_full_access_request(tmp_path, monkeypatch):
    _app, client, _ = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    revoked = write(client, "/api/permissions", {"mode": "ask", "expected_version": 1}, "revoke-stale")
    assert revoked["permissions"]["mode"] == "ask" and revoked["permissions"]["version"] == 3
    reaffirmed = write(client, "/api/permissions", {"mode": "ask", "expected_version": 3}, "fence-pending")
    assert reaffirmed["permissions"]["version"] == 4
    delayed = client.post("/api/permissions", json={"mode": "full", "expected_version": 3},
                          headers={"X-Desk-Request": "1", "X-Operation-Id": "delayed-full"})
    assert delayed.status_code == 409
    assert client.get("/api/permissions").json()["mode"] == "ask"


def test_completed_task_can_get_a_new_read_only_check_without_losing_its_scope(tmp_path, monkeypatch):
    app, client, _ = setup(tmp_path, monkeypatch)
    task = write(client, "/api/tasks", {"title": "Fixture archived task"}, "task")["task"]
    job = send(client, "Save note: Archived fixture", task_id=task["id"], key="note").json()["job"]
    current = app.state.runtime.jobs.detail(job["id"], review=True)
    write(client, f"/api/computer/jobs/{job['id']}/approve", {
        "expected_version": current["version"], "intent_hash": current["intent_hash"],
    }, "approve")
    app.state.runtime.jobs.run_one()
    completed = write(client, f"/api/tasks/{task['id']}/actions", {
        "action": "complete", "expected_version": 1,
    }, "complete")["task"]
    checked = write(client, "/api/computer/jobs", {
        "action": "verify_note", "source_job_id": job["id"], "title": "Check archived fixture",
        "task_id": task["id"], "task_version": completed["version"],
    }, "check")["job"]
    assert checked["task_id"] == task["id"] and checked["state"] == "review"


def test_realtime_dispatch_uses_same_owner_policy(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")

    async def run():
        dispatcher = ToolDispatcher(app.state.runtime, "voice-permission", principal=principal)
        dispatcher.submit({"id": "remember", "name": "memory_save_draft", "arguments": {"body": "Voice fixture"}})
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=3)
        assert result["saved"] is True
        dispatcher.delivered("remember", result)
        await dispatcher.close()

    asyncio.run(run())
    assert app.state.runtime.memory.for_model()[0]["body"] == "Voice fixture"


def test_full_access_read_status_cannot_approve_an_existing_pending_job(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    pending = send(client, "Save note: Old pending fixture", key="old-pending").json()["job"]
    mode(client, "full", "enable")
    runtime = app.state.runtime

    async def run():
        dispatcher = ToolDispatcher(runtime, "voice-status", principal=principal)
        dispatcher.submit({"id": "status", "name": "computer_job_status", "arguments": {"job_id": pending["id"]}})
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=3)
        assert result["job"]["state"] == "review"
        dispatcher.delivered("status", result)
        await dispatcher.close()

    asyncio.run(run())
    # The service independently refuses retrospective approval, even without the dispatch gate.
    runtime.permissions.apply_reply({"job": pending}, runtime.permissions.capture(principal))
    runtime.jobs.run_one()
    assert runtime.jobs.detail(pending["id"])["state"] == "review"
    assert not runtime.jobs.executor.root.exists()


def test_revoked_login_and_interrupted_preparation_cannot_use_captured_permission(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    runtime = app.state.runtime
    grant = runtime.permissions.capture(principal)
    pending = runtime.assistant.propose_fact("Interrupted fixture", "fixture", origin="assistant_confirmed")
    unchanged = runtime.permissions.apply_reply(pending, grant, cancelled=lambda: True)
    assert unchanged["saved"] is False
    client.delete("/api/session", headers={"X-Desk-Request": "1"})
    runtime.permissions.apply_reply(pending, grant)
    assert runtime.memory.for_model() == []


def test_realtime_interruption_discards_late_draft_before_automatic_application(tmp_path, monkeypatch):
    app, client, principal = setup(tmp_path, monkeypatch)
    mode(client, "full", "enable")
    runtime = app.state.runtime
    entered, release = Event(), Event()
    original = runtime.assistant.tool

    def slow_tool(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.assistant, "tool", slow_tool)

    async def run():
        dispatcher = ToolDispatcher(runtime, "interrupted-full", principal=principal)
        dispatcher.submit({"id": "slow", "name": "memory_save_draft", "arguments": {"body": "Must remain unsaved"}})
        assert await asyncio.to_thread(entered.wait, 2)
        await dispatcher.cancel()
        release.set()
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=3)
        assert result == {"error": "TOOL_CANCELLED", "saved": False}
        await dispatcher.close()

    asyncio.run(run())
    assert runtime.memory.for_model() == [] and runtime.assistant.proposals() == []
