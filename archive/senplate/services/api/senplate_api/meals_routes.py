"""Owner-only personal meals, local station confirmation, anonymous school samples."""

import csv
from datetime import date, datetime, time as datetime_time, timedelta
import io
import secrets
import time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import Cookie, Depends, Header, Response
import segno
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .domain import DomainError, digest, ingest, iso, operation_cached, remember, utcnow
from .meal_schemas import ConsoleLogin, ConsoleSimulation, MealAction, MealStart, PairApply
from .meals_domain import (
    ACTIVE_MEALS,
    act_meal,
    hash_code,
    meal_view,
    notify_owner,
    pair_view,
    request_pairing,
    start_meal,
)
from .models import ConsoleSession, FoodReference, Meal, PairRequest, Run, User, Workspace, uid
from .nutrition import reference_view
from .schemas import ObservationInput


def register_meal_routes(app, db_dependency, user_dependency, authorize, key_for):
    DB = Annotated[Session, Depends(db_dependency)]
    Actor = Annotated[User, Depends(user_dependency)]
    Context = Annotated[str | None, Header(alias="X-Context-ID")]
    Key = Annotated[str | None, Header(alias="Idempotency-Key")]
    cfg = app.state.settings
    attempts = {}

    def throttle(identifier, limit=12):
        recent = [t for t in attempts.get(identifier, []) if time.monotonic() - t < 60]
        if len(recent) >= limit:
            raise DomainError("TRY_LATER", 429)
        attempts[identifier] = [*recent, time.monotonic()]

    def op_lock(db, actor, context, key):
        # Personal operations can target different workspaces; serialize the same key globally.
        lock = int.from_bytes(bytes.fromhex(digest([actor, context, key]))[:8], signed=True)
        db.execute(select(func.pg_advisory_xact_lock(lock)))

    def personal(context):
        if context != "personal":
            raise DomainError("PERSONAL_CONTEXT_REQUIRED", 403)

    def console(db: DB, senplate_console: Annotated[str | None, Cookie()] = None):
        row = db.get(ConsoleSession, hash_code(senplate_console)) if senplate_console else None
        if not row or row.expires_at <= utcnow():
            raise DomainError("CONSOLE_AUTH_REQUIRED", 401)
        return row

    Console = Annotated[ConsoleSession, Depends(console)]

    def current(db, workspace_id, lock=False):
        query = select(Workspace).where(Workspace.id == workspace_id)
        ws = db.scalar(query.with_for_update() if lock else query)
        if not ws:
            raise DomainError("NOT_FOUND", 404)
        run_query = select(Run).where(Run.id == ws.active_run_id)
        run = db.scalar(run_query.with_for_update() if lock else run_query)
        return ws, run

    def owned_meal(db, id, actor, context, write=False):
        meal = db.get(Meal, id)
        if not meal:
            raise DomainError("NOT_FOUND", 404)
        run = db.get(Run, meal.run_id)
        if run.mode == "personal":
            if context != "personal" or meal.owner_id != actor.id:
                raise DomainError("NOT_FOUND", 404)
        elif run.mode == "school":
            authorize(db, actor, meal.workspace_id, context, write=write)
        else:
            raise DomainError("NOT_FOUND", 404)
        return meal, run

    def references(db):
        return {
            "items": [
                reference_view(r)
                for r in db.scalars(
                    select(FoodReference)
                    .where(FoodReference.active.is_(True))
                    .order_by(FoodReference.slug)
                )
            ]
        }

    @app.post("/v1/device-console/session", tags=["Station console"])
    def console_login(data: ConsoleLogin, response: Response, db: DB):
        throttle("console-login", 8)
        if not cfg.console_key or not secrets.compare_digest(data.setup_key, cfg.console_key):
            raise DomainError("INVALID_STATION_KEY", 401)
        workspace_id = data.workspace_id or cfg.console_workspace_id
        if (cfg.console_workspace_id and workspace_id != cfg.console_workspace_id) or not db.get(
            Workspace, workspace_id
        ):
            raise DomainError("INVALID_STATION_KEY", 401)
        raw = secrets.token_urlsafe(32)
        expiry = utcnow() + timedelta(hours=cfg.session_hours)
        db.add(
            ConsoleSession(token_hash=hash_code(raw), workspace_id=workspace_id, expires_at=expiry)
        )
        db.commit()
        response.set_cookie(
            "senplate_console",
            raw,
            httponly=True,
            samesite="strict",
            path="/v1/device-console",
            secure=not cfg.development,
            max_age=cfg.session_hours * 3600,
        )
        return {"workspace_id": workspace_id, "expires_at": iso(expiry)}

    @app.delete("/v1/device-console/session", tags=["Station console"])
    def console_logout(station: Console, response: Response, db: DB):
        db.execute(delete(ConsoleSession).where(ConsoleSession.token_hash == station.token_hash))
        db.commit()
        response.delete_cookie("senplate_console", path="/v1/device-console")
        return {"signed_out": True}

    @app.get("/v1/device-console/active", tags=["Station console"])
    def console_active(station: Console, db: DB):
        ws, run = current(db, station.workspace_id)
        meal = db.scalar(select(Meal).where(Meal.run_id == run.id)) if run else None
        return {
            "workspace_id": ws.id,
            "workspace_name": ws.name,
            "run_id": run.id if run else None,
            "mode": run.mode if run else None,
            "data_origin": run.origin if run else None,
            "development": cfg.development,
            "meal": meal_view(db, meal, run, device=True)
            if meal and meal.state in ACTIVE_MEALS
            else None,
        }

    @app.get("/v1/device-console/references", tags=["Station console"])
    def console_references(station: Console, db: DB):
        return references(db)

    @app.get("/v1/food-references", tags=["Meal references"])
    def user_references(actor: Actor, db: DB):
        return references(db)

    @app.post("/v1/device-console/meals", tags=["Station console"])
    def console_start(data: MealStart, station: Console, db: DB, idempotency_key: Key = None):
        if not cfg.development:
            raise DomainError("HARDWARE_SESSION_NOT_CONFIGURED", 409)
        actor_id = "console:" + station.workspace_id
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"path": "start_meal", "body": data.model_dump()})
        op_lock(db, actor_id, station.workspace_id, key)
        ws, _ = current(db, station.workspace_id, True)
        cached = operation_cached(db, actor_id, ws.id, key, fingerprint)
        if cached:
            return cached
        if data.expected_run_id != ws.active_run_id:
            raise DomainError("SESSION_CHANGED")
        meal, run = start_meal(db, ws, data.mode)
        result = remember(
            db,
            actor_id,
            ws.id,
            key,
            fingerprint,
            {
                "meal_id": meal.id,
                "run_id": run.id,
                "state": meal.state,
                "resource_version": meal.version,
            },
        )
        db.commit()
        return result

    @app.post("/v1/device-console/meals/{meal_id}/actions", tags=["Station console"])
    def console_action(
        meal_id: str, data: MealAction, station: Console, db: DB, idempotency_key: Key = None
    ):
        actor_id = "console:" + station.workspace_id
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"meal": meal_id, "body": data.model_dump()})
        op_lock(db, actor_id, station.workspace_id, key)
        ws, run = current(db, station.workspace_id, True)
        meal = db.get(Meal, meal_id)
        if not meal or meal.workspace_id != ws.id:
            raise DomainError("NOT_FOUND", 404)
        cached = operation_cached(db, actor_id, ws.id, key, fingerprint)
        if cached:
            return cached
        if not run or meal.run_id != run.id:
            raise DomainError("SESSION_CHANGED")
        db.refresh(meal)
        act_meal(db, meal, run, data, actor_id, device=True)
        result = remember(
            db,
            actor_id,
            ws.id,
            key,
            fingerprint,
            {"meal_id": meal.id, "state": meal.state, "resource_version": meal.version},
        )
        db.commit()
        return result

    @app.get("/v1/device-console/operations/{key}", tags=["Station console"])
    def console_operation(key: str, station: Console, db: DB):
        from .models import Operation

        row = db.scalar(
            select(Operation).where(
                Operation.actor_id == "console:" + station.workspace_id,
                Operation.context_id == station.workspace_id,
                Operation.key == key,
            )
        )
        if not row:
            raise DomainError("NOT_FOUND", 404)
        return row.result

    @app.get("/v1/device-console/pairing-qr.svg", tags=["Station console"])
    def pair_qr(station: Console, db: DB):
        _, run = current(db, station.workspace_id)
        meal = db.scalar(select(Meal).where(Meal.run_id == run.id)) if run else None
        if (
            not meal
            or meal.state != "pairing"
            or not meal.pair_code
            or meal.pair_expires_at <= utcnow()
        ):
            raise DomainError("PAIR_CODE_EXPIRED")
        output = io.BytesIO()
        segno.make_qr("senplate://pair/" + meal.pair_code, error="m").save(
            output, kind="svg", scale=6, dark="#163F35", light="white", border=4
        )
        return Response(output.getvalue(), media_type="image/svg+xml")

    @app.post("/v1/device-console/simulate", tags=["Development simulation"])
    def console_simulate(
        data: ConsoleSimulation, station: Console, db: DB, idempotency_key: Key = None
    ):
        key = key_for(idempotency_key, data.client_operation_id)
        actor_id = "console:" + station.workspace_id
        fingerprint = digest({"path": "console_simulation", "body": data.model_dump()})
        op_lock(db, actor_id, station.workspace_id, key)
        ws, run = current(db, station.workspace_id, True)
        cached = operation_cached(db, actor_id, ws.id, key, fingerprint)
        if cached:
            return cached
        if not run or run.id != data.run_id or run.state != "active":
            raise DomainError("SESSION_CHANGED")
        if (
            not cfg.development
            or run.origin != "simulated"
            or run.mode not in {"personal", "school"}
        ):
            raise DomainError("SIMULATION_NOT_ALLOWED", 403)
        run.clock_at += timedelta(seconds=data.seconds)
        if data.action != "advance":
            ingest(
                db,
                run,
                ObservationInput(
                    observation_id=uid(),
                    device_id=run.device_id,
                    session_id=run.id,
                    boot_id=run.boot_id,
                    sequence=run.last_sequence + 1,
                    observed_at=run.clock_at,
                    net_g=data.weight_g,
                    gross_g=data.weight_g + 500,
                    tare_g=500,
                    weight_quality="unstable" if data.action == "unstable" else "valid",
                    pan_presence="absent" if data.action == "remove" else "present",
                    calibration_version="demo-unverified",
                    binding_revision=run.binding_revision,
                ),
            )
        else:
            run.snapshot_version += 1
            meal = db.scalar(select(Meal).where(Meal.run_id == run.id))
            if meal:
                notify_owner(db, meal)
        result = remember(db, actor_id, ws.id, key, fingerprint, {"run_id": run.id})
        db.commit()
        return result

    @app.post("/v1/pairing/requests", tags=["Personal meals"])
    def pair_apply(
        data: PairApply,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        personal(x_context_id)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"path": "pair_apply", "body": data.model_dump()})
        op_lock(db, actor.id, "personal", key)
        cached = operation_cached(db, actor.id, "personal", key, fingerprint)
        if cached:
            return cached
        throttle("pair:" + actor.id)
        meal = db.scalar(select(Meal).where(Meal.pair_hash == hash_code(data.code)))
        if not meal:
            raise DomainError("PAIR_CODE_EXPIRED")
        _, run = current(db, meal.workspace_id, True)
        db.refresh(meal)
        if not run or meal.run_id != run.id or meal.pair_hash != hash_code(data.code):
            raise DomainError("PAIR_CODE_EXPIRED")
        req = request_pairing(db, meal, run, actor)
        result = remember(
            db, actor.id, "personal", key, fingerprint, {"request_id": req.id, "state": req.state}
        )
        db.commit()
        return result

    @app.get("/v1/me/pairing", tags=["Personal meals"])
    def my_pairing(actor: Actor, db: DB, x_context_id: Context = None):
        personal(x_context_id)
        rows = db.scalars(
            select(PairRequest)
            .where(PairRequest.user_id == actor.id)
            .order_by(PairRequest.created_at.desc())
            .limit(10)
        )
        return {"items": [pair_view(db, r) for r in rows]}

    @app.get("/v1/me/meals", tags=["Personal meals"])
    def my_meals(
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        data_origin: Literal["simulated", "replay", "hardware"] | None = None,
    ):
        personal(x_context_id)
        query = (
            select(Meal, Run)
            .join(Run, Meal.run_id == Run.id)
            .where(Meal.owner_id == actor.id, Run.mode == "personal")
        )
        if data_origin:
            query = query.where(Run.origin == data_origin)
        rows = db.execute(query.order_by(Meal.created_at.desc()).limit(100)).all()
        return {"items": [meal_view(db, m, r) for m, r in rows], "scope": "latest_100"}

    @app.get("/v1/meals/{meal_id}", tags=["Meals"])
    def get_meal(meal_id: str, actor: Actor, db: DB, x_context_id: Context = None):
        meal, run = owned_meal(db, meal_id, actor, x_context_id)
        return meal_view(db, meal, run)

    @app.post("/v1/meals/{meal_id}/actions", tags=["Meals"])
    def meal_action(
        meal_id: str,
        data: MealAction,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        meal, _ = owned_meal(db, meal_id, actor, x_context_id, True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"meal": meal_id, "body": data.model_dump()})
        op_lock(db, actor.id, x_context_id, key)
        _, run = current(db, meal.workspace_id, True)
        db.refresh(meal)
        cached = operation_cached(db, actor.id, x_context_id, key, fingerprint)
        if cached:
            return cached
        if not run or meal.run_id != run.id:
            raise DomainError("SESSION_CHANGED")
        act_meal(db, meal, run, data, actor.id)
        result = remember(
            db,
            actor.id,
            x_context_id,
            key,
            fingerprint,
            {"meal_id": meal.id, "state": meal.state, "resource_version": meal.version},
        )
        db.commit()
        return result

    def sample_rows(db, workspace_id, source, start, end):
        if start and end and start > end:
            raise DomainError("INVALID_DATE_RANGE", 422)
        query = (
            select(Meal, Run)
            .join(Run, Meal.run_id == Run.id)
            .where(Meal.workspace_id == workspace_id, Run.mode == "school", Run.origin == source)
        )
        zone = ZoneInfo("Asia/Hong_Kong")
        if start:
            query = query.where(Meal.created_at >= datetime.combine(start, datetime_time.min, zone))
        if end:
            query = query.where(
                Meal.created_at < datetime.combine(end + timedelta(days=1), datetime_time.min, zone)
            )
        return db.execute(query.order_by(Meal.created_at.desc()).limit(100)).all()

    @app.get("/v1/workspaces/{workspace_id}/samples", tags=["Anonymous school samples"])
    def samples(
        workspace_id: str,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        data_origin: Literal["simulated", "replay", "hardware"] = "simulated",
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        authorize(db, actor, workspace_id, x_context_id)
        rows = sample_rows(db, workspace_id, data_origin, date_from, date_to)
        items = [meal_view(db, meal, run) for meal, run in rows]
        complete = [m for m in items if m["state"] == "completed"]
        return {
            "items": items,
            "scope": "latest_100_matching_anonymous_samples",
            "data_origin": data_origin,
            "summary": {
                "completed_samples": len(complete),
                "provided_g": sum(m["provided_g"] for m in complete),
                "remaining_observed_g": sum(
                    m["remaining_g"] for m in complete if m["remaining_g"] is not None
                )
                if any(m["remaining_g"] is not None for m in complete)
                else None,
                "samples_with_remaining": sum(m["remaining_g"] is not None for m in complete),
                "samples_without_remaining": sum(m["remaining_g"] is None for m in complete),
            },
        }

    @app.get("/v1/workspaces/{workspace_id}/samples.csv", tags=["Anonymous school samples"])
    def samples_csv(
        workspace_id: str,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        data_origin: Literal["simulated", "replay", "hardware"] = "simulated",
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        if authorize(db, actor, workspace_id, x_context_id) != "manager":
            raise DomainError("MANAGER_REQUIRED", 403)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "sample_code",
                "created_at",
                "data_origin",
                "state",
                "provided_g",
                "remaining_g",
                "remaining_reason",
                "nutrition_status",
                "reference_energy_kcal",
                "scope",
                "plan_review_status",
            ]
        )
        for meal, run in sample_rows(db, workspace_id, data_origin, date_from, date_to):
            row = meal_view(db, meal, run)
            writer.writerow(
                [
                    meal.sample_code,
                    iso(meal.created_at),
                    run.origin,
                    meal.state,
                    row["provided_g"],
                    meal.remaining_g,
                    meal.remaining_reason,
                    row["nutrition"]["status"],
                    row["nutrition"]["total"]["energy_kcal"],
                    "latest_100_matching_samples_not_intake",
                    "illustrative_unreviewed",
                ]
            )
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="senplate-anonymous-samples.csv"'
            },
        )
