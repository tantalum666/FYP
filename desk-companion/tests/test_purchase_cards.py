"""Owner-confirmed staple card. Offers are checked offline. Nothing is purchased."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.workspace_data import WorkspacePreferences

HEADERS = {"X-Desk-Request": "1"}


def headers(operation_id):
    return {**HEADERS, "X-Operation-Id": operation_id}


def build(tmp_path, name="runtime"):
    moment = [datetime(2026, 11, 11, 2, tzinfo=UTC)]
    app = create_app(tmp_path / name, password="fixture", scheduler=False, clock=lambda: moment[0])
    return app, moment


def login(app):
    client = TestClient(app)
    response = client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    return client


def paired_client(app, owner):
    enrolled = owner.post(
        "/api/devices/enrol-display",
        json={"name": "Fixture screen"},
        headers=headers("enrol-" + uuid4().hex),
    )
    assert enrolled.status_code == 200, enrolled.text
    client = TestClient(app)
    client.headers.update(
        {**HEADERS, "Authorization": "Bearer " + owner.cookies.get("desk_companion_device")}
    )
    return client


def card_body(**overrides):
    body = {
        "label": "Tissues",
        "sku": "Tissue-Box",
        "quantity": 2,
        "unit": "box",
        "merchants": ["HKTVmall"],
        "budget_minor": 4500,
        "currency": "hkd",
        "substitution": "none",
        "address_scope": "Home",
    }
    body.update(overrides)
    return body


def offer_body(**overrides):
    body = {
        "offer_id": "offer-1",
        "merchant": "hktvmall",
        "sku": "TISSUE-BOX",
        "quantity": 2,
        "unit": "BOX",
        "unit_price_minor": 2000,
        "shipping_minor": 500,
        "currency": "HKD",
        "address_scope": "home",
        "observed_at": "2026-11-11T02:00:00Z",
        "same_spec": False,
    }
    body.update(overrides)
    return body


def post(client, path, body, operation_id):
    response = client.post(path, json=body, headers=headers(operation_id))
    return response


def create_card(client, operation_id="create-card", **overrides):
    response = post(client, "/api/purchase-cards", card_body(**overrides), operation_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["purchased"] is False and body["live_purchase"] is False
    return body["card"]


def confirm(client, card_id, operation_id="confirm-card"):
    response = post(client, f"/api/purchase-cards/{card_id}/confirmation", {}, operation_id)
    assert response.status_code == 200, response.text
    return response.json()["card"]


def submit(client, card_id, operation_id="offer-1", **overrides):
    return post(
        client,
        f"/api/purchase-cards/{card_id}/offers",
        offer_body(**overrides),
        operation_id,
    )


def tasks(client):
    response = client.get("/api/tasks?include_closed=true", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()["tasks"]


def task_detail(client, task_id):
    response = client.get(f"/api/tasks/{task_id}", headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def purchase_notices(client):
    response = client.get("/api/notices", headers=HEADERS)
    assert response.status_code == 200, response.text
    return [item for item in response.json()["notices"] if item["kind"] == "purchase_card"]


def notes(detail):
    return [row["note"] for row in detail["evidence"]]


def test_matching_offer_needs_approval_and_a_receipt_is_not_a_purchase(tmp_path):
    app, _moment = build(tmp_path)
    http = login(app)
    card = confirm(http, create_card(http)["id"])
    assert card["sku"] == "tissue-box"
    assert card["merchants"] == ["hktvmall"]
    assert card["address_scope"] == "home"
    assert card["state"] == "confirmed"

    draft = create_card(http, "second-card", label="Spare soap")
    refused = submit(http, draft["id"], "draft-offer")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "PURCHASE_CARD_NOT_CONFIRMED"
    assert tasks(http) == []

    matched = submit(http, card["id"])
    assert matched.status_code == 200, matched.text
    body = matched.json()
    assert body["completed"] is True
    assert body["purchased"] is False and body["live_purchase"] is False
    assert body["state"] == "needs_approval"
    assert body["total_minor"] == 4500
    assert body["reason"] is None
    saved = tasks(http)
    assert len(saved) == 1
    assert saved[0]["title"] == "Tissues"
    assert saved[0]["status"] == "todo"
    detail = task_detail(http, saved[0]["id"])
    assert detail["task"]["status"] != "completed"
    assert all("purchased" not in note.lower() for note in notes(detail))

    again = submit(http, card["id"], "offer-again")
    assert again.status_code == 200, again.text
    assert again.json()["task_id"] == body["task_id"]
    assert len(tasks(http)) == 1
    assert len(purchase_notices(http)) == 1
    assert "Nothing was bought" in purchase_notices(http)[0]["body_en"]

    early = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-1"},
        "receipt-too-soon",
    )
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "PURCHASE_RECEIPT_NOT_READY"
    assert task_detail(http, body["task_id"])["task"]["status"] == "todo"

    approved = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {},
        "approve-1",
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "approved"
    assert approved.json()["purchased"] is False
    repeated = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {},
        "approve-2",
    )
    assert repeated.status_code == 200, repeated.text
    detail = task_detail(http, body["task_id"])
    assert detail["task"]["status"] == "waiting"
    assert detail["task"]["status"] != "completed"
    assert notes(detail).count("Approved to prepare this offer. No order was placed.") == 1
    assert all(row["source"] != "owner_policy" for row in detail["evidence"])

    recorded = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-1"},
        "receipt-1",
    )
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["state"] == "receipt_recorded"
    assert recorded.json()["purchased"] is False and recorded.json()["live_purchase"] is False
    same = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-1"},
        "receipt-1",
    )
    assert same.status_code == 200, same.text
    assert same.json()["receipt_id"] == "rcpt-1"
    conflict = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-2"},
        "receipt-other",
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PURCHASE_RECEIPT_CONFLICT"
    detail = task_detail(http, body["task_id"])
    assert detail["task"]["status"] == "waiting"
    assert any("not a live purchase" in note.lower() for note in notes(detail))
    assert not any(row["kind"] == "complete" for row in detail["evidence"])
    later = submit(
        http,
        card["id"],
        "offer-after-receipt",
        offer_id="offer-2",
        unit_price_minor=4000,
        shipping_minor=500,
    )
    assert later.status_code == 200, later.text
    assert later.json()["state"] == "refused"
    assert later.json()["reason"] == "over_budget"
    assert later.json()["purchased"] is False
    detail = task_detail(http, body["task_id"])
    assert detail["task"]["status"] == "waiting"
    assert not any(row["kind"] == "complete" for row in detail["evidence"])
    kept = next(
        item
        for item in http.get("/api/purchase-cards", headers=HEADERS).json()["cards"]
        if item["label"] == "Tissues"
    )
    recorded_offer = next(item for item in kept["offers"] if item["offer_id"] == "offer-1")
    assert recorded_offer["state"] == "receipt_recorded"
    assert recorded_offer["receipt_id"] == "rcpt-1"
    http.close()


def test_mismatch_idempotency_and_a_later_offer_is_not_covered(tmp_path):
    app, _moment = build(tmp_path)
    http = login(app)
    card = confirm(http, create_card(http)["id"])
    over = submit(
        http,
        card["id"],
        "over-budget",
        offer_id="offer-high",
        unit_price_minor=3000,
        shipping_minor=500,
    )
    assert over.status_code == 200, over.text
    assert over.json()["state"] == "refused"
    assert over.json()["reason"] == "over_budget"
    assert over.json()["purchased"] is False
    assert tasks(http)[0]["status"] == "todo"

    changed = submit(
        http,
        card["id"],
        "over-budget",
        offer_id="offer-high",
        unit_price_minor=1000,
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    listing = http.get("/api/purchase-cards", headers=HEADERS).json()
    saved = listing["cards"][0]["offers"]
    assert saved[0]["state"] == "refused"
    assert saved[0]["unit_price_minor"] == 3000

    matched = submit(http, card["id"], "match", offer_id="offer-ok", unit_price_minor=1500)
    assert matched.json()["state"] == "needs_approval"
    approved = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-ok/approval",
        {},
        "approve-ok",
    )
    assert approved.status_code == 200, approved.text
    other = submit(
        http,
        card["id"],
        "other-merchant",
        offer_id="offer-other",
        merchant="other-shop",
        unit_price_minor=1000,
    )
    assert other.json()["state"] == "refused"
    assert other.json()["reason"] == "merchant_not_allowed"
    borrowed = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-other/approval",
        {},
        "borrow-approval",
    )
    assert borrowed.status_code == 409
    assert borrowed.json()["error"]["code"] == "PURCHASE_APPROVAL_NOT_READY"
    http.close()


def test_interruption_is_not_success_and_retry_applies_once(tmp_path):
    app, _moment = build(tmp_path)
    http = login(app)
    card = confirm(http, create_card(http)["id"])
    stopped = submit(http, card["id"], "once", interrupt="write")
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["completed"] is False
    assert stopped.json()["stopped"] == "interrupted"
    assert stopped.json()["purchased"] is False
    assert stopped.json()["state"] == "unopened"
    assert tasks(http) == []
    assert purchase_notices(http) == []

    opened = submit(http, card["id"], "once", interrupt="open")
    assert opened.status_code == 200, opened.text
    assert opened.json()["completed"] is False
    assert opened.json()["state"] == "opened"
    assert len(tasks(http)) == 1
    assert purchase_notices(http) == []
    detail = task_detail(http, opened.json()["task_id"])
    assert detail["task"]["status"] == "todo"
    assert not any("No order was placed" in note for note in notes(detail))

    finished = submit(http, card["id"], "once")
    assert finished.status_code == 200, finished.text
    assert finished.json()["completed"] is True
    assert finished.json()["state"] == "needs_approval"
    assert finished.json()["task_id"] == opened.json()["task_id"]
    assert len(tasks(http)) == 1
    assert len(purchase_notices(http)) == 1

    held = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {"interrupt": "hold"},
        "approve-hold",
    )
    assert held.status_code == 200, held.text
    assert held.json()["completed"] is False
    assert held.json()["stopped"] == "interrupted"
    assert task_detail(http, finished.json()["task_id"])["task"]["status"] == "todo"
    approved = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {},
        "approve-hold",
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "approved"
    assert notes(task_detail(http, finished.json()["task_id"])).count(
        "Approved to prepare this offer. No order was placed."
    ) == 1

    paused = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-9", "interrupt": "write"},
        "receipt-hold",
    )
    assert paused.json()["completed"] is False
    assert paused.json()["state"] == "approved"
    recorded = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-9"},
        "receipt-hold",
    )
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["state"] == "receipt_recorded"
    assert recorded.json()["purchased"] is False
    assert task_detail(http, finished.json()["task_id"])["task"]["status"] != "completed"
    http.close()


def test_omitted_fields_stay_and_a_changed_card_needs_a_new_approval(tmp_path):
    app, _moment = build(tmp_path)
    http = login(app)
    card = confirm(http, create_card(http)["id"])
    matched = submit(http, card["id"]).json()
    cleared = post(
        http,
        f"/api/purchase-cards/{card['id']}/updates",
        {"sku": None},
        "clear-sku",
    )
    assert cleared.status_code == 422
    assert cleared.json()["error"]["code"] == "FIELD_NOT_CLEARABLE"
    updated = post(
        http,
        f"/api/purchase-cards/{card['id']}/updates",
        {"budget_minor": 8000},
        "raise-budget",
    )
    assert updated.status_code == 200, updated.text
    fresh = updated.json()["card"]
    assert fresh["budget_minor"] == 8000
    assert fresh["sku"] == "tissue-box"
    assert fresh["quantity"] == 2
    assert fresh["merchants"] == ["hktvmall"]
    assert fresh["version"] == 2
    assert fresh["offers"][0]["state"] == "needs_reapproval"
    stale = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {},
        "stale-approval",
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_CARD"
    assert task_detail(http, matched["task_id"])["task"]["status"] == "todo"

    rechecked = submit(http, card["id"], "recheck")
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["state"] == "needs_approval"
    assert rechecked.json()["card_version"] == 2
    approved = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/approval",
        {},
        "approve-after-change",
    )
    assert approved.status_code == 200, approved.text
    narrowed = post(
        http,
        f"/api/purchase-cards/{card['id']}/updates",
        {"budget_minor": 1000},
        "lower-budget",
    )
    assert narrowed.json()["card"]["sku"] == "tissue-box"
    assert narrowed.json()["card"]["offers"][0]["state"] == "needs_reapproval"
    receipt = post(
        http,
        f"/api/purchase-cards/{card['id']}/offers/offer-1/receipt",
        {"receipt_id": "rcpt-stale"},
        "stale-receipt",
    )
    assert receipt.status_code == 409
    assert receipt.json()["error"]["code"] == "STALE_CARD"
    assert task_detail(http, matched["task_id"])["task"]["status"] != "completed"
    http.close()


def test_substitute_casefold_quiet_notice_permission_and_backup(tmp_path):
    app, moment = build(tmp_path)
    http = login(app)
    version = http.get("/api/permissions", headers=HEADERS).json()["version"]
    permission = http.post(
        "/api/permissions",
        json={"mode": "full", "expected_version": version},
        headers=headers("full-access"),
    )
    assert permission.status_code == 200, permission.text
    card = confirm(
        http,
        create_card(http, substitution="same_spec_cheaper", budget_minor=5000)["id"],
    )
    same_price = submit(
        http,
        card["id"],
        "not-cheaper",
        offer_id="offer-sub",
        sku="other-box",
        same_spec=True,
        unit_price_minor=2250,
        shipping_minor=500,
    )
    assert same_price.json()["state"] == "refused"
    assert same_price.json()["reason"] == "not_cheaper"
    cheaper = submit(
        http,
        card["id"],
        "cheaper",
        offer_id="offer-cheap",
        sku="Other-Box",
        same_spec=True,
        unit_price_minor=1500,
        shipping_minor=0,
    )
    assert cheaper.status_code == 200, cheaper.text
    assert cheaper.json()["state"] == "needs_approval"
    assert cheaper.json()["purchased"] is False
    assert http.get("/api/permissions", headers=HEADERS).json()["mode"] == "full"
    assert task_detail(http, cheaper.json()["task_id"])["task"]["status"] == "todo"

    settings = WorkspacePreferences(quiet_start="08:00", quiet_end="12:00").model_dump()
    quiet = http.post(
        "/api/workspace/preferences",
        json={"expected_version": 1, "preferences": settings},
        headers=headers("quiet"),
    )
    assert quiet.status_code == 200, quiet.text
    # The cheaper offer already published before quiet hours. A new offer is held.
    held = submit(
        http,
        card["id"],
        "quiet-offer",
        offer_id="offer-quiet",
        sku="tissue-box",
        same_spec=False,
        unit_price_minor=1000,
        shipping_minor=0,
    )
    assert held.json()["state"] == "needs_approval"
    assert [item["id"] for item in purchase_notices(http)].count(
        next(item["id"] for item in purchase_notices(http) if "Nothing was bought" in item["body_en"])
    ) >= 1
    before = len(purchase_notices(http))
    moment[0] = datetime(2026, 11, 11, 5, tzinfo=UTC)
    app.state.runtime.tick()
    after = purchase_notices(http)
    assert len(after) == before + 1
    app.state.runtime.tick()
    assert len(purchase_notices(http)) == len(after)

    screen = paired_client(app, http)
    denied = screen.post(
        "/api/purchase-cards",
        json=card_body(),
        headers=headers("paired-create"),
    )
    assert denied.status_code == 403
    denied_approval = screen.post(
        f"/api/purchase-cards/{card['id']}/offers/offer-cheap/approval",
        json={},
        headers=headers("paired-approve"),
    )
    assert denied_approval.status_code == 403
    anonymous = TestClient(app)
    assert anonymous.get("/api/purchase-cards", headers=HEADERS).status_code == 403

    revoked = post(http, f"/api/purchase-cards/{card['id']}/revocation", {}, "revoke")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["card"]["state"] == "revoked"
    later = submit(http, card["id"], "after-revoke", offer_id="offer-later")
    assert later.status_code == 409
    assert later.json()["error"]["code"] == "PURCHASE_CARD_REVOKED"

    backup = http.get("/api/exchange/backup.json", headers=HEADERS)
    assert backup.status_code == 200, backup.text
    payload = backup.json()["payload"]
    assert "mailbox_bundle" in payload
    assert "shopping_bundle" in payload
    assert "offline_calendar_bundle" in payload
    assert "purchase_bundle" not in payload
    assert "purchase_cards" not in payload
    http.close()
    screen.close()
    anonymous.close()
