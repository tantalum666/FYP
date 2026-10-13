from fastapi import APIRouter, Depends, Request
from .assistant import AssistantMessage, ProposalDecision


def assistant_routes(runtime, authenticated, operation_id):
    router = APIRouter(prefix="/api/assistant", dependencies=[Depends(authenticated)])

    @router.post("/messages")
    def message(
        payload: AssistantMessage,
        request: Request,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        if principal.get("kind") == "owner":
            principal = {**principal, "session": request.cookies.get("desk_companion_session")}
        return runtime.text_ai.message(payload, key, principal=principal)

    @router.get("/proposals")
    def proposals(request: Request, principal=Depends(authenticated)):
        if principal.get("kind") == "owner":
            principal = {**principal, "session": request.cookies.get("desk_companion_session")}
        return {
            "proposals": runtime.agent_runs.filter_proposals(
                runtime.assistant.proposals(
                    personal_context=runtime.personal_context.visible(principal)
                ),
                principal,
            )
        }

    @router.post("/proposals/{proposal_id}/decisions")
    def decide(
        proposal_id: str,
        payload: ProposalDecision,
        request: Request,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        if principal.get("kind") == "owner":
            principal = {**principal, "session": request.cookies.get("desk_companion_session")}
        runtime.agent_runs.require_proposal_access(proposal_id, principal, action=payload.action)
        return runtime.assistant.decide(
            proposal_id,
            payload.action,
            key,
            personal_context=runtime.personal_context.visible(principal),
        )

    return router
