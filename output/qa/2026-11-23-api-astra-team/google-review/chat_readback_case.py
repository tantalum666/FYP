"""Independent FastAPI sample with different preview, confirmation and question times."""

import json
from datetime import UTC, datetime
import httpx
from fastapi.testclient import TestClient

from desk.app import COOKIE, create_app
from session_protocol_fixture import install_session_protocol
from test_google_calendar_refresh import Desk, event, provider_error


def test_owner_chat_reads_only_the_confirmed_refresh(tmp_path, monkeypatch):
    def at(minute):
        return datetime(2026, 10, 1, 3, minute, tzinfo=UTC)

    now = [at(0)]
    app = create_app(tmp_path, password="fixture-only", scheduler=False,
                     connector_configs=(), clock=lambda: now[0])
    with TestClient(app) as client:
        desk = Desk(app, client)
        model = install_session_protocol(desk.runtime)
        google_wire = []

        def transport(request):
            google_wire.append(request.method)
            return desk.provider(request)

        desk.runtime.google.transport = httpx.MockTransport(transport)
        ids = ("change", "declined", "cancel", "away")
        private = "QA-only appointment "
        desk.import_events(*(event(remote, private + remote) for remote in ids))
        desk.events.update({
            "change": event("change", private + "accepted"),
            "declined": event("declined", private + "kept by owner"),
            "cancel": {"id": "cancel", "status": "cancelled"},
            "away": provider_error(404, "notFound"),
        })
        now[0] = at(7)
        review = desk.refresh()
        selection = [row["existing_id"] for row in review["rows"]
                     if row["status"] == "deleted" or row["event"]["title"] == private + "accepted"]
        assert len(selection) == 2
        eng = "What has changed in my Google Calendar?"
        zh = "刚才我的 Google 日历更新了什么？"
        tools_called = []
        real_tool = desk.runtime.assistant.tool

        def audit(name, arguments, *args, **kwargs):
            tools_called.append((name, arguments.get("service"), arguments.get("view")))
            return real_tool(name, arguments, *args, **kwargs)

        monkeypatch.setattr(desk.runtime.assistant, "tool", audit)

        def ask(question=eng, key=None, stream=False):
            before = len(google_wire)
            path = "/assistant/messages" + ("/stream" if stream else "")
            response = desk.post(path, {"message": question}, key)
            assert len(google_wire) == before and not model.requests
            assert private not in response.text and response.is_success, response.text
            if not stream:
                return response.json()
            frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            assert [f["type"] for f in frames] == ["done"]
            return frames[0]["reply"]

        def unavailable(answer):
            assert "no confirmed" in answer["message"]
            assert "2026-10-01" not in answer["message"] and "google_refresh_scope" not in answer

        unavailable(ask())
        now[0] = at(16)
        receipt = desk.ok("/exchange/" + review["preview_id"] + "/apply", {"selected_event_ids": selection})
        assert (receipt["updated"], receipt["removed"], receipt["kept"]) == (1, 1, 2)
        now[0] = at(25)
        desk.events.update({
            "change": {"id": "change", "status": "cancelled"},
            "declined": {"id": "declined", "status": "cancelled"},
            "away": event("away", private + "visible again"),
        })
        pending = desk.refresh()
        assert sorted(row["status"] for row in pending["rows"]) == ["changed", "deleted", "deleted"]
        now[0] = at(31)
        english = ask(key="verified-read")
        chinese = ask(zh, stream=True)
        assert "2026-10-01 03:16 UTC" in english["message"]
        assert "updated 1 local copy" in english["message"] and "removed 1 and kept 2" in english["message"]
        assert "1 unavailable from Google" in english["message"]
        assert "03:16 UTC" in chinese["message"] and "更新 1 项、移除 1 项、保留 2 项" in chinese["message"]
        assert "1 项在 Google 暂不可用" in chinese["message"]
        assert ask(key="verified-read") == english

        def hide(hidden):
            with desk.store.connection() as conn:
                settings = desk.store.settings(conn)
            desk.ok("/settings", {"expected_version": settings["version"],
                                  "timezone": settings["timezone"], "hide_private": hidden})

        hide(True)
        unavailable(ask(key="verified-read"))
        hide(False)
        client.cookies.clear()
        client.cookies.set(COOKIE, desk.store.create_owner_session())
        unavailable(ask())
        client.cookies.clear()
        client.cookies.set(COOKIE, desk.session)
        assert ask()["message"] == english["message"]
        desk.connect("different-grant")
        unavailable(ask())
        desk.ok("/apps/calendar/disconnect", {"expected_version": "different-grant"})
        unavailable(ask())
        with desk.store.connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM google_refresh_result").fetchone()[0] == 0
        desk.connect("first")
        unavailable(ask())
        assert set(tools_called) == {("connected_app_query", "google_calendar", "last_refresh")}
        assert len(tools_called) >= 5 and not model.requests
        print("03:07 preview, 03:16 selective confirmation, 03:25 pending preview, 03:31 ordinary chat")
        print(english["message"])
        print(chinese["message"])
