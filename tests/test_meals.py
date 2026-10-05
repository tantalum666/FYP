from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_api import api as api
from test_api import decision, low
from senplate_api.app import create_app
from senplate_api.domain import utcnow
from senplate_api.models import (
    ConsoleSession,
    FoodReference,
    Meal,
    Observation,
    PairRequest,
    Run,
    User,
)


def user(a, name="personal"):
    return {**a["headers"][name], "X-Context-ID": "personal"}


def post(a, path, body, headers=None, key=None):
    key = key or str(uuid4())
    return a["client"].post(
        path,
        headers={**(headers or {}), "Idempotency-Key": key},
        json={"client_operation_id": key, **body},
    )


def setup(a, mode="personal"):
    r = a["client"].post(
        "/v1/device-console/session",
        json={"workspace_id": a["workspace"], "setup_key": a["settings"].console_key},
    )
    assert r.status_code == 200, r.text
    r = post(a, "/v1/device-console/meals", {"expected_run_id": a["run"]["run_id"], "mode": mode})
    assert r.status_code == 200, r.text
    return r.json()["meal_id"]


def active(a):
    r = a["client"].get("/v1/device-console/active")
    assert r.status_code == 200, r.text
    return r.json()["meal"]


def measured(a, grams, action="set", seconds=1, key=None):
    state = active(a)
    r = post(
        a,
        "/v1/device-console/simulate",
        {"run_id": state["run_id"], "action": action, "weight_g": grams, "seconds": seconds},
        key=key,
    )
    assert r.status_code == 200, r.text
    return active(a)


def action(a, name, *, personal=False, key=None, **extra):
    state = active(a)
    prefix = "/v1/meals" if personal else "/v1/device-console/meals"
    return post(
        a,
        f"{prefix}/{state['id']}/actions",
        {"expected_version": state["version"], "action": name, **extra},
        user(a) if personal else None,
        key,
    )


def ready(a, mode="personal"):
    id = setup(a, mode)
    measured(a, 0)
    r = action(a, "confirm_empty", observation_id=active(a)["current"]["observation_id"])
    assert r.status_code == 200, r.text
    if mode == "personal":
        r = post(a, "/v1/pairing/requests", {"code": active(a)["pairing"]["code"]}, user(a))
        assert r.status_code == 200, r.text
        r = action(a, "approve_pairing", request_id=r.json()["request_id"])
        assert r.status_code == 200, r.text
    return id


def portion(a, slug, amount, personal=True):
    refs = a["client"].get("/v1/food-references", headers=user(a)).json()["items"]
    ref = next(r for r in refs if r["slug"] == slug)
    start = active(a)["current"]
    r = action(
        a,
        "prepare_portion",
        personal=personal,
        reference_id=ref["id"],
        observation_id=start["observation_id"],
    )
    assert r.status_code == 200, r.text
    measured(a, start["net_g"] + amount)
    r = action(
        a,
        "confirm_portion",
        personal=personal,
        observation_id=active(a)["current"]["observation_id"],
    )
    assert r.status_code == 200, r.text
    return active(a)


def test_personal_pairing_meal_nutrition_and_remaining_chain(api):
    a = api
    id = ready(a)
    for slug, grams in [("rice", 200), ("chicken", 100), ("broccoli", 150)]:
        state = portion(a, slug, grams)
    assert state["provided_g"] == 450
    assert [p["amount_g"] for p in state["portions"]] == [200, 100, 150]
    assert state["nutrition"]["status"] == "complete"
    assert state["nutrition"]["total"]["energy_kcal"] == float(
        Decimal(130) * 2 + Decimal(165) + Decimal(35) * Decimal("1.5")
    )
    assert state["nutrition"]["total"]["protein_g"] == 39.97
    assert (
        action(
            a, "finish_plating", personal=True, observation_id=state["current"]["observation_id"]
        ).status_code
        == 200
    )
    measured(a, 350)
    assert (
        action(
            a, "complete", personal=True, observation_id=active(a)["current"]["observation_id"]
        ).status_code
        == 200
    )
    own = a["client"].get(f"/v1/meals/{id}", headers=user(a)).json()
    assert own["state"] == "completed" and own["remaining_g"] == 350 and own["intake_g"] is None
    assert own["nutrition"]["total"]["energy_kcal"] == 477.5
    assert own["nutrition"]["intake"] is None and own["current"] is None
    assert active(a) is None


def test_pairing_requires_station_approval_and_is_single_use(api):
    a = api
    id = setup(a)
    assert action(a, "confirm_empty", observation_id="unknown").status_code == 409
    measured(a, 20)
    assert (
        action(a, "confirm_empty", observation_id=active(a)["current"]["observation_id"]).json()[
            "error"
        ]["code"]
        == "EMPTY_PLATE_REQUIRED"
    )
    measured(a, 0)
    action(a, "confirm_empty", observation_id=active(a)["current"]["observation_id"])
    code = active(a)["pairing"]["code"]
    r = post(a, "/v1/pairing/requests", {"code": code}, user(a))
    req = r.json()["request_id"]
    assert a["client"].get(f"/v1/meals/{id}", headers=user(a)).status_code == 404
    assert action(a, "approve_pairing", personal=True, request_id=req).status_code == 404
    pending = a["client"].get("/v1/me/pairing", headers=user(a)).json()["items"][0]
    assert pending["meal_id"] is None and len(pending["check_code"]) == 4
    assert action(a, "approve_pairing", request_id=req).status_code == 200
    assert post(a, "/v1/pairing/requests", {"code": code}, user(a, "manager")).status_code == 409
    assert a["client"].get(f"/v1/meals/{id}", headers=user(a)).status_code == 200


def test_pairing_two_people_only_one_pending_owner(api):
    a = api
    setup(a)
    measured(a, 0)
    action(a, "confirm_empty", observation_id=active(a)["current"]["observation_id"])
    code = active(a)["pairing"]["code"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda name: post(a, "/v1/pairing/requests", {"code": code}, user(a, name)),
                ["personal", "manager"],
            )
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    winner = next(r.json()["request_id"] for r in results if r.status_code == 200)
    assert action(a, "approve_pairing", request_id=winner).status_code == 200
    with Session(a["engine"]) as db:
        req = db.get(PairRequest, winner)
        m = db.get(Meal, req.meal_id)
        assert m.owner_id == req.user_id


def test_expired_rejected_and_rotated_pair_codes(api):
    a = api
    setup(a)
    measured(a, 0)
    action(a, "confirm_empty", observation_id=active(a)["current"]["observation_id"])
    code = active(a)["pairing"]["code"]
    req = post(a, "/v1/pairing/requests", {"code": code}, user(a)).json()["request_id"]
    assert action(a, "reject_pairing", request_id=req).status_code == 200
    assert (
        a["client"].get("/v1/me/pairing", headers=user(a)).json()["items"][0]["state"] == "rejected"
    )
    assert action(a, "rotate_code").status_code == 200
    assert post(a, "/v1/pairing/requests", {"code": code}, user(a)).status_code == 409
    state = active(a)
    with Session(a["engine"]) as db:
        db.get(Meal, state["id"]).pair_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert (
        post(a, "/v1/pairing/requests", {"code": state["pairing"]["code"]}, user(a)).status_code
        == 409
    )
    assert a["client"].get("/v1/device-console/pairing-qr.svg").status_code == 409


def test_private_measurements_do_not_leak_through_work_routes(api):
    a = api
    id = ready(a)
    state = portion(a, "rice", 200)
    h = a["headers"]["manager"]
    for context in [h, user(a, "manager"), a["headers"]["viewer"]]:
        assert a["client"].get(f"/v1/meals/{id}", headers=context).status_code == 404
    public = (
        a["client"].get(f"/v1/workspaces/{a['workspace']}/overview", headers=h).json()["station"]
    )
    assert (
        public["mode"] == "personal" and public["net_g"] is None and public["last_valid_g"] is None
    )
    assert public["history"] == public["events"] == public["tasks"] == []
    assert public["recommendation"] is None and public["provided_g"] is None
    assert (
        a["client"].get(f"/v1/stations/{public['station_id']}/events", headers=h).status_code == 403
    )
    assert (
        a["client"].get(f"/v1/workspaces/{a['workspace']}/events.csv", headers=h).status_code == 403
    )
    menu = a["client"].get(f"/v1/workspaces/{a['workspace']}/menu", headers=h).json()
    assert menu["items"] == [] and not menu["service_open"]
    samples = a["client"].get(f"/v1/workspaces/{a['workspace']}/samples", headers=h).json()
    assert samples["items"] == []
    assert state["provided_g"] == 200


def test_portion_retries_and_version_races_do_not_duplicate_weight(api):
    a = api
    ready(a)
    refs = a["client"].get("/v1/food-references", headers=user(a)).json()["items"]
    ref = next(r for r in refs if r["slug"] == "rice")
    state = active(a)
    action(
        a,
        "prepare_portion",
        personal=True,
        reference_id=ref["id"],
        observation_id=state["current"]["observation_id"],
    )
    state = measured(a, 200)
    key = str(uuid4())
    path = f"/v1/meals/{state['id']}/actions"
    body = {
        "action": "confirm_portion",
        "expected_version": state["version"],
        "observation_id": state["current"]["observation_id"],
    }
    first = post(a, path, body, user(a), key)
    assert first.status_code == 200
    assert post(a, path, body, user(a), key).json() == first.json()
    assert post(a, path, body, user(a)).status_code == 409
    assert post(a, path, {**body, "note": "changed"}, user(a), key).status_code == 409
    state = active(a)
    assert state["provided_g"] == 200 and len(state["portions"]) == 1
    assert a["client"].get("/v1/operations/" + key, headers=user(a)).json() == first.json()


def test_meal_unknown_reference_and_snapshot_version_isolation(api):
    a = api
    id = ready(a)
    state = portion(a, "rice", 200)
    ref_id = state["portions"][0]["reference_id"]
    with Session(a["engine"]) as db:
        ref = db.get(FoodReference, ref_id)
        ref.snapshot = {
            **ref.snapshot,
            "per_100_g": {**ref.snapshot["per_100_g"], "energy_kcal": "999"},
        }
        db.commit()
    state = a["client"].get(f"/v1/meals/{id}", headers=user(a)).json()
    assert state["nutrition"]["total"]["energy_kcal"] == 260
    state = portion(a, "unknown", 50)
    assert (
        state["nutrition"]["status"] == "partial"
        and state["nutrition"]["total"]["energy_kcal"] is None
    )
    assert state["nutrition"]["known_subtotal"]["energy_kcal"] == 260
    assert state["nutrition"]["covered_g"]["energy_kcal"] == 200 and state["provided_g"] == 250


def test_calibration_absence_and_decrease_reject_portion_windows(api):
    a = api
    ready(a)
    ref = next(
        r
        for r in a["client"].get("/v1/food-references", headers=user(a)).json()["items"]
        if r["slug"] == "rice"
    )
    action(
        a,
        "prepare_portion",
        personal=True,
        reference_id=ref["id"],
        observation_id=active(a)["current"]["observation_id"],
    )
    measured(a, 200)
    measured(a, 150)
    assert (
        action(
            a,
            "confirm_portion",
            personal=True,
            observation_id=active(a)["current"]["observation_id"],
        ).json()["error"]["code"]
        == "PORTION_WEIGHT_DECREASED"
    )
    measured(a, 0)
    assert (
        action(
            a,
            "cancel_portion",
            personal=True,
            note="Removed the unrecorded food",
            observation_id=active(a)["current"]["observation_id"],
        ).status_code
        == 200
    )
    action(
        a,
        "prepare_portion",
        personal=True,
        reference_id=ref["id"],
        observation_id=active(a)["current"]["observation_id"],
    )
    measured(a, 0, "remove")
    measured(a, 200)
    assert (
        action(
            a,
            "confirm_portion",
            personal=True,
            observation_id=active(a)["current"]["observation_id"],
        ).json()["error"]["code"]
        == "PLATE_MOVED_DURING_PORTION"
    )
    assert active(a)["provided_g"] == 0


def test_stale_readings_block_actions_and_restored_reading_recovers(api):
    a = api
    ready(a)
    ref = next(
        r
        for r in a["client"].get("/v1/food-references", headers=user(a)).json()["items"]
        if r["slug"] == "rice"
    )
    action(
        a,
        "prepare_portion",
        personal=True,
        reference_id=ref["id"],
        observation_id=active(a)["current"]["observation_id"],
    )
    measured(a, 200, "unstable")
    assert active(a)["current"]["net_g"] is None
    assert (
        action(a, "confirm_portion", personal=True, observation_id="none").json()["error"]["code"]
        == "DATA_NOT_READY"
    )
    state = measured(a, 200)
    old = state["current"]["observation_id"]
    measured(a, 200, "advance", seconds=6)
    assert active(a)["current"]["net_g"] is None
    assert action(a, "confirm_portion", personal=True, observation_id=old).status_code == 409
    state = measured(a, 200)
    assert (
        action(
            a, "confirm_portion", personal=True, observation_id=state["current"]["observation_id"]
        ).status_code
        == 200
    )
    assert active(a)["provided_g"] == 200


def test_anonymous_school_sample_plan_report_and_missing_remaining(api):
    a = api
    id = ready(a, "school")
    portion(a, "rice", 200, False)
    state = portion(a, "unknown", 50, False)
    assert state["sample_code"].startswith("S-") and "owner_id" not in state
    assert state["plan_comparison"]["status"] == "incomplete_food_groups"
    assert all(g["difference_g"] is None for g in state["plan_comparison"]["groups"])
    assert state["plan_comparison"]["plan"]["review_status"] == "illustrative_unreviewed"
    action(a, "finish_plating", observation_id=state["current"]["observation_id"])
    measured(a, 0, "remove")
    assert action(a, "complete", remaining_reason="pan_removed").status_code == 200
    report = (
        a["client"]
        .get(f"/v1/workspaces/{a['workspace']}/samples", headers=a["headers"]["manager"])
        .json()
    )
    assert report["summary"] == {
        "completed_samples": 1,
        "provided_g": 250,
        "remaining_observed_g": None,
        "samples_with_remaining": 0,
        "samples_without_remaining": 1,
    }
    assert a["client"].get(f"/v1/meals/{id}", headers=user(a)).status_code == 403
    csv = a["client"].get(
        f"/v1/workspaces/{a['workspace']}/samples.csv", headers=a["headers"]["manager"]
    )
    assert (
        csv.status_code == 200
        and "illustrative_unreviewed" in csv.text
        and "250,,pan_removed,partial,," in csv.text
    )
    assert (
        a["client"]
        .get(f"/v1/workspaces/{a['workspace']}/samples.csv", headers=a["headers"]["staff"])
        .status_code
        == 403
    )
    assert (
        a["client"]
        .get(f"/v1/workspaces/{a['other']}/samples", headers=a["headers"]["manager"])
        .status_code
        == 403
    )
    assert (
        a["client"]
        .get(
            f"/v1/workspaces/{a['workspace']}/samples?data_origin=hardware",
            headers=a["headers"]["manager"],
        )
        .json()["items"]
        == []
    )


def test_switch_blocks_open_meals_and_open_replenishment(api):
    a = api
    decision(a, low(a))
    a["client"].post(
        "/v1/device-console/session",
        json={"workspace_id": a["workspace"], "setup_key": a["settings"].console_key},
    )
    assert (
        post(
            a,
            "/v1/device-console/meals",
            {"expected_run_id": a["run"]["run_id"], "mode": "personal"},
        ).status_code
        == 409
    )


def test_console_auth_is_separate_and_closed_meals_do_not_accept_writes(api):
    a = api
    assert (
        a["client"].get("/v1/device-console/active", headers=a["headers"]["manager"]).status_code
        == 401
    )
    id = ready(a)
    state = portion(a, "rice", 200)
    assert action(a, "cancel", personal=True, note="End test recording").status_code == 200
    assert (
        post(
            a,
            f"/v1/meals/{id}/actions",
            {
                "action": "prepare_portion",
                "expected_version": state["version"] + 1,
                "reference_id": "unknown",
            },
            user(a),
        ).status_code
        == 409
    )
    assert (
        a["client"].get("/v1/me/meals", headers=user(a)).json()["items"][0]["state"] == "cancelled"
    )
    with TestClient(create_app(a["settings"])) as fresh:
        assert fresh.get(f"/v1/meals/{id}", headers=user(a)).json()["provided_g"] == 200
    a["client"].delete("/v1/device-console/session")
    assert a["client"].get("/v1/device-console/active").status_code == 401


def begin_rice(a):
    ref = next(
        r
        for r in a["client"].get("/v1/food-references", headers=user(a)).json()["items"]
        if r["slug"] == "rice"
    )
    assert (
        action(
            a,
            "prepare_portion",
            personal=True,
            reference_id=ref["id"],
            observation_id=active(a)["current"]["observation_id"],
        ).status_code
        == 200
    )


def packet(a, grams, offset=1, **changes):
    state = active(a)
    with Session(a["engine"]) as db:
        run = db.get(Run, state["run_id"])
        data = dict(
            observation_id=str(uuid4()),
            session_id=run.id,
            device_id=run.device_id,
            boot_id=run.boot_id,
            sequence=run.last_sequence + offset,
            observed_at=run.clock_at.isoformat(),
            net_g=grams,
            gross_g=grams + 500,
            tare_g=500,
            weight_quality="valid",
            pan_presence="present",
            calibration_version="demo-unverified",
            binding_revision=run.binding_revision,
        )
    data.update(changes)
    response = a["client"].post(
        "/v1/device/observations/batch", headers=a["machine"], json={"observations": [data]}
    )
    assert response.status_code == 200, response.text
    return data


@pytest.mark.parametrize(
    "change", [{"calibration_version": "new-v2"}, {"tare_g": 510, "gross_g": 710}]
)
def test_changed_calibration_or_tare_never_confirms_a_portion(api, change):
    ready(api)
    begin_rice(api)
    packet(api, 200, **change)
    state = active(api)
    assert state["prepared"]["validation_error"] == "CALIBRATION_CHANGED"
    assert (
        action(
            api, "confirm_portion", personal=True, observation_id=state["current"]["observation_id"]
        ).json()["error"]["code"]
        == "CALIBRATION_CHANGED"
    )
    assert active(api)["portions"] == []


def test_gap_and_late_packet_cannot_reconstruct_a_portion(api):
    ready(api)
    begin_rice(api)
    end = packet(api, 200, offset=2)
    late = {
        **end,
        "observation_id": str(uuid4()),
        "sequence": end["sequence"] - 1,
        "net_g": 100,
        "gross_g": 600,
    }
    assert (
        api["client"]
        .post(
            "/v1/device/observations/batch", headers=api["machine"], json={"observations": [late]}
        )
        .status_code
        == 200
    )
    state = active(api)
    assert state["prepared"]["validation_error"] == "MEASUREMENT_GAP"
    assert (
        action(api, "confirm_portion", personal=True, observation_id=end["observation_id"]).json()[
            "error"
        ]["code"]
        == "MEASUREMENT_GAP"
    )
    with Session(api["engine"]) as db:
        assert (
            db.scalar(select(Observation).where(Observation.id == late["observation_id"])).projected
            is False
        )


def test_stale_selection_and_manual_correction_keep_measured_grams(api):
    ready(api)
    begin_rice(api)
    old = measured(api, 200)["current"]["observation_id"]
    current = measured(api, 250)["current"]["observation_id"]
    assert (
        action(api, "confirm_portion", personal=True, observation_id=old).json()["error"]["code"]
        == "MEASUREMENT_CHANGED"
    )
    assert (
        action(
            api, "confirm_portion", personal=True, observation_id=current, amount_g=999
        ).status_code
        == 422
    )
    assert action(api, "confirm_portion", personal=True, observation_id=current).status_code == 200
    state = active(api)
    ref = next(
        r
        for r in api["client"].get("/v1/food-references", headers=user(api)).json()["items"]
        if r["slug"] == "banana"
    )
    args = {"portion_id": state["portions"][0]["id"], "reference_id": ref["id"]}
    assert action(api, "correct_food", personal=True, **args).status_code == 422
    assert (
        action(
            api,
            "correct_food",
            personal=True,
            note="Selected rice by mistake; actually peeled banana",
            **args,
        ).status_code
        == 200
    )
    corrected = active(api)
    assert corrected["provided_g"] == 250 and corrected["portions"][0]["version"] == 2
    assert corrected["history"][-1]["previous"]["reference"]["slug"] == "rice"
    assert corrected["nutrition"]["total"]["energy_kcal"] == 222.5


def test_plate_removal_between_items_blocks_finishing_at_same_total(api):
    ready(api)
    portion(api, "rice", 200)
    measured(api, 0, "remove")
    state = measured(api, 200)
    assert (
        action(
            api, "finish_plating", personal=True, observation_id=state["current"]["observation_id"]
        ).json()["error"]["code"]
        == "PLATE_MOVED_DURING_PORTION"
    )
    assert active(api)["state"] == "recording"


def test_extra_food_after_plating_requires_unknown_remaining(api):
    id = ready(api)
    state = portion(api, "rice", 200)
    assert (
        action(
            api, "finish_plating", personal=True, observation_id=state["current"]["observation_id"]
        ).status_code
        == 200
    )
    measured(api, 100)
    measured(api, 150)
    state = measured(api, 50)
    assert state["remaining_comparable"] is False
    assert (
        action(
            api, "complete", personal=True, observation_id=state["current"]["observation_id"]
        ).json()["error"]["code"]
        == "REMAINING_NOT_COMPARABLE"
    )
    assert (
        action(api, "complete", personal=True, remaining_reason="contents_changed").status_code
        == 200
    )
    meal = api["client"].get(f"/v1/meals/{id}", headers=user(api)).json()
    assert meal["remaining_g"] is None and meal["intake_g"] is None


def test_active_meal_blocks_both_switch_routes_and_cancel_allows_next(api):
    ready(api)
    state = active(api)
    r = post(
        api, "/v1/device-console/meals", {"expected_run_id": state["run_id"], "mode": "school"}
    )
    assert r.json()["error"]["code"] == "ACTIVE_MEAL_ON_STATION"
    assert (
        post(api, "/v1/dev/runs", {"workspace_id": api["workspace"]}, api["machine"]).status_code
        == 409
    )
    assert action(api, "cancel", personal=True, note="Finish QA sample").status_code == 200
    assert (
        post(
            api, "/v1/device-console/meals", {"expected_run_id": state["run_id"], "mode": "school"}
        ).status_code
        == 200
    )


def test_expired_request_and_inactive_applicant_are_not_approved(api):
    setup(api)
    measured(api, 0)
    action(api, "confirm_empty", observation_id=active(api)["current"]["observation_id"])
    assert (
        post(api, "/v1/pairing/requests", {"code": "SP-ABCDEF1234"}, user(api)).status_code == 422
    )
    req = post(
        api, "/v1/pairing/requests", {"code": active(api)["pairing"]["code"]}, user(api)
    ).json()["request_id"]
    with Session(api["engine"]) as db:
        db.get(User, api["ids"]["personal"]).active = False
        db.commit()
    assert (
        action(api, "approve_pairing", request_id=req).json()["error"]["code"]
        == "PAIR_REQUEST_CHANGED"
    )
    with Session(api["engine"]) as db:
        db.get(PairRequest, req).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert (
        action(api, "approve_pairing", request_id=req).json()["error"]["code"]
        == "PAIR_CODE_EXPIRED"
    )


def test_console_key_workspace_binding_and_expiry(api):
    client = api["client"]
    assert (
        client.post(
            "/v1/device-console/session",
            json={"workspace_id": api["other"], "setup_key": api["settings"].console_key},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/v1/device-console/session", json={"setup_key": api["settings"].console_key}
        ).status_code
        == 200
    )
    with Session(api["engine"]) as db:
        for row in db.scalars(select(ConsoleSession)):
            row.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/v1/device-console/active").status_code == 401


def test_known_school_plan_and_source_date_filters(api):
    ready(api, "school")
    for slug, amount in [("rice", 200), ("chicken", 100), ("broccoli", 150)]:
        state = portion(api, slug, amount, False)
    assert all(g["difference_g"] == 0 for g in state["plan_comparison"]["groups"])
    assert state["plan_comparison"]["nutritional_compliance"] is None
    action(api, "finish_plating", observation_id=state["current"]["observation_id"])
    measured(api, 300)
    action(api, "complete", observation_id=active(api)["current"]["observation_id"])
    path = f"/v1/workspaces/{api['workspace']}/samples"
    report = api["client"].get(path, headers=api["headers"]["manager"]).json()
    assert report["summary"]["remaining_observed_g"] == 300
    assert (
        api["client"]
        .get(path + "?date_from=2000-01-01&date_to=2000-01-02", headers=api["headers"]["manager"])
        .json()["items"]
        == []
    )
