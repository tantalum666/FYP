"""Owner-only review of exact connector intents; no model-facing approval tool."""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from .schemas import StrictModel


class ConnectorApproval(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    intent_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_only: bool = Field(strict=True)


class ConnectorCancel(StrictModel):
    expected_version: int = Field(ge=1, strict=True)


def metadata(item):
    fields = {"id", "state", "version", "code", "created_at", "updated_at", "expires_at",
              "dispatched", "cancel_requested", "verified"}
    return {key: value for key, value in item.items() if key in fields}


def connector_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/connectors", dependencies=[Depends(owner)])
    service = runtime.connectors

    def principal(request):
        # Revalidate the real session in the service, not an owner-shaped assertion.
        return {"kind": "owner", "session": request.cookies.get("desk_companion_session")}

    @router.get("/capabilities")
    def capabilities(request: Request):
        return service.catalog(principal(request))

    @router.get("/intents")
    def listing(request: Request, limit: int = Query(50, ge=1, le=100),
                metadata_only: bool = False):
        return service.listing(principal(request), limit=limit, metadata_only=metadata_only)

    @router.get("/intents/{intent_id}")
    def detail(intent_id: str, request: Request, metadata_only: bool = False):
        item = service.detail(intent_id, principal(request))
        return {"intent": metadata(item) if metadata_only else item}

    @router.post("/intents/{intent_id}/approve")
    def approve(intent_id: str, payload: ConnectorApproval, request: Request,
                key=Depends(operation_id)):
        return {"intent": service.approve(
            intent_id, payload.expected_version, payload.intent_hash, principal(request),
            public_only=payload.public_only,
        )}

    @router.post("/intents/{intent_id}/cancel")
    def cancel(intent_id: str, payload: ConnectorCancel, request: Request,
               metadata_only: bool = False, key=Depends(operation_id)):
        item = service.cancel(
            intent_id, principal(request), expected_version=payload.expected_version,
        )
        if metadata_only:
            item = metadata(item)
        return {"intent": item}

    return router
