"""Owner-scoped search, plate summary, and timezone clock."""

import asyncio
from datetime import datetime
from uuid import uuid4

from desk.assistant import TOOLS
from desk.capabilities import CAPABILITIES
from desk.jobs import JobInput
from desk.schemas import CreateEvents, EventInput
from desk.tasks import TaskInput
from desk.tool_dispatch import ToolDispatcher
from desk.voice import GeminiProtocol, QwenAudioProtocol, VoiceConfig

from test_agent_loop import _runtime


def test_lookup_tools_are_read_only_and_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    runtime = _runtime(tmp_path)
    runtime.memory.create("The spare key is under the lantern.", "fact-1")
    runtime.tasks.create(
        TaskInput(
            title="Pack the lantern",
            due_local=datetime(2026, 10, 27, 18, 0),
            timezone="Asia/Hong_Kong",
        ),
        "task-1",
    )
    runtime.tasks.create(
        TaskInput(
            title="November filing",
            due_local=datetime(2026, 11, 20, 9, 0),
            timezone="Asia/Hong_Kong",
        ),
        "task-2",
    )
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="Lantern review",
                start_local=datetime(2026, 10, 27, 10, 0),
                end_local=datetime(2026, 10, 27, 10, 30),
                timezone="Asia/Hong_Kong",
                visibility="displayable",
            )
        ),
        "event-today",
    )
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="November offsite",
                start_local=datetime(2026, 11, 20, 9, 0),
                end_local=datetime(2026, 11, 20, 12, 0),
                timezone="Asia/Hong_Kong",
                visibility="displayable",
            )
        ),
        "event-later",
    )
    runtime.jobs.prepare(JobInput(title="Desk note", content="Bring the lens"), "note-1")

    found = runtime.assistant.tool(
        "owner_search", {"query": "lantern"}, "lookup-search", allow_memory=True
    )
    sources = {row["source"] for row in found["matches"]}
    assert found["saved"] is False
    assert sources == {"memory", "tasks", "calendar"}
    assert all("path" not in row and "executor" not in row for row in found["matches"])
    lens = runtime.assistant.tool(
        "owner_search",
        {"query": "lens", "sources": ["notes"]},
        "lookup-note",
    )
    assert lens["matches"] == [
        {
            "source": "notes",
            "id": lens["matches"][0]["id"],
            "state": "review",
            "title": "Desk note",
            "snippet": "Bring the lens",
        }
    ]
    assert list(runtime.store.directory.glob("computer-notes/*.txt")) == []

    plate = runtime.assistant.tool("plate_summary", {"window": "today"}, "lookup-plate")
    assert plate["saved"] is False and plate["timezone"] == "Asia/Hong_Kong"
    assert plate["start"] == "2026-10-27"
    assert {row["title"] for row in plate["tasks"]} == {"Pack the lantern"}
    assert {row["title"] for row in plate["occurrences"]} == {"Lantern review"}

    clock = runtime.assistant.tool("owner_clock", {}, "lookup-clock")
    assert clock["weekday"] == "Tuesday"
    assert clock["today"] == "2026-10-27"
    assert clock["week_start"] == "2026-10-26" and clock["week_end"] == "2026-11-01"
    assert clock["now"].startswith("2026-10-27T08:00:00")

    rows = runtime.assistant.audit.listing()
    audited = {row["tool"] for row in rows}
    assert {"owner_search", "plate_summary", "owner_clock"} <= audited
    assert all(row["risk"] == "read" and row["saved"] is False for row in rows)
    assert {tool["name"] for tool in TOOLS} == set(CAPABILITIES)
    assert CAPABILITIES["owner_search"].risk == "read"


def test_paired_session_cannot_search_owner_facts(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.memory.create("Hidden lantern fact", uuid4().hex)
    qwen = QwenAudioProtocol().setup(VoiceConfig(), "Test", allow_memory=False)
    gemini = GeminiProtocol().setup(VoiceConfig(), "Test", allow_memory=False)
    offered = [tool["function"]["name"] for tool in qwen["session"]["tools"]]
    offered += [
        tool["name"] for tool in gemini["setup"]["tools"][0]["functionDeclarations"]
    ]
    assert "owner_search" not in offered and "memory_query" not in offered

    async def run():
        dispatcher = ToolDispatcher(runtime, "paired", allow_memory=False)
        dispatcher.submit(
            {"id": "search", "name": "owner_search", "arguments": {"query": "lantern"}}
        )
        _event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=2)
        await dispatcher.close()
        return result

    result = asyncio.run(run())
    assert result == {"error": "OWNER_SIGN_IN_REQUIRED", "saved": False}
    assert "Hidden" not in str(result)
    row = runtime.assistant.audit.listing()[0]
    assert row["tool"] == "owner_search" and row["outcome"] == "OWNER_SIGN_IN_REQUIRED"
    assert "Hidden" not in str(row)
