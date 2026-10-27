"""Web Push behind DESK_WEB_PUSH=1. Keys stay on this machine. Tests do not use the network.

The private key file is mode 0600. Sending uses a replaceable sender. Quiet hours
and the notice id still decide whether anything is sent; this module does not
add a second schedule.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import APIRouter, Depends
from pydantic import Field, field_validator

from .schemas import StrictModel
from .store import DomainError

SUBJECT = "mailto:desk-companion@localhost"
_RECORD = 4096


def push_enabled() -> bool:
    return os.environ.get("DESK_WEB_PUSH") == "1"


def b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(value: str) -> bytes:
    import base64

    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _write_secret(path: Path, pem: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, pem)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


class VapidKeys:
    def __init__(self, private, path: Path):
        self.private, self.path = private, path

    @classmethod
    def load_or_create(cls, path: Path):
        path = Path(path)
        if path.exists():
            os.chmod(path, 0o600)
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            return cls(key, path)
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        _write_secret(path, pem)
        return cls(key, path)

    def public_uncompressed(self) -> bytes:
        return self.private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )

    def authorization(self, endpoint: str, now: datetime) -> str:
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or not parts.netloc:
            raise DomainError("PUSH_ENDPOINT_INVALID", 422)
        header = b64url(b'{"typ":"JWT","alg":"ES256"}')
        payload = b64url(
            json.dumps(
                {
                    "aud": f"{parts.scheme}://{parts.netloc}",
                    "exp": int(now.timestamp()) + 12 * 3600,
                    "sub": SUBJECT,
                },
                separators=(",", ":"),
            ).encode()
        )
        signing = f"{header}.{payload}".encode()
        der = self.private.sign(signing, ec.ECDSA(hashes.SHA256()))
        raw_r, raw_s = decode_dss_signature(der)
        signature = b64url(raw_r.to_bytes(32, "big") + raw_s.to_bytes(32, "big"))
        return f"vapid t={header}.{payload}.{signature},k={b64url(self.public_uncompressed())}"


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def encrypt(payload: bytes, ua_public: bytes, auth: bytes) -> bytes:
    """aes128gcm body for one subscription (RFC 8291)."""
    if len(ua_public) != 65 or len(auth) != 16:
        raise DomainError("PUSH_KEY_INVALID", 422)
    local = ec.generate_private_key(ec.SECP256R1())
    as_public = local.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    client = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    shared = local.exchange(ec.ECDH(), client)
    ikm = _hkdf(auth, shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    salt = os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    header = salt + _RECORD.to_bytes(4, "big") + bytes([len(as_public)]) + as_public
    return header + ciphertext


def decrypt(body: bytes, client_private, auth: bytes) -> bytes:
    """Inverse of ``encrypt``, used to prove the body is readable by the subscriber."""
    salt, rs, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
    as_public, ciphertext = body[21 : 21 + idlen], body[21 + idlen :]
    ua_public = client_private.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    server = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public)
    shared = client_private.exchange(ec.ECDH(), server)
    ikm = _hkdf(auth, shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    del rs
    plain = AESGCM(cek).decrypt(nonce, ciphertext, None)
    return plain[: plain.rfind(b"\x02")]


class HttpPushSender:
    """POSTs one encrypted body. Pass a transport in tests so nothing leaves the process."""

    def __init__(self, transport=None):
        self.transport = transport

    def send(self, endpoint: str, body: bytes, headers: dict) -> None:
        with httpx.Client(timeout=8, transport=self.transport, follow_redirects=False) as client:
            response = client.post(endpoint, content=body, headers=headers)
            response.raise_for_status()


class PushService:
    def __init__(self, store, sender, key_path: Path):
        self.store, self.sender = store, sender
        self.keys = VapidKeys.load_or_create(Path(key_path))
        with store.connection(write=True) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS push_subscriptions(
                    id TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL UNIQUE,
                    p256dh TEXT NOT NULL,
                    auth TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT
                )"""
            )

    def public_key(self) -> str:
        return b64url(self.keys.public_uncompressed())

    def save(self, endpoint: str, p256dh: str, auth: str, key: str) -> dict:
        ua_public, secret = b64url_decode(p256dh), b64url_decode(auth)
        if len(ua_public) != 65 or len(secret) != 16:
            raise DomainError("PUSH_KEY_INVALID", 422)
        self.keys.authorization(endpoint, self.store.clock())

        def apply(conn):
            from .calendar import iso

            row = conn.execute(
                "SELECT id, revoked_at FROM push_subscriptions WHERE endpoint=?", (endpoint,)
            ).fetchone()
            now = iso(self.store.clock())
            if row:
                conn.execute(
                    "UPDATE push_subscriptions SET p256dh=?, auth=?, revoked_at=NULL WHERE id=?",
                    (p256dh, auth, row["id"]),
                )
                sub_id = row["id"]
            else:
                sub_id = uuid4().hex
                conn.execute(
                    "INSERT INTO push_subscriptions VALUES(?,?,?,?,?,NULL)",
                    (sub_id, endpoint, p256dh, auth, now),
                )
            self.store.record(conn, "push_subscription_saved", details={"id": sub_id})
            return {"id": sub_id, "revoked": False}

        return self.store.operation(
            key, {"type": "push_subscribe", "endpoint": endpoint, "p256dh": p256dh}, apply
        )

    def revoke(self, sub_id: str, key: str) -> dict:
        def apply(conn):
            from .calendar import iso

            row = conn.execute(
                "SELECT id FROM push_subscriptions WHERE id=?", (sub_id,)
            ).fetchone()
            if not row:
                raise DomainError("PUSH_NOT_FOUND", 404)
            conn.execute(
                "UPDATE push_subscriptions SET revoked_at=? WHERE id=?",
                (iso(self.store.clock()), sub_id),
            )
            self.store.record(conn, "push_subscription_revoked", details={"id": sub_id})
            return {"id": sub_id, "revoked": True}

        return self.store.operation(key, {"type": "push_revoke", "id": sub_id}, apply)

    def dispatch(self, payload: dict) -> int:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM push_subscriptions WHERE revoked_at IS NULL"
            ).fetchall()
        sent = 0
        for row in rows:
            try:
                body = encrypt(raw, b64url_decode(row["p256dh"]), b64url_decode(row["auth"]))
                headers = {
                    "Authorization": self.keys.authorization(row["endpoint"], self.store.clock()),
                    "Content-Encoding": "aes128gcm",
                    "Content-Type": "application/octet-stream",
                    "TTL": "60",
                }
                self.sender.send(row["endpoint"], body, headers)
                sent += 1
            except (httpx.HTTPError, OSError, ValueError, DomainError):
                continue
        return sent


class PushSubscriptionInput(StrictModel):
    endpoint: str = Field(min_length=12, max_length=500)
    p256dh: str = Field(min_length=80, max_length=200)
    auth: str = Field(min_length=16, max_length=64)

    @field_validator("endpoint")
    @classmethod
    def https_endpoint(cls, value):
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("Use an https push endpoint")
        return value


def push_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/push", dependencies=[Depends(owner)])

    @router.get("")
    def status():
        service = runtime.notify.push
        if service is None:
            return {"enabled": False, "public_key": None}
        return {"enabled": True, "public_key": service.public_key()}

    @router.post("/subscriptions")
    def subscribe(payload: PushSubscriptionInput, key=Depends(operation_id)):
        service = runtime.notify.push
        if service is None:
            raise DomainError("PUSH_DISABLED", 404)
        return service.save(payload.endpoint, payload.p256dh, payload.auth, key)

    @router.post("/subscriptions/{sub_id}/revocations")
    def revoke(sub_id: str, key=Depends(operation_id)):
        service = runtime.notify.push
        if service is None:
            raise DomainError("PUSH_DISABLED", 404)
        return service.revoke(sub_id, key)

    return router
