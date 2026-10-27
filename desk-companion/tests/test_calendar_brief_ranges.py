from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from desk.assistant import AssistantMessage, query_period
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventInput, SettingsInput
from desk.store import Store


@pytest.mark.parametrize(
    "now,start,end",
    [
        ("2026-10-25T23:50:00", "2026-10-26", "2026-11-02"),
        ("2026-10-26T00:00:00", "2026-11-02", "2026-11-09"),
        ("2026-12-31T10:00:00", "2027-01-04", "2027-01-11"),
    ],
)
def test_next_week_is_next_full_monday_week(now, start, end):
    for text in ["我下一周有什么会议", "下周日程", "What meetings do I have next week?"]:
        a, b = query_period(
            text, datetime.fromisoformat(now).replace(tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        assert a.date().isoformat() == start and b.date().isoformat() == end
        assert a.hour == b.hour == 0


def test_dst_week_uses_local_calendar_days():
    a, b = query_period("next week", datetime(2026, 10, 23, tzinfo=ZoneInfo("America/New_York")))
    assert (b.astimezone(UTC) - a.astimezone(UTC)).total_seconds() == 169 * 3600


def test_day_scope_and_unsupported_range_never_fall_back_to_today():
    now = datetime(2026, 10, 23, tzinfo=ZoneInfo("Asia/Hong_Kong"))
    assert query_period("后天的日程", now)[0].day == 25
    assert query_period("day after tomorrow", now)[0].day == 25
    assert query_period("下周日的日程", now)[0].isoformat().startswith("2026-11-01")
    assert query_period("2026-11-10 calendar", now)[0].day == 10
    for text in [
        "下个月的日程",
        "下月日程",
        "last week events",
        "今天和明天的日程",
        "today and next week events",
        "next Monday",
        "2026-02-30 events",
        "2026-10-23 to 2026-10-25 calendar",
    ]:
        assert query_period(text, now) is None


def test_local_brief_reads_real_range_preserves_privacy_and_excludes_next_boundary(tmp_path):
    store = Store(
        tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 23, 8, tzinfo=UTC)
    )
    runtime = Runtime(store)
    for name, day in [
        ("Today", "2026-10-23"),
        ("Next week", "2026-10-26"),
        ("Right boundary", "2026-11-02"),
    ]:
        store.create(
            CreateEvents(
                event=EventInput(title=name, start_local=day + "T00:00", end_local=day + "T01:00")
            ),
            name,
        )
    reply = runtime.assistant.local_message(
        AssistantMessage(message="我下一周有什么会议", language="zh"), "read"
    )
    assert [o["title"] for o in reply["occurrences"]] == ["Next week"]
    assert "2026-10-26 – 2026-11-01" in reply["message"]
    assert reply["range"]["end_exclusive"]
    store.update_settings(
        SettingsInput(expected_version=1, hide_private=True, timezone="Asia/Hong_Kong"), "private"
    )
    private = runtime.assistant.local_message(
        AssistantMessage(message="下周的日程", language="zh"), "private-read"
    )
    assert "Next week" not in str(private)
    assert "私人日程" in private["message"]
    empty = runtime.assistant.local_message(
        AssistantMessage(message="明天日程", language="zh"), "empty"
    )
    assert "2026-10-24" in empty["message"] and "0 项" in empty["message"]
    for text in ["删除下周的日程", "Cancel next week meetings"]:
        assert (
            runtime.assistant.local_message(AssistantMessage(message=text), text)["kind"]
            == "clarify"
        )
    assert runtime.assistant.proposals() == []
