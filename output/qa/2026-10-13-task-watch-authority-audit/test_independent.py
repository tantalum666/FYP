"""Independent real SQLite and HTTP tests; no live providers or user data."""

import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from desk.app import create_app
from desk.runtime import Runtime
from desk.store import Store, DomainError, encode
from desk.tasks import TaskInput, TaskAction
from desk.responsibilities import (
    ResponsibilityService,
    ResponsibilityCreate,
    ResponsibilityAction,
    ResponsibilityAcknowledge,
)
from desk.agent_run_schemas import RunCreate


@pytest.fixture
def w(tmp_path):
    now = [datetime(2026, 10, 13, 1, tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password="audit-only", clock=lambda: now[0]))
    p = {"kind": "owner", "session": r.store.authenticate("owner", "audit-only")}
    return r, p, now


def task(w, title="PRIVATE TITLE", **kw):
    return w[0].tasks.create(TaskInput(title=title, **kw), uuid4().hex)["task"]


def payload(w, t, **kw):
    s = w[0].responsibilities.scope(w[1], [t["id"]], ["status", "progress"])
    return ResponsibilityCreate(
        title="PRIVATE WATCH",
        kind="selected_task_changes",
        task_ids=[t["id"]],
        fields=s["fields"],
        scope_revision=s["scope_revision"],
        retain_change_history=True,
        expires_at=w[2][0] + timedelta(days=10),
        review_budget=kw.pop("review_budget", 100),
        **kw,
    )


def enroll(w, t, **kw):
    return w[0].responsibilities.create(payload(w, t, **kw), uuid4().hex, w[1])["responsibility"]


def edit(w, t, action="note", key=None, **kw):
    with w[0].store.connection() as c:
        current = w[0].tasks.get(c, t["id"])
    return w[0].tasks.action(
        t["id"],
        TaskAction(action=action, expected_version=current["version"], note="PRIVATE NOTE", **kw),
        key or uuid4().hex,
    )["task"]


def detail(w, d):
    return w[0].responsibilities.detail(d["id"], w[1])


def reviews(w, d):
    return detail(w, d)["reviews"]


def ack(w, d, v=None, key=None):
    v = v or reviews(w, d)[0]
    return w[0].responsibilities.acknowledge(
        d["id"],
        v["id"],
        ResponsibilityAcknowledge(expected_review_version=v["version"]),
        key or uuid4().hex,
        w[1],
    )


def action(w, d, name, **kw):
    cur = detail(w, d)["responsibility"]
    return w[0].responsibilities.action(
        d["id"],
        ResponsibilityAction(action=name, expected_version=cur["version"], **kw),
        uuid4().hex,
        w[1],
    )["responsibility"]


def rows(w, table):
    with w[0].store.connection() as c:
        return [dict(x) for x in c.execute("SELECT * FROM " + table)]


def hide(w):
    with w[0].store.connection(write=True) as c:
        data = w[0].store.settings(c)
        data.pop("version")
        data["hide_private"] = True
        c.execute("UPDATE settings SET data=?", (encode(data),))


def relogin(w):
    w[1]["session"] = w[0].store.authenticate("owner", "audit-only")


def test_scope_exact_no_initial_unrelated_and_10000_quiet(w):
    a, b = task(w), task(w, "UNSELECTED")
    d = enroll(w, a)
    edit(w, b)
    task(w, "LATER TASK")
    before = w[0].store.revision()
    for _ in range(10000):
        w[0].responsibilities.advance()
    assert not reviews(w, d)
    assert w[0].store.revision() == before
    assert {x["source_id"] for x in rows(w, "responsibility_sources")} == {a["id"]}
    assert not rows(w, "agent_runs")


def test_task_commit_rollback_and_replay_are_atomic(w):
    a = task(w)
    d = enroll(w, a)
    before = rows(w, "responsibility_sources")
    with pytest.raises(RuntimeError):
        with w[0].store.connection(write=True) as c:
            c.execute(
                "UPDATE tasks SET status='completed',version=version+1 WHERE id=?", (a["id"],)
            )
            assert (
                c.execute("SELECT dirty_generation FROM responsibility_sources").fetchone()[0] == 1
            )
            raise RuntimeError("rollback")
    assert rows(w, "responsibility_sources") == before
    w[0].responsibilities.advance()
    assert not reviews(w, d)
    p = TaskAction(action="note", expected_version=a["version"], note="PRIVATE NOTE")
    w[0].tasks.action(a["id"], p, "same-task-change")
    after = rows(w, "responsibility_sources")
    w[0].tasks.action(a["id"], p, "same-task-change")
    assert rows(w, "responsibility_sources") == after
    w[0].responsibilities.advance()
    assert len(reviews(w, d)) == 1


def test_noop_title_pause_snooze_and_return_to_baseline(w):
    a = task(w)
    d = enroll(w, a)
    for verb in ["pause", "snooze", "resume"]:
        edit(w, a, verb)
        w[0].responsibilities.advance()
        assert not reviews(w, d)
    edit(w, a, "update", task=TaskInput(title="RENAMED"))
    w[0].responsibilities.advance()
    assert not reviews(w, d)
    with w[0].store.connection(write=True) as c:
        c.execute("UPDATE tasks SET status='completed' WHERE id=?", (a["id"],))
        c.execute("UPDATE tasks SET status='todo' WHERE id=?", (a["id"],))
    w[0].responsibilities.advance()
    assert not reviews(w, d)


def test_concurrent_workers_coalescing_ack_and_restart(w):
    a = task(w)
    d = enroll(w, a)
    edit(w, a)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda _: w[0].responsibilities.advance(), range(24)))
    old = reviews(w, d)[0]
    edit(w, a)
    w[0].responsibilities.advance()
    new = reviews(w, d)[0]
    assert old["id"] == new["id"] and new["version"] == old["version"] + 1
    assert detail(w, d)["responsibility"]["reviews_used"] == 1
    with pytest.raises(DomainError, match="REVIEW_CHANGED"):
        ack(w, d, old)
    result = ack(w, d, new, "ack-stable")
    w[0].responsibilities = ResponsibilityService(w[0])
    assert ack(w, d, new, "ack-stable")["review_id"] == result["review_id"]
    w[0].responsibilities.advance()
    assert len(reviews(w, d)) == 1
    assert not detail(w, d)["responsibility"]["pending_count"]
    assert "PRIVATE NOTE" not in json.dumps(rows(w, "responsibility_reviews"))


def test_pause_cancel_fence_and_resume_baseline(w):
    a = task(w)
    d = enroll(w, a)
    edit(w, a)
    with ThreadPoolExecutor(2) as ex:
        list(
            ex.map(
                lambda f: f(),
                [lambda: w[0].responsibilities.advance(), lambda: action(w, d, "pause")],
            )
        )
    assert detail(w, d)["responsibility"]["pending_count"] == 0
    edit(w, a)
    w[0].responsibilities.advance()
    action(w, d, "resume", resume_policy="baseline_now")
    w[0].responsibilities.advance()
    assert detail(w, d)["responsibility"]["pending_count"] == 0
    edit(w, a)
    action(w, d, "cancel")
    w[0].responsibilities.advance()
    assert (
        detail(w, d)["responsibility"]["status"] == "cancelled"
        and detail(w, d)["responsibility"]["pending_count"] == 0
    )


def test_daily_budget_clock_rollback_and_lifetime(w):
    a = task(w)
    d = enroll(w, a, daily_review_budget=1, review_budget=2)
    edit(w, a)
    w[0].responsibilities.advance()
    ack(w, d)
    edit(w, a)
    before = rows(w, "responsibility_sources")
    w[0].responsibilities.advance()
    assert rows(w, "responsibility_sources") == before
    w[2][0] += timedelta(days=1)
    relogin(w)
    w[0].responsibilities.advance()
    ack(w, d)
    w[2][0] -= timedelta(days=1)
    relogin(w)
    edit(w, a)
    w[0].responsibilities.advance()
    assert detail(w, d)["responsibility"]["status"] == "budget_exhausted"
    edit(w, a)
    assert detail(w, d)["responsibility"]["reviews_used"] == 2


def test_pending_coalesces_even_when_budget_fully_reserved(w):
    a = task(w)
    d = enroll(w, a, daily_review_budget=1, review_budget=1)
    edit(w, a)
    w[0].responsibilities.advance()
    v = reviews(w, d)[0]
    edit(w, a)
    w[0].responsibilities.advance()
    assert reviews(w, d)[0]["id"] == v["id"] and reviews(w, d)[0]["version"] == 2
    assert detail(w, d)["responsibility"]["reviews_used"] == 1


def test_missing_blocks_once_never_denies_task_write(w):
    a = task(w)
    d = enroll(w, a)
    with w[0].store.connection(write=True) as c:
        c.execute("DELETE FROM tasks WHERE id=?", (a["id"],))
    w[0].responsibilities.advance()
    before = rows(w, "responsibility_sources")
    rev = w[0].store.revision()
    for _ in range(10):
        w[0].responsibilities.advance()
    assert w[0].store.revision() == rev and rows(w, "responsibility_sources") == before
    assert detail(w, d)["responsibility"]["blocked_code"] == "RESPONSIBILITY_SOURCE_UNAVAILABLE"
    assert not reviews(w, d)


@pytest.mark.parametrize(
    "principal",
    [
        None,
        {},
        {"kind": "owner"},
        {"kind": "owner", "session": "forged"},
        {"kind": "controller", "session": "forged"},
        {"kind": "display", "session": "forged"},
    ],
)
def test_owner_shaped_principals_cannot_read_or_enroll(w, principal):
    a = task(w)
    p = payload(w, a)
    for fn in [
        lambda: w[0].responsibilities.scope(principal),
        lambda: w[0].responsibilities.listing(principal),
        lambda: w[0].responsibilities.create(p, uuid4().hex, principal),
    ]:
        with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
            fn()
    assert not rows(w, "responsibilities")


def test_operation_replay_hash_conflict_and_live_privacy(w):
    a = task(w)
    p = payload(w, a)
    r = w[0].responsibilities.create(p, "same", w[1])
    d = r["responsibility"]
    assert w[0].responsibilities.create(p, "same", w[1]) == r
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        w[0].responsibilities.create(p.model_copy(update={"title": "other"}), "same", w[1])
    hide(w)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        w[0].responsibilities.create(p, "same", w[1])
    x = w[0].responsibilities.listing(w[1])
    assert "PRIVATE" not in json.dumps(x) and "task_ids" not in json.dumps(x)
    stop = ResponsibilityAction(action="pause", expected_version=d["version"])
    x = w[0].responsibilities.action(d["id"], stop, "stop", w[1])
    assert "PRIVATE" not in json.dumps(x)
    assert w[0].responsibilities.action(d["id"], stop, "stop", w[1]) == x


def test_final_reply_rechecks_hide_and_logout(w, monkeypatch):
    a = task(w)
    d = enroll(w, a)
    original = w[0].responsibilities._reply

    def hidden(result, principal, **kw):
        hide(w)
        return original(result, principal, **kw)

    monkeypatch.setattr(w[0].responsibilities, "_reply", hidden)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        detail(w, d)
    monkeypatch.setattr(w[0].responsibilities, "_reply", original)
    w[0].store.logout(w[1]["session"])
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        w[0].responsibilities.listing(w[1])


def test_expiry_without_dirty_is_terminal_and_never_creates_work(w):
    a = task(w)
    d = enroll(w, a)
    w[2][0] += timedelta(days=11)
    w[0].responsibilities.advance()
    relogin(w)
    assert detail(w, d)["responsibility"]["status"] == "expired"
    assert not reviews(w, d) and not rows(w, "agent_runs")


def test_http_owner_csrf_strict_and_privacy(tmp_path):
    app = create_app(tmp_path, password="audit-only", scheduler=False)
    with TestClient(app) as c:
        assert c.get("/api/responsibilities").status_code == 403
        assert (
            c.post(
                "/api/session",
                json={"username": "owner", "password": "audit-only"},
                headers={"X-Desk-Request": "1"},
            ).status_code
            == 200
        )
        r = app.state.runtime
        t = r.tasks.create(TaskInput(title="HTTP PRIVATE"), uuid4().hex)["task"]
        s = c.get("/api/responsibilities/scope", params={"task_id": t["id"]}).json()
        data = dict(
            title="HTTP WATCH",
            kind="selected_task_changes",
            task_ids=[t["id"]],
            fields=s["fields"],
            scope_revision=s["scope_revision"],
            retain_change_history=True,
            expires_at=(r.store.clock() + timedelta(days=1)).isoformat(),
            review_budget=2,
        )
        assert c.post("/api/responsibilities", json=data).status_code in {403, 422}
        headers = {"X-Desk-Request": "1", "X-Operation-Id": "http-create"}
        assert (
            c.post(
                "/api/responsibilities",
                json={**data, "arbitrary_url": "https://example.com"},
                headers=headers,
            ).status_code
            == 422
        )
        created = c.post("/api/responsibilities", json=data, headers=headers)
        assert created.status_code == 200, created.text
        assert (
            c.post("/api/responsibilities", json=data, headers=headers).json()["responsibility"][
                "id"
            ]
            == created.json()["responsibility"]["id"]
        )
        c.cookies.clear()
        assert c.get("/api/responsibilities").status_code == 403


def test_final_reply_rejects_hide_then_show_epoch_change(w, monkeypatch):
    a = task(w)
    d = enroll(w, a)
    original = w[0].responsibilities._reply

    def changed(result, principal, **kw):
        with w[0].store.connection(write=True) as c:
            data = w[0].store.settings(c)
            data.pop("version")
            data["hide_private"] = True
            c.execute("UPDATE settings SET data=?,version=version+1", (encode(data),))
        with w[0].store.connection(write=True) as c:
            data["hide_private"] = False
            c.execute("UPDATE settings SET data=?,version=version+1", (encode(data),))
        return original(result, principal, **kw)

    monkeypatch.setattr(w[0].responsibilities, "_reply", changed)
    with pytest.raises(DomainError):
        detail(w, d)


def test_expiry_dismisses_existing_pending(w):
    a = task(w)
    d = enroll(w, a)
    edit(w, a)
    w[0].responsibilities.advance()
    w[2][0] += timedelta(days=11)
    w[0].responsibilities.advance()
    relogin(w)
    assert detail(w, d)["responsibility"]["status"] == "expired"
    assert detail(w, d)["responsibility"]["pending_count"] == 0


def test_work_handoff_requires_fresh_owner_scope_and_artifacts_current(w):
    a = task(w, title='=PRIVATE, "task"')
    d = enroll(w, a)
    edit(w, a)
    w[0].responsibilities.advance()
    assert not rows(w, "agent_runs")
    scope = w[0].agent_runs.scope(w[1])
    edit(w, a)
    p = RunCreate(
        goal="Compile current selected task evidence",
        retain=True,
        task_ids=[a["id"]],
        scope_revision=scope["scope_revision"],
    )
    with pytest.raises(DomainError, match="RUN_SCOPE_CHANGED"):
        w[0].agent_runs.create(p, "stale-work", w[1])
    p = p.model_copy(update={"scope_revision": w[0].agent_runs.scope(w[1])["scope_revision"]})
    run = w[0].agent_runs.create(p, "work", w[1])["run"]
    source_before = rows(w, "tasks")
    for _ in range(30):
        w[0].agent_runs.advance_one()
        current = w[0].agent_runs.detail(run["id"], w[1])
        if current["run"]["state"] == "succeeded":
            break
    assert current["run"]["state"] == "succeeded", current["run"]
    assert rows(w, "tasks") == source_before
    assert current["run"]["model_calls"] == 0 and len(current["artifacts"]) == 2
    session = hashlib.sha256(w[1]["session"].encode()).hexdigest()
    for artifact in current["artifacts"]:
        metadata, body = w[0].artifacts.download(artifact["id"], session_hash=session)
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        assert "PRIVATE" in body.decode()
    assert detail(w, d)["responsibility"]["pending_count"] == 1


def test_enrollment_serializes_source_edit_no_lost_gap(w, monkeypatch):
    a = task(w)
    p = payload(w, a)
    service = w[0].responsibilities
    entered = threading.Event()
    release = threading.Event()
    original = service._scope

    def blocked(conn, ids, fields):
        result = original(conn, ids, fields)
        entered.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(service, "_scope", blocked)
    with ThreadPoolExecutor(2) as ex:
        creating = ex.submit(service.create, p, "enrollment-race", w[1])
        assert entered.wait(5)
        editing = ex.submit(edit, w, a)
        release.set()
        d = creating.result()["responsibility"]
        editing.result()
    service.advance()
    assert len(reviews(w, d)) == 1
    assert reviews(w, d)[0]["changed_ids"] == [a["id"]]


def test_stale_selection_denied_without_source_or_watch_mutation(w):
    a = task(w)
    p = payload(w, a)
    edit(w, a)
    before = rows(w, "tasks")
    with pytest.raises(DomainError, match="RESPONSIBILITY_SCOPE_CHANGED"):
        w[0].responsibilities.create(p, "stale", w[1])
    assert rows(w, "tasks") == before and not rows(w, "responsibilities")


def test_final_reply_logout_between_projection_and_return(w, monkeypatch):
    a = task(w)
    d = enroll(w, a)
    original = w[0].responsibilities._reply

    def logout(result, principal, **kw):
        w[0].store.logout(w[1]["session"])
        return original(result, principal, **kw)

    monkeypatch.setattr(w[0].responsibilities, "_reply", logout)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        detail(w, d)


@pytest.mark.parametrize("kind", ["controller", "display"])
def test_real_paired_http_identity_cannot_gain_watch_authority(tmp_path, kind):
    from desk.access import PairingRequest, PairingDecision, PairingClaim

    app = create_app(tmp_path, password="audit-only", scheduler=False)
    r = app.state.runtime
    issued = r.access.issue(kind, uuid4().hex)
    request = r.access.request(PairingRequest(code=issued["code"], name="Fixture only"))
    r.access.decide(
        PairingDecision(request_id=request["request_id"], action="approve"), uuid4().hex
    )
    paired = r.access.claim(
        PairingClaim(request_id=request["request_id"], secret=request["secret"])
    )
    with TestClient(app) as c:
        for path in [
            "/api/responsibilities",
            "/api/responsibilities/scope",
            "/api/responsibilities/fake",
        ]:
            assert (
                c.get(path, headers={"Authorization": "Bearer " + paired["token"]}).status_code
                == 403
            )
        c.cookies.set("desk_companion_device", paired["token"])
        assert c.get("/api/responsibilities").status_code == 403
        assert (
            c.post(
                "/api/responsibilities",
                json={},
                headers={"X-Desk-Request": "1", "X-Operation-Id": "paired"},
            ).status_code
            == 403
        )


def test_operation_exhaustion_preserves_stop_reserves(w):
    a = task(w)
    d = enroll(w, a)
    with w[0].store.connection(write=True) as c:
        c.executemany(
            "INSERT INTO responsibility_operations VALUES(?,?,?,?,?)",
            [(f"fill-{i}", "0" * 64, d["id"], None, "acknowledge") for i in range(256)],
        )
    edit(w, a)
    w[0].responsibilities.advance()
    with pytest.raises(DomainError, match="RESPONSIBILITY_OPERATION_LIMIT"):
        ack(w, d)
    action(w, d, "pause")
    action(w, d, "cancel")
    assert detail(w, d)["responsibility"]["status"] == "cancelled"


def test_background_survives_logout_but_owner_reads_do_not(w):
    a = task(w)
    d = enroll(w, a)
    w[0].store.logout(w[1]["session"])
    edit(w, a)
    w[0].responsibilities.advance()
    assert len(rows(w, "responsibility_reviews")) == 1
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        detail(w, d)
    assert not rows(w, "agent_runs")


def test_projection_only_reads_selected_ids(w, monkeypatch):
    a, b = task(w), task(w, "UNSELECTED")
    enroll(w, a)
    calls = []
    original = w[0].responsibilities._projection

    def observe(conn, task_id, fields):
        calls.append(task_id)
        return original(conn, task_id, fields)

    monkeypatch.setattr(w[0].responsibilities, "_projection", observe)
    edit(w, b)
    w[0].responsibilities.advance()
    assert not calls
    edit(w, a)
    w[0].responsibilities.advance()
    assert calls == [a["id"]]


def test_evaluation_failure_rolls_back_review_budget_and_cursor(w, monkeypatch):
    a = task(w)
    d = enroll(w, a)
    edit(w, a)
    original = w[0].responsibilities._evaluate
    before = rows(w, "responsibility_sources")

    def broken(conn, row, now):
        original(conn, row, now)
        raise DomainError("SIMULATED_POST_WRITE_FAILURE")

    monkeypatch.setattr(w[0].responsibilities, "_evaluate", broken)
    w[0].responsibilities.advance()
    assert not reviews(w, d)
    assert rows(w, "responsibility_sources") == before
    current = detail(w, d)["responsibility"]
    assert (
        current["reviews_used"] == 0
        and current["daily_used"] == 0
        and current["status"] == "blocked"
    )


def test_daily_watermark_cannot_restore_quota_after_rollback(w):
    a = task(w)
    d = enroll(w, a, daily_review_budget=1, review_budget=10)
    edit(w, a)
    w[0].responsibilities.advance()
    ack(w, d)
    w[2][0] += timedelta(days=1)
    relogin(w)
    edit(w, a)
    w[0].responsibilities.advance()
    ack(w, d)
    w[2][0] -= timedelta(days=1)
    relogin(w)
    edit(w, a)
    w[0].responsibilities.advance()
    assert detail(w, d)["responsibility"]["reviews_used"] == 2
    assert detail(w, d)["responsibility"]["budget_day"] == "2026-10-14"
    assert not detail(w, d)["responsibility"]["pending_count"]
    w[0].responsibilities = ResponsibilityService(w[0])
    w[0].responsibilities.advance()
    assert detail(w, d)["responsibility"]["reviews_used"] == 2
