"""London Metal Exchange (LME) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

logger = logging.getLogger(__name__)

LME_PRODUCTS = [
    {"name_en": "LME Copper", "ticker": "CA", "unit": 25, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME Aluminium", "ticker": "AH", "unit": 25, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME Zinc", "ticker": "ZS", "unit": 25, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME Lead", "ticker": "PB", "unit": 25, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME Nickel", "ticker": "NI", "unit": 6, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 1, "group": "Base Metals"},
    {"name_en": "LME Tin", "ticker": "SN", "unit": 5, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 1, "group": "Base Metals"},
    {"name_en": "LME Aluminium Alloy", "ticker": "AA", "unit": 20, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME NASAAC", "ticker": "NA", "unit": 25, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Base Metals"},
    {"name_en": "LME Cobalt", "ticker": "CO", "unit": 1, "unit_desc": "tonne", "quote": "USD/tonne", "tick": 5, "group": "Minor Metals"},
    {"name_en": "LME Lithium Hydroxide", "ticker": "LH", "unit": 1, "unit_desc": "tonne", "quote": "USD/tonne", "tick": 1, "group": "EV Metals"},
    {"name_en": "LME Steel Scrap", "ticker": "SS", "unit": 10, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Ferrous"},
    {"name_en": "LME Steel Rebar", "ticker": "SR", "unit": 10, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Ferrous"},
    {"name_en": "LME Steel HRC", "ticker": "HC", "unit": 10, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.5, "group": "Ferrous"},
    {"name_en": "LME Gold", "ticker": "LG", "unit": 100, "unit_desc": "troy ounces", "quote": "USD/troy oz", "tick": 0.1, "group": "Precious Metals"},
    {"name_en": "LME Silver", "ticker": "LS", "unit": 5000, "unit_desc": "troy ounces", "quote": "USD cents/troy oz", "tick": 0.25, "group": "Precious Metals"},
]


class LMECollector(BaseCollector):
    exchange_code = "LME"
    exchange_name_en = "London Metal Exchange"
    exchange_name_cn = "伦敦金属交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in LME_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit"]))
            spec = ContractSpec(
                exchange_code="LME",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{prod['unit']} {prod['unit_desc']}",
                contract_size_numeric=Decimal(str(prod["unit"])),
                contract_unit=prod["unit_desc"],
                quote_unit=prod["quote"],
                quote_currency="USD",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="USD",
                contract_months="Daily (out to 3 months), weekly (3-6 months), monthly (out to 123 months for base metals)",
                trading_hours_regular="11:40-17:00 London (Ring + Kerb)",
                trading_hours_electronic="01:00-19:00 London (LMEselect)",
                trading_hours_notes="London Time (GMT/BST). Unique 3-month rolling prompt date structure.",
                delivery_method=DeliveryMethod.PHYSICAL,
                delivery_points="LME approved warehouses worldwide",
                deliverable_grades=f"LME registered brands of {prod['name_en'].replace('LME ', '')}",
                source_url="https://www.lme.com/en/metals/non-ferrous/",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
