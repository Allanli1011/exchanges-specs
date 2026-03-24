"""ASX (Australian Securities Exchange) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

ASX_PRODUCTS = [
    {"name_en": "S&P/ASX 200 Index Futures", "ticker": "AP", "size": 25, "quote": "AUD/point", "tick": 1, "tick_val": 25, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "S&P/ASX 200 Mini Futures", "ticker": "XP", "size": 5, "quote": "AUD/point", "tick": 1, "tick_val": 5, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "3-Year Commonwealth Treasury Bond Futures", "ticker": "YT", "size": 100000, "quote": "100 - yield", "tick": 0.01, "tick_val": 28.87, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "10-Year Commonwealth Treasury Bond Futures", "ticker": "XT", "size": 100000, "quote": "100 - yield", "tick": 0.005, "tick_val": 43.08, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "90-Day Bank Bill Futures", "ticker": "IR", "size": 1000000, "quote": "100 - yield", "tick": 0.01, "tick_val": 24.66, "months": "H,M,U,Z + 2 serial", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "30-Day Interbank Cash Rate Futures", "ticker": "IB", "size": 3000000, "quote": "100 - rate", "tick": 0.005, "tick_val": 12.33, "months": "6 serial", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "Wheat (Eastern Australia) Futures", "ticker": "WM", "size": 20, "quote": "AUD/tonne", "tick": 0.5, "tick_val": 10, "months": "F,H,K,N,X", "group": "Agriculture", "delivery": "physical"},
    {"name_en": "Electricity Futures (Baseload NSW)", "ticker": "EN", "size": 1, "quote": "AUD/MWh", "tick": 0.01, "tick_val": 0.01, "months": "quarterly", "group": "Energy", "delivery": "cash"},
    {"name_en": "AUD/USD Futures", "ticker": "AU", "size": 100000, "quote": "USD/AUD", "tick": 0.0001, "tick_val": 10, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
]


class ASXCollector(BaseCollector):
    exchange_code = "ASX"
    exchange_name_en = "ASX (Australian Securities Exchange)"
    exchange_name_cn = "澳大利亚证券交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in ASX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="ASX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"AUD {prod['size']:,} x index" if "Index" in prod["group"] else f"{prod['size']:,} AUD",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency="AUD",
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency="AUD",
                contract_months=prod["months"],
                trading_hours_electronic="17:10-07:00, 09:50-16:30 AEST",
                trading_hours_notes="Australian Eastern Standard Time (AEST, UTC+10/11)",
                delivery_method=dm, source_url="https://www.asx.com.au/markets/trade-our-derivatives-market/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
