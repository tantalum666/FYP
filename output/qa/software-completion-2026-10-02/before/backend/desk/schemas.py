from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Recurrence(StrictModel):
    frequency: Literal["none", "daily", "weekly", "monthly", "yearly"] = "none"
    interval: int = Field(default=1, ge=1, le=52)
    until: date | None = None


class EventInput(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    start_local: datetime
    end_local: datetime
    timezone: str = "Asia/Hong_Kong"
    all_day: bool = False
    calendar: Literal["personal", "study"] = "personal"
    color: Literal["lavender", "blue", "sage", "peach"] = "lavender"
    visibility: Literal["private", "displayable"] = "private"
    busy: bool = True
    location: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=2000)
    recurrence: Recurrence = Field(default_factory=Recurrence)
    reminder_minutes: list[int] = Field(default_factory=lambda: [10], max_length=4)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Title is required")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone") from None
        return value

    @field_validator("start_local", "end_local")
    @classmethod
    def local_datetime(cls, value):
        if value.tzinfo or value.second or value.microsecond:
            raise ValueError("Use local time at minute precision, without an offset")
        if not 2000 <= value.year <= 2100:
            raise ValueError("Supported dates are 2000 through 2100")
        return value

    @field_validator("reminder_minutes")
    @classmethod
    def reminders(cls, value):
        if any(isinstance(v, bool) or v < 0 or v > 10080 for v in value):
            raise ValueError("Reminders must be 0 through 10080 minutes early")
        return sorted(set(value), reverse=True)

    @model_validator(mode="after")
    def validate_times(self):
        from .calendar import wall_to_utc

        if self.end_local <= self.start_local:
            raise ValueError("End must be after start")
        if self.end_local - self.start_local > timedelta(days=31):
            raise ValueError("An event may span at most 31 days")
        if self.all_day and (
            self.start_local.time().isoformat() != "00:00:00"
            or self.end_local.time().isoformat() != "00:00:00"
        ):
            raise ValueError("All-day events use midnight date boundaries")
        wall_to_utc(self.start_local, self.timezone, reject_ambiguous=True)
        wall_to_utc(self.end_local, self.timezone, reject_ambiguous=True)
        if self.recurrence.until and self.recurrence.until < self.start_local.date():
            raise ValueError("Repeat end cannot precede the first event")
        return self


class CreateEvents(StrictModel):
    event: EventInput
    additional_dates: list[date] = Field(default_factory=list, max_length=59)

    @model_validator(mode="after")
    def dates_and_repeats(self):
        if self.additional_dates and self.event.recurrence.frequency != "none":
            raise ValueError("Choose batch dates or a recurrence rule, not both")
        if len(set(self.additional_dates)) != len(self.additional_dates):
            raise ValueError("Duplicate dates are not allowed")
        if self.event.start_local.date() in self.additional_dates:
            raise ValueError("The main date is already included")
        return self


class EventAction(StrictModel):
    action: Literal["update", "delete", "complete", "reopen"]
    expected_version: int = Field(ge=1)
    scope: Literal["series", "occurrence"] = "occurrence"
    occurrence_key: str | None = Field(default=None, max_length=30)
    event: EventInput | None = None


class ReminderAction(StrictModel):
    action: Literal["acknowledge", "snooze"]
    expected_version: int = Field(ge=1)
    minutes: int = Field(default=10, ge=1, le=1440)


class Login(StrictModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


class SettingsInput(StrictModel):
    expected_version: int = Field(ge=1)
    timezone: str
    hide_private: bool

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        return EventInput.valid_zone(value)
