from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


CME_OAUTH_TOKEN_URL = "https://auth.cmegroup.com/as/token.oauth2"
CME_TRADING_SCHEDULES_URL = (
    "https://refdata.api.cmegroup.com/refdata/v3/tradingSchedules"
)


def extract_records(payload: Any) -> list[dict[str, Any]]:
    """Extract schedule records from common JSON/HAL response shapes."""

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("content", "results", "tradingSchedules"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    embedded = payload.get("_embedded")
    if isinstance(embedded, dict):
        for value in embedded.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _total_pages(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None

    page = payload.get("page")
    if isinstance(page, dict):
        value = page.get("totalPages")
        if isinstance(value, int):
            return value

    value = payload.get("totalPages")
    if isinstance(value, int):
        return value

    return None


@dataclass
class CMEReferenceDataClient:
    api_id: str
    api_password: str
    timeout_seconds: float = 30.0
    client: httpx.Client | None = None

    def _client(self) -> httpx.Client:
        return self.client or httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
        )

    def access_token(self) -> str:
        client = self._client()
        response = client.post(
            CME_OAUTH_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.api_id, self.api_password),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()
        token = str(payload.get("access_token", "")).strip()
        if not token:
            raise ValueError("CME OAuth response did not contain access_token")
        return token

    def fetch_trading_schedules(self, *, page_size: int = 20) -> list[dict[str, Any]]:
        if not 1 <= page_size < 30:
            raise ValueError("CME tradingSchedules page size must be between 1 and 29")

        token = self.access_token()
        client = self._client()
        records: list[dict[str, Any]] = []
        page = 0

        while page < 500:
            response = client.get(
                CME_TRADING_SCHEDULES_URL,
                params={"page": page, "size": page_size},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()
            chunk = extract_records(payload)
            records.extend(chunk)

            total_pages = _total_pages(payload)
            if total_pages is not None:
                if page + 1 >= total_pages:
                    break
            elif len(chunk) < page_size:
                break

            page += 1
        else:
            raise RuntimeError("CME tradingSchedules pagination exceeded safety limit")

        return records
