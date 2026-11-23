"""The only financial entry point is an explicit, versioned confirmation in the private form."""

import ipaddress
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Request
from pydantic import Field

from ..conversation import memory_context
from ..schemas import StrictModel
from ..store import DomainError


class SourceChoice(StrictModel):
    conversation_id: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=64)
    proposal_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    job_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class Action(StrictModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    version: int = Field(strict=True, ge=1)
    action: Literal[
        "search", "select", "status", "verify_seller", "verify_original", "other_offers"
    ]
    share_seller_page: bool = Field(default=False, strict=True)
    number: int | None = Field(default=None, strict=True, ge=1, le=8)


class Confirm(StrictModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    version: int = Field(strict=True, ge=1)
    amount_minor: int = Field(strict=True, gt=0)
    currency: Literal["HKD"]
    confirm_purchase: Literal[True]
    passengers: list[dict[str, Annotated[str, Field(max_length=200)]]] = Field(
        min_length=1, max_length=9
    )
    contact_email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def routes(runtime, authenticated):
    router = APIRouter(prefix="/flight-checkouts")
    service = runtime.live_flight_checkouts

    def who(request: Request, principal=Depends(authenticated)):
        scoped = {**principal, "session": request.cookies.get("desk_companion_session")}
        service.owner(scoped)
        return scoped

    @router.post("/source")
    def select_source(req: SourceChoice, principal=Depends(who)):
        if bool(req.proposal_id) == bool(req.job_id):
            raise DomainError("FLIGHT_SOURCE_NOT_FOUND", 422)
        if req.task_id:
            from ..conversation import task_context

            task_context(runtime, principal, req.task_id)
        chats = runtime.voice.conversations
        revision, _ = memory_context(runtime, True)
        try:
            chat = chats.open(principal, revision, req.conversation_id, task_id=req.task_id)
        except DomainError as error:
            if error.code != "CONVERSATION_NOT_FOUND":
                raise
            recover = service.can_resume(principal, req.conversation_id, None, req.task_id)
            chat = chats.open(
                principal,
                revision,
                req.conversation_id if recover else None,
                task_id=req.task_id,
                recover_review=recover,
            )
        pid = req.proposal_id
        if req.job_id:
            with runtime.store.connection() as db:
                found = db.execute(
                    """SELECT p.id FROM assistant_proposals p JOIN operations o
                    ON o.id='browser-research/prepare/' || p.id JOIN computer_jobs j
                    ON j.id=json_extract(o.response,'$.job.id') WHERE p.kind='browser_research' AND j.id=?
                    AND json_extract(j.request,'$.session_hash')=? AND json_extract(j.request,'$.task_id') IS ?
                    AND json_extract(j.request,'$.quote_request.provider')='kiwi'""",
                    (req.job_id, chat.owner, chat.task_id),
                ).fetchone()
            if not found:
                raise DomainError("FLIGHT_SOURCE_NOT_FOUND", 404)
            pid = found["id"]
        return {
            "conversation_id": chat.id,
            "live_flight_checkout": service.start(principal, chat, pid),
        }

    @router.get("/{ident}")
    def get(ident: str, conversation_id: str, principal=Depends(who)):
        return service.view(principal, conversation_id, ident)

    @router.post("/{ident}/actions")
    def act(ident: str, req: Action, principal=Depends(who)):
        return service.action(
            principal,
            req.conversation_id,
            ident,
            req.action,
            req.version,
            req.number,
            req.share_seller_page,
        )

    @router.post("/{ident}/confirm")
    def pay(ident: str, req: Confirm, request: Request, principal=Depends(who)):
        if request.url.scheme != "https":
            try:
                local = ipaddress.ip_address(request.client.host).is_loopback
            except (ValueError, AttributeError):
                local = False
            if not local or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise DomainError("FLIGHT_SECURE_FORM_REQUIRED", 403)
        return service.confirm(
            principal,
            req.conversation_id,
            ident,
            req.version,
            req.amount_minor,
            req.currency,
            req.passengers,
            req.contact_email,
        )

    return router
