"""Shared browser OAuth lifecycle for registered Google/Microsoft app manifests."""

import base64
import hashlib
import json
import os
import secrets
import stat
import threading
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import uuid4
import httpx
from .access import digest
from .calendar import iso
from .store import DomainError, encode
from .vault import Vault

from .app_specs import SPECS, SCOPES, CALLBACKS


def app_client_config(resource):
    prefix = "DESK_GOOGLE_" if SPECS[resource]["provider"] == "google" else "DESK_MICROSOFT_"
    config = {
        name: os.environ.get(prefix + name.upper(), "")
        for name in ("client_id", "client_secret", "redirect_uri")
    }
    if resource == "gmail":
        config["redirect_uri"] = os.environ.get("DESK_GMAIL_REDIRECT_URI", "")
    path = os.environ.get(prefix + "CLIENT_FILE", "")
    if path:
        target = Path(path).expanduser()
        if not target.is_absolute() or target.is_symlink():
            raise ValueError("GOOGLE_CLIENT_FILE_INVALID")
        with os.fdopen(os.open(target, os.O_RDONLY | os.O_NOFOLLOW), "rb") as file:
            info = os.fstat(file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > 32768
            ):
                raise ValueError("GOOGLE_CLIENT_FILE_INVALID")
            data = json.load(file).get("web", {})
        config["client_id"] = config["client_id"] or data.get("client_id", "")
        config["client_secret"] = config["client_secret"] or data.get("client_secret", "")
        choices = [
            uri
            for uri in data.get("redirect_uris", [])
            if isinstance(uri, str) and urlsplit(uri).path == CALLBACKS[resource]
        ]
        config["redirect_uri"] = config["redirect_uri"] or next(iter(choices), "")
        config["redirect_uris"] = choices
    return config


class AppOAuth:
    def __init__(self, runtime, transport=None, config=None, *, resource="calendar"):
        self.runtime, self.store = runtime, runtime.store
        self.transport = transport
        if resource not in SCOPES:
            raise ValueError("Unsupported Google app")
        self.resource = resource
        self.provider = SPECS[resource]["provider"]
        tenant = "organizations" if SPECS[resource].get("organization_only") else "common"
        self.authorization_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            if self.provider == "google"
            else f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
        )
        self.token_url = (
            "https://oauth2.googleapis.com/token"
            if self.provider == "google"
            else f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        )
        self.state_table = "google_oauth" if resource == "calendar" else resource + "_oauth"
        self.account_table = (
            "google_connection" if resource == "calendar" else resource + "_connection"
        )
        self.config = config or app_client_config(resource)
        self.lock = threading.RLock()
        self.vault = Vault(self.store.directory)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS oauth_flow_results(flow_id TEXT PRIMARY KEY, resource TEXT NOT NULL, session_hash TEXT NOT NULL, status TEXT NOT NULL, expires_at TEXT NOT NULL)"
            )
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self.state_table}(state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, session_hash TEXT NOT NULL, expires_at TEXT NOT NULL)"
            )
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self.account_table}(id INTEGER PRIMARY KEY CHECK(id=1), encrypted_tokens TEXT NOT NULL, connected_at TEXT NOT NULL, last_read TEXT)"
            )

    def configured(self):
        return bool(
            bool(self.config.get("client_id"))
            and (self.provider == "microsoft" or bool(self.config.get("client_secret")))
            and self.valid_redirect(self.config["redirect_uri"])
        )

    def valid_redirect(self, uri):
        parts = urlsplit(uri)
        return bool(
            (
                parts.scheme == "https"
                or parts.scheme == "http"
                and parts.hostname in {"127.0.0.1", "localhost"}
            )
            and parts.path == CALLBACKS[self.resource]
            and not parts.query
            and not parts.fragment
            and not parts.username
        )

    def snapshot(self):
        with self.store.connection() as conn:
            row = conn.execute(
                f"SELECT connected_at,last_read FROM {self.account_table} WHERE id=1"
            ).fetchone()
        return {
            "configured": self.configured(),
            "connected": bool(row),
            "mode": "send_after_review"
            if self.resource in {"gmail", "microsoft365"}
            else "read_only_preview",
            "connected_at": row["connected_at"] if row else None,
            "last_read": row["last_read"] if row else None,
        }

    def begin(self, owner_session, origin=None):
        if not self.configured():
            raise DomainError(
                "GOOGLE_NOT_CONFIGURED" if self.resource == "calendar" else "APP_NOT_CONFIGURED",
                409,
            )
        if not self.store.session_valid(owner_session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        redirect_uri = self.config["redirect_uri"]
        if origin:
            incoming = urlsplit(origin)
            for candidate in [redirect_uri, *self.config.get("redirect_uris", [])]:
                parts = urlsplit(candidate)
                if (
                    self.valid_redirect(candidate)
                    and parts.scheme == incoming.scheme
                    and parts.hostname == incoming.hostname
                    and parts.port == incoming.port
                ):
                    redirect_uri = candidate
                    break
            else:
                raise DomainError("APP_CALLBACK_UNAVAILABLE", 409)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        with self.lock, self.store.connection(write=True) as conn:
            conn.execute(
                "DELETE FROM oauth_flow_results WHERE expires_at<=?", (iso(self.store.clock()),)
            )
            conn.execute(
                "UPDATE oauth_flow_results SET status='cancelled' WHERE resource=? AND status IN ('pending','exchanging')",
                (self.resource,),
            )
            conn.execute(f"DELETE FROM {self.state_table}")
            conn.execute(
                f"INSERT INTO {self.state_table} VALUES(?,?,?,?)",
                (
                    digest(state),
                    self.vault.encrypt(
                        encode({"verifier": verifier, "redirect_uri": redirect_uri})
                    ),
                    digest(owner_session),
                    iso(self.store.clock() + timedelta(minutes=10)),
                ),
            )
            conn.execute(
                "INSERT INTO oauth_flow_results VALUES(?,?,?,'pending',?)",
                (
                    digest(state),
                    self.resource,
                    digest(owner_session),
                    iso(self.store.clock() + timedelta(minutes=10)),
                ),
            )
            conn.execute(
                "DELETE FROM oauth_flow_results WHERE flow_id NOT IN (SELECT flow_id FROM oauth_flow_results ORDER BY expires_at DESC LIMIT 100)"
            )
        return {
            "flow_id": digest(state),
            "url": self.authorization_url
            + "?"
            + urlencode(
                {
                    "client_id": self.config["client_id"],
                    "redirect_uri": redirect_uri,
                    "response_type": "code",
                    "scope": " ".join(SCOPES[self.resource]),
                    "state": state,
                    **(
                        {"access_type": "offline"}
                        if self.provider == "google"
                        else {"response_mode": "query"}
                    ),
                    "prompt": "consent" if self.provider == "google" else "select_account",
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            ),
        }

    def code(self, suffix):
        return ("GOOGLE_" if self.resource == "calendar" else "APP_") + suffix

    def _request(self, method, url, **kwargs):
        try:
            with httpx.Client(
                timeout=12, transport=self.transport, follow_redirects=False, trust_env=False
            ) as client:
                response = client.request(method, url, **kwargs)
                if len(response.content) > 3_000_000:
                    raise ValueError()
                data = response.json() if response.content else {}
                if not isinstance(data, dict):
                    raise ValueError()
                if (
                    url == self.token_url
                    and response.status_code in {400, 401}
                    and data.get("error") == "invalid_grant"
                ):
                    raise DomainError(self.code("RECONNECT_REQUIRED"), 409)
                response.raise_for_status()
                return data
        except (httpx.HTTPError, ValueError):
            raise DomainError(self.code("CONNECTION_FAILED"), 502) from None

    def callback(self, state, code):
        try:
            return self._callback(state, code)
        except DomainError:
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "UPDATE oauth_flow_results SET status='failed' WHERE flow_id=? AND status='exchanging'",
                    (digest(state),),
                )
            raise

    def _callback(self, state, code):
        if not self.configured() or len(state) > 200 or len(code) > 3000:
            raise DomainError("OAUTH_EXPIRED", 403)
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                f"SELECT * FROM {self.state_table} WHERE state_hash=? AND expires_at>?",
                (digest(state), iso(self.store.clock())),
            ).fetchone()
            if (
                not row
                or not conn.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (row["session_hash"], iso(self.store.clock())),
                ).fetchone()
            ):
                raise DomainError("OAUTH_EXPIRED", 403)
            conn.execute(f"DELETE FROM {self.state_table} WHERE state_hash=?", (digest(state),))
            conn.execute(
                "UPDATE oauth_flow_results SET status='exchanging' WHERE flow_id=? AND status='pending'",
                (digest(state),),
            )
        raw_verifier = self.vault.decrypt(row["verifier"])
        try:
            binding = json.loads(raw_verifier)
        except ValueError:
            binding = {"verifier": raw_verifier, "redirect_uri": self.config["redirect_uri"]}
        if (
            not isinstance(binding, dict)
            or not isinstance(binding.get("verifier"), str)
            or not self.valid_redirect(binding.get("redirect_uri", ""))
        ):
            raise DomainError("OAUTH_EXPIRED", 403)
        data = self._request(
            "POST",
            self.token_url,
            data={
                "client_id": self.config["client_id"],
                **(
                    {"client_secret": self.config["client_secret"]}
                    if self.config.get("client_secret")
                    else {}
                ),
                "redirect_uri": binding["redirect_uri"],
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": binding["verifier"],
            },
        )
        tokens = self._tokens(data)
        if not tokens.get("refresh_token"):
            raise DomainError(self.code("RECONNECT_REQUIRED"), 409)
        with self.store.connection() as conn:
            active = conn.execute(
                "SELECT 1 FROM oauth_flow_results f JOIN sessions s ON f.session_hash=s.token_hash WHERE f.flow_id=? AND f.status='exchanging' AND f.expires_at>? AND s.expires>?",
                (digest(state), iso(self.store.clock()), iso(self.store.clock())),
            ).fetchone()
        if not active:
            raise DomainError("OAUTH_EXPIRED", 403)
        tokens.update(self.identity(tokens["access_token"]))
        tokens["connection_id"] = uuid4().hex
        with self.lock, self.store.connection(write=True) as conn:
            if not conn.execute(
                "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                (row["session_hash"], iso(self.store.clock())),
            ).fetchone():
                raise DomainError("OAUTH_EXPIRED", 403)
            status = conn.execute(
                "SELECT status FROM oauth_flow_results WHERE flow_id=?", (digest(state),)
            ).fetchone()
            if not status or status[0] != "exchanging":
                raise DomainError("OAUTH_EXPIRED", 403)
            conn.execute(
                f"INSERT INTO {self.account_table} VALUES(1,?,?,NULL) ON CONFLICT(id) DO UPDATE SET encrypted_tokens=excluded.encrypted_tokens,connected_at=excluded.connected_at,last_read=NULL",
                (self.vault.encrypt(encode(tokens)), iso(self.store.clock())),
            )
            self.store.record(
                conn,
                ("google" if self.resource == "calendar" else self.resource) + "_connected",
                details={
                    "mode": "read_only_preview"
                    if self.resource == "calendar"
                    else "send_after_review"
                },
            )
            self.store.bump(conn)
            conn.execute(
                "UPDATE oauth_flow_results SET status='connected' WHERE flow_id=?", (digest(state),)
            )

    def _tokens(self, data, refresh=None):
        try:
            if (
                not isinstance(data["access_token"], str)
                or not 1 <= len(data["access_token"]) <= 10000
            ):
                raise ValueError()
            if isinstance(data["expires_in"], bool):
                raise ValueError()
            expires = int(data["expires_in"])
            if not 1 <= expires <= 86400:
                raise ValueError()
            refresh_token = data.get("refresh_token") or refresh
            if refresh_token is not None and (
                not isinstance(refresh_token, str) or not 1 <= len(refresh_token) <= 10000
            ):
                raise ValueError()
            granted = set(data["scope"].split()) if "scope" in data else set(SCOPES[self.resource])
            if (
                self.resource == "calendar"
                and "https://www.googleapis.com/auth/calendar.readonly" in granted
            ):
                granted.add(SCOPES["calendar"][0])
            if "https://www.googleapis.com/auth/userinfo.email" in granted:
                granted.add("email")
            required = set(SCOPES[self.resource])
            if self.provider == "microsoft":
                granted = {value.removeprefix("https://graph.microsoft.com/") for value in granted}
                required -= {"openid", "email", "offline_access"}
            if not required.issubset(granted):
                raise ValueError()
            return {
                "access_token": data["access_token"],
                "refresh_token": refresh_token,
                "expires_at": iso(self.store.clock() + timedelta(seconds=expires)),
            }
        except (ValueError, TypeError, KeyError):
            raise DomainError(self.code("SCOPE_REQUIRED"), 409) from None

    def access_token(self):
        with self.lock:
            with self.store.connection() as conn:
                row = conn.execute(
                    f"SELECT encrypted_tokens FROM {self.account_table} WHERE id=1"
                ).fetchone()
            if not row:
                raise DomainError(
                    "GOOGLE_NOT_CONNECTED" if self.resource == "calendar" else "APP_NOT_CONNECTED",
                    409,
                )
            tokens = json.loads(self.vault.decrypt(row[0]))
            if tokens["expires_at"] <= iso(self.store.clock() + timedelta(seconds=60)):
                response = self._request(
                    "POST",
                    self.token_url,
                    data={
                        "client_id": self.config["client_id"],
                        **(
                            {"client_secret": self.config["client_secret"]}
                            if self.config.get("client_secret")
                            else {}
                        ),
                        "grant_type": "refresh_token",
                        **(
                            {"scope": " ".join(SCOPES[self.resource])}
                            if self.provider == "microsoft"
                            else {}
                        ),
                        "refresh_token": tokens["refresh_token"],
                    },
                )
                tokens = {**tokens, **self._tokens(response, tokens["refresh_token"])}
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        f"UPDATE {self.account_table} SET encrypted_tokens=? WHERE id=1",
                        (self.vault.encrypt(encode(tokens)),),
                    )
            return tokens["access_token"]

    def disconnect(self):
        with self.lock:
            with self.store.connection(write=True) as conn:
                row = conn.execute(
                    f"SELECT encrypted_tokens FROM {self.account_table} WHERE id=1"
                ).fetchone()
                conn.execute(f"DELETE FROM {self.account_table}")
                conn.execute(f"DELETE FROM {self.state_table}")
                conn.execute(
                    "UPDATE oauth_flow_results SET status='cancelled' WHERE resource=? AND status IN ('pending','exchanging')",
                    (self.resource,),
                )
                self.store.record(
                    conn,
                    ("google" if self.resource == "calendar" else self.resource) + "_disconnected",
                )
                self.store.bump(conn)
            revoked = True
            if row and self.provider == "google":
                tokens = json.loads(self.vault.decrypt(row[0]))
                try:
                    self._request(
                        "POST",
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": tokens.get("refresh_token") or tokens["access_token"]},
                    )
                except DomainError:
                    revoked = False
            return {
                "disconnected": True,
                "provider_revocation_confirmed": revoked if self.provider == "google" else False,
            }

    def identity(self, access_token):
        if self.resource == "calendar":
            return {}
        info = self._request(
            "GET",
            "https://openidconnect.googleapis.com/v1/userinfo"
            if self.provider == "google"
            else "https://graph.microsoft.com/v1.0/me?$select=id,mail,userPrincipalName",
            headers={"Authorization": "Bearer " + access_token},
        )
        from .outbound_mail_models import address

        try:
            if self.provider == "google" and info.get("email_verified") is not True:
                raise ValueError()
            email = address(
                info["email"]
                if self.provider == "google"
                else info.get("mail") or info["userPrincipalName"]
            )
        except (ValueError, TypeError, KeyError):
            raise DomainError(self.code("ACCOUNT_UNVERIFIED"), 403) from None
        return {"email": email}

    def account(self):
        state = self.snapshot()
        with self.store.connection() as conn:
            row = conn.execute(
                f"SELECT encrypted_tokens FROM {self.account_table} WHERE id=1"
            ).fetchone()
        tokens = json.loads(self.vault.decrypt(row[0])) if row else {}
        return {
            **state,
            "email": tokens.get("email"),
            "version": tokens.get("connection_id", "disconnected"),
        }

    def cancel(self, flow_id, session):
        with self.lock, self.store.connection(write=True) as conn:
            conn.execute(
                f"DELETE FROM {self.state_table} WHERE state_hash=? AND session_hash=?",
                (flow_id, digest(session)),
            )
            conn.execute(
                "UPDATE oauth_flow_results SET status='cancelled' WHERE flow_id=? AND session_hash=? AND status IN ('pending','exchanging')",
                (flow_id, digest(session)),
            )
        return {"cancelled": True}

    def flow_status(self, flow_id, session):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT status FROM oauth_flow_results WHERE flow_id=? AND resource=? AND session_hash=? AND expires_at>?",
                (flow_id, self.resource, digest(session), iso(self.store.clock())),
            ).fetchone()
        return {"status": row[0] if row else "expired"}

    def reject(self, state):
        if not isinstance(state, str) or len(state) > 200:
            raise DomainError("OAUTH_EXPIRED", 403)
        with self.lock, self.store.connection(write=True) as conn:
            row = conn.execute(
                f"SELECT session_hash FROM {self.state_table} WHERE state_hash=? AND expires_at>?",
                (digest(state), iso(self.store.clock())),
            ).fetchone()
            if (
                not row
                or not conn.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (row["session_hash"], iso(self.store.clock())),
                ).fetchone()
            ):
                raise DomainError("OAUTH_EXPIRED", 403)
            conn.execute(f"DELETE FROM {self.state_table} WHERE state_hash=?", (digest(state),))
            conn.execute(
                "UPDATE oauth_flow_results SET status='declined' WHERE flow_id=? AND status='pending'",
                (digest(state),),
            )
