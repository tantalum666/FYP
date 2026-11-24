
from datetime import UTC, datetime
from fastapi.testclient import TestClient
from google_desk_fixture import Desk, event
from desk.app import create_app

def test_backup_with_two_grants_sharing_remote_occurrence_preserves_both(tmp_path):
    clock = lambda: datetime(2026, 10, 1, tzinfo=UTC)
    apps = [create_app(tmp_path / sub, clock=clock, password="fixture-only",
                       scheduler=False, connector_configs=()) for sub in ("source", "fresh")]
    with TestClient(apps[0]) as a, TestClient(apps[1]) as b:
        source, fresh = Desk(apps[0], a), Desk(apps[1], b)
        source.import_events(event("shared-id", "Account A appointment"))
        source.connect("second")
        source.import_events(event("shared-id", "Account B appointment"))
        local_before = source.calendar()
        assert set(local_before) == {"Account A appointment", "Account B appointment"}
        assert len({e["id"] for e in local_before.values()}) == 2
        backup = a.get("/api/exchange/backup.json")
        assert backup.status_code == 200
        saved = backup.json()["payload"]["events"]
        print("source IDs", len({v["id"] for v in saved}), "source external IDs", len({v["external_id"] for v in saved}))
        assert len(saved) == 2
        preview = fresh.ok("/exchange/backup/preview", {"content": backup.text})
        assert [r["status"] for r in preview["rows"]] == ["new", "new"]
        response = fresh.post("/exchange/" + preview["preview_id"] + "/apply", {"replace_matching": False})
        after = fresh.calendar()
        print("apply", response.status_code, response.text, "destination calendar", sorted(after))
        assert response.status_code == 200
        assert {k: v["id"] for k,v in after.items()} == {k: v["id"] for k,v in local_before.items()}
