from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.calendar_sources.cme_globex import fetch_cme_globex_holiday_windows
from src.exporters.notion_calendar import NotionCalendarClient
from src.utils.http_client import HttpClient


DEFAULT_NOTION_DATA_SOURCE_ID = "d9e7b145-64c9-462d-b56a-61dbc7502277"


async def build_cme_refresh_payload(years: list[int]) -> dict:
    client = HttpClient(cache=None)
    try:
        windows = []
        errors = []
        for year in years:
            try:
                windows.extend(await fetch_cme_globex_holiday_windows(client, year))
            except Exception as exc:
                errors.append({"year": year, "error": str(exc)})

        # Cross-year New Year windows can appear in both annual sections.
        deduped = {window.event_key: window for window in windows}
        ordered = sorted(
            deduped.values(),
            key=lambda window: (window.start_date, window.end_date, window.name),
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://www.cmegroup.com/trading-hours.html",
            "years": years,
            "windows": [window.as_dict() for window in ordered],
            "errors": errors,
            "_objects": ordered,
        }
    finally:
        await client.close()


def run_refresh(
    *,
    years: list[int],
    output_path: Path,
    notion_data_source_id: str,
) -> dict:
    payload = asyncio.run(build_cme_refresh_payload(years))
    windows = payload.pop("_objects")

    token = os.getenv("NOTION_TOKEN", "").strip()
    if token:
        notion = NotionCalendarClient(
            token=token,
            data_source_id=notion_data_source_id,
        )
        results = notion.ensure_cme_windows(windows)
        payload["notion_sync"] = [
            {
                "event_key": result.event_key,
                "holiday": result.holiday,
                "action": result.action,
                "page_id": result.page_id,
            }
            for result in results
        ]
    else:
        payload["notion_sync"] = {
            "status": "skipped",
            "reason": "NOTION_TOKEN is not set",
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    now = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description="Refresh exchange holiday coverage")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[now.year, now.year + 1],
    )
    parser.add_argument(
        "--output",
        default="artifacts/exchange_calendar_refresh.json",
    )
    parser.add_argument(
        "--notion-data-source-id",
        default=os.getenv(
            "NOTION_CALENDAR_DATA_SOURCE_ID",
            DEFAULT_NOTION_DATA_SOURCE_ID,
        ),
    )
    args = parser.parse_args()

    payload = run_refresh(
        years=args.years,
        output_path=Path(args.output),
        notion_data_source_id=args.notion_data_source_id,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
