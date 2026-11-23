"""Owner chat reads the applied Google import receipt through the existing app tool."""

import asyncio
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest
import uvicorn
from uvicorn.protocols.http.h11_impl import H11Protocol
from uvicorn.server import ServerState

from desk.app import COOKIE
from desk.capabilities import parse_call
from desk.store import DomainError, encode
from session_protocol_fixture import install_session_protocol
from test_google_calendar_refresh import desk as desk, event, provider_error

CHAT = "/assistant/messages"
EN = "What changed in my Google Calendar just now?"
ZH = "刚才我的 Google 日历更新了什么？"
TIME = "2026-10-01 00:00 UTC"
QUERY = {"service": "google_calendar", "view": "last_refresh"}


def mixed_review(desk):
    desk.import_events(*(event(k, "Private title " + k) for k in ("move", "cancel", "lost", "bad")))
    desk.events.update(
        move=event("move", "Private revised title"),
        cancel={"id": "cancel", "status": "cancelled"},
        lost=provider_error(404, "notFound"),
        bad=event("bad", transparency="unknown"),
    )
    return desk.refresh()


def ask(desk, question=EN, key=None, **context):
    return desk.ok(CHAT, {"message": question, **context}, key)


def assert_unavailable(reply):
    assert reply["message"] == "There’s no confirmed Google Calendar refresh available in this session."
    assert not reply["saved"] and "google_refresh_scope" not in reply


def privacy(desk, hidden):
    with desk.store.connection() as conn:
        settings = desk.store.settings(conn)
    desk.ok("/settings", {
        "expected_version": settings["version"], "timezone": settings["timezone"], "hide_private": hidden,
    })


def test_confirmed_counts_are_local_bilingual_and_survive_discard_and_retry(desk):
    model = install_session_protocol(desk.runtime)
    review = mixed_review(desk)
    calls = list(desk.calls)
    assert_unavailable(ask(desk, key="preview-only"))
    applied = desk.apply(review, "confirm")
    assert desk.apply(review, "confirm") == applied
    assert set(desk.calendar()) == {"Private revised title", "Private title lost", "Private title bad"}
    assert desk.status()["unresolved"] == 2 and desk.status()["unavailable"] == 1
    assert_unavailable(ask(desk, key="preview-only"))

    english = ask(desk, key="replay")
    chinese = ask(desk, ZH, conversation_id=english["conversation_id"])
    assert english["message"] == (
        f"Your last confirmed Google Calendar refresh ({TIME}) updated 1 local copy, "
        "removed 1 and kept 2 (1 unavailable from Google, 1 otherwise unresolved)."
    )
    assert chinese["message"] == (
        f"Google 日历副本上次于 {TIME} 确认刷新，更新 1 项、移除 1 项、保留 2 项"
        "（其中 1 项在 Google 暂不可用，另有 1 项未能核实）。"
    )
    assert not english["saved"] and "Private" not in encode([english, chinese])
    assert ask(desk, key="replay") == english and desk.calls == calls
    with desk.store.connection() as conn:
        cached = [json.loads(r[0]) for r in conn.execute("SELECT result FROM assistant_replies")]
    assert all(set(row) == {"mode", "kind", "saved", "refresh_ref", "conversation_id"} for row in cached)
    assert not desk.runtime.voice.conversations.entries[english["conversation_id"]].items
    assert model.requests == []

    desk.events["lost"] = {"id": "lost", "status": "cancelled"}
    newer = desk.refresh()
    calls = list(desk.calls)
    assert ask(desk)["message"] == english["message"]
    discard = f"/google/{newer['preview_id']}/discard"
    assert desk.ok(discard, {}, "discard") == desk.ok(discard, {}, "discard")
    assert ask(desk, key="replay") == english and desk.calls == calls and not model.requests


def test_workspace_login_grant_and_forgotten_connection_boundaries(desk):
    desk.apply(mixed_review(desk))
    answer = ask(desk, key="owner-read")
    first = desk.client.get("/api/workspace").json()
    assert first["google"]["review_version"] == answer["google_refresh_scope"]["review_version"]
    assert not {"last_refresh", "last_refresh_ref", "version", "email"} & first["google"].keys()
    assert desk.session not in encode(first)
    desk.client.cookies.clear()
    desk.client.cookies.set(COOKIE, desk.store.create_owner_session())
    assert desk.status() is None
    assert_unavailable(ask(desk))
    old = desk.post(CHAT, {"message": EN}, "owner-read")
    assert old.status_code == 404 and old.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"

    desk.client.cookies.clear()
    device = desk.runtime.access.enrol_display("Synthetic display", "pair-display")
    desk.client.headers["Authorization"] = "Bearer " + device["token"]
    assert_unavailable(ask(desk))
    assert "review_version" not in desk.client.get("/api/workspace").json()["google"]
    assert desk.client.get("/api/google/status").status_code == 403
    del desk.client.headers["Authorization"]
    desk.client.cookies.set(COOKIE, desk.session)
    privacy(desk, True)
    assert desk.status() is None
    assert_unavailable(ask(desk))
    assert_unavailable(ask(desk, key="owner-read"))
    privacy(desk, False)
    assert_unavailable(ask(desk, key="owner-read"))
    assert ask(desk)["message"] == answer["message"]

    desk.connect("replacement")
    current = desk.client.get("/api/workspace").json()["google"]
    assert current["connected_at"] == first["google"]["connected_at"]
    assert current["review_version"] != first["google"]["review_version"]
    assert_unavailable(ask(desk))
    desk.apply(desk.refresh())
    assert TIME in ask(desk, key="replacement-read")["message"]
    desk.ok("/apps/calendar/disconnect", {"expected_version": "replacement"})
    assert_unavailable(ask(desk))
    with desk.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM google_refresh_result").fetchone()[0] == 0
    desk.connect("replacement")  # Even restoring the identical synthetic grant cannot restore a receipt.
    assert_unavailable(ask(desk, key="replacement-read"))
    assert_unavailable(ask(desk))


@pytest.mark.parametrize("change", ["hidden", "signout", "new_confirmation", "forget_chat"])
def test_response_in_flight_loses_authority_or_is_superseded(desk, monkeypatch, change):
    original = desk.refresh()
    desk.apply(original)
    chat = ask(desk)["conversation_id"]
    next_review = desk.refresh()  # Identical counts, range, grant and clock.
    read, release = Event(), Event()
    original_tool = desk.runtime.assistant.tool

    def pause_after_read(*args, **kwargs):
        value = original_tool(*args, **kwargs)
        assert value["last_refresh"]
        read.set()
        assert release.wait(10)
        return value

    monkeypatch.setattr(desk.runtime.assistant, "tool", pause_after_read)
    body = {"message": EN, "conversation_id": chat}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(desk.post, CHAT, body, "in-flight")
        try:
            assert read.wait(10)
            if change == "hidden":
                privacy(desk, True)
            elif change == "signout":
                desk.store.logout(desk.session)
            elif change == "new_confirmation":
                desk.apply(next_review)
            else:
                assert desk.client.delete(f"/api/voice/conversations/{chat}").is_success
        finally:
            release.set()
        result = pending.result(timeout=10)
    assert TIME not in result.text
    if change in {"hidden", "new_confirmation"}:
        assert_unavailable(result.json())
        if change == "hidden":
            privacy(desk, False)
        assert_unavailable(desk.ok(CHAT, body, "in-flight"))
        assert TIME in ask(desk)["message"]
    else:
        assert result.status_code == (403 if change == "signout" else 404)
        assert not desk.post(CHAT, body, "in-flight").is_success


def test_simultaneous_new_chat_retries_reuse_the_same_scoped_refresh_receipt(desk, monkeypatch):
    desk.apply(desk.refresh())
    paired = Barrier(2)
    original_tool = desk.runtime.assistant.tool

    def read_together(*args, **kwargs):
        result = original_tool(*args, **kwargs)
        paired.wait(timeout=5)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(desk.runtime.assistant, "tool", read_together)
        responses = list(pool.map(lambda _: ask(desk, key="same-fresh-read"), range(2)))
    assert TIME in responses[0]["message"]
    assert responses[0] == responses[1] == ask(desk, key="same-fresh-read")


def test_legacy_summary_requires_the_latest_successful_approval(desk):
    first = desk.session
    desk.apply(desk.refresh(), "first-apply")
    second = desk.store.create_owner_session()
    desk.client.cookies.set(COOKIE, second)
    desk.apply(desk.refresh(), "latest-apply")
    with desk.store.connection(write=True) as conn:
        summary = json.loads(conn.execute("SELECT summary FROM google_refresh_result").fetchone()[0])
        for field in ("confirmed_session", "unavailable", "confirmation_id"):
            del summary[field]
        conn.execute("UPDATE google_refresh_result SET summary=?", (encode(summary),))
        conn.execute("DELETE FROM import_previews")
    assert "unavailable copies weren’t counted separately" in ask(desk)["message"]
    desk.client.cookies.set(COOKIE, first)
    assert_unavailable(ask(desk))
    # The earlier approval has identical counts and time but belongs to another login.
    with desk.store.connection(write=True) as conn:
        conn.execute("DELETE FROM operations WHERE id='latest-apply'")
    assert_unavailable(ask(desk))
    desk.client.cookies.set(COOKIE, second)
    assert_unavailable(ask(desk))


def test_existing_function_returns_only_local_receipt_to_owner(desk):
    desk.apply(mixed_review(desk))
    calls = list(desk.calls)
    model = install_session_protocol(desk.runtime)
    model.next_calls = [("connected_app_query", QUERY)]
    model.lose_result_once = True
    answer = ask(desk, "Please consult the linked app’s saved receipt.", key="functions")
    assert TIME in answer["message"] and "1 unavailable from Google" in answer["message"]
    tools = [tool for tool in model.creations[0]["agent"]["tools"] if tool["name"] == "connected_app_query"]
    assert len(tools) == 1 and "last_refresh" in encode(tools[0]["parameters"])
    assert len(model.functions) == 2 and model.functions[0] == model.functions[1]
    output = json.loads(model.functions[0][0][0]["output"])
    assert output == {"kind": "google_calendar_refresh", "saved": False}
    assert ask(desk, "Please consult the linked app’s saved receipt.", key="functions") == answer
    assert desk.calls == calls and len(model.creations) == 1 and len(model.functions) == 2
    for invalid in ({**QUERY, "service": "gmail"}, {**QUERY, "principal": {"kind": "owner"}},
                    {**QUERY, "start": "2026-10-01T00:00:00Z"}, {"service": "google_calendar"}):
        with pytest.raises(DomainError):
            parse_call("connected_app_query", invalid)
    _, query = parse_call("connected_app_query", {
        "service": "google_calendar", "start": "2026-10-01T00:00:00Z", "end": "2026-10-02T00:00:00Z",
    })
    assert query.get("view", "items") == "items"


def test_ordinary_composer_over_local_http(desk):
    desk.apply(mixed_review(desk))
    model = install_session_protocol(desk.runtime)
    provider_reads = list(desk.calls)

    async def run():
        # Serve real HTTP/1.1 over an inherited local socket, including the streamed chat route.
        config = uvicorn.Config(desk.app, ws="none", log_config=None, access_log=False)
        server, client = socket.socketpair()
        with client:
            transport, _ = await asyncio.get_running_loop().connect_accepted_socket(
                lambda: H11Protocol(config, ServerState(), {}), server
            )
            try:
                proc = await asyncio.create_subprocess_exec(
                    "node", "--experimental-transform-types", "--import",
                    "../tests/fixtures/register_ts_loader.mjs",
                    "tests/fixtures/google-refresh-composer.mjs", str(client.fileno()),
                    cwd=Path(__file__).resolve().parents[1] / "frontend",
                    pass_fds=(client.fileno(),),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(f"{COOKIE}={desk.session}".encode()), timeout=30
                    )
                finally:
                    if proc.returncode is None:
                        proc.kill()
                        await proc.wait()
                assert proc.returncode == 0, stderr.decode()
                assert stdout.strip() == b"ok"
            finally:
                transport.close()

    asyncio.run(run())
    assert not model.requests and desk.calls == provider_reads
