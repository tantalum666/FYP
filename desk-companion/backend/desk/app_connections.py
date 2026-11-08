"""Installed app catalog and browser OAuth. Account grants never become model tools."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import Field
from .app_specs import SPECS, SCOPES
from .access import digest
from .schemas import StrictModel
from .store import DomainError


class DisconnectApp(StrictModel):
    expected_version: str = Field(min_length=1, max_length=80)


class CancelAppAuthorization(StrictModel):
    flow_id: str = Field(pattern=r"^[a-f0-9]{64}$")


def app_connections_routes(runtime, owner):
    router = APIRouter(prefix="/api/apps")

    def resolve(app_id):
        if app_id == "gmail":
            return runtime.outbound_mail.auth
        if app_id == "calendar":
            return runtime.google
        if app_id in runtime.microsoft.auth:
            return runtime.microsoft.auth[app_id]
        raise DomainError("APP_NOT_AVAILABLE", 404)

    @router.get("", dependencies=[Depends(owner)])
    def catalog():
        return {
            "apps": [
                {
                    "id": name,
                    "name": spec["name"],
                    "provider": spec["provider"],
                    "auth": "oauth2_pkce",
                    "transport": "google_api"
                    if spec["provider"] == "google"
                    else "microsoft_graph",
                    "capabilities": list(spec["capabilities"]),
                    "organization_only": bool(spec.get("organization_only")),
                    "scopes": list(SCOPES[name]),
                    "bundled": True,
                    **resolve(name).account(),
                }
                for name, spec in SPECS.items()
            ],
            "mcp": [
                {
                    "id": config.id,
                    "name": config.server_name,
                    "endpoint": config.endpoint,
                    "tools": len(config.tools),
                    "data_policy": "public_or_synthetic",
                }
                for config in runtime.connectors.configs.values()
            ],
        }

    @router.post("/{app_id}/connect", dependencies=[Depends(owner)])
    def begin(app_id: str, request: Request):
        return resolve(app_id).begin(
            request.cookies.get("desk_companion_session"), request.headers.get("origin")
        )

    @router.post("/{app_id}/cancel", dependencies=[Depends(owner)])
    def cancel(app_id: str, payload: CancelAppAuthorization, request: Request):
        return resolve(app_id).cancel(
            payload.flow_id, request.cookies.get("desk_companion_session")
        )

    @router.get("/{app_id}/authorization/{flow_id}", dependencies=[Depends(owner)])
    def flow_status(app_id: str, flow_id: str, request: Request):
        return resolve(app_id).flow_status(flow_id, request.cookies.get("desk_companion_session"))

    @router.post("/{app_id}/disconnect", dependencies=[Depends(owner)])
    def disconnect(app_id: str, payload: DisconnectApp):
        if app_id == "gmail":
            return runtime.outbound_mail.disconnect(payload.expected_version)
        if app_id == "microsoft365":
            return runtime.outbound_mail.disconnect(payload.expected_version, "outlook")
        auth = resolve(app_id)
        with auth.lock:
            if auth.account()["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            return {**auth.disconnect(), **auth.account()}

    @router.get("/gmail/callback")
    def gmail_callback(state: str = "", code: str = "", error: str = ""):
        return complete("gmail", state, code, error)

    @router.get("/microsoft/callback")
    def microsoft_callback(state: str = "", code: str = "", error: str = ""):
        if len(state) > 200:
            raise DomainError("OAUTH_EXPIRED", 403)
        with runtime.store.connection() as conn:
            row = conn.execute(
                "SELECT resource FROM oauth_flow_results WHERE flow_id=?", (digest(state),)
            ).fetchone()
        if not row or row[0] not in runtime.microsoft.auth:
            raise DomainError("OAUTH_EXPIRED", 403)
        return complete(row[0], state, code, error)

    def complete(app_id, state, code, error):
        auth = resolve(app_id)
        name = SPECS[app_id]["name"]
        if error:
            auth.reject(state)
            message = name + " connection cancelled. You can return to Alice."
        else:
            auth.callback(state, code)
            message = name + " connected. You can return to Alice."
        return HTMLResponse(
            '<!doctype html><html lang="en"><head><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Alice · Apps</title><link rel="stylesheet" href="/oauth-complete.css"><script src="/oauth-complete.js" defer></script></head><body><main><h1>'
            + message
            + '</h1><a href="/?page=device">Return to Alice</a></main></body></html>',
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            },
        )

    return router
