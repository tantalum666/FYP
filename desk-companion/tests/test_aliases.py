"""Recall treats a built-in or owner-added pair as the same word. No model call."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage


def _owner(tmp_path):
    app = create_app(
        tmp_path,
        password="fixture-only",
        scheduler=False,
        clock=lambda: datetime(2026, 10, 3, 2, tzinfo=UTC),
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return app, client


def test_tea_matches_chinese_and_an_owner_pair_can_be_removed(tmp_path):
    app, client = _owner(tmp_path)
    runtime = app.state.runtime
    runtime.memory.create("I prefer tea", "en")
    runtime.memory.create("我更喜欢茶", "zh")
    runtime.memory.create("I prefer coffee", "coffee")
    reply = runtime.assistant.local_message(
        AssistantMessage(message="what do you remember about tea"),
        "ask-tea",
    )
    assert "I prefer tea" in reply["message"]
    assert "我更喜欢茶" in reply["message"]
    assert "coffee" not in reply["message"]
    chinese = runtime.assistant.local_message(
        AssistantMessage(message="你还记得茶吗", language="zh"),
        "ask-zh",
    )
    assert "I prefer tea" in chinese["message"] and "我更喜欢茶" in chinese["message"]

    headers = {"X-Desk-Request": "1", "X-Operation-Id": "add-grey"}
    saved = client.post(
        "/api/memory/aliases",
        json={"terms": ["Earl Grey", "伯爵茶"]},
        headers=headers,
    )
    assert saved.status_code == 200
    again = client.post(
        "/api/memory/aliases",
        json={"terms": ["Earl Grey", "伯爵茶"]},
        headers=headers,
    )
    assert again.status_code == 200
    assert again.json()["operation_id"] == saved.json()["operation_id"]
    runtime.memory.create("我喜欢伯爵茶", "grey")
    grey = runtime.assistant.local_message(
        AssistantMessage(message="what do you remember about earl grey"),
        "ask-grey",
    )
    assert "伯爵茶" in grey["message"]
    custom = next(group for group in saved.json()["groups"] if not group["builtin"])
    blocked = client.post(
        "/api/memory/aliases/builtin:tea/deletions",
        headers={"X-Desk-Request": "1", "X-Operation-Id": "drop-builtin"},
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "ALIAS_BUILTIN"
    removed = client.post(
        f"/api/memory/aliases/{custom['id']}/deletions",
        headers={"X-Desk-Request": "1", "X-Operation-Id": "drop-grey"},
    )
    assert removed.status_code == 200
    assert all(group["builtin"] for group in removed.json()["groups"])
    missed = runtime.assistant.local_message(
        AssistantMessage(message="what do you remember about earl grey"),
        "ask-grey-gone",
    )
    assert "伯爵茶" not in missed["message"]


def test_a_paired_display_cannot_edit_aliases(tmp_path):
    app, owner = _owner(tmp_path)
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Screen"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    response = display.post(
        "/api/memory/aliases",
        json={"terms": ["tea", "cha"]},
        headers={"X-Operation-Id": "display-alias"},
    )
    assert response.status_code == 403
