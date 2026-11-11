"""Held choices stay pending until the owner approves the exact wording."""

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.held_choices import ChoiceApproval
from desk.permissions import PermissionChange
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.store import DomainError

DRAFT = {
    "title": "Friday dinner",
    "assumption": "Budget stays HKD 2000",
    "choice": "Cook at home",
    "reason": "The quoted delivery is above that budget",
}


def owner_app(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return app, client


def post(client, path, body, key):
    return client.post(
        path,
        json=body,
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )


def prepare(client, body=None, key="prepare-1"):
    response = post(client, "/api/held-choices", body or DRAFT, key)
    assert response.status_code == 200, response.text
    return response.json()


def approval_body(pending):
    return {
        "expected_version": pending["version"],
        "title": pending["title"],
        "assumption": pending["assumption"],
        "choice": pending["choice"],
        "reason": pending["reason"],
    }


def counts(runtime):
    with runtime.store.connection() as conn:
        return {
            name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("tasks", "assistant_proposals", "computer_jobs", "held_choices")
        }


def test_prepare_is_not_current_and_approval_of_the_exact_wording_holds_it(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    before = counts(runtime)
    saved = prepare(client)
    choice = saved["choice"]
    assert saved["held"] is False and saved["mailed"] is False
    assert saved["purchased"] is False and saved["booked"] is False and saved["live_effect"] is False
    assert choice["current"] is None and choice["pending"]["state"] == "pending"
    assert choice["pending"]["assumption"] == DRAFT["assumption"]
    listed = client.get("/api/held-choices")
    assert listed.status_code == 200
    assert listed.json()["choices"][0]["pending"]["id"] == choice["pending"]["id"]
    assert listed.json()["choices"][0]["held"] is False
    mismatch = post(
        client,
        f"/api/held-choices/{choice['id']}/approval",
        {**approval_body(choice["pending"]), "assumption": "Budget stays HKD 9000"},
        "approve-wrong",
    )
    assert mismatch.status_code == 409 and mismatch.json()["error"]["code"] == "CHOICE_TEXT_MISMATCH"
    assert client.get("/api/held-choices").json()["choices"][0]["held"] is False
    approved = post(
        client,
        f"/api/held-choices/{choice['id']}/approval",
        approval_body(choice["pending"]),
        "approve-1",
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["held"] is True and body["choice"]["current"]["version"] == 1
    assert body["choice"]["pending"] is None
    again = post(
        client,
        f"/api/held-choices/{choice['id']}/approval",
        approval_body(choice["pending"]),
        "approve-1",
    )
    assert again.json()["choice"]["current"]["id"] == body["choice"]["current"]["id"]
    runtime.permissions.change(PermissionChange(mode="full", expected_version=1), "full-access")
    runtime.tick()
    after = counts(runtime)
    assert after["tasks"] == before["tasks"] == 0
    assert after["assistant_proposals"] == before["assistant_proposals"] == 0
    assert after["computer_jobs"] == before["computer_jobs"] == 0
    assert after["held_choices"] == 1
    assert client.get("/api/held-choices").json()["choices"][0]["current"]["state"] == "current"


def test_same_wording_does_not_open_a_second_choice(tmp_path):
    _, client = owner_app(tmp_path)
    first = prepare(client)
    post(
        client,
        f"/api/held-choices/{first['choice']['id']}/approval",
        approval_body(first["choice"]["pending"]),
        "approve-1",
    )
    second = prepare(client, key="prepare-2")
    assert second["reused"] is True and second["choice"]["id"] == first["choice"]["id"]
    folded = {**DRAFT, "choice": "cook at home"}
    third = prepare(client, folded, "prepare-3")
    assert third["reused"] is True and third["choice"]["id"] == first["choice"]["id"]
    assert client.get("/api/held-choices").json()["choices"][0]["current"]["choice"] == "Cook at home"
    with_space = {**DRAFT, "assumption": "Budget stays  HKD   2000"}
    collapsed = prepare(client, with_space, "prepare-space")
    assert collapsed["reused"] is True
    fresh = prepare(
        client,
        {**DRAFT, "assumption": "Budget stays HKD 1800"},
        "prepare-other",
    )
    assert fresh["reused"] is False and fresh["choice"]["id"] != first["choice"]["id"]
    assert len(client.get("/api/held-choices").json()["choices"]) == 2


def test_omitted_fields_stay_and_null_does_not_clear(tmp_path):
    _, client = owner_app(tmp_path)
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    pending = saved["choice"]["pending"]
    approved = post(client, f"/api/held-choices/{choice_id}/approval", approval_body(pending), "approve-1")
    current = approved.json()["choice"]["current"]
    replaced = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 1500"},
        "replace-1",
    )
    assert replaced.status_code == 200, replaced.text
    body = replaced.json()["choice"]
    assert body["current"]["assumption"] == DRAFT["assumption"]
    assert body["current"]["choice"] == DRAFT["choice"] and body["current"]["reason"] == DRAFT["reason"]
    assert body["pending"]["assumption"] == "Budget stays HKD 1500"
    assert body["pending"]["title"] == DRAFT["title"]
    assert body["pending"]["choice"] == DRAFT["choice"] and body["pending"]["reason"] == DRAFT["reason"]
    assert body["held"] is True
    cleared = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "choice": None},
        "replace-null",
    )
    assert cleared.status_code == 422 and cleared.json()["error"]["code"] == "VALIDATION_FAILED"
    still = client.get("/api/held-choices").json()["choices"][0]
    assert still["current"]["choice"] == DRAFT["choice"]
    assert still["pending"]["assumption"] == "Budget stays HKD 1500"
    same = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 1500"},
        "replace-1",
    )
    assert same.json()["choice"]["pending"]["id"] == body["pending"]["id"]
    conflict = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 100"},
        "replace-1",
    )
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert client.get("/api/held-choices").json()["choices"][0]["pending"]["assumption"] == "Budget stays HKD 1500"


def test_new_assumption_keeps_the_old_wording_until_a_fresh_approval(tmp_path):
    _, client = owner_app(tmp_path)
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    post(client, f"/api/held-choices/{choice_id}/approval", approval_body(saved["choice"]["pending"]), "approve-1")
    current = client.get("/api/held-choices").json()["choices"][0]["current"]
    opened = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 1500"},
        "replace-1",
    ).json()["choice"]
    blocked = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 100"},
        "replace-2",
    )
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "CHOICE_REVISION_OPEN"
    stale_version = post(
        client,
        f"/api/held-choices/{choice_id}/approval",
        approval_body(current),
        "approve-old-version",
    )
    assert stale_version.status_code == 409
    assert stale_version.json()["error"]["code"] == "VERSION_CONFLICT"
    stale_text = post(
        client,
        f"/api/held-choices/{choice_id}/approval",
        {**approval_body(opened["pending"]), "assumption": DRAFT["assumption"]},
        "approve-old-text",
    )
    assert stale_text.status_code == 409
    assert stale_text.json()["error"]["code"] == "CHOICE_TEXT_MISMATCH"
    held = client.get("/api/held-choices").json()["choices"][0]
    assert held["current"]["assumption"] == DRAFT["assumption"]
    assert held["pending"]["id"] == opened["pending"]["id"]
    approved = post(
        client,
        f"/api/held-choices/{choice_id}/approval",
        approval_body(opened["pending"]),
        "approve-2",
    )
    assert approved.status_code == 200, approved.text
    choice = approved.json()["choice"]
    assert choice["current"]["assumption"] == "Budget stays HKD 1500"
    assert choice["current"]["version"] == 2
    assert choice["previous"][0]["assumption"] == DRAFT["assumption"]
    assert choice["previous"][0]["choice"] == DRAFT["choice"]
    assert choice["previous"][0]["state"] == "previous"
    assert choice["pending"] is None and choice["held"] is True


def test_interruption_is_not_success_and_the_same_operation_finishes_once(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    pending = saved["choice"]["pending"]
    runtime.held_choices.interrupt_after_intent = True
    stopped = post(client, f"/api/held-choices/{choice_id}/approval", approval_body(pending), "approve-1")
    assert stopped.status_code == 409 and stopped.json()["error"]["code"] == "INTERRUPTED"
    assert client.get("/api/held-choices").json()["choices"][0]["held"] is False
    token = client.cookies["desk_companion_session"]
    restarted = Runtime(runtime.store)
    finished = restarted.held_choices.approve(
        choice_id, ChoiceApproval(**approval_body(pending)), "approve-1", token
    )
    assert finished["held"] is True and finished["operation_id"] == "approve-1"
    repeated = restarted.held_choices.approve(
        choice_id, ChoiceApproval(**approval_body(pending)), "approve-1", token
    )
    assert repeated["choice"]["current"]["id"] == finished["choice"]["current"]["id"]
    with runtime.store.connection() as conn:
        states = [row["state"] for row in conn.execute("SELECT state FROM held_choices")]
    assert states == ["current"]
    seen = client.get("/api/held-choices").json()["choices"][0]
    assert seen["held"] is True and seen["current"]["state"] == "current"
    extra = post(client, f"/api/held-choices/{choice_id}/approval", approval_body(pending), "approve-extra")
    assert extra.status_code == 404 and extra.json()["error"]["code"] == "CHOICE_NOT_FOUND"


def test_a_lost_prepare_does_not_create_the_choice_until_the_same_save_finishes(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    runtime.held_choices.interrupt_after_intent = True
    stopped = post(client, "/api/held-choices", DRAFT, "prepare-1")
    assert stopped.status_code == 409 and stopped.json()["error"]["code"] == "INTERRUPTED"
    assert client.get("/api/held-choices").json()["choices"] == []
    finished = prepare(client, key="prepare-1")
    assert finished["choice"]["pending"]["title"] == DRAFT["title"]
    again = prepare(client, key="prepare-1")
    assert again["choice"]["pending"]["id"] == finished["choice"]["pending"]["id"]
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM held_choices").fetchone()[0] == 1


def test_logout_and_hidden_private_cannot_finish_an_approval(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    pending = saved["choice"]["pending"]
    body = approval_body(pending)
    runtime.held_choices.interrupt_after_intent = True
    assert post(client, f"/api/held-choices/{choice_id}/approval", body, "approve-hidden").status_code == 409
    runtime.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide",
    )
    hidden = post(client, f"/api/held-choices/{choice_id}/approval", body, "approve-hidden")
    assert hidden.status_code == 403 and hidden.json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
    assert client.get("/api/held-choices").json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
    runtime.store.update_settings(
        SettingsInput(expected_version=2, timezone="Asia/Hong_Kong", hide_private=False),
        "show",
    )
    runtime.held_choices.interrupt_after_intent = True
    assert post(client, f"/api/held-choices/{choice_id}/approval", body, "approve-logout").status_code == 409
    assert client.delete("/api/session", headers={"X-Desk-Request": "1"}).status_code == 200
    logged_out = post(client, f"/api/held-choices/{choice_id}/approval", body, "approve-logout")
    assert logged_out.status_code == 403
    stranger = TestClient(app)
    assert stranger.get("/api/held-choices").status_code == 403
    assert post(stranger, f"/api/held-choices/{choice_id}/approval", body, "approve-stranger").status_code == 403
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT state FROM held_choices").fetchone()["state"] == "pending"


def test_signed_out_token_is_refused_inside_the_write(tmp_path):
    app, client = owner_app(tmp_path)
    runtime = app.state.runtime
    saved = prepare(client)
    token = client.cookies["desk_companion_session"]
    runtime.store.logout(token)
    with pytest.raises(DomainError) as caught:
        runtime.held_choices.approve(
            saved["choice"]["id"],
            ChoiceApproval(**approval_body(saved["choice"]["pending"])),
            "approve-direct",
            token,
        )
    assert caught.value.code == "OWNER_SIGN_IN_REQUIRED"
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT state FROM held_choices").fetchone()["state"] == "pending"


def test_a_later_approval_after_interruption_still_holds_once(tmp_path):
    app, client = owner_app(tmp_path)
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    pending = saved["choice"]["pending"]
    app.state.runtime.held_choices.interrupt_after_intent = True
    assert post(client, f"/api/held-choices/{choice_id}/approval", approval_body(pending), "approve-old").status_code == 409
    approved = post(client, f"/api/held-choices/{choice_id}/approval", approval_body(pending), "approve-new")
    assert approved.status_code == 200 and approved.json()["held"] is True
    with app.state.runtime.store.connection() as conn:
        rows = conn.execute("SELECT state FROM held_choices").fetchall()
    assert [row["state"] for row in rows] == ["current"]


def test_drop_the_draft_and_do_not_drop_the_held_choice_while_a_draft_is_open(tmp_path):
    app, client = owner_app(tmp_path)
    saved = prepare(client)
    choice_id = saved["choice"]["id"]
    post(client, f"/api/held-choices/{choice_id}/approval", approval_body(saved["choice"]["pending"]), "approve-1")
    current = client.get("/api/held-choices").json()["choices"][0]["current"]
    pending = post(
        client,
        f"/api/held-choices/{choice_id}/replacements",
        {"expected_version": current["version"], "assumption": "Budget stays HKD 1500"},
        "replace-1",
    ).json()["choice"]["pending"]
    blocked = post(
        client,
        f"/api/held-choices/{choice_id}/withdrawal",
        {"target": "current", "expected_version": current["version"]},
        "drop-current",
    )
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "CHOICE_REVISION_OPEN"
    dropped = post(
        client,
        f"/api/held-choices/{choice_id}/withdrawal",
        {"target": "pending", "expected_version": pending["version"]},
        "drop-pending",
    )
    assert dropped.status_code == 200, dropped.text
    choice = dropped.json()["choice"]
    assert choice["pending"] is None and choice["current"]["assumption"] == DRAFT["assumption"]
    assert dropped.json()["held"] is True
    withdrawn = post(
        client,
        f"/api/held-choices/{choice_id}/withdrawal",
        {"target": "current", "expected_version": current["version"]},
        "drop-held",
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["held"] is False
    assert client.get("/api/held-choices").json()["choices"] == []
    with app.state.runtime.store.connection() as conn:
        assert conn.execute("SELECT state FROM held_choices").fetchone()["state"] == "withdrawn"
