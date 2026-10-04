# Automated Exchange Calendar Refresh

The calendar pipeline separates **coverage**, **exact machine-readable schedules**
and **source-change monitoring**.

## CME

### Coverage guard

The annual high-level CME Globex holiday windows live in
`config/cme_globex_holidays.yaml`.

This baseline was verified against the official CME Trading Hours page and is
used to ensure the Notion calendar does not silently miss an entire holiday
window.

The sync is conservative:

1. Load the verified holiday windows.
2. Generate a stable `event_key`.
3. Query the existing Notion Global Trading & Macro Calendar.
4. If a detailed CME/CBOT/NYMEX/COMEX row already covers the holiday, claim the
   existing row by adding `Event Key` and `Venue=CME Globex`.
5. Only create a broad placeholder when there is a genuine coverage gap.
6. Never overwrite detailed product-specific notes or hours with the broad
   annual baseline.

### Exact Trading Schedules

When the GitHub secrets `CME_API_ID` and `CME_API_PASSWORD` are present,
the workflow authenticates with CME OAuth and downloads the official Reference
Data API v3 `tradingSchedules` dataset.

The raw response is stored as `cme_trading_schedules.json` for product-level
enrichment and audit.

If the credentials are absent, the workflow says so explicitly and continues
with the verified coverage baseline. It does not label the baseline as a live
API refresh.

## ICE / SGX source watch

The weekly job fingerprints:

- ICE Holiday Hours page
- ICE Futures Europe Trading Schedule PDF
- SGX-DT 2026 derivatives holiday circular

The first run establishes a baseline. Future content changes appear as
`status=changed` in `calendar_source_watch.json`, providing a machine-visible
signal that detailed holiday entries may need to be refreshed.

## Notion writes

Without `NOTION_TOKEN`, all jobs remain read/compute-only and produce
artifacts.

With `NOTION_TOKEN`, the CME coverage guard can claim existing rows and create
missing placeholders in the Global Trading & Macro Calendar.

## Automation cadence

`.github/workflows/calendar-refresh.yml` runs every Sunday at **00:00 UTC**,
can be triggered manually, and also runs after calendar-pipeline changes are
merged to `main`.

## Next enrichment adapters

- Translate CME Reference Data `marketEventsByDate` into product-level Notion
  close/open segments.
- Parse ICE holiday notices into product-specific early-close rows.
- Parse SGX-DT circular tables into commodity/non-commodity product scopes.
- Add LME exchange-holiday and prompt-date substitution logic.
- Add HKEX Holiday Trading product exceptions.
