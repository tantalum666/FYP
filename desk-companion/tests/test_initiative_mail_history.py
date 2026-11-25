from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from desk import initiative_sources
from desk.app import create_app
from desk.initiative import Initiative
from desk.store import DomainError
from desk.text_ai import TextConfig


def test_rotated_inbox_recovers_verified_history_without_new_interruptions(tmp_path, monkeypatch):
    now = [datetime(2026, 11, 25, 4, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: now[0])
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        "openai", "test", "https://api.openai.com/v1/responses", "test", background=True
    )
    r.openai_spend.path = tmp_path / "closed-test-budget"
    monkeypatch.setattr(r.openai_spend, "summary", lambda: {"active": False, "available_usd": 0})
    monkeypatch.setattr(
        r.text_ai, "generate", lambda *a, **k: (_ for _ in ()).throw(AssertionError("inference"))
    )
    account = {"connected": True, "version": "original", "email": "owner@example.test"}
    monkeypatch.setattr(r.outbound_mail.auth, "account", lambda: account)
    original = {
        "id": "original",
        "thread_id": "thread-a",
        "labels": ["INBOX"],
        "headers": [{"name": "Subject", "value": "Library pickup"}],
        "snippet": "Collect the atlas before Friday.",
    }
    recent, archived = [original], [original]
    offline, reads = False, []

    def read(_, query):
        reads.append(query.query)
        if offline:
            raise DomainError("APP_CONNECTION_FAILED", 502)
        return {"items": archived if "before:" in query.query else recent}

    monkeypatch.setattr(initiative_sources, "query_connected_app", read)
    r.initiative.advance()
    active = r.initiative.snapshot()["findings"]
    assert len(active) == 1 and active[0]["sources"][0]["href"].endswith("#all/thread-a")
    ident, created = active[0]["id"], active[0]["created_at"]

    offline = True
    now[0] += timedelta(minutes=6)
    r.initiative.advance()
    state = r.initiative.snapshot()
    assert not state["findings"] and not state["history"] and not state["mail_check"]["available"]
    with r.store.connection() as db:
        assert (
            db.execute("SELECT state FROM initiative_findings WHERE id=?", (ident,)).fetchone()[0]
            == "pending"
        )
        assert (
            db.execute("SELECT state FROM notice_inbox WHERE id LIKE 'insight-%'").fetchone()[0]
            == "open"
        )

    # Start with a pre-fix row that became obsolete when its original message
    # left the first ten results. Reopening uses the original dated suggestion.
    with r.store.connection(write=True) as db:
        db.execute("UPDATE initiative_findings SET state='obsolete' WHERE id=?", (ident,))
    r.initiative = Initiative(r)
    offline = False
    recent[:] = [{**original, "id": "new", "headers": [], "snippet": "Hello."}]
    now[0] += timedelta(minutes=6)
    r.initiative.advance()
    state = r.initiative.snapshot()
    assert state["findings"] == [] and r.initiative.cue() is None
    assert [(row["id"], row["created_at"]) for row in state["history"]] == [(ident, created)]
    assert state["history"][0]["sources"][0]["href"].endswith("#all/thread-a")
    assert not r.initiative.sources.collect()[1].get("mail:gmail:original")
    for _ in range(2):
        r.initiative.advance()
    assert len([q for q in reads if "before:" in q]) == 1
    with r.store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM notice_deliveries WHERE channel='in_app'").fetchone()[
                0
            ]
            == 1
        )
        assert db.execute("SELECT count(*) FROM text_ai_usage").fetchone()[0] == 0

    archived[:] = [{**original, "labels": ["TRASH"]}]
    now[0] += timedelta(minutes=31)
    r.initiative.advance()
    assert r.initiative.snapshot()["history"] == []
    archived[:] = [original]
    now[0] += timedelta(minutes=31)
    r.initiative.advance()
    assert r.initiative.snapshot()["history"]
    account["reconnect_required"] = True
    assert not r.initiative.snapshot()["history"]
    assert r.initiative.snapshot()["mail_check"]["error"] == "APP_RECONNECT_REQUIRED"
    account["reconnect_required"] = False
    account.update(version="other", email="other@example.test")
    assert not r.initiative.snapshot()["history"]
    now[0] += timedelta(minutes=31)
    r.initiative.advance()
    assert not r.initiative.snapshot()["history"]
    account.update(version="original", email="owner@example.test")
    now[0] += timedelta(minutes=31)
    r.initiative.advance()
    assert r.initiative.snapshot()["history"]
    client = TestClient(app)
    headers = {"X-Desk-Request": "1"}
    assert client.post(
        "/api/session", json={"username": "owner", "password": "fixture"}, headers=headers
    ).is_success
    assert client.post(
        f"/api/initiative/{ident}/dismissals",
        json={},
        headers={**headers, "X-Operation-ID": "dismiss-old"},
    ).is_success
    assert not r.initiative.snapshot()["history"]
    now[0] += timedelta(days=8)
    reads.clear()
    r.initiative.advance()
    assert not any("before:" in query for query in reads)


def test_quiet_mail_is_rechecked_before_its_first_alert(tmp_path, monkeypatch):
    now = [datetime(2026, 11, 25, 14, tzinfo=UTC)]  # 22:00 in Hong Kong
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: now[0])
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        "openai", "test", "https://api.openai.com/v1/responses", "test", background=True
    )
    r.openai_spend.path = tmp_path / "closed-test-budget"
    monkeypatch.setattr(r.openai_spend, "summary", lambda: {"active": False, "available_usd": 0})
    account = {"connected": True, "version": "same", "email": "owner@example.test"}
    monkeypatch.setattr(r.outbound_mail.auth, "account", lambda: account)
    offer = {
        "id": "book",
        "thread_id": "thread",
        "snippet": "Collect the book before Friday.",
        "headers": [],
    }
    recent = [offer]
    pending_original = []

    def read(_, query):
        return {"items": pending_original if "before:" in query.query else recent}

    monkeypatch.setattr(initiative_sources, "query_connected_app", read)
    r.initiative.advance()
    assert len(r.initiative.snapshot()["findings"]) == 1
    assert not r.notify.listing()["notices"]
    recent.clear()
    now[0] += timedelta(hours=10)
    r.initiative.advance()
    assert not r.notify.listing()["notices"]  # missing even from the explicit check
    pending_original.append(offer)
    now[0] += timedelta(minutes=31)
    r.initiative.advance()
    assert len(r.notify.listing()["notices"]) == 1
    assert len(r.initiative.snapshot()["history"]) == 1
    r.initiative.advance()
    assert len(r.notify.listing()["notices"]) == 1
