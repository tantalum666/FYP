import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest

from desk.assistant import AssistantMessage, TOOLS
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventAction, EventInput
from desk.store import DomainError, Store
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences, is_quiet, quiet_until


@pytest.fixture
def runtime(tmp_path):
    clock = [datetime(2026, 10, 2, 12, tzinfo=UTC)]
    store = Store(tmp_path, password="fixture-only", clock=lambda: clock[0])
    return Runtime(store), clock


def test_draft_never_saves_without_user_and_confirmation_is_repeat_safe(runtime):
    runtime, clock = runtime
    service = runtime.assistant
    reply = service.local_message(
        AssistantMessage(message="明天15:00到16:00 项目讨论", language="zh"), "draft"
    )
    proposal = reply["proposal"]
    assert not reply["saved"] and proposal["data"]["event"]["start_local"] == "2026-10-03T15:00:00"
    with runtime.store.connection() as conn:
        assert not runtime.store.data(conn)[0]
    first = service.decide(proposal["id"], "confirm", "once")
    clock[0] += timedelta(hours=1)
    assert service.decide(proposal["id"], "confirm", "retry") == first
    with runtime.store.connection() as conn:
        assert len(runtime.store.data(conn)[0]) == 1
    assert all("confirm" not in tool["name"] for tool in TOOLS)
    with pytest.raises(DomainError, match="TOOL_NOT_ALLOWED"):
        service.tool("confirm", {"id": proposal["id"]}, "injected")


def test_missing_duration_clarifies_cancel_and_expiry_do_not_save(runtime):
    runtime, clock = runtime
    service = runtime.assistant
    assert (
        service.local_message(AssistantMessage(message="Add tomorrow 15:00 Meeting"), "missing")[
            "kind"
        ]
        == "clarify"
    )
    reply = service.local_message(AssistantMessage(message="Tomorrow 15:00-16:00 Review"), "draft")
    service.decide(reply["proposal"]["id"], "cancel", "cancel")
    assert service.decide(reply["proposal"]["id"], "cancel", "cancel")["state"] == "cancelled"
    other = service.local_message(AssistantMessage(message="Tomorrow 15:00-16:00 Review"), "other")
    clock[0] += timedelta(minutes=6)
    with pytest.raises(DomainError, match="DRAFT_EXPIRED"):
        service.decide(other["proposal"]["id"], "confirm", "expired")


def test_change_draft_version_conflicts_and_hidden_titles_do_not_leave_tool(runtime):
    runtime, clock = runtime
    store, service = runtime.store, runtime.assistant
    event = EventInput(title="Hidden", start_local="2026-10-02T21:00", end_local="2026-10-02T22:00")
    event_id = store.create(CreateEvents(event=event), "create")["event_ids"][0]
    proposal = service.tool(
        "calendar_change_draft",
        {
            "event_id": event_id,
            "change": {"action": "delete", "scope": "series", "expected_version": 1},
        },
        "change",
    )["proposal"]
    store.event_action(
        event_id,
        EventAction(
            action="update",
            scope="series",
            expected_version=1,
            event=event.model_copy(update={"title": "Changed"}),
        ),
        "edit",
    )
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        service.decide(proposal["id"], "confirm", "confirm")
    from desk.schemas import SettingsInput

    store.update_settings(
        SettingsInput(expected_version=1, hide_private=True, timezone="Asia/Hong_Kong"), "privacy"
    )
    result = service.tool(
        "calendar_query",
        {"start": clock[0].isoformat(), "end": (clock[0] + timedelta(days=1)).isoformat()},
        "query",
    )
    assert "Changed" not in json.dumps(result)


def test_public_weather_is_opt_in_cached_and_stale_data_is_labelled(runtime):
    runtime, clock = runtime
    data = runtime.data
    calls = []

    def response(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "temperature": {
                    "data": [{"place": "Hong Kong Observatory", "value": 28}],
                    "recordTime": "2026-10-02T20:00:00+08:00",
                },
                "icon": [50],
            },
        )

    data.transport = httpx.MockTransport(response)
    data.poll_weather()
    assert not calls and data.snapshot()["weather"]["status"] == "not_configured"
    data.update(
        PreferencesUpdate(
            expected_version=1,
            preferences=WorkspacePreferences(
                weather_location="hong_kong", holiday_region="hong_kong"
            ),
        ),
        uuid4().hex,
    )
    data.poll_weather()
    data.poll_weather()
    assert len(calls) == 1 and data.snapshot()["weather"]["temperature_c"] == 28
    assert "2026-10-01" in data.snapshot()["holidays"]["en"]
    clock[0] += timedelta(hours=2)
    assert data.snapshot()["weather"]["status"] == "stale"


def test_quiet_hours_cross_midnight_and_csv_cannot_inject_formulas(runtime):
    runtime, _ = runtime
    prefs = WorkspacePreferences().model_dump()
    assert is_quiet(prefs, datetime(2026, 10, 2, 23))
    assert is_quiet(prefs, datetime(2026, 10, 2, 6))
    assert not is_quiet(prefs, datetime(2026, 10, 2, 12))
    hk = ZoneInfo("Asia/Hong_Kong")
    assert quiet_until(prefs, datetime(2026, 10, 2, 23, tzinfo=hk)) == datetime(
        2026, 10, 3, 7, tzinfo=hk
    )
    assert quiet_until(prefs, datetime(2026, 10, 3, 6, 30, tzinfo=hk)) == datetime(
        2026, 10, 3, 7, tzinfo=hk
    )
    assert quiet_until(prefs, datetime(2026, 10, 3, 12, tzinfo=hk)) is None
    always = {**prefs, "quiet_start": "00:00", "quiet_end": "00:00"}
    assert quiet_until(always, datetime(2026, 10, 3, 12, tzinfo=hk)) == datetime(
        2026, 10, 4, 12, tzinfo=hk
    )
    runtime.store.create(
        CreateEvents(
            event=EventInput(
                title="=HYPERLINK(1)", start_local="2026-10-02T21:00", end_local="2026-10-02T22:00"
            )
        ),
        "danger-title",
    )
    assert "'=HYPERLINK(1)" in runtime.data.records_csv()
