"""High-risk branches that the existing suite left unexecuted.

These tests follow the current contracts. They do not add product behaviour.
"""

import json
import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.access import digest
from desk.app import create_app
from desk.computer import accept_owner_folder, read_artifact
from desk.exchange import BackupInput, ImportApply, ImportFile
from desk.jobs import JobApproval, JobInput
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventAction, EventInput
from desk.store import DomainError, Store, encode
from desk.tasks import TaskInput


PASSWORD = "fixture-secret"


def _app(tmp_path, monkeypatch=None, clock=None):
    if monkeypatch is not None:
        monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    return create_app(
        tmp_path,
        password=PASSWORD,
        scheduler=False,
        clock=clock,
    )


def _prepare(jobs, key):
    return jobs.prepare(JobInput(title="Fixture note", content="Offline fixture text"), key)["job"]


def _approve(jobs, job, key):
    current = jobs.detail(job["id"], review=True)
    return jobs.approve(
        job["id"],
        JobApproval(expected_version=current["version"], intent_hash=current["intent_hash"]),
        key,
    )["job"]


def test_public_origin_must_be_one_https_origin_and_then_allows_that_host(tmp_path, monkeypatch):
    for value in (
        "http://desk.example",
        "https://desk.example/desk",
        "https://user:secret@desk.example",
        "https://desk.example?token=secret",
    ):
        monkeypatch.setenv("DESK_PUBLIC_ORIGIN", value)
        with pytest.raises(ValueError, match="DESK_PUBLIC_ORIGIN"):
            create_app(tmp_path / uuid4().hex, password=PASSWORD, scheduler=False)
    monkeypatch.setenv("DESK_PUBLIC_ORIGIN", "https://desk.example")
    app = create_app(tmp_path / "ok", password=PASSWORD, scheduler=False)
    with TestClient(app, base_url="https://desk.example") as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_login_lockout_hides_the_password_and_resets(tmp_path, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("desk.app.time.monotonic", lambda: now[0])
    app = _app(tmp_path)
    with TestClient(app) as client:
        client.headers["X-Desk-Request"] = "1"
        for _ in range(9):
            failed = client.post(
                "/api/session", json={"username": "owner", "password": "wrong-password"}
            )
            assert failed.status_code == 401
            assert "wrong-password" not in failed.text
        opened = client.post("/api/session", json={"username": "owner", "password": PASSWORD})
        assert opened.status_code == 200
        assert PASSWORD not in opened.text
        # A successful login clears the counter, so the next failure is not a lockout.
        again = client.post("/api/session", json={"username": "owner", "password": "wrong-password"})
        assert again.status_code == 401
        for _ in range(9):
            client.post("/api/session", json={"username": "owner", "password": "wrong-password"})
        locked = client.post("/api/session", json={"username": "owner", "password": PASSWORD})
        assert locked.status_code == 429
        assert locked.json()["error"]["code"] == "TRY_LATER"
        assert PASSWORD not in locked.text
        now[0] += 61
        recovered = client.post("/api/session", json={"username": "owner", "password": PASSWORD})
        assert recovered.status_code == 200


def test_pairing_attempts_use_the_separate_limiter(tmp_path):
    app = _app(tmp_path)
    with TestClient(app) as client:
        client.headers["X-Desk-Request"] = "1"
        body = {"code": "00000000", "name": "Fixture display"}
        for _ in range(8):
            response = client.post("/api/pairing/requests", json=body)
            assert response.status_code == 410
            assert response.json()["error"]["code"] == "PAIRING_EXPIRED"
            assert "00000000" not in response.text
        blocked = client.post("/api/pairing/requests", json=body)
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "TRY_LATER"


def test_session_expires_at_eight_hours_and_logout_keeps_other_sessions(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    store = _app(tmp_path, clock=lambda: clock[0]).state.store
    first = store.authenticate("owner", PASSWORD)
    second = store.authenticate("owner", PASSWORD)
    clock[0] = clock[0] + timedelta(hours=8) - timedelta(microseconds=1)
    assert store.session_valid(first) and store.session_valid(second)
    clock[0] = datetime(2026, 10, 2, tzinfo=UTC) + timedelta(hours=8)
    assert not store.session_valid(first)
    clock[0] = datetime(2026, 10, 2, tzinfo=UTC)
    assert store.session_valid(second)
    store.logout(first)
    assert not store.session_valid(first)
    assert store.session_valid(second)
    with pytest.raises(DomainError) as missing:
        store.operation("", {"type": "noop"}, lambda conn: {})
    with pytest.raises(DomainError) as long:
        store.operation("k" * 101, {"type": "noop"}, lambda conn: {})
    assert missing.value.code == long.value.code == "OPERATION_ID_REQUIRED"


def test_backup_refuses_replacement_tampering_and_expired_previews(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password=PASSWORD, clock=lambda: clock[0]))
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Keep me",
                start_local="2026-10-02T15:00",
                end_local="2026-10-02T16:00",
            )
        ),
        "create",
    )
    backup = runtime.exchange.backup()
    other = Runtime(Store(tmp_path / "other", password=PASSWORD, clock=lambda: clock[0]))
    preview = other.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "preview")
    assert other.exchange.apply(preview["preview_id"], ImportApply(), "restore")["created"] == 1
    changed = json.loads(json.dumps(backup))
    changed["payload"]["events"][0]["title"] = "Replaced"
    changed["sha256"] = digest(encode(changed["payload"]))
    replacement = other.exchange.preview_backup(
        BackupInput(content=json.dumps(changed)), "changed"
    )
    with pytest.raises(DomainError) as refused:
        other.exchange.apply(
            replacement["preview_id"], ImportApply(replace_matching=True), "replace"
        )
    assert refused.value.code == "RESTORE_KEEP_EXISTING"
    with other.store.connection() as conn:
        assert other.store.data(conn)[0][0]["title"] == "Keep me"

    duplicate = json.loads(json.dumps(backup))
    task = {
        "id": "task-1",
        "title": "Fixture",
        "status": "todo",
        "timezone": "Asia/Hong_Kong",
        "next_step": "",
        "waiting_for": "",
        "steps": [],
        "visibility": "private",
        "follow_up_enabled": True,
        "interval_minutes": 1440,
    }
    duplicate["payload"]["task_bundle"] = {"tasks": [task, dict(task)], "evidence": []}
    duplicate["sha256"] = digest(encode(duplicate["payload"]))
    with pytest.raises(DomainError) as bad_tasks:
        other.exchange.preview_backup(BackupInput(content=json.dumps(duplicate)), "dup-tasks")
    assert bad_tasks.value.code == "INVALID_BACKUP"

    unknown = json.loads(json.dumps(backup))
    unknown["payload"]["task_bundle"] = {
        "tasks": [task],
        "evidence": [{"task_id": "missing", "note": "no", "at": "2026-10-02T00:00:00Z"}],
    }
    unknown["sha256"] = digest(encode(unknown["payload"]))
    with pytest.raises(DomainError) as bad_evidence:
        other.exchange.preview_backup(BackupInput(content=json.dumps(unknown)), "bad-evidence")
    assert bad_evidence.value.code == "INVALID_BACKUP"

    oversized = json.loads(json.dumps(backup))
    sample = oversized["payload"]["events"][0]
    oversized["payload"]["events"] = [{**sample, "id": f"e{i:04d}"} for i in range(501)]
    oversized["sha256"] = digest(encode(oversized["payload"]))
    before = other.store.revision()
    with pytest.raises(DomainError) as too_many:
        other.exchange.preview_backup(BackupInput(content=json.dumps(oversized)), "too-many")
    assert too_many.value.code == "INVALID_BACKUP"
    assert other.store.revision() == before

    fresh = other.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "fresh")
    clock[0] += timedelta(minutes=15)
    with pytest.raises(DomainError) as stale:
        other.exchange.apply(fresh["preview_id"], ImportApply(), "late-apply")
    assert stale.value.code == "IMPORT_EXPIRED"


def test_ics_all_day_floating_and_local_exceptions(tmp_path):
    runtime = Runtime(
        Store(tmp_path, password=PASSWORD, clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    )
    all_day = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:allday@example.test
DTSTART;VALUE=DATE:20261002
DTEND;VALUE=DATE:20261003
SUMMARY:All day fixture
END:VEVENT
END:VCALENDAR
"""
    preview = runtime.exchange.preview_ics(
        ImportFile(content=all_day, start=date(2026, 10, 1), end=date(2026, 10, 4)), "all-day"
    )
    assert preview["rows"][0]["event"]["all_day"] is True
    assert preview["rows"][0]["event"]["timezone"] == "Asia/Hong_Kong"

    seconds = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:seconds@example.test
DTSTART;TZID=Asia/Hong_Kong:20261002T150030
DTEND;TZID=Asia/Hong_Kong:20261002T160000
SUMMARY:Seconds
END:VEVENT
END:VCALENDAR
"""
    rounded = runtime.exchange.preview_ics(
        ImportFile(content=seconds, start=date(2026, 10, 1), end=date(2026, 10, 4)), "seconds"
    )
    assert any("rounded to minute" in warning for warning in rounded["warnings"])
    assert rounded["rows"][0]["event"]["start_local"].endswith("T07:00:00")

    floating = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:float@example.test
DTSTART:20261002T150000
DTEND:20261002T160000
SUMMARY:Floating
END:VEVENT
END:VCALENDAR
"""
    floated = runtime.exchange.preview_ics(
        ImportFile(content=floating, start=date(2026, 10, 1), end=date(2026, 10, 4)), "float"
    )
    assert floated["rows"][0]["event"]["start_local"].endswith("T07:00:00")
    assert floated["rows"][0]["event"]["timezone"] == "UTC"

    once = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:once@example.test
DTSTART;TZID=Asia/Hong_Kong:20261002T150000
DTEND;TZID=Asia/Hong_Kong:20261002T160000
SUMMARY:Once
END:VEVENT
END:VCALENDAR
"""
    imported = runtime.exchange.preview_ics(
        ImportFile(content=once, start=date(2026, 10, 1), end=date(2026, 10, 4)), "once"
    )
    runtime.exchange.apply(imported["preview_id"], ImportApply(), "apply-once")
    with runtime.store.connection() as conn:
        saved = runtime.store.data(conn)[0][0]
    runtime.store.event_action(
        saved["id"],
        EventAction(
            action="delete",
            scope="occurrence",
            expected_version=saved["version"],
            occurrence_key=saved["start_local"][:16],
        ),
        "cancel-one",
    )
    changed = runtime.exchange.preview_ics(
        ImportFile(
            content=once.replace("Once", "Renamed"), start=date(2026, 10, 1), end=date(2026, 10, 4)
        ),
        "renamed",
    )
    with pytest.raises(DomainError) as blocked:
        runtime.exchange.apply(changed["preview_id"], ImportApply(replace_matching=True), "replace")
    assert blocked.value.code == "SERIES_HAS_EXCEPTIONS"
    with runtime.store.connection() as conn:
        assert runtime.store.event(conn, saved["id"])["title"] == "Once"


def test_snapshot_and_create_stop_at_the_calendar_caps(tmp_path):
    def clock():
        return datetime(2026, 10, 1, tzinfo=UTC)

    store = Store(tmp_path, password=PASSWORD, clock=clock)
    for index in range(50):
        store.create(
            CreateEvents(
                event=EventInput(
                    title=f"Busy {index}",
                    start_local="2026-10-01T09:00",
                    end_local="2026-10-01T10:00",
                    recurrence={"frequency": "daily"},
                )
            ),
            f"busy-{index}",
        )
    with pytest.raises(DomainError) as narrow:
        store.snapshot(
            datetime(2026, 10, 1, tzinfo=UTC),
            datetime(2026, 10, 1, tzinfo=UTC) + timedelta(days=62),
        )
    assert narrow.value.code == "NARROW_DATE_RANGE"
    with store.connection(write=True) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]
        for index in range(500 - existing):
            conn.execute(
                "INSERT INTO events(id,data,version) VALUES(?,?,1)",
                (f"pad{index}", encode({"title": "pad"})),
            )
    with pytest.raises(DomainError) as limited:
        store.create(
            CreateEvents(
                event=EventInput(
                    title="One more",
                    start_local="2026-10-02T09:00",
                    end_local="2026-10-02T10:00",
                )
            ),
            "one-more",
        )
    assert limited.value.code == "EVENT_LIMIT"


def test_occurrence_keys_reject_offsets_off_days_and_garbage():
    from desk.calendar import is_occurrence

    weekly = {
        "start_local": "2026-10-02T15:00",
        "recurrence": {"frequency": "weekly", "interval": 1, "until": None},
    }
    assert is_occurrence(weekly, "2026-10-09T15:00")
    assert not is_occurrence(weekly, "2026-10-02T15:00+08:00")
    assert not is_occurrence(weekly, "2026-10-02T15:00:00")
    assert not is_occurrence(weekly, "2026-10-03T15:00")
    assert not is_occurrence(weekly, "not-a-date")
    single = {**weekly, "recurrence": {"frequency": "none", "interval": 1, "until": None}}
    assert is_occurrence(single, "2026-10-02T15:00")
    assert not is_occurrence(single, "2026-10-09T15:00")


def test_disabled_follow_up_clears_a_due_check_and_restore_stops_at_500(tmp_path):
    runtime = Runtime(
        Store(tmp_path, password=PASSWORD, clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    )
    created = runtime.tasks.create(TaskInput(title="Fixture task"), "create")["task"]
    with runtime.store.connection(write=True) as conn:
        data = json.loads(conn.execute("SELECT data FROM tasks WHERE id=?", (created["id"],)).fetchone()[0])
        data["follow_up_enabled"] = False
        conn.execute(
            "UPDATE tasks SET data=?, next_check_at=? WHERE id=?",
            (encode(data), "2026-10-01T00:00:00.000000Z", created["id"]),
        )
        conn.execute(
            "INSERT INTO task_quiet_holds VALUES(?,?)",
            (created["id"], "2026-10-02T23:59:00.000000Z"),
        )
    runtime.tasks.tick()
    with runtime.store.connection() as conn:
        row = conn.execute("SELECT next_check_at FROM tasks WHERE id=?", (created["id"],)).fetchone()
        assert row["next_check_at"] is None
        assert conn.execute("SELECT 1 FROM task_quiet_holds WHERE task_id=?", (created["id"],)).fetchone() is None
        assert conn.execute("SELECT COUNT(*) FROM task_followups").fetchone()[0] == 0
    bundle = runtime.tasks.validate_backup(
        {
            "tasks": [
                {
                    "id": "restored-one",
                    "title": "Restored",
                    "status": "todo",
                    "timezone": "Asia/Hong_Kong",
                    "next_step": "",
                    "waiting_for": "",
                    "steps": [],
                    "visibility": "private",
                    "follow_up_enabled": False,
                    "interval_minutes": 1440,
                }
            ],
            "evidence": [],
        }
    )
    with runtime.store.connection(write=True) as conn:
        now = "2026-10-02T00:00:00.000000Z"
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        for index in range(500 - count):
            conn.execute(
                "INSERT INTO tasks VALUES(?,?,1,'todo',0,NULL,?,?)",
                (f"pad{index}", encode({"title": "pad"}), now, now),
            )
        with pytest.raises(DomainError) as limited:
            runtime.tasks.restore(conn, bundle)
    assert limited.value.code == "TASK_LIMIT"


def test_job_caps_unapproved_queue_deadline_and_reconcile(tmp_path, monkeypatch):
    clock = [datetime(2026, 10, 6, 12, tzinfo=UTC)]
    app = _app(tmp_path, monkeypatch, clock=lambda: clock[0])
    jobs, store = app.state.runtime.jobs, app.state.store
    original_verify = jobs.executor.verify
    for index in range(20):
        _prepare(jobs, f"draft-{index}")
    with pytest.raises(DomainError) as drafts:
        _prepare(jobs, "draft-overflow")
    assert drafts.value.code == "TOO_MANY_DRAFTS"
    with store.connection() as conn:
        identifiers = [row["id"] for row in conn.execute("SELECT id FROM computer_jobs")]
    assert len(identifiers) == 20
    for index, job_id in enumerate(identifiers):
        jobs.cancel(job_id, f"cancel-{index}")

    capped = _app(tmp_path / "cap", monkeypatch, clock=lambda: clock[0])
    now = "2026-10-06T12:00:00.000000Z"
    with capped.state.store.connection(write=True) as conn:
        conn.executemany(
            "INSERT INTO computer_jobs(id,request,intent_hash,state,version,created_at,updated_at,expires_at) "
            "VALUES(?,?,?,'succeeded',0,?,?,?)",
            [(uuid4().hex, "{}", "a" * 64, now, now, now) for _ in range(1000)],
        )
    with pytest.raises(DomainError) as limit:
        _prepare(capped.state.runtime.jobs, "over-cap")
    assert limit.value.code == "JOB_LIMIT"

    queued = _prepare(jobs, "unapproved")
    with store.connection(write=True) as conn:
        conn.execute(
            "UPDATE computer_jobs SET state='queued', approved_by=NULL, deadline=? WHERE id=?",
            ("2026-10-06T12:01:00.000000Z", queued["id"]),
        )
    jobs.run_one()
    failed = jobs.detail(queued["id"])
    assert failed["state"] == "failed" and failed["error"] == "COMPUTER_SCOPE_CHANGED"
    assert not jobs.executor.root.exists()

    review = _prepare(jobs, "still-review")

    def refuse_verify(_request):
        raise AssertionError("reconcile must not read a review job")

    jobs.executor.verify = refuse_verify
    assert jobs.reconcile(review["id"])["job"]["state"] == "review"

    approved = _approve(jobs, _prepare(jobs, "deadline"), "approve-deadline")
    original = jobs.executor.execute

    def expire_before_write(request, checkpoint):
        clock[0] = clock[0] + timedelta(seconds=61)
        return original(request, checkpoint)

    jobs.executor.execute = expire_before_write
    jobs.run_one()
    late = jobs.detail(approved["id"])
    assert late["state"] == "failed" and late["error"] == "JOB_DEADLINE_EXCEEDED"
    assert not (jobs.executor.root / (approved["id"] + ".txt")).exists()

    unknown = _prepare(jobs, "unknown-job")
    with store.connection(write=True) as conn:
        conn.execute("UPDATE computer_jobs SET state='unknown' WHERE id=?", (unknown["id"],))
    jobs.executor.root.mkdir(mode=0o700, exist_ok=True)

    def unavailable(_request):
        raise RuntimeError("disk offline")

    jobs.executor.verify = unavailable
    hidden = jobs.reconcile(unknown["id"])["job"]
    assert hidden["state"] == "unknown"
    assert hidden["result"]["reason"] == "verification_unavailable"
    assert "disk offline" not in json.dumps(hidden)

    missing = _prepare(jobs, "missing-file")
    with store.connection(write=True) as conn:
        conn.execute("UPDATE computer_jobs SET state='unknown' WHERE id=?", (missing["id"],))
    jobs.executor.verify = original_verify
    receipt = jobs.reconcile(missing["id"])["job"]
    assert receipt["state"] == "unknown"
    assert receipt["result"]["reason"] == "artifact_missing"


def test_read_artifact_and_folder_path_refuse_unsafe_targets(tmp_path):
    directory = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert read_artifact(directory, "absent.txt", b"x", "id", "scope") == {
            "verified": False,
            "reason": "artifact_missing",
        }
        (tmp_path / "nested").mkdir()
        denied = read_artifact(directory, "nested", b"x", "id", "scope")
        assert denied == {"verified": False, "reason": "target_denied"}
    finally:
        os.close(directory)
    with pytest.raises(DomainError) as nul:
        accept_owner_folder("/tmp/a\x00b", tmp_path)
    with pytest.raises(DomainError) as relative:
        accept_owner_folder("relative/path", tmp_path)
    assert nul.value.code == relative.value.code == "FOLDER_PATH_DENIED"
