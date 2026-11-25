"""Task -> reviewed file -> independent receipt -> later owner continuation, offline."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.computer import LocalNotesExecutor
from desk.jobs import FolderNaming
from desk.schemas import SettingsInput
from desk.tasks import TaskInput

from test_text_conversation_scope import owner_client, send


def write(client, path, body, key):
    response = client.post(path, json=body, headers={
        "X-Desk-Request": "1", "X-Operation-Id": key,
    })
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("prefix", [
    "Save note", "保存笔记", "Save to folder", "保存到文件夹", "Editor preview", "编辑并预览",
])
def test_each_local_file_command_keeps_selected_task_and_invalidates_stale_approval(
    tmp_path, monkeypatch, prefix
):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    app = create_app(tmp_path / "runtime", password="fixture", scheduler=False)
    runtime = app.state.runtime
    folder = tmp_path / "files"
    folder.mkdir()
    runtime.jobs.set_folder(FolderNaming(label="Fixture folder", path=str(folder)), "folder")
    monkeypatch.setattr(runtime.jobs.desktop, "status", lambda: {"ready": True})
    task = runtime.tasks.create(TaskInput(title="Review fixture"), "task")["task"]
    reply = runtime.assistant.local_message(
        AssistantMessage(message=f"{prefix}: Fixture text", task_id=task["id"]), "draft"
    )
    job = runtime.jobs.detail(reply["job"]["id"], review=True)
    assert job["task_id"] == task["id"]
    assert job["request"]["task_version"] == task["version"]
    assert reply["saved"] is False and not runtime.jobs.executor.root.exists()
    assert list(folder.iterdir()) == []
    client = owner_client(app)
    write(client, f"/api/tasks/{task['id']}/actions", {
        "action": "note", "expected_version": task["version"], "note": "Scope changed",
    }, "task-update")
    rejected = client.post(f"/api/computer/jobs/{job['id']}/approve", json={
        "expected_version": job["version"], "intent_hash": job["intent_hash"],
    }, headers={"X-Desk-Request": "1", "X-Operation-Id": "approve-stale"})
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "JOB_TASK_CHANGED"


@pytest.mark.parametrize("crash_after_write", [False, True])
def test_http_task_journey_recovers_after_restart_without_rewriting_or_auto_completing(
    tmp_path, monkeypatch, crash_after_write
):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = owner_client(app)
    runtime = app.state.runtime
    task = write(client, "/api/tasks", {
        "title": "Fixture review", "next_step": "Read saved result", "follow_up_enabled": False,
    }, "create-task")["task"]
    text = "Fixture review\n核对文件后继续处理。"
    response = send(client, "Save note: " + text, task_id=task["id"], key="prepare-note")
    assert response.status_code == 200
    job_id = response.json()["job"]["id"]
    job = client.get(f"/api/computer/jobs/{job_id}").json()["job"]
    path = runtime.jobs.executor.root / (job_id + ".txt")
    assert not path.exists()
    approval = {"expected_version": job["version"], "intent_hash": job["intent_hash"]}
    write(client, f"/api/computer/jobs/{job_id}/approve", approval, "approval-lost-response")

    class ProcessCrash(BaseException):
        pass

    class CrashAfterWrite(LocalNotesExecutor):
        def execute(self, request, checkpoint):
            super().execute(request, checkpoint)
            raise ProcessCrash()

    if crash_after_write:
        runtime.jobs.executor = CrashAfterWrite(tmp_path)
        with pytest.raises(ProcessCrash):
            runtime.jobs.run_one()
    else:
        runtime.jobs.run_one()
    original = path.stat().st_mtime_ns
    assert path.read_bytes() == text.encode()

    restarted = create_app(tmp_path, password="fixture", scheduler=False)
    phone = owner_client(restarted)
    jobs = restarted.state.runtime.jobs
    # Recover the same approval receipt after login/restart. Never create another intent.
    recovered = write(phone, f"/api/computer/jobs/{job_id}/approve", approval,
                      "approval-lost-response")["job"]
    assert recovered["state"] == ("unknown" if crash_after_write else "succeeded")
    jobs.run_one()
    assert path.stat().st_mtime_ns == original
    if crash_after_write:
        detail = phone.get(f"/api/tasks/{task['id']}").json()
        assert detail["jobs"][0]["state"] == "unknown"
        write(phone, f"/api/computer/jobs/{job_id}/reconcile", {}, "read-existing")
    detail = phone.get(f"/api/tasks/{task['id']}").json()
    summary = detail["jobs"][0]
    assert len(detail["jobs"]) == 1 and summary["state"] == "succeeded"
    assert summary["result"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert summary["result"]["bytes"] == len(text.encode())
    assert "request" not in summary and "content" not in str(summary)
    assert detail["task"]["status"] == "todo" and detail["task"]["version"] == 1
    progress = write(phone, f"/api/tasks/{task['id']}/actions", {
        "action": "note", "expected_version": 1, "note": "Read verified result on phone",
    }, "phone-progress")["task"]
    assert progress["status"] == "todo" and progress["version"] == 2
    write(phone, f"/api/tasks/{task['id']}/actions", {
        "action": "complete", "expected_version": 2,
    }, "owner-confirm-complete")
    final = phone.get(f"/api/tasks/{task['id']}").json()
    assert final["task"]["status"] == "completed"
    assert final["task"]["completion_source"] == "user_confirmed"
    assert final["jobs"][0]["id"] == job_id
    assert len(list(path.parent.glob("*.txt"))) == 1 and path.stat().st_mtime_ns == original


def test_selected_task_keeps_an_unknown_result_away_from_a_same_name_task_and_a_paired_screen(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = owner_client(app)
    runtime = app.state.runtime
    selected = write(client, "/api/tasks", {
        "title": "Fixture review",
        "next_step": "Read the saved file",
        "follow_up_enabled": False,
        "steps": [{"title": "Gather the notes", "done": True}],
    }, "selected-task")["task"]
    other = write(client, "/api/tasks", {
        "title": "Fixture review",
        "next_step": "Leave this one alone",
        "follow_up_enabled": False,
    }, "other-task")["task"]
    text = "Fixture review\n核对文件后继续处理。"
    response = send(client, "Save note: " + text, task_id=selected["id"], key="prepare-selected")
    job_id = response.json()["job"]["id"]
    job = client.get(f"/api/computer/jobs/{job_id}").json()["job"]
    path = runtime.jobs.executor.root / (job_id + ".txt")
    approval = {"expected_version": job["version"], "intent_hash": job["intent_hash"]}
    write(client, f"/api/computer/jobs/{job_id}/approve", approval, "approval-once")

    class ProcessCrash(BaseException):
        pass

    class CrashAfterWrite(LocalNotesExecutor):
        def execute(self, request, checkpoint):
            super().execute(request, checkpoint)
            raise ProcessCrash()

    runtime.jobs.executor = CrashAfterWrite(tmp_path)
    with pytest.raises(ProcessCrash):
        runtime.jobs.run_one()
    original = path.stat().st_mtime_ns
    restarted = create_app(tmp_path, password="fixture", scheduler=False)
    phone = owner_client(restarted)
    recovered = write(
        phone, f"/api/computer/jobs/{job_id}/approve", approval, "approval-once"
    )["job"]
    assert recovered["state"] == "unknown"
    detail = phone.get(f"/api/tasks/{selected['id']}").json()
    assert detail["jobs"][0]["state"] == "unknown"
    assert detail["jobs"][0]["task_id"] == selected["id"]
    assert detail["task"]["steps"] == [{"title": "Gather the notes", "done": True}]
    assert phone.get(f"/api/tasks/{other['id']}").json()["jobs"] == []
    paired = TestClient(restarted)
    paired.cookies.set(
        "desk_companion_device",
        restarted.state.runtime.access.enrol_display("Lobby", "pair-lobby")["token"],
    )
    hidden = paired.get(f"/api/tasks/{selected['id']}")
    assert hidden.status_code == 403
    assert hidden.json()["error"]["code"] == "PRIVATE_TASK_HIDDEN"
    assert "Gather the notes" not in hidden.text and text not in hidden.text
    listed = paired.get("/api/tasks").json()["tasks"]
    assert all(row["title"] != "Fixture review" for row in listed)
    denied = paired.post(
        f"/api/tasks/{selected['id']}/actions",
        json={"action": "note", "expected_version": 1, "note": "paired note"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "paired-note"},
    )
    assert denied.status_code == 403
    enrolled = restarted.state.runtime.access.enrol_display("Later", "pair-later")
    client_id, token = enrolled["client_id"], enrolled["token"]
    restarted.state.runtime.access.revoke(client_id, "revoke-later")
    revoked = TestClient(restarted)
    revoked.cookies.set("desk_companion_device", token)
    assert revoked.get(f"/api/tasks/{selected['id']}").status_code == 401
    checked = write(phone, f"/api/computer/jobs/{job_id}/reconcile", {}, "read-existing")
    again = write(phone, f"/api/computer/jobs/{job_id}/reconcile", {}, "read-existing")
    assert checked["job"]["state"] == again["job"]["state"] == "succeeded"
    assert path.stat().st_mtime_ns == original
    after = phone.get(f"/api/tasks/{selected['id']}").json()["task"]
    assert after["steps"] == [{"title": "Gather the notes", "done": True}]
    assert after["status"] == "todo"
    with restarted.state.runtime.store.connection() as conn:
        version = restarted.state.runtime.store.settings(conn)["version"]
    restarted.state.runtime.store.update_settings(
        SettingsInput(expected_version=version, timezone="Asia/Hong_Kong", hide_private=True),
        "hide-task",
    )
    concealed = phone.get(f"/api/tasks/{selected['id']}")
    assert concealed.status_code == 403
    assert "Gather the notes" not in concealed.text
