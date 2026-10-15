"""The owner-named folder uses the same job contract as the notes adapter."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.jobs import FolderNaming, JobApproval, JobInput
from desk.store import DomainError


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_COMPUTER_ENABLED", raising=False)
    runtime = tmp_path / "runtime"
    drop = tmp_path / "drop"
    drop.mkdir()
    app = create_app(runtime, password="fictional-fixture", scheduler=False)
    jobs = app.state.runtime.jobs
    jobs.set_folder(FolderNaming(label="Sandbox", path=str(drop)), "name-folder")
    return app, jobs, drop, runtime


def prepare(jobs, key="prepare-folder", **kwargs):
    return jobs.prepare(
        JobInput(
            action="save_folder_file",
            title="Fictional drop",
            content="你好 · folder 🦉\n",
            **kwargs,
        ),
        key,
    )["job"]


def approve(jobs, job, key="approve-folder"):
    current = jobs.detail(job["id"], review=True)
    return jobs.approve(
        job["id"],
        JobApproval(expected_version=current["version"], intent_hash=current["intent_hash"]),
        key,
    )["job"]


def test_unconfigured_folder_prepares_nothing_and_notes_stay_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_COMPUTER_ENABLED", raising=False)
    runtime = tmp_path / "runtime"
    jobs = create_app(runtime, password="fictional-fixture", scheduler=False).state.runtime.jobs
    with pytest.raises(DomainError, match="FOLDER_NOT_CONFIGURED"):
        prepare(jobs)
    with pytest.raises(DomainError, match="COMPUTER_DISABLED"):
        jobs.prepare(JobInput(title="Note", content="still off"), "note")
    assert jobs.capabilities()["folder"]["configured"] is False
    assert jobs.capabilities()["actions"] == []
    assert not (runtime / "computer-notes").exists()


def test_rejected_paths_are_not_stored(desk, tmp_path):
    app, jobs, drop, runtime = desk
    inside = runtime / "inbox"
    inside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(drop, target_is_directory=True)
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("nope")
    denied = [
        str(link),
        str(inside),
        str(runtime),
        str(tmp_path),
        "drop",
        str(tmp_path / "missing-folder"),
        str(file_path),
    ]
    for path in denied:
        with pytest.raises(DomainError, match="FOLDER_PATH_DENIED"):
            jobs.set_folder(
                FolderNaming(label="Denied", path=path),
                "denied-" + hashlib.sha256(path.encode()).hexdigest()[:12],
            )
    status = jobs.folder_status()
    assert status["path"] == str(drop.resolve())
    assert status["label"] == "Sandbox"
    with pytest.raises(ValidationError):
        JobInput.model_validate(
            {
                "action": "save_folder_file",
                "title": "Fixture",
                "content": "safe",
                "path": str(drop),
            }
        )


def test_approval_then_independent_readback_and_cancel_before_write(desk):
    _app, jobs, drop, _runtime = desk
    waiting = prepare(jobs, key="cancel-first")
    jobs.cancel(waiting["id"], "cancel-folder")
    jobs.run_one()
    assert jobs.detail(waiting["id"])["state"] == "cancelled"
    assert list(drop.iterdir()) == []

    job = prepare(jobs)
    assert not (drop / (job["id"] + ".txt")).exists()
    review = jobs.detail(job["id"], review=True)
    assert review["request"]["folder_label"] == "Sandbox"
    assert "path" not in review["request"]
    assert str(drop) not in json.dumps(jobs.detail(job["id"]))
    assert str(drop) not in json.dumps(jobs.capabilities())
    approve(jobs, job)
    jobs.run_one()
    done = jobs.detail(job["id"])
    artifact = drop / (job["id"] + ".txt")
    body = artifact.read_bytes()
    assert done["state"] == "succeeded" and done["result"]["verified"]
    assert body == "你好 · folder 🦉\n".encode()
    assert done["result"]["sha256"] == hashlib.sha256(body).hexdigest()
    assert done["result"]["artifact"] == job["id"] + ".txt"
    assert list(drop.iterdir()) == [artifact]
    assert "Fictional drop" not in artifact.read_text()


def test_moving_or_clearing_the_folder_blocks_the_old_intent(desk, tmp_path):
    app, jobs, drop, _runtime = desk
    other = tmp_path / "other"
    other.mkdir()
    job = prepare(jobs)
    jobs.set_folder(FolderNaming(label="Other box", path=str(other)), "move-folder")
    with pytest.raises(DomainError, match="COMPUTER_SCOPE_CHANGED"):
        approve(jobs, job, "approve-moved")
    jobs.run_one()
    assert list(drop.iterdir()) == [] and list(other.iterdir()) == []

    jobs.set_folder(FolderNaming(label="Sandbox", path=str(drop)), "restore-folder")
    again = prepare(jobs, key="prepare-again")
    client = TestClient(app)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": "clear-http"}
    client.post(
        "/api/session",
        headers=headers,
        json={"username": "owner", "password": "fictional-fixture"},
    )
    cleared = client.post("/api/computer/folder/clearance", json={}, headers=headers)
    assert cleared.status_code == 200 and cleared.json()["configured"] is False
    with pytest.raises(DomainError, match="COMPUTER_SCOPE_CHANGED"):
        approve(jobs, again, "approve-cleared")
    assert list(drop.iterdir()) == []


def test_display_cannot_name_the_folder_or_prepare_a_file(desk):
    app, _jobs, drop, _runtime = desk
    client = TestClient(app)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": "display-folder"}
    assert client.get("/api/computer/folder", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/computer/jobs",
            json={"action": "save_folder_file", "title": "A", "content": "B"},
            headers=headers,
        ).status_code
        == 403
    )
    owner = client.post(
        "/api/session",
        headers=headers,
        json={"username": "owner", "password": "fictional-fixture"},
    )
    assert owner.status_code == 200
    named = client.post(
        "/api/computer/folder",
        headers={**headers, "X-Operation-Id": "owner-folder"},
        json={"label": "Renamed", "path": str(drop)},
    )
    assert named.status_code == 200
    assert named.json()["label"] == "Renamed"
    with app.state.store.connection(write=True) as conn:
        conn.execute("DELETE FROM sessions")
    token = None
    owner_client = TestClient(app)
    owner_client.post(
        "/api/session",
        headers={"X-Desk-Request": "1"},
        json={"username": "owner", "password": "fictional-fixture"},
    )
    enrolled = owner_client.post(
        "/api/devices/enrol-display",
        json={"name": "Test display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "enrol-display"},
    )
    token = enrolled.cookies.get("desk_companion_device")
    display = TestClient(app)
    display.headers["Authorization"] = "Bearer " + token
    assert (
        display.post(
            "/api/computer/folder",
            json={"label": "Stolen", "path": str(drop)},
            headers={"X-Desk-Request": "1", "X-Operation-Id": "display-rename"},
        ).status_code
        == 403
    )
    assert app.state.runtime.jobs.folder_status()["label"] == "Renamed"


def test_local_rule_prepares_a_review_and_does_not_write(desk):
    app, jobs, drop, _runtime = desk
    bare = create_app(
        app.state.store.directory.parent / "bare", password="fictional-fixture", scheduler=False
    )
    clarify = bare.state.runtime.assistant.local_message(
        AssistantMessage(message="保存到文件夹：还没指定目录", language="zh"),
        "folder-missing",
    )
    assert clarify["kind"] == "clarify"

    reply = jobs.runtime.assistant.local_message(
        AssistantMessage(message="Save to folder: 你好，沙箱", language="en"),
        "folder-rule",
    )
    assert reply["kind"] == "job"
    job = jobs.detail(reply["job"]["id"], review=True)
    assert job["state"] == "review" and job["request"]["content"] == "你好，沙箱"
    assert list(drop.iterdir()) == []
    approve(jobs, job, "approve-rule")
    jobs.run_one()
    assert (drop / (job["id"] + ".txt")).read_text() == "你好，沙箱"


def test_existing_name_is_left_unchanged(desk):
    _app, jobs, drop, _runtime = desk
    job = prepare(jobs)
    approve(jobs, job)
    victim = drop / (job["id"] + ".txt")
    victim.write_text("keep the existing fixture")
    jobs.run_one()
    assert jobs.detail(job["id"])["error"] == "COMPUTER_TARGET_EXISTS"
    assert victim.read_text() == "keep the existing fixture"


def test_a_folder_replaced_by_a_link_is_not_followed(desk, tmp_path):
    _app, jobs, drop, _runtime = desk
    real = tmp_path / "real-drop"
    real.mkdir()
    job = prepare(jobs, key="prepare-link")
    approve(jobs, job, "approve-link")
    moved = tmp_path / "moved-drop"
    drop.rename(moved)
    drop.symlink_to(real, target_is_directory=True)
    jobs.run_one()
    assert jobs.detail(job["id"])["state"] == "failed"
    assert list(real.iterdir()) == []


def test_ancestor_link_changed_between_validation_and_open_is_not_followed(
    desk, tmp_path, monkeypatch
):
    _app, jobs, _drop, _runtime = desk
    parent = tmp_path / "parent"
    target = parent / "drop"
    target.mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "drop").mkdir(parents=True)
    jobs.set_folder(FolderNaming(label="Original", path=str(target)), "parent-folder")
    job = prepare(jobs, key="ancestor-job")
    approve(jobs, job, "approve-ancestor")
    original = jobs.folder._bound_root

    def changed(request):
        root = original(request)
        parent.rename(tmp_path / "moved-parent")
        parent.symlink_to(outside, target_is_directory=True)
        return root

    monkeypatch.setattr(jobs.folder, "_bound_root", changed)
    jobs.run_one()
    assert jobs.detail(job["id"])["state"] == "failed"
    assert list((outside / "drop").iterdir()) == []


def test_tampered_folder_file_is_reported_and_not_repaired(desk):
    app, jobs, drop, _runtime = desk
    fresh = prepare(jobs, key="prepare-fresh")
    approve(jobs, fresh, "approve-fresh")
    jobs.run_one()
    artifact = drop / (fresh["id"] + ".txt")
    artifact.write_text("edited outside the job")
    verification = jobs.prepare(
        JobInput(action="verify_folder_file", title="Check drop", source_job_id=fresh["id"]),
        "verify-folder",
    )["job"]
    approve(jobs, verification, "approve-verify")
    jobs.run_one()
    assert jobs.detail(verification["id"])["state"] == "unknown"
    checked = jobs.reconcile(verification["id"])["job"]
    assert checked["result"]["reason"] == "content_mismatch"
    assert artifact.read_text() == "edited outside the job"
    assert app.state.runtime.jobs.detail(fresh["id"])["state"] == "succeeded"


def test_restart_runs_only_the_approved_folder_job(desk):
    app, jobs, drop, _runtime = desk
    job = prepare(jobs)
    approve(jobs, job)
    resumed = create_app(
        app.state.store.directory, password="fictional-fixture", scheduler=False
    ).state.runtime.jobs
    resumed.run_one()
    assert resumed.detail(job["id"])["state"] == "succeeded"
    assert (drop / (job["id"] + ".txt")).read_text() == "你好 · folder 🦉\n"
    resumed.run_one()
    assert len(list(drop.iterdir())) == 1
