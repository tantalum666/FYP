"""Owner HTTP for offline trip quotes. Paired devices are rejected."""

from fastapi import APIRouter, Depends, Request
from pydantic import Field, model_validator

from ..schemas import StrictModel
from ..store import DomainError


class TripConnect(StrictModel):
    fixture_id: str = Field(min_length=1, max_length=41)


class TripSync(StrictModel):
    disconnect_after: int | None = Field(default=None, ge=0, le=100)


class TripQuoteAction(StrictModel):
    quote_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    quote_version: int = Field(ge=1)
    expected_task_version: int = Field(ge=1)
    next_step: str | None = Field(default=None, max_length=500)
    waiting_for: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def omit_clears(self):
        for name in ("next_step", "waiting_for"):
            value = getattr(self, name)
            if name in self.model_fields_set and (value is None or not str(value).strip()):
                raise ValueError("Omit a field to leave it unchanged")
        return self


def trip_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/trips", dependencies=[Depends(owner)])

    def principal(request: Request):
        token = request.cookies.get("desk_companion_session")
        if not runtime.store.session_valid(token):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        who = {"kind": "owner", "id": "owner", "name": "Owner", "session": token}
        runtime.personal_context.require_visible(who)
        return who

    @router.get("/connections")
    def listing(request: Request):
        return runtime.trips.listing(principal(request))

    @router.post("/connections")
    def connect(payload: TripConnect, request: Request, key=Depends(operation_id)):
        return runtime.trips.connect(payload.fixture_id, key, principal(request))

    @router.get("/connections/{connection_id}")
    def snapshot(connection_id: str, request: Request):
        return runtime.trips.snapshot(connection_id, principal(request))

    @router.post("/connections/{connection_id}/sync")
    def sync(connection_id: str, request: Request, payload: TripSync = TripSync()):
        return runtime.trips.sync(
            connection_id, principal(request), disconnect_after=payload.disconnect_after
        )

    @router.post("/connections/{connection_id}/revocation")
    def revoke(connection_id: str, request: Request, key=Depends(operation_id)):
        return runtime.trips.revoke(connection_id, key, principal(request))

    @router.post("/connections/{connection_id}/holds")
    def hold(connection_id: str, payload: TripQuoteAction, request: Request, key=Depends(operation_id)):
        return runtime.trips.hold(connection_id, payload, key, principal(request))

    @router.post("/connections/{connection_id}/releases")
    def release(
        connection_id: str, payload: TripQuoteAction, request: Request, key=Depends(operation_id)
    ):
        return runtime.trips.release(connection_id, payload, key, principal(request))

    return router
