from datetime import date, datetime, timezone

from src.calendar_sources.cme_schedule_normalizer import (
    normalize_trading_schedules,
    parse_market_event_time,
)


def test_normalize_cme_trading_schedule_events():
    records = [
        {
            "tradingScheduleId": 42,
            "applicableGlobexGroupCodes": ["CL", "NG"],
            "quadrants": ["NYMEX"],
            "scheduleNames": ["Energy"],
            "marketEventsByDate": [
                {
                    "tradingDate": "112726",
                    "marketEvents": [
                        {
                            "marketEventType": "open",
                            "marketEventTime": "11272026-23:00:00.000Z",
                        },
                        {
                            "marketEventType": "closed",
                            "marketEventTime": "11272026-18:45:00.000Z",
                        },
                    ],
                }
            ],
        }
    ]

    events = normalize_trading_schedules(records)

    assert len(events) == 2
    assert events[0].trading_date == date(2026, 11, 27)
    assert events[0].applicable_globex_group_codes == ("CL", "NG")
    assert events[0].quadrants == ("NYMEX",)
    assert {event.market_event_type for event in events} == {"open", "closed"}


def test_market_event_time_accepts_cme_compact_timestamp():
    value = parse_market_event_time("11272026-18:45:00.000Z")
    assert value == datetime(2026, 11, 27, 18, 45, tzinfo=timezone.utc)
