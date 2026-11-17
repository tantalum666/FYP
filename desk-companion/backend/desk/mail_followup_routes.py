from fastapi import APIRouter, Depends, Request

from .mail_followup_models import MailFollowupDraft, MailFollowupQuery, MailFollowupAcknowledge


def mail_followup_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/mail-followups", dependencies=[Depends(owner)])

    def visible(request: Request, principal=Depends(owner)):
        actor = {**principal, "session": request.cookies.get("desk_companion_session")}
        runtime.personal_context.require_visible(actor)
        return actor

    @router.post("/preview", dependencies=[Depends(visible)])
    def preview(payload: MailFollowupDraft, key=Depends(operation_id)):
        return runtime.mail_followups.draft(payload.model_dump(), key)

    @router.get("", dependencies=[Depends(visible)])
    def listing(query: MailFollowupQuery = Depends()):
        return runtime.mail_followups.listing(query)

    @router.post("/{followup_id}/stop")
    def stop(followup_id: str, key=Depends(operation_id)):
        return runtime.mail_followups.stop(followup_id, key)

    @router.post("/{followup_id}/acknowledge")
    def acknowledge(
        followup_id: str,
        payload: MailFollowupAcknowledge,
        principal=Depends(visible),
        key=Depends(operation_id),
    ):
        return runtime.mail_followups.acknowledge(
            followup_id, payload.observed_revision, key, principal
        )

    return router
