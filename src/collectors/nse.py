"""National Stock Exchange of India (NSE) collector."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

NSE_CONTRACT_INFO_URL = "https://www.nseindia.com/static/products-services/equity-derivatives-contract-information"
NSE_LOT_SIZE_CSV_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
NSE_STOCK_FNO_URL = "https://www.nseindia.com/static/products-services/equity-derivatives-individual-securities"

STATIC_NSE_PRODUCTS = [
    {
        "name_en": "India VIX Futures",
        "ticker": "INDIAVIX",
        "size": 550,
        "quote": "INR/point",
        "tick": Decimal("0.25"),
        "months": "3 weekly + 3 monthly",
        "group": "Volatility",
        "delivery": DeliveryMethod.CASH,
        "source_url": NSE_CONTRACT_INFO_URL,
    },
    {
        "name_en": "USD/INR Futures",
        "ticker": "USDINR",
        "size": 1000,
        "quote": "INR/USD",
        "tick": Decimal("0.0025"),
        "months": "3 monthly",
        "group": "FX",
        "delivery": DeliveryMethod.CASH,
        "source_url": NSE_CONTRACT_INFO_URL,
    },
    {
        "name_en": "EUR/INR Futures",
        "ticker": "EURINR",
        "size": 1000,
        "quote": "INR/EUR",
        "tick": Decimal("0.0025"),
        "months": "3 monthly",
        "group": "FX",
        "delivery": DeliveryMethod.CASH,
        "source_url": NSE_CONTRACT_INFO_URL,
    },
    {
        "name_en": "GBP/INR Futures",
        "ticker": "GBPINR",
        "size": 1000,
        "quote": "INR/GBP",
        "tick": Decimal("0.0025"),
        "months": "3 monthly",
        "group": "FX",
        "delivery": DeliveryMethod.CASH,
        "source_url": NSE_CONTRACT_INFO_URL,
    },
    {
        "name_en": "JPY/INR Futures",
        "ticker": "JPYINR",
        "size": 100000,
        "quote": "INR/100JPY",
        "tick": Decimal("0.0025"),
        "months": "3 monthly",
        "group": "FX",
        "delivery": DeliveryMethod.CASH,
        "source_url": NSE_CONTRACT_INFO_URL,
    },
]

INDEX_DISPLAY_NAMES = {
    "NIFTY": "Nifty 50 Futures",
    "BANKNIFTY": "Bank Nifty Futures",
    "FINNIFTY": "Nifty Financial Services Futures",
    "MIDCPNIFTY": "Nifty Midcap Select Futures",
    "NIFTYNXT50": "Nifty Next 50 Futures",
}


def _clean_cell(value: str) -> str:
    return value.strip()


def _title_case_underlying(underlying: str) -> str:
    compact = " ".join(underlying.split())
    titled = compact.title()
    return titled.replace("(I)", "(I)").replace("&Amp;", "&")


def _parse_expiry_months(row: dict[str, str], month_headers: list[str]) -> list[str]:
    months: list[str] = []
    for header in month_headers:
        raw = _clean_cell(row.get(header, ""))
        if raw:
            months.append(header)
    return months


def parse_nse_lot_sizes(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[dict] = []
    section = "index"
    month_headers = [header.strip() for header in reader.fieldnames[2:]] if reader.fieldnames else []

    for raw_row in reader:
        normalized = {_clean_cell(k): _clean_cell(v) for k, v in raw_row.items() if k is not None}
        underlying = normalized.get("UNDERLYING", "")
        symbol = normalized.get("SYMBOL", "")

        if not underlying or not symbol:
            continue

        if underlying.lower().startswith("derivatives on individual securities"):
            section = "stock"
            continue

        expiries = _parse_expiry_months(normalized, month_headers)
        if not expiries:
            continue

        lot_size = int(normalized[expiries[0]])
        rows.append(
            {
                "section": section,
                "underlying": underlying,
                "symbol": symbol,
                "lot_size": lot_size,
                "expiries": expiries,
            }
        )

    return rows


class NSECollector(BaseCollector):
    exchange_code = "NSE"
    exchange_name_en = "National Stock Exchange of India"
    exchange_name_cn = "印度国家证券交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results: list[ContractSpec] = []
        now_str = datetime.now(timezone.utc).isoformat()

        notes_prefix = None
        try:
            lot_size_rows = await self._fetch_lot_size_rows()
            results.extend(self._build_equity_futures(lot_size_rows, now_str))
        except Exception as exc:
            self.logger.warning(f"NSE official lot-size CSV unavailable, falling back to static subset: {exc}")
            notes_prefix = "Official NSE lot size CSV was unavailable during this run. "
            results.extend(self._build_static_fallback_equity(now_str, notes_prefix))

        seen_tickers = {spec.ticker for spec in results}
        for prod in STATIC_NSE_PRODUCTS:
            if prod["ticker"] in seen_tickers:
                continue
            results.append(self._build_static_contract(prod, now_str, notes_prefix=notes_prefix))

        return results

    async def _fetch_lot_size_rows(self) -> list[dict]:
        csv_text = await self.client.get(
            NSE_LOT_SIZE_CSV_URL,
            headers={
                "Referer": NSE_CONTRACT_INFO_URL,
                "Accept": "text/csv,*/*;q=0.8",
            },
            rate_limit=self.rate_limit,
        )
        return parse_nse_lot_sizes(csv_text)

    def _build_equity_futures(self, rows: list[dict], now_str: str) -> list[ContractSpec]:
        results: list[ContractSpec] = []
        for row in rows:
            is_index = row["section"] == "index"
            lot_size = Decimal(str(row["lot_size"]))
            tick_size = Decimal("0.05")
            expiries = row["expiries"]
            ticker = row["symbol"]

            if is_index:
                product_name = INDEX_DISPLAY_NAMES.get(ticker, f"{_title_case_underlying(row['underlying'])} Futures")
                quote_unit = "INR/point"
                contract_size = f"INR {row['lot_size']} x index"
                contract_unit = "index multiplier"
                delivery_method = DeliveryMethod.CASH
                product_group = "Equity Index"
                source_url = NSE_CONTRACT_INFO_URL
                notes = "Lot size and listed expiries sourced from NSE permitted lot size CSV."
            else:
                product_name = f"{_title_case_underlying(row['underlying'])} Futures"
                quote_unit = "INR/share"
                contract_size = f"{row['lot_size']:,} shares"
                contract_unit = "shares"
                delivery_method = DeliveryMethod.PHYSICAL
                product_group = "Single Stock"
                source_url = NSE_STOCK_FNO_URL
                notes = (
                    "Lot size and listed expiries sourced from NSE permitted lot size CSV; "
                    "individual securities derivatives are physically settled on NSE."
                )

            spec = ContractSpec(
                exchange_code="NSE",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=product_name,
                product_group=product_group,
                ticker=ticker,
                contract_size=contract_size,
                contract_size_numeric=lot_size,
                contract_unit=contract_unit,
                quote_unit=quote_unit,
                quote_currency="INR",
                tick_size=str(tick_size),
                tick_size_numeric=tick_size,
                tick_value=lot_size * tick_size,
                tick_value_currency="INR",
                contract_months=", ".join(expiries),
                listed_contracts=str(len(expiries)),
                trading_hours_regular="09:15-15:30 IST",
                trading_hours_notes="Indian Standard Time (IST, UTC+5:30). NSE equity derivatives session.",
                delivery_method=delivery_method,
                source_url=source_url,
                source_type="csv+html",
                last_updated=now_str,
                notes=notes,
            )
            results.append(spec)

        return results

    def _build_static_fallback_equity(self, now_str: str, notes_prefix: str | None = None) -> list[ContractSpec]:
        fallback_equity = [
            {
                "name_en": "Nifty 50 Futures",
                "ticker": "NIFTY",
                "size": 65,
                "quote": "INR/point",
                "tick": Decimal("0.05"),
                "months": "3 serial + 5 quarterly",
                "group": "Equity Index",
                "delivery": DeliveryMethod.CASH,
            },
            {
                "name_en": "Bank Nifty Futures",
                "ticker": "BANKNIFTY",
                "size": 30,
                "quote": "INR/point",
                "tick": Decimal("0.05"),
                "months": "3 serial + 3 quarterly",
                "group": "Equity Index",
                "delivery": DeliveryMethod.CASH,
            },
            {
                "name_en": "Nifty Financial Services Futures",
                "ticker": "FINNIFTY",
                "size": 60,
                "quote": "INR/point",
                "tick": Decimal("0.05"),
                "months": "3 serial",
                "group": "Equity Index",
                "delivery": DeliveryMethod.CASH,
            },
            {
                "name_en": "Nifty Midcap Select Futures",
                "ticker": "MIDCPNIFTY",
                "size": 120,
                "quote": "INR/point",
                "tick": Decimal("0.05"),
                "months": "3 serial",
                "group": "Equity Index",
                "delivery": DeliveryMethod.CASH,
            },
            {
                "name_en": "Nifty Next 50 Futures",
                "ticker": "NIFTYNXT50",
                "size": 25,
                "quote": "INR/point",
                "tick": Decimal("0.05"),
                "months": "3 serial",
                "group": "Equity Index",
                "delivery": DeliveryMethod.CASH,
            },
        ]

        return [
            self._build_static_contract(
                {**prod, "source_url": NSE_CONTRACT_INFO_URL},
                now_str,
                notes_prefix=notes_prefix,
            )
            for prod in fallback_equity
        ]

    def _build_static_contract(self, prod: dict, now_str: str, notes_prefix: str | None = None) -> ContractSpec:
        tick_value = Decimal(str(prod["size"])) * prod["tick"]
        base_note = "Static fallback because this product is not present in NSE lot size CSV."
        return ContractSpec(
            exchange_code="NSE",
            exchange_name_en=self.exchange_name_en,
            exchange_name_cn=self.exchange_name_cn,
            product_name_en=prod["name_en"],
            product_group=prod["group"],
            ticker=prod["ticker"],
            contract_size=(
                f"INR {prod['size']} x index"
                if prod["group"] in {"Equity Index", "Volatility"}
                else f"{prod['size']:,}"
            ),
            contract_size_numeric=Decimal(str(prod["size"])),
            quote_unit=prod["quote"],
            quote_currency="INR",
            tick_size=str(prod["tick"]),
            tick_size_numeric=prod["tick"],
            tick_value=tick_value,
            tick_value_currency="INR",
            contract_months=prod["months"],
            trading_hours_regular="09:15-15:30 IST",
            trading_hours_notes="Indian Standard Time (IST, UTC+5:30). Static fallback metadata.",
            delivery_method=prod["delivery"],
            source_url=prod["source_url"],
            source_type="static",
            last_updated=now_str,
            notes=f"{notes_prefix or ''}{base_note}".strip(),
        )
