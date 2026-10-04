# CME Machine-Readable Calendar Source

## Why the public webpage is not the automation source

The human-facing CME Trading Hours page is useful for research and manual
verification, but GitHub-hosted runners can receive HTTP 403 from that page.

The automation therefore uses two explicit layers:

1. **Verified baseline**
   - `config/cme_globex_holidays.yaml`
   - records the high-level annual holiday windows last verified against the
     official CME Trading Hours page;
   - keeps the Notion calendar coverage guard functional when no CME API
     credentials are configured.

2. **CME Reference Data API v3**
   - production endpoint:
     `https://refdata.api.cmegroup.com/refdata/v3/tradingSchedules`
   - OAuth token endpoint:
     `https://auth.cmegroup.com/as/token.oauth2`
   - requires an OAuth API ID and password;
   - Futures and Options Trading Schedules do not require an additional
     entitlement beyond a valid OAuth API ID.

## GitHub secrets

To enable live CME Trading Schedules, configure:

- `CME_API_ID`
- `CME_API_PASSWORD`

To enable Notion writes, also configure:

- `NOTION_TOKEN`

If CME credentials are absent, the workflow reports
`coverage_source_mode=verified_static_baseline` and does not pretend the
baseline is a live API pull.

## Data separation

The high-level holiday baseline is used only for completeness / coverage.

The Reference Data API payload is stored as a separate artifact
`cme_trading_schedules.json` so product-level schedule enrichment can be
developed and audited independently from the broad holiday-window layer.
