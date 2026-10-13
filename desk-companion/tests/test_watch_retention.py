"""Isolated synthetic watch histories only; no user stores or provider calls."""

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.responsibilities import ResponsibilityAction, ResponsibilityService
from desk.responsibility_retention import (
    RetentionAction,
    RetentionPreviewRequest,
    TOMBSTONE,
    watch_accounting,
)
from desk.store import DomainError, encode
from test_responsibilities import (
    acknowledge,
    change,
    control,
    create_payload,
    detail,
    enroll,
    hide,
    login,
    rows,
    task,
    world as watch_world,
)


@pytest.fixture
def world(tmp_path):
    return watch_world.__wrapped__(tmp_path)


def prepared(world, watch=None, action="trash"):
    r, owner, _ = world
    if watch is None:
        watch = control(world, enroll(world, [task(world)]), "cancel")
    request = RetentionPreviewRequest(
        action=action,
        expected_version=watch["version"],
        expected_retention_version=watch["retention_version"],
    )
    preview = r.responsibilities.retention_preview(watch["id"], request, owner)
    payload = RetentionAction(
        **request.model_dump(),
        preview_id=preview["preview_id"],
        **({"confirm_permanent_removal": True} if action == "purge" else {}),
    )
    return watch, payload, preview


def apply(world, watch, payload, key=None):
    return world[0].responsibilities.retention_action(
        watch["id"], payload, key or uuid4().hex, world[1]
    )


def usage(world):
    return world[0].responsibilities.listing(world[1])["maintenance_usage"]


def dump(world):
    with world[0].store.connection() as conn:
        return list(conn.iterdump())


def test_trash_restore_preserve_terminal_identity_spent_budgets_and_no_alert(world):
    r, owner, _ = world
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    r.responsibilities.advance()
    watch = control(world, watch, "cancel")
    original = detail(world, watch)
    before = dump(world)
    watch, payload, preview = prepared(world, watch)
    assert dump(world) == before
    assert preview["logical_slots_released"] == 0
    assert (
        preview["retained_operation_receipts_after"] == preview["counts"]["operation_receipts"] + 1
    )
    result = apply(world, watch, payload, "trash")
    assert result["kind"] == "retention_disposition" and result["retention_state"] == "trashed"
    assert "title" not in encode(result) and "acknowledged" not in result
    assert r.responsibilities.listing(owner)["responsibilities"] == []
    assert usage(world)["retained_count"] == usage(world)["trashed_count"] == 1
    with pytest.raises(DomainError, match="RESPONSIBILITY_RETAINED_STATE_REQUIRED"):
        detail(world, watch)
    hidden = r.responsibilities.maintenance_detail(watch["id"], owner)
    assert hidden["reviews"] == original["reviews"]
    restored_watch, restore, _ = prepared(world, hidden["responsibility"], "restore")
    restored = apply(world, restored_watch, restore)["responsibility"]
    for key in (
        "id",
        "status",
        "version",
        "generation",
        "expires_at",
        "reviews_used",
        "review_budget",
        "daily_used",
        "budget_day",
    ):
        assert restored[key] == watch[key]
    assert restored["retention_version"] == watch["retention_version"] + 2
    change(world, selected)
    assert r.responsibilities.advance() == 0
    assert restored["pending_count"] == 0 and usage(world)["retained_count"] == 1


def test_full_capacity_exact_one_slot_original_keys_no_resurrection(world):
    r, owner, _ = world
    selected = task(world)
    create = create_payload(world, [selected])
    first = r.responsibilities.create(create, "original-create", owner)["responsibility"]
    cancel = ResponsibilityAction(action="cancel", expected_version=1)
    first = r.responsibilities.action(first["id"], cancel, "original-cancel", owner)[
        "responsibility"
    ]
    for _ in range(19):
        enroll(world, [selected])
    watch, trash, _ = prepared(world, first)
    apply(world, watch, trash, "original-trash")
    with pytest.raises(DomainError, match="RESPONSIBILITY_LIMIT"):
        r.responsibilities.create(create, "new-before-purge", owner)
    trashed = r.responsibilities.maintenance_detail(first["id"], owner)["responsibility"]
    _, purge, preview = prepared(world, trashed, "purge")
    assert preview["logical_slots_released"] == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: apply(world, trashed, purge, "original-purge"), range(4)))
    assert all(result == results[0] for result in results)
    session_hash = hashlib.sha256(owner["session"].encode()).hexdigest()
    capacity = r.work_capacity.snapshot(session_hash=session_hash)
    assert capacity["watches"]["count"]["used"] == 19
    r.responsibilities.create(create, "new-after-purge", owner)
    assert usage(world)["retained_count"] == 20 and usage(world)["lifetime_count"] == 21
    r.responsibilities = ResponsibilityService(r)
    for result in (
        r.responsibilities.create(create, "original-create", owner),
        r.responsibilities.action(first["id"], cancel, "original-cancel", owner),
        apply(world, watch, trash, "original-trash"),
        apply(world, trashed, purge, "original-purge"),
    ):
        assert result["retention_state"] == "purged" and result["responsibility_id"] == first["id"]
        assert first["title"] not in encode(result)
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        r.responsibilities.create(
            create.model_copy(update={"title": "Wrong"}), "original-create", owner
        )
    with pytest.raises(DomainError, match="RESPONSIBILITY_REMOVED") as error:
        r.responsibilities.maintenance_detail(first["id"], owner)
    assert error.value.status == 410
    with r.store.connection() as conn:
        assert (
            conn.execute("SELECT data FROM responsibilities WHERE id=?", (first["id"],)).fetchone()[
                0
            ]
            == TOMBSTONE
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM responsibility_sources WHERE responsibility_id=?",
                (first["id"],),
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM responsibility_operations WHERE responsibility_id=? AND kind='purge'",
                (first["id"],),
            ).fetchone()[0]
            == 1
        )


def test_old_ack_after_review_pruning_and_purge_is_safe_disposition(world):
    r, owner, _ = world
    selected = task(world)
    watch = enroll(world, [selected])
    change(world, selected)
    r.responsibilities.advance()
    review = detail(world, watch)["reviews"][0]
    acknowledge(world, watch, review, "old-ack")
    watch = control(world, watch, "cancel")
    watch, purge, _ = prepared(world, watch, "purge")
    apply(world, watch, purge)
    result = acknowledge(world, watch, review, "old-ack")
    assert (
        result["original_operation_kind"] == "acknowledge" and result["review_id"] == review["id"]
    )
    assert result["recorded_success"] is True and "acknowledged" not in result
    other = enroll(world, [selected])
    from desk.responsibilities import ResponsibilityAcknowledge

    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        r.responsibilities.acknowledge(
            other["id"],
            review["id"],
            ResponsibilityAcknowledge(expected_review_version=review["version"]),
            "old-ack",
            owner,
        )


@pytest.mark.parametrize("action", ["trash", "restore", "purge"])
def test_nonterminal_refused_zero_write(world, action):
    watch = enroll(world, [task(world)])
    before = dump(world)
    with pytest.raises(DomainError, match="RESPONSIBILITY_NOT_TERMINAL"):
        prepared(world, watch, action)
    assert dump(world) == before


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_purge_strict_final_confirmation(value):
    with pytest.raises(ValidationError):
        RetentionAction(
            action="purge",
            expected_version=1,
            expected_retention_version=1,
            preview_id="x" * 32,
            confirm_permanent_removal=value,
        )


@pytest.mark.parametrize("action", ["trash", "restore"])
@pytest.mark.parametrize("value", [None, False, True])
def test_confirmation_field_forbidden_on_reversible_actions(action, value):
    with pytest.raises(ValidationError):
        RetentionAction(
            action=action,
            expected_version=1,
            expected_retention_version=1,
            preview_id="x" * 32,
            confirm_permanent_removal=value,
        )


@pytest.mark.parametrize("change_kind", ["expiry", "monotonic", "rollback", "restart", "eviction"])
def test_preview_expiry_dual_clocks_restart_eviction_no_writes(world, change_kind):
    r, _, clock = world
    watch, payload, _ = prepared(world)
    if change_kind == "expiry":
        clock[0] += timedelta(minutes=5)
    elif change_kind == "rollback":
        clock[0] -= timedelta(seconds=1)
    elif change_kind == "monotonic":
        old = r.responsibilities.retention_previews.monotonic
        r.responsibilities.retention_previews.monotonic = lambda: old() + 301
    elif change_kind == "restart":
        r.responsibilities = ResponsibilityService(r)
    else:
        for _ in range(32):
            prepared(world, watch)
        assert len(r.responsibilities.retention_previews.entries) == 32
    before = dump(world)
    with pytest.raises(DomainError, match="RESPONSIBILITY_PREVIEW_EXPIRED"):
        apply(world, watch, payload)
    assert dump(world) == before


@pytest.mark.parametrize(
    "change_kind", ["session", "settings", "personal", "inventory", "action", "target"]
)
def test_preview_binding_mismatch_zero_writes(world, change_kind):
    r, owner, _ = world
    watch, payload, _ = prepared(world)
    if change_kind == "session":
        login(world)
    elif change_kind == "settings":
        hide(world, True)
        hide(world, False)
    elif change_kind == "personal":
        with r.store.connection(write=True) as conn:
            conn.execute("UPDATE personal_settings SET epoch=epoch+1")
    elif change_kind == "inventory":
        with r.store.connection(write=True) as conn:
            conn.execute("UPDATE responsibility_sources SET dirty_generation=dirty_generation+1")
    elif change_kind == "action":
        payload = RetentionAction(
            **{
                **payload.model_dump(exclude_unset=True),
                "action": "purge",
                "confirm_permanent_removal": True,
            }
        )
    else:
        watch = control(world, enroll(world, [task(world)]), "cancel")
    before = dump(world)
    with pytest.raises(DomainError, match="RESPONSIBILITY_PREVIEW_CHANGED"):
        apply(world, watch, payload)
    assert dump(world) == before


def test_postcommit_authority_denial_original_key_recovers_after_cache_loss(world, monkeypatch):
    r, _, _ = world
    watch, payload, _ = prepared(world, action="purge")
    original = r.responsibilities._reply

    def changed(*args, **kwargs):
        with r.store.connection(write=True) as conn:
            conn.execute("UPDATE personal_settings SET epoch=epoch+1")
        return original(*args, **kwargs)

    monkeypatch.setattr(r.responsibilities, "_reply", changed)
    with pytest.raises(DomainError, match="RESPONSIBILITY_CONTEXT_CHANGED"):
        apply(world, watch, payload, "lost")
    r.responsibilities = ResponsibilityService(r)
    result = apply(world, watch, payload, "lost")
    assert result["retention_state"] == "purged"
    assert len(rows(world, "responsibility_operations")) == 3


def fill_receipts(world, watch, total):
    with world[0].store.connection(write=True) as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM responsibility_operations WHERE responsibility_id=?",
            (watch["id"],),
        ).fetchone()[0]
        for i in range(existing, total):
            conn.execute(
                "INSERT INTO responsibility_operations VALUES(?,?,?,NULL,'acknowledge')",
                (f"synthetic-{watch['id']}-{i}", "0" * 64, watch["id"]),
            )


def test_receipt_254_trash255_restore256_then_direct_purge257(world):
    watch = control(world, enroll(world, [task(world)]), "cancel")
    fill_receipts(world, watch, 254)
    _, trash, _ = prepared(world, watch)
    apply(world, watch, trash)
    current = world[0].responsibilities.maintenance_detail(watch["id"], world[1])["responsibility"]
    _, restore, _ = prepared(world, current, "restore")
    restored = apply(world, current, restore)["responsibility"]
    assert len(rows(world, "responsibility_operations")) == 256
    with pytest.raises(DomainError, match="RESPONSIBILITY_OPERATION_LIMIT"):
        prepared(world, restored)
    _, purge, _ = prepared(world, restored, "purge")
    apply(world, restored, purge)
    assert len(rows(world, "responsibility_operations")) == 257


def test_stop_receipt_258_and_final_purge259(world):
    watch = enroll(world, [task(world)])
    fill_receipts(world, watch, 256)
    watch = control(world, watch, "pause")
    watch = control(world, watch, "cancel")
    assert len(rows(world, "responsibility_operations")) == 258
    _, purge, _ = prepared(world, watch, "purge")
    apply(world, watch, purge, "purge")
    assert len(rows(world, "responsibility_operations")) == 259
    before = dump(world)
    with pytest.raises(DomainError, match="VERSION_CONFLICT|RESPONSIBILITY_RETENTION_INVALID"):
        apply(world, watch, purge, "other-purge")
    assert dump(world) == before


def test_distinct_key_no_op_trash_restore_refused_without_receipts(world):
    watch, trash, _ = prepared(world)
    apply(world, watch, trash, "one")
    before = dump(world)
    with pytest.raises(DomainError):
        apply(world, watch, trash, "two")
    assert dump(world) == before
    trashed = world[0].responsibilities.maintenance_detail(watch["id"], world[1])["responsibility"]
    _, restore, _ = prepared(world, trashed, "restore")
    apply(world, trashed, restore, "three")
    before = dump(world)
    with pytest.raises(DomainError):
        apply(world, trashed, restore, "four")
    assert dump(world) == before


def test_lifetime_identity_ceiling_and_invalid_shell_fail_closed(world):
    r, owner, _ = world
    watch, purge, _ = prepared(world, action="purge")
    apply(world, watch, purge)
    with r.store.connection(write=True) as conn:
        template = dict(conn.execute("SELECT * FROM responsibilities").fetchone())
        columns = list(template)
        for i in range(255):
            values = {**template, "id": f"fixture-purged-{i}"}
            conn.execute(
                f"INSERT INTO responsibilities({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                [values[c] for c in columns],
            )
            conn.execute(
                "INSERT INTO responsibility_operations VALUES(?,?,?,NULL,'purge')",
                (f"fixture-purge-{i}", "0" * 64, values["id"]),
            )
    assert usage(world)["retained_count"] == 0 and usage(world)["lifetime_remaining"] == 0
    payload = create_payload(world, [task(world)])
    with pytest.raises(DomainError, match="RESPONSIBILITY_METADATA_LIMIT"):
        r.responsibilities.create(payload, "no-lifetime-room", owner)
    with r.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE responsibilities SET data='private stale title' WHERE id=?", (watch["id"],)
        )
    session = hashlib.sha256(owner["session"].encode()).hexdigest()
    assert (
        r.work_capacity.snapshot(session_hash=session)["watches"]["count"]["state"] == "unavailable"
    )
    with pytest.raises(DomainError, match="RESPONSIBILITY_METADATA_UNAVAILABLE"):
        r.responsibilities.create(payload, "malformed-shell", owner)


@pytest.mark.parametrize("bad", ["unknown", None])
def test_unknown_lifecycle_never_claims_free_capacity(world, bad):
    watch = enroll(world, [task(world)])
    with world[0].store.connection(write=True) as conn:
        if bad is None:
            # Schema NOT NULL is another barrier; corrupt unknown labels tested below.
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("UPDATE responsibilities SET retention_state=NULL")
            return
        conn.execute("UPDATE responsibilities SET retention_state=?", (bad,))
        result = watch_accounting(conn)
    assert result["state"] == "unavailable" and result["retained_count"] is None
    assert watch["id"] in encode(rows(world, "responsibilities"))


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM responsibility_sources",
        "DELETE FROM responsibility_reviews",
        "UPDATE responsibilities SET data=",
        "INSERT INTO responsibility_operations",
        "UPDATE state SET revision=revision+1",
    ],
)
def test_purge_every_mutation_rollback_atomic(world, monkeypatch, sql):
    r = world[0]
    watch, purge, _ = prepared(world, action="purge")
    before = dump(world)
    original = r.store.connection

    class Fault:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, statement, *args):
            result = self.conn.execute(statement, *args)
            if statement.startswith(sql):
                raise RuntimeError("Synthetic crash checkpoint")
            return result

        def __getattr__(self, name):
            return getattr(self.conn, name)

    @contextmanager
    def connection(write=False):
        with original(write=write) as conn:
            yield Fault(conn) if write else conn

    monkeypatch.setattr(r.store, "connection", connection)
    with pytest.raises(RuntimeError, match="Synthetic crash"):
        apply(world, watch, purge, "atomic")
    monkeypatch.setattr(r.store, "connection", original)
    assert dump(world) == before
    assert apply(world, watch, purge, "atomic")["retention_state"] == "purged"


def test_hidden_actual_owner_and_nonwatch_rows_preserved(world):
    r, owner, _ = world
    watch, purge, _ = prepared(world, action="purge")
    with r.store.connection() as conn:
        protected = {
            name: [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")]
            for name in (
                "tasks",
                "task_evidence",
                "events",
                "agent_runs",
                "agent_run_operations",
                "private_files",
                "agent_voice_origins",
            )
        }
    for principal in (
        {"kind": "owner", "session": "forged"},
        {"kind": "controller", "session": owner["session"]},
    ):
        with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
            r.responsibilities.retention_action(watch["id"], purge, "unauthorized", principal)
    hide(world, True)
    assert usage(world)["retained_count"] == 1
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        apply(world, watch, purge)
    hide(world, False)
    _, purge, _ = prepared(world, watch, "purge")
    apply(world, watch, purge)
    with r.store.connection() as conn:
        for name, values in protected.items():
            assert [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")] == values


def test_http_preview_routes_confirmation_and_origin(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    r = app.state.runtime
    with TestClient(app) as client:
        headers = {"X-Desk-Request": "1"}
        client.post(
            "/api/session", headers=headers, json={"username": "owner", "password": "fixture-only"}
        )
        owner = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
        w = (r, owner, [r.store.clock()])
        watch = control(w, enroll(w, [task(w)]), "cancel")
        url = f"/api/responsibilities/{watch['id']}"
        request = dict(
            action="purge", expected_version=watch["version"], expected_retention_version=1
        )
        assert client.post(url + "/maintenance-preview", json=request).status_code == 403
        assert (
            client.post(
                url + "/maintenance-preview",
                headers={**headers, "Origin": "https://example.com"},
                json=request,
            ).status_code
            == 403
        )
        preview = client.post(url + "/maintenance-preview", headers=headers, json=request)
        assert preview.status_code == 200 and preview.headers["cache-control"] == "no-store"
        payload = {**request, "preview_id": preview.json()["preview_id"]}
        mutation_headers = {**headers, "X-Operation-Id": "explicit-final-click"}
        assert (
            client.post(url + "/retention", headers=mutation_headers, json=payload).status_code
            == 422
        )
        payload["confirm_permanent_removal"] = True
        response = client.post(url + "/retention", headers=mutation_headers, json=payload)
        assert response.status_code == 200 and response.json()["retention_state"] == "purged"
        assert client.get(url + "/maintenance").status_code == 410
        assert client.get("/api/responsibilities/maintenance").json()["responsibilities"] == []


@pytest.mark.parametrize("count", [259, 260])
def test_excess_legacy_receipts_do_not_get_another_purge(world, count):
    watch = control(world, enroll(world, [task(world)]), "cancel")
    fill_receipts(world, watch, count)
    before = dump(world)
    with pytest.raises(DomainError, match="RESPONSIBILITY_OPERATION_LIMIT"):
        prepared(world, watch, "purge")
    assert dump(world) == before


@pytest.mark.parametrize("column", ["retention_state", "trashed_at", "restored_at", "purged_at"])
def test_accounting_large_scalars_are_bounded_before_python(world, column):
    enroll(world, [task(world)])
    with world[0].store.connection(write=True) as conn:
        conn.execute(f"UPDATE responsibilities SET {column}=?", ("x" * 1048576,))
    observed = []
    original = world[0].store.connection

    @contextmanager
    def checked(write=False):
        with original(write=write) as conn:

            def row_factory(cursor, values):
                observed.extend(value for value in values if isinstance(value, str))
                return sqlite3.Row(cursor, values)

            conn.row_factory = row_factory
            yield conn

    with checked() as conn:
        assert watch_accounting(conn)["state"] == "unavailable"
    assert max(map(len, observed), default=0) <= 64


def test_receipt_metadata_excess_not_mislabeled_body_capacity_overflow(world):
    watch = control(world, enroll(world, [task(world)]), "cancel")
    fill_receipts(world, watch, 260)
    assert usage(world)["state"] == "over_limit"
    r, owner, _ = world
    session = hashlib.sha256(owner["session"].encode()).hexdigest()
    assert r.work_capacity.snapshot(session_hash=session)["watches"]["count"] == {
        "limit": 20,
        "used": None,
        "remaining": None,
        "state": "unavailable",
    }


@pytest.mark.parametrize("raw", ["broken json", "x" * 1048576])
def test_hidden_stop_never_decodes_or_loads_private_body(world, monkeypatch, raw):
    import desk.responsibilities as module

    r, owner, _ = world
    watch = enroll(world, [task(world)])
    with r.store.connection(write=True) as conn:
        conn.execute("UPDATE responsibilities SET data=?", (raw,))
    hide(world, True)

    def forbidden(*args):
        pytest.fail("Hidden stop projection decoded private data")

    monkeypatch.setattr(module, "decode_body", forbidden)
    observed = []
    original = r.store.connection

    @contextmanager
    def checked(write=False):
        with original(write=write) as conn:

            def row_factory(cursor, values):
                observed.extend(value for value in values if isinstance(value, str))
                return sqlite3.Row(cursor, values)

            conn.row_factory = row_factory
            yield conn

    monkeypatch.setattr(r.store, "connection", checked)
    assert r.responsibilities.listing(owner)["responsibilities"][0]["hidden"]
    paused = r.responsibilities.action(
        watch["id"], ResponsibilityAction(action="pause", expected_version=1), "hidden-pause", owner
    )["responsibility"]
    cancelled = r.responsibilities.action(
        watch["id"],
        ResponsibilityAction(action="cancel", expected_version=paused["version"]),
        "hidden-cancel",
        owner,
    )["responsibility"]
    assert cancelled["status"] == "cancelled" and cancelled["hidden"]
    assert raw not in observed and "title" not in cancelled
