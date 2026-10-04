# Exchange Calendar Normalization

The exchange-calendar layer converts source-specific holiday schedules into one
canonical event model before downstream export to Notion, CSV or other tools.

## Boundary

Collectors remain responsible for reading exchange HTML, PDF, XLSX or notices.

They should produce structured rows shaped roughly like:

```python
{
    "date": "2026-11-27",
    "event_type": "early close",
    "products": "Energy; Metals",
    "close": "12:45",
    "notes": "Post-Thanksgiving modified hours",
}
```

Then normalize:

```python
from src.parsers.calendar_normalizer import normalize_calendar_record

event = normalize_calendar_record(
    row,
    exchange="CME",
    venue="Globex",
    timezone="America/Chicago",
    source_url="https://...",
    last_verified="2026-10-03",
)
```

## Canonical fields

- exchange
- venue
- product_scope
- event_date
- trading_date
- event_type
- timezone
- open_time
- close_time
- source_url
- last_verified
- notes

The model generates a stable `event_key` for de-duplication/upsert logic.

## Event types

- `full_close`
- `early_close`
- `late_open`
- `modified_hours`

Product scope is mandatory conceptually. `["ALL"]` means exchange-wide.

## JSON Schema

See `schemas/calendar_event.schema.json`.

This schema is intended to be the contract between source parsers and downstream
Notion/calendar exporters.
