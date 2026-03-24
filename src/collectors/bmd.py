"""Bursa Malaysia Derivatives (BMD) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

BMD_PRODUCTS = [
    {"name_en": "Crude Palm Oil Futures", "name_cn": "毛棕榈油期货", "ticker": "FCPO", "unit": 25, "unit_desc": "metric tonnes", "quote": "MYR/tonne", "tick": 1, "tick_val": 25, "months": "Spot + 24 months", "group": "Agriculture", "delivery": "physical"},
    {"name_en": "Palm Kernel Oil Futures", "ticker": "FPKO", "unit": 25, "unit_desc": "metric tonnes", "quote": "MYR/tonne", "tick": 1, "tick_val": 25, "months": "Spot + 12 months", "group": "Agriculture", "delivery": "physical"},
    {"name_en": "Refined Palm Oil Futures", "ticker": "FPOL", "unit": 25, "unit_desc": "metric tonnes", "quote": "USD/tonne", "tick": 0.5, "tick_val": 12.5, "months": "Spot + 24 months", "group": "Agriculture", "delivery": "cash"},
    {"name_en": "FTSE Bursa Malaysia KLCI Futures", "ticker": "FKLI", "unit": 50, "unit_desc": "index", "quote": "MYR/point", "tick": 0.5, "tick_val": 25, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "3-Month KLIBOR Futures", "ticker": "FKB3", "unit": 1000000, "unit_desc": "MYR", "quote": "100 - rate", "tick": 0.01, "tick_val": 25, "months": "H,M,U,Z + 2 serial", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "Gold Futures", "ticker": "FGLD", "unit": 100, "unit_desc": "grams", "quote": "MYR/gram", "tick": 0.01, "tick_val": 1, "months": "even months", "group": "Metals", "delivery": "physical"},
    {"name_en": "Tin Futures", "ticker": "FTIN", "unit": 5000, "unit_desc": "kg", "quote": "MYR/kg", "tick": 0.5, "tick_val": 2500, "months": "1-12", "group": "Metals", "delivery": "physical"},
    {"name_en": "East Malaysia Crude Palm Oil Futures", "ticker": "FEPO", "unit": 25, "unit_desc": "metric tonnes", "quote": "MYR/tonne", "tick": 1, "tick_val": 25, "months": "Spot + 6 months", "group": "Agriculture", "delivery": "physical"},
]


class BMDCollector(BaseCollector):
    exchange_code = "BMD"
    exchange_name_en = "Bursa Malaysia Derivatives"
    exchange_name_cn = "马来西亚衍生品交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in BMD_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            ccy = "USD" if "USD" in prod["quote"] else "MYR"
            spec = ContractSpec(
                exchange_code="BMD", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_name_cn=prod.get("name_cn"),
                product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"{prod['unit']} {prod['unit_desc']}",
                contract_size_numeric=Decimal(str(prod["unit"])), contract_unit=prod["unit_desc"],
                quote_unit=prod["quote"], quote_currency=ccy,
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=ccy,
                contract_months=prod["months"],
                trading_hours_regular="09:00-12:30, 14:30-17:30 MYT",
                trading_hours_electronic="21:00-23:30 MYT (Night Session for FCPO)",
                trading_hours_notes="Malaysia Time (MYT, UTC+8)",
                delivery_method=dm, source_url="https://www.bursamalaysia.com/trade/our-products-services/derivatives/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
