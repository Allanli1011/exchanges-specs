from pathlib import Path

from src.calendar_sources.cme_baseline import load_cme_holiday_baseline
from src.calendar_sources.cme_reference_data import (
    CMEReferenceDataClient,
    extract_records,
)


def test_load_verified_cme_baseline(tmp_path: Path):
    path = tmp_path / "baseline.yaml"
    path.write_text(
        "source_url: https://example.com\n"
        "verified_on: 2026-10-04\n"
        "years:\n"
        "  '2026':\n"
        "    - name: Thanksgiving\n"
        "      start_date: 2026-11-26\n"
        "      end_date: 2026-11-28\n",
        encoding="utf-8",
    )

    windows, metadata = load_cme_holiday_baseline(path, [2026, 2027])

    assert len(windows) == 1
    assert windows[0].name == "Thanksgiving"
    assert metadata["verified_on"] == "2026-10-04"
    assert metadata["missing_years"] == [2027]


def test_extract_reference_data_records_from_hal_response():
    payload = {
        "_embedded": {
            "tradingSchedules": [
                {"tradingScheduleId": 1},
                {"tradingScheduleId": 2},
            ]
        }
    }
    assert [row["tradingScheduleId"] for row in extract_records(payload)] == [1, 2]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, url, data, auth, headers):
        self.calls.append(("POST", url, data, auth, headers))
        return FakeResponse({"access_token": "abc123"})

    def get(self, url, params, headers):
        self.calls.append(("GET", url, params, headers))
        page = params["page"]
        if page == 0:
            return FakeResponse({
                "content": [{"tradingScheduleId": 1}],
                "page": {"totalPages": 2},
            })
        return FakeResponse({
            "content": [{"tradingScheduleId": 2}],
            "page": {"totalPages": 2},
        })


def test_reference_data_client_uses_client_credentials_and_paginates():
    fake = FakeClient()
    client = CMEReferenceDataClient(
        api_id="id",
        api_password="password",
        client=fake,
    )

    rows = client.fetch_trading_schedules(page_size=20)

    assert [row["tradingScheduleId"] for row in rows] == [1, 2]
    assert fake.calls[0][0] == "POST"
    assert fake.calls[0][3] == ("id", "password")
    assert fake.calls[1][3]["Authorization"] == "Bearer abc123"
