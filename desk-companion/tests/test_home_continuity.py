from datetime import UTC, datetime
import json
import asyncio

from fastapi.testclient import TestClient

from desk.app import COOKIE, create_app
from desk.initiative import Initiative
from desk.text_ai import TextConfig
from session_protocol_fixture import install_session_protocol


def normal_desk(path):
    app = create_app(path, password="fixture", scheduler=False)
    r = app.state.runtime
    provider = install_session_protocol(r)
    client = TestClient(app, headers={"X-Desk-Request": "1"})
    client.post(
        "/api/session", json={"username": "owner", "password": "fixture"}
    ).raise_for_status()
    return r, provider, client


def preferences(client, *, save=True, share=True, voice=False):
    settings = client.get("/api/assistant/context-settings").json()
    return client.post(
        "/api/assistant/context-settings",
        headers={"X-Operation-Id": f"prefs-{settings['version']}"},
        json={
            "expected_version": settings["version"],
            "save_text_history": save,
            "save_voice_transcripts": voice,
            "use_text_history_in_ai": share,
            "use_memory_in_ai": share,
            "share_business_context": share,
            "approved_destinations": [
                d["id"] for d in settings["destinations"] if d["kind"] == "text" or voice
            ],
        },
    )


def send(client, words, op):
    response = client.post(
        "/api/assistant/messages",
        headers={"X-Operation-Id": op},
        json={"message": words, "language": "en"},
    )
    response.raise_for_status()
    return response.json()


def test_normal_window_reopens_local_prose_across_restart_without_restoring_old_authority(tmp_path):
    r, api, c = normal_desk(tmp_path)
    user = "The lamp on my study desk has an amber shade. What colour would go with it?"
    api.final = "The amber lamp suits the study."
    preferences(c).raise_for_status()
    first = send(c, user, "first")
    same = c.get("/api/assistant/continuity").json()
    assert [item["body"] for item in same["turns"]] == [user, api.final]
    assert same["live_id"] == first["conversation_id"]
    send(c, user, "first")
    assert len(c.get("/api/assistant/continuity").json()["turns"]) == 2

    other, model, fresh = normal_desk(tmp_path)
    recovered = fresh.get("/api/assistant/continuity").json()
    assert recovered["turns"] == same["turns"] and recovered["live_id"] is None
    model.final = "You chose the amber reading lamp."
    second = send(fresh, "Which lamp did I choose for the study?", "second")
    assert second["conversation_id"] != first["conversation_id"]
    packed = json.loads(model.creations[0]["input"][0]["content"][0]["text"])
    assert any(t["body"] == user for t in packed["turns"])
    assert first["conversation_id"] not in json.dumps(packed["turns"])
    hidden = TestClient(c.app)
    assert hidden.get("/api/assistant/continuity").status_code in (401, 403)
    preferences(fresh, share=False).raise_for_status()
    assert (
        other.home_history.provider_turns(
            {"kind": "owner", "session": fresh.cookies[COOKIE]}, "text"
        )
        == []
    )
    assert len(fresh.get("/api/assistant/continuity").json()["turns"]) == 4
    g = recovered["generation"]
    new = fresh.post(
        "/api/assistant/continuity/new", json={"generation": g}, headers={"X-Operation-Id": "new"}
    )
    new.raise_for_status()
    assert fresh.get("/api/assistant/continuity").json()["turns"] == []
    assert len(fresh.get("/api/assistant/conversations").json()["conversations"]) == 1
    assert (
        fresh.post(
            "/api/assistant/continuity/new",
            json={"generation": g},
            headers={"X-Operation-Id": "stale"},
        ).status_code
        == 409
    )


def test_retention_off_and_a_revoked_inflight_permission_leave_no_saved_exchange(tmp_path):
    r, api, c = normal_desk(tmp_path)
    actor = {"kind": "owner", "session": c.cookies[COOKIE], "id": "owner"}
    send(c, "Describe a fictional blue reading chair.", "without-consent")
    assert c.get("/api/assistant/continuity").json()["turns"] == []
    preferences(c).raise_for_status()
    stamp = r.home_history.stamp(actor)
    assert stamp is not None
    preferences(c, save=False, share=False).raise_for_status()
    from types import SimpleNamespace

    r.home_history.record(
        stamp,
        actor,
        SimpleNamespace(home_generation=None),
        "late",
        SimpleNamespace(language="en", message="a late message"),
        {"kind": "reply", "message": "late answer"},
    )
    assert c.get("/api/assistant/continuity").json()["turns"] == []


def test_live_records_only_completed_visible_captions_with_separate_consent(tmp_path):
    from desk.openai_live import OPENAI_LIVE_ENDPOINT
    from desk.voice import VoiceConfig
    from voice_fixtures import Provider, Socket

    r, _, c = normal_desk(tmp_path)
    r.voice.config = VoiceConfig(
        "openai_live",
        OPENAI_LIVE_ENDPOINT,
        "gpt-live-1.1",
        "fixture-key",
        "marin",
        backend_model="gpt-6.2-sol",
    )
    who = {"kind": "owner", "id": "owner", "session": c.cookies[COOKIE]}

    async def spoken(abort=False):
        p, sock = Provider(), Socket(lambda: None)
        r.voice.connector = lambda *a, **k: p
        provider_send = p.send

        async def output(raw):
            await provider_send(raw)
            item = json.loads(raw)
            if item["type"] == "session.start":
                await p.queue.put({"type": "session.started", "session": {"model": "gpt-live-1.1"}})
                for role, words in (
                    ("input", "Read the "),
                    ("input", "blue map."),
                    ("output", "Here is "),
                    ("output", "the blue map."),
                ):
                    await p.queue.put({"type": f"session.{role}_transcript.delta", "delta": words})
            elif item["type"] == "session.close":
                await p.queue.put({"type": "session.closed", "usage": {"seconds": 2}})

        p.send = output
        client_send = sock.send_json

        async def delivered(event):
            await client_send(event)
            if (abort and event.get("role") == "assistant") or event["type"] == "turn_complete":
                await sock.queue.put({"type": "stop"})

        sock.send_json = delivered
        await asyncio.wait_for(
            r.voice.run(sock, r.voice.consume(r.voice.ticket(who)["ticket"]), "en"), 12
        )
        assert any(item.get("role") == "assistant" for item in sock.messages)

    preferences(c).raise_for_status()
    asyncio.run(spoken())
    assert not c.get("/api/assistant/continuity").json()["turns"]
    preferences(c, voice=True).raise_for_status()
    asyncio.run(spoken(abort=True))
    assert not c.get("/api/assistant/continuity").json()["turns"]
    asyncio.run(spoken())
    assert [x["body"] for x in c.get("/api/assistant/continuity").json()["turns"]] == [
        "Read the blue map.",
        "Here is the blue map.",
    ]
    with r.store.connection() as db:
        assert {r["mode"] for r in db.execute("SELECT mode FROM conversation_messages")} == {
            "voice_transcript"
        }


def test_closed_budget_still_delivers_cited_local_mail_once_across_restart(tmp_path, monkeypatch):
    from desk import initiative_sources

    now = datetime(2026, 11, 25, 5, tzinfo=UTC)
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: now)
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        "openai", "gpt-6.2-sol", "https://api.openai.com/v1/responses", "fake-only", background=True
    )
    r.openai_spend.path = tmp_path / "budget-fixture"
    monkeypatch.setattr(r.openai_spend, "summary", lambda: {"active": False, "available_usd": 0})
    monkeypatch.setattr(
        r.text_ai, "generate", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Paid call"))
    )
    acct = {"connected": True, "version": 1, "email": "owner@example.test"}
    monkeypatch.setattr(r.outbound_mail.auth, "account", lambda: acct)

    def item(ident, title, preview):
        return {
            "id": ident,
            "thread_id": ident,
            "headers": [{"name": "Subject", "value": title}],
            "snippet": preview,
        }

    docs = [
        item("abc12", "Library pickup", "Collect the atlas before Friday."),
        item("def12", "Verification code", "Your verification code is 123456."),
    ]
    monkeypatch.setattr(
        initiative_sources, "query_connected_app", lambda *_args, **_kwargs: {"items": docs}
    )
    r.initiative.advance()
    rows = r.initiative.snapshot()["findings"]
    assert len(rows) == 1 and "atlas" in rows[0]["message_en"]
    assert rows[0]["sources"][0]["href"].endswith("#all/abc12")
    assert "123456" not in json.dumps(rows)
    r.initiative = Initiative(r)
    r.initiative.advance()
    assert len(r.initiative.snapshot()["findings"]) == 1
    with r.store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM notice_inbox WHERE id LIKE 'insight-%'").fetchone()[0]
            == 1
        )
        assert db.execute("SELECT count(*) FROM text_ai_usage").fetchone()[0] == 0
    acct.update(connected=False, version=2)
    assert r.initiative.snapshot()["findings"] == []
