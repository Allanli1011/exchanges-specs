"""Eurex Exchange collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

logger = logging.getLogger(__name__)

EUREX_PRODUCTS = [
    {"name_en": "Euro Stoxx 50 Futures", "ticker": "FESX", "size": 10, "quote": "EUR/point", "tick": 1, "tick_val": 10, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "DAX Futures", "ticker": "FDAX", "size": 25, "quote": "EUR/point", "tick": 0.5, "tick_val": 12.5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Mini-DAX Futures", "ticker": "FDXM", "size": 5, "quote": "EUR/point", "tick": 1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Micro-DAX Futures", "ticker": "FDXS", "size": 1, "quote": "EUR/point", "tick": 1, "tick_val": 1, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "STOXX Europe 600 Futures", "ticker": "FXXP", "size": 50, "quote": "EUR/point", "tick": 0.1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "VSTOXX Futures", "ticker": "FVS", "size": 100, "quote": "EUR/point", "tick": 0.05, "tick_val": 5, "months": "8 nearest months", "group": "Volatility", "delivery": "cash"},
    {"name_en": "Euro-Bund Futures", "ticker": "FGBL", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.01, "tick_val": 10, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Euro-Bobl Futures", "ticker": "FGBM", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.01, "tick_val": 10, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Euro-Schatz Futures", "ticker": "FGBS", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.005, "tick_val": 5, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Euro-Buxl Futures", "ticker": "FGBX", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.02, "tick_val": 20, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Euro-OAT Futures", "ticker": "FOAT", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.01, "tick_val": 10, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Euro-BTP Futures", "ticker": "FBTP", "size": 100000, "quote": "EUR per 100 nominal", "tick": 0.01, "tick_val": 10, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Three-Month EURIBOR Futures", "ticker": "FEU3", "size": 1000000, "quote": "100 - rate", "tick": 0.005, "tick_val": 12.5, "months": "H,M,U,Z + 2 serial", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "EURO STOXX Banks Futures", "ticker": "FESB", "size": 50, "quote": "EUR/point", "tick": 0.1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "MSCI World Futures", "ticker": "FMWO", "size": 10, "quote": "USD/point", "tick": 0.1, "tick_val": 1, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "MSCI Emerging Markets Futures", "ticker": "FMEM", "size": 50, "quote": "USD/point", "tick": 0.5, "tick_val": 25, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
]


class EurexCollector(BaseCollector):
    exchange_code = "EUREX"
    exchange_name_en = "Eurex Exchange"
    exchange_name_cn = "欧洲期货交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in EUREX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            ccy = "USD" if "USD" in prod["quote"] else "EUR"
            spec = ContractSpec(
                exchange_code="EUREX",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{ccy} {prod['size']} x index" if prod["group"] in ("Equity Index", "Volatility") else f"EUR {prod['size']:,} nominal",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"],
                quote_currency=ccy,
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])),
                tick_value_currency=ccy,
                contract_months=prod["months"],
                trading_hours_electronic="08:00-22:00 CET (varies)",
                trading_hours_notes="CET/CEST. T7 trading system.",
                delivery_method=dm,
                final_settlement_price="Based on index value at expiration" if dm == DeliveryMethod.CASH else None,
                source_url="https://www.eurex.com/ex-en/markets/",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
