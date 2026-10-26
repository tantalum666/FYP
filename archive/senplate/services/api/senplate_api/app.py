import asyncio
import csv
import hashlib
import io
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, Header, Query, Request, Response, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pwdlib import PasswordHash
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.websockets import WebSocketDisconnect

from .config import Settings, load_settings
from .database import prepare_database
from .availability import has_open_orders
from .domain import (ACTIVE_TASKS, DomainError, act_on_task, decide, digest, event, event_view,
                     ingest, iso, operation_cached, rec_view, refresh_recommendation,
                     remember, snapshot, task_view, utcnow)
from .models import (Event, LoginSession, Membership, Operation, Recommendation,
                     Run, Task, User, Workspace, uid)
from .schemas import (CreateRun, Decision, Heartbeat, Login, ObservationBatch,
                      ObservationInput, SimulationAction, TaskAction)
from .ordering import register_order_routes, seed_menu
from .meals_domain import station_can_switch
from .meals_routes import register_meal_routes
from .nutrition import seed_references

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(24))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    engine = create_engine(cfg.database_url, pool_pre_ping=True)
    factory = sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app):
        prepare_database(engine)
        with factory() as db:
            seed_references(db)
            db.commit()
        if cfg.development:
            with factory() as db:
                for workspace in db.scalars(select(Workspace).where(Workspace.active_run_id.is_not(None))):
                    run = db.get(Run, workspace.active_run_id)
                    if run:
                        seed_menu(db, run)
                db.commit()
        yield
        engine.dispose()

    app = FastAPI(title="Senplate local prototype", version="0.3.0", lifespan=lifespan)
    app.state.factory, app.state.settings = factory, cfg
    failed_logins = {}
    allowed_origins = set(cfg.allowed_origins)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uid()
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in allowed_origins:
            return JSONResponse({"error": {"code": "ORIGIN_NOT_ALLOWED"},
                                 "request_id": request.state.request_id}, status_code=403)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse({"error": {"code": exc.code},
                             "request_id": getattr(request.state, "request_id", uid())},
                            status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"error": {"code": "VALIDATION_FAILED",
                             "fields": [".".join(map(str, e["loc"])) for e in exc.errors()]},
                             "request_id": request.state.request_id}, status_code=422)

    def db_session():
        with factory() as db:
            yield db

    DB = Annotated[Session, Depends(db_session)]

    def resolve_user(db, raw):
        login = db.get(LoginSession, token_hash(raw)) if raw else None
        user = db.get(User, login.user_id) if login and login.expires_at > utcnow() else None
        if not user or not user.active:
            raise DomainError("AUTH_REQUIRED", 401)
        return user

    def current_user(db: DB, authorization: Annotated[str | None, Header()] = None,
                     senplate_session: Annotated[str | None, Cookie()] = None):
        raw = authorization[7:] if authorization and authorization.startswith("Bearer ") else senplate_session
        return resolve_user(db, raw)

    Actor = Annotated[User, Depends(current_user)]

    def authorize(db, actor, workspace_id, context_id, write=False):
        member = db.get(Membership, (actor.id, workspace_id))
        if context_id != workspace_id or not member or not member.active:
            raise DomainError("FORBIDDEN", 403)
        if write and member.role not in {"staff", "manager"}:
            raise DomainError("FORBIDDEN", 403)
        return member.role

    def machine(key, *, simulator_only=False):
        if key and secrets.compare_digest(key, cfg.simulator_key) and cfg.development:
            return "simulator"
        if not simulator_only and key and secrets.compare_digest(key, cfg.device_key):
            return "device"
        raise DomainError("MACHINE_AUTH_REQUIRED", 401)

    def run_by(db, *, run_id=None, station_id=None, lock=False):
        query = select(Run).where(Run.id == run_id) if run_id else select(Run).where(Run.station_id == station_id)
        run = db.scalar(query.with_for_update() if lock else query)
        if not run:
            raise DomainError("NOT_FOUND", 404)
        return run

    def active_run(db, workspace_id):
        ws = db.get(Workspace, workspace_id)
        if not ws or not ws.active_run_id:
            raise DomainError("NO_ACTIVE_RUN", 404)
        return run_by(db, run_id=ws.active_run_id)

    def key_for(header, client):
        if not header or header != client or len(header) > 80:
            raise DomainError("IDEMPOTENCY_KEY_REQUIRED", 422)
        return header

    @app.get("/health")
    def health(db: DB):
        db.execute(select(1))
        return {"status": "ok", "environment": "development" if cfg.development else "local"}

    @app.post("/v1/auth/sessions")
    def login(data: Login, response: Response, request: Request, db: DB):
        identifier = (request.client.host, data.username.lower())
        attempts = [t for t in failed_logins.get(identifier, []) if time.monotonic() - t < 60]
        if len(attempts) >= 8:
            raise DomainError("TRY_LATER", 429)
        user = db.scalar(select(User).where(User.username == data.username.strip().lower()))
        valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
        if not user or not valid or not user.active:
            failed_logins[identifier] = [*attempts, time.monotonic()]
            raise DomainError("INVALID_CREDENTIALS", 401)
        failed_logins.pop(identifier, None)
        raw = secrets.token_urlsafe(32)
        expires = utcnow() + timedelta(hours=cfg.session_hours)
        db.add(LoginSession(token_hash=token_hash(raw), user_id=user.id, expires_at=expires))
        db.commit()
        response.set_cookie("senplate_session", raw, httponly=True, samesite="strict",
                            secure=not cfg.development, max_age=cfg.session_hours * 3600)
        return {"access_token": raw, "token_type": "bearer", "expires_at": iso(expires)}

    @app.get("/v1/me")
    def me(actor: Actor, db: DB):
        contexts = [{"id": "personal", "name": "个人", "name_en": "Personal", "role": "personal"}]
        for member in db.scalars(select(Membership).where(Membership.user_id == actor.id,
                                                          Membership.active.is_(True))):
            ws = db.get(Workspace, member.workspace_id)
            contexts.append({"id": ws.id, "name": ws.name, "name_en": "Demo dining room",
                             "role": member.role})
        return {"id": actor.id, "name": actor.name, "username": actor.username, "contexts": contexts}

    @app.delete("/v1/auth/sessions/current")
    def logout(actor: Actor, db: DB, request: Request, response: Response):
        auth = request.headers.get("authorization", "")
        raw = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("senplate_session", "")
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(raw)))
        db.commit()
        response.delete_cookie("senplate_session")
        return {"signed_out": True}

    @app.get("/v1/workspaces/{workspace_id}/overview")
    def overview(workspace_id: str, actor: Actor, db: DB,
                 x_context_id: Annotated[str | None, Header()] = None):
        role = authorize(db, actor, workspace_id, x_context_id)
        run = active_run(db, workspace_id)
        result = snapshot(db, run)
        return {"workspace_name": db.get(Workspace, workspace_id).name, "role": role,
                "station_count": 1, "pending_count": int(result["recommendation"] is not None),
                "active_task_count": sum(t["state"] in ACTIVE_TASKS for t in result["tasks"]),
                "station": result}

    @app.get("/v1/workspaces/{workspace_id}/stations")
    def stations(workspace_id: str, actor: Actor, db: DB,
                 x_context_id: Annotated[str | None, Header()] = None):
        authorize(db, actor, workspace_id, x_context_id)
        return {"items": [snapshot(db, active_run(db, workspace_id))]}

    @app.get("/v1/stations/{station_id}/snapshot")
    def station_snapshot(station_id: str, actor: Actor, db: DB,
                         x_context_id: Annotated[str | None, Header()] = None):
        run = run_by(db, station_id=station_id)
        authorize(db, actor, run.workspace_id, x_context_id)
        return snapshot(db, run)

    @app.get("/v1/stations/{station_id}/events")
    def events(station_id: str, actor: Actor, db: DB,
               x_context_id: Annotated[str | None, Header()] = None,
               cursor: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
               data_origin: str | None = None):
        run = run_by(db, station_id=station_id)
        authorize(db, actor, run.workspace_id, x_context_id)
        if run.mode == "personal":
            raise DomainError("PRIVATE_MEAL_SESSION", 403)
        if data_origin and data_origin != run.origin:
            return {"items": [], "next_cursor": None}
        rows = list(db.scalars(select(Event).where(Event.run_id == run.id)
                    .order_by(Event.sequence.desc()).offset(cursor).limit(limit + 1)))
        return {"items": [event_view(e, run.origin) for e in rows[:limit]],
                "next_cursor": cursor + limit if len(rows) > limit else None}

    @app.get("/v1/workspaces/{workspace_id}/recommendations")
    def recommendations(workspace_id: str, actor: Actor, db: DB,
                        x_context_id: Annotated[str | None, Header()] = None):
        authorize(db, actor, workspace_id, x_context_id)
        rec = snapshot(db, active_run(db, workspace_id))["recommendation"]
        return {"items": [rec] if rec else []}

    @app.get("/v1/recommendations/{rec_id}")
    def recommendation(rec_id: str, actor: Actor, db: DB,
                       x_context_id: Annotated[str | None, Header()] = None):
        rec = db.get(Recommendation, rec_id)
        if not rec:
            raise DomainError("NOT_FOUND", 404)
        run = run_by(db, run_id=rec.run_id)
        authorize(db, actor, run.workspace_id, x_context_id)
        return rec_view(rec)

    @app.post("/v1/recommendations/{rec_id}/decisions")
    def decision(rec_id: str, data: Decision, actor: Actor, db: DB,
                 x_context_id: Annotated[str | None, Header()] = None,
                 idempotency_key: Annotated[str | None, Header()] = None):
        rec = db.get(Recommendation, rec_id)
        if not rec:
            raise DomainError("NOT_FOUND", 404)
        run = run_by(db, run_id=rec.run_id, lock=True)
        authorize(db, actor, run.workspace_id, x_context_id, write=True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"rec": rec_id, "body": data.model_dump()})
        cached = operation_cached(db, actor.id, run.workspace_id, key, fingerprint)
        if cached:
            return cached
        if db.get(Workspace, run.workspace_id).active_run_id != run.id:
            raise DomainError("SESSION_CHANGED")
        db.refresh(rec)
        result = remember(db, actor.id, run.workspace_id, key, fingerprint, decide(db, run, rec, data, actor))
        db.commit()
        return result

    @app.get("/v1/workspaces/{workspace_id}/tasks")
    def tasks(workspace_id: str, actor: Actor, db: DB,
              x_context_id: Annotated[str | None, Header()] = None,
              state: str | None = None, mine: bool = False):
        authorize(db, actor, workspace_id, x_context_id)
        items = snapshot(db, active_run(db, workspace_id))["tasks"]
        return {"items": [t for t in items if (not state or t["state"] == state)
                          and (not mine or t["assignee_id"] == actor.id)]}

    @app.get("/v1/tasks/{task_id}")
    def task_detail(task_id: str, actor: Actor, db: DB,
                    x_context_id: Annotated[str | None, Header()] = None):
        task = db.get(Task, task_id)
        if not task:
            raise DomainError("NOT_FOUND", 404)
        run = run_by(db, run_id=task.run_id)
        authorize(db, actor, run.workspace_id, x_context_id)
        return task_view(db, task)

    @app.post("/v1/tasks/{task_id}/actions")
    def task_action(task_id: str, data: TaskAction, actor: Actor, db: DB,
                    x_context_id: Annotated[str | None, Header()] = None,
                    idempotency_key: Annotated[str | None, Header()] = None):
        task = db.get(Task, task_id)
        if not task:
            raise DomainError("NOT_FOUND", 404)
        run = run_by(db, run_id=task.run_id, lock=True)
        role = authorize(db, actor, run.workspace_id, x_context_id, write=True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"task": task_id, "body": data.model_dump()})
        cached = operation_cached(db, actor.id, run.workspace_id, key, fingerprint)
        if cached:
            return cached
        if db.get(Workspace, run.workspace_id).active_run_id != run.id:
            raise DomainError("SESSION_CHANGED")
        db.refresh(task)
        result = remember(db, actor.id, run.workspace_id, key, fingerprint,
                          act_on_task(db, run, task, data, actor, role))
        db.commit()
        return result

    @app.get("/v1/operations/{operation_key}")
    def operation_result(operation_key: str, actor: Actor, db: DB,
                         x_context_id: Annotated[str | None, Header()] = None):
        if x_context_id != 'personal':
            authorize(db, actor, x_context_id, x_context_id, write=True)
        op = db.scalar(select(Operation).where(Operation.actor_id == actor.id,
                       Operation.context_id == x_context_id, Operation.key == operation_key))
        if not op:
            raise DomainError("NOT_FOUND", 404)
        return op.result

    @app.post("/v1/device/observations/batch")
    def observations(data: ObservationBatch, db: DB,
                     x_device_key: Annotated[str | None, Header()] = None):
        source = machine(x_device_key)
        results = []
        for item in data.observations:
            try:
                with db.begin_nested():
                    run = run_by(db, run_id=item.session_id, lock=True)
                    if (source == "device") != (run.origin == "hardware"):
                        raise DomainError("SOURCE_MISMATCH", 403)
                    if db.get(Workspace, run.workspace_id).active_run_id != run.id:
                        raise DomainError("SESSION_CHANGED")
                    results.append({"observation_id": item.observation_id, "status": ingest(db, run, item)})
            except DomainError as exc:
                results.append({"observation_id": item.observation_id, "status": "rejected", "code": exc.code})
        db.commit()
        return {"results": results}

    @app.post("/v1/device/heartbeats")
    def heartbeat(data: Heartbeat, db: DB, x_device_key: Annotated[str | None, Header()] = None):
        source = machine(x_device_key)
        run = run_by(db, run_id=data.session_id, lock=True)
        if db.get(Workspace, run.workspace_id).active_run_id != run.id or run.state != "active":
            raise DomainError("SESSION_CHANGED")
        if data.device_id != run.device_id or (source == "device") != (run.origin == "hardware"):
            raise DomainError("SOURCE_MISMATCH", 403)
        if data.at.tzinfo is None or data.at > run.clock_at + timedelta(seconds=1):
            raise DomainError("INVALID_TIMESTAMP", 422)
        if run.heartbeat_at is None or data.at > run.heartbeat_at:
            run.heartbeat_at = data.at
            run.snapshot_version += 1
        db.commit()
        return {"accepted": True}

    @app.post("/v1/dev/runs")
    def create_run(data: CreateRun, db: DB, x_device_key: Annotated[str | None, Header()] = None,
                   idempotency_key: Annotated[str | None, Header()] = None):
        machine(x_device_key, simulator_only=True)
        key = key_for(idempotency_key, data.client_operation_id)
        ws = db.scalar(select(Workspace).where(Workspace.id == data.workspace_id).with_for_update())
        if not ws:
            raise DomainError("NOT_FOUND", 404)
        fingerprint = digest(data.model_dump())
        cached = operation_cached(db, "simulator", ws.id, key, fingerprint)
        if cached:
            return cached
        old = run_by(db, run_id=ws.active_run_id, lock=True) if ws.active_run_id else None
        station_can_switch(db, old)
        if old:
            old.state = "closed"
            old.paused = True
        clock = datetime.now(timezone.utc).replace(hour=4, minute=0, second=0, microsecond=0)
        run = Run(id=uid(), workspace_id=ws.id, clock_at=clock, closes_at=clock + timedelta(hours=2),
                  food_name=data.food_name, food_name_en=data.food_name_en, origin=data.source,
                  service_type=data.service_type)
        db.add(run)
        db.flush()
        ws.active_run_id = run.id
        ingest(db, run, simulated_observation(run, data.initial_g))
        seed_menu(db, run)
        result = remember(db, "simulator", ws.id, key, fingerprint,
                          {"run_id": run.id, "station_id": run.station_id, "workspace_id": ws.id})
        db.commit()
        return result

    def simulated_observation(run, weight, quality="valid", presence="present", vision="available"):
        return ObservationInput(observation_id=uid(), device_id=run.device_id, session_id=run.id,
                                boot_id=run.boot_id, sequence=run.last_sequence + 1,
                                observed_at=run.clock_at, gross_g=weight + 500, tare_g=500,
                                net_g=weight, weight_quality=quality, pan_presence=presence,
                                vision_status=vision, calibration_version="demo-unverified",
                                binding_revision=run.binding_revision)

    @app.post("/v1/dev/runs/{run_id}/actions")
    def simulation(run_id: str, data: SimulationAction, db: DB,
                   x_device_key: Annotated[str | None, Header()] = None,
                   idempotency_key: Annotated[str | None, Header()] = None):
        machine(x_device_key, simulator_only=True)
        run = run_by(db, run_id=run_id, lock=True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"run": run_id, "body": data.model_dump()})
        cached = operation_cached(db, "simulator", run.workspace_id, key, fingerprint)
        if cached:
            return cached
        if db.get(Workspace, run.workspace_id).active_run_id != run.id or run.state != "active":
            raise DomainError("SESSION_CHANGED")
        run.clock_at += timedelta(seconds=data.seconds or (300 if data.action == "consume" else 1))
        weight = run.last_valid_g or 0
        if data.action in {"consume", "add"}:
            if run.measurement_status != "valid" or run.paused:
                raise DomainError("DATA_NOT_READY")
            weight += data.amount_g * (-1 if data.action == "consume" else 1)
            if not 0 <= weight <= 5000:
                raise DomainError("INVALID_WEIGHT", 422)
        if data.action == "rebind":
            if run.mode != "foodservice":
                raise DomainError("ACTIVE_MEAL_ON_STATION")
            if has_open_orders(db, run.id):
                raise DomainError('OPEN_ORDERS_OR_MEASUREMENT')
            run.binding_revision += 1
            run.food_id = uid()
            event(db, run, "food_rebound")
        if data.action == "closing":
            run.closes_at = run.clock_at + timedelta(minutes=5)
        if data.action in {"pause", "resume"}:
            run.paused = data.action == "pause"
            event(db, run, "monitoring_paused" if run.paused else "monitoring_resumed")
        if data.action == "disconnect":
            run.clock_at += timedelta(seconds=16)
        if data.action not in {"advance", "disconnect", "pause"}:
            ingest(db, run, simulated_observation(run, weight,
                   quality="unstable" if data.action == "unstable" else "valid",
                   presence="absent" if data.action == "remove" else "present",
                   vision="occluded" if data.action == "occlude" else "available"))
        run.snapshot_version += 1
        db.flush()
        refresh_recommendation(db, run)
        result = remember(db, "simulator", run.workspace_id, key, fingerprint,
                          {"run_id": run.id, "snapshot_version": run.snapshot_version})
        db.commit()
        return result

    @app.get("/v1/workspaces/{workspace_id}/events.csv")
    def export_events(workspace_id: str, actor: Actor, db: DB,
                      x_context_id: Annotated[str | None, Header()] = None):
        role = authorize(db, actor, workspace_id, x_context_id)
        if role != "manager":
            raise DomainError("MANAGER_REQUIRED", 403)
        run = active_run(db, workspace_id)
        if run.mode == "personal":
            raise DomainError("PRIVATE_MEAL_SESSION", 403)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["run_id", "data_origin", "event_id", "at", "kind", "delta_g", "net_g"])
        for e in db.scalars(select(Event).where(Event.run_id == run.id).order_by(Event.sequence)):
            writer.writerow([run.id, run.origin, e.id, iso(e.at), e.kind, e.delta_g, e.net_g])
        return Response(out.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="senplate-events.csv"'})

    @app.websocket("/v1/events")
    async def updates(ws: WebSocket, context_id: str):
        origin = ws.headers.get("origin")
        if origin and origin not in allowed_origins:
            await ws.close(code=4403)
            return
        authorization = ws.headers.get("authorization", "")
        raw = authorization[7:] if authorization.startswith("Bearer ") else ws.cookies.get("senplate_session")
        try:
            with factory() as db:
                actor = resolve_user(db, raw)
                if context_id != "personal":
                    authorize(db, actor, context_id, context_id)
            await ws.accept()
            last = None
            while True:
                with factory() as db:
                    actor = resolve_user(db, raw)
                    if context_id == "personal":
                        version = actor.activity_version
                    else:
                        authorize(db, actor, context_id, context_id)
                        run = active_run(db, context_id)
                        version = (run.id, run.snapshot_version, run.measurement_status)
                    if version != last:
                        await ws.send_json({"event_id": uid(), "type": "state.changed",
                                            "context_id": context_id, "server_time": iso(utcnow())})
                        last = version
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=1)
                except asyncio.TimeoutError:
                    pass
        except DomainError:
            await ws.close(code=4403)
        except (WebSocketDisconnect, RuntimeError):
            pass

    register_order_routes(app, db_session, current_user, authorize, key_for)
    register_meal_routes(app, db_session, current_user, authorize, key_for)
    return app
