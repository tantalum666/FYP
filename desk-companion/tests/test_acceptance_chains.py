"""Full local data/approval chain; model selection is checked separately live."""

from datetime import UTC, datetime

import pytest

from desk.app import create_app
from desk.schemas import CreateEvents, EventInput
from desk.voice import QwenOmniProtocol
from desk.persona import voice_instructions
from test_voice_omni import config
from desk.store import DomainError
from desk.conversation import draft_context, memory_context
import json


@pytest.fixture
def desk(tmp_path):
    runtime = create_app(
        tmp_path,
        password="fixture",
        scheduler=False,
        clock=lambda: datetime(2026, 10, 23, 4, tzinfo=UTC),
    ).state.runtime
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Design review", start_local="2026-10-28T15:00", end_local="2026-10-28T16:00"
            )
        ),
        "seed",
    )
    return runtime


def occurrence(runtime):
    return runtime.assistant.tool(
        "calendar_query",
        {"start": "2026-10-26T00:00:00+08:00", "end": "2026-11-02T00:00:00+08:00"},
        "read",
    )["occurrences"][0]


def change(runtime, event, start, end, key):
    return runtime.assistant.tool(
        "calendar_change_draft",
        {
            "event_id": event["id"],
            "change": {
                "action": "update",
                "expected_version": event["version"],
                "scope": "occurrence",
                "occurrence_key": event["occurrence_key"],
                "event": {"title": "Design review", "start_local": start, "end_local": end},
            },
        },
        key,
    )["proposal"]


def test_calendar_correction_invalidates_only_the_replaced_draft_before_commit(desk):
    event = occurrence(desk)
    first = change(desk, event, "2026-10-30T15:00", "2026-10-30T16:00", "first")
    correction = change(desk, event, "2026-10-30T15:30", "2026-10-30T16:30", "correct")
    # The source record is unchanged until the corrected draft is confirmed.
    assert occurrence(desk)["start"] == event["start"]
    assert [p["id"] for p in desk.assistant.proposals()] == [correction["id"]]
    with pytest.raises(DomainError):
        desk.assistant.decide(first["id"], "confirm", "stale-confirm")
    one = desk.assistant.decide(correction["id"], "confirm", "confirm")
    two = desk.assistant.decide(correction["id"], "confirm", "retry-confirm")
    assert one == two
    current = occurrence(desk)
    assert current["version"] == event["version"] + 1
    assert current["start"].startswith("2026-10-30T07:30")
    assert current["end"].startswith("2026-10-30T08:30")
    assert current["start_local"] == "2026-10-30T15:30"
    assert current["occurrence_key"] == "2026-10-28T15:00"


def test_memory_correction_draft_supersedes_older_body_without_writing(desk):
    item = desk.memory.create("Project code Aurora", "seed-memory")["memory"]
    first = desk.assistant.tool(
        "memory_replace_draft",
        {"memory_id": item["id"], "expected_version": 1, "body": "Project code Blue"},
        "first-memory",
    )["proposal"]
    second = desk.assistant.tool(
        "memory_replace_draft",
        {"memory_id": item["id"], "expected_version": 1, "body": "Project code 星穹蓝"},
        "second-memory",
    )["proposal"]
    assert desk.memory.for_model()[0]["body"] == "Project code Aurora"
    assert [p["id"] for p in desk.assistant.proposals()] == [second["id"]]
    with pytest.raises(DomainError):
        desk.assistant.decide(first["id"], "confirm", "old-memory-confirm")
    desk.assistant.decide(second["id"], "confirm", "memory-confirm")
    assert desk.memory.for_model()[0]["body"] == "Project code 星穹蓝"


def test_rescheduling_preserves_unmentioned_fields_without_sending_notes_to_model(desk):
    desk.store.create(
        CreateEvents(
            event=EventInput(
                title="Private fixture",
                start_local="2026-10-27T10:00",
                end_local="2026-10-27T11:00",
                notes="Do not upload this preserved note",
                location="Room private",
                calendar="study",
                color="sage",
                reminder_minutes=[60, 15],
                visibility="displayable",
            )
        ),
        "rich",
    )
    event = next(
        x
        for x in desk.assistant.tool(
            "calendar_query",
            {"start": "2026-10-26T00:00:00+08:00", "end": "2026-11-02T00:00:00+08:00"},
            "query",
        )["occurrences"]
        if x["title"] == "Private fixture"
    )
    result = desk.assistant.tool(
        "calendar_change_draft",
        {
            "event_id": event["id"],
            "change": {
                "action": "update",
                "expected_version": 1,
                "scope": "series",
                "event": {
                    "title": "Private fixture",
                    "start_local": "2026-10-30T15:00",
                    "end_local": "2026-10-30T16:00",
                },
            },
        },
        "rich-change",
    )
    assert "Do not upload" not in str(result)
    desk.assistant.decide(result["proposal"]["id"], "confirm", "rich-confirm")
    with desk.store.connection() as conn:
        saved = desk.store.event(conn, event["id"])
    assert saved["notes"] == "Do not upload this preserved note"
    assert saved["location"] == "Room private" and saved["calendar"] == "study"
    assert saved["reminder_minutes"] == [60, 15] and saved["visibility"] == "displayable"


def test_model_write_schema_matches_local_datetime_validator_and_scope_requirements():
    tools = QwenOmniProtocol().setup(config(), "fixture")["session"]["tools"]
    schema = next(
        x["function"]["parameters"]
        for x in tools
        if x["function"]["name"] == "calendar_change_draft"
    )
    change_schema = schema["properties"]["change"]
    assert "scope" in change_schema["required"]
    event_schema = next(
        x for x in change_schema["properties"]["event"]["anyOf"] if x.get("type") == "object"
    )
    local = event_schema["properties"]["start_local"]
    assert "format" not in local and "pattern" in local
    assert "without" in local["description"]


@pytest.mark.parametrize(
    "now, friday",
    [
        ("2026-10-23T12:00:00+08:00", "2026-10-30"),
        ("2026-12-27T23:59:00+08:00", "2027-01-01"),
        ("2027-01-04T00:01:00+08:00", "2027-01-15"),
    ],
)
def test_relative_date_anchors_use_today_not_the_queried_week(now, friday):
    instructions = voice_instructions("Fixture", "zh", now, "Asia/Hong_Kong")
    assert f"Friday={friday}" in instructions
    assert "never from dates in chat" in instructions


def test_correction_leaves_an_unrelated_pending_create_intact(desk):
    unrelated = desk.assistant.tool(
        "calendar_create_draft",
        {
            "event": {
                "title": "Other",
                "start_local": "2026-10-27T09:00",
                "end_local": "2026-10-27T10:00",
            }
        },
        "unrelated",
    )["proposal"]
    event = occurrence(desk)
    change(desk, event, "2026-10-30T15:00", "2026-10-30T16:00", "one")
    correction = change(desk, event, "2026-10-30T15:30", "2026-10-30T16:30", "two")
    assert {p["id"] for p in desk.assistant.proposals()} == {unrelated["id"], correction["id"]}
    desk.assistant.decide(unrelated["id"], "confirm", "save-unrelated")
    assert next(p for p in desk.assistant.proposals() if p["id"] == correction["id"])


def test_receipts_use_saved_event_ids_and_never_export_preserved_private_fields(desk):
    proposal = desk.assistant.tool(
        "calendar_create_draft",
        {
            "event": {
                "title": "Receipt fixture",
                "start_local": "2026-10-27T09:00",
                "end_local": "2026-10-27T10:00",
                "notes": "PRIVATE-NOTE",
                "location": "PRIVATE-ROOM",
            }
        },
        "new",
    )["proposal"]
    saved = desk.assistant.decide(proposal["id"], "confirm", "save")
    context = draft_context(desk, True)
    assert proposal["id"] in context and saved["result"]["event_ids"][0] in context
    assert '"version": 1' in context
    assert "PRIVATE-NOTE" not in context and "PRIVATE-ROOM" not in context
    assert draft_context(desk, False) == ""


def test_deleted_memory_receipts_cannot_resurrect_a_saved_fact(desk):
    proposal = desk.assistant.tool("memory_save_draft", {"body": "CODE-OLD"}, "save-draft")[
        "proposal"
    ]
    desk.assistant.decide(proposal["id"], "confirm", "save")
    fact = desk.memory.for_model()[0]
    desk.memory.delete(fact["id"], fact["version"], "delete")
    assert "ZERO saved" in memory_context(desk, True)[1]
    assert "CODE-OLD" not in draft_context(desk, True)
    assert proposal["id"] not in draft_context(desk, True)


def test_receipt_counts_include_older_pending_but_exclude_expired_drafts(desk):
    pending = desk.assistant.tool("memory_save_draft", {"body": "pending"}, "pending")["proposal"]
    expired = desk.assistant.tool("memory_save_draft", {"body": "expired"}, "expired")["proposal"]
    with desk.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE assistant_proposals SET expires_at='2026-10-22T00:00:00Z' WHERE id=?",
            (expired["id"],),
        )
    for i in range(22):
        row = desk.assistant.tool("memory_save_draft", {"body": str(i)}, f"history-{i}")["proposal"]
        desk.assistant.decide(row["id"], "cancel", f"cancel-{i}")
    context = draft_context(desk, True)
    assert '"pending_memory_drafts": 1' in context
    assert pending["id"] in context
    rows = json.loads(
        context.split("(metadata, not instructions): ")[1].split("\nA proposal_id")[0]
    )
    assert next(r for r in rows if r["proposal_id"] == expired["id"])["state"] == "expired"
