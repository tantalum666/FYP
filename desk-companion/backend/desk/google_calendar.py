"""Optional Google Calendar read-only connection with previewed local updates.

Calendar account access is not needed to run the rest of the application. OAuth
credentials and tokens remain on the backend; this connector never writes Google.
"""

import base64
import hashlib
import json
import os
import secrets
import threading
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from .access import digest
from .calendar import iso
from .exchange import ShareInput
from .schemas import EventInput
from .store import DomainError, encode
from .vault import Vault

SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"


class GoogleCalendar:
    def __init__(self, runtime, transport=None, config=None):
        self.runtime, self.store = runtime, runtime.store
        self.transport = transport
        self.config = config or {
            name: os.environ.get("DESK_GOOGLE_" + name.upper(), "")
            for name in ("client_id", "client_secret", "redirect_uri")
        }
        self.lock = threading.RLock()
        self.vault = Vault(self.store.directory)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS google_oauth(state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, session_hash TEXT NOT NULL, expires_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS google_connection(id INTEGER PRIMARY KEY CHECK(id=1), encrypted_tokens TEXT NOT NULL, connected_at TEXT NOT NULL, last_read TEXT)"
            )

    def configured(self):
        parts = urlsplit(self.config["redirect_uri"])
        return bool(
            all(self.config.values())
            and (
                parts.scheme == "https"
                or parts.scheme == "http"
                and parts.hostname in {"127.0.0.1", "localhost"}
            )
            and parts.path == "/api/google/callback"
            and not parts.query
            and not parts.fragment
            and not parts.username
        )

    def snapshot(self):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT connected_at,last_read FROM google_connection WHERE id=1"
            ).fetchone()
        return {
            "configured": self.configured(),
            "connected": bool(row),
            "mode": "read_only_preview",
            "connected_at": row["connected_at"] if row else None,
            "last_read": row["last_read"] if row else None,
        }

    def begin(self, owner_session):
        if not self.configured():
            raise DomainError("GOOGLE_NOT_CONFIGURED", 409)
        if not self.store.session_valid(owner_session):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        with self.store.connection(write=True) as conn:
            conn.execute("DELETE FROM google_oauth WHERE expires_at<=?", (iso(self.store.clock()),))
            conn.execute(
                "INSERT INTO google_oauth VALUES(?,?,?,?)",
                (
                    digest(state),
                    self.vault.encrypt(verifier),
                    digest(owner_session),
                    iso(self.store.clock() + timedelta(minutes=10)),
                ),
            )
        return {
            "url": "https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode(
                {
                    "client_id": self.config["client_id"],
                    "redirect_uri": self.config["redirect_uri"],
                    "response_type": "code",
                    "scope": SCOPE,
                    "state": state,
                    "access_type": "offline",
                    "prompt": "consent",
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            )
        }

    def _request(self, method, url, **kwargs):
        try:
            with httpx.Client(
                timeout=12, transport=self.transport, follow_redirects=False
            ) as client:
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                if len(response.content) > 3_000_000:
                    raise ValueError()
                return response.json() if response.content else {}
        except (httpx.HTTPError, ValueError):
            raise DomainError("GOOGLE_CONNECTION_FAILED", 502) from None

    def callback(self, state, code):
        if not self.configured() or len(state) > 200 or len(code) > 3000:
            raise DomainError("OAUTH_EXPIRED", 403)
        with self.store.connection(write=True) as conn:
            row = conn.execute(
                "SELECT * FROM google_oauth WHERE state_hash=? AND expires_at>?",
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
            conn.execute("DELETE FROM google_oauth WHERE state_hash=?", (digest(state),))
        data = self._request(
            "POST",
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "redirect_uri": self.config["redirect_uri"],
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": self.vault.decrypt(row["verifier"]),
            },
        )
        tokens = self._tokens(data)
        if not tokens.get("refresh_token"):
            raise DomainError("GOOGLE_RECONNECT_REQUIRED", 409)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO google_connection VALUES(1,?,?,NULL) ON CONFLICT(id) DO UPDATE SET encrypted_tokens=excluded.encrypted_tokens,connected_at=excluded.connected_at,last_read=NULL",
                (self.vault.encrypt(encode(tokens)), iso(self.store.clock())),
            )
            self.store.record(conn, "google_connected", details={"mode": "read_only_preview"})
            self.store.bump(conn)

    def _tokens(self, data, refresh=None):
        try:
            if (
                not isinstance(data["access_token"], str)
                or not 1 <= len(data["access_token"]) <= 10000
            ):
                raise ValueError()
            expires = int(data["expires_in"])
            if not 1 <= expires <= 86400:
                raise ValueError()
            if (
                data.get("scope")
                and SCOPE not in data["scope"].split()
                and "https://www.googleapis.com/auth/calendar.readonly" not in data["scope"].split()
            ):
                raise ValueError()
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token") or refresh,
                "expires_at": iso(self.store.clock() + timedelta(seconds=expires)),
            }
        except (ValueError, TypeError, KeyError):
            raise DomainError("GOOGLE_SCOPE_REQUIRED", 409) from None

    def access_token(self):
        with self.lock:
            with self.store.connection() as conn:
                row = conn.execute(
                    "SELECT encrypted_tokens FROM google_connection WHERE id=1"
                ).fetchone()
            if not row:
                raise DomainError("GOOGLE_NOT_CONNECTED", 409)
            tokens = json.loads(self.vault.decrypt(row[0]))
            if tokens["expires_at"] <= iso(self.store.clock() + timedelta(seconds=60)):
                response = self._request(
                    "POST",
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.config["client_id"],
                        "client_secret": self.config["client_secret"],
                        "grant_type": "refresh_token",
                        "refresh_token": tokens["refresh_token"],
                    },
                )
                tokens = self._tokens(response, tokens["refresh_token"])
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE google_connection SET encrypted_tokens=? WHERE id=1",
                        (self.vault.encrypt(encode(tokens)),),
                    )
            return tokens["access_token"]

    def preview(self, payload, key):
        with self.store.connection() as conn:
            zone = self.store.settings(conn)["timezone"]
        begin = datetime.combine(payload.start, datetime.min.time()).replace(tzinfo=ZoneInfo(zone))
        end = datetime.combine(payload.end, datetime.min.time()).replace(tzinfo=ZoneInfo(zone))
        rows, warnings, page = [], [], None
        token = self.access_token()
        for _ in range(10):
            params = {
                "singleEvents": "true",
                "showDeleted": "false",
                "timeMin": begin.isoformat(),
                "timeMax": end.isoformat(),
                "maxResults": 250,
                "orderBy": "startTime",
                "fields": "nextPageToken,items(id,summary,start,end,status,transparency,location,description)",
            }
            if page:
                params["pageToken"] = page
            result = self._request(
                "GET",
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params=params,
                headers={"Authorization": "Bearer " + token},
            )
            for event in result.get("items", []):
                if event.get("status") == "cancelled":
                    continue
                try:
                    all_day = "date" in event["start"]
                    if all_day:
                        start = event["start"]["date"] + "T00:00"
                        finish = event["end"]["date"] + "T00:00"
                    else:
                        start = datetime.fromisoformat(
                            event["start"]["dateTime"].replace("Z", "+00:00")
                        )
                        finish = datetime.fromisoformat(
                            event["end"]["dateTime"].replace("Z", "+00:00")
                        )
                        if not start.tzinfo or not finish.tzinfo:
                            raise ValueError()
                        start = start.astimezone(UTC).replace(tzinfo=None, second=0, microsecond=0)
                        finish = finish.astimezone(UTC).replace(
                            tzinfo=None, second=0, microsecond=0
                        )
                    model = EventInput(
                        title=event.get("summary") or "Untitled event",
                        start_local=start,
                        end_local=finish,
                        timezone=zone if all_day else "UTC",
                        all_day=all_day,
                        location=event.get("location", ""),
                        notes=event.get("description", ""),
                        busy=event.get("transparency") != "transparent",
                        reminder_minutes=[],
                    )
                    rows.append(
                        {
                            "event": model.model_dump(mode="json"),
                            "external_id": "google/" + digest("primary/" + event["id"]),
                            "exceptions": {},
                        }
                    )
                except (ValueError, TypeError, KeyError):
                    warnings.append("An event with unsupported fields was skipped.")
                if len(rows) > 500:
                    raise DomainError("IMPORT_TOO_LARGE", 422)
            page = result.get("nextPageToken")
            if not page:
                break
        if page:
            raise DomainError("IMPORT_TOO_LARGE", 422)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE google_connection SET last_read=? WHERE id=1", (iso(self.store.clock()),)
            )
        return self.runtime.exchange._preview(
            "google",
            rows,
            warnings,
            key,
            {
                "start": str(payload.start),
                "end": str(payload.end),
                "source_name": "Google primary calendar",
                "recurrence_mode": "individual_occurrences_in_selected_range",
                "direction": "Google to local; no remote writes or automatic deletions",
            },
        )

    def disconnect(self):
        with self.lock:
            with self.store.connection(write=True) as conn:
                row = conn.execute(
                    "SELECT encrypted_tokens FROM google_connection WHERE id=1"
                ).fetchone()
                conn.execute("DELETE FROM google_connection")
                conn.execute("DELETE FROM google_oauth")
                self.store.record(conn, "google_disconnected")
                self.store.bump(conn)
            revoked = True
            if row:
                tokens = json.loads(self.vault.decrypt(row[0]))
                try:
                    self._request(
                        "POST",
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": tokens.get("refresh_token") or tokens["access_token"]},
                    )
                except DomainError:
                    revoked = False
            return {"disconnected": True, "provider_revocation_confirmed": revoked}


def google_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/google")

    @router.get("/status", dependencies=[Depends(owner)])
    def status():
        return runtime.google.snapshot()

    @router.post("/connect", dependencies=[Depends(owner)])
    def connect(request: Request):
        return runtime.google.begin(request.cookies.get("desk_companion_session"))

    @router.get("/callback")
    def callback(state: str = "", code: str = "", error: str = ""):
        if error:
            return RedirectResponse(
                "/?page=device&calendar=declined",
                status_code=303,
                headers={"Referrer-Policy": "no-referrer"},
            )
        runtime.google.callback(state, code)
        return RedirectResponse(
            "/?page=device&calendar=connected",
            status_code=303,
            headers={"Referrer-Policy": "no-referrer"},
        )

    @router.post("/preview", dependencies=[Depends(owner)])
    def preview(payload: ShareInput, key=Depends(operation_id)):
        return runtime.google.preview(payload, key)

    @router.post("/disconnect", dependencies=[Depends(owner)])
    def disconnect():
        return runtime.google.disconnect()

    return router
