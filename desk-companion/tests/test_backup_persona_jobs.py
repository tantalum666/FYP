"""Persona text and computer jobs travel in the business backup. Run tokens do not."""

import json
from datetime import UTC, datetime

import pytest

from desk.access import digest
from desk.exchange import BackupInput, ImportApply
from desk.persona import PersonaRevision
from desk.jobs import JobInput, FolderNaming
from desk.computer import LocalNotesExecutor
from desk.runtime import Runtime
from desk.store import DomainError, Store, encode


def _runtime(tmp_path):
    return Runtime(
        Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))
    )


def _job(conn, job_id, state, run_id=None):
    now = "2026-10-27T00:00:00+00:00"
    request = JobInput(title="Notes", content="hello note").model_dump()
    request.update(
        artifact_id=job_id, executor=LocalNotesExecutor.identity, scope=LocalNotesExecutor.scope
    )
    conn.execute(
        "INSERT INTO computer_jobs("
        "id, request, intent_hash, state, version, created_at, updated_at, expires_at, run_id"
        ") VALUES(?,?,?,?,1,?,?,?,?)",
        (job_id, encode(request), digest(encode(request)), state, now, now, now, run_id),
    )


def test_backup_restores_persona_and_jobs_without_a_run_token(tmp_path):
    source = _runtime(tmp_path / "source")
    source.persona.replace(PersonaRevision(body="Speak briefly.", expected_version=1), "persona")
    with source.store.connection(write=True) as conn:
        _job(conn, "b" * 32, "succeeded")
        _job(conn, "c" * 32, "running", run_id="run-secret-token")
    folder_path = tmp_path / "owner-folder"
    folder_path.mkdir()
    source.jobs.set_folder(FolderNaming(label="Desk", path=str(folder_path)), "folder")
    backup = source.exchange.backup()
    encoded = json.dumps(backup)
    assert "Speak briefly." in encoded and "hello note" in encoded
    assert "run-secret-token" not in encoded
    assert backup["payload"]["job_bundle"]["folder"]["label"] == "Desk"

    restored = _runtime(tmp_path / "restored")
    preview = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "preview")
    applied = restored.exchange.apply(preview["preview_id"], ImportApply(), "apply")
    assert applied["persona_created"] == 1 and applied["jobs_created"] == 2
    assert restored.persona.current()["body"] == "Speak briefly."
    with restored.store.connection() as conn:
        running = conn.execute(
            "SELECT state, run_id FROM computer_jobs WHERE id=?", ("c" * 32,)
        ).fetchone()
        done = conn.execute("SELECT state FROM computer_jobs WHERE id=?", ("b" * 32,)).fetchone()
        folder = conn.execute("SELECT path FROM computer_folder WHERE id=1").fetchone()
    assert running["state"] == "review" and running["run_id"] is None
    assert done["state"] == "succeeded"
    assert folder["path"] == str(folder_path.resolve())
    assert len(restored.jobs.listing(review=True)) == 2
    assert restored.jobs.detail("c" * 32, review=True)["request"]["task_id"] is None

    restored.persona.replace(
        PersonaRevision(body="Keep mine.", expected_version=restored.persona.current()["version"]),
        "local-persona",
    )
    again = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "again")
    second = restored.exchange.apply(again["preview_id"], ImportApply(), "apply-again")
    assert second["persona_kept"] == 1 and second["jobs_kept"] == 2
    assert restored.persona.current()["body"] == "Keep mine."

    legacy = json.loads(json.dumps(backup))
    legacy["payload"].pop("persona_bundle")
    legacy["payload"].pop("job_bundle")
    legacy["sha256"] = digest(encode(legacy["payload"]))
    legacy_preview = restored.exchange.preview_backup(
        BackupInput(content=json.dumps(legacy)), "legacy"
    )
    assert legacy_preview["metadata"]["jobs_count"] == 0
    assert legacy_preview["metadata"]["persona_bundle"]["persona"] is None

    broken = json.loads(json.dumps(backup))
    broken["payload"]["persona_bundle"]["persona"]["source"] = "model"
    broken["sha256"] = digest(encode(broken["payload"]))
    with pytest.raises(DomainError) as caught:
        restored.exchange.preview_backup(BackupInput(content=json.dumps(broken)), "broken")
    assert caught.value.code == "INVALID_BACKUP"
