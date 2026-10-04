from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx

from src.calendar_sources.cme_globex import CMEHolidayWindow


CME_EXCHANGE_TAGS = {"CME", "CBOT", "NYMEX", "COMEX"}


def _plain_text(prop: dict[str, Any]) -> str:
    parts = prop.get("rich_text") or prop.get("title") or []
    return "".join(part.get("plain_text", "") for part in parts).strip()


def _select_names(prop: dict[str, Any]) -> set[str]:
    return {
        item.get("name", "")
        for item in prop.get("multi_select", [])
        if item.get("name")
    }


def _date_range(prop: dict[str, Any]) -> tuple[date | None, date | None]:
    value = prop.get("date")
    if not value or not value.get("start"):
        return None, None
    start = date.fromisoformat(value["start"][:10])
    end = date.fromisoformat((value.get("end") or value["start"])[:10])
    return start, end


def _overlaps(
    left_start: date,
    left_end: date,
    right_start: date,
    right_end: date,
) -> bool:
    return left_start <= right_end and right_start <= left_end


@dataclass(frozen=True)
class CalendarSyncResult:
    event_key: str
    holiday: str
    action: str
    page_id: str | None = None


class NotionCalendarClient:
    BASE_URL = "https://api.notion.com/v1"

    def __init__(
        self,
        *,
        token: str,
        data_source_id: str,
        notion_version: str = "2025-09-03",
        timeout_seconds: int = 30,
        client: httpx.Client | None = None,
    ) -> None:
        if not token.strip():
            raise ValueError("Notion token must not be blank")
        self.token = token.strip()
        self.data_source_id = data_source_id
        self.notion_version = notion_version
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.client.request(
            method,
            f"{self.BASE_URL}{path}",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def query_all(self) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"page_size": 100}
        pages: list[dict[str, Any]] = []
        while True:
            data = self._request(
                "POST",
                f"/data_sources/{self.data_source_id}/query",
                payload=payload,
            )
            pages.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            payload["start_cursor"] = data["next_cursor"]
        return pages

    def _find_by_event_key(
        self,
        pages: list[dict[str, Any]],
        event_key: str,
    ) -> dict[str, Any] | None:
        for page in pages:
            if _plain_text(page.get("properties", {}).get("Event Key", {})) == event_key:
                return page
        return None

    def _find_existing_window(
        self,
        pages: list[dict[str, Any]],
        window: CMEHolidayWindow,
    ) -> dict[str, Any] | None:
        holiday_words = {
            token
            for token in window.name.lower().replace("’", "'").split()
            if len(token) >= 4
        }

        candidates: list[dict[str, Any]] = []
        for page in pages:
            props = page.get("properties", {})
            if not (_select_names(props.get("Exchange", {})) & CME_EXCHANGE_TAGS):
                continue
            start, end = _date_range(props.get("Event Time (HKT)", {}))
            if start is None or end is None:
                continue
            if not _overlaps(start, end, window.start_date, window.end_date):
                continue

            title = _plain_text(props.get("Event", {})).lower()
            ref = _plain_text(props.get("Reference Period", {})).lower()
            haystack = f"{title} {ref}"
            if holiday_words and not any(word in haystack for word in holiday_words):
                continue

            candidates.append(page)

        if not candidates:
            return None

        # Prefer the broadest CME Group row rather than an individual contract
        # or venue detail, because Event Key represents the high-level window.
        candidates.sort(
            key=lambda page: len(
                _select_names(page.get("properties", {}).get("Exchange", {}))
                & CME_EXCHANGE_TAGS
            ),
            reverse=True,
        )
        return candidates[0]

    def _claim_existing(
        self,
        page: dict[str, Any],
        window: CMEHolidayWindow,
    ) -> CalendarSyncResult:
        page_id = str(page["id"])
        self._request(
            "PATCH",
            f"/pages/{page_id}",
            payload={
                "properties": {
                    "Event Key": {
                        "rich_text": [
                            {"type": "text", "text": {"content": window.event_key}}
                        ]
                    },
                    "Venue": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "CME Globex"}}
                        ]
                    },
                }
            },
        )
        return CalendarSyncResult(
            event_key=window.event_key,
            holiday=window.name,
            action="claimed_existing",
            page_id=page_id,
        )

    def _refresh_placeholder(
        self,
        page: dict[str, Any],
        window: CMEHolidayWindow,
        verified_on: date,
    ) -> CalendarSyncResult:
        page_id = str(page["id"])
        self._request(
            "PATCH",
            f"/pages/{page_id}",
            payload={
                "properties": {
                    "Last Verified": {"date": {"start": verified_on.isoformat()}},
                    "Source": {"url": window.source_url},
                }
            },
        )
        return CalendarSyncResult(
            event_key=window.event_key,
            holiday=window.name,
            action="refreshed_placeholder",
            page_id=page_id,
        )

    def _create_placeholder(
        self,
        window: CMEHolidayWindow,
        verified_on: date,
    ) -> CalendarSyncResult:
        date_value: dict[str, str] = {"start": window.start_date.isoformat()}
        if window.end_date != window.start_date:
            date_value["end"] = window.end_date.isoformat()

        created = self._request(
            "POST",
            "/pages",
            payload={
                "parent": {
                    "type": "data_source_id",
                    "data_source_id": self.data_source_id,
                },
                "properties": {
                    "Event": {
                        "title": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"CME Group — {window.name} holiday window"
                                },
                            }
                        ]
                    },
                    "Event Key": {
                        "rich_text": [
                            {"type": "text", "text": {"content": window.event_key}}
                        ]
                    },
                    "Event Time (HKT)": {"date": date_value},
                    "Exchange": {
                        "multi_select": [
                            {"name": name}
                            for name in ["CME", "CBOT", "NYMEX", "COMEX"]
                        ]
                    },
                    "Market Status": {"select": {"name": "Modified Hours"}},
                    "Region": {"select": {"name": "US"}},
                    "Impact": {"select": {"name": "High"}},
                    "Official Time": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        f"{window.start_date.isoformat()} to "
                                        f"{window.end_date.isoformat()}; product-specific"
                                    )
                                },
                            }
                        ]
                    },
                    "Affected Products": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "CME, CBOT, NYMEX and COMEX products; "
                                        "exact holiday hours are product-specific."
                                    )
                                },
                            }
                        ]
                    },
                    "Reference Period": {
                        "rich_text": [
                            {"type": "text", "text": {"content": window.name}}
                        ]
                    },
                    "Notes": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "Auto-created coverage placeholder from the official "
                                        "CME Globex holiday calendar. CME states exact holiday "
                                        "hours are usually finalized about two weeks before the "
                                        "holiday. Replace/enrich with product-specific hours when "
                                        "the detailed schedule is available."
                                    )
                                },
                            }
                        ]
                    },
                    "Source": {"url": window.source_url},
                    "Last Verified": {"date": {"start": verified_on.isoformat()}},
                    "Venue": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "CME Globex"}}
                        ]
                    },
                },
            },
        )
        return CalendarSyncResult(
            event_key=window.event_key,
            holiday=window.name,
            action="created_placeholder",
            page_id=str(created["id"]),
        )

    def ensure_cme_windows(
        self,
        windows: list[CMEHolidayWindow],
        *,
        verified_on: date | None = None,
    ) -> list[CalendarSyncResult]:
        checked = verified_on or datetime.now(timezone.utc).date()
        pages = self.query_all()
        results: list[CalendarSyncResult] = []

        for window in windows:
            keyed = self._find_by_event_key(pages, window.event_key)
            if keyed is not None:
                results.append(self._refresh_placeholder(keyed, window, checked))
                continue

            existing = self._find_existing_window(pages, window)
            if existing is not None:
                result = self._claim_existing(existing, window)
                results.append(result)
                # Keep local snapshot current so repeated windows in one run
                # cannot claim the same page again.
                existing.setdefault("properties", {})["Event Key"] = {
                    "rich_text": [
                        {
                            "plain_text": window.event_key,
                            "text": {"content": window.event_key},
                        }
                    ]
                }
                continue

            created = self._create_placeholder(window, checked)
            results.append(created)

        return results
