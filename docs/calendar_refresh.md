# Automated Exchange Calendar Refresh

The first live source adapter covers the official **CME Globex holiday
calendar** on CME Group's Trading Hours page.

The design is intentionally conservative:

1. Fetch the official annual holiday-window table.
2. Parse each holiday into a stable `event_key`.
3. Query the existing Notion Global Trading & Macro Calendar.
4. If a detailed CME/CBOT/NYMEX/COMEX row already covers that holiday, claim
   the existing row by adding `Event Key` and `Venue=CME Globex`.
5. Only create a broad coverage placeholder when the calendar has a genuine
   gap.
6. Never overwrite existing product-specific notes or hours with the broad
   annual table.

CME states holiday hours can change and are usually finalized roughly two
weeks before a holiday. The high-level annual table therefore acts as a
**coverage guard**, not a substitute for product-level holiday hours.

## Run locally

```bash
python -m src.calendar_refresh --output artifacts/exchange_calendar_refresh.json
```

Without `NOTION_TOKEN`, the command only writes the audit artifact.

With `NOTION_TOKEN`, it upserts/claims rows in the configured Notion data
source.

## Automation

`.github/workflows/calendar-refresh.yml` runs every Sunday at **00:00 UTC**
and can also be triggered manually.

## Exact product-level CME hours

For exact product/session-level schedules, CME also exposes its Reference Data
Trading Schedules API. That endpoint requires an OAuth API identity. The
calendar pipeline is structured so this can be added as a second-stage
enricher without changing the Notion event identity model.

## Next source adapters

- ICE Futures Europe / ICE Futures U.S. holiday-hours notices
- SGX-DT derivatives holiday circulars
- LME exchange holidays and prompt-date substitutions
- HKEX derivatives Holiday Trading product exceptions
