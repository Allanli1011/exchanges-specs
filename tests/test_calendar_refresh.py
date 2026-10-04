from datetime import date

from src.calendar_sources.cme_globex import (
    parse_cme_globex_holiday_windows,
    parse_date_range,
)
from src.exporters.notion_calendar import NotionCalendarClient


HTML = """
<html>
  <body>
    <h2>2026 CME Globex Trading Schedule</h2>
    <table>
      <tr>
        <th>U.S. HOLIDAY</th>
        <th>INCLUDES THE FOLLOWING DATES:</th>
        <th>HOLIDAY HOURS</th>
      </tr>
      <tr>
        <td>Thanksgiving</td>
        <td>26 - 28 November 2026</td>
        <td>Holiday Schedule</td>
      </tr>
      <tr>
        <td>Christmas</td>
        <td>24 - 26 December 2026</td>
        <td>Holiday Schedule</td>
      </tr>
      <tr>
        <td>New Year's</td>
        <td>31 December 2026 - 1 January 2027</td>
        <td>Holiday Schedule</td>
      </tr>
    </table>
  </body>
</html>
"""


def test_parse_cme_date_ranges():
    assert parse_date_range("26 - 28 November 2026") == (
        date(2026, 11, 26),
        date(2026, 11, 28),
    )
    assert parse_date_range("31 December 2026 – 1 January 2027") == (
        date(2026, 12, 31),
        date(2027, 1, 1),
    )


def test_parse_cme_globex_holiday_table():
    windows = parse_cme_globex_holiday_windows(HTML, 2026)

    assert [window.name for window in windows] == [
        "Thanksgiving",
        "Christmas",
        "New Year's",
    ]
    assert windows[0].event_key.startswith("cme-globex-2026-11-26-2026-11-28")
    assert windows[2].end_date == date(2027, 1, 1)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def request(self, method, url, headers, json):
        self.calls.append((method, url, json))
        if url.endswith("/query"):
            return FakeResponse({"results": self.pages, "has_more": False})
        if method == "POST" and url.endswith("/pages"):
            return FakeResponse({"id": "created-page"})
        return FakeResponse({"id": "updated-page"})


def _existing_cme_page():
    return {
        "id": "existing-page",
        "properties": {
            "Event": {
                "title": [
                    {"plain_text": "CME Group — Thanksgiving"}
                ]
            },
            "Event Key": {"rich_text": []},
            "Reference Period": {
                "rich_text": [{"plain_text": "Thanksgiving"}]
            },
            "Exchange": {
                "multi_select": [
                    {"name": "CME"},
                    {"name": "CBOT"},
                    {"name": "NYMEX"},
                    {"name": "COMEX"},
                ]
            },
            "Event Time (HKT)": {
                "date": {"start": "2026-11-26"}
            },
        },
    }


def test_notion_sync_claims_existing_cme_row_instead_of_duplicating():
    window = parse_cme_globex_holiday_windows(HTML, 2026)[0]
    fake = FakeClient([_existing_cme_page()])
    client = NotionCalendarClient(
        token="secret",
        data_source_id="calendar-ds",
        client=fake,
    )

    result = client.ensure_cme_windows([window], verified_on=date(2026, 10, 4))

    assert result[0].action == "claimed_existing"
    assert result[0].page_id == "existing-page"
    patch_calls = [call for call in fake.calls if call[0] == "PATCH"]
    assert len(patch_calls) == 1
    properties = patch_calls[0][2]["properties"]
    assert properties["Event Key"]["rich_text"][0]["text"]["content"] == window.event_key
    assert properties["Venue"]["rich_text"][0]["text"]["content"] == "CME Globex"


def test_notion_sync_creates_placeholder_when_calendar_has_gap():
    window = parse_cme_globex_holiday_windows(HTML, 2026)[1]
    fake = FakeClient([])
    client = NotionCalendarClient(
        token="secret",
        data_source_id="calendar-ds",
        client=fake,
    )

    result = client.ensure_cme_windows([window], verified_on=date(2026, 10, 4))

    assert result[0].action == "created_placeholder"
    create_calls = [
        call for call in fake.calls
        if call[0] == "POST" and call[1].endswith("/pages")
    ]
    assert len(create_calls) == 1
    props = create_calls[0][2]["properties"]
    assert props["Event Key"]["rich_text"][0]["text"]["content"] == window.event_key
    assert props["Exchange"]["multi_select"] == [
        {"name": "CME"},
        {"name": "CBOT"},
        {"name": "NYMEX"},
        {"name": "COMEX"},
    ]
