"""National Stock Exchange of India (NSE) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

NSE_PRODUCTS = [
    {"name_en": "Nifty 50 Futures", "name_cn": "印度Nifty50指数期货", "ticker": "NIFTY", "size": 75, "quote": "INR/point", "tick": 0.05, "tick_val": 3.75, "months": "3 serial + 5 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Bank Nifty Futures", "ticker": "BANKNIFTY", "size": 30, "quote": "INR/point", "tick": 0.05, "tick_val": 1.5, "months": "3 serial + 3 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Nifty Financial Services Futures", "ticker": "FINNIFTY", "size": 40, "quote": "INR/point", "tick": 0.05, "tick_val": 2, "months": "3 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Nifty Midcap Select Futures", "ticker": "MIDCPNIFTY", "size": 75, "quote": "INR/point", "tick": 0.05, "tick_val": 3.75, "months": "3 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "India VIX Futures", "ticker": "INDIAVIX", "size": 550, "quote": "INR/point", "tick": 0.25, "tick_val": 137.5, "months": "3 weekly + 3 monthly", "group": "Volatility", "delivery": "cash"},
    {"name_en": "USD/INR Futures", "ticker": "USDINR", "size": 1000, "quote": "INR/USD", "tick": 0.0025, "tick_val": 2.5, "months": "12 monthly", "group": "FX", "delivery": "cash"},
    {"name_en": "EUR/INR Futures", "ticker": "EURINR", "size": 1000, "quote": "INR/EUR", "tick": 0.0025, "tick_val": 2.5, "months": "3 monthly", "group": "FX", "delivery": "cash"},
    {"name_en": "GBP/INR Futures", "ticker": "GBPINR", "size": 1000, "quote": "INR/GBP", "tick": 0.0025, "tick_val": 2.5, "months": "3 monthly", "group": "FX", "delivery": "cash"},
    {"name_en": "JPY/INR Futures", "ticker": "JPYINR", "size": 100000, "quote": "INR/100JPY", "tick": 0.0025, "tick_val": 2.5, "months": "3 monthly", "group": "FX", "delivery": "cash"},
]


class NSECollector(BaseCollector):
    exchange_code = "NSE"
    exchange_name_en = "National Stock Exchange of India"
    exchange_name_cn = "印度国家证券交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in NSE_PRODUCTS:
            spec = ContractSpec(
                exchange_code="NSE", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_name_cn=prod.get("name_cn"),
                product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"INR {prod['size']} x index" if "Index" in prod["group"] or "Volatility" in prod["group"] else f"{prod['size']:,}",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency="INR",
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency="INR",
                contract_months=prod["months"],
                trading_hours_regular="09:15-15:30 IST",
                trading_hours_notes="Indian Standard Time (IST, UTC+5:30). SEBI regulated.",
                price_limit_daily="±10% (circuit breaker for equity index futures)",
                delivery_method=DeliveryMethod.CASH,
                source_url="https://www.nseindia.com/products-services/equity-derivatives",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
