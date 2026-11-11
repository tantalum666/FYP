"""Combined-branch user boundaries; no live provider or external actions."""

import json
from datetime import UTC, datetime

import pytest

from desk.assistant import AssistantMessage
from desk.held_choices import ChoiceDraft
from desk.next_step import answer_next_step
from desk.schemas import SettingsInput
from desk.store import DomainError
from desk.tasks import TaskInput
from desk.travel_quotes.service import _instant
from test_chat_attachments import setup, login, upload, send
from test_held_choices import owner_app, DRAFT
from test_memory_morning_checkin import _app, _memory, _followup, _headers, _login
from test_purchase_cards import build, login as purchase_login, create_card, confirm, submit, post
from test_reply_owed import _say


def hide(runtime, value=True):
    with runtime.store.connection() as conn:
        settings = runtime.store.settings(conn)
    runtime.store.update_settings(
        SettingsInput(
            expected_version=settings["version"], timezone="Asia/Hong_Kong", hide_private=value
        ),
        "hide-" + str(value),
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "What should I do next?",
        "Prep me for my next meeting",
        "When am I free tomorrow?",
        "Who do I need to reply to?",
        "What am I waiting on?",
    ],
)
def test_retained_attachments_reach_provider_for_followup_questions(tmp_path, phrase):
    app, runtime, calls = setup(tmp_path)
    client = login(app)
    saved = upload(client).json()
    chat = saved["conversation_id"]
    first = send(client, conversation_id=chat, attachment_ids=[saved["attachment"]["id"]])
    assert first.status_code == 200
    before = len(calls)
    reply = send(client, phrase, conversation_id=chat)
    assert reply.status_code == 200, reply.text
    assert len(calls) == before + 1
    assert "Reviewed the selected material." in reply.json()["message"]


def test_paired_next_step_never_reveals_private_goal(tmp_path):
    app, _ = owner_app(tmp_path)
    runtime = app.state.runtime
    task = runtime.tasks.create(TaskInput(title="Secret medical goal"), "private-goal")["task"]
    runtime.goals.record(task["id"], "Secret medical goal", "2026-12-12T02:00:00+00:00")
    reply = answer_next_step(
        runtime, AssistantMessage(message="What should I do next?"), owner=False
    )
    assert "Secret medical goal" not in json.dumps(reply)
    assert reply["next_step"]["source"] != "goal"


def test_completed_reply_step_is_not_owed_and_selected_task_wins(tmp_path):
    app, _ = owner_app(tmp_path)
    runtime = app.state.runtime
    other = runtime.tasks.create(TaskInput(title="Reply to Sam"), "other")["task"]
    selected = runtime.tasks.create(
        TaskInput(title="Conference", steps=[{"title": "Reply to Pat", "done": True}]), "selected"
    )["task"]
    owed = _say(runtime, "Who do I need to reply to?", "who")
    assert "Pat" not in owed["message"]
    reply = _say(
        runtime, "I need to reply to Sam about the venue", "scoped", task_id=selected["id"]
    )
    assert reply["proposal"]["data"]["task_id"] == selected["id"]
    assert reply["proposal"]["data"]["change"]["task"]["title"] == "Conference"
    assert runtime.tasks.detail(other["id"])["task"]["title"] == "Reply to Sam"


def test_hidden_memory_endpoints_and_purchase_cards_are_unavailable(tmp_path):
    app, _ = build(tmp_path)
    runtime = app.state.runtime
    client = purchase_login(app)
    card = create_card(client)
    hide(runtime)
    for path in ["/api/memory-followups", "/api/memory-followups/morning", "/api/purchase-cards"]:
        reply = client.get(path)
        assert reply.status_code == 403, (path, reply.text)
        assert card["label"] not in reply.text
    reply = client.post(
        "/api/purchase-cards/" + card["id"] + "/confirmation",
        json={"expected_version": 1},
        headers=_headers("hidden-confirm"),
    )
    assert reply.status_code == 403


def test_held_choice_cached_receipt_still_requires_current_owner(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    token = client.cookies.get("desk_companion_session")
    runtime.held_choices.prepare(ChoiceDraft(**DRAFT), "receipt", token)
    runtime.store.logout(token)
    with pytest.raises(DomainError) as failure:
        runtime.held_choices.prepare(ChoiceDraft(**DRAFT), "receipt", token)
    assert failure.value.status == 403


def test_offer_operation_cannot_replay_for_a_different_card(tmp_path):
    app, _ = build(tmp_path)
    client = purchase_login(app)
    first = confirm(client, create_card(client)["id"])
    second = confirm(client, create_card(client, "card-two")["id"], "confirm-two")
    assert submit(client, first["id"], "same-offer").status_code == 200
    reply = submit(client, second["id"], "same-offer")
    assert reply.status_code == 409
    assert reply.json()["error"]["code"] == "OPERATION_ID_CONFLICT"


def test_purchase_approval_is_bound_to_the_version_the_owner_saw(tmp_path):
    app, _ = build(tmp_path)
    client = purchase_login(app)
    card = confirm(client, create_card(client)["id"])
    assert submit(client, card["id"], "offer-v1").status_code == 200
    change = post(
        client,
        f"/api/purchase-cards/{card['id']}/updates",
        {"expected_version": 1, "address_scope": "school"},
        "revise",
    )
    assert change.status_code == 200, change.text
    # The offer is checked against the changed card in another window.
    change_back = post(
        client,
        f"/api/purchase-cards/{card['id']}/updates",
        {"expected_version": 2, "address_scope": "home"},
        "revise-back",
    )
    assert change_back.status_code == 200
    assert submit(client, card["id"], "offer-v3").status_code == 200
    stale = post(
        client,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {"expected_version": 1},
        "stale-approval",
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"


def test_substitute_cheaper_than_budget_is_not_necessarily_cheaper_than_original(tmp_path):
    app, _ = build(tmp_path)
    client = purchase_login(app)
    card = confirm(client, create_card(client, substitution="same_spec_cheaper")["id"])
    offer = submit(
        client,
        card["id"],
        "substitute",
        sku="other-box",
        same_spec=True,
        unit_price_minor=1500,
        shipping_minor=0,
        reference_total_minor=2000,
    )
    assert offer.status_code == 200
    assert offer.json()["state"] == "refused"
    assert offer.json()["reason"] == "not_cheaper"


@pytest.mark.parametrize("local", ["2026-03-08T02:30", "2026-11-01T01:30"])
def test_trip_rejects_nonexistent_or_ambiguous_civil_time(local):
    with pytest.raises(DomainError) as failure:
        _instant(local, "America/New_York")
    assert failure.value.code == "TRIP_ITINERARY_INVALID"


def test_morning_citations_are_dynamic_and_never_copied_to_push_or_disk(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 11, 0, tzinfo=UTC))
    runtime = app.state.runtime
    facts = [
        _memory(client, body, "memory-" + str(i))
        for i, body in enumerate(["Private dentist marker", "Private lab marker"])
    ]
    for i, fact in enumerate(facts):
        _followup(client, fact, "2026-11-11T09:00", "follow-" + str(i))
    assert (
        client.post(
            "/api/memory-followups/morning",
            json={"due_local": "2026-11-11T09:00"},
            headers=_headers("morning"),
        ).status_code
        == 200
    )
    clock[0] = datetime(2026, 11, 11, 1, 1, tzinfo=UTC)
    runtime.tick()
    notice = runtime.notify.listing()["notices"][0]
    assert "Private dentist marker" in notice["body_en"]
    assert "Private dentist marker" not in json.dumps(notice["push"])
    with runtime.store.connection() as conn:
        for table in ["notice_inbox", "browser_notices", "device_notices"]:
            assert "Private dentist marker" not in str(
                [tuple(r) for r in conn.execute("SELECT * FROM " + table)]
            )
    _login(client)
    forgotten = client.post(
        f"/api/memory/{facts[0]['id']}/deletions",
        json={"expected_version": 1},
        headers=_headers("forget"),
    )
    assert forgotten.status_code == 200, forgotten.text
    assert "Private dentist marker" not in json.dumps(runtime.notify.listing())
    hide(runtime)
    assert "Private lab marker" not in json.dumps(runtime.notify.listing())


@pytest.mark.parametrize("service_name", ["purchase_cards", "source_briefs", "saved_skills"])
def test_new_private_write_rechecks_revoked_session_inside_transaction(
    tmp_path, monkeypatch, service_name
):
    from desk.purchase_cards import CardCreate
    from desk.source_briefs import OpenBrief
    from desk.saved_skills import CheckInput
    from test_purchase_cards import card_body

    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    token = client.cookies.get("desk_companion_session")
    principal = {"kind": "owner", "session": token}
    service = getattr(runtime, service_name)
    gate_name = "_gate" if service_name == "saved_skills" else "_owner"
    gate = getattr(service, gate_name)

    def expire_after_admission(*args, **kwargs):
        result = gate(*args, **kwargs)
        runtime.store.logout(token)
        return result

    monkeypatch.setattr(service, gate_name, expire_after_admission)
    with pytest.raises(DomainError) as failure:
        if service_name == "purchase_cards":
            service.create(CardCreate(**card_body()), "revoked-purchase", principal)
        elif service_name == "source_briefs":
            service.open(
                OpenBrief(question="Compare two private notes"), "revoked-brief", principal
            )
        else:
            service.record_check(
                CheckInput(
                    title="Private checklist", steps=["Review"], input_names=["topic"], passed=True
                ),
                "revoked-checklist",
                token,
            )
    assert failure.value.status == 403
    table = {
        "purchase_cards": "purchase_cards",
        "source_briefs": "source_briefs",
        "saved_skills": "saved_skills",
    }[service_name]
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0


def test_followup_retry_does_not_replay_expired_fact_text(tmp_path):
    app, client, clock = _app(tmp_path, datetime(2026, 11, 11, 0, tzinfo=UTC))
    runtime = app.state.runtime
    fact = _memory(client, "Expired confidential reminder", "expiring-memory")
    _followup(client, fact, "2026-11-11T09:00", "original-followup")
    response = client.post(
        f"/api/memory/{fact['id']}/expiry",
        json={"expected_version": 1, "expires_at": "2026-11-11T00:01:00Z"},
        headers=_headers("expiry"),
    )
    assert response.status_code == 200
    clock[0] = datetime(2026, 11, 11, 0, 2, tzinfo=UTC)
    runtime.tick()
    retry = client.post(
        "/api/memory-followups",
        json={
            "memory_id": fact["id"],
            "memory_version": 1,
            "due_local": "2026-11-11T09:00",
            "timezone": "Asia/Hong_Kong",
        },
        headers=_headers("original-followup"),
    )
    assert retry.status_code == 200, retry.text
    assert "Expired confidential reminder" not in retry.text
    assert retry.json()["followup"]["memory_active"] is False
