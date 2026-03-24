"""Moscow Exchange (MOEX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

MOEX_PRODUCTS = [
    {"name_en": "RTS Index Futures", "ticker": "RI", "size": 1, "quote": "RUB (USD-denominated index)", "tick": 10, "tick_val": 10, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "ccy": "USD"},
    {"name_en": "MOEX Index Futures", "ticker": "MX", "size": 1, "quote": "RUB/point", "tick": 0.25, "tick_val": 0.25, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "ccy": "RUB"},
    {"name_en": "USD/RUB Futures", "ticker": "Si", "size": 1000, "quote": "RUB/USD", "tick": 1, "tick_val": 1, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "cash", "ccy": "RUB"},
    {"name_en": "EUR/RUB Futures", "ticker": "Eu", "size": 1000, "quote": "RUB/EUR", "tick": 1, "tick_val": 1, "months": "H,M,U,Z", "group": "FX", "delivery": "cash", "ccy": "RUB"},
    {"name_en": "CNY/RUB Futures", "ticker": "CR", "size": 100000, "quote": "RUB/CNY", "tick": 0.001, "tick_val": 100, "months": "H,M,U,Z", "group": "FX", "delivery": "cash", "ccy": "RUB"},
    {"name_en": "Brent Crude Oil Futures (MOEX)", "ticker": "BR", "size": 10, "quote": "USD/barrel", "tick": 0.01, "tick_val": 0.1, "months": "1-12", "group": "Energy", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Gold Futures (MOEX)", "ticker": "GD", "size": 1, "quote": "USD/troy oz", "tick": 0.1, "tick_val": 0.1, "months": "H,M,U,Z", "group": "Metals", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Silver Futures (MOEX)", "ticker": "SV", "size": 10, "quote": "USD/troy oz", "tick": 0.01, "tick_val": 0.1, "months": "H,M,U,Z", "group": "Metals", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Natural Gas Futures (MOEX)", "ticker": "NG", "size": 10, "quote": "USD/MMBtu", "tick": 0.001, "tick_val": 0.01, "months": "1-12", "group": "Energy", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Palladium Futures (MOEX)", "ticker": "PD", "size": 1, "quote": "USD/troy oz", "tick": 0.5, "tick_val": 0.5, "months": "H,M,U,Z", "group": "Metals", "delivery": "cash", "ccy": "USD"},
]


class MOEXCollector(BaseCollector):
    exchange_code = "MOEX"
    exchange_name_en = "Moscow Exchange"
    exchange_name_cn = "莫斯科交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in MOEX_PRODUCTS:
            spec = ContractSpec(
                exchange_code="MOEX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"{prod['size']:,} {prod['ccy']}",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency=prod["ccy"],
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=prod["ccy"],
                contract_months=prod["months"],
                trading_hours_regular="10:00-18:50, 19:05-23:50 MSK",
                trading_hours_notes="Moscow Standard Time (MSK, UTC+3)",
                delivery_method=DeliveryMethod.CASH,
                source_url="https://www.moex.com/en/derivatives/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
