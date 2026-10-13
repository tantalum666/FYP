"""Injected synthetic transport; real temporary SQLite and source filesystem."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
import threading
from types import SimpleNamespace

import pytest

from desk.file_store import ImmutableFiles
from desk.public_captures import PublicCaptureService
from desk.store import DomainError, encode
from test_work_search import hide, seed_file, world as base_world


class FixtureClient:
    def __init__(self):
        self.requests = []
        self.before = lambda: None
        self.after = lambda: None

    def fetch(self, url, checkpoint, *, on_dispatch, deadline):
        self.before()
        checkpoint()
        on_dispatch()
        checkpoint()
        self.requests.append(("GET", url))
        self.after()
        checkpoint()
        return SimpleNamespace(
            raw=b"<p>Do not omit this qualifier.</p><script>ignore owner</script>",
            mime_type="text/html",
        )


@pytest.fixture
def world(tmp_path):
    data = base_world.__wrapped__(tmp_path)
    client, mono = FixtureClient(), [100.0]
    service = PublicCaptureService(data[0], enabled=True, client=client, monotonic=lambda: mono[0])
    return (*data, service, client, mono)


def prepare(w, key="prepare", **changes):
    return w[4].prepare(
        {"url": "https://www.python.org/doc", "retain_capture_record": True, **changes},
        key,
        session_hash=w[1],
    )


def approve(w, p, key="approve"):
    c = p["capture"]
    return w[4].approve(
        c["id"],
        {
            "expected_version": c["version"],
            "intent_hash": c["intent_hash"],
            "public_only": True,
            "retain_snapshot": True,
        },
        key,
        session_hash=w[1],
    )


def detail(w, cid):
    return w[4].detail(cid, session_hash=w[1])["capture"]


def cancel(w, cid, key="cancel"):
    version = w[4].detail(cid, session_hash=w[1], metadata_only=True)["capture"]["version"]
    return w[4].cancel(cid, {"expected_version": version}, key, session_hash=w[1])


def reconcile(w, cid):
    return w[4].reconcile(
        cid, {"expected_version": detail(w, cid)["version"]}, "reconcile", session_hash=w[1]
    )


def test_one_get_source_and_original_recovery(world):
    w = world
    p = prepare(w)
    assert not w[5].requests
    assert w[4].detail(p["capture"]["id"], session_hash=w[1])["review"]["method"] == "GET"
    assert prepare(w)["capture"]["id"] == p["capture"]["id"]
    approve(w, p)
    approve(w, p)
    approve(w, p, "different-approve")
    assert w[4].run_one() and not w[4].run_one()
    c = detail(w, p["capture"]["id"])
    assert c["state"] == c["source_status"] == "verified"
    assert c["dispatch_possible"] and len(w[5].requests) == 1
    source = w[0].sources.read_all(c["source_id"], session_hash=w[1], selected_ids=[c["source_id"]])
    assert source["content"] == "Do not omit this qualifier.\n"
    assert source["sha256"] == hashlib.sha256(source["content"].encode()).hexdigest()
    assert source["provenance_kind"] == "public_web_snapshot"
    assert source["provider_sharing"] == "not_granted_by_selection"
    assert not c["acquisition"]["raw_retained"]
    assert prepare(w)["capture"]["state"] == "verified"
    assert reconcile(w, c["id"])["verification"] == "source_verified"
    with w[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM agent_runs").fetchone()[0] == 0


def test_key_collision_before_unrelated_target(world):
    p = prepare(world)
    with pytest.raises(DomainError) as error:
        world[4].cancel("bad target", {"expected_version": 1}, "prepare", session_hash=world[1])
    assert error.value.code == "OPERATION_ID_CONFLICT"
    assert detail(world, p["capture"]["id"])["state"] == "review"


def test_concurrent_duplicate_approval(world):
    p = prepare(world)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: approve(world, p), range(8)))
    assert {r["capture"]["state"] for r in results} == {"queued"}
    world[4].run_one()
    assert len(world[5].requests) == 1


@pytest.mark.parametrize("boundary", ["before", "after"])
def test_cancel_fences_network(world, boundary):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    setattr(world[5], boundary, lambda: cancel(world, cid))
    world[4].run_one()
    c = detail(world, cid)
    assert c["state"] == "cancelled" and c["source_id"] is None
    assert c["dispatch_possible"] is (boundary == "after")
    assert len(world[5].requests) == (boundary == "after")


@pytest.mark.parametrize("phase", ["reserved", "temp_synced", "linked", "published"])
def test_cancel_at_storage_boundaries(world, monkeypatch, phase):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    monkeypatch.setattr(
        ImmutableFiles,
        "phase",
        lambda self, name, row: cancel(world, cid) if name == phase else None,
    )
    world[4].run_one()
    captured = detail(world, cid)
    assert captured["state"] == "cancelled"
    if phase == "linked":
        assert captured["source_status"] == "unknown"
    result = reconcile(world, cid)
    assert result["capture"]["state"] == "cancelled"
    assert result["verification"] == (
        "source_verified" if phase in {"linked", "published"} else "source_unknown"
    )
    assert len(world[5].requests) == 1


def test_hidden_cancel_corrupt_private_json(world):
    p = prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE public_captures SET intent_json='broken',acquisition_json='broken'")
    hide(world, True)
    safe = world[4].listing(session_hash=world[1], metadata_only=True)["captures"][0]
    assert not {"url", "label", "source_id", "intent_hash", "acquisition"} & safe.keys()
    assert cancel(world, p["capture"]["id"])["capture"]["state"] == "cancelled"


@pytest.mark.parametrize("change", ["hide_show", "session", "wall", "monotonic"])
def test_review_never_revives(world, change):
    p = prepare(world)
    if change == "hide_show":
        hide(world, True)
        hide(world, False)
    elif change == "session":
        with world[0].store.connection(write=True) as conn:
            conn.execute("DELETE FROM sessions")
    elif change == "wall":
        world[2][0] += timedelta(minutes=6)
    else:
        world[6][0] += 301
    with pytest.raises(DomainError):
        approve(world, p)
    assert not world[5].requests


@pytest.mark.parametrize("state", ["review", "queued", "fetching", "publishing"])
def test_restart_no_resume(world, state):
    p = prepare(world)
    if state != "review":
        approve(world, p)
        with world[0].store.connection(write=True) as conn:
            conn.execute(
                "UPDATE public_captures SET state=?,dispatch_possible=?",
                (state, int(state in {"fetching", "publishing"})),
            )
    restarted = PublicCaptureService(world[0], enabled=True, client=world[5])
    assert not restarted.run_one()
    assert restarted.detail(p["capture"]["id"], session_hash=world[1])["capture"]["state"] in {
        "expired",
        "failed",
        "unknown",
    }
    assert not world[5].requests


def test_recovery_ignores_unrelated_corrupt_capacity(world):
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    seed_file(world, 123, kind="sources", data={"byte_count": True})
    assert prepare(world)["capture"]["state"] == "verified"
    assert reconcile(world, p["capture"]["id"])["verification"] == "source_verified"
    with pytest.raises(DomainError) as error:
        prepare(world, "new")
    assert error.value.code == "CAPTURE_SOURCE_CAPACITY_UNAVAILABLE"


def test_last_source_slot_not_double_charged(world):
    for n in range(99):
        seed_file(world, n + 1000, kind="sources")
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    assert detail(world, p["capture"]["id"])["state"] == "verified"
    assert reconcile(world, p["capture"]["id"])["verification"] == "source_verified"
    with pytest.raises(DomainError) as error:
        prepare(world, "full")
    assert error.value.code == "CAPTURE_SOURCE_CAPACITY_LIMIT"


def test_identity_tampering_blocks_adoption(world):
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    with world[0].store.connection(write=True) as conn:
        row = conn.execute("SELECT id,metadata FROM private_files WHERE kind='sources'").fetchone()
        data = json.loads(row["metadata"])
        data["capture_id"] = "0" * 32
        conn.execute("UPDATE private_files SET metadata=? WHERE id=?", (encode(data), row["id"]))
    with pytest.raises(DomainError) as error:
        detail(world, p["capture"]["id"])
    assert error.value.code == "CAPTURE_SOURCE_IDENTITY_INVALID"


def test_response_fence_after_projection(world, monkeypatch):
    p = prepare(world)
    original = world[4]._projection

    def changed(*args):
        result = original(*args)
        hide(world, True)
        hide(world, False)
        return result

    monkeypatch.setattr(world[4], "_projection", changed)
    with pytest.raises(DomainError) as error:
        detail(world, p["capture"]["id"])
    assert error.value.code == "CAPTURE_PRIVACY_CHANGED"


def test_blocked_worker_no_replacement(world):
    p = prepare(world)
    approve(world, p)
    entered, released = threading.Event(), threading.Event()
    world[5].before = lambda: (entered.set(), released.wait(3))
    worker = threading.Thread(target=world[4].run_one)
    worker.start()
    assert entered.wait(1)
    second = prepare(world, "second")
    with pytest.raises(DomainError) as error:
        approve(world, second, "second-approve")
    assert error.value.code == "CAPTURE_BUSY"
    world[4].stop(0)
    assert not world[4].run_one()
    released.set()
    worker.join(2)
    assert not world[5].requests


def test_reconcile_fresh_privacy_after_io(world, monkeypatch):
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    original = ImmutableFiles._read_bytes

    def changed(self, row):
        result = original(self, row)
        hide(world, True)
        hide(world, False)
        return result

    monkeypatch.setattr(ImmutableFiles, "_read_bytes", changed)
    with pytest.raises(DomainError) as error:
        reconcile(world, p["capture"]["id"])
    assert error.value.code == "CAPTURE_PRIVACY_CHANGED"


def test_hidden_huge_private_json_never_materialized(world):
    p = prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("PRAGMA ignore_check_constraints=ON")
        conn.execute("UPDATE public_captures SET intent_json=?", ("x" * 1000000,))
    hide(world, True)
    assert cancel(world, p["capture"]["id"])["capture"]["state"] == "cancelled"


def test_actual_loopback_get_explicit_deterministic_work(world):
    import http.client
    import socket
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from desk.connectors.public_capture_transport import PublicCaptureClient
    from desk.agent_run_schemas import RunCreate

    observed = []
    raw = b"<main><p>Version 1 does not support sync.</p><p>Offline only.</p></main>"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            observed.append((self.command, self.path, dict(self.headers)))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)

    class Connection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2)
            self.sock.connect(server.server_address)

    class LocalFixture(PublicCaptureClient):
        def _connection(self, host, deadline, checkpoint):
            checkpoint()
            return Connection(host)

    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        world[4].client = LocalFixture()
        world[4].monotonic = time.monotonic
        p = prepare(world)
        approve(world, p)
        world[4].run_one()
        c = detail(world, p["capture"]["id"])
        assert c["state"] == "verified", c
        assert len(observed) == 1 and observed[0][:2] == ("GET", "/doc")
        assert observed[0][2]["Host"] == "www.python.org"
        assert not {"Cookie", "Authorization", "Referer", "Origin"} & observed[0][2].keys()
        expected = b"Version 1 does not support sync.\nOffline only.\n"
        source = world[0].sources.read_all(
            c["source_id"], session_hash=world[1], selected_ids=[c["source_id"]]
        )
        assert source["content"].encode() == expected
        assert c["acquisition"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
        assert source["sha256"] == hashlib.sha256(expected).hexdigest()
        owner = {"kind": "owner", "session": world[3]}
        run = world[0].agent_runs.create(
            RunCreate(
                goal="Compile the explicitly selected static source",
                retain=True,
                source_ids=[c["source_id"]],
                scope_revision=world[0].agent_runs.scope(owner)["scope_revision"],
            ),
            "work-after-capture",
            owner,
        )["run"]
        for _ in range(40):
            world[0].agent_runs.advance_one()
            world[2][0] += timedelta(seconds=2)
            result = world[0].agent_runs.detail(run["id"], owner)
            if result["run"]["state"] in {"succeeded", "failed", "blocked"}:
                break
        assert result["run"]["state"] == "succeeded"
        assert result["run"]["model_calls"] == 0 and len(result["artifacts"]) == 2
        for artifact in result["artifacts"]:
            record, body = world[0].artifacts.download(artifact["id"], session_hash=world[1])
            assert record["status"] == "verified"
            assert hashlib.sha256(body).hexdigest() == record["sha256"]
        assert len(observed) == 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(2)


@pytest.mark.parametrize("phase", ["reserved", "temp_synced", "published"])
def test_uncertain_publication_recovers_only_final_bytes(world, monkeypatch, phase):
    p = prepare(world)
    approve(world, p)

    def crash(self, name, row):
        if name == phase:
            raise OSError("synthetic crash")

    with monkeypatch.context() as patch:
        patch.setattr(ImmutableFiles, "phase", crash)
        world[4].run_one()
    c = detail(world, p["capture"]["id"])
    assert c["state"] == "unknown"
    result = reconcile(world, c["id"])
    assert result["verification"] == (
        "source_verified" if phase == "published" else "source_unknown"
    )
    assert len(world[5].requests) == 1


def test_nlink_two_remains_unknown_without_repair(world, monkeypatch):
    import desk.file_store as files

    p = prepare(world)
    approve(world, p)
    original = files.os.unlink

    def fail(path, *args, **kwargs):
        if str(path).endswith(".pending"):
            raise OSError("crash between link and unlink")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(files.os, "unlink", fail)
        world[4].run_one()
    c = detail(world, p["capture"]["id"])
    result = reconcile(world, c["id"])
    assert result["verification"] == "source_unknown"
    final = world[0].store.directory / "sources" / (c["source_id"] + ".txt")
    assert final.stat().st_nlink == 2
    assert (final.parent / ("." + c["source_id"] + ".pending")).exists()


@pytest.mark.parametrize("direction", ["review", "execution"])
def test_clock_rollback_invalidates(world, direction):
    p = prepare(world)
    if direction == "execution":
        approve(world, p)
    world[2][0] -= timedelta(seconds=1)
    if direction == "review":
        with pytest.raises(DomainError):
            approve(world, p)
    else:
        world[4].run_one()
    assert not world[5].requests


def test_receipt_loss_fails_closed_without_get(world):
    p = prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("DELETE FROM public_capture_operations")
    with pytest.raises(DomainError) as error:
        approve(world, p)
    assert error.value.code == "CAPTURE_RECEIPT_INVALID"
    assert not world[5].requests


def test_history_200_and_receipts_600_are_lifetime_bounds(world):
    first = None
    for number in range(200):
        p = prepare(world, f"p-{number}")
        first = first or p
        approve(world, p, f"a-{number}")
        world[4].cancel(
            p["capture"]["id"], {"expected_version": 2}, f"c-{number}", session_hash=world[1]
        )
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM public_captures").fetchone()[0] == 200
        assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 600
    assert prepare(world, "p-0")["capture"]["state"] == "cancelled"
    assert (
        world[4].cancel(
            first["capture"]["id"], {"expected_version": 2}, "c-0", session_hash=world[1]
        )["capture"]["state"]
        == "cancelled"
    )
    with pytest.raises(DomainError) as error:
        prepare(world, "p-201")
    assert error.value.code == "CAPTURE_HISTORY_LIMIT"
    assert not world[5].requests


def test_new_owner_can_read_but_not_approve_old_review(world):
    p = prepare(world)
    token = world[0].store.authenticate("owner", "fixture-only")
    new_session = hashlib.sha256(token.encode()).hexdigest()
    assert world[4].detail(p["capture"]["id"], session_hash=new_session)["capture"]["url"]
    c = p["capture"]
    with pytest.raises(DomainError) as error:
        world[4].approve(
            c["id"],
            {
                "expected_version": 1,
                "intent_hash": c["intent_hash"],
                "public_only": True,
                "retain_snapshot": True,
            },
            "newowner",
            session_hash=new_session,
        )
    assert error.value.code == "CAPTURE_APPROVAL_EXPIRED"


def test_noninjected_client_factory_module_path(world, monkeypatch):
    import desk.connectors.public_capture_transport as transport

    world[4].client = None
    monkeypatch.setattr(transport, "PublicCaptureClient", lambda: world[5])
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    assert detail(world, p["capture"]["id"])["state"] == "verified"


def test_prepare_never_uses_dns_or_socket(world, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("prepare must be local only")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert prepare(world)["capture"]["state"] == "review"


def test_worker_control_failure_disables_without_replay(world, monkeypatch):
    def fail():
        raise RuntimeError("synthetic durable control unavailable")

    monkeypatch.setattr(world[4], "run_one", fail)
    world[4].start()
    world[4]._wake.set()
    world[4]._thread.join(2)
    assert world[4]._worker_error == "CAPTURE_WORKER_UNAVAILABLE"
    assert not world[4].capabilities(session_hash=world[1])["enabled"]
    with pytest.raises(DomainError) as error:
        prepare(world)
    assert error.value.code == "CAPTURE_WORKER_UNAVAILABLE"


def test_stop_wakes_and_joins_even_on_database_failure(world, monkeypatch):
    joins = []
    world[4]._thread = SimpleNamespace(join=lambda timeout: joins.append(timeout))

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(world[0].store, "connection", fail)
    with pytest.raises(RuntimeError):
        world[4].stop(0.2)
    assert world[4]._stopping and world[4]._wake.is_set() and joins == [0.2]


def test_racing_upload_consumes_slot_after_get(world):
    for number in range(99):
        seed_file(world, number + 2000, kind="sources")
    p = prepare(world)
    approve(world, p)
    world[5].after = lambda: seed_file(world, 5000, kind="sources")
    world[4].run_one()
    c = detail(world, p["capture"]["id"])
    assert c["state"] == "unknown" and c["source_id"] is None
    assert c["error_code"] == "CAPTURE_SOURCE_CAPACITY_LIMIT"
    assert len(world[5].requests) == 1


def test_cancel_during_readback_prevents_verification_commit(world, monkeypatch):
    p = prepare(world)
    cid = p["capture"]["id"]
    approve(world, p)
    original = ImmutableFiles._read_bytes

    def cancel_after_read(self, row):
        body = original(self, row)
        cancel(world, cid)
        return body

    with monkeypatch.context() as patch:
        patch.setattr(ImmutableFiles, "_read_bytes", cancel_after_read)
        world[4].run_one()
    c = detail(world, cid)
    assert c["state"] == "cancelled" and c["source_status"] == "unknown"
    assert reconcile(world, cid)["verification"] == "source_verified"
    assert detail(world, cid)["state"] == "cancelled"


@pytest.mark.parametrize("key", ["é" * 100, "key\x00tail", "newline\nkey", " ", "x" * 101])
def test_invalid_operation_key_rejected_before_persistence(world, key):
    with pytest.raises(DomainError) as error:
        prepare(world, key)
    assert error.value.code == "OPERATION_ID_REQUIRED"
    with world[0].store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM public_captures").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM public_capture_operations").fetchone()[0] == 0


def test_forged_verified_state_without_acquisition_fails_closed(world):
    p = prepare(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE public_captures SET state='verified'")
    with pytest.raises(DomainError) as error:
        detail(world, p["capture"]["id"])
    assert error.value.code in {"CAPTURE_RECEIPT_INVALID", "CAPTURE_SOURCE_IDENTITY_INVALID"}


def test_boolean_integer_metadata_identity_fails_canonical_hash(world):
    p = prepare(world)
    approve(world, p)
    world[4].run_one()
    with world[0].store.connection(write=True) as conn:
        row = conn.execute("SELECT id,metadata FROM private_files WHERE kind='sources'").fetchone()
        data = json.loads(row["metadata"])
        data["policy_version"] = True
        conn.execute("UPDATE private_files SET metadata=? WHERE id=?", (encode(data), row["id"]))
    with pytest.raises(DomainError) as error:
        detail(world, p["capture"]["id"])
    assert error.value.code == "CAPTURE_SOURCE_IDENTITY_INVALID"
