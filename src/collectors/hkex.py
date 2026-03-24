"""Hong Kong Exchanges and Clearing (HKEX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

HKEX_PRODUCTS = [
    {"name_en": "Hang Seng Index Futures", "name_cn": "恒生指数期货", "ticker": "HSI", "size": 50, "quote": "HKD/point", "tick": 1, "tick_val": 50, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Mini Hang Seng Index Futures", "name_cn": "小型恒指期货", "ticker": "MHI", "size": 10, "quote": "HKD/point", "tick": 1, "tick_val": 10, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Hang Seng TECH Index Futures", "name_cn": "恒生科技指数期货", "ticker": "HTI", "size": 50, "quote": "HKD/point", "tick": 1, "tick_val": 50, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "H-shares Index Futures", "name_cn": "国企指数期货", "ticker": "HHI", "size": 50, "quote": "HKD/point", "tick": 1, "tick_val": 50, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Mini H-shares Index Futures", "name_cn": "小型国企指数期货", "ticker": "MCH", "size": 10, "quote": "HKD/point", "tick": 1, "tick_val": 10, "months": "Spot + next + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "MSCI China A50 Connect Index Futures", "name_cn": "MSCI中国A50互联互通指数期货", "ticker": "MCA", "size": 5, "quote": "USD/point", "tick": 1, "tick_val": 5, "months": "2 serial + 2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "USD/CNH Futures", "name_cn": "美元兑人民币期货", "ticker": "CUS", "size": 100000, "quote": "CNH per USD", "tick": 0.0001, "tick_val": 10, "months": "12 consecutive", "group": "FX", "delivery": "physical"},
    {"name_en": "CNH Gold Futures", "name_cn": "人民币黄金期货", "ticker": "GDR", "size": 1000, "quote": "CNH/gram", "tick": 0.01, "tick_val": 10, "months": "Even months (6)", "group": "Metals", "delivery": "physical"},
    {"name_en": "USD Gold Futures", "name_cn": "美元黄金期货", "ticker": "GDU", "size": 100, "quote": "USD/troy oz", "tick": 0.01, "tick_val": 1, "months": "Even months (6)", "group": "Metals", "delivery": "physical"},
    {"name_en": "Iron Ore Futures", "name_cn": "铁矿石期货", "ticker": "FEM", "size": 100, "quote": "USD/tonne", "tick": 0.01, "tick_val": 1, "months": "Monthly (12)", "group": "Ferrous", "delivery": "cash"},
]


class HKEXCollector(BaseCollector):
    exchange_code = "HKEX"
    exchange_name_en = "Hong Kong Exchanges and Clearing"
    exchange_name_cn = "香港交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in HKEX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            ccy = "USD" if "USD" in prod["quote"] else "CNH" if "CNH" in prod["quote"] else "HKD"
            spec = ContractSpec(
                exchange_code="HKEX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_name_cn=prod.get("name_cn"),
                product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"{ccy} {prod['size']} x index" if "Index" in prod["name_en"] else f"{prod['size']:,} units",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency=ccy,
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=ccy,
                contract_months=prod["months"],
                trading_hours_regular="09:15-12:00, 13:00-16:30 HKT",
                trading_hours_electronic="17:15-03:00 HKT (After-Hours)",
                trading_hours_notes="Hong Kong Time (HKT, UTC+8)",
                delivery_method=dm, source_url="https://www.hkex.com.hk/Products/Listed-Derivatives/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
