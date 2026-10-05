import asyncio
import contextlib
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .schemas import CreateEvents, EventAction, Login, ReminderAction, SettingsInput
from .store import DomainError, Store


COOKIE = "desk_companion_session"


def create_app(directory=None, clock=None, password=None, scheduler=True):
    runtime = (
        directory
        or os.environ.get("DESK_RUNTIME_DIR")
        or Path(__file__).resolve().parents[2] / ".runtime"
    )
    store = Store(runtime, clock=clock, password=password)
    attempts = defaultdict(deque)

    @asynccontextmanager
    async def lifespan(app):
        async def worker():
            while True:
                await asyncio.to_thread(store.tick)
                await asyncio.sleep(1)

        task = asyncio.create_task(worker()) if scheduler else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Desk Companion", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )

    @app.middleware("http")
    async def local_request_boundary(request, call_next):
        origin = request.headers.get("origin")
        if origin:
            parts = urlsplit(origin)
            if (
                parts.scheme != "http"
                or parts.hostname not in {"localhost", "127.0.0.1", "testserver"}
                or parts.port not in {None, 5190, 8831, 5191, 8832}
            ):
                return JSONResponse({"error": {"code": "ORIGIN_NOT_ALLOWED"}}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith(
            "/api/"
        ):
            if request.headers.get("x-desk-request") != "1":
                return JSONResponse({"error": {"code": "REQUEST_HEADER_REQUIRED"}}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
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
        if not store.session_valid(request.cookies.get(COOKIE)):
            raise DomainError("AUTH_REQUIRED", 401)

    def operation_id(x_operation_id: str = Header(default="")):
        return x_operation_id

    @app.get("/api/health")
    def health():
        return {"service": "desk-companion", "status": "ok"}

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
            COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600, path="/api"
        )
        return {"username": "owner"}

    @app.get("/api/session", dependencies=[Depends(authenticated)])
    def session():
        with store.connection() as conn:
            return {"username": "owner", "settings": store.settings(conn)}

    @app.delete("/api/session", dependencies=[Depends(authenticated)])
    def logout(request: Request, response: Response):
        store.logout(request.cookies[COOKIE])
        response.delete_cookie(COOKIE, path="/api")
        return {"signed_out": True}

    @app.get("/api/revision", dependencies=[Depends(authenticated)])
    def revision():
        return {"revision": store.revision()}

    @app.get("/api/calendar", dependencies=[Depends(authenticated)])
    def calendar(start: datetime, end: datetime):
        return store.snapshot(start, end)

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
    def records():
        return {"records": store.records()}

    return app
