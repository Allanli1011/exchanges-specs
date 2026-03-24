"""Shanghai International Energy Exchange (INE) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

INE_PRODUCTS = [
    {"name_en": "Crude Oil", "name_cn": "原油", "ticker": "SC", "unit": 1000, "unit_desc": "barrels", "quote": "CNY/barrel", "tick": 0.1, "months": "1-12", "group": "Energy"},
    {"name_en": "TSR 20 Rubber", "name_cn": "20号胶", "ticker": "NR", "unit": 10, "unit_desc": "tons", "quote": "CNY/ton", "tick": 5, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Low Sulfur Fuel Oil", "name_cn": "低硫燃料油", "ticker": "LU", "unit": 10, "unit_desc": "tons", "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Energy"},
    {"name_en": "Bonded Copper", "name_cn": "国际铜", "ticker": "BC", "unit": 5, "unit_desc": "tons", "quote": "CNY/ton", "tick": 10, "months": "1-12", "group": "Metals"},
]


class INECollector(BaseCollector):
    exchange_code = "INE"
    exchange_name_en = "Shanghai International Energy Exchange"
    exchange_name_cn = "上海国际能源交易中心"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in INE_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit"]))
            spec = ContractSpec(
                exchange_code="INE",
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
                trading_hours_electronic="21:00-02:30 (next day)",
                trading_hours_notes="Beijing Time (UTC+8). International participants eligible.",
                price_limit_daily="±4%-±10% (varies)",
                delivery_method=DeliveryMethod.PHYSICAL,
                delivery_points="INE designated bonded delivery warehouses",
                source_url="https://www.ine.cn/en/products/",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
