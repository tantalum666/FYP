from fastapi import APIRouter, Depends, Request, Response

from .cookies import cookie_secure
from .access import (
    DEVICE_COOKIE,
    EnrolDisplay,
    PairingClaim,
    PairingDecision,
    PairingIssue,
    PairingRequest,
)
from .outputs import OutputHeartbeat, OutputReceipt, OutputRequest
from .posture import ObservationBatch, PostureAction
from .store import DomainError


def device_routes(runtime, authenticated, owner, agent, operation_id, limit):
    router = APIRouter(prefix="/api")

    def device_cookie(response, token, request):
        response.set_cookie(
            DEVICE_COOKIE,
            token,
            httponly=True,
            samesite="strict",
            secure=cookie_secure(request),
            max_age=365 * 86400,
            path="/api",
        )

    @router.get("/workspace")
    def workspace(principal=Depends(authenticated)):
        return runtime.snapshot(principal)

    @router.post("/posture/actions", dependencies=[Depends(authenticated)])
    def posture_action(payload: PostureAction, key=Depends(operation_id)):
        return runtime.posture.action(payload, key)

    @router.post("/pairing/codes", dependencies=[Depends(owner)])
    def issue(payload: PairingIssue, key=Depends(operation_id)):
        return runtime.access.issue(payload.kind, key)

    @router.post("/pairing/requests")
    def pair_request(payload: PairingRequest, request: Request):
        limit("pairing", request, 8, 60)
        return runtime.access.request(payload)

    @router.post("/pairing/decisions", dependencies=[Depends(owner)])
    def pair_decision(payload: PairingDecision, key=Depends(operation_id)):
        return runtime.access.decide(payload, key)

    @router.post("/pairing/claim")
    def pair_claim(payload: PairingClaim, request: Request, response: Response):
        limit("claim", request, 120, 60)
        result = runtime.access.claim(payload)
        if token := result.pop("token", None):
            device_cookie(response, token, request)
            # Native clients obtain this secret once and retain it in Keychain.
            if request.headers.get("X-Desk-Native") == "1":
                result["token"] = token
        return result

    @router.post("/devices/enrol-display", dependencies=[Depends(owner)])
    def enrol(
        payload: EnrolDisplay, request: Request, response: Response, key=Depends(operation_id)
    ):
        result = runtime.access.enrol_display(payload.name, key)
        device_cookie(response, result.pop("token"), request)
        return result

    @router.post("/devices/{client_id}/revoke", dependencies=[Depends(owner)])
    def revoke(client_id: str, key=Depends(operation_id)):
        return runtime.access.revoke(client_id, key)

    @router.get("/agent/config", dependencies=[Depends(agent)])
    def agent_config():
        posture = runtime.posture.snapshot()
        return {
            "camera_enabled": posture["preferences"]["enabled"] and not posture["paused"],
            "calibration_phase": posture["calibration"]["phase"],
            "output_stopped": runtime.outputs.snapshot()["stopped"],
            "replay_allowed": runtime.allow_replay,
            "voice_enabled": runtime.data.preferences()["voice_enabled"]
            and runtime.voice.config.valid(),
        }

    @router.post("/agent/observations", dependencies=[Depends(agent)])
    def observations(payload: ObservationBatch):
        if payload.source == "replay" and not runtime.allow_replay:
            raise DomainError("REPLAY_NOT_ENABLED", 403)
        return runtime.posture.ingest(payload)

    @router.post("/agent/outputs/heartbeat", dependencies=[Depends(agent)])
    def heartbeat(payload: OutputHeartbeat):
        if payload.source == "replay" and not runtime.allow_replay:
            raise DomainError("REPLAY_NOT_ENABLED", 403)
        return runtime.outputs.heartbeat(payload)

    @router.post("/agent/outputs/claim", dependencies=[Depends(agent)])
    def claim():
        return runtime.outputs.claim()

    @router.post("/agent/outputs/{command_id}/receipt", dependencies=[Depends(agent)])
    def receipt(command_id: str, payload: OutputReceipt):
        return runtime.outputs.receipt(command_id, payload)

    @router.post("/outputs/stop", dependencies=[Depends(authenticated)])
    def stop(key=Depends(operation_id)):
        return runtime.outputs.emergency_stop(key)

    @router.post("/outputs/enable", dependencies=[Depends(owner)])
    def enable(key=Depends(operation_id)):
        return runtime.outputs.enable(key)

    @router.post("/outputs/commands", dependencies=[Depends(authenticated)])
    def output(payload: OutputRequest, key=Depends(operation_id)):
        return runtime.outputs.request(payload, key)

    return router
