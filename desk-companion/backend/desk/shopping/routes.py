"""Owner HTTP for offline shopping fixtures. Paired devices are rejected."""

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from ..schemas import StrictModel
from ..store import DomainError


class ShoppingConnect(StrictModel):
    fixture_id: str = Field(min_length=1, max_length=41)


class ShoppingSync(StrictModel):
    disconnect_after: int | None = Field(default=None, ge=0, le=100)


def shopping_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/shopping", dependencies=[Depends(owner)])

    def principal(request: Request):
        token = request.cookies.get("desk_companion_session")
        if not runtime.store.session_valid(token):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"kind": "owner", "id": "owner", "name": "Owner", "session": token}

    @router.get("/connections")
    def listing(request: Request):
        return runtime.shopping.listing(principal(request))

    @router.post("/connections")
    def connect(payload: ShoppingConnect, request: Request, key=Depends(operation_id)):
        return runtime.shopping.connect(payload.fixture_id, key, principal(request))

    @router.get("/connections/{connection_id}")
    def snapshot(connection_id: str, request: Request):
        return runtime.shopping.snapshot(connection_id, principal(request))

    @router.post("/connections/{connection_id}/sync")
    def sync(
        connection_id: str,
        request: Request,
        payload: ShoppingSync = ShoppingSync(),
    ):
        return runtime.shopping.sync(
            connection_id, principal(request), disconnect_after=payload.disconnect_after
        )

    @router.post("/connections/{connection_id}/revocation")
    def revoke(connection_id: str, request: Request, key=Depends(operation_id)):
        return runtime.shopping.revoke(connection_id, key, principal(request))

    return router
