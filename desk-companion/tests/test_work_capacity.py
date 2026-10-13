"""Local SQLite and HTTP capacity checks; no live provider/browser claims."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.artifacts import ArtifactInput
from desk.file_store import ImmutableFiles
from desk.sources import SourceInput
from desk.store import DomainError, encode
from desk.work_capacity import CapacityDimension, WorkCapacityService
from desk.work_limits import ARTIFACT_BYTES, SOURCE_BYTES
from test_work_search import hide, seed_file, seed_run, world as search_world


@pytest.fixture
def world(tmp_path):
    return search_world.__wrapped__(tmp_path)


def capacity(world):
    return WorkCapacityService(world[0]).snapshot(session_hash=world[1])


def watch(world, number, state="cancelled"):
    with world[0].store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO responsibilities VALUES(?,?,1,1,?,'','','','',1,0,1,'',0,NULL,0)",
            (f"{number:032x}", "malformed private body", state),
        )


def test_empty_shared_limits_and_strict_output(world):
    result = capacity(world)
    assert set(result) == {
        "basis",
        "advisory",
        "observed_at",
        "sources",
        "artifacts",
        "runs",
        "watches",
    }
    assert result["basis"] == "retained_reservations" and result["advisory"] is True
    for resource, limit in [("sources", 100), ("artifacts", 400), ("runs", 100), ("watches", 20)]:
        assert result[resource]["count"] == dict(
            limit=limit, used=0, remaining=limit, state="known"
        )
    for resource in ["sources", "artifacts"]:
        assert result[resource]["bytes"] == dict(
            limit=67108864, used=0, remaining=67108864, state="known"
        )
    assert result["sources"]["file_bytes"] == SOURCE_BYTES
    assert result["artifacts"]["file_bytes"] == ARTIFACT_BYTES
    assert result["artifacts"]["per_run_count"] == 4
    assert result["artifacts"]["per_run_bytes"] == 1048576
    for service, resource in [(world[0].sources, "sources"), (world[0].artifacts, "artifacts")]:
        limits = service.listing(session_hash=world[1])["limits"]
        assert limits["count"] == result[resource]["count"]["limit"]
        assert limits["total_bytes"] == result[resource]["bytes"]["limit"]
        assert limits["file_bytes"] == result[resource]["file_bytes"]


@pytest.mark.parametrize(
    "resource,cap", [("sources", 100), ("artifacts", 400), ("runs", 100), ("watches", 20)]
)
def test_full_and_cap_plus_many_never_claim_false_exact_total(world, resource, cap):
    def add(i):
        if resource == "runs":
            seed_run(world, i, state=["cancelled", "failed", "succeeded"][i % 3])
        elif resource == "watches":
            watch(world, i, ["cancelled", "expired", "budget_exhausted"][i % 3])
        else:
            seed_file(world, i, kind=resource, status=["reserved", "unknown", "verified"][i % 3])

    for i in range(cap):
        add(i)
    assert capacity(world)[resource]["count"] == dict(
        limit=cap, used=cap, remaining=0, state="known"
    )
    for i in range(cap, cap + 7):
        add(i)
    result = capacity(world)[resource]
    assert result["count"] == dict(limit=cap, used=None, remaining=None, state="over_limit")
    if "bytes" in result:
        assert result["bytes"]["state"] == "unavailable"
        assert result["bytes"]["used"] is result["bytes"]["remaining"] is None


@pytest.mark.parametrize("kind,size", [("sources", SOURCE_BYTES), ("artifacts", ARTIFACT_BYTES)])
def test_exact_byte_limit_independent_from_count_and_exact_over_limit(world, kind, size):
    n = 67108864 // size
    for i in range(n):
        seed_file(world, i, kind=kind, data={"byte_count": size})
    result = capacity(world)[kind]
    assert result["bytes"] == dict(limit=67108864, used=67108864, remaining=0, state="known")
    assert result["count"]["remaining"] > 0
    seed_file(world, n, kind=kind, data={"byte_count": 1})
    assert capacity(world)[kind]["bytes"] == dict(
        limit=67108864, used=67108865, remaining=0, state="over_limit"
    )


@pytest.mark.parametrize(
    "raw",
    [
        "broken",
        "[]",
        "null",
        "true",
        "{}",
        '{"byte_count":true}',
        '{"byte_count":false}',
        '{"byte_count":"1"}',
        '{"byte_count":1.0}',
        '{"byte_count":0}',
        '{"byte_count":-1}',
        '{"byte_count":1048577}',
        '{"byte_count":9223372036854775808}',
        '{"byte_count":1e300}',
        '{"byte_count":{"private":[1,2,3]}}',
        '{"byte_count":1,"byte_count":9}',
        '{"byte_count":1,"x":"' + "中" * 23000 + '"}',
        '{"byte_count":' + "[" * 2100 + "1" + "]" * 2100 + "}",
        b'{"byte_count":1}',
    ],
)
def test_invalid_metadata_counts_retained_but_bytes_unknown(world, raw):
    seed_file(world, 1, kind="sources")
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE private_files SET metadata=?", (raw,))
    result = capacity(world)
    assert result["sources"]["count"]["used"] == 1
    assert result["sources"]["bytes"]["state"] == "unavailable"
    assert result["sources"]["bytes"]["used"] is result["sources"]["bytes"]["remaining"] is None
    assert result["artifacts"]["bytes"]["used"] == 0
    assert len(encode(result)) < 1400


def test_authoritative_buckets_and_excluded_fields_never_leak(world):
    seed_file(
        world,
        1,
        kind="artifacts",
        data={
            "id": "secret-id",
            "kind": "sources",
            "byte_count": 7,
            "run_id": {"hostile": [1, 2]},
            "supersedes_id": "secret-old",
        },
    )
    seed_file(world, 2, kind="other")
    seed_run(world, 3)
    watch(world, 4)
    result = capacity(world)
    assert result["sources"]["count"]["used"] == 0
    assert result["artifacts"]["count"]["used"] == 1
    assert result["artifacts"]["bytes"]["used"] == 7
    for secret in [
        "secret",
        "never",
        "/private",
        world[1],
        "run_id",
        "operation",
        "status",
        "provenance",
    ]:
        assert secret not in encode(result)


@pytest.mark.parametrize("session", [None, "owner", "0" * 64, {"kind": "owner"}])
def test_actual_session_required(world, session):
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        WorkCapacityService(world[0]).snapshot(session_hash=session)


@pytest.mark.parametrize(
    "change,code",
    [
        ("hide", "PRIVATE_CONTEXT_HIDDEN"),
        ("hide_show", "WORK_CAPACITY_PRIVACY_CHANGED"),
        ("logout", "OWNER_SIGN_IN_REQUIRED"),
        ("expire", "OWNER_SIGN_IN_REQUIRED"),
        ("epoch", "WORK_CAPACITY_PRIVACY_CHANGED"),
    ],
)
def test_final_fresh_authority_check(world, monkeypatch, change, code):
    service = WorkCapacityService(world[0])
    original = service._read

    def delayed(conn):
        result = original(conn)
        if change.startswith("hide"):
            hide(world, True)
            if change == "hide_show":
                hide(world, False)
        elif change == "logout":
            world[0].store.logout(world[3])
        elif change == "expire":
            world[2][0] += timedelta(hours=9)
        else:
            with world[0].store.connection(write=True) as other:
                other.execute("UPDATE personal_settings SET epoch=epoch+1")
        return result

    monkeypatch.setattr(service, "_read", delayed)
    with pytest.raises(DomainError, match=code):
        service.snapshot(session_hash=world[1])


def test_initial_hidden_and_expired(world):
    hide(world, True)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        capacity(world)
    hide(world, False)
    world[2][0] += timedelta(hours=9)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        capacity(world)


def test_one_snapshot_across_concurrent_changes(world, monkeypatch):
    service = WorkCapacityService(world[0])
    original = service._files

    def delayed(conn, kind, *args):
        result = original(conn, kind, *args)
        if kind == "sources":
            seed_file(world, 1, kind="artifacts")
            seed_run(world, 2)
            watch(world, 3)
        return result

    monkeypatch.setattr(service, "_files", delayed)
    result = service.snapshot(session_hash=world[1])
    assert all(result[r]["count"]["used"] == 0 for r in ["sources", "artifacts", "runs", "watches"])
    assert capacity(world)["artifacts"]["count"]["used"] == 1


def test_no_effects_construction_query_only_no_files_or_service_reads(world, monkeypatch):
    runtime = world[0]
    seed_file(world, 1)
    with runtime.store.connection() as conn:
        before = list(conn.iterdump())

    def forbidden(*args, **kwargs):
        pytest.fail("Capacity attempted a mutation, body read, reconciliation or unrelated service")

    for method in [
        "_directory",
        "_read_bytes",
        "checked",
        "metadata",
        "reconcile",
        "listing",
        "put",
    ]:
        monkeypatch.setattr(ImmutableFiles, method, forbidden)
    for service, methods in [
        (runtime.sources, ["read", "read_all", "covered", "listing"]),
        (runtime.artifacts, ["download", "read", "listing"]),
        (runtime.agent_runs, ["scope", "advance_one"]),
        (runtime.responsibilities, ["listing", "advance"]),
    ]:
        for method in methods:
            monkeypatch.setattr(service, method, forbidden)
    connection = runtime.store.connection
    queries = []

    @contextmanager
    def checked_connection(write=False):
        assert not write
        with connection() as conn:
            conn.set_trace_callback(queries.append)
            yield conn

    monkeypatch.setattr(runtime.store, "connection", checked_connection)
    WorkCapacityService(runtime).snapshot(session_hash=world[1])
    assert sum(q == "PRAGMA query_only=ON" for q in queries) == 2
    assert not any(q.startswith(("INSERT", "UPDATE", "DELETE", "CREATE")) for q in queries)
    with connection() as conn:
        assert list(conn.iterdump()) == before


def test_missing_schema_has_safe_error_not_empty_usage(world):
    with world[0].store.connection(write=True) as conn:
        conn.execute("ALTER TABLE private_files RENAME TO missing_files")
    with pytest.raises(DomainError) as error:
        capacity(world)
    assert (error.value.code, error.value.status) == ("WORK_CAPACITY_UNAVAILABLE", 409)


@pytest.mark.parametrize("value", [True, 1.0, "1", -1, 2**53])
def test_output_integer_contract_does_not_coerce(value):
    with pytest.raises(ValidationError):
        CapacityDimension(limit=100, used=value, remaining=99, state="known")


def test_stale_observation_does_not_reserve_and_parallel_admission_is_authoritative(world):
    for i in range(99):
        seed_file(world, i, kind="sources")
    assert capacity(world)["sources"]["count"]["remaining"] == 1

    def create(i):
        try:
            return world[0].sources.ingest(
                SourceInput(name="new.txt", format="text"), b"x", f"new-{i}", session_hash=world[1]
            )["source"]["id"]
        except DomainError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert results.count("FILE_CAPACITY_LIMIT") == 1
    assert capacity(world)["sources"]["count"]["used"] == 100


@pytest.mark.parametrize("kind", ["sources", "artifacts"])
@pytest.mark.parametrize("full", ["count", "bytes"])
def test_same_key_recovery_survives_full_capacity(world, kind, full):
    runtime, session, _, _ = world

    def publish(key):
        if kind == "sources":
            return runtime.sources.ingest(
                SourceInput(name="real.txt", format="text"), b"x", key, session_hash=session
            )["source"]
        return runtime.artifacts.publish(
            ArtifactInput(format="text", display_name="Real", content="x"),
            key,
            session_hash=session,
            selected_source_ids=[],
        )["artifact"]

    first = publish("original")
    cap, file_cap = (100, SOURCE_BYTES) if kind == "sources" else (400, ARTIFACT_BYTES)
    sizes = (
        [1] * (cap - 1)
        if full == "count"
        else [file_cap] * (67108864 // file_cap - 1) + [file_cap - 1]
    )
    for i, size in enumerate(sizes):
        seed_file(world, i, kind=kind, data={"byte_count": size})
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE private_files SET status='unknown' WHERE id=?", (first["id"],))
    before = capacity(world)[kind]
    assert before[full]["remaining"] == 0
    with pytest.raises(DomainError, match="FILE_CAPACITY_LIMIT"):
        publish("new-operation")
    recovered = publish("original")
    assert recovered["id"] == first["id"] and recovered["status"] == "verified"
    assert capacity(world)[kind] == before


def test_per_run_limit_preserved_and_global_counts_include_superseded_unlinked(world):
    runtime, session, _, _ = world
    previous = None
    for i in range(4):
        item = runtime.artifacts.publish(
            ArtifactInput(
                format="text", display_name="Output", content="x", supersedes_id=previous
            ),
            f"run-output-{i}",
            session_hash=session,
            selected_source_ids=[],
            run_id="standalone-scope",
        )["artifact"]
        previous = item["id"]
    assert capacity(world)["artifacts"]["count"]["used"] == 4
    with pytest.raises(DomainError, match="ARTIFACT_RUN_LIMIT"):
        runtime.artifacts.publish(
            ArtifactInput(format="text", display_name="Output", content="x"),
            "extra",
            session_hash=session,
            selected_source_ids=[],
            run_id="standalone-scope",
        )


def test_http_owner_no_store_origin_and_read_only(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        assert client.get("/api/work/capacity").status_code == 403
        client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "fixture-only"},
        )
        with app.state.store.connection() as conn:
            before = list(conn.iterdump())
        response = client.get("/api/work/capacity")
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["sources"]["count"]["used"] == 0
        assert (
            client.get("/api/work/capacity", headers={"Origin": "https://example.com"}).status_code
            == 403
        )
        with app.state.store.connection() as conn:
            assert list(conn.iterdump()) == before


@pytest.mark.parametrize("kind", ["controller", "display"])
@pytest.mark.parametrize("transport", ["bearer", "device_cookie", "owner_cookie"])
def test_http_real_paired_clients_denied(tmp_path, kind, transport):
    from desk.access import PairingClaim, PairingDecision, PairingRequest

    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    access = app.state.runtime.access
    code = access.issue(kind, "issue")
    requested = access.request(PairingRequest(code=code["code"], name="Synthetic paired client"))
    access.decide(PairingDecision(request_id=requested["request_id"], action="approve"), "decide")
    paired = access.claim(
        PairingClaim(request_id=requested["request_id"], secret=requested["secret"])
    )
    with TestClient(app) as client:
        headers = {}
        if transport == "bearer":
            headers["Authorization"] = "Bearer " + paired["token"]
        else:
            client.cookies.set(
                "desk_companion_device"
                if transport == "device_cookie"
                else "desk_companion_session",
                paired["token"],
            )
        response = client.get("/api/work/capacity", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"


@pytest.mark.parametrize(
    "table,column,raw",
    [
        ("private_files", "metadata", '{"byte_count":1}\x00garbage'),
        ("settings", "data", '{"hide_private":false}\x00garbage'),
    ],
)
def test_literal_nul_cannot_make_malformed_json_appear_valid(world, table, column, raw):
    seed_file(world, 1, kind="sources")
    with world[0].store.connection(write=True) as conn:
        conn.execute(f"UPDATE {table} SET {column}=?", (raw,))
    if table == "settings":
        with pytest.raises(DomainError, match="WORK_CAPACITY_UNAVAILABLE"):
            capacity(world)
    else:
        assert capacity(world)["sources"]["bytes"]["state"] == "unavailable"
