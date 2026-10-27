from fastapi import APIRouter, Depends
from .assistant import AssistantMessage, ProposalDecision
from .store import DomainError


def assistant_routes(runtime, authenticated, operation_id):
    router = APIRouter(prefix="/api/assistant", dependencies=[Depends(authenticated)])

    @router.post("/messages")
    def message(
        payload: AssistantMessage, key=Depends(operation_id), principal=Depends(authenticated)
    ):
        return runtime.text_ai.message(payload, key, allow_memory=principal["kind"] == "owner")

    @router.get("/tool-calls")
    def tool_calls(limit: int = 50, principal=Depends(authenticated)):
        if principal["kind"] != "owner":
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        return {"calls": runtime.assistant.audit.listing(limit)}

    @router.get("/proposals")
    def proposals(principal=Depends(authenticated)):
        return {"proposals": runtime.assistant.proposals(allow_memory=principal["kind"] == "owner")}

    @router.post("/proposals/{proposal_id}/decisions")
    def decide(
        proposal_id: str,
        payload: ProposalDecision,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        return runtime.assistant.decide(
            proposal_id, payload.action, key, allow_memory=principal["kind"] == "owner"
        )

    return router
