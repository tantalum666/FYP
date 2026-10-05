from fastapi import APIRouter, Depends
from .assistant import AssistantMessage, ProposalDecision


def assistant_routes(runtime, authenticated, operation_id):
    router = APIRouter(prefix="/api/assistant", dependencies=[Depends(authenticated)])

    @router.post("/messages")
    def message(payload: AssistantMessage, key=Depends(operation_id)):
        return runtime.text_ai.message(payload, key)

    @router.get("/proposals")
    def proposals():
        return {"proposals": runtime.assistant.proposals()}

    @router.post("/proposals/{proposal_id}/decisions")
    def decide(proposal_id: str, payload: ProposalDecision, key=Depends(operation_id)):
        return runtime.assistant.decide(proposal_id, payload.action, key)

    return router
