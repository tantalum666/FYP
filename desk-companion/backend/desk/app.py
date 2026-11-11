import asyncio
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware

from .access import DEVICE_COOKIE
from .assistant_routes import assistant_routes
from .memory import memory_routes
from .memory_followups import memory_followup_routes
from .moments import moment_routes
from .nudges import nudge_routes
from .digest import digest_routes
from .saved_skills import saved_skill_routes
from .goals import goal_routes
from .profile import profile_routes
from .notify import notice_routes
from .web_push import push_routes
from .persona import persona_routes
from .permissions import permission_routes
from .device_routes import device_routes
from .runtime import Runtime
from .workspace_data import PreferencesUpdate
from .voice import voice_routes
from .wake_listening import wake_routes
from .exchange_routes import exchange_routes
from .google_calendar import google_routes
from .mailbox import mailbox_routes
from .offline_calendar import offline_calendar_routes
from .phone import phone_snapshot
from .tasks import task_routes
from .jobs import job_routes
from .personal_context import personal_routes
from .routines import routine_routes
from .sources import sources_routes
from .artifacts import artifact_routes
from .agent_runs import agent_run_routes
from .browser_jobs import browser_routes
from .connector_routes import connector_routes
from .work_search import work_search_routes
from .responsibilities import responsibility_routes
from .work_capacity import work_capacity_routes
from .public_captures import public_capture_routes
from .shopping.routes import shopping_routes
from .travel_quotes.routes import trip_routes
from .connectors.contracts import load_connector_configs
from .backups import CHECK_INTERVAL_SECONDS
from .diagnostics import diagnostics_html, diagnostics_report
from .log import configure, log_event, redact_text

from .cookies import cookie_secure
from .session_cookie_scope import LoopbackCookieScope
from .schemas import CreateEvents, EventAction, Login, ReminderAction, SettingsInput
from .store import DomainError, Store


COOKIE = "desk_companion_session"


def create_app(
    directory=None,
    clock=None,
    password=None,
    scheduler=True,
    allow_replay=None,
    connector_configs=None,
    allow_watch_retention_migration=False,
    allow_public_capture_migration=False,
    public_capture_enabled=None,
):
    if public_capture_enabled is not None and type(public_capture_enabled) is not bool:
        raise DomainError("CAPTURE_CAPABILITY_INVALID", 422)
    runtime = (
        directory
        or os.environ.get("DESK_RUNTIME_DIR")
        or Path(__file__).resolve().parents[2] / ".runtime"
    )
    configure()
    store = Store(
        runtime,
        clock=clock,
        password=password,
        allow_watch_retention_migration=allow_watch_retention_migration,
        allow_public_capture_migration=allow_public_capture_migration,
    )
    if connector_configs is None:
        config_path = os.environ.get("DESK_MCP_CONFIG_PATH")
        connector_configs = load_connector_configs(config_path) if config_path else ()
    services = Runtime(
        store,
        allow_replay=os.environ.get("DESK_ALLOW_REPLAY") == "1"
        if allow_replay is None
        else allow_replay,
        connector_configs=connector_configs,
        public_capture_enabled=os.environ.get("DESK_PUBLIC_CAPTURE_ENABLED") == "1"
        if public_capture_enabled is None
        else public_capture_enabled,
    )
    attempts = defaultdict(deque)

    schedule = (
        ("rules", lambda: services.tick(), 1),
        ("public_data", lambda: services.data.poll_weather(), 10),
        ("task_advice", lambda: services.text_ai.enrich_one(), 30),
        ("computer_jobs", lambda: services.jobs.run_one(), 0.5),
        ("responsibilities", lambda: services.responsibilities.advance(), 1),
        ("agent_runs", lambda: services.agent_runs.advance_one(), 0.5),
        ("browser_jobs", lambda: services.browser_jobs.advance_one(), 0.5),
        ("connectors", lambda: services.connectors.advance_one(), 0.5),
        ("local_backup", lambda: services.backups.tick(), CHECK_INTERVAL_SECONDS),
    )

    @asynccontextmanager
    async def lifespan(app):
        async def worker(name, action, interval):
            while True:
                try:
                    await asyncio.to_thread(action)
                    services.worker_health[name] = "ready"
                except Exception:
                    # Keep transient failures from silently killing a scheduler.
                    # Expose a safe status, never raw provider/private error text.
                    services.worker_health[name] = "retrying_after_error"
                await asyncio.sleep(interval)

        if scheduler:
            services.public_captures.start()
        workers = (
            [
                asyncio.create_task(worker(name, action, interval))
                for name, action, interval in schedule
            ]
            if scheduler
            else []
        )
        try:
            yield
        finally:
            failure = None
            for stop in (
                services.public_captures.stop,
                services.agent_runs.shutdown,
                services.browser_jobs.shutdown,
                services.connectors.shutdown,
                services.jobs.shutdown,
            ):
                try:
                    stop()
                except BaseException as error:
                    if failure is None:
                        failure = error
            for running in workers:
                running.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            if failure is not None:
                raise failure

    app = FastAPI(title="Desk Companion", version="0.1.0", lifespan=lifespan)
    app.add_middleware(LoopbackCookieScope)
    app.state.store = store
    app.state.runtime = services
    app.state.scheduled = tuple((name, interval) for name, _action, interval in schedule)
    public_origin = os.environ.get("DESK_PUBLIC_ORIGIN", "").rstrip("/")
    allowed_origins = {
        f"http://{host}{port}"
        for host in ("localhost", "127.0.0.1", "testserver")
        for port in ("", ":5190", ":8831", ":5191", ":8832")
    }
    # The Mac-to-Pi SSH launcher binds this port on Mac loopback only.
    allowed_origins.update({"http://127.0.0.1:8891", "http://localhost:8891"})
    allowed_hosts = ["localhost", "127.0.0.1", "testserver"]
    if public_origin:
        parts = urlsplit(public_origin)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.path
            or parts.query
            or parts.fragment
            or parts.username
        ):
            raise ValueError("DESK_PUBLIC_ORIGIN must be a single HTTPS origin")
        allowed_origins.add(public_origin)
        allowed_hosts.append(parts.hostname)
    if os.environ.get("DESK_NATIVE_CLIENTS") == "1":
        allowed_origins.add("capacitor://localhost")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["capacitor://localhost"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Desk-Request",
                "X-Operation-Id",
                "X-Desk-Native",
            ],
        )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def local_request_boundary(request, call_next):
        def access_log(status):
            log_event(
                "http",
                method=request.method,
                path=request.url.path,
                query=redact_text(request.url.query),
                status=status,
            )

        origin = request.headers.get("origin")
        if origin:
            if origin not in allowed_origins:
                access_log(403)
                return JSONResponse({"error": {"code": "ORIGIN_NOT_ALLOWED"}}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith(
            "/api/"
        ):
            if request.headers.get("x-desk-request") != "1":
                access_log(403)
                return JSONResponse({"error": {"code": "REQUEST_HEADER_REQUIRED"}}, status_code=403)
        response = await call_next(request)
        access_log(response.status_code)
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable"
            if request.url.path.startswith("/assets/") and response.status_code == 200
            else "no-store"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        # The app's explicit local preview needs both devices in production too.
        # Browser permission and the UI's separate share action still apply.
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(self)"
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"error": {"code": error.code}}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        fields = [".".join(str(v) for v in e["loc"][1:]) for e in error.errors()]
        return JSONResponse(
            {"error": {"code": "VALIDATION_FAILED", "fields": fields}}, status_code=422
        )

    def authenticated(request: Request):
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ")
        principal = services.access.principal(
            request.cookies.get(COOKIE), request.cookies.get(DEVICE_COOKIE), bearer
        )
        if not principal:
            raise DomainError("AUTH_REQUIRED", 401)
        return principal

    def owner(request: Request):
        if not store.session_valid(request.cookies.get(COOKIE)):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"kind": "owner", "id": "owner", "name": "Owner"}

    def agent(request: Request):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not services.access.agent_valid(token):
            raise DomainError("AGENT_AUTH_REQUIRED", 401)

    def limit(bucket, request, count, seconds):
        identity = (bucket, request.client.host if request.client else "local")
        queue = attempts[identity]
        now = time.monotonic()
        while queue and queue[0] < now - seconds:
            queue.popleft()
        if len(queue) >= count:
            raise DomainError("TRY_LATER", 429)
        queue.append(now)

    def operation_id(x_operation_id: str = Header(default="")):
        if x_operation_id.startswith("assistant-confirm/"):
            raise DomainError("RESERVED_OPERATION_ID", 422)
        return x_operation_id

    @app.get("/api/health")
    def health():
        return {"service": "desk-companion", "status": "ok"}

    from .owner_session import local_owner_available

    def automatic_owner(request: Request):
        return local_owner_available(
            request,
            public_origin=public_origin,
            enabled=os.environ.get("DESK_AUTO_OWNER", "1") == "1",
        )

    def local_preview(request: Request):
        # Compatibility for already installed clients using the old preview API.
        return local_owner_available(
            request,
            public_origin=public_origin,
            enabled=os.environ.get("DESK_LOCAL_PREVIEW") == "1",
        )

    def session_payload(request, principal):
        with store.connection() as conn:
            return {
                "username": "owner",
                "settings": store.settings(conn),
                "principal": principal,
                "local_preview": local_preview(request),
                "automatic_owner": automatic_owner(request),
            }

    def connect_owner(request, response):
        token = request.cookies.get(COOKIE)
        if not store.session_valid(token):
            token = store.create_owner_session()
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            samesite="strict",
            secure=cookie_secure(request),
            max_age=8 * 3600,
            path="/api",
        )

    @app.get("/api/session-mode")
    def session_mode(request: Request):
        return {
            "local_preview": local_preview(request),
            "automatic_owner": automatic_owner(request),
        }

    @app.post("/api/session/connect")
    def connect_session(request: Request, response: Response):
        if not automatic_owner(request):
            raise DomainError("LOCAL_OWNER_UNAVAILABLE", 403)
        limit("connect", request, 20, 60)
        connect_owner(request, response)
        return session_payload(request, {"kind": "owner", "id": "owner", "name": "Owner"})

    @app.post("/api/session/preview")
    def preview_session(request: Request, response: Response):
        if not local_preview(request):
            raise DomainError("LOCAL_PREVIEW_DISABLED", 403)
        limit("preview", request, 20, 60)
        connect_owner(request, response)
        return {"local_preview": True}

    @app.post("/api/session")
    def login(payload: Login, request: Request, response: Response):
        ip = request.client.host if request.client else "local"
        queue = attempts[ip]
        now = time.monotonic()
        while queue and queue[0] < now - 60:
            queue.popleft()
        if len(queue) >= 10:
            raise DomainError("TRY_LATER", 429)
        queue.append(now)
        token = store.authenticate(payload.username, payload.password)
        queue.clear()
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            samesite="strict",
            secure=cookie_secure(request),
            max_age=8 * 3600,
            path="/api",
        )
        return {"username": "owner"}

    @app.get("/api/session", dependencies=[Depends(authenticated)])
    def session(request: Request, response: Response, principal=Depends(authenticated)):
        if token := request.cookies.get(DEVICE_COOKIE):
            if services.access.principal(device_token=token):
                response.set_cookie(
                    DEVICE_COOKIE,
                    token,
                    httponly=True,
                    samesite="strict",
                    secure=cookie_secure(request),
                    max_age=365 * 86400,
                    path="/api",
                )
        return session_payload(request, principal)

    @app.delete("/api/session", dependencies=[Depends(authenticated)])
    def logout(request: Request, response: Response, principal=Depends(authenticated)):
        device_principal = services.access.principal(
            device_token=request.cookies.get(DEVICE_COOKIE),
            bearer=request.headers.get("Authorization", "").removeprefix("Bearer "),
        )
        if request.cookies.get(COOKIE):
            store.logout(request.cookies[COOKIE])
        if device_principal or principal["kind"] != "owner":
            from uuid import uuid4

            services.access.revoke((device_principal or principal)["id"], uuid4().hex)
        response.delete_cookie(COOKIE, path="/api")
        response.delete_cookie(DEVICE_COOKIE, path="/api")
        return {"signed_out": True}

    @app.get("/api/revision", dependencies=[Depends(authenticated)])
    def revision():
        return {"revision": store.revision()}

    @app.get("/api/phone/snapshot", dependencies=[Depends(authenticated)])
    def phone():
        return phone_snapshot(services)

    @app.get("/api/calendar", dependencies=[Depends(authenticated)])
    def calendar(start: datetime, end: datetime, display: bool = False):
        snapshot = store.snapshot(start, end)
        posture = services.posture.snapshot()
        hide_when_away = (
            display
            and posture["preferences"]["enabled"]
            and posture["preferences"]["privacy_when_away"]
            and (not posture["connected"] or posture["status"] in {"absent", "unknown", "paused"})
        )
        if hide_when_away:
            from .calendar import redact

            snapshot["occurrences"] = [redact(o, True) for o in snapshot["occurrences"]]
            with store.connection() as conn:
                snapshot["reminders"] = store.reminder_list(conn, {"hide_private": True})
        snapshot["automatic_privacy"] = bool(hide_when_away)
        snapshot["device"] = services.device_status()
        return snapshot

    @app.post("/api/events", dependencies=[Depends(authenticated)])
    def create_events(payload: CreateEvents, key=Depends(operation_id)):
        return store.create(payload, key)

    @app.get("/api/events/{event_id}", dependencies=[Depends(authenticated)])
    def read_event(event_id: str):
        with store.connection() as conn:
            return store.event(conn, event_id)

    @app.post("/api/events/{event_id}/actions", dependencies=[Depends(authenticated)])
    def event_action(event_id: str, payload: EventAction, key=Depends(operation_id)):
        return store.event_action(event_id, payload, key)

    @app.post("/api/reminders/{reminder_id}/actions", dependencies=[Depends(authenticated)])
    def reminder_action(reminder_id: str, payload: ReminderAction, key=Depends(operation_id)):
        return store.reminder_action(reminder_id, payload, key)

    @app.post("/api/settings", dependencies=[Depends(authenticated)])
    def settings(payload: SettingsInput, key=Depends(operation_id)):
        return store.update_settings(payload, key)

    @app.get("/api/records", dependencies=[Depends(authenticated)])
    def records(
        kind: str = "all", source: str = "all", start: date | None = None, end: date | None = None
    ):
        return {
            "records": services.data.record_rows(
                kind, source, str(start) if start else None, str(end) if end else None
            )
        }

    @app.get("/api/records.csv", dependencies=[Depends(authenticated)])
    def records_csv(
        kind: str = "all", source: str = "all", start: date | None = None, end: date | None = None
    ):
        return Response(
            services.data.records_csv(
                kind=kind,
                source=source,
                start=str(start) if start else None,
                end=str(end) if end else None,
            ),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="desk-records.csv"'},
        )

    @app.post("/api/workspace/preferences", dependencies=[Depends(authenticated)])
    def workspace_preferences(
        payload: PreferencesUpdate, key=Depends(operation_id), principal=Depends(authenticated)
    ):
        if (
            payload.preferences.weather_location == "automatic"
            and principal["kind"] != "owner"
            and services.data.preferences()["weather_location"] != "automatic"
        ):
            raise DomainError("OWNER_REQUIRED", 403)
        return services.data.update(payload, key)

    @app.post("/api/announcements/claim", dependencies=[Depends(authenticated)])
    def announcement(payload: dict):
        return services.data.claim_announcement(
            str(payload.get("client_id", "")),
            services.posture.snapshot(),
            services.tasks.listing(display=True)["tasks"],
        )

    @app.get("/api/diagnostics", dependencies=[Depends(owner)])
    def diagnostics():
        return diagnostics_report(services, app.version)

    @app.get("/api/diagnostics/page", dependencies=[Depends(owner)])
    def diagnostics_page():
        report = diagnostics_report(services, app.version)
        return HTMLResponse(
            diagnostics_html(report),
            headers={
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                )
            },
        )

    app.include_router(device_routes(services, authenticated, owner, agent, operation_id, limit))
    from .weather import weather_routes

    app.include_router(weather_routes(services.data, authenticated))
    app.include_router(task_routes(services, authenticated, operation_id))
    app.include_router(job_routes(services, owner, operation_id))
    app.include_router(permission_routes(services, owner, operation_id))
    app.include_router(memory_routes(services, owner, operation_id))
    app.include_router(memory_followup_routes(services, owner, operation_id))
    app.include_router(moment_routes(services, owner, operation_id))
    app.include_router(nudge_routes(services, owner, operation_id))
    app.include_router(notice_routes(services, owner, operation_id))
    app.include_router(push_routes(services, owner, operation_id))
    app.include_router(goal_routes(services, owner, operation_id))
    app.include_router(digest_routes(services, owner, operation_id))
    app.include_router(saved_skill_routes(services, owner, operation_id))
    app.include_router(profile_routes(services, owner, operation_id))
    app.include_router(persona_routes(services, owner, operation_id))
    app.include_router(assistant_routes(services, authenticated, operation_id))
    app.include_router(personal_routes(services, owner, operation_id))
    app.include_router(routine_routes(services, owner, operation_id))
    app.include_router(responsibility_routes(services, owner, operation_id))
    app.include_router(sources_routes(services, owner, operation_id))
    app.include_router(artifact_routes(services, owner, operation_id))
    app.include_router(agent_run_routes(services, owner, operation_id))
    app.include_router(browser_routes(services, owner, operation_id))
    app.include_router(connector_routes(services, owner, operation_id))
    app.include_router(work_search_routes(services, owner))
    app.include_router(work_capacity_routes(services, owner))
    app.include_router(public_capture_routes(services, owner, operation_id))
    app.include_router(shopping_routes(services, owner, operation_id))
    app.include_router(voice_routes(services, authenticated, agent, allowed_origins, limit))
    app.include_router(wake_routes(services, owner, allowed_origins))
    app.include_router(exchange_routes(services, authenticated, owner, operation_id))
    app.include_router(google_routes(services, owner, operation_id))
    app.include_router(mailbox_routes(services, owner, operation_id))
    from .outbound_mail import outbound_mail_routes

    app.include_router(outbound_mail_routes(services, owner, operation_id))
    from .app_connections import app_connections_routes

    app.include_router(app_connections_routes(services, owner))
    app.include_router(offline_calendar_routes(services, owner, operation_id))
    app.include_router(trip_routes(services, owner, operation_id))
    static_root = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    @app.get("/{path:path}", include_in_schema=False)
    def static(path: str):
        if (
            path == "api"
            or path.startswith("api/")
            or any(part.startswith(".") for part in Path(path).parts)
        ):
            raise HTTPException(404)
        candidate = (static_root / path).resolve()
        if not candidate.is_relative_to(static_root.resolve()):
            raise HTTPException(404)
        if not candidate.is_file():
            if Path(path).suffix:
                raise HTTPException(404)
            candidate = static_root / "index.html"
        if not candidate.is_file():
            raise HTTPException(
                503, "Frontend not built. Run npm ci and npm run build in frontend/."
            )
        return FileResponse(
            candidate,
            headers={
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            },
        )

    return app
