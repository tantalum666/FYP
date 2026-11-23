"""A scoped booking can become one private desk event after a separate owner review."""

import json
from datetime import timedelta

from fastapi.testclient import TestClient

from test_conversation_flight_booking import desk as desk, login, send, status


def ticketed(client):
    reply = send(client, "calendar-test-quote", "帮我订 HKG 去 HND 的测试航班").json()
    chat, original = reply["conversation_id"], reply["flight_booking"]
    send(client, "calendar-test-order", "确认", chat, original).raise_for_status()
    revised = status(client, chat)[0]
    send(client, "calendar-test-new-total", "确认新总价 HK$35.43", chat, revised).raise_for_status()
    ticket = status(client, chat)[0]
    assert ticket["state"] == "completed" and ticket["charged_minor"] == 3543
    return chat, ticket


def calendar_turn(client, chat, key, message, card=None):
    body = {"message": message, "conversation_id": chat, "language": "zh"}
    if card:
        body.update(
            selected_commerce_card=True,
            flight_review={
                "id": card["id"],
                "version": card["version"],
                "amount_minor": card["review_minor"],
            },
        )
    return client.post(
        "/api/assistant/messages", json=body, headers={"X-Desk-Request": "1", "X-Operation-Id": key}
    )


def stored_events(runtime):
    with runtime.store.connection() as db:
        return [
            (r[0], json.loads(r[1]))
            for r in db.execute("SELECT id,data FROM events WHERE deleted=0")
        ]


def test_normal_chat_preview_save_and_read_back_without_paying_again(desk):
    runtime, client, provider = desk
    chat, ticket = ticketed(client)
    writes = [c for c in provider.calls if c[0] != "GET"]
    prior = len(stored_events(runtime))
    preview = calendar_turn(
        client, chat, "cal-preview", "把这趟已经订好的测试航班加到我的桌面日历"
    ).json()
    review = preview["flight_booking"]
    event = review["calendar_preview"]
    assert event["start_local"][11:16] == "19:00" and event["end_local"][11:16] == "21:10"
    assert event["timezone"] == "Asia/Hong_Kong" and event["visibility"] == "private"
    assert ticket["pnr"] not in str(event) and len(stored_events(runtime)) == prior
    other = TestClient(client.app)
    login(other)
    assert calendar_turn(other, chat, "foreign-calendar", "确认加入日历", review).status_code in {
        403,
        404,
    }
    assert len(stored_events(runtime)) == prior
    saved = calendar_turn(client, chat, "cal-save", "确认加入日历", review)
    saved.raise_for_status()
    assert saved.json()["flight_booking"]["calendar_linked"] and "查到" in saved.json()["message"]
    created = stored_events(runtime)
    assert len(created) == prior + 1
    ident, actual = next((i, e) for i, e in created if e["title"] == event["title"])
    assert actual["end_local"] == event["end_local"] and actual["reminder_minutes"] == []
    assert ticket["pnr"] not in str(actual)
    assert calendar_turn(client, chat, "cal-save", "确认加入日历", review).is_success
    assert calendar_turn(client, chat, "different-key", "确认加入日历", review).is_success
    assert len(stored_events(runtime)) == prior + 1
    with runtime.store.connection(write=True) as db:
        db.execute("UPDATE events SET deleted=1 WHERE id=?", (ident,))
    again = calendar_turn(client, chat, "cal-save", "确认加入日历", review)
    assert "已移除" in again.json()["message"]
    assert len(stored_events(runtime)) == prior
    assert [c for c in provider.calls if c[0] != "GET"] == writes


def test_expired_or_dismissed_review_requires_preview_again(desk, monkeypatch):
    runtime, client, _ = desk
    chat, _ = ticketed(client)
    old = calendar_turn(client, chat, "preview", "把这趟航班加入我的桌面日历").json()[
        "flight_booking"
    ]
    clock = runtime.store.clock
    monkeypatch.setattr(runtime.store, "clock", lambda: clock() + timedelta(minutes=6))
    revised = calendar_turn(client, chat, "stale", "确认加入日历", old).json()["flight_booking"]
    assert revised["version"] > old["version"] and "calendar_linked" not in revised
    assert calendar_turn(client, chat, "wrong", "确认加入日历", old).status_code == 409
    skipped = calendar_turn(client, chat, "skip", "暂不加入日历", revised).json()["flight_booking"]
    assert "calendar_preview" not in skipped and "calendar_linked" not in skipped
    assert calendar_turn(client, chat, "after-skip", "确认加入日历", revised).status_code == 409
    assert not any(e["title"].startswith("Test itinerary") for _, e in stored_events(runtime))


def test_changed_provider_receipt_cannot_save(desk):
    runtime, client, provider = desk
    chat, _ = ticketed(client)
    card = calendar_turn(client, chat, "preview", "Add this flight to my desk calendar").json()[
        "flight_booking"
    ]
    provider.total += 1
    result = calendar_turn(client, chat, "changed", "确认加入日历", card).json()
    assert result["kind"] == "clarify" and not result["saved"]
    assert not any(e["title"].startswith("Test itinerary") for _, e in stored_events(runtime))


def test_privacy_switch_during_provider_read_suppresses_calendar_write(desk, monkeypatch):
    runtime, client, provider = desk
    chat, _ = ticketed(client)
    review = calendar_turn(client, chat, "draft-to-hide", "把这趟航班加入我的桌面日历").json()[
        "flight_booking"
    ]
    original = runtime.flight_bookings.provider.status

    def read_then_hide(ident):
        result = original(ident)
        with runtime.store.connection(write=True) as db:
            db.execute(
                "UPDATE settings SET data=json_set(data,'$.hide_private',json('true')) WHERE id=1"
            )
        return result

    monkeypatch.setattr(runtime.flight_bookings.provider, "status", read_then_hide)
    response = calendar_turn(client, chat, "private-during-read", "确认加入日历", review)
    assert response.status_code == 403
    assert "PRIVATE_CONTEXT_HIDDEN" in response.text
    assert not any(e["title"].startswith("Test itinerary") for _, e in stored_events(runtime))
    assert len([c for c in provider.calls if c[1] == "book"]) == 1


def test_calendar_intent_survives_service_restart_but_not_forgotten_chat(desk):
    runtime, client, _ = desk
    chat, _ = ticketed(client)
    review = calendar_turn(client, chat, "draft-to-reopen", "把这趟航班加入我的桌面日历").json()[
        "flight_booking"
    ]
    runtime.voice.conversations.entries.clear()
    resumed = calendar_turn(client, chat, "after-restart", "确认加入日历", review)
    assert resumed.is_success and resumed.json()["flight_booking"]["calendar_linked"]
    assert client.delete(
        "/api/voice/conversations/" + chat, headers={"X-Desk-Request": "1"}
    ).is_success
    denied = calendar_turn(client, chat, "after-forget", "查看航班日程", review)
    assert denied.status_code == 404
