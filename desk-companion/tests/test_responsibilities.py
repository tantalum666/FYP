"""Real local SQLite/task-change tests; no model, remote or browser claims."""

import csv
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.agent_run_schemas import RunCreate
from desk.app import create_app
from desk.responsibilities import (
    LIMITS,
    ResponsibilityService,
    ResponsibilityCreate,
    ResponsibilityAction,
    ResponsibilityAcknowledge,
)
from desk.runtime import Runtime
from desk.store import DomainError, Store, encode
from desk.tasks import TaskInput, TaskAction


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 10, 13, 12, tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    r.responsibilities = ResponsibilityService(r)
    owner = {"kind": "owner", "session": r.store.authenticate("owner", "fixture-only")}
    return r, owner, clock


def task(world, title="Selected private task"):
    return world[0].tasks.create(TaskInput(title=title), uuid4().hex)["task"]


def create_payload(world, tasks, **changes):
    r, owner, clock = world
    fields = changes.pop("fields", ["status", "due", "progress"])
    ids = [t["id"] for t in tasks]
    data = dict(
        title="Review selected changes",
        kind="selected_task_changes",
        task_ids=ids,
        fields=fields,
        scope_revision=r.responsibilities.scope(owner, ids, fields)["scope_revision"],
        retain_change_history=True,
        expires_at=clock[0] + timedelta(days=30),
        review_budget=100,
        daily_review_budget=20,
    )
    return ResponsibilityCreate(**{**data, **changes})


def enroll(world, tasks, **changes):
    return world[0].responsibilities.create(
        create_payload(world, tasks, **changes), uuid4().hex, world[1]
    )["responsibility"]


def detail(world, watch):
    return world[0].responsibilities.detail(watch["id"], world[1])


def change(world, item, action="note", **changes):
    r = world[0]
    with r.store.connection() as conn:
        current = r.tasks.get(conn, item["id"])
    return r.tasks.action(
        item["id"],
        TaskAction(
            action=action,
            expected_version=current["version"],
            **({"note": "A private progress note"} if action == "note" else {}),
            **changes,
        ),
        uuid4().hex,
    )["task"]


def update(world, item, **changes):
    with world[0].store.connection() as conn:
        old = world[0].tasks.get(conn, item["id"])
    values = {k: old[k] for k in TaskInput.model_fields}
    return change(world, item, "update", task=TaskInput(**{**values, **changes}))


def control(world, watch, action, **changes):
    current = detail(world, watch)["responsibility"]
    return world[0].responsibilities.action(
        watch["id"],
        ResponsibilityAction(action=action, expected_version=current["version"], **changes),
        uuid4().hex,
        world[1],
    )["responsibility"]


def acknowledge(world, watch, review=None, key=None):
    review = review or detail(world, watch)["reviews"][0]
    return world[0].responsibilities.acknowledge(
        watch["id"],
        review["id"],
        ResponsibilityAcknowledge(expected_review_version=review["version"]),
        key or uuid4().hex,
        world[1],
    )


def rows(world, table):
    assert table in {
        "responsibility_sources",
        "responsibility_reviews",
        "responsibility_operations",
        "responsibilities",
        "agent_runs",
        "private_files",
    }
    with world[0].store.connection() as conn:
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]


def hide(world, value):
    with world[0].store.connection(write=True) as conn:
        settings = world[0].store.settings(conn)
        settings.pop("version")
        conn.execute(
            "UPDATE settings SET data=?,version=version+1",
            (encode({**settings, "hide_private": value}),),
        )


def login(world):
    world[1]["session"] = world[0].store.authenticate("owner", "fixture-only")


def test_enrollment_restart_10000_quiet_ticks_no_source_read_or_revision(world, monkeypatch):
    r, owner, _ = world
    selected = task(world)
    watch = enroll(world, [selected])
    r.responsibilities = ResponsibilityService(r)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unchanged tick read source or dispatched")

    monkeypatch.setattr(r.responsibilities, "_projection", forbidden)
    monkeypatch.setattr(r.agent_runs, "create", forbidden)
    revision = r.store.revision()
    for _ in range(10000):
        assert r.responsibilities.advance() == 0
    assert r.store.revision() == revision
    assert detail(world, watch)["reviews"] == []
    assert not rows(world, "agent_runs") and not rows(world, "private_files")
    assert r.responsibilities.scope(owner)["scope_revision"] is None


def test_scope_exact_selection_and_atomic_retry(world):
    r, owner, _ = world
    selected, unrelated = task(world), task(world, "Unselected")
    payload = create_payload(world, [selected])
    change(world, unrelated)
    first = r.responsibilities.create(payload, "create-same", owner)
    assert r.responsibilities.create(payload, "create-same", owner) == first
    change(world, selected)
    with pytest.raises(DomainError, match="RESPONSIBILITY_SCOPE_CHANGED"):
        r.responsibilities.create(payload, "stale", owner)
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        r.responsibilities.create(
            payload.model_copy(update={"title": "Other"}), "create-same", owner
        )
    assert len(rows(world, "responsibilities")) == 1
    assert len(rows(world, "responsibility_sources")) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"task_ids": []},
        {"fields": []},
        {"fields": ["status", "status"]},
        {"fields": ["title"]},
        {"retain_change_history": False},
        {"retain_change_history": 1},
        {"review_budget": True},
        {"daily_review_budget": "2"},
        {"review_budget": 101},
        {"title": "  "},
        {"expires_at": "2026-10-14T09:00:00"},
        {"expires_at": "2026-10-14T09:00:00+08:00"},
        {"url": "https://example.com"},
        {"script": "anything"},
    ],
)
def test_strict_enrollment_schema(world, changes):
    data = create_payload(world, [task(world)]).model_dump(mode="json")
    with pytest.raises(ValidationError):
        ResponsibilityCreate(**{**data, **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "selected_calendar_changes"},
        {"source_ids": ["immutable"]},
        {"artifact_ids": ["old-file"]},
    ],
)
def test_unsupported_sources(world, changes):
    data = create_payload(world, [task(world)]).model_dump(mode="json")
    with pytest.raises(DomainError, match="RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED"):
        ResponsibilityCreate(**{**data, **changes})


@pytest.mark.parametrize("days", [0, -1, 31])
def test_explicit_future_expiry_bound(world, days):
    payload = create_payload(world, [task(world)], expires_at=world[2][0] + timedelta(days=days))
    with pytest.raises(DomainError, match="RESPONSIBILITY_EXPIRY_INVALID"):
        world[0].responsibilities.create(payload, "bad-expiry", world[1])


def test_only_selected_fields_and_ids_trigger(world, monkeypatch):
    r = world[0]
    selected, unselected = task(world), task(world, "Unselected")
    watch = enroll(world, [selected], fields=["status", "progress"])
    change(world, unselected)
    task(world, "Later task")
    assert r.responsibilities.advance() == 0
    for action in ("pause", "resume", "snooze"):
        change(world, selected, action)
        revision = r.store.revision()
        assert r.responsibilities.advance() == 1
        assert r.store.revision() == revision
    update(world, selected, title="Live renamed label", next_step="Irrelevant field")
    r.responsibilities.advance()
    assert not detail(world, watch)["reviews"]
    seen = []
    original = r.responsibilities._projection

    def check(conn, task_id, fields):
        seen.append(task_id)
        assert task_id == selected["id"]
        return original(conn, task_id, fields)

    monkeypatch.setattr(r.responsibilities, "_projection", check)
    change(world, selected)
    r.responsibilities.advance()
    review = detail(world, watch)["reviews"][0]
    assert seen == [selected["id"]]
    assert review["changed_ids"] == [selected["id"]] and review["changed_fields"] == ["progress"]
    durable = encode(
        rows(world, "responsibility_reviews")
        + rows(world, "responsibility_sources")
        + rows(world, "responsibility_operations")
    )
    assert "Live renamed label" not in durable and "A private progress note" not in durable
    assert detail(world, watch)["selected_tasks"][0]["title"] == "Live renamed label"


def test_projection_fields_no_op_authoritative_status_and_return_to_baseline(world):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected], fields=["status", "due", "next_step", "waiting_for", "steps"])
    update(world, selected)
    r.responsibilities.advance()
    assert not detail(world, watch)["reviews"]
    update(world, selected, next_step="B")
    update(world, selected, next_step="")
    r.responsibilities.advance()
    assert not detail(world, watch)["reviews"]
    update(
        world,
        selected,
        next_step="C",
        waiting_for="A reply",
        due_local=datetime(2026, 10, 15, 9),
        steps=[{"title": "First", "done": True}],
    )
    r.responsibilities.advance()
    first = detail(world, watch)["reviews"][0]
    assert set(first["changed_fields"]) == {"next_step", "waiting_for", "due", "steps"}
    change(world, selected, "complete")
    r.responsibilities.advance()
    second = detail(world, watch)["reviews"][0]
    assert second["id"] == first["id"] and "status" in second["changed_fields"]
    assert second["version"] == 2 and second["catch_up"]


def test_coalesce_stale_ack_restart_and_new_review(world):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    r.responsibilities.advance()
    first = detail(world, watch)["reviews"][0]
    change(world, selected)
    r.responsibilities = ResponsibilityService(r)
    r.responsibilities.advance()
    second = detail(world, watch)["reviews"][0]
    assert second["id"] == first["id"] and second["version"] == first["version"] + 1
    assert detail(world, watch)["responsibility"]["reviews_used"] == 1
    with pytest.raises(DomainError, match="REVIEW_CHANGED"):
        acknowledge(world, watch, first)
    receipt = acknowledge(world, watch, second, "ack-stable")
    assert acknowledge(world, watch, second, "ack-stable") == receipt
    r.responsibilities = ResponsibilityService(r)
    for _ in range(5):
        assert r.responsibilities.advance() == 0
    change(world, selected)
    r.responsibilities.advance()
    assert len(detail(world, watch)["reviews"]) == 2
    assert detail(world, watch)["reviews"][0]["id"] != first["id"]


def test_transaction_rollback_and_concurrent_ticks(world):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected])
    baseline = rows(world, "responsibility_sources")
    with pytest.raises(RuntimeError):
        with r.store.connection(write=True) as conn:
            r.tasks.evidence(conn, selected["id"], 1, "note", "Rollback text", "fixture")
            raise RuntimeError()
    assert rows(world, "responsibility_sources") == baseline
    change(world, selected)
    with ThreadPoolExecutor(max_workers=5) as pool:
        assert sum(pool.map(lambda _: r.responsibilities.advance(), range(5))) == 1
    assert len(detail(world, watch)["reviews"]) == 1


def test_daily_budget_rollback_restart_and_last_pending_coalescing(world):
    r, _, clock = world
    selected = task(world)
    watch = enroll(world, [selected], daily_review_budget=1, review_budget=3)
    change(world, selected)
    r.responsibilities.advance()
    acknowledge(world, watch)
    change(world, selected)
    baseline = rows(world, "responsibility_sources")[0]
    r.responsibilities.advance()
    assert rows(world, "responsibility_sources")[0] == baseline
    clock[0] += timedelta(days=1)
    r.responsibilities = ResponsibilityService(r)
    r.responsibilities.advance()
    login(world)
    acknowledge(world, watch)
    change(world, selected)
    clock[0] -= timedelta(days=1)
    r.responsibilities.advance()
    assert detail(world, watch)["responsibility"]["reviews_used"] == 2
    clock[0] += timedelta(days=2)
    r.responsibilities.advance()
    login(world)
    last = detail(world, watch)["reviews"][0]
    change(world, selected)
    r.responsibilities.advance()
    assert detail(world, watch)["reviews"][0]["id"] == last["id"]
    assert detail(world, watch)["responsibility"]["reviews_used"] == 3
    acknowledge(world, watch)
    change(world, selected)
    r.responsibilities.advance()
    assert detail(world, watch)["responsibility"]["status"] == "budget_exhausted"
    clock[0] += timedelta(days=1)
    login(world)
    assert r.responsibilities.advance() == 0
    with pytest.raises(DomainError, match="RESPONSIBILITY_CLOSED"):
        control(world, watch, "resume", resume_policy="baseline_now")


def test_pause_resume_baseline_cancel_and_expiry(world):
    r, _, clock = world
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    r.responsibilities.advance()
    control(world, watch, "pause")
    assert detail(world, watch)["reviews"][0]["delivery_state"] == "dismissed"
    change(world, selected)
    assert r.responsibilities.advance() == 0
    control(world, watch, "resume", resume_policy="baseline_now")
    assert r.responsibilities.advance() == 0
    assert len(detail(world, watch)["reviews"]) == 1
    change(world, selected)
    r.responsibilities.advance()
    assert len(detail(world, watch)["reviews"]) == 2
    control(world, watch, "cancel")
    change(world, selected)
    assert r.responsibilities.advance() == 0
    second = enroll(world, [selected], expires_at=clock[0] + timedelta(minutes=1))
    clock[0] += timedelta(minutes=1)
    r.responsibilities.advance()
    assert detail(world, second)["responsibility"]["status"] == "expired"
    assert not detail(world, second)["reviews"]


def test_hidden_and_logout_keep_comparison_not_owner_authority(world):
    r, owner, _ = world
    selected = task(world)
    watch = enroll(world, [selected])
    hide(world, True)
    change(world, selected)
    r.responsibilities.advance()
    listing = r.responsibilities.listing(owner)
    assert listing["hidden"] and listing["pending_count"] == 1
    assert (
        "title" not in listing["responsibilities"][0]
        and "fields" not in listing["responsibilities"][0]
    )
    assert selected["id"] not in encode(listing)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        detail(world, watch)
    paused = r.responsibilities.action(
        watch["id"], ResponsibilityAction(action="pause", expected_version=1), "hidden-pause", owner
    )
    assert paused["responsibility"]["hidden"]
    hide(world, False)
    control(world, watch, "resume", resume_policy="baseline_now")
    r.store.logout(owner["session"])
    change(world, selected)
    r.responsibilities.advance()
    for principal in [
        None,
        {},
        {"kind": "owner"},
        {"kind": "owner", "session": "fake"},
        owner,
        {"kind": "controller", "session": owner["session"]},
    ]:
        with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
            r.responsibilities.listing(principal)
    login(world)
    assert detail(world, watch)["responsibility"]["pending_count"] == 1
    assert not rows(world, "agent_runs")


def test_missing_corrupt_source_blocks_once_explicit_recheck(world):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected])
    with r.store.connection(write=True) as conn:
        original = conn.execute("SELECT data FROM tasks WHERE id=?", (selected["id"],)).fetchone()[
            0
        ]
        conn.execute("UPDATE tasks SET data='broken private text' WHERE id=?", (selected["id"],))
    cursor = rows(world, "responsibility_sources")
    r.responsibilities.advance()
    assert (
        detail(world, watch)["responsibility"]["blocked_code"]
        == "RESPONSIBILITY_SOURCE_UNAVAILABLE"
    )
    revision = r.store.revision()
    assert r.responsibilities.advance() == 0 and r.store.revision() == revision
    assert rows(world, "responsibility_sources") == cursor
    with pytest.raises(DomainError, match="RESPONSIBILITY_SOURCE_UNAVAILABLE"):
        control(world, watch, "recheck")
    with r.store.connection(write=True) as conn:
        conn.execute("UPDATE tasks SET data=? WHERE id=?", (original, selected["id"]))
    control(world, watch, "recheck")
    r.responsibilities.advance()
    assert detail(world, watch)["responsibility"]["status"] == "active"
    with r.store.connection(write=True) as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (selected["id"],))
    r.responsibilities.advance()
    assert not detail(world, watch)["selected_tasks"][0]["available"]
    assert detail(world, watch)["responsibility"]["status"] == "blocked"


def test_control_capacity_retains_independent_stop_reserves(world, monkeypatch):
    selected = task(world)
    watch = enroll(world, [selected])
    monkeypatch.setitem(LIMITS, "ordinary_operations", 3)
    control(world, watch, "pause")
    control(world, watch, "resume", resume_policy="baseline_now")
    control(world, watch, "pause")
    with pytest.raises(DomainError, match="RESPONSIBILITY_ACTION_INVALID"):
        control(world, watch, "pause")
    with pytest.raises(DomainError, match="RESPONSIBILITY_OPERATION_LIMIT"):
        control(world, watch, "resume", resume_policy="baseline_now")
    control(world, watch, "cancel")
    assert len(rows(world, "responsibility_operations")) == 5


def test_capacity_terminal_definitions_not_deleted(world, monkeypatch):
    monkeypatch.setitem(LIMITS, "definitions", 2)
    selected = task(world)
    first = enroll(world, [selected])
    control(world, first, "cancel")
    enroll(world, [selected])
    with pytest.raises(DomainError, match="RESPONSIBILITY_LIMIT"):
        enroll(world, [selected])
    assert len(rows(world, "responsibilities")) == 2


def test_history_pruning_not_cursor_or_operation_reset(world, monkeypatch):
    r = world[0]
    monkeypatch.setitem(LIMITS, "review_history", 3)
    selected = task(world)
    watch = enroll(world, [selected])
    first = None
    for index in range(6):
        change(world, selected)
        r.responsibilities.advance()
        current = detail(world, watch)["reviews"][0]
        if index == 0:
            first = current
        acknowledge(world, watch, current, "ack-" + str(index))
    assert len(rows(world, "responsibility_reviews")) == 3
    r.responsibilities = ResponsibilityService(r)
    assert r.responsibilities.advance() == 0
    assert acknowledge(world, watch, first, "ack-0")["review_id"] == first["id"]
    assert detail(world, watch)["responsibility"]["reviews_used"] == 6


def test_fair_bounded_evaluation(world):
    r = world[0]
    selected = task(world)
    watches = [enroll(world, [selected]) for _ in range(20)]
    change(world, selected)
    assert r.responsibilities.advance() == 10
    change(world, selected)
    assert r.responsibilities.advance() == 10
    assert all(detail(world, watch)["responsibility"]["pending_count"] == 1 for watch in watches)


def test_late_hide_rechecks_fresh_snapshot(world, monkeypatch):
    r, owner, _ = world
    selected = task(world)
    watch = enroll(world, [selected])
    original = r.responsibilities._reply

    def delayed(result, principal, **kwargs):
        hide(world, True)
        return original(result, principal, **kwargs)

    monkeypatch.setattr(r.responsibilities, "_reply", delayed)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        r.responsibilities.detail(watch["id"], owner)


def test_real_files_explicit_work_followup(world):
    r, owner, _ = world
    selected = task(world, '=SUM(1,2), "选定事务"')
    watch = enroll(world, [selected])
    change(world, selected)
    r.responsibilities.advance()
    assert not rows(world, "agent_runs") and not rows(world, "private_files")
    acknowledge(world, watch)
    run = r.agent_runs.create(
        RunCreate(
            goal="Compile current selected task evidence",
            retain=True,
            task_ids=[selected["id"]],
            scope_revision=r.agent_runs.scope(owner)["scope_revision"],
        ),
        "explicit-work",
        owner,
    )["run"]
    for _ in range(20):
        r.agent_runs.advance_one()
        current = r.agent_runs.detail(run["id"], owner)
        if current["run"]["state"] in {"succeeded", "partial", "failed", "blocked"}:
            break
    assert current["run"]["state"] == "succeeded"
    session = hashlib.sha256(owner["session"].encode()).hexdigest()
    artifacts = current["artifacts"]
    assert len(artifacts) == 2
    for artifact in artifacts:
        metadata, body = r.artifacts.download(artifact["id"], session_hash=session)
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        if artifact["format"] == "csv":
            parsed = list(csv.reader(io.StringIO(body.decode())))
            assert len(parsed) >= 2
        else:
            assert selected["title"] in body.decode()
    with r.store.connection() as conn:
        assert r.tasks.get(conn, selected["id"])["status"] == "todo"


def test_evaluation_rollback_before_block_preserves_cursor_and_reviews(world, monkeypatch):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    before = rows(world, "responsibility_sources")
    original = r.responsibilities._evaluate

    def failing(conn, row, now):
        original(conn, row, now)
        raise ValueError("untrusted failure text")

    monkeypatch.setattr(r.responsibilities, "_evaluate", failing)
    r.responsibilities.advance()
    assert rows(world, "responsibility_sources") == before
    assert not rows(world, "responsibility_reviews")
    state = detail(world, watch)["responsibility"]
    assert state["reviews_used"] == 0 and state["status"] == "blocked"


def test_budget_wait_uses_metadata_only(world, monkeypatch):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected], daily_review_budget=1)
    change(world, selected)
    r.responsibilities.advance()
    acknowledge(world, watch)
    change(world, selected)
    before = rows(world, "responsibility_sources")

    def forbidden(*args):
        raise AssertionError("Daily budget wait read the source again")

    monkeypatch.setattr(r.responsibilities, "_projection", forbidden)
    for _ in range(10):
        assert r.responsibilities.advance() == 0
    assert rows(world, "responsibility_sources") == before


def test_pause_race_with_evaluation_cannot_leave_pending(world, monkeypatch):
    import threading

    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    entered, release = threading.Event(), threading.Event()
    original = r.responsibilities._projection

    def waiting(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(r.responsibilities, "_projection", waiting)
    with ThreadPoolExecutor(max_workers=2) as pool:
        evaluation = pool.submit(r.responsibilities.advance)
        assert entered.wait(5)
        stop = pool.submit(
            r.responsibilities.action,
            watch["id"],
            ResponsibilityAction(action="pause", expected_version=1),
            "racing-pause",
            world[1],
        )
        release.set()
        evaluation.result()
        stop.result()
    assert detail(world, watch)["responsibility"]["status"] == "paused"
    assert detail(world, watch)["responsibility"]["pending_count"] == 0
    assert r.responsibilities.advance() == 0


def test_scope_edit_enrollment_boundary_is_revalidated(world):
    r, owner, _ = world
    selected = task(world)
    payload = create_payload(world, [selected])
    with ThreadPoolExecutor(max_workers=2) as pool:
        creating = pool.submit(r.responsibilities.create, payload, "concurrent-create", owner)
        edit = pool.submit(change, world, selected)
        edit.result()
        try:
            watch = creating.result()["responsibility"]
        except DomainError as error:
            assert error.code == "RESPONSIBILITY_SCOPE_CHANGED"
            assert not rows(world, "responsibilities")
        else:
            r.responsibilities.advance()
            assert len(detail(world, watch)["reviews"]) == 1


def test_source_note_insertion_alone_and_deletion_mark_enrolled(world):
    r = world[0]
    selected = task(world)
    watch = enroll(world, [selected], fields=["progress"])
    with r.store.connection(write=True) as conn:
        r.tasks.evidence(
            conn,
            selected["id"],
            selected["version"],
            "note",
            "Saved by another existing writer",
            "fixture",
        )
    r.responsibilities.advance()
    assert detail(world, watch)["reviews"][0]["changed_fields"] == ["progress"]
    acknowledge(world, watch)
    with r.store.connection(write=True) as conn:
        conn.execute("DELETE FROM task_evidence WHERE task_id=? AND kind='note'", (selected["id"],))
    r.responsibilities.advance()
    assert len(detail(world, watch)["reviews"]) == 2


def test_http_routes_real_owner_privacy_replay_and_headers(tmp_path):
    clock = [datetime(2026, 10, 13, 12, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture-only", scheduler=False, clock=lambda: clock[0])
    r = app.state.runtime
    selected = r.tasks.create(TaskInput(title="HTTP selected"), "http-task")["task"]
    base = "/api/responsibilities"
    with TestClient(app) as client:
        assert client.get(base).status_code == 403
        assert (
            client.post(
                "/api/session",
                json={"username": "owner", "password": "fixture-only"},
                headers={"X-Desk-Request": "1"},
            ).status_code
            == 200
        )
        candidate = client.get(base + "/scope").json()
        assert candidate["selected_task_ids"] == [] and candidate["scope_revision"] is None
        scope = client.get(
            base + "/scope", params=[("task_id", selected["id"]), ("field", "progress")]
        ).json()
        data = dict(
            title="HTTP watch",
            kind="selected_task_changes",
            task_ids=[selected["id"]],
            fields=["progress"],
            scope_revision=scope["scope_revision"],
            retain_change_history=True,
            expires_at="2026-10-14T12:00:00Z",
            review_budget=10,
        )
        assert client.post(base, json=data).json()["error"]["code"] == "REQUEST_HEADER_REQUIRED"
        assert (
            client.post(base, json=data, headers={"X-Desk-Request": "1"}).json()["error"]["code"]
            == "OPERATION_ID_REQUIRED"
        )
        headers = {"X-Desk-Request": "1", "X-Operation-Id": "http-create"}
        response = client.post(base, json=data, headers=headers)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        watch = response.json()["responsibility"]
        world = (
            r,
            {"kind": "owner", "session": client.cookies.get("desk_companion_session")},
            clock,
        )
        change(world, selected)
        r.responsibilities.advance()
        review = client.get(base + "/" + watch["id"]).json()["reviews"][0]
        ack_url = base + "/" + watch["id"] + "/reviews/" + review["id"] + "/acknowledge"
        assert (
            client.post(
                ack_url,
                json={"expected_review_version": review["version"]},
                headers={**headers, "X-Operation-Id": "http-ack"},
            ).status_code
            == 200
        )
        hide(world, True)
        assert client.post(base, json=data, headers=headers).status_code == 403
        assert client.get(base + "/scope").status_code == 403
        listing = client.get(base).json()
        assert listing["hidden"] and "title" not in listing["responsibilities"][0]
        stopped = client.post(
            base + "/" + watch["id"] + "/actions",
            json={"action": "cancel", "expected_version": 1},
            headers={**headers, "X-Operation-Id": "http-cancel"},
        )
        assert stopped.status_code == 200 and stopped.json()["responsibility"]["hidden"]
        client.cookies.clear()
        client.cookies.set("desk_companion_device", "fake-device")
        assert client.get(base).status_code == 403
        assert client.get(base, headers={"Authorization": "Bearer fake-agent"}).status_code == 403


@pytest.mark.parametrize("read", ["scope", "listing", "detail", "create_replay"])
def test_hide_then_show_epoch_rejects_all_private_replies(world, monkeypatch, read):
    r, owner, _ = world
    selected = task(world)
    payload = create_payload(world, [selected])
    watch = r.responsibilities.create(payload, "epoch-create", owner)["responsibility"]
    original = r.responsibilities._reply

    def delayed(result, principal, **kwargs):
        hide(world, True)
        hide(world, False)
        return original(result, principal, **kwargs)

    monkeypatch.setattr(r.responsibilities, "_reply", delayed)
    with pytest.raises(DomainError, match="RESPONSIBILITY_CONTEXT_CHANGED"):
        if read == "scope":
            r.responsibilities.scope(owner, [selected["id"]])
        elif read == "listing":
            r.responsibilities.listing(owner)
        elif read == "detail":
            detail(world, watch)
        else:
            r.responsibilities.create(payload, "epoch-create", owner)


def test_expiry_preserves_history_but_dismisses_pending(world):
    r, _, clock = world
    selected = task(world)
    watch = enroll(world, [selected], expires_at=clock[0] + timedelta(minutes=1))
    change(world, selected)
    r.responsibilities.advance()
    old = detail(world, watch)["reviews"][0]
    clock[0] += timedelta(minutes=1)
    r.responsibilities.advance()
    result = detail(world, watch)
    assert result["responsibility"]["status"] == "expired"
    assert result["responsibility"]["pending_count"] == 0
    assert result["reviews"][0]["id"] == old["id"]
    assert result["reviews"][0]["delivery_state"] == "dismissed"
