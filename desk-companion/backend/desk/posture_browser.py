"""Owner-bound, short-lived admission for locally computed camera landmarks.

Frames never cross this endpoint. One browser supplies observations at a time;
the device camera agent is disabled while the browser source is selected.
"""

import hashlib
import secrets
import threading

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from .calendar import iso
from .posture import ObservationBatch
from .schemas import StrictModel
from .store import DomainError


class BrowserCamera(StrictModel):
    client_id: str = Field(pattern=r"^[a-f0-9-]{32,36}$")
    camera_id: str = Field(min_length=1, max_length=120)


class BrowserObservations(StrictModel):
    lease: str = Field(pattern=r"^[a-f0-9]{48}$")
    batch: ObservationBatch


class BrowserPosture:
    def __init__(self, runtime):
        self.runtime = runtime
        self.lock = threading.RLock()
        self.lease = None

    def current(self, session):
        if not session or not self.runtime.store.session_valid(session):
            raise DomainError("OWNER_REQUIRED", 403)
        p = self.runtime.posture.snapshot()
        if (
            not p["preferences"]["enabled"]
            or p["paused"]
            or p["preferences"].get("camera_source", "device") != "browser"
        ):
            raise DomainError("POSTURE_CAPTURE_DISABLED", 409)
        self.runtime.personal_context.require_visible({"kind": "owner"})
        return hashlib.sha256(session.encode()).hexdigest()

    def claim(self, payload, session):
        with self.lock:
            owner = self.current(session)
            now = self.runtime.store.clock().timestamp()
            same_client = (
                self.lease
                and self.lease["owner"] == owner
                and self.lease["client"] == payload.client_id
            )
            if self.lease and now < self.lease["expires"] and not same_client:
                raise DomainError("POSTURE_CAMERA_BUSY", 409)
            self.lease = {
                "token": secrets.token_hex(24),
                "owner": owner,
                "client": payload.client_id,
                "camera": payload.camera_id,
                "boot": secrets.token_hex(16),
                "expires": now + 4,
            }
            return {
                "lease": self.lease["token"],
                "boot_id": self.lease["boot"],
                "server_time": iso(self.runtime.store.clock()),
            }

    def ingest(self, payload, session):
        with self.lock:
            owner = self.current(session)
            now = self.runtime.store.clock().timestamp()
            lease = self.lease
            if (
                not lease
                or not secrets.compare_digest(payload.lease, lease["token"])
                or lease["owner"] != owner
                or now >= lease["expires"]
            ):
                raise DomainError("POSTURE_CAMERA_LEASE_EXPIRED", 409)
            if (
                payload.batch.source != "live"
                or payload.batch.boot_id != lease["boot"]
                or any(o.camera_id != lease["camera"] for o in payload.batch.observations)
            ):
                raise DomainError("POSTURE_CAMERA_SOURCE_CHANGED", 409)
            result = self.runtime.posture.ingest(payload.batch)
            lease["expires"] = now + 4
            return result

    def release(self, token, session):
        with self.lock:
            owner = hashlib.sha256((session or "").encode()).hexdigest()
            if (
                self.lease
                and self.lease["owner"] == owner
                and secrets.compare_digest(token, self.lease["token"])
            ):
                self.lease = None
            return {"released": True}


def browser_posture_routes(runtime, owner):
    router = APIRouter(prefix="/posture/browser", dependencies=[Depends(owner)])

    @router.post("/session")
    def claim(payload: BrowserCamera, request: Request):
        return runtime.browser_posture.claim(payload, request.cookies.get("desk_companion_session"))

    @router.post("/observations")
    def ingest(payload: BrowserObservations, request: Request):
        return runtime.browser_posture.ingest(
            payload, request.cookies.get("desk_companion_session")
        )

    @router.delete("/session/{token}")
    def release(token: str, request: Request):
        return runtime.browser_posture.release(token, request.cookies.get("desk_companion_session"))

    return router
