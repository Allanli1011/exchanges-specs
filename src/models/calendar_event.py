from __future__ import annotations

from datetime import date, time
from enum import Enum
from hashlib import sha1

from pydantic import BaseModel, Field, HttpUrl, model_validator


class CalendarEventType(str, Enum):
    FULL_CLOSE = "full_close"
    EARLY_CLOSE = "early_close"
    LATE_OPEN = "late_open"
    MODIFIED_HOURS = "modified_hours"


class CalendarEvent(BaseModel):
    """Canonical exchange calendar event.

    The model is intentionally product-aware because many holiday schedules
    close or modify only part of an exchange.
    """

    exchange: str
    venue: str | None = None
    product_scope: list[str] = Field(default_factory=lambda: ["ALL"])
    event_date: date
    trading_date: date | None = None
    event_type: CalendarEventType
    timezone: str
    open_time: time | None = None
    close_time: time | None = None
    source_url: HttpUrl
    last_verified: date
    notes: str | None = None

    @model_validator(mode="after")
    def validate_event_hours(self) -> "CalendarEvent":
        if self.event_type is CalendarEventType.EARLY_CLOSE and self.close_time is None:
            raise ValueError("early_close requires close_time")
        if self.event_type is CalendarEventType.LATE_OPEN and self.open_time is None:
            raise ValueError("late_open requires open_time")
        if (
            self.event_type is CalendarEventType.MODIFIED_HOURS
            and self.open_time is None
            and self.close_time is None
        ):
            raise ValueError("modified_hours requires open_time or close_time")
        if self.event_type is CalendarEventType.FULL_CLOSE:
            self.open_time = None
            self.close_time = None
        if not self.exchange.strip():
            raise ValueError("exchange must not be blank")
        if not self.timezone.strip():
            raise ValueError("timezone must not be blank")
        if not self.product_scope:
            self.product_scope = ["ALL"]
        return self

    @property
    def event_key(self) -> str:
        """Stable id for de-duplication and Notion upsert logic."""

        payload = "|".join(
            [
                self.exchange,
                self.venue or "",
                self.event_date.isoformat(),
                self.event_type.value,
                ",".join(sorted(self.product_scope)),
            ]
        )
        return sha1(payload.encode("utf-8")).hexdigest()[:16]
