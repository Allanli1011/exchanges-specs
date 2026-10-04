from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CMETradingScheduleEvent:
    trading_schedule_id: str
    applicable_globex_group_codes: tuple[str, ...]
    quadrants: tuple[str, ...]
    schedule_names: tuple[str, ...]
    trading_date: date
    market_event_type: str
    market_event_time: datetime
    no_cancel_period: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["applicable_globex_group_codes"] = list(
            self.applicable_globex_group_codes
        )
        payload["quadrants"] = list(self.quadrants)
        payload["schedule_names"] = list(self.schedule_names)
        payload["trading_date"] = self.trading_date.isoformat()
        payload["market_event_time"] = (
            self.market_event_time.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return payload


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item is not None)
    return (str(value),)


def parse_trading_date(value: Any) -> date:
    text = str(value).strip()
    for fmt in ("%m%d%y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported CME tradingDate: {value!r}")


def parse_market_event_time(value: Any) -> datetime:
    text = str(value).strip()
    formats = (
        "%m%d%Y-%H:%M:%S.%fZ",
        "%d%m%Y-%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unsupported CME marketEventTime: {value!r}")


def normalize_trading_schedules(
    records: list[dict[str, Any]],
) -> list[CMETradingScheduleEvent]:
    events: list[CMETradingScheduleEvent] = []

    for record in records:
        schedule_id = str(record.get("tradingScheduleId", ""))
        group_codes = _strings(record.get("applicableGlobexGroupCodes"))
        quadrants = _strings(record.get("quadrants"))
        schedule_names = _strings(record.get("scheduleNames"))

        by_date = record.get("marketEventsByDate") or []
        if isinstance(by_date, dict):
            by_date = [by_date]

        for date_block in by_date:
            if not isinstance(date_block, dict):
                continue
            trading_date = parse_trading_date(date_block.get("tradingDate"))
            market_events = date_block.get("marketEvents") or []
            if isinstance(market_events, dict):
                market_events = [market_events]

            for market_event in market_events:
                if not isinstance(market_event, dict):
                    continue
                event_type = str(market_event.get("marketEventType", "")).strip()
                event_time = market_event.get("marketEventTime")
                if not event_type or not event_time:
                    continue

                events.append(
                    CMETradingScheduleEvent(
                        trading_schedule_id=schedule_id,
                        applicable_globex_group_codes=group_codes,
                        quadrants=quadrants,
                        schedule_names=schedule_names,
                        trading_date=trading_date,
                        market_event_type=event_type.lower(),
                        market_event_time=parse_market_event_time(event_time),
                        no_cancel_period=(
                            str(market_event["noCancelPeriod"])
                            if market_event.get("noCancelPeriod") is not None
                            else None
                        ),
                    )
                )

    return sorted(
        events,
        key=lambda event: (
            event.trading_date,
            event.market_event_time,
            event.trading_schedule_id,
            event.market_event_type,
        ),
    )
