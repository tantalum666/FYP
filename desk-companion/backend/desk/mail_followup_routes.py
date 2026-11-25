from fastapi import APIRouter, Depends, Request

from .mail_followup_models import MailFollowupAcknowledge, MailFollowupDraft, MailFollowupQuery
from .mail_reply_reminder import ReplyDraftRequest, ReplyRead, SampleFollow


def mail_followup_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/mail-followups", dependencies=[Depends(owner)])

    def visible(request: Request, principal=Depends(owner)):
        actor = {**principal, "session": request.cookies.get("desk_companion_session")}
        runtime.personal_context.require_visible(actor)
        return actor

    @router.get("/sample", dependencies=[Depends(visible)])
    def sample(principal=Depends(visible)):
        return runtime.mail_replies.catalog(principal)

    @router.post("/sample/follow", dependencies=[Depends(visible)])
    def follow_sample(payload: SampleFollow, principal=Depends(visible), key=Depends(operation_id)):
        return runtime.mail_replies.follow(payload.thread_id, key, principal)

    @router.post("/sample/replies", dependencies=[Depends(visible)])
    def simulate_reply(principal=Depends(visible), key=Depends(operation_id)):
        return runtime.mail_replies.simulate(key, principal)

    @router.get("/reminders", dependencies=[Depends(visible)])
    def reminders(task_id: str | None = None, principal=Depends(visible)):
        return runtime.mail_replies.reminders(principal, task_id)

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

    @router.post("/{followup_id}/reads", dependencies=[Depends(visible)])
    def read_message(followup_id: str, payload: ReplyRead, principal=Depends(visible), key=Depends(operation_id)):
        return runtime.mail_replies.read(followup_id, payload.message_id, key, principal)

    @router.post("/{followup_id}/reread", dependencies=[Depends(visible)])
    def reread(followup_id: str, principal=Depends(visible), key=Depends(operation_id)):
        return runtime.mail_replies.reread(followup_id, key, principal)

    @router.post("/{followup_id}/reply-drafts", dependencies=[Depends(visible)])
    def reply_draft(
        followup_id: str, payload: ReplyDraftRequest, principal=Depends(visible), key=Depends(operation_id)
    ):
        return runtime.mail_replies.draft(followup_id, payload, key, principal)

    @router.post("/{followup_id}/forget", dependencies=[Depends(visible)])
    def forget(followup_id: str, principal=Depends(visible), key=Depends(operation_id)):
        return runtime.mail_replies.forget(followup_id, key, principal)

    return router
