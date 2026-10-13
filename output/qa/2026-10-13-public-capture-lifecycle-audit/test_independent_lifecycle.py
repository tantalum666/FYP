"""Independent synthetic lifecycle/source audit, no external networking."""

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import timedelta

import pytest

from desk.agent_run_schemas import RunCreate
from desk.file_store import ImmutableFiles
from desk.store import DomainError, encode
from test_public_captures import world as world, prepare, approve, detail, cancel, reconcile
from test_work_search import hide


def completed(w):
    p = prepare(w)
    approve(w, p)
    w[4].run_one()
    return detail(w, p["capture"]["id"])


def test_exact_metadata_canonical_hash_not_python_equality(world):
    c = completed(world)
    with world[0].store.connection(write=True) as conn:
        row = conn.execute(
            "SELECT metadata FROM private_files WHERE id=?", (c["source_id"],)
        ).fetchone()
        value = json.loads(row[0])
        value["policy_version"] = True
        conn.execute(
            "UPDATE private_files SET metadata=? WHERE id=?", (encode(value), c["source_id"])
        )
    with pytest.raises(DomainError, match="CAPTURE_SOURCE_IDENTITY_INVALID"):
        detail(world, c["id"])


def test_exact_source_sql_bounds_materialized_scalars(world, monkeypatch):
    c = completed(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute(
            "UPDATE private_files SET metadata=? WHERE id=?", ("x" * 2000000, c["source_id"])
        )
    original = world[0].store.connection
    observed = []

    @contextmanager
    def inspected(*args, **kwargs):
        with original(*args, **kwargs) as conn:

            def factory(cursor, row):
                observed.extend(len(v.encode()) for v in row if isinstance(v, str))
                return sqlite3.Row(cursor, row)

            conn.row_factory = factory
            yield conn

    monkeypatch.setattr(world[0].store, "connection", inspected)
    with pytest.raises(DomainError, match="CAPTURE_SOURCE_IDENTITY_INVALID"):
        detail(world, c["id"])
    assert max(observed) < 65537, max(observed)


@pytest.mark.parametrize("window", ["temporary", "double_link", "single_link"])
def test_unknown_evidence_never_repaired(world, monkeypatch, window):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    original_unlink = os.unlink

    def fail_unlink(path, *args, **kwargs):
        if str(path).endswith(".pending"):
            raise OSError("fixture cleanup failure")
        return original_unlink(path, *args, **kwargs)

    if window == "double_link":
        monkeypatch.setattr(os, "unlink", fail_unlink)
    else:

        def phase(self, name, row):
            if name == ("temp_synced" if window == "temporary" else "linked"):
                raise OSError("fixture interrupted publication")

        monkeypatch.setattr(ImmutableFiles, "phase", phase)
    world[4].run_one()
    directory = world[0].store.directory / "sources"
    before = {
        p.name: (p.stat().st_ino, p.stat().st_nlink, p.read_bytes()) for p in directory.iterdir()
    }
    assert before
    result = reconcile(world, cid)
    after = {
        p.name: (p.stat().st_ino, p.stat().st_nlink, p.read_bytes()) for p in directory.iterdir()
    }
    assert before == after
    assert result["verification"] == (
        "source_verified" if window == "single_link" else "source_unknown"
    )
    assert len(world[5].requests) == 1
    assert not world[4].run_one()


def test_unpublished_cleanup_failure_retained_and_counted(world, monkeypatch):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    monkeypatch.setattr(
        ImmutableFiles,
        "phase",
        lambda self, name, row: cancel(world, cid) if name == "temp_synced" else None,
    )
    original = os.unlink

    def fail(path, *args, **kwargs):
        if str(path).endswith(".pending"):
            raise OSError("fixture cleanup failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", fail)
    world[4].run_one()
    assert detail(world, cid)["state"] == "cancelled"
    assert reconcile(world, cid)["verification"] == "source_unknown"
    assert len(list((world[0].store.directory / "sources").iterdir())) == 1
    with world[0].store.connection() as conn:
        assert (
            conn.execute("SELECT count(*) FROM private_files WHERE kind='sources'").fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("boundary", ["before", "after", "temp_synced", "linked"])
@pytest.mark.parametrize("change", ["privacy", "session", "rollback"])
def test_worker_epoch_and_time_fences(world, monkeypatch, boundary, change):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)

    def revoke():
        if change == "privacy":
            hide(world, True)
            hide(world, False)
        elif change == "session":
            with world[0].store.connection(write=True) as conn:
                conn.execute("DELETE FROM sessions")
        else:
            world[2][0] -= timedelta(seconds=1)

    if boundary in {"before", "after"}:
        setattr(world[5], boundary, revoke)
    else:
        monkeypatch.setattr(
            ImmutableFiles, "phase", lambda self, name, row: revoke() if name == boundary else None
        )
    world[4].run_one()
    with world[0].store.connection() as conn:
        row = conn.execute(
            "SELECT state,source_id,dispatch_possible FROM public_captures WHERE id=?", (cid,)
        ).fetchone()
    assert row["state"] in {"failed", "unknown"}
    assert row["source_id"] is None
    assert len(world[5].requests) == (0 if boundary == "before" else 1)
    assert bool(row["dispatch_possible"]) == (boundary != "before")


def test_capture_explicit_selection_ordinary_work_and_disk_readback(world):
    c = completed(world)
    runtime = world[0]
    owner = {"kind": "owner", "session": world[3]}
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM agent_runs").fetchone()[0] == 0
    run = runtime.agent_runs.create(
        RunCreate(
            goal="Compile the selected public static evidence",
            retain=True,
            source_ids=[c["source_id"]],
            scope_revision=runtime.agent_runs.scope(owner)["scope_revision"],
        ),
        "audit-work",
        owner,
    )["run"]
    for _ in range(30):
        runtime.agent_runs.advance_one()
        world[2][0] += timedelta(seconds=2)
        result = runtime.agent_runs.detail(run["id"], owner)
        if result["run"]["state"] in {"succeeded", "partial", "blocked"}:
            break
    assert result["run"]["state"] == "succeeded"
    assert result["run"]["model_calls"] == 0
    assert len(result["artifacts"]) == 2
    for artifact in result["artifacts"]:
        row, body = runtime.artifacts.download(artifact["id"], session_hash=world[1])
        filename = ImmutableFiles.filename(row)
        actual = (runtime.store.directory / "artifacts" / filename).read_bytes()
        assert actual == body
        assert hashlib.sha256(actual).hexdigest() == row["sha256"]
        assert row["verification"] == "byte_readback"
    assert len(world[5].requests) == 1


def test_exact_200_history_600_receipts_noop_recovery(world):
    first = None
    for i in range(200):
        p = prepare(world, f"prepare-{i}")
        if first is None:
            first = p
        approve(world, p, f"approve-{i}")
        cancel(world, p["capture"]["id"], f"cancel-{i}")
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM public_captures").fetchone()[0] == 200
        assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 600
    assert prepare(world, "prepare-0")["capture"]["state"] == "cancelled"
    assert approve(world, first, "approve-0")["capture"]["state"] == "cancelled"
    assert approve(world, first, "different-approve")["capture"]["state"] == "cancelled"
    assert (
        cancel(world, first["capture"]["id"], "different-cancel")["capture"]["state"] == "cancelled"
    )
    with pytest.raises(DomainError, match="CAPTURE_HISTORY_LIMIT"):
        prepare(world, "overflow")
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        prepare(world, "prepare-0", label="different")
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 600
    assert not world[5].requests


def test_receipt_sql_bounds_materialized_scalars(world, monkeypatch):
    prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("PRAGMA ignore_check_constraints=ON")
        conn.execute(
            "UPDATE public_capture_operations SET request_hash=? WHERE operation_key='prepare'",
            ("x" * 2000000,),
        )
    original = world[0].store.connection
    observed = []

    @contextmanager
    def inspected(*args, **kwargs):
        with original(*args, **kwargs) as conn:

            def factory(cursor, row):
                observed.extend(len(v.encode()) for v in row if isinstance(v, str))
                return sqlite3.Row(cursor, row)

            conn.row_factory = factory
            yield conn

    monkeypatch.setattr(world[0].store, "connection", inspected)
    with pytest.raises(DomainError):
        prepare(world)
    assert max(observed) < 8193, max(observed)


@pytest.mark.parametrize("operation", ["approve", "cancel", "reconcile"])
def test_same_receipt_conflict_before_unknown_target(world, operation):
    prepare(world)
    payload = {"expected_version": 1}
    if operation == "approve":
        payload.update(intent_hash="0" * 64, public_only=True, retain_snapshot=True)
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        getattr(world[4], operation)("not-an-id", payload, "prepare", session_hash=world[1])


def test_hidden_corrupt_private_json_list_restart_stop(world):
    from desk.public_captures import PublicCaptureService

    p = prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE public_captures SET intent_json='broken',acquisition_json='broken'")
    hide(world, True)
    safe = world[4].listing(session_hash=world[1], metadata_only=True)["captures"][0]
    assert set(safe) == {
        "id",
        "state",
        "version",
        "created_at",
        "updated_at",
        "expires_at",
        "dispatch_possible",
        "error_code",
        "cancel_available",
    }
    assert cancel(world, p["capture"]["id"])["capture"]["state"] == "cancelled"
    replacement = PublicCaptureService(world[0], enabled=False)
    assert (
        replacement.detail(p["capture"]["id"], session_hash=world[1], metadata_only=True)[
            "capture"
        ]["state"]
        == "cancelled"
    )


@pytest.mark.parametrize("kind", ["list", "detail", "reconcile"])
def test_response_rechecks_real_session_after_projection(world, monkeypatch, kind):
    c = completed(world)
    original = world[4]._projection

    def revoke(*args):
        result = original(*args)
        with world[0].store.connection(write=True) as conn:
            conn.execute("DELETE FROM sessions")
        return result

    monkeypatch.setattr(world[4], "_projection", revoke)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        if kind == "list":
            world[4].listing(session_hash=world[1])
        elif kind == "detail":
            detail(world, c["id"])
        else:
            world[4].reconcile(
                c["id"], {"expected_version": c["version"]}, "reconcile", session_hash=world[1]
            )


@pytest.mark.parametrize("remaining", [27, 28, 29])
def test_exact_source_byte_capacity_at_reservation(world, remaining):
    from test_work_search import seed_file
    from desk.work_limits import SOURCE_BYTES, SOURCE_TOTAL_BYTES

    for i in range(63):
        seed_file(world, 1000 + i, kind="sources", data={"byte_count": SOURCE_BYTES})
    seed_file(world, 1100, kind="sources", data={"byte_count": SOURCE_BYTES - remaining})
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    c = detail(world, p["capture"]["id"])
    assert len(world[5].requests) == 1
    if remaining < 28:
        assert c["state"] == "unknown" and c["source_id"] is None
        assert c["error_code"] == "CAPTURE_SOURCE_CAPACITY_LIMIT"
    else:
        assert c["state"] == "verified"
        assert reconcile(world, c["id"])["verification"] == "source_verified"
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM private_files WHERE kind='sources'").fetchone()[
            0
        ] == 64 + (remaining >= 28)
        used = conn.execute(
            "SELECT sum(json_extract(metadata,'$.byte_count')) FROM private_files WHERE kind='sources'"
        ).fetchone()[0]
        assert used == SOURCE_TOTAL_BYTES - remaining + (28 if remaining >= 28 else 0)


def test_same_source_operation_full_quota_and_corrupt_unrelated_bucket(world):
    from test_work_search import seed_file

    c = completed(world)
    service = world[4]
    with world[0].store.connection() as conn:
        row = service._row(conn, c["id"], private=True)
        intent = service._intent(row)
        acquisition = service._acquisition(row, intent)
    for i in range(99):
        seed_file(world, 2000 + i, kind="sources")
    seed_file(world, 4000, kind="artifacts", data={"byte_count": True})
    result = world[0].sources.ingest_public_capture(
        intent=intent,
        acquisition=acquisition,
        body=b"Do not omit this qualifier.\n",
        key=f"capture:{c['id']}:source:v1",
        session_hash=world[1],
        checkpoint=lambda conn: None,
    )
    assert result["source"]["id"] == c["source_id"]
    assert result["source"]["status"] == "verified"
    with world[0].store.connection() as conn:
        assert (
            conn.execute("SELECT count(*) FROM private_files WHERE kind='sources'").fetchone()[0]
            == 100
        )
    assert len(world[5].requests) == 1


def test_cancel_after_link_not_automatically_verified(world, monkeypatch):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    monkeypatch.setattr(
        ImmutableFiles,
        "phase",
        lambda self, name, row: cancel(world, cid) if name == "linked" else None,
    )
    world[4].run_one()
    c = detail(world, cid)
    assert c["state"] == "cancelled"
    assert c["source_status"] == "unknown"
    assert reconcile(world, cid)["verification"] == "source_verified"


def test_dispatch_possible_not_actual_get_and_no_replay(world):
    from types import SimpleNamespace

    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)

    def interrupted(url, checkpoint, *, on_dispatch, deadline):
        checkpoint()
        on_dispatch()
        raise OSError("fixture before GET")

    world[4].client = SimpleNamespace(fetch=interrupted)
    world[4].run_one()
    c = detail(world, cid)
    assert c["dispatch_possible"] and c["state"] == "unknown"
    assert not world[5].requests
    assert not world[4].run_one()
    assert reconcile(world, cid)["verification"] == "no_final_source"


def test_verified_state_requires_acquisition_and_source_identity(world):
    p = prepare(world)
    cid = p["capture"]["id"]
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE public_captures SET state='verified' WHERE id=?", (cid,))
    with pytest.raises(DomainError):
        detail(world, cid)


def test_hide_show_after_link_requires_new_owner_reconcile(world, monkeypatch):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)

    def phase(self, name, row):
        if name == "linked":
            hide(world, True)
            hide(world, False)

    monkeypatch.setattr(ImmutableFiles, "phase", phase)
    world[4].run_one()
    c = detail(world, cid)
    assert c["state"] == "unknown" and c["source_status"] == "unknown"
    assert reconcile(world, cid)["verification"] == "source_verified"
    assert len(world[5].requests) == 1


@pytest.mark.parametrize("key", ["é" * 100, "key\x00tail"])
def test_invalid_receipt_key_rejected_before_persistence_or_recoverable(world, key):
    try:
        p = prepare(world, key)
    except DomainError:
        with world[0].store.connection() as conn:
            assert conn.execute("SELECT count(*) FROM public_captures").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 0
    else:
        assert prepare(world, key)["capture"]["id"] == p["capture"]["id"]
        assert cancel(world, p["capture"]["id"])["capture"]["state"] == "cancelled"


@pytest.mark.parametrize("table,column", [("settings", "version"), ("personal_settings", "epoch")])
def test_authority_sql_bounds_corrupt_integer_scalars(world, monkeypatch, table, column):
    with world[0].store.connection(write=True) as conn:
        conn.execute(f"UPDATE {table} SET {column}=? WHERE id=1", ("x" * 2000000,))
    original = world[0].store.connection
    observed = []

    @contextmanager
    def inspected(*args, **kwargs):
        with original(*args, **kwargs) as conn:

            def factory(cursor, row):
                observed.extend(len(v.encode()) for v in row if isinstance(v, str))
                return sqlite3.Row(cursor, row)

            conn.row_factory = factory
            yield conn

    monkeypatch.setattr(world[0].store, "connection", inspected)
    with pytest.raises(DomainError, match="CAPTURE_AUTHORITY_UNAVAILABLE"):
        world[4].capabilities(session_hash=world[1])
    assert max(observed, default=0) < 8193, max(observed, default=0)
