"""Bounded reads exposed by connected apps, with no caller-supplied URLs."""

from datetime import datetime
from typing import Literal
from pydantic import Field, model_validator
from .schemas import StrictModel


class ConnectedAppQuery(StrictModel):
    service: Literal[
        "gmail",
        "google_calendar",
        "outlook_mail",
        "outlook_calendar",
        "onedrive",
        "todo",
        "onenote",
        "teams",
        "sharepoint",
    ]
    resource_id: str | None = Field(
        default=None, min_length=1, max_length=400, pattern=r"^[A-Za-z0-9_!=.+:@,-]+$"
    )
    query: str | None = Field(default=None, min_length=1, max_length=200)
    start: datetime | None = None
    end: datetime | None = None
    limit: int = Field(default=10, ge=1, le=20, strict=True)

    @model_validator(mode="after")
    def scope(self):
        if self.resource_id in {".", ".."}:
            raise ValueError("Use an item ID returned by the connected app")
        if self.service in {"google_calendar", "outlook_calendar"}:
            if self.resource_id:
                raise ValueError("This reads the owner's primary calendar")
            if (
                not self.start
                or not self.end
                or not self.start.tzinfo
                or not self.end.tzinfo
                or not 0 < (self.end - self.start).total_seconds() <= 62 * 86400
            ):
                raise ValueError("Calendar reads require an offset-aware range of at most62 days")
        elif self.start is not None or self.end is not None:
            raise ValueError("Dates apply only to calendar reads")
        if self.query is not None and self.service != "gmail":
            raise ValueError("Search text is currently supported by Gmail")
        if self.query and self.resource_id:
            raise ValueError("Choose a search or one message ID")
        return self
