"""One plate: local ownership confirmation and observed, non-overlapping portions."""

from copy import deepcopy
from datetime import timedelta
import hashlib
import secrets

from sqlalchemy import select, update

from .availability import has_open_orders
from .domain import ACTIVE_TASKS, DomainError, iso, quality, tasks_for, usable, utcnow
from .models import (
    FoodReference,
    Meal,
    MealHistory,
    Observation,
    PairRequest,
    Portion,
    Run,
    User,
    uid,
)
from .nutrition import DEMO_PLAN, groups_for, nutrition_for, plan_comparison, reference_view

ACTIVE_MEALS = {"setup", "pairing", "recording", "observing"}


def hash_code(value):
    return hashlib.sha256(value.encode()).hexdigest()


def portions_for(db, meal):
    return list(
        db.scalars(
            select(Portion).where(Portion.meal_id == meal.id).order_by(Portion.at, Portion.id)
        )
    )


def notify_owner(db, meal):
    if meal.owner_id:
        db.execute(
            update(User)
            .where(User.id == meal.owner_id)
            .values(activity_version=User.activity_version + 1)
        )


def audit(db, meal, run, action, actor, note="", previous=None, increment=True):
    if increment:
        meal.version += 1
    meal.updated_at = utcnow()
    run.snapshot_version += 1
    db.add(
        MealHistory(
            meal_id=meal.id,
            sequence=meal.version,
            action=action,
            actor_id=actor,
            at=meal.updated_at,
            note=note,
            previous=previous,
        )
    )
    notify_owner(db, meal)
    db.flush()


def station_can_switch(db, run):
    if not run:
        return
    meal = db.scalar(select(Meal).where(Meal.run_id == run.id))
    if meal and meal.state in ACTIVE_MEALS:
        raise DomainError("ACTIVE_MEAL_ON_STATION")
    if has_open_orders(db, run.id) or any(t.state in ACTIVE_TASKS for t in tasks_for(db, run)):
        raise DomainError("OPEN_ORDERS_OR_MEASUREMENT")


def start_meal(db, ws, mode):
    old = db.scalar(select(Run).where(Run.id == ws.active_run_id).with_for_update())
    station_can_switch(db, old)
    if old:
        old.state = "closed"
        old.paused = True
    now = utcnow()
    run = Run(
        id=uid(),
        workspace_id=ws.id,
        mode=mode,
        origin="simulated",
        clock_at=now,
        closes_at=now + timedelta(hours=4),
        food_name="个人餐食" if mode == "personal" else "匿名样本",
        food_name_en="Personal meal" if mode == "personal" else "Anonymous sample",
    )
    db.add(run)
    db.flush()
    meal = Meal(
        id=uid(),
        run_id=run.id,
        workspace_id=ws.id,
        state="setup",
        created_at=now,
        updated_at=now,
        sample_code=("S-" + secrets.token_hex(5).upper()) if mode == "school" else None,
        plan_snapshot=deepcopy(DEMO_PLAN) if mode == "school" else None,
    )
    db.add(meal)
    ws.active_run_id = run.id
    db.flush()
    audit(db, meal, run, "created", "console", increment=False)
    return meal, run


def latest_observation(db, run):
    if not usable(run):
        raise DomainError("DATA_NOT_READY")
    row = db.scalar(
        select(Observation).where(
            Observation.run_id == run.id,
            Observation.sequence == run.last_sequence,
            Observation.projected.is_(True),
        )
    )
    if not row:
        raise DomainError("DATA_NOT_READY")
    return row


def current_observation(db, run, requested):
    row = latest_observation(db, run)
    if requested != row.id:
        raise DomainError("MEASUREMENT_CHANGED")
    return row


def same_calibration(base, row):
    return base.boot_id == row.boot_id and all(
        base.payload[k] == row.payload[k]
        for k in ["tare_g", "calibration_version", "binding_revision"]
    )


def invalidate_request(db, meal, state):
    request = db.get(PairRequest, meal.pending_request_id) if meal.pending_request_id else None
    if request and request.state == "pending":
        request.state = state
        db.execute(
            update(User)
            .where(User.id == request.user_id)
            .values(activity_version=User.activity_version + 1)
        )
    meal.pending_request_id = None


def issue_pair_code(meal):
    meal.pair_code = "SPM-" + secrets.token_hex(6).upper()
    meal.pair_hash = hash_code(meal.pair_code)
    meal.pair_expires_at = utcnow() + timedelta(seconds=120)


def request_pairing(db, meal, run, actor):
    if (
        meal.state != "pairing"
        or meal.owner_id
        or not meal.pair_expires_at
        or meal.pair_expires_at <= utcnow()
    ):
        raise DomainError("PAIR_CODE_EXPIRED")
    if run.state != "active":
        raise DomainError("SESSION_CHANGED")
    if meal.pending_request_id:
        raise DomainError("PAIRING_BUSY")
    req = PairRequest(
        id=uid(),
        meal_id=meal.id,
        user_id=actor.id,
        state="pending",
        check_code=f"{secrets.randbelow(10000):04d}",
        expires_at=meal.pair_expires_at,
        created_at=utcnow(),
    )
    db.add(req)
    meal.pending_request_id = req.id
    audit(db, meal, run, "pairing_requested", actor.id)
    db.execute(
        update(User).where(User.id == actor.id).values(activity_version=User.activity_version + 1)
    )
    return req


def pair_view(db, request, device=False):
    status = (
        "expired"
        if request.state == "pending" and request.expires_at <= utcnow()
        else request.state
    )
    result = {
        "id": request.id,
        "state": status,
        "check_code": request.check_code,
        "expires_at": iso(request.expires_at),
        "meal_id": request.meal_id if status == "approved" else None,
    }
    if device:
        result["applicant_name"] = db.get(User, request.user_id).name
    return result


def reference(db, id):
    row = db.get(FoodReference, id) if id else None
    if not row or not row.active:
        raise DomainError("REFERENCE_UNAVAILABLE")
    return row


def validate_window(db, run, start, end):
    rows = list(
        db.scalars(
            select(Observation)
            .where(
                Observation.run_id == run.id,
                Observation.sequence > start.sequence,
                Observation.sequence <= end.sequence,
                Observation.projected.is_(True),
            )
            .order_by(Observation.sequence)
        )
    )
    if [r.sequence for r in rows] != list(range(start.sequence + 1, end.sequence + 1)):
        raise DomainError("MEASUREMENT_GAP")
    previous = start.payload["net_g"]
    for row in rows:
        if not same_calibration(start, row):
            raise DomainError("CALIBRATION_CHANGED")
        if row.payload["pan_presence"] != "present":
            raise DomainError("PLATE_MOVED_DURING_PORTION")
        if row.payload["weight_quality"] == "invalid":
            raise DomainError("MEASUREMENT_GAP")
        if row.payload["weight_quality"] == "valid":
            if row.payload["net_g"] < previous:
                raise DomainError("PORTION_WEIGHT_DECREASED")
            previous = row.payload["net_g"]
    if not rows or end.payload["net_g"] <= start.payload["net_g"]:
        raise DomainError("NO_POSITIVE_PORTION")


def validate_idle_window(db, meal, run, end):
    """A matching total alone cannot join observations across an unobserved plate swap."""
    anchors = [db.get(Observation, meal.baseline_observation_id)]
    anchors.extend(db.get(Observation, p.end_observation_id) for p in portions_for(db, meal))
    start = max((r for r in anchors if r), key=lambda r: r.sequence)
    rows = list(
        db.scalars(
            select(Observation)
            .where(
                Observation.run_id == run.id,
                Observation.projected.is_(True),
                Observation.sequence > start.sequence,
                Observation.sequence <= end.sequence,
            )
            .order_by(Observation.sequence)
        )
    )
    if [r.sequence for r in rows] != list(range(start.sequence + 1, end.sequence + 1)):
        raise DomainError("MEASUREMENT_GAP")
    for row in rows:
        if not same_calibration(start, row):
            raise DomainError("CALIBRATION_CHANGED")
        if row.payload["pan_presence"] != "present":
            raise DomainError("PLATE_MOVED_DURING_PORTION")
        if row.payload["weight_quality"] == "invalid":
            raise DomainError("MEASUREMENT_GAP")
        if (
            row.payload["weight_quality"] == "valid"
            and row.payload["net_g"] != start.payload["net_g"]
        ):
            raise DomainError("UNRECORDED_WEIGHT_CHANGE")


def remaining_is_comparable(db, meal, run, end, provided):
    start = db.get(Observation, meal.served_observation_id)
    if not start or not same_calibration(start, end) or not 0 <= end.payload["net_g"] <= provided:
        return False
    rows = list(
        db.scalars(
            select(Observation)
            .where(
                Observation.run_id == run.id,
                Observation.sequence > start.sequence,
                Observation.sequence <= end.sequence,
                Observation.projected.is_(True),
            )
            .order_by(Observation.sequence)
        )
    )
    if [r.sequence for r in rows] != list(range(start.sequence + 1, end.sequence + 1)):
        return False
    previous = start.payload["net_g"]
    for row in rows:
        if not same_calibration(start, row) or row.payload["pan_presence"] != "present":
            return False
        if row.payload["weight_quality"] == "invalid":
            return False
        if row.payload["weight_quality"] == "valid":
            if row.payload["net_g"] > previous:
                return False
            previous = row.payload["net_g"]
    return True


def act_meal(db, meal, run, data, actor_id, *, device=False):
    if data.expected_version != meal.version:
        raise DomainError("VERSION_CONFLICT")
    if meal.state not in ACTIVE_MEALS or run.state != "active":
        raise DomainError("MEAL_CLOSED")
    action = data.action
    if (
        action in {"confirm_empty", "approve_pairing", "reject_pairing", "rotate_code"}
        and not device
    ):
        raise DomainError("DEVICE_CONFIRMATION_REQUIRED", 403)
    previous = None
    if action == "confirm_empty":
        if meal.state != "setup":
            raise DomainError("INVALID_TRANSITION")
        row = current_observation(db, run, data.observation_id)
        if row.payload["net_g"] != 0:
            raise DomainError("EMPTY_PLATE_REQUIRED")
        meal.baseline_observation_id = row.id
        meal.state = "pairing" if run.mode == "personal" else "recording"
        if run.mode == "personal":
            issue_pair_code(meal)
    elif action in {"approve_pairing", "reject_pairing", "rotate_code"}:
        if meal.state != "pairing" or meal.owner_id:
            raise DomainError("INVALID_TRANSITION")
        if action == "rotate_code":
            row = latest_observation(db, run)
            if row.payload["net_g"] != 0:
                raise DomainError("EMPTY_PLATE_REQUIRED")
            meal.baseline_observation_id = row.id
            invalidate_request(db, meal, "rejected")
            issue_pair_code(meal)
        else:
            req = db.get(PairRequest, data.request_id) if data.request_id else None
            if not req or req.id != meal.pending_request_id or req.state != "pending":
                raise DomainError("PAIR_REQUEST_CHANGED")
            if req.expires_at <= utcnow():
                raise DomainError("PAIR_CODE_EXPIRED")
            if action == "approve_pairing":
                row = latest_observation(db, run)
                base = db.get(Observation, meal.baseline_observation_id)
                if row.payload["net_g"] != 0 or not base or not same_calibration(base, row):
                    raise DomainError("EMPTY_PLATE_REQUIRED")
                if not db.get(User, req.user_id).active:
                    raise DomainError("PAIR_REQUEST_CHANGED")
                meal.owner_id, meal.state = req.user_id, "recording"
                req.state = "approved"
                meal.pending_request_id = None
            else:
                invalidate_request(db, meal, "rejected")
            meal.pair_code = meal.pair_hash = None
            meal.pair_expires_at = None
    elif action == "prepare_portion":
        if meal.state != "recording" or meal.prepared_reference_id:
            raise DomainError("PORTION_ALREADY_OPEN")
        ref = reference(db, data.reference_id)
        row = current_observation(db, run, data.observation_id)
        base = db.get(Observation, meal.baseline_observation_id)
        if not base or not same_calibration(base, row):
            raise DomainError("CALIBRATION_CHANGED")
        if row.payload["net_g"] != sum(p.amount_g for p in portions_for(db, meal)):
            raise DomainError("UNRECORDED_WEIGHT_CHANGE")
        validate_idle_window(db, meal, run, row)
        meal.prepared_reference_id, meal.start_observation_id = ref.id, row.id
    elif action == "confirm_portion":
        if meal.state != "recording" or not meal.prepared_reference_id:
            raise DomainError("NO_OPEN_PORTION")
        start = db.get(Observation, meal.start_observation_id)
        end = current_observation(db, run, data.observation_id)
        validate_window(db, run, start, end)
        if db.scalar(select(Portion.id).where(Portion.end_observation_id == end.id)):
            raise DomainError("MEASUREMENT_ALREADY_RECORDED")
        ref = db.get(FoodReference, meal.prepared_reference_id)
        db.add(
            Portion(
                meal_id=meal.id,
                reference_id=ref.id,
                reference_snapshot=deepcopy(reference_view(ref)),
                amount_g=end.payload["net_g"] - start.payload["net_g"],
                start_observation_id=start.id,
                end_observation_id=end.id,
                at=utcnow(),
            )
        )
        meal.prepared_reference_id = meal.start_observation_id = None
    elif action == "cancel_portion":
        if meal.state != "recording" or not meal.prepared_reference_id:
            raise DomainError("NO_OPEN_PORTION")
        if not data.note.strip():
            raise DomainError("REASON_REQUIRED", 422)
        start = db.get(Observation, meal.start_observation_id)
        end = current_observation(db, run, data.observation_id)
        if end.payload["net_g"] != start.payload["net_g"] or not same_calibration(start, end):
            raise DomainError("RESTORE_PORTION_BASELINE")
        # Explicit restoration with an audit reason establishes a new observed boundary.
        meal.baseline_observation_id = end.id
        meal.prepared_reference_id = meal.start_observation_id = None
    elif action == "correct_food":
        if meal.state != "recording" or meal.prepared_reference_id:
            raise DomainError("INVALID_TRANSITION")
        if not data.note.strip():
            raise DomainError("REASON_REQUIRED", 422)
        portion = db.get(Portion, data.portion_id) if data.portion_id else None
        if not portion or portion.meal_id != meal.id:
            raise DomainError("NOT_FOUND", 404)
        ref = reference(db, data.reference_id)
        previous = {
            "portion_id": portion.id,
            "reference": portion.reference_snapshot,
            "version": portion.version,
            "amount_g": portion.amount_g,
        }
        portion.reference_id, portion.reference_snapshot = ref.id, deepcopy(reference_view(ref))
        portion.version += 1
        portion.entry_source = "manual_correction"
    elif action == "finish_plating":
        portions = portions_for(db, meal)
        if meal.state != "recording" or meal.prepared_reference_id or not portions:
            raise DomainError("FINISH_PORTIONS_FIRST")
        row = current_observation(db, run, data.observation_id)
        base = db.get(Observation, meal.baseline_observation_id)
        if not base or not same_calibration(base, row):
            raise DomainError("CALIBRATION_CHANGED")
        if row.payload["net_g"] != sum(p.amount_g for p in portions):
            raise DomainError("UNRECORDED_WEIGHT_CHANGE")
        validate_idle_window(db, meal, run, row)
        meal.served_observation_id = row.id
        meal.state = "observing"
    elif action == "complete":
        if meal.state != "observing":
            raise DomainError("INVALID_TRANSITION")
        if data.remaining_reason:
            if data.observation_id:
                raise DomainError("VALIDATION_FAILED", 422)
            meal.remaining_reason = data.remaining_reason
        else:
            row = current_observation(db, run, data.observation_id)
            if not remaining_is_comparable(
                db, meal, run, row, sum(p.amount_g for p in portions_for(db, meal))
            ):
                raise DomainError("REMAINING_NOT_COMPARABLE")
            meal.remaining_g, meal.remaining_observation_id = row.payload["net_g"], row.id
            meal.remaining_reason = "observed_total"
        meal.state, meal.completed_at = "completed", utcnow()
        run.state = "closed"
    elif action == "cancel":
        if not data.note.strip():
            raise DomainError("REASON_REQUIRED", 422)
        invalidate_request(db, meal, "rejected")
        meal.pair_code = meal.pair_hash = None
        meal.prepared_reference_id = meal.start_observation_id = None
        meal.state, meal.completed_at = "cancelled", utcnow()
        run.state = "closed"
    else:
        raise DomainError("INVALID_TRANSITION")
    audit(db, meal, run, action, actor_id, data.note, previous)


def meal_view(db, meal, run, *, device=False):
    portions = portions_for(db, meal)
    provided = sum(p.amount_g for p in portions)
    current = None
    row = None
    if meal.state in ACTIVE_MEALS:
        connection, freshness = quality(run)
        row = db.scalar(
            select(Observation).where(
                Observation.run_id == run.id,
                Observation.sequence == run.last_sequence,
                Observation.projected.is_(True),
            )
        )
        current = {
            "net_g": run.net_g if usable(run) else None,
            "last_valid_g": run.last_valid_g,
            "observed_at": iso(run.observed_at),
            "last_valid_at": iso(run.last_valid_at),
            "observation_id": row.id if row and usable(run) else None,
            "connectivity": connection,
            "freshness": freshness,
            "measurement_status": run.measurement_status,
            "snapshot_version": run.snapshot_version,
        }
    prepared = None
    if meal.prepared_reference_id:
        start = db.get(Observation, meal.start_observation_id)
        validation_error = None
        try:
            if not row or not usable(run):
                raise DomainError("DATA_NOT_READY")
            validate_window(db, run, start, row)
        except DomainError as problem:
            validation_error = problem.code
        prepared = {
            "reference": reference_view(db.get(FoodReference, meal.prepared_reference_id)),
            "baseline_g": start.payload["net_g"],
            "candidate_g": run.net_g - start.payload["net_g"] if usable(run) else None,
            "validation_error": validation_error,
        }
    history = list(
        db.scalars(
            select(MealHistory).where(MealHistory.meal_id == meal.id).order_by(MealHistory.sequence)
        )
    )
    result = {
        "id": meal.id,
        "run_id": run.id,
        "workspace_id": meal.workspace_id,
        "mode": run.mode,
        "state": meal.state,
        "version": meal.version,
        "sample_code": meal.sample_code,
        "created_at": iso(meal.created_at),
        "updated_at": iso(meal.updated_at),
        "completed_at": iso(meal.completed_at),
        "data_origin": run.origin,
        "current": current,
        "prepared": prepared,
        "provided_g": provided,
        "remaining_g": meal.remaining_g,
        "remaining_reason": meal.remaining_reason,
        "remaining_comparable": remaining_is_comparable(db, meal, run, row, provided)
        if meal.state == "observing" and row and usable(run)
        else False,
        "intake_g": None,
        "nutrition": nutrition_for(portions),
        "food_groups_g": groups_for(portions),
        "plan_comparison": plan_comparison(meal.plan_snapshot, portions),
        "portions": [
            {
                "id": p.id,
                "amount_g": p.amount_g,
                "reference": p.reference_snapshot,
                "reference_id": p.reference_id,
                "entry_source": p.entry_source,
                "version": p.version,
                "at": iso(p.at),
            }
            for p in portions
        ],
        "history": [
            {
                "id": h.id,
                "action": h.action,
                "at": iso(h.at),
                "note": h.note,
                "previous": h.previous,
            }
            for h in history
        ],
    }
    if device:
        result["pairing"] = (
            {"code": meal.pair_code, "expires_at": iso(meal.pair_expires_at)}
            if meal.state == "pairing"
            else None
        )
        req = db.get(PairRequest, meal.pending_request_id) if meal.pending_request_id else None
        result["pair_request"] = pair_view(db, req, True) if req else None
    return result
