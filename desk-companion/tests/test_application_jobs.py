"""Service boundary tests use a fake bridge; real app evidence is recorded separately."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.application_models import ApplicationJobInput, CellEdit, SourceReference
from desk.application_executor import formula, pdf_matches, validate_application_request
from desk.jobs import JobApproval
from desk.permissions import PermissionChange
from desk.store import DomainError
from desk.tasks import TaskInput, TaskAction


class FakeBridge:
    configured = True

    def __init__(self, root):
        self.root = root
        self.before_return = None
        self.edits = 0

    def run(self, payload, checkpoint=lambda: None, cancel_file=None):
        del cancel_file
        path = self.root / payload["path"]
        if payload["mode"] == "inspect":
            return json.loads(path.read_text())
        self.edits += 1
        previous = (
            json.loads((self.root / payload["source"]).read_text())
            if payload.get("source")
            else {"sheets": []}
        )
        cells = {(s["sheet"], c["cell"]): c for s in previous["sheets"] for c in s["cells"]}
        for sheet in payload["step"]["sheets"]:
            for edit in sheet["cells"]:
                value = edit["value"]
                cells[sheet["sheet"], edit["cell"]] = {
                    "cell": edit["cell"],
                    "kind": "TEXT" if edit["kind"] == "text" else "VALUE",
                    "formula": str(value),
                    "text": str(value),
                    "value": 0 if edit["kind"] == "text" else value,
                    "error": 0,
                }
        snapshot = {
            "application": "libreoffice_calc",
            "visible": True,
            "operation_id": payload["operation_id"],
            "sheets": [
                {"sheet": name, "cells": [c for (s, _), c in cells.items() if s == name]}
                for name in sorted({s for s, _ in cells})
            ],
        }
        path.write_text(json.dumps(snapshot))
        if self.before_return:
            self.before_return()
        checkpoint()
        return snapshot


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_APPLICATION_ENABLED", "1")
    app = create_app(tmp_path / "state", password="fixture", scheduler=False)
    runtime = app.state.runtime
    runtime.jobs.applications.bridge = FakeBridge(runtime.jobs.applications.root)
    runtime.jobs.applications.sources.bridge = runtime.jobs.applications.bridge
    task = runtime.tasks.create(
        TaskInput(title="Fictional app task", follow_up_enabled=False), "task"
    )["task"]
    return runtime, task


def payload(task, source=None, filename="budget.xlsx", value="Initial"):
    return ApplicationJobInput(
        title="Update budget",
        task_id=task["id"],
        task_version=task["version"],
        stage="budget",
        step={
            "kind": "workbook",
            "filename": filename,
            "source_job_id": source,
            "sheets": [
                {"sheet": "Budget", "cells": [{"cell": "A1", "kind": "text", "value": value}]}
            ],
        },
    )


def approve(jobs, job, key):
    review = jobs.detail(job["id"], review=True)
    jobs.approve(
        job["id"],
        JobApproval(expected_version=review["version"], intent_hash=review["intent_hash"]),
        key,
    )


def complete(runtime, task, key="initial", **kwargs):
    job = runtime.jobs.prepare(payload(task, **kwargs), key)["job"]
    approve(runtime.jobs, job, key + "-approve")
    runtime.jobs.run_one()
    result = runtime.jobs.detail(job["id"], review=True)
    assert result["state"] == "succeeded"
    return result


def test_real_queue_requires_approval_and_keeps_prior_versions(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    job = runtime.jobs.prepare(payload(task), "prepare")["job"]
    runtime.jobs.run_one()
    assert not runtime.jobs.applications.root.exists()
    approve(runtime.jobs, job, "approve")
    runtime.jobs.run_one()
    original = runtime.jobs.application_download(job["id"])[1]
    update = complete(runtime, task, key="update", source=job["id"], value="Revised")
    assert runtime.jobs.application_download(job["id"])[1] == original
    assert runtime.jobs.application_download(update["id"])[1] != original
    state = runtime.jobs.application_state(task["id"])
    assert len(state["stages"]) == len(state["artifacts"]) == 1
    assert state["stages"][0]["job_id"] == update["id"]
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "todo"
    assert "readback" not in runtime.jobs.detail(update["id"])["result"]


def test_published_result_survives_lost_ack_and_restart_without_reexecution(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    job = runtime.jobs.prepare(payload(task), "lost")["job"]
    executor = runtime.jobs.applications
    original = executor.execute

    def lose_ack(request, checkpoint):
        original(request, checkpoint)
        raise ConnectionError("Lost completion acknowledgment")

    executor.execute = lose_ack
    approve(runtime.jobs, job, "approve")
    runtime.jobs.run_one()
    assert runtime.jobs.detail(job["id"])["state"] == "unknown"
    request = runtime.jobs.detail(job["id"], review=True)["request"]
    path = executor.target(request)
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    restarted = create_app(tmp_path / "state", password="fixture", scheduler=False).state.runtime
    bridge = FakeBridge(restarted.jobs.applications.root)
    restarted.jobs.applications.bridge = bridge
    result = restarted.jobs.reconcile(job["id"])
    assert result["job"]["state"] == "succeeded"
    assert bridge.edits == 0 and (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert len(restarted.jobs.listing()) == 1


def test_cancel_during_staging_does_not_publish(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    job = runtime.jobs.prepare(payload(task), "cancel")["job"]
    approve(runtime.jobs, job, "approve")
    executor = runtime.jobs.applications
    executor.bridge.before_return = lambda: runtime.jobs.cancel(job["id"], "stop")
    runtime.jobs.run_one()
    result = runtime.jobs.detail(job["id"], review=True)
    assert result["state"] == "cancelled" and not executor.target(result["request"]).exists()


def test_source_change_and_artifact_change_reject_obsolete_work(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    source = inputs / "rates.csv"
    source.write_text("USD,7.80\n")
    runtime.jobs.applications.sources.root = inputs
    p = payload(task)
    p.sources = [
        SourceReference(
            source_id="rates.csv", sha256=hashlib.sha256(source.read_bytes()).hexdigest()
        )
    ]
    job = runtime.jobs.prepare(p, "source")["job"]
    approve(runtime.jobs, job, "approve")
    source.write_text("USD,7.90\n")
    runtime.jobs.run_one()
    assert runtime.jobs.detail(job["id"])["error"] == "APPLICATION_SOURCE_CHANGED"
    first = complete(runtime, task, key="file")
    runtime.jobs.applications.target(first["request"]).write_text("External change")
    with pytest.raises(DomainError, match="APPLICATION_ARTIFACT_CHANGED"):
        runtime.jobs.prepare(payload(task, source=first["id"], value="Later"), "stale")


def test_revocation_and_stale_task_stop_queued_application_work(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    runtime.permissions.change(PermissionChange(mode="full", expected_version=1), "full")
    grant = runtime.permissions.capture(
        {"kind": "owner", "session": runtime.store.create_owner_session()}, task["id"]
    )
    reply = runtime.jobs.prepare(payload(task), "draft")
    runtime.permissions.apply_reply(reply, grant)
    runtime.permissions.change(PermissionChange(mode="ask", expected_version=2), "revoke")
    runtime.jobs.run_one()
    assert runtime.jobs.detail(reply["job"]["id"])["error"] == "PERMISSION_CHANGED"
    assert runtime.jobs.application_state(task["id"])["stages"][0]["error"] == "PERMISSION_CHANGED"
    second = runtime.jobs.prepare(payload(task), "new")["job"]
    approve(runtime.jobs, second, "manual")
    runtime.tasks.action(
        task["id"],
        TaskAction(action="note", expected_version=task["version"], note="Changed request"),
        "changed",
    )
    runtime.jobs.run_one()
    assert runtime.jobs.detail(second["id"])["error"] == "JOB_TASK_CHANGED"
    assert not runtime.jobs.applications.root.exists()


def test_backup_preserves_typed_intents_but_not_execution_authority(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    first = complete(runtime, task)
    pending = runtime.jobs.prepare(payload(task, source=first["id"], value="Next"), "pending")[
        "job"
    ]
    approve(runtime.jobs, pending, "queue")
    bundle = runtime.jobs.validate_backup(runtime.jobs.export())
    assert len(bundle["jobs"]) == 2
    original = runtime.jobs.detail(pending["id"], review=True)["request"]
    for field, value in [
        ("dependencies", "wrong"),
        ("base", {"filename": "../outside"}),
        ("scope", "applications:bad"),
    ]:
        with pytest.raises(ValueError):
            validate_application_request({**original, field: value})
    bad = json.loads(json.dumps(original))
    bad["dependencies"][0]["job_id"] = "f" * 32
    with pytest.raises(ValueError):
        validate_application_request(bad)
    restored = create_app(tmp_path / "restored", password="fixture", scheduler=False).state.runtime
    with restored.store.connection(write=True) as conn:
        restored.jobs.restore(conn, bundle)
    assert restored.jobs.detail(pending["id"])["state"] == "review"
    with restored.store.connection() as conn:
        assert all(
            row["approved_by"] is None and row["run_id"] is None
            for row in conn.execute("SELECT approved_by,run_id FROM computer_jobs")
        )


@pytest.mark.parametrize(
    "value",
    ['=WEBSERVICE("https://example.invalid")', "=SUM(A1:A999)", '=HYPERLINK("file:///etc/passwd")'],
)
def test_external_or_unbounded_formulas_are_not_application_commands(value):
    with pytest.raises(ValidationError):
        CellEdit(cell="A1", kind="formula", value=value)


def test_source_symlinks_and_paired_requests_cannot_gain_application_access(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("Do not expose")
    (inputs / "reference.txt").symlink_to(outside)
    runtime.jobs.applications.sources.root = inputs
    with pytest.raises(DomainError):
        runtime.jobs.applications.sources.listing()
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        runtime.assistant.tool("application_sources", {}, "paired", allow_memory=False)
    with pytest.raises(ValidationError):
        payload(task, filename="../outside.xlsx")


def test_owner_http_download_rejects_anonymous_and_changed_history(tmp_path, monkeypatch):
    runtime, task = setup(tmp_path, monkeypatch)
    first = complete(runtime, task)
    app = create_app(tmp_path / "state", password="fixture", scheduler=False)
    client = TestClient(app)
    assert client.get(f"/api/computer/jobs/{first['id']}/artifact").status_code == 403
    assert (
        client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "fixture"},
        ).status_code
        == 200
    )
    result = client.get(f"/api/computer/jobs/{first['id']}/artifact")
    assert (
        result.status_code == 200
        and 'filename="budget.xlsx"' in result.headers["content-disposition"]
    )
    archive = app.state.runtime.jobs.applications.root / "history" / first["id"] / "budget.xlsx"
    archive.write_text("Changed")
    assert client.get(f"/api/computer/jobs/{first['id']}/artifact").status_code == 409


def test_application_execution_is_disabled_until_operator_connects_it(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_APPLICATION_ENABLED", raising=False)
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    task = runtime.tasks.create(
        TaskInput(title="Application request", follow_up_enabled=False), "task"
    )["task"]
    with pytest.raises(DomainError, match="APPLICATION_UNAVAILABLE"):
        runtime.jobs.prepare(payload(task), "disabled")
    assert runtime.jobs.listing() == [] and not runtime.jobs.applications.root.exists()


def test_xlsx_sheet_canonicalization_preserves_anchors_and_quoted_content():
    assert formula('=IF($Summary.B1="colour";SUM($A$2:A3);0)') == formula(
        '=if(Summary!B1="colour",sum($A$2:A3),0)'
    )
    assert formula("=Summary.$A$1") != formula("=Summary.A1")
    assert formula('=IF(A1="a b";1;0)') != formula('=IF(A1="AB";1;0)')


def test_pdf_readback_requires_all_content_in_order_and_exact_receipt():
    operation = "a" * 32
    readback = {
        "info": "Subject: Desk Companion operation " + operation,
        "text": "Task Owner\nT02 Voice candidate\nreview A\n25\n",
    }
    expected = ["Task", "Owner", "T02 Voice candidate review", "A", "25"]
    assert pdf_matches(readback, expected, operation)
    assert not pdf_matches(
        {**readback, "text": readback["text"].replace("25", "125")}, expected, operation
    )
    assert not pdf_matches(readback, expected[:-1], operation)
    assert not pdf_matches(readback, expected[::-1], operation)
    assert not pdf_matches(readback, expected, "b" * 32)
