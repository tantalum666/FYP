"""Autonomous checks read existing records only while the original login is permitted."""

from types import SimpleNamespace
from datetime import timedelta

import pytest

from desk.app import create_app
from desk.calendar import iso
from desk.commerce_chat import follow_orders
from desk.conversation import Conversations
from test_conversation_shop_checkout import quote


@pytest.fixture
def active(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_WOO_SANDBOX_CONFIG", "/test-only")
    monkeypatch.setenv("DESK_LETSFG_SANDBOX_ENABLED", "1")
    runtime = create_app(tmp_path, password="test", scheduler=False).state.runtime
    who = {"kind": "owner", "session": runtime.store.create_owner_session()}
    chat = SimpleNamespace(id="test-chat", task_id=None, owner=Conversations.owner(who))
    shop = runtime.shop_orders
    view = shop.attach(quote(800), "synthetic-order", who, chat)
    row = shop._get(view["id"], chat.owner, chat.id)
    previous = {"order": 21, "charged_minor": 4200, "order_status": "processing", "test_mode": True}
    row.update(
        approved=4200,
        state="refund_pending",
        receipt=previous,
        next_read=0,
        cancel_requested_at=runtime.store.clock().timestamp(),
    )
    shop._save(row)
    read = []

    def refund(ref, terms):
        read.append(ref)
        return {
            **previous,
            "order_status": "refunded",
            "refund_status": "succeeded",
            "refunded_minor": 4200,
            "net_minor": 0,
            "buyer_cancel_requested": True,
        }

    shop.provider = SimpleNamespace(receipt=refund)
    return runtime, who, chat, row, read


def test_desk_finishes_an_existing_refund_without_a_client_or_second_write(active):
    runtime, _, chat, row, reads = active
    follow_orders(runtime)
    follow_orders(runtime)
    result = runtime.shop_orders._get(row["id"], chat.owner, chat.id)
    assert (
        reads == [row["id"]]
        and result["state"] == "refunded"
        and result["receipt"]["net_minor"] == 0
    )
    assert "_follow" not in result


@pytest.mark.parametrize(
    "gate", ["logout", "expiry", "forgotten", "private", "off", "unapproved", "not_due"]
)
def test_watch_respects_original_authority_and_due_time(active, gate):
    runtime, who, chat, row, reads = active
    if gate == "logout":
        runtime.store.logout(who["session"])
    elif gate == "forgotten":
        runtime.shop_orders.forget_chat(who, chat.id)
    elif gate == "unapproved":
        row.update(approved=None)
        runtime.shop_orders._save(row)
    elif gate == "not_due":
        row.update(next_read=runtime.store.clock().timestamp() + 100)
        runtime.shop_orders._save(row)
    else:
        with runtime.store.connection(write=True) as db:
            if gate == "expiry":
                db.execute(
                    "update sessions set expires=?",
                    (iso(runtime.store.clock() - timedelta(seconds=2)),),
                )
            elif gate == "private":
                db.execute(
                    "update settings set data=json_set(data,'$.hide_private',json('true')),version=version+1"
                )
            else:
                db.execute(
                    "update workspace_preferences set data=json_set(data,'$.proactivity','off'),version=version+1"
                )
    follow_orders(runtime)
    assert reads == []


def test_logout_during_read_discards_late_receipt(active):
    runtime, who, chat, row, read = active
    get = runtime.shop_orders.provider.receipt

    def changed(*args):
        receipt = get(*args)
        runtime.store.logout(who["session"])
        return receipt

    runtime.shop_orders.provider.receipt = changed
    follow_orders(runtime)
    saved = runtime.shop_orders._get(row["id"], chat.owner, chat.id)
    assert (
        len(read) == 1
        and saved["state"] == "refund_pending"
        and "net_minor" not in saved["receipt"]
    )


def test_supplier_increase_is_read_in_background_and_left_for_the_owner(active):
    r, who, chat, _, _ = active
    svc = r.flight_bookings
    leg = {
        "flight": "AF3258",
        "origin": "HKG",
        "destination": "HND",
        "departs": "2026-11-27T07:00",
        "arrives": "2026-11-27T14:53",
    }
    quote = {
        "scenario": "price_change",
        "search_id": "sb_s",
        "offer_id": "sb_f",
        "segments": [leg],
        "adults": 1,
        "currency": "HKD",
        "total_minor": 5500,
    }
    view = svc.attach(quote, "flight", who, chat)
    row = svc._get(view["id"], chat.owner, chat.id)
    row.update(approved=5500, remote="sb_dev_test", state="processing", next_read=0)
    svc._save(row)
    reads = []

    def status(ident):
        reads.append(ident)
        return {
            "sandbox": True,
            "booking_id": ident,
            "offer": {"search_id": "sb_s", "offer_id": "sb_f"},
            "currency": "HKD",
            "card_last4": "4242",
            "state": "booking_in_progress",
            "terminal": False,
            "question": {
                "kind": "price_change",
                "round": 1,
                "expires_at_ms": int((r.store.clock().timestamp() + 600) * 1000),
                "price_change": {"old_total": 55, "new_total": 59, "currency": "HKD"},
            },
        }

    svc.provider = SimpleNamespace(status=status)
    svc.follow_one()
    svc.follow_one()
    saved = svc._get(view["id"], chat.owner, chat.id)
    assert reads == ["sb_dev_test"] and saved["state"] == "reprice" and saved["approved"] == 5500
    assert saved["question"]["new"] == 5900 and "capture" not in saved and "pnr" not in saved


def test_owner_can_ask_for_the_existing_followup_without_starting_another_job(active):
    from desk import commerce_aftercare

    r, who, chat, row, reads = active
    row["next_read"] = r.store.clock().timestamp() + 120
    r.shop_orders._save(row)
    chat.attachment_ids = []
    message = SimpleNamespace(
        message="退款到了告诉我",
        language="zh",
        attachment_ids=[],
        shopping_review=None,
        flight_review=None,
    )
    reply = commerce_aftercare.turn(r, message, who, chat)
    assert (
        reply["commerce_note"]
        and reply["message"] == "有结果我会在这段对话里告诉你。"
        and reads == []
    )
    with r.store.connection(write=True) as db:
        db.execute(
            "update workspace_preferences set data=json_set(data,'$.proactivity','off'),version=version+1"
        )
    assert "已关闭" in commerce_aftercare.turn(r, message, who, chat)["message"] and reads == []
