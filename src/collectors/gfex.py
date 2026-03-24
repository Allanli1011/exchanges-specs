"""Guangzhou Futures Exchange (GFEX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

GFEX_PRODUCTS = [
    {"name_en": "Lithium Carbonate", "name_cn": "碳酸锂", "ticker": "LC", "unit": 1, "unit_desc": "ton", "quote": "CNY/ton", "tick": 50, "months": "1-12", "group": "Metals"},
    {"name_en": "Industrial Silicon", "name_cn": "工业硅", "ticker": "SI", "unit": 5, "unit_desc": "tons", "quote": "CNY/ton", "tick": 5, "months": "1-12", "group": "Metals"},
]


class GFEXCollector(BaseCollector):
    exchange_code = "GFEX"
    exchange_name_en = "Guangzhou Futures Exchange"
    exchange_name_cn = "广州期货交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in GFEX_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit"]))
            spec = ContractSpec(
                exchange_code="GFEX",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_name_cn=prod["name_cn"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{prod['unit']} {prod['unit_desc']}/lot",
                contract_size_numeric=Decimal(str(prod["unit"])),
                contract_unit=prod["unit_desc"],
                quote_unit=prod["quote"],
                quote_currency="CNY",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="CNY",
                contract_months=prod["months"],
                trading_hours_regular="09:00-10:15, 10:30-11:30, 13:30-15:00",
                trading_hours_electronic="21:00-23:00",
                trading_hours_notes="Beijing Time (UTC+8)",
                price_limit_daily="±5%-±13%",
                delivery_method=DeliveryMethod.PHYSICAL,
                source_url="https://www.gfex.com.cn/gfex/hycs/sspzjs.shtml",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
