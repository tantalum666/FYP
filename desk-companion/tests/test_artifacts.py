import csv
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.artifacts import ArtifactInput, ArtifactService, SourceReference
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.sources import SOURCE_BYTES, SourceInput, SourceService
from desk.store import DomainError, Store


@pytest.fixture
def files(tmp_path):
    clock = [datetime(2026, 10, 12, 12, tzinfo=UTC)]
    store = Store(tmp_path, password="test-only", clock=lambda: clock[0])
    runtime = Runtime(store)
    runtime.sources = SourceService(runtime)
    runtime.artifacts = ArtifactService(runtime)
    token = store.authenticate("owner", "test-only")
    return runtime, hashlib.sha256(token.encode()).hexdigest(), clock


def ingest(
    runtime,
    session,
    content="First line\nSecond line\nThird line\n",
    name="notes.md",
    format="markdown",
    key=None,
):
    return runtime.sources.ingest(
        SourceInput(name=name, format=format),
        content.encode(),
        key or uuid4().hex,
        session_hash=session,
    )["source"]


def publish(
    runtime,
    session,
    *,
    content="A useful result.\n",
    format="markdown",
    key=None,
    run_id=None,
    refs=None,
    selected=None,
    authorship="deterministic",
):
    payload = ArtifactInput(
        format=format,
        display_name="Result",
        content=content,
        provenance=refs or [],
        authorship=authorship,
    )
    return runtime.artifacts.publish(
        payload,
        key or uuid4().hex,
        session_hash=session,
        selected_source_ids=selected or [],
        run_id=run_id,
        step_id="report",
    )["artifact"]


def path_of(runtime, row):
    suffix = {"markdown": "md", "text": "txt", "json": "json", "csv": "csv"}[row["format"]]
    return runtime.store.directory / row["kind"] / f"{row['id']}.{suffix}"


def test_actual_markdown_and_json_bytes_manifest_and_plain_preview(files):
    runtime, session, _ = files
    md = publish(
        runtime,
        session,
        content="# Actual report\n<script>alert(1)</script>\n![remote](https://example.com/x)\n",
    )
    saved = path_of(runtime, md).read_bytes()
    assert saved.startswith(b"# Actual report")
    assert hashlib.sha256(saved).hexdigest() == md["sha256"]
    assert len(saved) == md["byte_count"] and md["status"] == "verified"
    assert md["verification"] == "byte_readback" and md["quality"] == "not_semantically_checked"
    preview = runtime.artifacts.read(md["id"], session_hash=session)
    assert preview["preview_kind"] == "plain_text" and "<script>" in preview["content"]
    result = publish(runtime, session, format="json", content={"items": [1, "中文"], "ready": True})
    assert json.loads(path_of(runtime, result).read_text()) == {"items": [1, "中文"], "ready": True}
    assert path_of(runtime, result).stat().st_mode & 0o777 == 0o600


def test_csv_is_actual_parseable_formula_safe_file(files):
    runtime, session, _ = files
    inputs = [
        "=SUM(A1)",
        "+cmd",
        "-cmd",
        "@cmd",
        "\tcmd",
        "\rcmd",
        "  =cmd",
        'a,"b"\nc',
        -3,
        2.5,
        True,
        None,
    ]
    artifact = publish(
        runtime,
        session,
        format="csv",
        content={"columns": ["=header"], "rows": [[v] for v in inputs]},
    )
    with path_of(runtime, artifact).open(newline="") as source:
        rows = list(csv.reader(source))
    assert rows[0] == ["'=header"]
    assert [r[0] for r in rows[1:8]] == ["'" + v for v in inputs[:7]]
    assert [r[0] for r in rows[8:]] == [inputs[7], "-3", "2.5", "true", ""]
    assert artifact["csv_string_escaping"] == "apostrophe_prefix"


def test_source_snapshot_chunk_ranges_are_exact_and_local_parser_is_explicit(files):
    runtime, session, _ = files
    content = "é" * 3000 + "\n" + "中" * 2000 + "\n" + "Tail\n"
    source = ingest(runtime, session, content=content)
    original = path_of(runtime, source).read_bytes()
    assert original == content.encode()
    first = runtime.sources.read(
        source["id"],
        session_hash=session,
        selected_ids=[source["id"]],
        max_lines=1,
        coverage_id="run",
    )
    assert first["end_line"] == 1 and first["truncated"]
    assert len(first["content"].encode()) <= 12 * 1024
    second = runtime.sources.read(
        source["id"],
        session_hash=session,
        selected_ids=[source["id"]],
        start_line=2,
        coverage_id="run",
    )
    assert first["content"] + second["content"] == content
    all_text = runtime.sources.read_all(
        source["id"], session_hash=session, selected_ids=[source["id"]], coverage_id="parser"
    )
    assert all_text["content"] == content and all_text["provider_ready"] is False
    assert all_text["reader"] == "local_parser"
    assert source["provider_sharing"] == "not_granted_by_selection"


def test_citations_require_selected_actual_ranges_and_observed_coverage(files):
    runtime, session, _ = files
    source = ingest(runtime, session)
    ref = {"source_id": source["id"], "source_revision": 1, "start_line": 1, "end_line": 2}
    with pytest.raises(DomainError, match="SOURCE_NOT_SELECTED"):
        publish(runtime, session, refs=[ref], run_id="run")
    with pytest.raises(DomainError, match="SOURCE_RANGE_NOT_OBSERVED"):
        publish(runtime, session, refs=[ref], selected=[source["id"]], run_id="run")
    runtime.sources.read_all(
        source["id"], session_hash=session, selected_ids=[source["id"]], coverage_id="run"
    )
    with pytest.raises(DomainError, match="SOURCE_RANGE_NOT_OBSERVED"):
        publish(
            runtime, session, refs=[ref], selected=[source["id"]], run_id="run", authorship="model"
        )
    runtime.sources.read(
        source["id"],
        session_hash=session,
        selected_ids=[source["id"]],
        max_lines=1,
        coverage_id="run",
    )
    runtime.sources.read(
        source["id"],
        session_hash=session,
        selected_ids=[source["id"]],
        start_line=2,
        max_lines=1,
        coverage_id="run",
    )
    artifact = publish(
        runtime, session, refs=[ref], selected=[source["id"]], run_id="run", authorship="model"
    )
    assert artifact["provenance"][0]["sha256"] == source["sha256"]
    assert artifact["quality"] == "not_semantically_checked"
    with pytest.raises(DomainError, match="SOURCE_RANGE_INVALID"):
        publish(runtime, session, refs=[{**ref, "end_line": 4}], selected=[source["id"]])
    with pytest.raises(DomainError, match="FILE_NOT_FOUND"):
        fake = "a" * 32
        publish(runtime, session, refs=[{**ref, "source_id": fake}], selected=[fake])


def test_idempotency_restart_concurrency_and_no_text_in_operation_tables(files):
    runtime, session, _ = files
    source = ingest(runtime, session, key="source-key")
    assert ingest(runtime, session, key="source-key")["id"] == source["id"]
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        ingest(runtime, session, content="Different", key="source-key")
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda _: publish(runtime, session, content="Private output", key="stable"),
                range(2),
            )
        )
    assert len({r["id"] for r in replies}) == 1
    runtime.artifacts = ArtifactService(runtime)
    assert (
        publish(runtime, session, content="Private output", key="stable")["id"] == replies[0]["id"]
    )
    assert len(list((runtime.store.directory / "artifacts").iterdir())) == 1
    with runtime.store.connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM private_files")]
        assert "Private output" not in json.dumps(rows)
        assert not conn.execute("SELECT 1 FROM operations WHERE id='stable'").fetchone()


class Crash(BaseException):
    pass


@pytest.mark.parametrize(
    "phase,verified",
    [
        ("reserved", False),
        ("opened", False),
        ("written", False),
        ("temp_synced", False),
        ("linked", True),
        ("synced", True),
        ("published", True),
    ],
)
def test_crash_boundaries_reconcile_without_rewrite(files, monkeypatch, phase, verified):
    runtime, session, _ = files

    def crash(at, row):
        if at == phase:
            raise Crash()

    monkeypatch.setattr(runtime.artifacts.files, "phase", crash)
    with pytest.raises(Crash):
        publish(runtime, session, key="crash", content="Durable bytes")
    with runtime.store.connection() as conn:
        row = json.loads(
            conn.execute(
                "SELECT metadata FROM private_files WHERE operation_key='crash'"
            ).fetchone()[0]
        )
    target = path_of(runtime, row)
    existed = target.exists()
    before = target.read_bytes() if existed else None
    runtime.artifacts = ArtifactService(runtime)
    reply = publish(runtime, session, key="crash", content="Durable bytes")
    assert (reply["status"] == "verified") is verified
    assert target.exists() is existed
    assert (target.read_bytes() if existed else None) == before
    if not verified:
        assert reply["verification"] == "unverified"


@pytest.mark.parametrize(
    "attack", ["symlink", "hardlink", "corrupt", "directory", "fifo", "permissions"]
)
def test_readback_rejects_replaced_corrupt_or_linked_files(files, attack):
    runtime, session, _ = files
    row = publish(runtime, session)
    target = path_of(runtime, row)
    other = runtime.store.directory / "unrelated.txt"
    other.write_text("Unrelated private data")
    if attack == "hardlink":
        os.link(target, runtime.store.directory / "linked.txt")
    elif attack == "permissions":
        target.chmod(0o644)
    elif attack == "corrupt":
        target.write_bytes(b"x" * row["byte_count"])
    else:
        target.unlink()
        if attack == "symlink":
            target.symlink_to(other)
        elif attack == "directory":
            target.mkdir()
        else:
            os.mkfifo(target)
    assert runtime.artifacts.detail(row["id"], session_hash=session)["status"] == "unknown"
    with pytest.raises(DomainError):
        runtime.artifacts.download(row["id"], session_hash=session)
    assert other.read_text() == "Unrelated private data"


def test_no_overwrite_of_collision_and_no_follow_root(files, monkeypatch):
    runtime, session, _ = files
    outside = runtime.store.directory / "outside"
    outside.mkdir()

    def collision(phase, row):
        if phase == "reserved":
            folder = runtime.store.directory / "artifacts"
            folder.mkdir(mode=0o700)
            path_of(runtime, row).write_text("Already exists")

    monkeypatch.setattr(runtime.artifacts.files, "phase", collision)
    row = publish(runtime, session)
    assert row["status"] == "unknown" and path_of(runtime, row).read_text() == "Already exists"
    os.close(runtime.sources.files._directory("sources", create=True))
    (runtime.store.directory / "sources").rmdir()
    (runtime.store.directory / "sources").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DomainError, match="FILE_SCOPE_UNAVAILABLE"):
        ingest(runtime, session)
    assert not list(outside.iterdir())


def test_auth_hidden_expired_revoked_fake_owner_and_replays(files):
    runtime, session, clock = files
    row = publish(runtime, session, key="saved")
    for identity in [None, "", "owner", {"kind": "owner"}, "a" * 64]:
        with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
            runtime.artifacts.detail(row["id"], session_hash=identity)
    runtime.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True), "hide"
    )
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        publish(runtime, session, key="saved")
    runtime.store.update_settings(
        SettingsInput(expected_version=2, timezone="Asia/Hong_Kong", hide_private=False), "show"
    )
    clock[0] += timedelta(hours=9)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        runtime.artifacts.listing(session_hash=session)


@pytest.mark.parametrize(
    "fmt,content",
    [
        ("text", ""),
        ("text", "\0"),
        ("text", "x" * (256 * 1024 + 1)),
        ("json", float("nan")),
        ("csv", {"columns": ["a", "a"], "rows": []}),
        ("csv", {"columns": ["a"], "rows": [[1, 2]]}),
        ("csv", {"columns": ["a"], "rows": [["x"]] * 1001}),
    ],
)
def test_invalid_output_rejected_before_filesystem(files, fmt, content):
    runtime, session, _ = files
    with pytest.raises(DomainError):
        publish(runtime, session, format=fmt, content=content)
    assert not (runtime.store.directory / "artifacts").exists()


@pytest.mark.parametrize(
    "name,fmt,body",
    [
        ("a.txt", "text", b"\xff"),
        ("a.txt", "text", b"\x00"),
        ("a.txt", "text", b"x" * (SOURCE_BYTES + 1)),
        ("a.txt", "text", b"x" * (12 * 1024 + 1)),
        ("a.json", "json", b'{"bad":NaN}'),
        ("a.csv", "csv", b"a,b\n1\n"),
        ("a.json", "json", b"[" * 30 + b"0" + b"]" * 30),
    ],
)
def test_invalid_sources_rejected_before_storage(files, name, fmt, body):
    runtime, session, _ = files
    with pytest.raises(DomainError):
        runtime.sources.ingest(
            SourceInput(name=name, format=fmt), body, "invalid", session_hash=session
        )
    assert not (runtime.store.directory / "sources").exists()


def test_scope_and_path_schema_boundaries(files):
    runtime, session, _ = files
    for name in ["../x.md", "/tmp/x.md", "x\\evil.md", "x.exe", "x.html"]:
        with pytest.raises(ValidationError):
            SourceInput(name=name, format="markdown")
    with pytest.raises(ValidationError):
        ArtifactInput(format="html", display_name="X", content="<html/>")
    with pytest.raises(ValidationError):
        SourceReference(source_id="../anything", start_line=1, end_line=2)
    with pytest.raises(DomainError, match="FILE_NOT_FOUND"):
        runtime.artifacts.detail("../../anything", session_hash=session)
    source = ingest(runtime, session)
    with pytest.raises(DomainError, match="SOURCE_NOT_SELECTED"):
        runtime.sources.read(source["id"], session_hash=session, selected_ids=[])


def test_run_capacity_counts_uncertain_and_verified_reservations(files):
    runtime, session, _ = files
    for _ in range(4):
        publish(runtime, session, run_id="one-run")
    with pytest.raises(DomainError, match="ARTIFACT_RUN_LIMIT"):
        publish(runtime, session, run_id="one-run")
    assert len(runtime.artifacts.listing(session_hash=session, run_id="one-run")["artifacts"]) == 4
    assert not runtime.artifacts.listing(session_hash=session, run_id="other")["artifacts"]
    page = runtime.artifacts.listing(session_hash=session, limit=2)
    next_page = runtime.artifacts.listing(session_hash=session, limit=2, cursor=page["next_cursor"])
    assert len({r["id"] for r in page["artifacts"] + next_page["artifacts"]}) == 4


def test_import_requires_exact_actual_download_bytes(files):
    runtime, session, _ = files
    body = b"# Actually downloaded\n"
    payload = ArtifactInput(format="markdown", display_name="Export", content=body.decode())
    row = runtime.artifacts.import_download(
        payload,
        "download",
        body=body,
        expected_sha256=hashlib.sha256(body).hexdigest(),
        session_hash=session,
        selected_source_ids=[],
        run_id="browser",
        step_id="export",
    )["artifact"]
    assert row["origin"] == "browser_download" and path_of(runtime, row).read_bytes() == body
    with pytest.raises(DomainError, match="DOWNLOAD_BYTES_MISMATCH"):
        runtime.artifacts.import_download(
            payload,
            "bad",
            body=b"Other",
            expected_sha256=hashlib.sha256(body).hexdigest(),
            session_hash=session,
            selected_source_ids=[],
            run_id="browser",
            step_id="export",
        )


def test_owner_routes_raw_upload_plain_preview_and_safe_attachment(tmp_path):
    app = create_app(tmp_path, password="test-only", scheduler=False)
    runtime = app.state.runtime
    runtime.sources, runtime.artifacts = SourceService(runtime), ArtifactService(runtime)
    headers = {
        "X-Desk-Request": "1",
        "X-Operation-Id": "upload",
        "Content-Type": "text/plain; charset=utf-8",
    }
    with TestClient(app) as client:
        assert client.get("/api/sources").status_code == 403
        client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "test-only"},
        )
        response = client.post(
            "/api/sources/upload?name=notes.md&format=markdown",
            headers=headers,
            content=b"# Input\nActual bytes\n",
        )
        assert response.status_code == 200, response.text
        source = response.json()["source"]
        assert (
            client.get(f"/api/sources/{source['id']}/content").json()["content"]
            == "# Input\nActual bytes\n"
        )
        assert (
            client.post(
                "/api/sources/upload?name=big.txt&format=text",
                headers=headers,
                content=b"x" * (SOURCE_BYTES + 1),
            ).status_code
            == 413
        )
        session = hashlib.sha256(client.cookies.get("desk_companion_session").encode()).hexdigest()
        row = publish(runtime, session, content="<script>doNotRun()</script>")
        preview = client.get(f"/api/artifacts/{row['id']}/content")
        assert preview.headers["content-type"].startswith("application/json")
        download = client.get(f"/api/artifacts/{row['id']}/download")
        assert download.content == b"<script>doNotRun()</script>"
        assert download.headers["content-disposition"] == f'attachment; filename="{row["id"]}.md"'
        assert download.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in download.headers["content-security-policy"]
        client.cookies.clear()
        assert client.get(f"/api/artifacts/{row['id']}/download").status_code == 403


def test_source_read_budget_records_only_complete_observed_lines(files):
    runtime, session, _ = files
    source = ingest(runtime, session, content="small\n" + "x" * 2000 + "\nlast\n")
    reply = runtime.sources.read(
        source["id"],
        session_hash=session,
        selected_ids=[source["id"]],
        max_bytes=1800,
        coverage_id="model",
    )
    assert reply["content"] == "small\n" and reply["end_line"] == 1
    with pytest.raises(DomainError, match="SOURCE_LINE_EXCEEDS_READ_BUDGET"):
        runtime.sources.read(
            source["id"],
            session_hash=session,
            selected_ids=[source["id"]],
            start_line=2,
            max_bytes=1800,
            coverage_id="model",
        )
    assert runtime.sources.covered(source["id"], 1, 1, "model", "model", session)
    assert not runtime.sources.covered(source["id"], 1, 2, "model", "model", session)


def test_unpublished_temporary_file_cannot_be_read_as_verified(files, monkeypatch):
    runtime, session, _ = files
    snapshots = []

    def observe(phase, row):
        if phase == "written":
            snapshots.append(runtime.artifacts.detail(row["id"], session_hash=session))

    monkeypatch.setattr(runtime.artifacts.files, "phase", observe)
    artifact = publish(runtime, session)
    assert snapshots[0]["status"] == "unknown" and snapshots[0]["verification"] == "unverified"
    assert artifact["status"] == "verified"
    assert not list((runtime.store.directory / "artifacts").glob("*.pending"))


def test_recovery_requires_successful_file_and_directory_fsync(files, monkeypatch):
    runtime, session, _ = files

    def crash(phase, row):
        if phase == "linked":
            raise Crash()

    monkeypatch.setattr(runtime.artifacts.files, "phase", crash)
    with pytest.raises(Crash):
        publish(runtime, session, key="durability")
    runtime.artifacts = ArtifactService(runtime)
    real_fsync = os.fsync

    def fail(fd):
        raise OSError("simulated durability failure")

    monkeypatch.setattr(os, "fsync", fail)
    result = publish(runtime, session, key="durability")
    assert result["status"] == "unknown" and result["verification"] == "unverified"
    before = path_of(runtime, result).read_bytes()
    monkeypatch.setattr(os, "fsync", real_fsync)
    calls = []

    def count(fd):
        import stat

        calls.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", count)
    result = publish(runtime, session, key="durability")
    assert result["status"] == "verified"
    assert "file" in calls and "directory" in calls
    assert path_of(runtime, result).read_bytes() == before


def test_revocation_during_write_never_returns_private_result(files, monkeypatch):
    runtime, session, _ = files

    def revoke(phase, row):
        if phase == "written":
            with runtime.store.connection(write=True) as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (session,))

    monkeypatch.setattr(runtime.artifacts.files, "phase", revoke)
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        publish(runtime, session, key="revoked-write")
    with runtime.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM private_files WHERE operation_key='revoked-write'"
            ).fetchone()[0]
            == 1
        )
    token = runtime.store.authenticate("owner", "test-only")
    current = hashlib.sha256(token.encode()).hexdigest()
    artifact = publish(runtime, current, key="revoked-write")
    assert artifact["status"] == "unknown"
    assert not path_of(runtime, artifact).exists()


def test_unknown_reservations_consume_run_capacity(files, monkeypatch):
    runtime, session, _ = files

    def crash(phase, row):
        if phase == "reserved":
            raise Crash()

    monkeypatch.setattr(runtime.artifacts.files, "phase", crash)
    for i in range(4):
        with pytest.raises(Crash):
            publish(runtime, session, run_id="uncertain", key=f"unknown-{i}")
    with pytest.raises(DomainError, match="ARTIFACT_RUN_LIMIT"):
        publish(runtime, session, run_id="uncertain", key="fifth")
    assert publish(runtime, session, run_id="uncertain", key="unknown-0")["status"] == "unknown"
    assert (
        len(runtime.artifacts.listing(session_hash=session, run_id="uncertain")["artifacts"]) == 4
    )


def test_source_capacity_and_preview_utf8_boundaries(files):
    runtime, session, _ = files
    for i in range(100):
        ingest(runtime, session, content="A\n", key=f"source-{i}")
    with pytest.raises(DomainError, match="FILE_CAPACITY_LIMIT"):
        ingest(runtime, session, content="A\n", key="source-101")
    assert len(runtime.sources.listing(session_hash=session, limit=100)["sources"]) == 100
    artifact = publish(runtime, session, content="A" + "🦉" * 10000)
    preview = runtime.artifacts.read(artifact["id"], session_hash=session)
    assert preview["truncated"] and len(preview["content"].encode()) <= 32768
    assert "�" not in preview["content"]


@pytest.mark.parametrize(
    "name,fmt,content",
    [
        ("a.json", "json", '{"a":1,"a":2}'),
        ("a.csv", "csv", "a,a\n1,2\n"),
        ("a.csv", "csv", ",b\n1,2\n"),
    ],
)
def test_ambiguous_structured_input_rejected(files, name, fmt, content):
    runtime, session, _ = files
    with pytest.raises(DomainError):
        ingest(runtime, session, name=name, format=fmt, content=content)


def test_existing_artifact_becomes_immutable_selected_source_without_reupload(files):
    runtime, session, _ = files
    artifact = publish(runtime, session, content="# Earlier report\nActual prior output\n")
    reply = runtime.sources.from_artifact(artifact["id"], "select-artifact", session_hash=session)
    source = reply["source"]
    assert source["parent_artifact_id"] == artifact["id"]
    assert source["provenance_kind"] == "artifact_snapshot"
    assert source["sha256"] == artifact["sha256"]
    assert path_of(runtime, source).read_bytes() == path_of(runtime, artifact).read_bytes()
    assert (
        runtime.sources.from_artifact(artifact["id"], "select-artifact", session_hash=session)
        == reply
    )
    assert source["provider_sharing"] == "not_granted_by_selection"


@pytest.mark.parametrize("phase,expected", [("written", "unknown"), ("linked", "verified")])
def test_actual_process_exit_then_restart_recovers_without_reexecution(files, phase, expected):
    import subprocess
    import sys
    from pathlib import Path

    runtime, session, _ = files
    code = f"""
import os
from datetime import UTC,datetime
from desk.store import Store
from desk.runtime import Runtime
from desk.artifacts import ArtifactInput
r=Runtime(Store({str(runtime.store.directory)!r},password="test-only",clock=lambda:datetime(2026,10,12,12,tzinfo=UTC)))
def stop(phase,row):
    if phase=={phase!r}: os._exit(19)
r.artifacts.files.phase=stop
r.artifacts.publish(ArtifactInput(format="markdown",display_name="Result",content="A useful result.\\n"),"process-crash",session_hash={session!r},selected_source_ids=[],step_id="report")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "backend")},
        timeout=20,
    )
    assert completed.returncode == 19
    runtime.artifacts = ArtifactService(runtime)
    artifact = publish(runtime, session, key="process-crash")
    assert artifact["status"] == expected
    final = path_of(runtime, artifact)
    assert final.exists() is (expected == "verified")
    if final.exists():
        assert hashlib.sha256(final.read_bytes()).hexdigest() == artifact["sha256"]
