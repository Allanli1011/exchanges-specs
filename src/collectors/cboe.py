"""CBOE Futures Exchange collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

CBOE_PRODUCTS = [
    {"name_en": "VIX Futures", "ticker": "VX", "size": 1000, "quote": "USD/point", "tick": 0.05, "tick_val": 50, "months": "weekly + 9 monthly + 6 quarterly", "group": "Volatility", "delivery": "cash",
     "tas_eligible": True, "tas_range": "+/- 0.01"},
    {"name_en": "Mini VIX Futures", "ticker": "VXM", "size": 100, "quote": "USD/point", "tick": 0.05, "tick_val": 5, "months": "6 monthly", "group": "Volatility", "delivery": "cash"},
    {"name_en": "S&P 500 Variance Futures", "ticker": "VA", "size": 1, "quote": "variance points", "tick": 0.01, "tick_val": 0.01, "months": "H,M,U,Z", "group": "Volatility", "delivery": "cash"},
    {"name_en": "Cboe Bitcoin U.S. ETF Index Futures", "ticker": "XBTF", "size": 1, "quote": "USD", "tick": 0.25, "tick_val": 0.25, "months": "6 serial", "group": "Cryptocurrency", "delivery": "cash"},
]


class CBOECollector(BaseCollector):
    exchange_code = "CBOE"
    exchange_name_en = "CBOE Futures Exchange"
    exchange_name_cn = "芝加哥期权交易所期货"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in CBOE_PRODUCTS:
            spec = ContractSpec(
                exchange_code="CBOE", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"USD {prod['size']:,} x VIX" if "VIX" in prod["name_en"] else f"{prod['size']} units",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency="USD",
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency="USD",
                contract_months=prod["months"],
                trading_hours_electronic="17:00-16:00 CT (Sun-Fri), 08:30-15:15 CT (regular)",
                trading_hours_notes="Central Time (CT, UTC-6/-5)",
                delivery_method=DeliveryMethod.CASH,
                final_settlement_price="SOQ of VIX on settlement date",
                tas_eligible=prod.get("tas_eligible"),
                tas_tick_range=prod.get("tas_range"),
                source_url="https://www.cboe.com/tradable_products/vix/vix_futures/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
