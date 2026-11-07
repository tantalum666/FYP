import re

import pytest
from pydantic import ValidationError

from desk.schemas import EventInput


def test_model_time_contract_matches_strict_local_wall_clock_api():
    fields = EventInput.model_json_schema()["properties"]
    for name in ("start_local", "end_local"):
        assert "format" not in fields[name]
        assert re.fullmatch(fields[name]["pattern"], "2026-11-22T19:30")
        assert re.fullmatch(fields[name]["pattern"], "2026-11-22T19:30:00")
        assert not re.fullmatch(fields[name]["pattern"], "2026-11-22T19:30:00+08:00")
    valid = dict(
        title="Fixture",
        start_local="2026-11-22T19:30",
        end_local="2026-11-22T23:15",
        timezone="Asia/Hong_Kong",
    )
    assert EventInput(**valid).start_local.tzinfo is None
    assert fields["reminder_minutes"]["default"] == EventInput(**valid).reminder_minutes
    assert EventInput(**{**valid, "reminder_minutes": []}).reminder_minutes == []
    with pytest.raises(ValidationError):
        EventInput(**{**valid, "start_local": "2026-11-22T19:30:00+08:00"})
