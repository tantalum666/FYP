"""Single-station state machine; quantities change only through valid observations."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import Event, Meal, Observation, Operation, Recommendation, Run, Task, User, uid
from .schemas import Decision, ObservationInput, TaskAction
from .availability import has_fulfillment_window, reserved_grams

ACTIVE_TASKS = {"planned", "in_progress", "ready", "awaiting_reconciliation", "needs_review"}
INCOMING_TASKS = {"planned", "in_progress", "ready"}


class DomainError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(at: datetime | None):
    return at.isoformat() if at else None


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def tasks_for(db: Session, run: Run) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.run_id == run.id).order_by(Task.created_at, Task.id)))


def quality(run: Run) -> tuple[str, str]:
    clock = run.clock_at if run.origin != "hardware" else utcnow()
    online = run.heartbeat_at is not None and (clock - run.heartbeat_at).total_seconds() <= 15
    fresh = run.last_valid_at is not None and (clock - run.last_valid_at).total_seconds() <= 5
    return ("online" if online else "offline", "fresh" if fresh else "stale")


def usable(run: Run) -> bool:
    return (run.state == "active" and not run.paused and run.food_binding == "confirmed"
            and run.measurement_status == "valid" and quality(run) == ("online", "fresh"))


def event(db: Session, run: Run, kind: str, *, delta=None, observation=None,
          actor=None, task=None, detail="") -> Event:
    e = Event(id=uid(), run_id=run.id, sequence=run.snapshot_version + 1, kind=kind, at=run.clock_at, delta_g=delta,
              net_g=run.net_g, binding_revision=run.binding_revision,
              observation_id=observation, actor_id=actor, task_id=task, detail=detail)
    db.add(e)
    run.snapshot_version += 1
    return e


def suggestion_context(db: Session, run: Run) -> tuple[str, int]:
    if run.mode != "foodservice":
        return "MEAL_MODE_ACTIVE", 0
    tasks = tasks_for(db, run)
    incoming = sum(t.planned_g for t in tasks if t.state in INCOMING_TASKS)
    if not usable(run):
        return "DATA_NOT_READY", incoming
    if any(t.state in {"awaiting_reconciliation", "needs_review"} for t in tasks):
        return "RECONCILIATION_REQUIRED", incoming
    if has_fulfillment_window(db, run.id):
        return "ORDER_RECONCILIATION_REQUIRED", incoming
    if (run.closes_at - run.clock_at).total_seconds() <= run.lead_seconds:
        return "SERVICE_ENDING", incoming
    if (run.net_g or 0) - reserved_grams(db, run.id) + incoming > run.threshold_g:
        return "INCOMING_SUFFICIENT" if incoming else "ENOUGH_REMAINING", incoming
    return "BELOW_THRESHOLD", incoming


def refresh_recommendation(db: Session, run: Run):
    reason, _ = suggestion_context(db, run)
    rows = list(db.scalars(select(Recommendation).where(
        Recommendation.run_id == run.id).order_by(Recommendation.created_at.desc())))
    for rec in rows:
        if rec.state == "pending" and (rec.binding_revision != run.binding_revision
                                      or rec.expires_at <= run.clock_at
                                      or reason != "BELOW_THRESHOLD"):
            rec.state = "expired" if rec.expires_at <= run.clock_at else "superseded"
            rec.version += 1
    if reason != "BELOW_THRESHOLD" or any(r.state == "pending" for r in rows):
        return
    if rows and rows[0].state == "rejected" and run.clock_at - rows[0].created_at < timedelta(minutes=5):
        return
    rec = Recommendation(id=uid(), run_id=run.id, binding_revision=run.binding_revision,
                         version=1, state="pending", amount_g=run.batch_g,
                         basis_g=max(0, (run.net_g or 0) - reserved_grams(db, run.id)),
                         method=run.baseline_method, created_at=run.clock_at,
                         expires_at=run.clock_at + timedelta(minutes=5), reason=reason)
    db.add(rec)
    event(db, run, "recommendation_created", detail=rec.id)


def ingest(db: Session, run: Run, item: ObservationInput) -> str:
    payload = item.model_dump(mode="json")
    hashed = digest(payload)
    existing = db.scalar(select(Observation).where(Observation.id == item.observation_id))
    if existing:
        if existing.run_id == run.id and existing.content_hash == hashed:
            return "duplicate"
        raise DomainError("OBSERVATION_ID_CONFLICT")
    if run.state != "active":
        raise DomainError("SESSION_CLOSED")
    if item.device_id != run.device_id or item.session_id != run.id or item.boot_id != run.boot_id:
        raise DomainError("DEVICE_SESSION_MISMATCH", 422)
    if item.binding_revision != run.binding_revision:
        raise DomainError("BINDING_CHANGED", 409)
    if item.observed_at.tzinfo is None:
        raise DomainError("TIMEZONE_REQUIRED", 422)
    if item.observed_at > run.clock_at + timedelta(seconds=1):
        raise DomainError("FUTURE_OBSERVATION", 422)
    if item.gross_g - item.tare_g != item.net_g:
        raise DomainError("WEIGHT_INCONSISTENT", 422)
    seq = db.scalar(select(Observation).where(Observation.run_id == run.id,
                    Observation.boot_id == item.boot_id, Observation.sequence == item.sequence))
    if seq:
        raise DomainError("SEQUENCE_CONFLICT", 409)
    projected = item.sequence > run.last_sequence and (
        run.observed_at is None or item.observed_at >= run.observed_at)
    db.add(Observation(id=item.observation_id, run_id=run.id, boot_id=item.boot_id,
                       sequence=item.sequence, observed_at=item.observed_at, received_at=utcnow(),
                       payload=payload, content_hash=hashed, projected=projected))
    if not projected:
        return "accepted_historical"
    old_status, previous = run.measurement_status, run.last_valid_g
    run.last_sequence = item.sequence
    run.observed_at = item.observed_at
    run.heartbeat_at = item.observed_at
    run.vision_status = item.vision_status
    status = "absent" if item.pan_presence == "absent" else item.weight_quality
    if status == "valid" and not 0 <= item.net_g <= 5000:
        status = "invalid"
    run.measurement_status = status
    run.net_g = item.net_g if status == "valid" else None
    if status == "valid":
        run.last_valid_g, run.last_valid_at = item.net_g, item.observed_at
        if previous is None:
            run.provided_g += item.net_g
            event(db, run, "initial_supply", delta=item.net_g, observation=item.observation_id)
        elif old_status == "valid":
            delta = item.net_g - previous
            if delta:
                if delta > 0:
                    run.provided_g += delta
                else:
                    run.removed_g -= delta
                event(db, run, "food_added" if delta > 0 else "food_removed",
                      delta=delta, observation=item.observation_id)
        else:
            event(db, run, "measurement_resumed", observation=item.observation_id,
                  detail="Quantity changes across an invalid interval are not allocated.")
    elif old_status != status:
        event(db, run, "pan_removed" if status == "absent" else "measurement_" + status,
              observation=item.observation_id)
    run.snapshot_version += 1
    db.flush()
    refresh_recommendation(db, run)
    if run.mode == "personal":
        meal = db.scalar(select(Meal).where(Meal.run_id == run.id))
        if meal and meal.owner_id:
            db.execute(update(User).where(User.id == meal.owner_id)
                       .values(activity_version=User.activity_version + 1))
    return "accepted"


def operation_cached(db, actor, context, key, fingerprint):
    op = db.scalar(select(Operation).where(Operation.actor_id == actor,
                   Operation.context_id == context, Operation.key == key))
    if op and op.fingerprint != fingerprint:
        raise DomainError("IDEMPOTENCY_CONFLICT")
    return op.result if op else None


def remember(db, actor, context, key, fingerprint, result):
    result = {**result, "operation_id": key, "server_time": iso(utcnow())}
    db.add(Operation(actor_id=actor, context_id=context, key=key,
                     fingerprint=fingerprint, result=result, created_at=utcnow()))
    return result


def decide(db: Session, run: Run, rec: Recommendation, data: Decision, actor: User) -> dict:
    if rec.state != "pending":
        raise DomainError("RECOMMENDATION_ALREADY_DECIDED")
    if rec.version != data.expected_version:
        raise DomainError("VERSION_CONFLICT")
    if rec.binding_revision != run.binding_revision or rec.expires_at <= run.clock_at:
        raise DomainError("RECOMMENDATION_OUTDATED")
    reason, _ = suggestion_context(db, run)
    if reason != "BELOW_THRESHOLD":
        raise DomainError("RECOMMENDATION_OUTDATED")
    if data.decision in {"adjust", "reject"} and not data.reason_code:
        raise DomainError("REASON_REQUIRED", 422)
    task_id = None
    if data.decision == "reject":
        rec.state = "rejected"
    else:
        amount = rec.amount_g if data.decision == "accept" else data.accepted_g
        if amount is None or amount < 100 or amount % 50:
            raise DomainError("INVALID_BATCH_SIZE", 422)
        task_id = uid()
        db.add(Task(id=task_id, run_id=run.id, recommendation_id=rec.id,
                    binding_revision=run.binding_revision, planned_g=amount, state="planned",
                    version=1, created_at=run.clock_at, updated_at=run.clock_at))
        rec.state = "accepted"
    rec.decision_reason = data.reason_code
    rec.version += 1
    event(db, run, "recommendation_" + rec.state, actor=actor.id, task=task_id)
    return {"recommendation_id": rec.id, "decision": rec.state,
            "task_id": task_id, "resource_version": rec.version}


def act_on_task(db: Session, run: Run, task: Task, data: TaskAction, actor: User, role: str):
    if data.expected_version != task.version:
        raise DomainError("VERSION_CONFLICT")
    if task.assignee_id not in {None, actor.id} and role != "manager":
        raise DomainError("ASSIGNED_TO_ANOTHER_STAFF", 403)
    transitions = {("planned", "start"): "in_progress", ("in_progress", "mark_ready"): "ready",
                   ("ready", "begin_replenishment"): "awaiting_reconciliation",
                   ("awaiting_reconciliation", "request_review"): "needs_review",
                   ("needs_review", "close_unverified"): "closed_unverified"}
    if data.action == "cancel" and task.state in INCOMING_TASKS:
        next_state = "cancelled"
    elif data.action == "confirm_replenishment" and task.state in {"awaiting_reconciliation", "needs_review"}:
        if task.state == "needs_review" and role != "manager":
            raise DomainError("MANAGER_REQUIRED", 403)
        e = db.get(Event, data.physical_event_id) if data.physical_event_id else None
        observation = db.get(Observation, e.observation_id) if e and e.observation_id else None
        if not (e and observation and e.run_id == run.id and e.kind == "food_added"
                and e.binding_revision == task.binding_revision == run.binding_revision
                and task.reconciliation_sequence is not None
                and observation.sequence > task.reconciliation_sequence
                and observation.projected and e.delta_g and e.delta_g > 0):
            raise DomainError("NO_VALID_REPLENISHMENT_EVENT")
        if db.scalar(select(Task.id).where(Task.event_id == e.id)):
            raise DomainError("EVENT_ALREADY_USED")
        task.event_id, task.actual_added_g = e.id, e.delta_g
        next_state = "completed"
    else:
        next_state = transitions.get((task.state, data.action))
    if not next_state:
        raise DomainError("INVALID_TRANSITION")
    if data.action in {"cancel", "request_review", "close_unverified"} and not data.note.strip():
        raise DomainError("REASON_REQUIRED", 422)
    if data.action == "close_unverified" and role != "manager":
        raise DomainError("MANAGER_REQUIRED", 403)
    if data.action not in {"cancel", "request_review", "close_unverified"} and task.binding_revision != run.binding_revision:
        raise DomainError("BINDING_CHANGED")
    if data.action == "start":
        task.assignee_id = actor.id
    if data.action == "begin_replenishment":
        if has_fulfillment_window(db, run.id):
            raise DomainError("FULFILLMENT_WINDOW_BUSY")
        if not usable(run):
            raise DomainError("DATA_NOT_READY")
        task.reconciliation_started_at = run.clock_at
        task.reconciliation_sequence = run.last_sequence
    task.state, task.updated_at = next_state, run.clock_at
    task.version += 1
    task.note = data.note
    event(db, run, "task_" + next_state, actor=actor.id, task=task.id, detail=data.note)
    db.flush()
    refresh_recommendation(db, run)
    return {"task_id": task.id, "state": task.state, "resource_version": task.version,
            "actual_added_g": task.actual_added_g}


def task_view(db, task):
    owner = db.get(User, task.assignee_id) if task.assignee_id else None
    eligible = []
    run = db.get(Run, task.run_id)
    if (task.state in {"awaiting_reconciliation", "needs_review"}
            and task.reconciliation_sequence is not None
            and task.binding_revision == run.binding_revision):
        used = select(Task.event_id).where(Task.event_id.is_not(None))
        candidates = db.scalars(select(Event).join(Observation, Event.observation_id == Observation.id)
            .where(Event.run_id == task.run_id, Event.kind == "food_added",
                   Event.binding_revision == task.binding_revision, Event.delta_g > 0,
                   Observation.sequence > task.reconciliation_sequence, Observation.projected.is_(True),
                   Event.id.not_in(used)).order_by(Observation.sequence.desc()))
        eligible = [event_view(e, run.origin) for e in candidates]
    return {"id": task.id, "run_id": task.run_id, "recommendation_id": task.recommendation_id,
            "state": task.state, "version": task.version, "planned_g": task.planned_g,
            "actual_added_g": task.actual_added_g, "assignee_id": task.assignee_id,
            "assignee_name": owner.name if owner else None, "created_at": iso(task.created_at),
            "updated_at": iso(task.updated_at), "reconciliation_sequence": task.reconciliation_sequence,
            "verification": "confirmed_event" if task.event_id else "unverified", "note": task.note,
            "eligible_events": eligible}


def rec_view(rec):
    return {"id": rec.id, "state": rec.state, "version": rec.version, "amount_g": rec.amount_g,
            "basis_g": rec.basis_g, "method": rec.method, "reason": rec.reason,
            "expires_at": iso(rec.expires_at), "binding_revision": rec.binding_revision}


def event_view(e, origin):
    return {"id": e.id, "sequence": e.sequence, "kind": e.kind, "at": iso(e.at), "delta_g": e.delta_g,
            "net_g": e.net_g, "task_id": e.task_id, "actor_id": e.actor_id,
            "detail": e.detail, "data_origin": origin}


def snapshot(db: Session, run: Run):
    connectivity, freshness = quality(run)
    reason, incoming = suggestion_context(db, run)
    reserved = reserved_grams(db, run.id)
    recs = list(db.scalars(select(Recommendation).where(Recommendation.run_id == run.id,
            Recommendation.state == "pending").order_by(Recommendation.created_at.desc())))
    valid_recs = [r for r in recs if r.expires_at > run.clock_at and r.binding_revision == run.binding_revision]
    observations = list(db.scalars(select(Observation).where(Observation.run_id == run.id,
        Observation.projected.is_(True)).order_by(Observation.sequence.desc()).limit(30)))[::-1]
    history = [{"id": o.id, "at": iso(o.observed_at),
                "net_g": o.payload["net_g"] if o.payload["weight_quality"] == "valid"
                and o.payload["pan_presence"] == "present" and 0 <= o.payload["net_g"] <= 5000 else None}
               for o in observations]
    events = list(db.scalars(select(Event).where(Event.run_id == run.id)
                 .order_by(Event.sequence.desc()).limit(100)))
    availability = "unknown"
    if usable(run):
        availability = "replenishing" if incoming else ("low" if (run.net_g or 0) <= run.threshold_g else "available")
    result = {"station_id": run.station_id, "session_id": run.id, "run_id": run.id,
            "device_id": run.device_id, "boot_id": run.boot_id, "workspace_id": run.workspace_id,
            "station_name": "餐位 01", "food_name": run.food_name, "food_name_en": run.food_name_en,
            "food_id": run.food_id, "binding_revision": run.binding_revision,
            "snapshot_version": run.snapshot_version, "data_origin": run.origin, "mode": run.mode,
            "clock_at": iso(run.clock_at), "closes_at": iso(run.closes_at),
            "observed_at": iso(run.observed_at), "last_valid_at": iso(run.last_valid_at),
            "connectivity": connectivity, "freshness": freshness, "measurement_status": run.measurement_status,
            "food_binding": run.food_binding, "vision_status": run.vision_status,
            "recognition_source": "manual", "net_g": run.net_g, "last_valid_g": run.last_valid_g,
            "incoming_g": incoming, "reserved_g": reserved, "safety_buffer_g": 0,
            "available_to_promise_g": max(0, run.net_g - reserved) if usable(run) else None,
            "service_type": run.service_type,
            "availability": availability, "threshold_g": run.threshold_g, "batch_g": run.batch_g,
            "suggestion_reason": reason, "recommendation": rec_view(valid_recs[0]) if valid_recs else None,
            "tasks": [task_view(db, t) for t in tasks_for(db, run)], "history": history,
            "events": [event_view(e, run.origin) for e in events],
            "provided_g": run.provided_g, "removed_g": run.removed_g,
            "paused": run.paused, "state": run.state, "last_sequence": run.last_sequence}
    if run.mode == "personal":
        result.update(net_g=None, last_valid_g=None, observed_at=None, last_valid_at=None,
                      provided_g=None, removed_g=None, available_to_promise_g=None,
                      food_name="个人餐食使用中", food_name_en="Personal meal session",
                      food_id=None, food_binding="private", measurement_status="private",
                      vision_status="unavailable", recognition_source="unavailable",
                      history=[], events=[], tasks=[], recommendation=None)
    return result
