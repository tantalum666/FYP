"""Owner overviews share the composer with commerce, quiet hours and Google readback."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event

from desk import approval_status
from desk.flight_booking.provider import FlightQuery
from desk.permissions import PermissionChange
from test_conversation_shop_checkout import quote
from test_quiet_catch_up import ASK, COOKIE, client_for, desk as desk, open_chat, post, review


STATUS = "What needs my approval?"
GOOGLE = "What changed in my Google Calendar just now?"


def say(client, key, words, chat=None, **fields):
    return post(client, "assistant/messages", {"message": words, "conversation_id": chat, **fields}, key)


def originals(runtime):
    with runtime.store.connection() as db:
        return [list(map(tuple, db.execute(f"SELECT * FROM {table} ORDER BY rowid"))) for table in (
            "sandbox_shop_orders", "sandbox_flight_bookings", "assistant_proposals", "agent_runs", "tasks", "events",
        )]


def test_private_questions_keep_inferred_approvals_read_only_in_full_mode(desk, monkeypatch):
    d = desk
    current = open_chat(d)
    who = {"kind": "owner", "session": d.client.cookies[COOKIE]}
    shop = d.runtime.shop_orders.attach(quote(), "original-shop", who, current)
    service = d.runtime.flight_bookings
    fare = service.prepare(FlightQuery(origin="HKG", destination="HND", departure=d.flight.day, flight_number="FR4315"))
    flight = service.attach(fare["sandbox_quote"], "original-flight", who, current)
    menu = service.prepare(FlightQuery(origin="HKG", destination="HND", departure=d.flight.day, flight_number="XX999"))
    service.attach_shortlist(menu["flight_alternatives"], "original-menu", who, current)
    d.runtime.permissions.change(PermissionChange(mode="full", expected_version=d.runtime.permissions.snapshot()["version"]), "full-owner")
    before = originals(d.runtime)
    before_lookup = len(d.flight.calls)

    def no_grant(*args, **kwargs):
        raise AssertionError("A read-only question requested an execution grant")

    with monkeypatch.context() as patch:
        patch.setattr(d.runtime.permissions, "capture", no_grant)
        patch.setattr(d.runtime.permissions, "apply_reply", no_grant)
        summary = say(d.client, "overview", STATUS, current.id, shopping_review=review(shop)).json()
        assert summary["kind"] == "approval_status" and summary["total"] == 2
        assert summary["acted"] is False and summary["saved"] is False
        assert {row["title"] for row in summary["items"]} == {"FR4315", "测试文具包 × 2"}
        assert summary == say(d.client, "overview", STATUS, current.id, shopping_review=review(shop)).json()
        with d.runtime.store.connection() as db:
            (stored,) = db.execute("SELECT result FROM assistant_replies WHERE json_extract(result,'$.kind')='approval_status'").fetchone()
        assert not {"items", "message", "total"}.intersection(json.loads(stored))
        assert "FR4315" not in stored and "测试文具包" not in stored
        quiet = say(d.client, "quiet-overview", ASK, current.id, flight_review=review(flight)).json()
        assert quiet["kind"] == "quiet_catch_up" and not quiet["saved"]
        google = say(d.client, "google-overview", GOOGLE, current.id, flight_review=review(flight)).json()
        assert google["kind"] == "reply" and "no confirmed Google Calendar" in google["message"]
    menu_reply = say(d.client, "read-flight-options", "show flight list 1", current.id).json()
    assert menu_reply["flight_alternatives"]["original"] and not menu_reply["saved"]
    assert originals(d.runtime) == before
    assert d.shop.submissions == 0 and len(d.flight.calls) == before_lookup and not d.protocol.requests
    assert say(client_for(d.client.app), "other-login", STATUS, current.id).status_code == 404

    # A deliberate click on a real, versioned card still reaches just that order.
    declined = say(d.client, "decline-card", "decline", current.id,
                   flight_review=review(flight), selected_commerce_card=True).json()
    assert declined["flight_booking"]["state"] == "cancelled"
    remaining = say(d.client, "overview-after-decline", STATUS, current.id).json()
    assert remaining["total"] == 1 and remaining["items"][0]["title"] == "测试文具包 × 2"
    assert d.shop.submissions == 0 and len(d.flight.calls) == before_lookup


def test_forgetting_an_initial_overview_severs_its_original_operation(desk):
    first = say(desk.client, "headless-overview", STATUS).json()
    chat = first["conversation_id"]
    assert first["kind"] == "approval_status"
    restarted = client_for(desk.boot(), desk.client.cookies[COOKIE])
    assert say(restarted, "headless-overview", STATUS).json()["conversation_id"] == chat
    other = client_for(desk.boot())
    assert say(other, "headless-overview", STATUS).status_code == 404
    # An explicit follow-up with a new key can also recover from the saved scope alone.
    restarted = client_for(desk.boot(), desk.client.cookies[COOKIE])
    assert say(restarted, "next-overview", STATUS, chat).json()["conversation_id"] == chat
    assert restarted.delete("/api/voice/conversations/" + chat, headers={"X-Desk-Request": "1"}).is_success
    restarted = client_for(desk.boot(), desk.client.cookies[COOKIE])
    assert say(restarted, "headless-overview", STATUS).status_code == 404
    assert say(restarted, "old-chat", STATUS, chat).status_code == 404
    assert say(desk.client, "fresh-overview", STATUS).json()["conversation_id"] != chat


def test_legacy_status_marker_without_scope_cannot_recreate_a_forgotten_chat(desk):
    first = say(desk.client, "old-marker", STATUS).json()
    with desk.runtime.store.connection(write=True) as db:
        db.execute("UPDATE assistant_replies SET result=? WHERE json_extract(result,'$.kind')='approval_status'",
                   ('{"kind":"approval_status"}',))
    # The original live chat is still usable before it is explicitly forgotten.
    assert say(desk.client, "old-marker", STATUS).json()["conversation_id"] == first["conversation_id"]
    assert desk.client.delete("/api/voice/conversations/" + first["conversation_id"],
                              headers={"X-Desk-Request": "1"}).is_success
    assert say(desk.client, "old-marker", STATUS).status_code == 404


def test_competing_google_and_approval_questions_reject_a_reused_operation_key(desk, monkeypatch):
    chat = open_chat(desk)
    prepared, finish = Event(), Event()
    original = approval_status.answer

    def pause_after_snapshot(*args):
        reply = original(*args)
        prepared.set()
        assert finish.wait(10)
        return reply

    monkeypatch.setattr(approval_status, "answer", pause_after_snapshot)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(say, desk.client, "competing-read", STATUS, chat.id)
        try:
            assert prepared.wait(10)
            assert say(desk.client, "competing-read", GOOGLE, chat.id).is_success
        finally:
            finish.set()
        rejected = pending.result(timeout=10)
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert desk.shop.submissions == 0 and not desk.flight.calls
