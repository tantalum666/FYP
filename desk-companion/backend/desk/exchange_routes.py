import json
from fastapi import APIRouter, Depends, Header, Response
from .exchange import BackupInput, ImportApply, ImportFile, ShareInput


def exchange_routes(runtime, authenticated, owner, operation_id):
    router = APIRouter(prefix="/api")

    @router.post("/exchange/ics/preview", dependencies=[Depends(authenticated)])
    def preview(payload: ImportFile, key=Depends(operation_id)):
        return runtime.exchange.preview_ics(payload, key)

    @router.post("/exchange/{preview_id}/apply", dependencies=[Depends(authenticated)])
    def apply(
        preview_id: str,
        payload: ImportApply,
        key=Depends(operation_id),
        principal=Depends(authenticated),
    ):
        return runtime.exchange.apply(
            preview_id, payload, key, allow_backup=principal["kind"] == "owner"
        )

    @router.get("/exchange/calendar.ics", dependencies=[Depends(owner)])
    def export():
        return Response(
            runtime.exchange.export_ics(),
            media_type="text/calendar",
            headers={"Content-Disposition": 'attachment; filename="desk-calendar.ics"'},
        )

    @router.get("/exchange/backup.json", dependencies=[Depends(owner)])
    def backup():
        return Response(
            json.dumps(runtime.exchange.backup(), ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="desk-backup.json"'},
        )

    @router.post("/exchange/backup/preview", dependencies=[Depends(owner)])
    def restore(payload: BackupInput, key=Depends(operation_id)):
        return runtime.exchange.preview_backup(payload, key)

    @router.post("/shares", dependencies=[Depends(owner)])
    def share(payload: ShareInput, key=Depends(operation_id)):
        return runtime.exchange.create_share(payload, key)

    @router.get("/shares", dependencies=[Depends(owner)])
    def shares():
        return {"shares": runtime.exchange.shares()}

    @router.post("/shares/{share_id}/revoke", dependencies=[Depends(owner)])
    def revoke(share_id: str, key=Depends(operation_id)):
        return runtime.exchange.revoke(share_id, key)

    @router.get("/share/view")
    def shared(x_desk_share: str = Header(default="")):
        return runtime.exchange.shared(x_desk_share)

    return router
