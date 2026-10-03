from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Iterable

from src.models.calendar_event import CalendarEvent, CalendarEventType


_EVENT_ALIASES = {
    "closed": CalendarEventType.FULL_CLOSE,
    "close": CalendarEventType.FULL_CLOSE,
    "holiday": CalendarEventType.FULL_CLOSE,
    "full_close": CalendarEventType.FULL_CLOSE,
    "full close": CalendarEventType.FULL_CLOSE,
    "early_close": CalendarEventType.EARLY_CLOSE,
    "early close": CalendarEventType.EARLY_CLOSE,
    "late_open": CalendarEventType.LATE_OPEN,
    "late open": CalendarEventType.LATE_OPEN,
    "modified_hours": CalendarEventType.MODIFIED_HOURS,
    "modified hours": CalendarEventType.MODIFIED_HOURS,
    "partial": CalendarEventType.MODIFIED_HOURS,
}


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported date format: {value!r}")


def parse_clock(value: str | time | None) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"unsupported clock format: {value!r}")


def parse_event_type(value: str | CalendarEventType) -> CalendarEventType:
    if isinstance(value, CalendarEventType):
        return value
    key = str(value).strip().lower()
    if key not in _EVENT_ALIASES:
        raise ValueError(f"unsupported event type: {value!r}")
    return _EVENT_ALIASES[key]


def parse_product_scope(value: Any) -> list[str]:
    if value is None:
        return ["ALL"]
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or ["ALL"]

    text = str(value).strip()
    if not text or text.upper() in {"ALL", "EXCHANGE-WIDE", "EXCHANGE WIDE"}:
        return ["ALL"]

    delimiter = ";" if ";" in text else ","
    items = [part.strip() for part in text.split(delimiter) if part.strip()]
    return items or ["ALL"]


def normalize_calendar_record(
    record: dict[str, Any],
    *,
    exchange: str,
    timezone: str,
    source_url: str,
    last_verified: str | date,
    venue: str | None = None,
) -> CalendarEvent:
    """Normalize a structured source row into the canonical calendar model.

    Expected row keys:
      date/event_date, event_type/status, products/product_scope,
      open/open_time, close/close_time, trading_date, notes.

    Source-specific collectors can remain responsible for turning PDFs/HTML
    into rows; this function handles the shared normalization boundary.
    """

    raw_date = record.get("event_date", record.get("date"))
    if raw_date is None:
        raise ValueError("record requires event_date or date")

    raw_type = record.get("event_type", record.get("status"))
    if raw_type is None:
        raise ValueError("record requires event_type or status")

    return CalendarEvent(
        exchange=exchange,
        venue=venue,
        product_scope=parse_product_scope(
            record.get("product_scope", record.get("products"))
        ),
        event_date=parse_date(raw_date),
        trading_date=(
            parse_date(record["trading_date"]) if record.get("trading_date") else None
        ),
        event_type=parse_event_type(raw_type),
        timezone=timezone,
        open_time=parse_clock(record.get("open_time", record.get("open"))),
        close_time=parse_clock(record.get("close_time", record.get("close"))),
        source_url=source_url,
        last_verified=parse_date(last_verified),
        notes=(str(record["notes"]).strip() if record.get("notes") else None),
    )


def normalize_calendar_records(
    records: Iterable[dict[str, Any]],
    **defaults: Any,
) -> list[CalendarEvent]:
    events = [normalize_calendar_record(record, **defaults) for record in records]

    seen: set[str] = set()
    deduped: list[CalendarEvent] = []
    for event in events:
        if event.event_key in seen:
            continue
        seen.add(event.event_key)
        deduped.append(event)

    return sorted(
        deduped,
        key=lambda event: (
            event.event_date,
            event.exchange,
            event.venue or "",
            event.event_type.value,
            event.event_key,
        ),
    )
