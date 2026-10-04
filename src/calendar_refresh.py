from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.calendar_sources.cme_baseline import load_cme_holiday_baseline
from src.calendar_sources.cme_reference_data import CMEReferenceDataClient
from src.calendar_sources.cme_schedule_normalizer import normalize_trading_schedules
from src.exporters.notion_calendar import NotionCalendarClient


DEFAULT_NOTION_DATA_SOURCE_ID = "d9e7b145-64c9-462d-b56a-61dbc7502277"
DEFAULT_CME_BASELINE = "config/cme_globex_holidays.yaml"


def build_cme_refresh_payload(
    years: list[int],
    *,
    baseline_path: Path,
) -> dict:
    windows, baseline_meta = load_cme_holiday_baseline(baseline_path, years)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage_source_mode": "verified_static_baseline",
        "baseline": baseline_meta,
        "windows": [window.as_dict() for window in windows],
        "_objects": windows,
    }

    api_id = os.getenv("CME_API_ID", "").strip()
    api_password = os.getenv("CME_API_PASSWORD", "").strip()
    if api_id and api_password:
        try:
            schedules = CMEReferenceDataClient(
                api_id=api_id,
                api_password=api_password,
            ).fetch_trading_schedules()
            normalized_events = normalize_trading_schedules(schedules)
            payload["cme_reference_data"] = {
                "status": "success",
                "endpoint": (
                    "https://refdata.api.cmegroup.com/"
                    "refdata/v3/tradingSchedules"
                ),
                "record_count": len(schedules),
                "normalized_event_count": len(normalized_events),
                "records": schedules,
                "normalized_events": [
                    event.as_dict() for event in normalized_events
                ],
            }
        except Exception as exc:
            payload["cme_reference_data"] = {
                "status": "error",
                "error": str(exc),
            }
    else:
        payload["cme_reference_data"] = {
            "status": "skipped",
            "reason": (
                "CME_API_ID / CME_API_PASSWORD are not set. "
                "The coverage guard uses the last verified official baseline; "
                "configure CME OAuth credentials for live Trading Schedules."
            ),
        }

    return payload


def run_refresh(
    *,
    years: list[int],
    output_path: Path,
    notion_data_source_id: str,
    baseline_path: Path,
    reference_output_path: Path | None = None,
) -> dict:
    payload = build_cme_refresh_payload(years, baseline_path=baseline_path)
    windows = payload.pop("_objects")

    reference = payload.get("cme_reference_data", {})
    if reference_output_path is not None and reference.get("status") == "success":
        reference_output_path.parent.mkdir(parents=True, exist_ok=True)
        reference_output_path.write_text(
            json.dumps(reference, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Keep the main audit report compact.
        payload["cme_reference_data"] = {
            key: value
            for key, value in reference.items()
            if key not in {"records", "normalized_events"}
        }
        payload["cme_reference_data"]["artifact"] = str(reference_output_path)

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
        default=[now.year],
    )
    parser.add_argument(
        "--output",
        default="artifacts/exchange_calendar_refresh.json",
    )
    parser.add_argument(
        "--cme-reference-output",
        default="artifacts/cme_trading_schedules.json",
    )
    parser.add_argument(
        "--cme-baseline",
        default=DEFAULT_CME_BASELINE,
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
        baseline_path=Path(args.cme_baseline),
        reference_output_path=(
            Path(args.cme_reference_output)
            if args.cme_reference_output
            else None
        ),
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
