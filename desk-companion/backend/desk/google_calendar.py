"""Google Calendar adapter using the shared application OAuth lifecycle."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from .access import digest
from .calendar import iso
from .exchange import ShareInput
from .schemas import EventInput
from .store import DomainError
from .google_oauth import GoogleOAuth

SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"


class GoogleCalendar(GoogleOAuth):
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


def google_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/google")

    @router.get("/status", dependencies=[Depends(owner)])
    def status():
        return runtime.google.snapshot()

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
    def preview(payload: ShareInput, key=Depends(operation_id)):
        return runtime.google.preview(payload, key)

    @router.post("/disconnect", dependencies=[Depends(owner)])
    def disconnect():
        return runtime.google.disconnect()

    return router
