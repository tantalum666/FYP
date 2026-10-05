"""Explicitly approved, individually revocable clients; no password in QR codes."""

import hashlib
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, field_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError
from .vault import Vault


DEVICE_COOKIE = "desk_companion_device"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class PairingIssue(StrictModel):
    kind: Literal["controller", "display"] = "controller"


class PairingRequest(StrictModel):
    code: str = Field(pattern=r"^[0-9]{8}$")
    name: str = Field(min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("A device name is required")
        return value.strip()


class PairingDecision(StrictModel):
    request_id: str = Field(min_length=16, max_length=64)
    action: Literal["approve", "reject"]


class PairingClaim(StrictModel):
    request_id: str = Field(min_length=16, max_length=64)
    secret: str = Field(min_length=30, max_length=100)


class EnrolDisplay(StrictModel):
    name: str = Field(default="Desk display", min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        return PairingRequest.nonblank_name(value)


class AccessService:
    def __init__(self, store):
        self.store = store
        self.vault = Vault(store.directory)
        with store.connection(write=True) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trusted_clients (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS pairing_codes (
                    id TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS pairing_requests (
                    id TEXT PRIMARY KEY, code_id TEXT NOT NULL, name TEXT NOT NULL,
                    secret_hash TEXT NOT NULL, check_code TEXT NOT NULL, state TEXT NOT NULL,
                    expires_at TEXT NOT NULL, client_id TEXT, encrypted_token TEXT);
            """)
        path = Path(store.directory) / "agent.json"
        if not path.exists():
            try:
                with path.open("x") as stream:
                    os.chmod(path, 0o600)
                    json.dump({"token": secrets.token_urlsafe(32)}, stream)
            except FileExistsError:
                pass
        self.agent_hash = digest(json.loads(path.read_text())["token"])

    def agent_valid(self, token):
        return bool(token) and secrets.compare_digest(digest(token), self.agent_hash)

    def principal(self, owner_token=None, device_token=None, bearer=None):
        if owner_token and self.store.session_valid(owner_token):
            return {"kind": "owner", "id": "owner", "name": "Owner"}
        token = bearer or device_token
        if not token:
            return None
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM trusted_clients WHERE token_hash=? AND revoked=0", (digest(token),)
            ).fetchone()
            if not row:
                return None
            now = iso(self.store.clock())
            if row["last_seen"] < iso(self.store.clock() - timedelta(minutes=1)):
                conn.execute("UPDATE trusted_clients SET last_seen=? WHERE id=?", (now, row["id"]))
            return {"kind": row["kind"], "id": row["id"], "name": row["name"]}

    def _enrol(self, conn, name, kind):
        if conn.execute("SELECT COUNT(*) FROM trusted_clients WHERE revoked=0").fetchone()[0] >= 20:
            raise DomainError("DEVICE_LIMIT", 422)
        token = secrets.token_urlsafe(32)
        client_id, now = uuid4().hex, iso(self.store.clock())
        conn.execute(
            "INSERT INTO trusted_clients VALUES(?,?,?,?,?,?,0)",
            (client_id, name, kind, digest(token), now, now),
        )
        self.store.record(
            conn, "device_paired", details={"client_id": client_id, "name": name, "kind": kind}
        )
        return client_id, token

    def enrol_display(self, name, key):
        def apply(conn):
            client_id, token = self._enrol(conn, name, "display")
            return {"client_id": client_id, "encrypted_token": self.vault.encrypt(token)}

        result = self.store.operation(key, {"type": "enrol_display", "name": name}, apply)
        return {
            "client_id": result["client_id"],
            "token": self.vault.decrypt(result["encrypted_token"]),
        }

    def issue(self, kind, key):
        def apply(conn):
            conn.execute("UPDATE pairing_codes SET used=1 WHERE used=0")
            code = f"{secrets.randbelow(100_000_000):08d}"
            expires = iso(self.store.clock() + timedelta(minutes=2))
            code_id = uuid4().hex
            conn.execute(
                "INSERT INTO pairing_codes VALUES(?,?,?,?,0)",
                (code_id, digest(code), kind, expires),
            )
            return {"encrypted_code": self.vault.encrypt(code), "expires_at": expires, "kind": kind}

        result = self.store.operation(key, {"type": "pairing_issue", "kind": kind}, apply)
        return {
            "code": self.vault.decrypt(result["encrypted_code"]),
            "expires_at": result["expires_at"],
            "kind": kind,
        }

    def request(self, payload):
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM pairing_codes WHERE code_hash=? AND used=0 AND expires_at>?",
                (digest(payload.code), iso(self.store.clock())),
            ).fetchone()
            if not row:
                raise DomainError("PAIRING_EXPIRED", 410)
            request_id, secret = uuid4().hex, secrets.token_urlsafe(32)
            check_code = f"{secrets.randbelow(10_000):04d}"
            conn.execute(
                "INSERT INTO pairing_requests VALUES(?,?,?,?,?,'pending',?,NULL,NULL)",
                (
                    request_id,
                    row["id"],
                    payload.name.strip(),
                    digest(secret),
                    check_code,
                    iso(self.store.clock() + timedelta(minutes=5)),
                ),
            )
            conn.execute("UPDATE pairing_codes SET used=1 WHERE id=?", (row["id"],))
            self.store.bump(conn)
            return {
                "request_id": request_id,
                "secret": secret,
                "check_code": check_code,
                "state": "pending",
            }

    def decide(self, payload, key):
        def apply(conn):
            row = conn.execute(
                "SELECT r.*,c.kind FROM pairing_requests r JOIN pairing_codes c ON c.id=r.code_id WHERE r.id=?",
                (payload.request_id,),
            ).fetchone()
            if not row or row["state"] != "pending" or row["expires_at"] <= iso(self.store.clock()):
                raise DomainError("PAIRING_EXPIRED", 410)
            client_id, encrypted = None, None
            if payload.action == "approve":
                client_id, token = self._enrol(conn, row["name"], row["kind"])
                encrypted = self.vault.encrypt(token)
            state = "approved" if payload.action == "approve" else "rejected"
            conn.execute(
                "UPDATE pairing_requests SET state=?,client_id=?,encrypted_token=? WHERE id=?",
                (state, client_id, encrypted, row["id"]),
            )
            return {"state": state, "client_id": client_id}

        return self.store.operation(
            key, {"type": "pairing_decision", **payload.model_dump()}, apply
        )

    def claim(self, payload):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT * FROM pairing_requests WHERE id=?", (payload.request_id,)
            ).fetchone()
            if not row or not secrets.compare_digest(row["secret_hash"], digest(payload.secret)):
                raise DomainError("PAIRING_EXPIRED", 410)
            if row["expires_at"] <= iso(self.store.clock()) or row["state"] == "revoked":
                raise DomainError("PAIRING_EXPIRED", 410)
            if row["state"] == "approved":
                client = conn.execute(
                    "SELECT revoked FROM trusted_clients WHERE id=?", (row["client_id"],)
                ).fetchone()
                if not client or client["revoked"]:
                    raise DomainError("PAIRING_EXPIRED", 410)
                return {
                    "state": "approved",
                    "client_id": row["client_id"],
                    "token": self.vault.decrypt(row["encrypted_token"]),
                }
            return {"state": row["state"]}

    def listing(self):
        with self.store.connection() as conn:
            return {
                "clients": [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id,name,kind,created_at,last_seen FROM trusted_clients WHERE revoked=0 ORDER BY created_at DESC"
                    )
                ],
                "requests": [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id,name,check_code,expires_at FROM pairing_requests WHERE state='pending' AND expires_at>?",
                        (iso(self.store.clock()),),
                    )
                ],
            }

    def revoke(self, client_id, key):
        def apply(conn):
            cursor = conn.execute("UPDATE trusted_clients SET revoked=1 WHERE id=?", (client_id,))
            if not cursor.rowcount:
                raise DomainError("DEVICE_NOT_FOUND", 404)
            conn.execute(
                "UPDATE pairing_requests SET encrypted_token=NULL,state='revoked' WHERE client_id=?",
                (client_id,),
            )
            self.store.record(conn, "device_revoked", details={"client_id": client_id})
            return {"revoked": client_id}

        return self.store.operation(key, {"type": "revoke_device", "id": client_id}, apply)
