"""Quiet outcomes from real local writers through the owner's ordinary conversation."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.commerce_chat import follow_orders
from desk.flight_booking.provider import FlightQuery, LetsFG
from desk.notify import Notice
from desk.stream_contract import parse_sse
from session_protocol_fixture import install_session_protocol
from test_conversation_flight_booking import Sandbox
from test_conversation_shop_checkout import Shop, quote


ASK = "What changed while I was away?"
ASK_ZH = "刚才静音时有什么进展？"
ACK = "Mark these updates as read"
COOKIE = "desk_companion_session"
ZONE = "America/New_York"
# New York, Nov 22 23:49. The quiet window crosses midnight, 23:50–00:10.
START = datetime(2026, 11, 23, 4, 49, tzinfo=UTC)


def client_for(app, token=None):
    client = TestClient(app)
    client.cookies.set(COOKIE, token or app.state.store.create_owner_session())
    return client


def post(client, path, body, key=None):
    return client.post(
        "/api/" + path,
        json=body,
        headers={"X-Desk-Request": "1", "X-Operation-Id": key or uuid4().hex},
    )


def message(client, text, chat=None, *, key=None, stream=False, **fields):
    body = {"message": text, "conversation_id": chat, **fields}
    response = post(client, "assistant/messages" + ("/stream" if stream else ""), body, key)
    assert response.is_success, response.text
    if not stream:
        return response.json()
    events = parse_sse(response.text)
    assert events[-1]["type"] == "done", events
    reply = events[-1]["reply"]
    assert all(event["type"] == "delta" for event in events[:-1])
    assert "".join(event["text"] for event in events[:-1]) == reply["message"]
    return reply


def settings(desk, hidden):
    with desk.runtime.store.connection() as db:
        version = desk.runtime.store.settings(db)["version"]
    post(desk.client, "settings", {
        "expected_version": version, "timezone": ZONE, "hide_private": hidden,
    }).raise_for_status()


def preferences(desk, proactivity):
    post(desk.client, "workspace/preferences", {
        "expected_version": desk.runtime.data.preferences()["version"],
        "preferences": {"quiet_start": "23:50", "quiet_end": "00:10", "proactivity": proactivity},
    }).raise_for_status()


class RefundShop(Shop):
    def cancel(self, ref, receipt):
        self.orders[ref].update(buyer_cancel_requested=True, refund_status="pending")

    def settle(self, ref):
        self.orders[ref].update(
            order_status="refunded", refund_status="succeeded", refunded_minor=4200, net_minor=0
        )


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_WEB_PUSH", "0")
    monkeypatch.setenv("DESK_WOO_SANDBOX_CONFIG", "/synthetic-unused")
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    clock = [START]

    def boot():
        return create_app(
            tmp_path, password="fixture", clock=lambda: clock[0], scheduler=False, connector_configs=()
        )

    app = boot()
    runtime = app.state.runtime
    shop = RefundShop()
    flight = Sandbox("2026-11-30")
    runtime.shop_orders.provider = shop
    runtime.flight_bookings.provider = LetsFG(httpx.MockTransport(flight))
    d = SimpleNamespace(
        runtime=runtime, client=client_for(app), clock=clock, boot=boot, shop=shop, flight=flight,
        protocol=install_session_protocol(runtime),
    )
    settings(d, hidden=False)
    preferences(d, "low")
    return d


def open_chat(d, client=None, task=None):
    client = client or d.client
    reply = message(client, "What should I do next?", task_id=task)
    assert reply["kind"] == "next_step"
    return d.runtime.voice.conversations.entries[reply["conversation_id"]]


def review(card):
    return {"id": card["id"], "version": card["version"], "amount_minor": card["review_minor"]}


def pay(d, chat, client=None):
    client = client or d.client
    who = {"kind": "owner", "session": client.cookies[COOKIE]}
    card = d.runtime.shop_orders.attach(quote(), uuid4().hex, who, chat)
    return message(
        client, "确认支付", chat.id, task_id=chat.task_id, shopping_review=review(card),
    )["shopping_order"]


def book(d, chat):
    service = d.runtime.flight_bookings
    requested = FlightQuery(
        origin="HKG", destination="HND", departure=d.flight.day,
        flight_number="FR4315", rehearse_price_change=True,
    )
    fare = service.prepare(requested)["sandbox_quote"]
    who = {"kind": "owner", "session": d.client.cookies[COOKIE]}
    card = service.attach(fare, uuid4().hex, who, chat)
    return message(d.client, "确认", chat.id, flight_review=review(card))["flight_booking"]


def new_task(d, title):
    response = post(d.client, "tasks", {"title": title})
    response.raise_for_status()
    return response.json()["task"]["id"]


def advance_work(d, task, *, wait_for_review=False):
    scope = d.client.get("/api/agent-runs/scope").json()
    response = post(d.client, "agent-runs", {
        "scope_revision": scope["scope_revision"], "retain": True,
        "goal": "Prepare a private fixture report for buyer@example.invalid", "task_ids": [task],
        "mutation_requests": [{"tool": "task_create_draft", "arguments": {"title": "private draft"}}]
        if wait_for_review else [],
    })
    response.raise_for_status()
    run = response.json()["run"]
    for _ in range(12):
        assert d.runtime.agent_runs.advance_one()
        run = d.client.get("/api/agent-runs/" + run["id"]).json()["run"]
        if run["state"] in {"succeeded", "waiting_review"}:
            break
    assert run["state"] == ("waiting_review" if wait_for_review else "succeeded")
    assert run["model_calls"] == 0
    return run


def inbox(d):
    with d.runtime.store.connection() as db:
        return [
            (json.loads(row["content"]), row["state"])
            for row in db.execute("SELECT content,state FROM notice_inbox WHERE source IS NOT NULL")
        ]


def test_streamed_order_flight_and_work_recap_acknowledges_only_the_displayed_changes(desk):
    d = desk
    chat = open_chat(d)
    order = pay(d, chat)
    d.shop.orders[order["id"]]["can_cancel"] = True
    pending = message(d.client, "取消这笔购物订单并全额退款", chat.id, shopping_review=review(order))
    assert pending["shopping_order"]["state"] == "refund_pending"
    fare = book(d, chat)
    assert fare["state"] == "processing"
    note = message(d.client, "退款到了告诉我", chat.id)
    assert note["commerce_note"] and inbox(d) == []

    d.clock[0] += timedelta(minutes=1)
    d.shop.settle(order["id"])
    follow_orders(d.runtime)
    task = new_task(d, "Private client name at 17 Example Street")
    advance_work(d, task)
    d.clock[0] += timedelta(minutes=11)
    follow_orders(d.runtime)
    cards = d.client.get("/api/assistant/commerce-reviews", params={"conversation_id": chat.id}).json()["rows"]
    changed, refunded = cards
    assert refunded["state"] == "refunded" and refunded["receipt"]["net_minor"] == 0
    assert changed["state"] == "reprice" and changed["review_minor"] == 3543
    assert changed["approved_minor"] == 3400 and all(card["quiet_update"] for card in cards)
    assert d.client.get("/api/notices").json() == {"notices": []}
    with d.runtime.store.connection() as db:
        for table in ("notice_deliveries", "device_notices", "browser_notices"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    before = (d.shop.checks, d.shop.submissions, len(d.flight.calls))
    zh = message(d.client, ASK_ZH, chat.id, stream=True, flight_review=review(changed))
    en = message(d.client, ASK, chat.id, key="read", stream=True)
    assert all(s in zh["message"] for s in ("退款已核实", "机票报价有变", "工作已完成"))
    assert all(s in en["message"] for s in ("refund was verified", "fare changed", "work run finished"))
    assert set(zh) == set(en) == {"kind", "mode", "message", "saved", "conversation_id", "catch_up_ref"}
    assert en["kind"] == "quiet_catch_up" and not en["saved"]
    assert not any(s in json.dumps(en) for s in ("buyer@", "Example Street", "FR4315", "3543", "4242", task))
    assert message(d.client, ASK, chat.id, key="read", stream=True) == en
    assert {p["change"] for p, state in inbox(d) if state == "open"} == {
        "shop.refunded", "flight.reprice", "work.succeeded",
    }
    bare = message(d.client, ACK, chat.id, flight_review=review(changed))
    assert bare["acknowledged"] == 0 and not bare["saved"]
    assert before == (d.shop.checks, d.shop.submissions, len(d.flight.calls))

    # The supplier changes its outstanding round between the read and the owner's click.
    status = d.runtime.flight_bookings.provider.status

    def second_round(ident):
        result = status(ident)
        result["question"]["round"] = 2
        result["question"]["price_change"]["new_total"] = 37
        return result

    d.runtime.flight_bookings.provider.status = second_round
    d.clock[0] += timedelta(seconds=21)
    follow_orders(d.runtime)
    before = (d.shop.checks, d.shop.submissions, len(d.flight.calls))
    ack = message(d.client, ACK, chat.id, key="ack", stream=True, catch_up_ref=en["catch_up_ref"])
    assert ack["saved"] and ack["acknowledged"] == 2
    assert inbox(d).count(({"change": "flight.reprice"}, "open")) == 1
    assert sum(state == "dismissed" for _, state in inbox(d)) == 2
    latest = message(d.client, ASK, chat.id)
    assert latest["message"] == "A fare changed and needs your review."
    assert before == (d.shop.checks, d.shop.submissions, len(d.flight.calls))
    saved = d.runtime.flight_bookings._get(fare["id"], chat.owner, chat.id)
    assert saved["approved"] == 3400 and saved["question"]["new"] == 3700
    assert saved["state"] == "reprice" and d.flight.answer is None and not d.protocol.requests


def test_partial_refund_during_quiet_hours_remains_distinct_from_full_refund(desk):
    chat = open_chat(desk)
    order = pay(desk, chat)
    receipt = desk.shop.orders[order["id"]]
    receipt["can_cancel"] = True
    message(desk.client, "取消这笔购物订单并全额退款", chat.id, shopping_review=review(order))
    desk.clock[0] += timedelta(minutes=2)
    receipt.update(refund_status="partial", refunded_minor=700, net_minor=3500)
    follow_orders(desk.runtime)

    reads = desk.shop.checks
    recap = message(desk.client, ASK, chat.id, stream=True)
    assert recap["message"] == "A partial shopping refund was verified."
    assert inbox(desk) == [({"change": "shop.partially_refunded"}, "open")]
    assert desk.shop.checks == reads and desk.shop.submissions == 1


def test_pages_are_retryable_after_restart_and_concurrent_ack_uses_one_snapshot(desk):
    d = desk
    chat = open_chat(d)
    d.clock[0] += timedelta(minutes=1)
    for _ in range(4):
        pay(d, chat)
    page = message(d.client, ASK, chat.id, key="page")
    assert "3 ×" in page["message"] and "More updates are unread" in page["message"]
    token = d.client.cookies[COOKIE]
    second_app = d.boot()
    protocol = install_session_protocol(second_app.state.runtime)
    restarted = client_for(second_app, token)
    assert message(restarted, ASK, chat.id, key="page") == page
    clients = [d.client, restarted]
    with ThreadPoolExecutor(2) as pool:
        acks = list(pool.map(
            lambda client: message(client, ACK, chat.id, catch_up_ref=page["catch_up_ref"]),
            clients,
        ))
    assert sorted(r["acknowledged"] for r in acks) == [0, 3]
    original = message(restarted, ASK, chat.id, key="page")
    assert "catch_up_ref" not in original and "other updates" in original["message"]
    last = message(restarted, ASK, chat.id)
    result = message(d.client, ACK, chat.id, key="last", catch_up_ref=last["catch_up_ref"])
    assert result["acknowledged"] == 1
    assert message(restarted, ACK, chat.id, key="last", catch_up_ref=last["catch_up_ref"]) == result
    assert message(restarted, ASK, chat.id)["message"] == "There are no unread updates from quiet hours."
    assert not d.protocol.requests and not protocol.requests


def test_original_login_chat_task_visibility_and_clear_guard_reads_and_retries(desk):
    d = desk
    task = new_task(d, "Private scope")
    elsewhere = new_task(d, "Separate scope")
    chat = open_chat(d, task=task)
    other = client_for(d.client.app)
    other_chat = open_chat(d, other, task)
    d.clock[0] += timedelta(minutes=2)
    pay(d, chat)
    advance_work(d, task)
    scoped = message(d.client, ASK, chat.id, key="scoped", task_id=task)
    assert "payment" in scoped["message"] and "work run" in scoped["message"]
    assert "catch_up_ref" not in message(other, ASK, other_chat.id, task_id=task)
    assert "catch_up_ref" not in message(d.client, ASK, task_id=elsewhere)
    # Work has task/login scope. Commerce additionally requires the original chat.
    fresh = message(d.client, ASK, task_id=task)
    assert fresh["message"] == "A work run finished."
    ack = {"message": ACK, "conversation_id": chat.id, "task_id": task, "catch_up_ref": scoped["catch_up_ref"]}
    for client, body in ((other, ack), (d.client, ack | {"conversation_id": fresh["conversation_id"]})):
        assert post(client, "assistant/messages", body).status_code == 404
    assert post(d.client, "assistant/messages", ack | {"message": "确认支付"}).status_code == 422
    settings(d, hidden=True)
    assert post(d.client, "assistant/messages", ack).status_code == 403
    assert post(d.client, "assistant/messages", {
        "message": ASK, "conversation_id": chat.id, "task_id": task,
    }, "scoped").status_code == 403
    settings(d, hidden=False)
    assert all(state == "open" for _, state in inbox(d))
    d.client.delete("/api/voice/conversations/" + chat.id, headers={"X-Desk-Request": "1"}).raise_for_status()
    restarted = client_for(d.boot(), d.client.cookies[COOKIE])
    assert post(restarted, "assistant/messages", ack).status_code == 404
    assert post(restarted, "assistant/messages", {
        "message": ASK, "conversation_id": chat.id, "task_id": task,
    }, "scoped").status_code == 404
    assert message(restarted, ASK, task_id=task)["message"] == "A work run finished."
    assert inbox(d) == [({"change": "work.succeeded"}, "open")]
    d.runtime.store.logout(restarted.cookies[COOKIE])
    assert post(restarted, "assistant/messages", {"message": ASK}).status_code == 401
    assert not d.protocol.requests


def test_clock_boundaries_cancellation_configuration_and_routine_are_not_progress(desk):
    d = desk
    chat = open_chat(d)
    pay(d, chat)  # Before the quiet window.
    post(d.client, "routines", {
        "title": "Private fixture routine", "frequency": "daily", "skill": "day_briefing",
        "start_local": "2026-11-22T23:50", "timezone": ZONE,
    }).raise_for_status()
    d.runtime.notify.publish(Notice("ordinary", "test", *["private fixture reminder"] * 6), quiet=False)
    d.clock[0] += timedelta(minutes=1)
    d.runtime.routines.tick()
    task = new_task(d, "Private review")
    run = advance_work(d, task, wait_for_review=True)
    pending = message(d.client, ASK, chat.id)
    assert pending["message"] == "A work run is ready for your review."
    post(d.client, "agent-runs/" + run["id"] + "/actions", {
        "action": "cancel", "expected_version": run["version"],
    }).raise_for_status()
    assert message(d.client, ACK, chat.id, catch_up_ref=pending["catch_up_ref"])["acknowledged"] == 0
    preferences(d, "off")
    pay(d, chat)
    preferences(d, "normal")
    assert "catch_up_ref" not in message(d.client, ASK, chat.id)
    d.clock[0] = START + timedelta(minutes=20, seconds=59)  # 00:09:59
    paid = pay(d, chat)
    assert paid["quiet_update"]
    d.clock[0] += timedelta(seconds=1)  # 00:10:00, end exclusive
    assert "quiet_update" not in pay(d, chat)
    assert message(d.client, ASK_ZH, chat.id)["message"] == "一笔购物付款已核实。"
    assert inbox(d) == [({"change": "shop.completed"}, "open")]
    assert [n["id"] for n in d.client.get("/api/notices").json()["notices"]] == ["ordinary"]
    assert not d.protocol.requests


def test_legacy_inbox_and_existing_terminal_order_are_not_backfilled(desk):
    d = desk
    chat = open_chat(d)
    paid = pay(d, chat)
    notice = Notice("legacy", "test", *["existing reminder"] * 6)
    with d.runtime.store.connection(write=True) as db:
        db.execute("DROP TABLE notice_inbox")
        db.execute("CREATE TABLE notice_inbox(id TEXT PRIMARY KEY,created_at TEXT,state TEXT,content TEXT)")
        db.execute("INSERT INTO notice_inbox VALUES(?,?,'open',?)", ("legacy", START.isoformat(), json.dumps(notice.payload())))
        db.execute("UPDATE sandbox_shop_orders SET data=json_remove(data,'$.task_id') WHERE id=?", (paid["id"],))
    d.clock[0] += timedelta(minutes=2)
    app = d.boot()
    app.state.runtime.shop_orders.enabled = False
    client = client_for(app, d.client.cookies[COOKIE])
    assert client.get("/api/notices").json()["notices"] == [dict(notice.payload(), state="open")]
    assert message(client, ASK, chat.id)["message"] == "There are no unread updates from quiet hours."
    assert inbox(d) == []
