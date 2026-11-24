"""Owner-reviewed reads of the connected primary Google Calendar."""

import re
from datetime import UTC, datetime, time
from functools import partial
from time import monotonic
from zoneinfo import ZoneInfo

import anyio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import Field

from . import google_imports
from .access import digest
from .app_oauth import ProviderResponseError
from .calendar import iso
from .exchange import ShareInput
from .google_oauth import SCOPES, GoogleOAuth
from .schemas import EventInput
from .store import DomainError, encode

SCOPE = SCOPES["calendar"][0]
EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
FIELDS = "id,summary,start,end,status,transparency,location,description"
MAX_REFRESH_COPIES = 50
READ_BUDGET_SECONDS = 60


def remaining_read_time(deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise DomainError("GOOGLE_READ_TIMEOUT", 504)
    return remaining


class GoogleRange(ShareInput):
    expected_version: str | None = Field(default=None, min_length=1, max_length=100)


class RefreshRange(GoogleRange):
    expected_version: str = Field(min_length=1, max_length=100)


def identifier(event):
    value = event.get("id") if isinstance(event, dict) else None
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,1024}", value):
        raise ValueError("Invalid Google event ID")
    return value


def external_id(remote_id):
    return "google/" + digest("primary/" + remote_id)


def review_fence(session, account, settings):
    return {
        "session": digest(session),
        "account_version": account["version"],
        "settings_version": settings["version"],
    }


def import_event(event, zone):
    if event.get("recurrence") or event.get("status", "confirmed") not in (
        "confirmed",
        "tentative",
    ):
        raise ValueError("Expected an active individual occurrence")
    if event.get("transparency", "opaque") not in ("opaque", "transparent"):
        raise ValueError("Unknown availability")
    all_day = "date" in event["start"]
    summary = event.get("summary", "")
    if not isinstance(summary, str):
        raise ValueError("Invalid event title")

    def local(bound):
        if set(event[bound]) & {"date", "dateTime"} != {"date" if all_day else "dateTime"}:
            raise ValueError("Expected matching all-day or timed bounds")
        if all_day:
            return event[bound]["date"] + "T00:00"
        value = datetime.fromisoformat(event[bound]["dateTime"].replace("Z", "+00:00"))
        if not value.tzinfo:
            raise ValueError("Expected a timezone offset")
        return value.astimezone(UTC).replace(tzinfo=None, second=0, microsecond=0)

    return EventInput(
        title=summary or "Untitled event",
        start_local=local("start"),
        end_local=local("end"),
        timezone=zone if all_day else "UTC",
        all_day=all_day,
        location=event.get("location", ""),
        notes=event.get("description", ""),
        busy=event.get("transparency") != "transparent",
        reminder_minutes=[],
    ).model_dump(mode="json")


class GoogleCalendar(GoogleOAuth):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with self.store.connection(write=True) as conn:
            google_imports.initialize(conn)

    def import_status(self, session, *, include_result=True):
        with self.store.connection() as conn:
            if not self.store.session_valid(session, conn):
                raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
            account = self.account(conn)
            settings = self.store.settings(conn)
            visible = account["connected"] and not settings["hide_private"]
            fence = review_fence(session, account, settings)
            version = digest(encode(fence)) if visible else None
            if not include_result:
                # The ordinary workspace needs only the existing opaque display fence.
                return {
                    **self._snapshot(account if account["connected"] else None),
                    "review_version": version,
                }
            last = (
                google_imports.last_refresh(conn, account["version"], fence["session"])
                if visible else None
            )
            # A newer confirmation can have identical counts and even the same clock time.
            receipt = digest(encode([version, last])) if last else None
            if last:
                last.pop("confirmation_id", None)
            return {
                **account, "review_version": version, "last_refresh": last, "last_refresh_ref": receipt,
            }

    def check_fence(self, conn, session, expected=None):
        if not self.store.session_valid(session, conn):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        settings = self.store.settings(conn)
        if settings["hide_private"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        account = self.account(conn)
        if not account["connected"]:
            raise DomainError("GOOGLE_NOT_CONNECTED")
        fence = review_fence(session, account, settings)
        if expected and fence["session"] != expected["session"]:
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if expected and fence["account_version"] != expected["account_version"]:
            raise DomainError("APP_CONNECTION_CHANGED")
        if expected and settings["version"] != expected["settings_version"]:
            raise DomainError("IMPORT_EXPIRED", 410)
        return fence

    def _list(self, get, begin, end, *, ids_only=False):
        # Expanded occurrences in a filtered date window cannot seed a collection syncToken.
        params = {
            "singleEvents": "true",
            "showDeleted": "true" if ids_only else "false",
            "timeMin": begin.isoformat(),
            "timeMax": end.isoformat(),
            "maxResults": 250,
            "orderBy": "startTime",
            "fields": "nextPageToken,items(" + ("id" if ids_only else FIELDS) + ")",
        }
        try:
            return self._read_pages(get, params)
        except ProviderResponseError as exc:
            if exc.provider_status != 410:
                raise
        # Discard the partial read and restart the exact same scoped list once.
        return self._read_pages(get, params)

    @staticmethod
    def _read_pages(get, params):
        pages, rows = set(), []
        for _ in range(10):
            result = get(EVENTS, params)
            items = result.get("items", [])
            if not isinstance(items, list):
                raise DomainError("APP_RESPONSE_INVALID", 502)
            if len(rows) + len(items) > 500:
                raise DomainError("IMPORT_TOO_LARGE", 422)
            rows.extend(items)
            page = result.get("nextPageToken")
            if page is None:
                return rows
            if not isinstance(page, str) or not 1 <= len(page) <= 4096 or page in pages:
                raise DomainError("APP_RESPONSE_INVALID", 502)
            pages.add(page)
            params = {**params, "pageToken": page}
        raise DomainError("IMPORT_TOO_LARGE", 422)

    def _range_rows(self, get, begin, end, copies, identifiers, warnings):
        rows = []
        for event in self._list(get, begin, end):
            try:
                remote_id = identifier(event)
                if event.get("status") == "cancelled":
                    continue
                ext = external_id(remote_id)
                if ext in identifiers:
                    raise DomainError("APP_RESPONSE_INVALID", 502)
                item = import_event(event, begin.tzinfo.key)
                rows.append(google_imports.review_row(ext, copies.get(ext), item))
                identifiers[ext] = remote_id
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                warnings.append("An event with unsupported fields was skipped.")
        return rows

    def _refresh_rows(self, get, begin, end, copies, identifiers):
        targets = {ext: copy for ext, copy in copies.items() if copy.overlaps(begin, end)}
        if len(targets) > MAX_REFRESH_COPIES:
            raise DomainError("GOOGLE_REFRESH_TOO_LARGE", 422)
        legacy = {ext for ext, copy in targets.items() if not copy.remote_id}
        if legacy:
            for item in self._list(get, begin, end, ids_only=True):
                try:
                    remote_id = identifier(item)
                except ValueError:
                    raise DomainError("APP_RESPONSE_INVALID", 502) from None
                ext = external_id(remote_id)
                if ext in legacy:
                    identifiers[ext] = remote_id
        rows = []
        for ext, copy in targets.items():
            remote_id = copy.remote_id or identifiers.get(ext)
            if not remote_id:
                rows.append(google_imports.review_row(ext, copy, status="unresolved"))
                continue
            identifiers[ext] = remote_id
            status, document = None, None
            try:
                event = get(EVENTS + "/" + remote_id, {"fields": FIELDS + ",recurrence"})
                if event.get("id") != remote_id:
                    raise DomainError("APP_RESPONSE_INVALID", 502)
                if event.get("status") == "cancelled":
                    status = "deleted"
                else:
                    zone = copy.event["timezone"] if copy.event["all_day"] else begin.tzinfo.key
                    document = import_event(event, zone)
            except ProviderResponseError as exc:
                if exc.provider_status == 410 and exc.reasons == {"deleted"}:
                    status = "deleted"
                elif exc.provider_status == 404 and exc.reasons == {"notFound"}:
                    # Google also returns notFound when the caller no longer has access.
                    status = "unavailable"
                else:
                    raise
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                status = "unsupported"
            row = google_imports.review_row(ext, copy, document, status)
            if status == "deleted":
                row["confirmed_cancellation"] = True
            rows.append(row)
        return rows

    def preview(self, payload, key, owner_session, *, refresh=False, deadline=None):
        if deadline is None:
            deadline = monotonic() + READ_BUDGET_SECONDS
        kind = "google_refresh" if refresh else "google"
        with self.store.connection() as conn:
            fence = self.check_fence(conn, owner_session)
            expected = getattr(payload, "expected_version", None)
            if expected is not None and expected != fence["account_version"]:
                raise DomainError("APP_CONNECTION_CHANGED")
            request = {
                "type": "preview",
                "kind": kind,
                "range": payload.model_dump(mode="json"),
                "fence": fence,
            }
            _, cached = self.store.operation_receipt(conn, key, request)
            if cached is not None:
                return self.runtime.exchange.pending_preview(conn, cached)
            copies = google_imports.imported_copies(conn, fence["account_version"])
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        begin = datetime.combine(payload.start, time.min, zone)
        end = datetime.combine(payload.end, time.min, zone)
        token = None

        def get(url, params):
            nonlocal token
            remaining_read_time(deadline)
            with self.store.connection() as conn:
                self.check_fence(conn, owner_session, fence)
            if token is None:
                token = self.access_token()
                with self.store.connection() as conn:
                    self.check_fence(conn, owner_session, fence)
            try:
                return self._request(
                    "GET",
                    url,
                    headers={"Authorization": "Bearer " + token},
                    params=params,
                    timeout=min(12, remaining_read_time(deadline)),
                )
            finally:
                remaining_read_time(deadline)

        identifiers, warnings = {}, []
        rows = (
            self._refresh_rows(get, begin, end, copies, identifiers)
            if refresh
            else self._range_rows(get, begin, end, copies, identifiers, warnings)
        )
        metadata = {
            "start": str(payload.start),
            "end": str(payload.end),
            "source_name": "Google primary calendar",
            "recurrence_mode": "individual_occurrences_in_selected_range",
            "account_version": fence["account_version"],
            "review_version": digest(encode(fence)),
            "direction": "Google to local",
        }

        def save(conn):
            remaining_read_time(deadline)
            if token is not None:
                conn.execute(
                    "UPDATE google_connection SET last_read=? WHERE id=1",
                    (iso(self.store.clock()),),
                )
            preview = self.runtime.exchange.save_preview(
                conn,
                kind,
                rows,
                warnings,
                metadata,
                google={
                    "fence": fence,
                    "identifiers": identifiers,
                    "last_reviews": {
                        row["existing_id"]: copies[row["external_id"]].review_id
                        for row in rows
                        if row["existing_id"]
                    },
                },
            )
            # Only the temporary review needs the private event text.
            return {"preview_id": preview["preview_id"]}

        receipt = self.store.operation(
            key, request, save, authorize=lambda conn: self.check_fence(conn, owner_session, fence)
        )
        with self.store.connection() as conn:
            self.check_fence(conn, owner_session, fence)
            return self.runtime.exchange.pending_preview(conn, receipt)

    def discard(self, preview_id, key, session):
        request = {"type": "google_discard", "preview_id": preview_id}

        def authorize(conn):
            self.runtime.exchange.authorize_review(
                conn, key, request, session, owner=True, google_only=True
            )

        def discard(conn):
            if not conn.execute(
                "UPDATE import_previews SET state='discarded' WHERE id=? AND state='pending' AND expires_at>?",
                (preview_id, iso(self.store.clock())),
            ).rowcount:
                raise DomainError("IMPORT_EXPIRED", 410)
            return {"discarded": True}

        return self.store.operation(key, request, discard, authorize=authorize)


def google_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/google")

    async def read_preview(payload, request, key, *, refresh=False):
        deadline = monotonic() + READ_BUDGET_SECONDS
        read = partial(
            runtime.google.preview,
            payload,
            key,
            request.cookies.get("desk_companion_session"),
            refresh=refresh,
            deadline=deadline,
        )
        # httpx timeouts bound socket inactivity. A stalled or trickling final
        # response must also release the Web caller and cannot publish a review.
        with anyio.move_on_after(remaining_read_time(deadline)):
            return await anyio.to_thread.run_sync(read, abandon_on_cancel=True)
        raise DomainError("GOOGLE_READ_TIMEOUT", 504)

    @router.get("/status", dependencies=[Depends(owner)])
    def status(request: Request):
        return runtime.google.import_status(request.cookies.get("desk_companion_session"))

    @router.post("/connect", dependencies=[Depends(owner)])
    def connect(request: Request):
        return runtime.google.begin(
            request.cookies.get("desk_companion_session"), request.headers.get("origin")
        )

    @router.get("/callback")
    def callback(state: str = "", code: str = "", error: str = ""):
        if error:
            runtime.google.reject(state)
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
    async def preview(payload: GoogleRange, request: Request, key=Depends(operation_id)):
        return await read_preview(payload, request, key)

    @router.post("/refresh", dependencies=[Depends(owner)])
    async def refresh(payload: RefreshRange, request: Request, key=Depends(operation_id)):
        return await read_preview(payload, request, key, refresh=True)

    @router.post("/{preview_id}/discard", dependencies=[Depends(owner)])
    def discard(preview_id: str, request: Request, key=Depends(operation_id)):
        return runtime.google.discard(
            preview_id, key, request.cookies.get("desk_companion_session")
        )

    @router.post("/disconnect", dependencies=[Depends(owner)])
    def disconnect():
        return runtime.google.disconnect()

    return router
