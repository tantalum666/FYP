"""Local SQLite retrieval tests; no semantic/model or actual-browser claims."""

import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.artifacts import ArtifactInput
from desk.file_store import ImmutableFiles
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.sources import SourceInput
from desk.store import DomainError, Store, encode
from desk.work_search import WorkSearchInput, WorkSearchService


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 10, 13, 12, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    token = runtime.store.authenticate("owner", "fixture-only")
    session = hashlib.sha256(token.encode()).hexdigest()
    runtime.work_search = WorkSearchService(runtime)
    return runtime, session, clock, token


def opaque(number):
    return f"{number:032x}"


def seed_run(world, number=1, goal="Saved work", **changes):
    runtime, session, _, _ = world
    data = {
        "goal": goal,
        "mode": "deterministic",
        "plan_revision": 1,
        "source_ids": [],
        "artifact_ids": [],
        "current_artifact_ids": [],
        "report": {"secret": "never project report"},
        "evidence": [{"content": "never search content"}],
        "pending_tool": {"arguments": "never project arguments"},
        **changes.pop("data", {}),
    }
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?)",
            (
                opaque(number),
                changes.pop("state", "succeeded"),
                changes.pop("version", 1),
                1,
                None,
                session,
                encode(data),
                changes.pop("updated_at", "2026-10-12T12:00:00Z"),
            ),
        )
    assert not changes
    return opaque(number)


def seed_file(world, number=1000, *, kind="artifacts", name="Work report v1", **changes):
    data = {
        "id": opaque(number),
        "kind": kind,
        "display_name": name,
        "format": "markdown",
        "byte_count": 17,
        "created_at": "2026-10-12T12:00:00Z",
        "run_id": None,
        "provenance": [],
        "sha256": "never project digest",
        "path": "/private/never-project",
        "content": "never search body",
        **changes.pop("data", {}),
    }
    with world[0].store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO private_files VALUES(?,?,?,?,?,?,?)",
            (
                opaque(number),
                kind,
                "operation-" + opaque(number),
                "never-project-request",
                encode(data),
                changes.pop("status", "verified"),
                "never project errors",
            ),
        )
    assert not changes
    return opaque(number)


def search(world, query="", **changes):
    return world[0].work_search.search(
        WorkSearchInput(query=query, **changes),
        session_hash=world[1],
    )


def change_data(world, run_id, **changes):
    with world[0].store.connection(write=True) as conn:
        row = conn.execute("SELECT data FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        conn.execute(
            "UPDATE agent_runs SET data=? WHERE id=?",
            (encode({**json.loads(row[0]), **changes}), run_id),
        )


def hide(world, value):
    with world[0].store.connection() as conn:
        version = world[0].store.settings(conn)["version"]
    world[0].store.update_settings(
        SettingsInput(expected_version=version, timezone="UTC", hide_private=value),
        f"privacy-{version}",
    )


def test_strong_older_matches_outrank_newer_linked_and_phrase_matches(world):
    source = seed_file(world, 2000, kind="sources", name="Launch plan.md")
    exact = seed_run(world, 1, "Launch plan", updated_at="2020-01-01T00:00:00Z")
    phrase = seed_run(world, 2, "Revisit the launch plan tomorrow")
    terms = seed_run(world, 3, "Plan the next launch")
    linked = seed_run(world, 4, "Review selected evidence", data={"source_ids": [source]})
    result = search(world, "launch plan", kind="run")
    assert [item["id"] for item in result["items"]] == [exact, phrase, terms, linked]
    assert [item["match_reason"] for item in result["items"]] == [
        "exact_title",
        "phrase",
        "all_terms",
        "linked_metadata",
    ]
    assert result["items"][-1]["matched_fields"] == ["source_name"]
    assert search(world, "launch missing")["total"] == 0
    assert search(world, exact.upper())["items"][0]["match_reason"] == "exact_id"


@pytest.mark.parametrize(
    "query", ["研究报告", "ＲＥＰＯＲＴ", "report", "研究报告 2026", "报告 REPORT"]
)
def test_unicode_mixed_fullwidth_casefold_and_literal_chinese(world, query):
    seed_run(world, goal="研究报告 REPORT 2026")
    assert search(world, query)["total"] == 1
    assert search(world, "调查报告")["total"] == 0


def test_normalized_whitespace_diacritics_casefold_and_expansion(world):
    seed_run(world, goal="Straße Café　项目")
    assert search(world, "STRASSE  CAFE\u0301\t项目")["total"] == 1
    assert search(world, "  STRASSE CAFÉ 项目  ")["items"][0]["match_reason"] == "exact_title"
    seed_run(world, 2, "株式会社" * 200)
    assert search(world, "㍿" * 200)["total"] == 1


@pytest.mark.parametrize("query", ["%", "_", "' OR 1=1 --", "[a-z].*", "<script>alert(1)</script>"])
def test_query_is_literal_data_and_never_sql_regex_or_html(world, query):
    own = seed_run(world, goal=query)
    seed_run(world, 2, "Unrelated record")
    result = search(world, query)
    assert [item["id"] for item in result["items"]] == [own]
    assert result["items"][0]["title"] == query


def test_complete_admitted_corpus_includes_all_600_records_and_deterministic_pages(world):
    for number in range(1, 101):
        seed_run(world, number, f"Record {number}")
    for number in range(1000, 1100):
        seed_file(world, number, kind="sources", name=f"Source {number}.md")
    for number in range(2000, 2400):
        seed_file(world, number, name=f"Artifact {number}")
    first = search(world, limit=50)
    assert first["total"] == 600 and first["next_offset"] == 50
    assert first["search_scope"] == "local_metadata" and first["ranking"] == "lexical_v1"
    assert first["file_status_basis"] == "last_recorded"
    ids = [item["id"] for item in first["items"]]
    page = first
    while page["next_offset"] is not None:
        page = search(world, limit=50, offset=page["next_offset"], snapshot=first["snapshot"])
        ids += [item["id"] for item in page["items"]]
    assert len(ids) == len(set(ids)) == 600
    assert ids == sorted(ids[:400]) + sorted(ids[400:500]) + sorted(ids[500:])
    assert search(world, "Artifact 2399")["items"][0]["id"] == opaque(2399)
    assert search(world, "Source 1099.md")["items"][0]["id"] == opaque(1099)
    assert search(world, limit=50) == first
    assert search(world, offset=600, snapshot=first["snapshot"])["items"] == []


@pytest.mark.parametrize("kind,cap", [("run", 100), ("sources", 100), ("artifacts", 400)])
def test_over_capacity_fails_instead_of_claiming_partial_search_complete(world, kind, cap):
    for number in range(1, cap + 2):
        if kind == "run":
            seed_run(world, number)
        else:
            seed_file(world, number, kind=kind)
    with pytest.raises(DomainError) as error:
        search(world, kind="source")
    assert (error.value.code, error.value.status) == ("WORK_SEARCH_CAPACITY_EXCEEDED", 409)


def test_snapshot_binds_normalized_query_filter_session_and_metadata(world):
    item = seed_run(world, goal="Launch plan")
    seed_run(world, 2, "Launch plan")
    first = search(world, "launch", limit=1, kind="run")
    assert (
        search(world, "  ＬＡＵＮＣＨ ", limit=1, kind="run", offset=1, snapshot=first["snapshot"])[
            "total"
        ]
        == 2
    )
    for changes in [{"query": "plan", "kind": "run"}, {"query": "launch", "kind": "all"}]:
        with pytest.raises(DomainError, match="WORK_SEARCH_CHANGED"):
            search(world, offset=1, snapshot=first["snapshot"], **changes)
    token = world[0].store.authenticate("owner", "fixture-only")
    with pytest.raises(DomainError, match="WORK_SEARCH_CHANGED"):
        world[0].work_search.search(
            WorkSearchInput(query="launch", kind="run", offset=1, snapshot=first["snapshot"]),
            session_hash=hashlib.sha256(token.encode()).hexdigest(),
        )
    change_data(world, item, goal="Launch revised plan")
    with pytest.raises(DomainError, match="WORK_SEARCH_CHANGED"):
        search(world, "launch", kind="run", offset=1, snapshot=first["snapshot"])


def test_status_only_file_change_invalidates_pagination(world):
    artifact = seed_file(world)
    first = search(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE private_files SET status='unknown' WHERE id=?", (artifact,))
    with pytest.raises(DomainError, match="WORK_SEARCH_CHANGED"):
        search(world, snapshot=first["snapshot"])


def test_nonsearchable_body_and_tool_change_does_not_change_search_snapshot(world):
    run = seed_run(world)
    first = search(world)
    change_data(world, run, report="new report", pending_tool={"arguments": "secret"})
    assert search(world) == first
    assert search(world, "never")["total"] == 0 and search(world, "secret")["total"] == 0


def test_current_earlier_unknown_unlinked_and_no_invented_original_goal(world):
    source = seed_file(world, 2000, kind="sources", name="Prototype findings.md")
    run = seed_run(world, goal="Current revised goal", data={"source_ids": [source]})
    earlier = seed_file(world, 1000, data={"run_id": run, "supersedes_id": opaque(1002)})
    current = seed_file(world, 1001, data={"run_id": run, "provenance": [{"source_id": source}]})
    prelink = seed_file(world, 1002, data={"run_id": run})
    missing = seed_file(world, 1003, data={"run_id": opaque(4000)})
    standalone = seed_file(world, 1004)
    change_data(world, run, artifact_ids=[earlier, current], current_artifact_ids=[current])
    results = {i["id"]: i for i in search(world, kind="artifact")["items"]}
    assert results[earlier]["output_membership"] == "earlier"
    assert results[current]["output_membership"] == "current"
    assert (
        results[prelink]["output_membership"] == results[missing]["output_membership"] == "unknown"
    )
    assert results[standalone]["output_membership"] == "unlinked"
    assert all(
        results[i]["current_linked_goal"] == "Current revised goal"
        for i in (earlier, current, prelink)
    )
    assert results[missing]["current_linked_goal"] is None
    assert len({i["id"] for i in results.values() if i["title"] == "Work report v1"}) == 5
    linked = search(world, "revised", kind="artifact")
    assert linked["total"] == 3 and linked["items"][0]["matched_fields"] == ["current_linked_goal"]
    by_source = search(world, "Prototype", kind="artifact")
    assert by_source["total"] == 1 and by_source["items"][0]["id"] == current
    assert by_source["items"][0]["source_names"] == ["Prototype findings.md"]
    change_data(world, run, goal="New direction", current_artifact_ids=[])
    assert search(world, "revised", kind="artifact")["total"] == 0
    result = search(world, "New direction", kind="artifact")
    assert all(i["current_linked_goal"] == "New direction" for i in result["items"])
    assert {i["output_membership"] for i in result["items"]} == {"earlier", "unknown"}


@pytest.mark.parametrize("current", [None, "not a list", {}, [3], [opaque(1000), opaque(1000)]])
def test_legacy_malformed_current_lists_are_unknown_even_when_in_history(world, current):
    run = seed_run(world, data={"artifact_ids": [opaque(1000)], "current_artifact_ids": current})
    seed_file(world, data={"run_id": run})
    assert search(world, kind="artifact")["items"][0]["output_membership"] == "unknown"


def test_current_membership_does_not_require_history_in_legacy_parent(world):
    run = seed_run(world, data={"artifact_ids": None, "current_artifact_ids": [opaque(1000)]})
    seed_file(world, data={"run_id": run})
    assert search(world, kind="artifact")["items"][0]["output_membership"] == "current"


def test_invalid_legacy_scalar_fields_are_unavailable_not_coerced_or_leaked(world):
    run = seed_run(
        world,
        data={"goal": ["not a title"], "mode": {}, "plan_revision": True, "source_ids": [3]},
        state="secret arbitrary state",
        version=0,
        updated_at="not a timestamp",
    )
    seed_file(
        world,
        data={
            "run_id": "/private/path",
            "display_name": "/private/file.md",
            "format": {"private": "config"},
            "byte_count": True,
            "created_at": "untrusted timestamp",
            "provenance": "wrong",
        },
        status="reserved",
    )
    file, work = search(world)["items"]
    assert work["id"] == run and work["title"] == "" and work["state"] == "unknown"
    assert work["version"] is work["mode"] is work["plan_revision"] is work["timestamp"] is None
    assert file["title"] == "" and file["run_id"] is None
    assert file["output_membership"] == "unknown" and file["recorded_status"] == "unknown"
    assert file["format"] is file["byte_count"] is file["timestamp"] is None
    assert "/private/" not in encode(search(world))


@pytest.mark.parametrize(
    "provenance", [None, "bad", {}, [1], [{"source_id": []}], [{"source_id": {}}]]
)
def test_malformed_provenance_never_crashes_or_converts_values_to_source_ids(world, provenance):
    seed_file(world, data={"provenance": provenance})
    assert search(world)["items"][0]["source_names"] == []


@pytest.mark.parametrize("raw", ["{broken", "null", "[]", '"string"', "[" * 1100])
@pytest.mark.parametrize("table,column", [("agent_runs", "data"), ("private_files", "metadata")])
def test_irrecoverable_metadata_reports_clear_error_without_partial_results(
    world, raw, table, column
):
    seed_run(world)
    seed_file(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute(f"UPDATE {table} SET {column}=?", (raw,))
    with pytest.raises(DomainError, match="WORK_SEARCH_METADATA_INVALID"):
        search(world)


def test_compact_strict_whitelist_excludes_all_private_internal_fields(world):
    seed_run(world)
    seed_file(world)
    seed_file(world, 2000, kind="sources")
    result = search(world)
    common = {"kind", "id", "title", "timestamp", "matched_fields", "match_reason"}
    fields = {
        "run": {"state", "version", "mode", "plan_revision", "source_names"},
        "source": {"format", "byte_count", "recorded_status", "revision"},
        "artifact": {
            "format",
            "byte_count",
            "recorded_status",
            "run_id",
            "current_linked_goal",
            "output_membership",
            "source_names",
        },
    }
    for item in result["items"]:
        assert set(item) == common | fields[item["kind"]]
    for secret in [
        world[1],
        "operation-",
        "never",
        "/private/",
        "session_hash",
        "sha256",
        '"report":',
        "evidence",
        "pending_tool",
        "provider",
    ]:
        assert secret not in encode(result)


@pytest.mark.parametrize("session", [None, "owner", "0" * 64, {"kind": "owner"}])
def test_real_owner_session_required(world, session):
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        world[0].work_search.search(WorkSearchInput(), session_hash=session)


def test_hidden_and_expired_sessions_cannot_read_search(world):
    hide(world, True)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        search(world)
    hide(world, False)
    world[2][0] += timedelta(hours=9)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        search(world)


@pytest.mark.parametrize(
    "change,code",
    [
        ("hide", "PRIVATE_CONTEXT_HIDDEN"),
        ("hide_show", "WORK_SEARCH_PRIVACY_CHANGED"),
        ("revoke", "OWNER_SIGN_IN_REQUIRED"),
        ("expire", "OWNER_SIGN_IN_REQUIRED"),
        ("consent", "WORK_SEARCH_PRIVACY_CHANGED"),
    ],
)
@pytest.mark.parametrize("stage", ["rows", "corpus"])
def test_delayed_reads_recheck_actual_privacy_and_session(world, monkeypatch, change, code, stage):
    seed_run(world)
    service = world[0].work_search
    method = "_rows" if stage == "rows" else "_corpus"
    original = getattr(service, method)

    def delayed(*args):
        result = original(*args)
        if change.startswith("hide"):
            hide(world, True)
            if change == "hide_show":
                hide(world, False)
        elif change == "revoke":
            world[0].store.logout(world[3])
        elif change == "expire":
            world[2][0] += timedelta(hours=9)
        else:
            with world[0].store.connection(write=True) as conn:
                conn.execute("UPDATE personal_settings SET epoch=epoch+1 WHERE id=1")
        return result

    monkeypatch.setattr(service, method, delayed)
    with pytest.raises(DomainError, match=code):
        search(world)


def test_tables_are_read_from_one_consistent_sqlite_snapshot(world, monkeypatch):
    run = seed_run(world, goal="Old goal")
    artifact = seed_file(world, data={"run_id": run})
    service = world[0].work_search
    original = service._rows

    def rows(conn):
        change_data(world, run, goal="New goal")
        with world[0].store.connection(write=True) as writer:
            data = json.loads(
                writer.execute(
                    "SELECT metadata FROM private_files WHERE id=?", (artifact,)
                ).fetchone()[0]
            )
            writer.execute(
                "UPDATE private_files SET metadata=? WHERE id=?",
                (encode({**data, "display_name": "New name"}), artifact),
            )
        return original(conn)

    monkeypatch.setattr(service, "_rows", rows)
    first = search(world)
    by_kind = {item["kind"]: item for item in first["items"]}
    assert by_kind["run"]["title"] == "Old goal"
    assert by_kind["artifact"]["title"] == "Work report v1"
    assert by_kind["artifact"]["current_linked_goal"] == "Old goal"
    monkeypatch.setattr(service, "_rows", original)
    with pytest.raises(DomainError, match="WORK_SEARCH_CHANGED"):
        search(world, snapshot=first["snapshot"])


def test_zero_database_writes_file_body_reads_reconciliation_models_or_tools(world, monkeypatch):
    seed_run(world)
    seed_file(world)
    runtime = world[0]
    with runtime.store.connection() as conn:
        before = list(conn.iterdump())
    original = runtime.store.connection
    read_connections = []

    @contextmanager
    def read_only(write=False):
        assert not write, "Search attempted a write transaction"
        with original() as conn:
            read_connections.append(conn)
            yield conn
            assert conn.total_changes == 0

    def forbidden(*args, **kwargs):
        raise AssertionError("Search used a forbidden effect or body read")

    monkeypatch.setattr(runtime.store, "connection", read_only)
    monkeypatch.setattr(runtime.store, "operation", forbidden)
    monkeypatch.setattr(runtime.agent_runs, "_view", forbidden)
    monkeypatch.setattr(runtime.agent_runs, "advance_one", forbidden)
    monkeypatch.setattr(runtime.text_ai, "generate", forbidden)
    monkeypatch.setattr(runtime.browser_jobs, "advance_one", forbidden)
    monkeypatch.setattr(runtime.connectors, "advance_one", forbidden)
    for name in ("_read_bytes", "reconcile", "checked", "put", "listing"):
        monkeypatch.setattr(ImmutableFiles, name, forbidden)
    query = "Saved work private query"
    assert search(world, query)["total"] == 0 and search(world)["total"] == 2
    assert len(read_connections) == 4
    with original() as conn:
        assert list(conn.iterdump()) == before
        assert query not in "".join(conn.iterdump())


def test_search_recorded_status_does_not_establish_current_file_bytes(world):
    runtime, session, _, _ = world
    source = runtime.sources.ingest(
        SourceInput(name="Evidence.md", format="markdown"),
        b"Known bytes",
        "ingest",
        session_hash=session,
    )["source"]
    artifact = runtime.artifacts.publish(
        ArtifactInput(display_name="Result", format="markdown", content="Actual saved bytes"),
        "publish",
        session_hash=session,
        selected_source_ids=[],
    )["artifact"]
    (runtime.store.directory / "artifacts" / (artifact["id"] + ".md")).unlink()
    (runtime.store.directory / "sources" / (source["id"] + ".md")).write_text("Changed bytes")
    assert all(item["recorded_status"] == "verified" for item in search(world)["items"])
    assert runtime.artifacts.detail(artifact["id"], session_hash=session)["status"] == "unknown"
    assert runtime.sources.metadata(source["id"], session_hash=session)["status"] == "unknown"
    assert all(item["recorded_status"] == "unknown" for item in search(world)["items"])
    with pytest.raises(DomainError):
        runtime.artifacts.download(artifact["id"], session_hash=session)


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "x" * 201},
        {"query": 7},
        {"query": "\ud800"},
        {"kind": "semantic"},
        {"limit": 0},
        {"limit": 51},
        {"limit": True},
        {"limit": "20"},
        {"offset": -1},
        {"offset": 601},
        {"offset": 1},
        {"offset": True},
        {"snapshot": "bad"},
        {"operation_id": "must-not-persist"},
        {"regex": True},
    ],
)
def test_request_is_strict_bounded_and_rejects_unbound_pages(payload):
    with pytest.raises(ValidationError):
        WorkSearchInput(**payload)


def test_empty_query_browses_and_recency_uses_aware_instants(world):
    old = seed_run(world, 1, updated_at="2026-10-13T12:00:00+08:00")
    newer = seed_run(world, 2, updated_at="2026-10-13T11:00:00Z")
    result = search(world, "   ")
    assert [item["id"] for item in result["items"]] == [newer, old]
    assert all(
        item["match_reason"] == "browse" and item["matched_fields"] == []
        for item in result["items"]
    )


def test_route_owner_origin_header_readonly_json_contract(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        assert (
            client.post("/api/work/search", json={}, headers={"X-Desk-Request": "1"}).status_code
            == 403
        )
        client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "fixture-only"},
        )
        with app.state.store.connection() as conn:
            before = list(conn.iterdump())
        assert (
            client.post("/api/work/search", json={}).json()["error"]["code"]
            == "REQUEST_HEADER_REQUIRED"
        )
        denied = client.post(
            "/api/work/search",
            json={},
            headers={"X-Desk-Request": "1", "Origin": "https://example.com"},
        )
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
        response = client.post(
            "/api/work/search", json={"query": "Private query"}, headers={"X-Desk-Request": "1"}
        )
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["items"] == [] and "operation_id" not in response.json()
        assert (
            client.post(
                "/api/work/search", json={"limit": True}, headers={"X-Desk-Request": "1"}
            ).status_code
            == 422
        )
        with app.state.store.connection() as conn:
            assert list(conn.iterdump()) == before
        client.cookies.clear()
        client.cookies.set("desk_companion_device", "not-an-owner-cookie")
        assert (
            client.post(
                "/api/work/search",
                json={},
                headers={"X-Desk-Request": "1", "Authorization": "Bearer device-agent"},
            ).status_code
            == 403
        )


@pytest.mark.parametrize("kind", ["controller", "display"])
@pytest.mark.parametrize("transport", ["bearer", "device_cookie", "owner_cookie"])
def test_real_paired_clients_are_denied_without_owner_cookie(tmp_path, kind, transport):
    from desk.access import PairingClaim, PairingDecision, PairingRequest

    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    access = app.state.runtime.access
    code = access.issue(kind, "issue")
    requested = access.request(PairingRequest(code=code["code"], name="Synthetic paired client"))
    access.decide(PairingDecision(request_id=requested["request_id"], action="approve"), "decide")
    paired = access.claim(
        PairingClaim(request_id=requested["request_id"], secret=requested["secret"])
    )
    assert access.principal(bearer=paired["token"])["kind"] == kind
    with TestClient(app) as client:
        headers = {"X-Desk-Request": "1"}
        if transport == "bearer":
            headers["Authorization"] = "Bearer " + paired["token"]
        elif transport == "device_cookie":
            client.cookies.set("desk_companion_device", paired["token"])
        else:
            client.cookies.set("desk_companion_session", paired["token"])
        response = client.post("/api/work/search", json={}, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"


def test_missing_current_list_is_unknown_and_json_string_is_not_a_list(world):
    run = seed_run(world, data={"artifact_ids": [opaque(1000)]})
    seed_file(world, data={"run_id": run})
    with world[0].store.connection(write=True) as conn:
        data = json.loads(
            conn.execute("SELECT data FROM agent_runs WHERE id=?", (run,)).fetchone()[0]
        )
        del data["current_artifact_ids"]
        conn.execute("UPDATE agent_runs SET data=? WHERE id=?", (encode(data), run))
    assert search(world, kind="artifact")["items"][0]["output_membership"] == "unknown"
    change_data(world, run, current_artifact_ids=json.dumps([opaque(1000)]))
    assert search(world, kind="artifact")["items"][0]["output_membership"] == "unknown"


def test_record_id_overrides_malformed_metadata_identity_and_private_extra_keys(world):
    artifact = seed_file(world, data={"id": "/private/fake", "kind": "sources"})
    result = search(world)["items"][0]
    assert result["id"] == artifact and result["kind"] == "artifact"
    with world[0].store.connection(write=True) as conn:
        conn.execute("UPDATE private_files SET id='not-an-openable-id'")
    with pytest.raises(DomainError, match="WORK_SEARCH_METADATA_INVALID"):
        search(world)


def test_legacy_surrogate_and_nonfinite_values_do_not_break_utf8_response(world):
    run = seed_run(world)
    with world[0].store.connection(write=True) as conn:
        conn.execute(
            "UPDATE agent_runs SET data=? WHERE id=?",
            (json.dumps({"goal": "\ud800", "plan_revision": 1e300}), run),
        )
    result = search(world)
    assert result["items"][0]["title"] == "" and result["items"][0]["plan_revision"] is None
    encode(result).encode("utf-8")


def test_projection_size_limit_is_explicit_not_partial_or_unbounded(world):
    seed_run(world, data={"goal": "large" * 20000})
    with pytest.raises(DomainError, match="WORK_SEARCH_METADATA_INVALID"):
        search(world)


def test_projected_metadata_limit_counts_utf8_bytes_not_characters(world):
    seed_run(world, data={"goal": "中" * 23000})
    with pytest.raises(DomainError, match="WORK_SEARCH_METADATA_INVALID"):
        search(world)
