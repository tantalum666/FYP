"""Codex integration-review regressions. Offline fixtures; production paths only.

Lessons and the checks that fail if they return:

1. Login/transaction isolation and fresh reads after delete+retry.
2. Owner authority on backup apply and goal confirmation, including a replay.
3. Backup validation before list/restore: incomplete jobs and folder rebinding.
4. Omitted calendar fields survive the shared tool-validation path.
5. An interrupted assistant stream is not complete; recovery is SSE, one draft.
6. Case-insensitive component/helper paths, and removed service methods have no callers.
7. Lessons 3 and 4 go through HTTP list/restore and execute_tool, not a private write.
"""

import ast
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.access import digest
from desk.app import create_app
from desk.jobs import FolderNaming, JobApproval, JobInput
from desk.schemas import CreateEvents, EventInput
from desk.store import encode
from desk.stream_contract import parse_sse
from desk.tasks import TaskInput
from desk.text_ai import TextPlan
from desk.tool_policy import execute_tool

HEADERS = {"X-Desk-Request": "1"}
ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "backend", ROOT / "frontend" / "src")
SKIP_DIRS = {
    ".git",
    ".runtime",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


def app_at(path):
    return create_app(path, password="fixture", scheduler=False)


def owner_at(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers=HEADERS,
        ).status_code
        == 200
    )
    return client


def paired_at(app, owner):
    assert (
        owner.post(
            "/api/devices/enrol-display",
            json={"name": "Fixture screen"},
            headers={**HEADERS, "X-Operation-Id": uuid4().hex},
        ).status_code
        == 200
    )
    client = TestClient(app)
    client.headers.update(
        {**HEADERS, "Authorization": "Bearer " + owner.cookies.get("desk_companion_device")}
    )
    return client


def rehash(backup):
    backup["sha256"] = digest(encode(backup["payload"]))
    return backup


def post_backup(client, backup, key):
    return client.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(rehash(backup))},
        headers={**HEADERS, "X-Operation-Id": key},
    )


def job_list(client):
    response = client.get("/api/computer/jobs", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()["jobs"]


def dumped(value):
    return json.dumps(value, ensure_ascii=False)


def test_deleted_facts_do_not_return_from_tool_cache_or_another_login(tmp_path, monkeypatch):
    first_app = app_at(tmp_path / "alpha")
    second_app = app_at(tmp_path / "beta")
    alpha, beta = first_app.state.runtime, second_app.state.runtime
    fact = alpha.memory.create("alpha-cobalt-token", "alpha-fact")["memory"]
    beta.memory.create("beta-cobalt-token", "beta-fact")
    arguments = {"query": "cobalt"}
    # The same scope string on two stores must not share a process-global read cache.
    seen = execute_tool(alpha, "memory_query", arguments, "read", scope="shared-login")
    other = execute_tool(beta, "memory_query", arguments, "read", scope="shared-login")
    assert "alpha-cobalt-token" in dumped(seen)
    assert "alpha-cobalt-token" not in dumped(other)
    assert "beta-cobalt-token" in dumped(other)
    searched = execute_tool(
        alpha,
        "owner_search",
        {"query": "cobalt", "sources": ["memory"]},
        "search",
        scope="shared-login",
    )
    assert "alpha-cobalt-token" in dumped(searched)
    alpha.memory.delete(fact["id"], fact["version"], "forget")
    again = execute_tool(alpha, "memory_query", arguments, "read", scope="shared-login")
    retried = execute_tool(
        alpha,
        "owner_search",
        {"query": "cobalt", "sources": ["memory"]},
        "search",
        scope="shared-login",
    )
    assert "alpha-cobalt-token" not in dumped(again)
    assert "alpha-cobalt-token" not in dumped(retried)
    assert again["memories"] == [] and retried["matches"] == []
    # A different login/task on the store that still has the other fact is unaffected.
    assert "beta-cobalt-token" in dumped(
        execute_tool(beta, "memory_query", arguments, "read", scope="other-login")
    )

    runtime = alpha
    captured = []
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(system, context, schema, purpose):
        captured.append(context)
        return TextPlan(message="Acknowledged", tool="none")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    first, second = owner_at(first_app), owner_at(first_app)
    task_a = runtime.tasks.create(TaskInput(title="Fixture A"), "task-a")["task"]
    task_b = runtime.tasks.create(TaskInput(title="Fixture B"), "task-b")["task"]
    for client, key, message, task_id in (
        (first, "one", "Transient fixture alpha-cobalt-token", task_a["id"]),
        (first, "two", "Hello on another task", task_b["id"]),
        (second, "three", "Hello from another login", None),
    ):
        body = {"message": message}
        if task_id:
            body["task_id"] = task_id
        response = client.post(
            "/api/assistant/messages",
            json=body,
            headers={**HEADERS, "X-Operation-Id": key},
        )
        assert response.status_code == 200, response.text
    assert any("alpha-cobalt-token" in turn["body"] for turn in captured[0]["turns"]) is False
    assert captured[1]["turns"] == []
    assert captured[2]["turns"] == []
    assert "alpha-cobalt-token" not in dumped(captured[1])
    assert "alpha-cobalt-token" not in dumped(captured[2])


def test_paired_principal_cannot_apply_backup_or_confirm_goal(tmp_path):
    source = app_at(tmp_path / "source").state.runtime
    source.memory.create("Source fixture fact", "source-fact")
    source.jobs.enabled = True
    source.jobs.prepare(JobInput(title="Fixture", content="No execution"), "source-job")
    app = app_at(tmp_path / "target")
    owner = owner_at(app)
    paired = paired_at(app, owner)
    preview = post_backup(owner, source.exchange.backup(), "preview")
    assert preview.status_code == 200, preview.text
    path = "/api/exchange/" + preview.json()["preview_id"] + "/apply"
    refused = paired.post(path, json={}, headers={"X-Operation-Id": "paired-apply"})
    assert refused.status_code == 403, refused.text
    assert job_list(owner) == []
    assert app.state.runtime.memory.for_model() == []
    applied = owner.post(path, json={}, headers={**HEADERS, "X-Operation-Id": "owner-apply"})
    assert applied.status_code == 200, applied.text
    listed = job_list(owner)
    assert len(listed) == 1 and listed[0]["action"] == "save_note"
    assert listed[0]["state"] == "review"
    replay = paired.post(path, json={}, headers={"X-Operation-Id": "owner-apply"})
    assert replay.status_code == 403, replay.text
    assert len(job_list(owner)) == 1

    draft = owner.post(
        "/api/assistant/messages",
        json={"message": "Goal: finish fixture report"},
        headers={**HEADERS, "X-Operation-Id": "goal"},
    )
    assert draft.status_code == 200, draft.text
    proposal_id = draft.json()["proposal"]["id"]
    assert paired.get("/api/goals", headers=HEADERS).status_code == 403
    denied = paired.post(
        "/api/assistant/proposals/" + proposal_id + "/decisions",
        json={"action": "confirm"},
        headers={"X-Operation-Id": "paired-confirm"},
    )
    assert denied.status_code == 403, denied.text
    assert owner.get("/api/goals", headers=HEADERS).json()["goals"] == []
    confirmed = owner.post(
        "/api/assistant/proposals/" + proposal_id + "/decisions",
        json={"action": "confirm"},
        headers={**HEADERS, "X-Operation-Id": "owner-confirm"},
    )
    assert confirmed.status_code == 200, confirmed.text
    goals = owner.get("/api/goals", headers=HEADERS).json()["goals"]
    assert len(goals) == 1 and goals[0]["title"] == "finish fixture report"
    again = paired.post(
        "/api/assistant/proposals/" + proposal_id + "/decisions",
        json={"action": "confirm"},
        headers={"X-Operation-Id": "owner-confirm"},
    )
    assert again.status_code == 403, again.text
    assert len(owner.get("/api/goals", headers=HEADERS).json()["goals"]) == 1


def test_restored_jobs_round_trip_through_list_and_reject_bad_backups(tmp_path):
    source_app = app_at(tmp_path / "source")
    source = source_app.state.runtime
    source.jobs.enabled = True
    source.jobs.prepare(JobInput(title="Fixture note", content="Keep this text"), "note")
    target = app_at(tmp_path / "target")
    owner = owner_at(target)
    preview = post_backup(owner, source.exchange.backup(), "good-preview")
    assert preview.status_code == 200, preview.text
    applied = owner.post(
        "/api/exchange/" + preview.json()["preview_id"] + "/apply",
        json={},
        headers={**HEADERS, "X-Operation-Id": "good-apply"},
    )
    assert applied.status_code == 200, applied.text
    listed = job_list(owner)
    assert len(listed) == 1
    assert listed[0]["action"] == "save_note" and listed[0]["state"] == "review"
    assert listed[0]["request"]["content"] == "Keep this text"
    with target.state.store.connection() as conn:
        assert conn.execute("SELECT approved_by, run_id FROM computer_jobs").fetchone()[:] == (
            None,
            None,
        )

    incomplete = source.exchange.backup()
    row = incomplete["payload"]["job_bundle"]["jobs"][0]
    row["request"].pop("task_id")
    row["intent_hash"] = hashlib.sha256(encode(row["request"]).encode()).hexdigest()
    rejected_app = app_at(tmp_path / "rejected")
    rejected = owner_at(rejected_app)
    refused = post_backup(rejected, incomplete, "bad-preview")
    assert refused.status_code == 422, refused.text
    assert refused.json()["error"]["code"] == "INVALID_BACKUP"
    assert job_list(rejected) == []

    folder_root = tmp_path / "folders"
    folder_a, folder_b = folder_root / "a", folder_root / "b"
    folder_a.mkdir(parents=True)
    folder_b.mkdir()
    rebound = app_at(tmp_path / "rebind")
    runtime = rebound.state.runtime
    runtime.jobs.set_folder(FolderNaming(label="A", path=str(folder_a.resolve())), "folder")
    prepared = runtime.jobs.prepare(
        JobInput(action="save_folder_file", title="Bound", content="Stay on A"),
        "folder-job",
    )["job"]
    detail = runtime.jobs.detail(prepared["id"], review=True)
    runtime.jobs.approve(
        prepared["id"],
        JobApproval(expected_version=detail["version"], intent_hash=detail["intent_hash"]),
        "approve",
    )
    fingerprint = detail["request"]["folder_fingerprint"]
    backup = runtime.exchange.backup()
    backup["payload"]["job_bundle"]["folder"]["path"] = str(folder_b.resolve())
    runtime.jobs.clear_folder("clear")
    rebound_owner = owner_at(rebound)
    moved = post_backup(rebound_owner, backup, "rebind-preview")
    assert moved.status_code == 200, moved.text
    denied = rebound_owner.post(
        "/api/exchange/" + moved.json()["preview_id"] + "/apply",
        json={},
        headers={**HEADERS, "X-Operation-Id": "rebind-apply"},
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "COMPUTER_SCOPE_CHANGED"
    restored = job_list(rebound_owner)
    assert len(restored) == 1 and restored[0]["state"] == "queued"
    assert restored[0]["request"]["folder_fingerprint"] == fingerprint
    assert runtime.jobs.folder_config() is None
    assert list(folder_b.iterdir()) == []


def test_shared_tool_validation_preserves_omitted_schedule_fields(tmp_path):
    app = app_at(tmp_path)
    runtime = app.state.runtime
    created = runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Fixture",
                start_local="2026-10-30T10:00",
                end_local="2026-10-30T11:00",
                timezone="UTC",
                calendar="study",
                color="sage",
                visibility="displayable",
                busy=False,
                location="Fixture room",
                notes="Keep private note",
                recurrence={"frequency": "weekly", "interval": 1, "until": "2026-12-31"},
                reminder_minutes=[60, 15],
            )
        ),
        "event",
    )
    event_id = created["event_ids"][0]
    # execute_tool runs parse_call. A direct assistant.tool call would skip that fill-in.
    result = execute_tool(
        runtime,
        "calendar_change_draft",
        {
            "event_id": event_id,
            "change": {
                "action": "update",
                "expected_version": 1,
                "scope": "series",
                "event": {
                    "title": "Fixture moved",
                    "start_local": "2026-10-30T12:00",
                    "end_local": "2026-10-30T13:00",
                },
            },
        },
        "move",
        scope="move-turn",
    )
    assert result.get("error") is None, result
    assert "Keep private note" not in dumped(result)
    owner = owner_at(app)
    decision = owner.post(
        "/api/assistant/proposals/" + result["proposal"]["id"] + "/decisions",
        json={"action": "confirm"},
        headers={**HEADERS, "X-Operation-Id": "confirm-move"},
    )
    assert decision.status_code == 200, decision.text
    saved = owner.get("/api/events/" + event_id, headers=HEADERS)
    assert saved.status_code == 200, saved.text
    event = saved.json()
    assert event["title"] == "Fixture moved"
    assert event["start_local"].startswith("2026-10-30T12:00")
    assert event["notes"] == "Keep private note"
    assert event["location"] == "Fixture room"
    assert event["reminder_minutes"] == [60, 15]
    assert event["visibility"] == "displayable"
    assert event["calendar"] == "study"
    assert event["timezone"] == "UTC"
    assert event["color"] == "sage" and event["busy"] is False
    assert event["recurrence"]["frequency"] == "weekly"
    assert event["recurrence"]["until"] == "2026-12-31"


def test_interrupted_assistant_stream_recovers_once_through_sse(tmp_path):
    app = app_at(tmp_path)
    owner = owner_at(app)
    body = {"message": "Goal: finish fixture report", "language": "en"}
    headers = {**HEADERS, "X-Operation-Id": "stream-recover"}
    with owner.stream("POST", "/api/assistant/messages/stream", json=body, headers=headers) as first:
        assert first.status_code == 200, first.read()
        assert first.headers["content-type"].startswith("text/event-stream")
        chunk = next(first.iter_bytes())
        assert chunk
    recovered = owner.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers["content-type"].startswith("text/event-stream")
    with pytest.raises(json.JSONDecodeError):
        json.loads(recovered.text)
    events = parse_sse(recovered.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["saved"] is False
    proposals = owner.get("/api/assistant/proposals", headers=HEADERS).json()["proposals"]
    drafts = [row for row in proposals if row["data"].get("goal")]
    assert len(drafts) == 1
    repeated = owner.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert repeated.status_code == 200, repeated.text
    again = owner.get("/api/assistant/proposals", headers=HEADERS).json()["proposals"]
    assert len([row for row in again if row["data"].get("goal")]) == 1

    script = ROOT / "tests" / "fixtures" / "stream_recovery_check.mjs"
    register = ROOT / "tests" / "fixtures" / "register_ts_loader.mjs"
    if shutil.which("node") is None:
        pytest.fail("node is required to load the production stream client")
    completed = subprocess.run(
        [
            "node",
            "--experimental-transform-types",
            "--import",
            str(register),
            str(script),
        ],
        cwd=ROOT / "frontend",
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "ok"


def case_key_groups(paths):
    grouped = {}
    for path in paths:
        grouped.setdefault(path.casefold(), []).append(path)
    return [sorted(items) for items in grouped.values() if len(set(items)) > 1]


def directory_case_groups(paths):
    grouped = {}
    for path in paths:
        parts = Path(path).parts
        for index in range(1, len(parts)):
            directory = "/".join(parts[:index])
            grouped.setdefault(directory.casefold(), set()).add(directory)
    return [sorted(items) for items in grouped.values() if len(items) > 1]


def extensionless_ts_groups(paths):
    grouped = {}
    for path in paths:
        if not path.endswith((".ts", ".tsx")) or path.endswith(".d.ts"):
            continue
        grouped.setdefault(path.rsplit(".", 1)[0].casefold(), []).append(path)
    return [sorted(items) for items in grouped.values() if len(set(items)) > 1]


def source_paths():
    found = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_symlink():
                raise AssertionError(f"Unsupported source symlink: {path}")
            if path.is_file():
                found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def direct_service_calls(tree):
    """Yield (service, method, line) for runtime.service.method() and the same on self.runtime."""

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.stack = []
            self.calls = []

        def visit_ClassDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Call(self, node):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
                owner = func.value
                if _runtime_receiver(owner, self.stack):
                    self.calls.append((owner.attr, func.attr, node.lineno))
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(tree)
    return visitor.calls


def _runtime_receiver(owner, stack):
    base = owner.value
    if isinstance(base, ast.Name) and base.id in {"runtime", "services"}:
        return True
    if (
        isinstance(base, ast.Attribute)
        and isinstance(base.value, ast.Name)
        and base.value.id == "self"
        and base.attr == "runtime"
    ):
        return True
    return bool(
        isinstance(base, ast.Name) and base.id == "self" and stack and stack[-1] == "Runtime"
    )


def test_macos_paths_and_service_callers_stay_resolvable(tmp_path):
    assert case_key_groups(
        ["frontend/src/diagnostics.tsx", "frontend/src/Diagnostics.tsx"]
    ) == [["frontend/src/Diagnostics.tsx", "frontend/src/diagnostics.tsx"]]
    assert directory_case_groups(["frontend/src/views/Foo/a.ts", "frontend/src/views/foo/b.tsx"])
    assert extensionless_ts_groups(
        ["frontend/src/diagnostics.ts", "frontend/src/diagnostics.tsx"]
    ) == [["frontend/src/diagnostics.ts", "frontend/src/diagnostics.tsx"]]
    assert extensionless_ts_groups(
        ["frontend/src/diagnostics.tsx", "frontend/src/diagnosticsData.ts"]
    ) == []
    paths = source_paths()
    assert paths, "source trees must be scanned"
    assert case_key_groups(paths) == []
    assert directory_case_groups(paths) == []
    assert extensionless_ts_groups(paths) == []

    app = app_at(tmp_path)
    services = {
        name: value
        for name, value in vars(app.state.runtime).items()
        if not name.startswith("_") and not callable(value)
    }
    missing = []
    checked = 0
    for path in (ROOT / "backend" / "desk").rglob("*.py"):
        calls = direct_service_calls(ast.parse(path.read_text(encoding="utf-8")))
        for service, method, line in calls:
            if service not in services:
                continue
            checked += 1
            if not hasattr(services[service], method):
                missing.append(f"{path.relative_to(ROOT)}:{line} {service}.{method}")
    assert checked > 100
    assert missing == []


def test_removed_method_detector_flags_a_missing_call():
    source = "class Runtime:\n    def tick(self):\n        self.jobs.listing()\n"
    calls = direct_service_calls(ast.parse(source))
    assert calls == [("jobs", "listing", 3)]
    assert not hasattr(object(), "listing")
