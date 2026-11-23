"""Public-client LetsFG OAuth. Approval, callback binding and encryption are shared with Apps."""

from datetime import timedelta
import hashlib
import json
import os
import re
from urllib.parse import urlsplit

from ..app_oauth import AppOAuth
from ..calendar import iso
from ..store import DomainError, encode

ISSUER = "https://letsfg.co/developers/api"
METADATA = ISSUER + "/.well-known/oauth-authorization-server"
RESOURCE = "https://letsfg.co/.well-known/oauth-protected-resource/mcp"
REGISTER = ISSUER + "/oauth/register"
CALLBACK = "/api/apps/letsfg/callback"


def metadata_has(document, key, *required):
    values = document.get(key)
    return isinstance(values, list) and all(value in values for value in required)


def callback_uris():
    configured = os.getenv("DESK_LETSFG_REDIRECT_URI")
    public = os.getenv("DESK_PUBLIC_ORIGIN", "").rstrip("/")
    urls = ([configured] if configured else []) + ([public + CALLBACK] if public else [])
    urls += [
        f"http://{host}:{port}{CALLBACK}"
        for port in (5190, 8831, 5191, 8832, 8891)
        for host in ("127.0.0.1", "localhost")
    ]
    return list(dict.fromkeys(urls))


class LetsFGAccount(AppOAuth):
    def __init__(self, runtime, transport=None, config=None):
        uris = callback_uris()
        super().__init__(
            runtime,
            transport,
            config or {"client_id": "", "redirect_uri": uris[0], "redirect_uris": uris},
            resource="letsfg",
        )
        self.registration_key = hashlib.sha256(
            encode(self.config.get("redirect_uris", [])).encode()
        ).hexdigest()
        with self.store.connection(write=True) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS letsfg_oauth_client(redirect_hash TEXT PRIMARY KEY, client_id TEXT NOT NULL)"
            )
            row = db.execute(
                "SELECT client_id FROM letsfg_oauth_client WHERE redirect_hash=?",
                (self.registration_key,),
            ).fetchone()
        if row and not self.config.get("client_id"):
            self.config["client_id"] = row[0]

    def valid_redirect(self, uri):
        if not isinstance(uri, str):
            return False
        try:
            p = urlsplit(uri)
            if not p.hostname or p.username is not None or p.password is not None or p.port == 0:
                return False
            return super().valid_redirect(uri)
        except ValueError:
            return False

    def _tokens(self, data, refresh=None):
        if str(data.get("token_type", "")).casefold() != "bearer":
            raise DomainError("LETSFG_CONNECT_REQUIRED", 409)
        return super()._tokens({"expires_in": 3600, **data}, refresh)

    def configured(self):
        return self.valid_redirect(self.config["redirect_uri"]) and all(
            self.valid_redirect(u) for u in self.config.get("redirect_uris", [])
        )

    def identity(self, access_token):
        # The agent grant contains only flights:search and flights:book.
        return {}

    def begin(self, owner_session, origin=None):
        if not self.store.session_valid(owner_session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if not self.configured():
            raise DomainError("APP_NOT_CONFIGURED", 409)
        if origin == "capacitor://localhost":
            origin = None  # Open the backend's configured callback in the system browser.
        if origin:
            parts = urlsplit(origin)
            if not any(
                (urlsplit(uri).scheme, urlsplit(uri).netloc) == (parts.scheme, parts.netloc)
                for uri in [self.config["redirect_uri"], *self.config.get("redirect_uris", [])]
            ):
                raise DomainError("APP_CALLBACK_UNAVAILABLE", 409)
        with self.lock:
            if not self.config.get("client_id"):
                metadata = self._request("GET", METADATA)
                protected = self._request("GET", RESOURCE)
                if (
                    metadata.get("issuer") != ISSUER
                    or metadata.get("registration_endpoint") != REGISTER
                    or metadata.get("authorization_endpoint") != self.authorization_url
                    or metadata.get("token_endpoint") != self.token_url
                    or not metadata_has(metadata, "code_challenge_methods_supported", "S256")
                    or not metadata_has(metadata, "token_endpoint_auth_methods_supported", "none")
                    or not metadata_has(
                        metadata, "scopes_supported", "flights:search", "flights:book"
                    )
                    or protected.get("resource") != "https://letsfg.co/mcp"
                    or not metadata_has(protected, "authorization_servers", ISSUER)
                ):
                    raise DomainError("LETSFG_DISCOVERY_UNVERIFIED", 502)
                uris = self.config.get("redirect_uris", [self.config["redirect_uri"]])
                registration = self._request(
                    "POST",
                    REGISTER,
                    json={
                        "client_name": "FYP Desk Companion",
                        "redirect_uris": uris,
                        "grant_types": ["authorization_code", "refresh_token"],
                        "response_types": ["code"],
                        "token_endpoint_auth_method": "none",
                    },
                )
                ident = registration.get("client_id")
                if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", ident):
                    raise DomainError("LETSFG_DISCOVERY_UNVERIFIED", 502)
                with self.store.connection(write=True) as db:
                    db.execute(
                        "INSERT OR IGNORE INTO letsfg_oauth_client VALUES(?,?)",
                        (self.registration_key, ident),
                    )
                    self.config["client_id"] = db.execute(
                        "SELECT client_id FROM letsfg_oauth_client WHERE redirect_hash=?",
                        (self.registration_key,),
                    ).fetchone()[0]
            return super().begin(owner_session, origin)

    def access_token(self, principal=None):
        return self.grant(principal)[0]

    def snapshot(self):
        state = super().snapshot()
        if state["connected"]:
            with self.store.connection() as db:
                row = db.execute(
                    "SELECT encrypted_tokens FROM letsfg_connection WHERE id=1"
                ).fetchone()
            if row:
                tokens = json.loads(self.vault.decrypt(row[0]))
                if not tokens.get("refresh_token") and tokens.get("rotating_until", "") <= iso(
                    self.store.clock()
                ):
                    state["connected"] = False
        return state

    def grant(self, principal, expected_version=None):
        if (
            not isinstance(principal, dict)
            or principal.get("kind") != "owner"
            or not self.store.session_valid(principal.get("session"))
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        with self.lock:
            now = self.store.clock()
            with self.store.connection(write=True) as db:
                row = db.execute(
                    "SELECT encrypted_tokens FROM letsfg_connection WHERE id=1"
                ).fetchone()
                if not row:
                    raise DomainError("LETSFG_CONNECT_REQUIRED", 409)
                tokens = json.loads(self.vault.decrypt(row[0]))
                version = tokens["connection_id"]
                if expected_version and expected_version != version:
                    raise DomainError("LETSFG_ACCOUNT_CHANGED", 409)
                if tokens["expires_at"] > iso(now + timedelta(seconds=60)):
                    return tokens["access_token"], version
                refresh = tokens.get("refresh_token")
                if not refresh:
                    code = (
                        "LETSFG_REFRESH_PENDING"
                        if tokens.get("rotating_until", "") > iso(now)
                        else "LETSFG_CONNECT_REQUIRED"
                    )
                    raise DomainError(code, 409)
                # The provider revokes the entire grant on reuse. Commit consumption
                # before sending it, including when processes restart or an ACK is lost.
                reserved = {
                    **tokens,
                    "refresh_token": None,
                    "rotating_until": iso(now + timedelta(seconds=30)),
                }
                claim = self.vault.encrypt(encode(reserved))
                db.execute("UPDATE letsfg_connection SET encrypted_tokens=? WHERE id=1", (claim,))
            try:
                response = self._request(
                    "POST",
                    self.token_url,
                    data={
                        "client_id": tokens["client_id"],
                        "refresh_token": refresh,
                        "grant_type": "refresh_token",
                    },
                )
                renewed = self._tokens(response)
                if not renewed.get("refresh_token") or renewed["refresh_token"] == refresh:
                    raise DomainError("LETSFG_CONNECT_REQUIRED", 409)
            except DomainError:
                raise DomainError("LETSFG_CONNECT_REQUIRED", 409) from None
            with self.store.connection(write=True) as db:
                updated = db.execute(
                    "UPDATE letsfg_connection SET encrypted_tokens=? WHERE id=1 AND encrypted_tokens=?",
                    (self.vault.encrypt(encode({**tokens, **renewed})), claim),
                ).rowcount
                if not updated:
                    raise DomainError("LETSFG_ACCOUNT_CHANGED", 409)
            return renewed["access_token"], version
