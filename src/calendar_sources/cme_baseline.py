from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from src.calendar_sources.cme_globex import CMEHolidayWindow


def load_cme_holiday_baseline(
    path: Path,
    years: list[int],
) -> tuple[list[CMEHolidayWindow], dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source_url = str(payload.get("source_url", "")).strip()
    verified_on = str(payload.get("verified_on", "")).strip()
    by_year = payload.get("years", {})

    windows: list[CMEHolidayWindow] = []
    missing_years: list[int] = []
    for year in years:
        rows = by_year.get(str(year))
        if not rows:
            missing_years.append(year)
            continue

        for row in rows:
            windows.append(
                CMEHolidayWindow(
                    name=str(row["name"]),
                    start_date=date.fromisoformat(str(row["start_date"])),
                    end_date=date.fromisoformat(str(row["end_date"])),
                    source_url=source_url,
                )
            )

    deduped = {window.event_key: window for window in windows}
    ordered = sorted(
        deduped.values(),
        key=lambda window: (window.start_date, window.end_date, window.name),
    )
    metadata = {
        "source_url": source_url,
        "verified_on": verified_on,
        "requested_years": years,
        "missing_years": missing_years,
    }
    return ordered, metadata
