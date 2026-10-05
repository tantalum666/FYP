"""Opt-in public data and local workspace preferences."""

import csv
import io
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field, field_validator

from .calendar import iso
from .schemas import StrictModel
from .store import DomainError, encode


class WorkspacePreferences(StrictModel):
    weather_location: Literal["none", "hong_kong"] = "none"
    holiday_region: Literal["none", "hong_kong"] = "none"
    show_lunar: bool = False
    reminder_strength: Literal["silent", "chime"] = "silent"
    quiet_enabled: bool = True
    quiet_start: str = "22:00"
    quiet_end: str = "07:00"
    daily_brief_time: str = "08:00"
    daily_brief_enabled: bool = False
    avatar_display: Literal["calendar", "companion"] = "calendar"
    voice_enabled: bool = False

    @field_validator("quiet_start", "quiet_end", "daily_brief_time")
    @classmethod
    def time_of_day(cls, value):
        import re

        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Use HH:mm")
        return value


class PreferencesUpdate(StrictModel):
    expected_version: int = Field(ge=1)
    preferences: WorkspacePreferences


def is_quiet(prefs, at):
    if not prefs["quiet_enabled"]:
        return False
    start, end, current = prefs["quiet_start"], prefs["quiet_end"], at.strftime("%H:%M")
    if start == end:
        return True
    return start <= current < end if start < end else current >= start or current < end


class WorkspaceData:
    def __init__(self, store, transport=None):
        self.store, self.transport = store, transport
        self.lock = threading.Lock()
        self.weather = None
        self.next_fetch = 0.0
        self.weather_error = None
        with store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS workspace_preferences(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL,version INTEGER NOT NULL)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO workspace_preferences VALUES(1,?,1)",
                (encode(WorkspacePreferences().model_dump()),),
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS display_announcements(id TEXT PRIMARY KEY,kind TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,claimed_by TEXT)"
            )
        self.holidays = {}
        for language, code in [("en", "en"), ("zh", "sc")]:
            document = json.loads(
                (Path(__file__).parent / "data" / f"hk-holidays-{code}.json").read_text(
                    encoding="utf-8-sig"
                )
            )
            self.holidays[language] = {
                row["dtstart"][0][:4]
                + "-"
                + row["dtstart"][0][4:6]
                + "-"
                + row["dtstart"][0][6:8]: row["summary"]
                for row in document["vcalendar"][0]["vevent"]
            }

    def preferences(self):
        with self.store.connection() as conn:
            row = conn.execute("SELECT * FROM workspace_preferences WHERE id=1").fetchone()
            return {"version": row["version"], **json.loads(row["data"])}

    def update(self, payload, key):
        def apply(conn):
            row = conn.execute("SELECT version FROM workspace_preferences WHERE id=1").fetchone()
            if row[0] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            conn.execute(
                "UPDATE workspace_preferences SET data=?,version=version+1 WHERE id=1",
                (encode(payload.preferences.model_dump()),),
            )
            self.store.record(conn, "workspace_preferences_updated")
            return {"version": row[0] + 1, **payload.preferences.model_dump()}

        return self.store.operation(
            key, {"type": "workspace_preferences", **payload.model_dump()}, apply
        )

    def poll_weather(self):
        # Called outside the reminder tick. Fixed HTTPS endpoint; no user-provided URL.
        if self.preferences()["weather_location"] != "hong_kong":
            return
        now = self.store.clock().timestamp()
        if now < self.next_fetch or not self.lock.acquire(blocking=False):
            return
        try:
            self.next_fetch = now + 600
            with httpx.Client(
                timeout=8, transport=self.transport, follow_redirects=False
            ) as client:
                response = client.get(
                    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php",
                    params={"dataType": "rhrread", "lang": "en"},
                )
                response.raise_for_status()
                if len(response.content) > 1_000_000:
                    raise ValueError("Oversized weather data")
                data = response.json()
            temperature = next(
                r["value"]
                for r in data["temperature"]["data"]
                if r["place"] == "Hong Kong Observatory"
            )
            observed = datetime.fromisoformat(data["temperature"]["recordTime"])
            if (
                observed.tzinfo is None
                or abs(now - observed.timestamp()) > 86400
                or not -30 <= temperature <= 60
            ):
                raise ValueError("Invalid weather reading")
            self.weather = {
                "temperature_c": temperature,
                "observed_at": iso(observed),
                "fetched_at": iso(self.store.clock()),
                "source": "Hong Kong Observatory",
                "source_url": "https://www.hko.gov.hk/en/index.html",
                "location": "hong_kong",
                "icon_code": data.get("icon", [None])[0],
            }
            self.weather_error = None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, StopIteration, IndexError):
            self.weather_error = "weather_unavailable"
            self.next_fetch = now + 60
        finally:
            self.lock.release()

    def snapshot(self):
        prefs = self.preferences()
        weather = {"status": "not_configured"}
        if prefs["weather_location"] == "hong_kong":
            weather = {"status": "unavailable" if self.weather_error else "loading"}
            if self.weather:
                stale = (
                    self.store.clock().timestamp()
                    - datetime.fromisoformat(
                        self.weather["observed_at"].replace("Z", "+00:00")
                    ).timestamp()
                    > 3600
                )
                weather = {
                    **self.weather,
                    "status": "stale" if stale or self.weather_error else "current",
                }
        with self.store.connection() as conn:
            zone = self.store.settings(conn)["timezone"]
        return {
            "preferences": prefs,
            "weather": weather,
            "holidays": self.holidays
            if prefs["holiday_region"] == "hong_kong"
            else {"en": {}, "zh": {}},
            "holiday_coverage": [2025, 2026, 2027],
            "quiet_now": is_quiet(prefs, self.store.clock().astimezone(ZoneInfo(zone))),
        }

    def record_rows(self, kind="all", source="all", start=None, end=None):
        rows = self.store.records(limit=10000)
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        allowed = {"all", "calendar", "posture", "devices", "assistant", "tasks"}
        if kind not in allowed or source not in {"all", "live", "replay"}:
            raise DomainError("INVALID_FILTER", 422)

        def keep(row):
            action = row["action"]
            day = (
                datetime.fromisoformat(row["at"].replace("Z", "+00:00"))
                .astimezone(zone)
                .date()
                .isoformat()
            )
            category = (
                "tasks"
                if action.startswith("task_")
                else "posture"
                if action.startswith(("posture_", "calibration_", "movement_"))
                else "assistant"
                if action.startswith("assistant_")
                else "devices"
                if action.startswith(("device_", "output_"))
                else "calendar"
            )
            return (
                (kind == "all" or category == kind)
                and (source == "all" or row["details"].get("source") == source)
                and (start is None or day >= start)
                and (end is None or day <= end)
            )

        return [r for r in rows if keep(r)]

    def claim_announcement(self, client_id, posture=None, tasks=None):
        if not 8 <= len(client_id) <= 100:
            raise DomainError("INVALID_CLIENT", 422)
        prefs = self.preferences()
        with self.store.connection(write=True) as conn:
            zone = self.store.settings(conn)["timezone"]
            now = self.store.clock().astimezone(ZoneInfo(zone))
            if is_quiet(prefs, now):
                return {"announcement": None, "quiet": True}
            candidates = []
            feedback = posture.get("feedback") if posture else None
            if (
                feedback
                and feedback["source"] == "live"
                and posture["connected"]
                and not posture["paused"]
                and posture["preferences"]["enabled"]
                and feedback["outcome"] == "waiting"
                and self.store.clock().timestamp() >= posture["snooze_until"]
                and prefs["reminder_strength"] == "chime"
            ):
                candidates.append(
                    (
                        "posture/" + str(feedback["created_at"]),
                        {"kind": "posture", "position": feedback["kind"]},
                    )
                )
            if prefs["reminder_strength"] == "chime":
                for row in self.store.reminder_list(conn, {"hide_private": True}):
                    trigger = row["snooze_until"] or row["due_at"]
                    if row["status"] == "due" and trigger >= iso(
                        self.store.clock() - timedelta(minutes=15)
                    ):
                        candidates.append(
                            (
                                "reminder/" + row["id"] + "/" + str(row["version"]),
                                {
                                    "kind": "reminder",
                                    "title": row["title"],
                                    "redacted": row["redacted"],
                                },
                            )
                        )
            if prefs["reminder_strength"] == "chime":
                for task in tasks or []:
                    alert = task.get("followup")
                    if alert and alert["created_at"] >= iso(
                        self.store.clock() - timedelta(minutes=15)
                    ):
                        candidates.append(
                            ("task/" + alert["id"], {"kind": "task", "title": "", "redacted": True})
                        )
            brief_at = now.replace(
                hour=int(prefs["daily_brief_time"][:2]),
                minute=int(prefs["daily_brief_time"][3:]),
                second=0,
                microsecond=0,
            )
            if prefs["daily_brief_enabled"] and 0 <= (now - brief_at).total_seconds() < 120:
                from .calendar import expand_all, redact

                events, exceptions = self.store.data(conn)
                begin = now.replace(hour=0, minute=0, second=0, microsecond=0)
                items = expand_all(events, exceptions, begin, begin + timedelta(days=1), zone)
                candidates.append(
                    (
                        "brief/" + str(now.date()),
                        {
                            "kind": "brief",
                            "events": [
                                {
                                    "title": redact(o, True)["title"],
                                    "start": o["start"],
                                    "all_day": o["all_day"],
                                }
                                for o in items[:20]
                            ],
                            "total": len(items),
                        },
                    )
                )
            for announcement_id, content in candidates:
                if conn.execute(
                    "SELECT 1 FROM display_announcements WHERE id=?", (announcement_id,)
                ).fetchone():
                    continue
                conn.execute(
                    "INSERT INTO display_announcements VALUES(?,?,?,?,?)",
                    (
                        announcement_id,
                        content["kind"],
                        iso(self.store.clock()),
                        iso(self.store.clock() + timedelta(minutes=2)),
                        client_id,
                    ),
                )
                self.store.record(
                    conn,
                    "announcement_claimed",
                    details={"kind": content["kind"], "client_id": client_id},
                )
                self.store.bump(conn)
                return {
                    "announcement": {"id": announcement_id, "timezone": zone, **content},
                    "quiet": False,
                }
            return {"announcement": None, "quiet": False}

    def records_csv(self, **filters):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Time (UTC)", "Action", "Title", "Source", "Outcome"])
        for row in self.record_rows(**filters):
            values = [
                row["at"],
                row["action"],
                row["title"] or "",
                row["details"].get("source", ""),
                row["details"].get("outcome", ""),
            ]
            writer.writerow(
                [
                    "'" + v if str(v).lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else v
                    for v in values
                ]
            )
        return "\ufeff" + output.getvalue()
