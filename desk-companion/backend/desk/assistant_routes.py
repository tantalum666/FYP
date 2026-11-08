from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .assistant import AssistantMessage, ProposalDecision
from .mailbox import proposal_kind, visible_proposals
from .offline_calendar import visible_proposals as visible_calendar_proposals
from .store import DomainError


def assistant_routes(runtime, authenticated, operation_id):
    router = APIRouter(prefix="/api/assistant", dependencies=[Depends(authenticated)])

    @router.post("/messages")
    def message(
        payload: AssistantMessage,
        request: Request,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        return runtime.text_ai.message(
            payload,
            key,
            allow_memory=principal["kind"] == "owner",
            principal={**principal, "session": request.cookies.get("desk_companion_session")},
        )

    @router.post("/messages/stream")
    def message_stream(
        payload: AssistantMessage,
        request: Request,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        stream = runtime.text_ai.event_stream(
            payload,
            key,
            allow_memory=principal["kind"] == "owner",
            principal={**principal, "session": request.cookies.get("desk_companion_session")},
        )
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @router.get("/tool-calls")
    def tool_calls(limit: int = 50, principal=Depends(authenticated)):
        if principal["kind"] != "owner":
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"calls": runtime.assistant.audit.listing(limit)}

    @router.get("/proposals")
    def proposals(request: Request, principal=Depends(authenticated)):
        principal = {**principal, "session": request.cookies.get("desk_companion_session")}
        proposals = visible_proposals(
            runtime.assistant.proposals(allow_memory=principal["kind"] == "owner"), principal
        )
        proposals = visible_calendar_proposals(proposals, principal)
        proposals = runtime.agent_runs.filter_proposals(proposals, principal)
        if principal["kind"] != "owner" or not runtime.store.session_valid(
            principal.get("session")
        ):
            proposals = [item for item in proposals if item.get("kind") != "shopping_advice"]
        return {"proposals": proposals}

    @router.post("/proposals/{proposal_id}/decisions")
    def decide(
        proposal_id: str,
        payload: ProposalDecision,
        request: Request,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        principal = {**principal, "session": request.cookies.get("desk_companion_session")}
        if (
            proposal_kind(runtime, proposal_id) in {"mailbox_reply", "calendar_advice", "email_send"}
            and principal["kind"] != "owner"
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if runtime.shopping.is_proposal(proposal_id):
            signed_in = principal["kind"] == "owner" and runtime.store.session_valid(
                principal.get("session")
            )
            if not signed_in:
                raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        runtime.agent_runs.require_proposal_access(proposal_id, principal, action=payload.action)
        return runtime.assistant.decide(
            proposal_id, payload.action, key, allow_memory=principal["kind"] == "owner"
        )

    return router
