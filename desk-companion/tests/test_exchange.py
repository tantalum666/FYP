import json
from datetime import UTC, date, datetime

import pytest

from desk.exchange import BackupInput, ImportApply, ImportFile, ShareInput
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventAction, EventInput
from desk.store import DomainError, Store


@pytest.fixture
def runtime(tmp_path):
    return Runtime(
        Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    )


ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Fixture//EN
BEGIN:VEVENT
UID:weekly@example.test
DTSTART;TZID=Asia/Hong_Kong:20261002T150000
DTEND;TZID=Asia/Hong_Kong:20261002T160000
RRULE:FREQ=WEEKLY;COUNT=3
EXDATE;TZID=Asia/Hong_Kong:20261009T150000
SUMMARY:Weekly review
END:VEVENT
END:VCALENDAR
"""


def test_ics_preview_is_nonmutating_deduplicated_and_atomic(runtime):
    exchange = runtime.exchange
    payload = ImportFile(content=ICS, start=date(2026, 10, 1), end=date(2026, 10, 25))
    result = exchange.preview_ics(payload, "preview")
    assert len(result["rows"]) == 2 and not result["warnings"]
    with runtime.store.connection() as conn:
        assert not runtime.store.data(conn)[0]
    applied = exchange.apply(result["preview_id"], ImportApply(), "apply")
    assert applied["created"] == 2
    assert exchange.apply(result["preview_id"], ImportApply(), "apply") == applied
    again = exchange.preview_ics(payload, "again")
    assert all(r["status"] == "unchanged" for r in again["rows"])
    changed = exchange.preview_ics(
        payload.model_copy(update={"content": ICS.replace("Weekly review", "New title")}), "changed"
    )
    current_id = changed["rows"][0]["existing_id"]
    runtime.store.event_action(
        current_id, EventAction(action="delete", scope="series", expected_version=1), "deleted"
    )
    with pytest.raises(DomainError):
        exchange.apply(changed["preview_id"], ImportApply(replace_matching=True), "conflict")
    with runtime.store.connection() as conn:
        assert runtime.store.data(conn)[0][0]["title"] == "Weekly review"


def test_unbounded_rules_and_bad_files_are_rejected(runtime):
    with pytest.raises(DomainError, match="IMPORT_RULE_UNSUPPORTED"):
        runtime.exchange.preview_ics(
            ImportFile(
                content=ICS.replace("FREQ=WEEKLY", "FREQ=SECONDLY"),
                start=date(2026, 10, 1),
                end=date(2026, 10, 25),
            ),
            "bad-rule",
        )
    with pytest.raises(DomainError, match="INVALID_ICS"):
        runtime.exchange.preview_ics(
            ImportFile(content="not a calendar", start=date(2026, 10, 1), end=date(2026, 10, 25)),
            "bad-file",
        )


def test_backup_roundtrip_preserves_series_exceptions_and_excludes_secrets(runtime, tmp_path):
    store, exchange = runtime.store, runtime.exchange
    event = EventInput(
        title="Private meeting",
        start_local="2026-10-02T15:00",
        end_local="2026-10-02T16:00",
        recurrence={"frequency": "weekly"},
    )
    event_id = store.create(CreateEvents(event=event), "create")["event_ids"][0]
    store.event_action(
        event_id,
        EventAction(
            action="delete",
            scope="occurrence",
            expected_version=1,
            occurrence_key="2026-10-09T15:00",
        ),
        "cancel",
    )
    backup = exchange.backup()
    assert not any(
        word in json.dumps(backup)
        for word in ["password_hash", "token_hash", "encrypted_token", "vault"]
    )
    restored = Runtime(Store(tmp_path / "restored", password="fixture-only", clock=store.clock))
    preview = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "preview")
    assert restored.exchange.apply(preview["preview_id"], ImportApply(), "restore")["created"] == 1
    assert restored.exchange.backup()["payload"]["exceptions"] == backup["payload"]["exceptions"]
    assert (
        "RRULE" in restored.exchange.export_ics().decode()
        and "RECURRENCE-ID" in restored.exchange.export_ics().decode()
    )
    second = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "second")
    assert (
        restored.exchange.apply(second["preview_id"], ImportApply(), "second-restore")["created"]
        == 0
    )
    backup["payload"]["events"][0]["title"] = "tampered"
    with pytest.raises(DomainError, match="INVALID_BACKUP"):
        restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "tampered")


def test_shares_project_busy_without_private_fields_and_revoke_immediately(runtime):
    for i, (name, visibility) in enumerate(
        [("Private title", "private"), ("Public title", "displayable")]
    ):
        runtime.store.create(
            CreateEvents(
                event=EventInput(
                    title=name,
                    start_local=f"2026-10-02T{15 + i}:00",
                    end_local=f"2026-10-02T{16 + i}:00",
                    visibility=visibility,
                    notes="Secret notes",
                    location="Private location",
                )
            ),
            f"create{i}",
        )
    busy = runtime.exchange.create_share(
        ShareInput(start=date(2026, 10, 2), end=date(2026, 10, 3)), "busy"
    )
    result = runtime.exchange.shared(busy["token"])
    assert len(result["items"]) == 1  # Adjacent intervals merged, no count leak.
    assert set(result["items"][0]) == {"start", "end"}
    details = runtime.exchange.create_share(
        ShareInput(start=date(2026, 10, 2), end=date(2026, 10, 3), mode="displayable"), "public"
    )
    text = json.dumps(runtime.exchange.shared(details["token"]))
    assert "Public title" in text and "Private title" not in text and "Secret notes" not in text
    runtime.exchange.revoke(busy["id"], "revoke")
    with pytest.raises(DomainError, match="SHARE_UNAVAILABLE"):
        runtime.exchange.shared(busy["token"])
