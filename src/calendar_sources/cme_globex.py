from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

from bs4 import BeautifulSoup

from src.utils.http_client import HttpClient


CME_TRADING_HOURS_URL = "https://www.cmegroup.com/trading-hours.html"


@dataclass(frozen=True)
class CMEHolidayWindow:
    name: str
    start_date: date
    end_date: date
    source_url: str = CME_TRADING_HOURS_URL

    @property
    def year(self) -> int:
        return self.start_date.year

    @property
    def event_key(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"cme-globex-{self.start_date.isoformat()}-{self.end_date.isoformat()}-{slug}"

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["start_date"] = self.start_date.isoformat()
        payload["end_date"] = self.end_date.isoformat()
        payload["event_key"] = self.event_key
        return payload


def _month_number(name: str) -> int:
    return datetime.strptime(name.strip(), "%B").month


def parse_date_range(text: str) -> tuple[date, date]:
    normalized = (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\xa0", " ")
        .strip()
    )
    normalized = re.sub(r"\s+", " ", normalized)

    cross = re.fullmatch(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*-\s*"
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        normalized,
    )
    if cross:
        d1, m1, y1, d2, m2, y2 = cross.groups()
        return (
            date(int(y1), _month_number(m1), int(d1)),
            date(int(y2), _month_number(m2), int(d2)),
        )

    same_month = re.fullmatch(
        r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        normalized,
    )
    if same_month:
        d1, d2, month, year = same_month.groups()
        return (
            date(int(year), _month_number(month), int(d1)),
            date(int(year), _month_number(month), int(d2)),
        )

    single = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", normalized)
    if single:
        day, month, year = single.groups()
        value = date(int(year), _month_number(month), int(day))
        return value, value

    raise ValueError(f"Unsupported CME holiday date range: {text!r}")


def _heading_matches(text: str, year: int) -> bool:
    compact = " ".join(text.split()).lower()
    return str(year) in compact and "cme globex trading schedule" in compact


def parse_cme_globex_holiday_windows(html: str, year: int) -> list[CMEHolidayWindow]:
    """Parse the official high-level CME Globex holiday-window table."""

    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            tag
            for tag in soup.find_all(re.compile(r"^h[1-6]$"))
            if _heading_matches(tag.get_text(" ", strip=True), year)
        ),
        None,
    )
    if heading is None:
        raise ValueError(f"Could not find {year} CME Globex Trading Schedule heading")

    table = heading.find_next("table")
    if table is None:
        raise ValueError(f"Could not find holiday table after {year} CME heading")

    windows: list[CMEHolidayWindow] = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) < 2:
            continue
        if cells[0].strip().lower() in {"u.s. holiday", "holiday"}:
            continue

        name = cells[0].strip()
        date_text = cells[1].strip()
        if not name or not date_text:
            continue

        try:
            start_date, end_date = parse_date_range(date_text)
        except ValueError:
            continue

        # The section may include a cross-year New Year's window. Keep any
        # window that touches the requested calendar year.
        if start_date.year != year and end_date.year != year:
            continue

        windows.append(
            CMEHolidayWindow(
                name=name,
                start_date=start_date,
                end_date=end_date,
            )
        )

    if not windows:
        raise ValueError(f"No {year} CME Globex holiday windows parsed")

    return windows


async def fetch_cme_globex_holiday_windows(
    client: HttpClient,
    year: int,
) -> list[CMEHolidayWindow]:
    html = await client.get(CME_TRADING_HOURS_URL, use_cache=False)
    return parse_cme_globex_holiday_windows(html, year)
