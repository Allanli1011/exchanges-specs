from datetime import date, time

import pytest

from src.models.calendar_event import CalendarEventType
from src.parsers.calendar_normalizer import (
    normalize_calendar_record,
    normalize_calendar_records,
    parse_product_scope,
)


def defaults():
    return {
        "exchange": "CME",
        "venue": "Globex",
        "timezone": "America/Chicago",
        "source_url": "https://example.com/holiday-hours",
        "last_verified": "2026-10-03",
    }


def test_normalize_early_close_event():
    event = normalize_calendar_record(
        {
            "date": "2026-11-27",
            "status": "early close",
            "products": "Energy; Metals",
            "close": "12:45",
            "notes": "Post-Thanksgiving modified hours",
        },
        **defaults(),
    )

    assert event.event_date == date(2026, 11, 27)
    assert event.event_type is CalendarEventType.EARLY_CLOSE
    assert event.product_scope == ["Energy", "Metals"]
    assert event.close_time == time(12, 45)
    assert event.event_key


def test_full_close_clears_accidental_hours():
    event = normalize_calendar_record(
        {
            "date": "2026-12-25",
            "event_type": "holiday",
            "open": "08:00",
            "close": "12:00",
        },
        **defaults(),
    )

    assert event.event_type is CalendarEventType.FULL_CLOSE
    assert event.open_time is None
    assert event.close_time is None
    assert event.product_scope == ["ALL"]


def test_early_close_requires_close_time():
    with pytest.raises(ValueError, match="close_time"):
        normalize_calendar_record(
            {"date": "2026-12-24", "event_type": "early_close"},
            **defaults(),
        )


def test_product_scope_accepts_exchange_wide_alias():
    assert parse_product_scope("exchange-wide") == ["ALL"]
    assert parse_product_scope(["Brent", "Gasoil"]) == ["Brent", "Gasoil"]


def test_normalize_records_deduplicates_by_stable_event_key():
    rows = [
        {
            "date": "2026-12-25",
            "event_type": "closed",
            "products": "ALL",
        },
        {
            "date": "2026-12-25",
            "event_type": "holiday",
            "products": "ALL",
        },
    ]

    events = normalize_calendar_records(rows, **defaults())

    assert len(events) == 1
