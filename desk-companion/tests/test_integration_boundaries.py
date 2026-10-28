"""Cross-stack authorization, retention and backup regression checks; offline fixtures only."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.access import digest
from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.exchange import BackupInput, ImportApply
from desk.jobs import FolderNaming, JobApproval, JobInput
from desk.persona import PersonaRevision
from desk.schemas import CreateEvents, EventInput, SettingsInput
from desk.store import DomainError, encode
from desk.text_ai import TextPlan
from desk.tool_policy import execute_tool

HEADERS = {"X-Desk-Request": "1"}


def app_at(path):
    return create_app(path, password="fixture", scheduler=False)


def owner_at(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": "fixture"}, headers=HEADERS
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
    return BackupInput(content=json.dumps(backup))


def test_backup_apply_and_replayed_receipt_require_owner(tmp_path):
    source = app_at(tmp_path / "source").state.runtime
    source.memory.create("Source fixture fact", "fact")
    source.persona.replace(PersonaRevision(body="Speak briefly.", expected_version=1), "style")
    source.jobs.enabled = True
    source.jobs.prepare(JobInput(title="Fixture", content="No execution"), "job")
    app = app_at(tmp_path / "target")
    owner = owner_at(app)
    paired = paired_at(app, owner)
    preview = owner.post(
        "/api/exchange/backup/preview",
        json={"content": json.dumps(source.exchange.backup())},
        headers={**HEADERS, "X-Operation-Id": "preview"},
    ).json()
    path = "/api/exchange/" + preview["preview_id"] + "/apply"
    response = paired.post(path, json={}, headers={"X-Operation-Id": "paired-apply"})
    assert response.status_code == 403, response.text
    assert app.state.runtime.memory.for_model() == []
    with app.state.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM assistant_persona").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0] == 0
    applied = owner.post(path, json={}, headers={**HEADERS, "X-Operation-Id": "owner-apply"})
    assert applied.status_code == 200
    result = applied.json()
    assert result["persona_created"] == 1 and result["jobs_created"] == 1
    assert paired.post(path, json={}, headers={"X-Operation-Id": "owner-apply"}).status_code == 403


@pytest.mark.parametrize(
    "tool,args,field",
    [
        ("memory_query", {}, "memories"),
        ("owner_search", {"query": "cobalt", "sources": ["memory"]}, "matches"),
    ],
)
def test_read_tools_recheck_after_forgetting_even_with_same_effect_key(tmp_path, tool, args, field):
    runtime = app_at(tmp_path).state.runtime
    fact = runtime.memory.create("The private fixture word is cobalt", "fact")["memory"]
    first = execute_tool(runtime, tool, args, "read", scope="same-operation")
    assert first[field]
    runtime.memory.delete(fact["id"], fact["version"], "forget")
    second = execute_tool(runtime, tool, args, "read", scope="same-operation")
    assert second[field] == [], second


def test_backup_cannot_rebind_a_queued_folder_job(tmp_path):
    runtime = app_at(tmp_path / "runtime").state.runtime
    folder_a, folder_b = tmp_path / "a", tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    runtime.jobs.set_folder(FolderNaming(label="A", path=str(folder_a.resolve())), "folder-a")
    draft = runtime.jobs.prepare(
        JobInput(action="save_folder_file", title="Fixture", content="Bound to A"), "job"
    )["job"]
    draft = runtime.jobs.detail(draft["id"], review=True)
    runtime.jobs.approve(
        draft["id"],
        JobApproval(expected_version=draft["version"], intent_hash=draft["intent_hash"]),
        "approve",
    )
    backup = runtime.exchange.backup()
    backup["payload"]["job_bundle"]["folder"]["path"] = str(folder_b.resolve())
    runtime.jobs.clear_folder("clear")
    preview = runtime.exchange.preview_backup(rehash(backup), "preview")
    with pytest.raises(DomainError) as refused:
        runtime.exchange.apply(preview["preview_id"], ImportApply(), "apply")
    assert refused.value.code in {"COMPUTER_SCOPE_CHANGED", "FOLDER_PATH_DENIED"}
    assert runtime.jobs.folder_config() is None
    assert list(folder_b.iterdir()) == []
    assert runtime.jobs.detail(draft["id"])["state"] == "queued"


def test_backup_rejects_incomplete_job_before_persisting(tmp_path):
    source = app_at(tmp_path / "source").state.runtime
    source.jobs.enabled = True
    source.jobs.prepare(JobInput(title="Fixture", content="No execution"), "job")
    backup = source.exchange.backup()
    row = backup["payload"]["job_bundle"]["jobs"][0]
    row["request"] = {"action": "save_note", "title": "Fixture", "content": "No execution"}
    row["intent_hash"] = digest(encode(row["request"]))
    target = app_at(tmp_path / "target").state.runtime
    with pytest.raises(DomainError) as refused:
        target.exchange.preview_backup(rehash(backup), "preview")
    assert refused.value.code == "INVALID_BACKUP"
    assert target.jobs.listing() == []


def test_linux_job_backup_round_trip_keeps_it_unapproved(tmp_path, monkeypatch):
    source = app_at(tmp_path / "source").state.runtime
    monkeypatch.setattr(source.jobs.desktop, "status", lambda: {"ready": True})
    source.jobs.prepare(
        JobInput(action="linux_note_preview", title="Fixture", content="No execution"), "job"
    )
    target = app_at(tmp_path / "target").state.runtime
    preview = target.exchange.preview_backup(
        BackupInput(content=json.dumps(source.exchange.backup())), "preview"
    )
    target.exchange.apply(preview["preview_id"], ImportApply(), "apply")
    rows = target.jobs.listing(review=True)
    assert (
        len(rows) == 1
        and rows[0]["action"] == "linux_note_preview"
        and rows[0]["state"] == "review"
    )
    with target.store.connection() as conn:
        assert conn.execute("SELECT approved_by,run_id FROM computer_jobs").fetchone()[:] == (
            None,
            None,
        )


@pytest.mark.parametrize("action", ["list", "confirm"])
def test_goal_drafts_retain_owner_boundary(tmp_path, action):
    app = app_at(tmp_path)
    owner = owner_at(app)
    paired = paired_at(app, owner)
    draft = app.state.runtime.assistant.local_message(
        AssistantMessage(message="Goal: finish fixture report"), "goal"
    )["proposal"]
    assert paired.get("/api/goals").status_code == 403
    if action == "list":
        assert draft["id"] not in [
            row["id"] for row in paired.get("/api/assistant/proposals").json()["proposals"]
        ]
    else:
        response = paired.post(
            "/api/assistant/proposals/" + draft["id"] + "/decisions",
            json={"action": "confirm"},
            headers={"X-Operation-Id": "paired-confirm"},
        )
        assert response.status_code == 403, response.text


def test_new_login_does_not_receive_other_login_transcript(tmp_path, monkeypatch):
    app = app_at(tmp_path)
    runtime = app.state.runtime
    captured = []
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(system, context, schema, purpose):
        captured.append(context)
        return TextPlan(message="Acknowledged", tool="none")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    first, second = owner_at(app), owner_at(app)
    for client, key, message in [
        (first, "one", "Transient fixture cobalt"),
        (second, "two", "Hello"),
    ]:
        response = client.post(
            "/api/assistant/messages",
            json={"message": message},
            headers={**HEADERS, "X-Operation-Id": key},
        )
        assert response.status_code == 200
    assert captured[1]["turns"] == [], captured[1]["turns"]


def test_real_policy_preserves_omitted_calendar_fields(tmp_path):
    runtime = app_at(tmp_path).state.runtime
    created = runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Fixture",
                start_local="2026-10-30T10:00",
                end_local="2026-10-30T11:00",
                notes="Keep private note",
                location="Fixture room",
                calendar="study",
                reminder_minutes=[60, 15],
                visibility="displayable",
            )
        ),
        "event",
    )
    event_id = created["event_ids"][0]
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
                    "title": "Fixture",
                    "start_local": "2026-10-30T12:00",
                    "end_local": "2026-10-30T13:00",
                },
            },
        },
        "move",
        scope="move-turn",
    )
    assert "Keep private note" not in str(result)
    runtime.assistant.decide(result["proposal"]["id"], "confirm", "confirm")
    with runtime.store.connection() as conn:
        saved = runtime.store.event(conn, event_id)
    assert saved["notes"] == "Keep private note" and saved["location"] == "Fixture room"
    assert saved["reminder_minutes"] == [60, 15] and saved["visibility"] == "displayable"


def test_hidden_goal_does_not_break_private_summary_consumers(tmp_path):
    runtime = app_at(tmp_path).state.runtime
    draft = runtime.assistant.local_message(
        AssistantMessage(message="Goal: fixture report"), "goal"
    )["proposal"]
    runtime.assistant.decide(draft["id"], "confirm", "confirm")
    runtime.store.update_settings(
        SettingsInput(timezone="Asia/Hong_Kong", hide_private=True, expected_version=1), "hide"
    )
    assert runtime.goals.listing()["goals"] == []
    assert runtime.profile.view()["text"] == ""
