import pytest

from desk.app import create_app
from desk.jobs import JobInput
from desk.store import DomainError
from test_computer_jobs import approve


def fixture_jobs(tmp_path):
    jobs = create_app(tmp_path, password="fixture", scheduler=False).state.runtime.jobs
    jobs.desktop.status = lambda: {"enabled": True, "ready": True}
    return jobs


def prepare(jobs):
    return jobs.prepare(
        JobInput(
            action="linux_note_preview",
            title="Synthetic",
            content="中文 $HOME <script>not code</script>\n",
        ),
        "prepare",
    )["job"]


def test_linux_workflow_is_not_enabled_by_default(tmp_path):
    jobs = create_app(tmp_path, password="fixture", scheduler=False).state.runtime.jobs
    with pytest.raises(DomainError, match="LINUX_DESKTOP_UNAVAILABLE"):
        prepare(jobs)
    assert not jobs.desktop.root.exists()


def test_same_approval_queue_and_independent_file_and_app_evidence(tmp_path):
    jobs = fixture_jobs(tmp_path)

    def bridge(request, checkpoint):
        checkpoint()
        (jobs.desktop.root / (request["artifact_id"] + ".txt")).write_text(request["content"])
        return {"editor_saved": True, "browser_text_matches": True}

    jobs.desktop.run_bridge = bridge
    job = prepare(jobs)
    jobs.run_one()
    assert not jobs.desktop.root.exists()
    approve(jobs, job)
    jobs.run_one()
    done = jobs.detail(job["id"])
    assert done["state"] == "succeeded"
    assert done["result"]["apps_verified"] == ["mousepad", "chromium"]
    assert (
        jobs.desktop.root / (job["id"] + ".txt")
    ).read_text() == "中文 $HOME <script>not code</script>\n"
    check = jobs.prepare(
        JobInput(action="verify_linux_file", title="Check", source_job_id=job["id"]), "check"
    )["job"]
    approve(jobs, check, "approve-check")
    jobs.run_one()
    assert jobs.detail(check["id"])["state"] == "succeeded"
    assert len(list(jobs.desktop.root.glob("*.txt"))) == 1


def test_incomplete_gui_cannot_be_reported_as_success_even_if_file_exists(tmp_path):
    jobs = fixture_jobs(tmp_path)

    def bridge(request, checkpoint):
        (jobs.desktop.root / (request["artifact_id"] + ".txt")).write_text(request["content"])
        return {"editor_saved": True, "browser_text_matches": False}

    jobs.desktop.run_bridge = bridge
    job = prepare(jobs)
    approve(jobs, job)
    jobs.run_one()
    assert jobs.detail(job["id"])["state"] == "unknown"
    assert jobs.reconcile(job["id"])["job"]["result"]["reason"] == "workflow_incomplete"


def test_cancellation_after_reservation_does_not_claim_no_side_effect(tmp_path):
    jobs = fixture_jobs(tmp_path)

    def bridge(request, checkpoint):
        jobs.cancel(request["artifact_id"], "cancel")
        checkpoint()

    jobs.desktop.run_bridge = bridge
    job = prepare(jobs)
    approve(jobs, job)
    jobs.run_one()
    assert jobs.detail(job["id"])["state"] == "unknown"
    assert (jobs.desktop.root / (job["id"] + ".txt")).exists()


def test_linux_symlink_collision_keeps_outside_file_unchanged(tmp_path):
    jobs = fixture_jobs(tmp_path)
    job = prepare(jobs)
    approve(jobs, job)
    jobs.desktop.root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("Preserve")
    (jobs.desktop.root / (job["id"] + ".txt")).symlink_to(outside)
    jobs.run_one()
    assert jobs.detail(job["id"])["error"] == "COMPUTER_TARGET_EXISTS"
    assert outside.read_text() == "Preserve"
