"""Admission parity and fail-closed accounting boundaries, synthetic local state."""

import socket
import sqlite3
from datetime import timedelta

import pytest

from desk.agent_run_schemas import RunAction, RunCreate
from desk.responsibilities import ResponsibilityAction, ResponsibilityCreate
from desk.sources import SourceInput
from desk.store import DomainError
from desk.tasks import TaskInput
from desk.work_capacity import WorkCapacityService
from test_work_capacity import capacity, seed_file, seed_run, watch, world as capacity_world


@pytest.fixture
def world(tmp_path):
    return capacity_world.__wrapped__(tmp_path)


def test_run_same_key_and_cancel_remain_available_at_full(world):
    runtime, session, _, token = world
    owner = {"kind": "owner", "session": token}
    source = runtime.sources.ingest(
        SourceInput(name="selected.txt", format="text"),
        b"selected",
        "selected",
        session_hash=session,
    )["source"]
    payload = RunCreate(
        goal="Summarize the selected source",
        retain=True,
        source_ids=[source["id"]],
        scope_revision=runtime.agent_runs.scope(owner)["scope_revision"],
    )
    original = runtime.agent_runs.create(payload, "original-run", owner)["run"]
    for i in range(99):
        seed_run(world, i)
    assert capacity(world)["runs"]["count"]["remaining"] == 0
    with pytest.raises(DomainError, match="RUN_LIMIT_REACHED"):
        runtime.agent_runs.create(payload, "new-run", owner)
    assert runtime.agent_runs.create(payload, "original-run", owner)["run"]["id"] == original["id"]
    runtime.agent_runs.action(
        original["id"],
        RunAction(action="cancel", expected_version=original["version"]),
        "cancel-run",
        owner,
    )
    assert capacity(world)["runs"]["count"]["used"] == 100
    assert runtime.agent_runs.create(payload, "original-run", owner)["run"]["state"] == "cancelled"


def test_watch_same_key_cancel_and_terminal_retention_at_full(world):
    runtime, _, clock, token = world
    owner = {"kind": "owner", "session": token}
    task = runtime.tasks.create(TaskInput(title="Synthetic selected task"), "selected-task")["task"]
    scope = runtime.responsibilities.scope(owner, [task["id"]], ["status"])
    payload = ResponsibilityCreate(
        title="Synthetic watch",
        kind="selected_task_changes",
        task_ids=[task["id"]],
        fields=["status"],
        scope_revision=scope["scope_revision"],
        retain_change_history=True,
        expires_at=clock[0] + timedelta(days=1),
        review_budget=10,
    )
    original = runtime.responsibilities.create(payload, "original-watch", owner)["responsibility"]
    for i in range(19):
        watch(world, i)
    assert capacity(world)["watches"]["count"]["remaining"] == 0
    with pytest.raises(DomainError, match="RESPONSIBILITY_LIMIT"):
        runtime.responsibilities.create(payload, "new-watch", owner)
    assert (
        runtime.responsibilities.create(payload, "original-watch", owner)["responsibility"]["id"]
        == original["id"]
    )
    runtime.responsibilities.action(
        original["id"],
        ResponsibilityAction(action="cancel", expected_version=original["version"]),
        "cancel-watch",
        owner,
    )
    assert capacity(world)["watches"]["count"]["used"] == 20


@pytest.mark.parametrize("length", [65536, 65537])
def test_metadata_byte_guard_exact_boundary(world, length):
    raw = (
        '{"byte_count":1,"padding":"' + "x" * (length - len('{"byte_count":1,"padding":""}')) + '"}'
    )
    assert len(raw.encode()) == length
    seed_file(world, 1, kind="sources")
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE private_files SET metadata=?", (raw,))
    assert capacity(world)["sources"]["bytes"]["used"] == (1 if length == 65536 else None)


@pytest.mark.parametrize(
    "raw", ["{}", '{"hide_private":0}', '{"hide_private":false,"hide_private":true}', "broken"]
)
def test_corrupt_privacy_metadata_is_fail_closed(world, raw):
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE settings SET data=?", (raw,))
    with pytest.raises(DomainError, match="WORK_CAPACITY_UNAVAILABLE"):
        capacity(world)


def test_query_only_rejects_accidental_writes_and_no_provider_network(world, monkeypatch):
    service = WorkCapacityService(world[0])
    original = service._read

    def guarded(conn):
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("UPDATE state SET revision=revision+1")
        return original(conn)

    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected provider/network operation")

    monkeypatch.setattr(service, "_read", guarded)
    monkeypatch.setattr(world[0].text_ai, "generate", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert service.snapshot(session_hash=world[1])["runs"]["count"]["used"] == 0
