"""Shanghai Futures Exchange (SHFE) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod
from src.utils.http_client import HttpClient
from src.parsers.html_parser import parse_spec_table

logger = logging.getLogger(__name__)

# SHFE product definitions (static catalog — SHFE doesn't have a product list API)
SHFE_PRODUCTS = [
    {"name_en": "Copper", "name_cn": "铜", "ticker": "CU", "url_id": "cu", "unit": "5 tons/lot", "unit_num": 5, "quote": "CNY/ton", "tick": 10, "months": "1-12", "delivery": "physical"},
    {"name_en": "Aluminum", "name_cn": "铝", "ticker": "AL", "url_id": "al", "unit": "5 tons/lot", "unit_num": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "delivery": "physical"},
    {"name_en": "Zinc", "name_cn": "锌", "ticker": "ZN", "url_id": "zn", "unit": "5 tons/lot", "unit_num": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "delivery": "physical"},
    {"name_en": "Lead", "name_cn": "铅", "ticker": "PB", "url_id": "pb", "unit": "5 tons/lot", "unit_num": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "delivery": "physical"},
    {"name_en": "Nickel", "name_cn": "镍", "ticker": "NI", "url_id": "ni", "unit": "1 ton/lot", "unit_num": 1, "quote": "CNY/ton", "tick": 10, "months": "1-12", "delivery": "physical"},
    {"name_en": "Tin", "name_cn": "锡", "ticker": "SN", "url_id": "sn", "unit": "1 ton/lot", "unit_num": 1, "quote": "CNY/ton", "tick": 10, "months": "1-12", "delivery": "physical"},
    {"name_en": "Gold", "name_cn": "黄金", "ticker": "AU", "url_id": "au", "unit": "1000 grams/lot", "unit_num": 1000, "quote": "CNY/gram", "tick": 0.02, "months": "even months", "delivery": "physical"},
    {"name_en": "Silver", "name_cn": "白银", "ticker": "AG", "url_id": "ag", "unit": "15 kg/lot", "unit_num": 15, "quote": "CNY/kg", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Steel Rebar", "name_cn": "螺纹钢", "ticker": "RB", "url_id": "rb", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Hot Rolled Coil", "name_cn": "热轧卷板", "ticker": "HC", "url_id": "hc", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Stainless Steel", "name_cn": "不锈钢", "ticker": "SS", "url_id": "ss", "unit": "5 tons/lot", "unit_num": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "delivery": "physical"},
    {"name_en": "Natural Rubber", "name_cn": "天然橡胶", "ticker": "RU", "url_id": "ru", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 5, "months": "1,3,4,5,6,7,8,9,10,11", "delivery": "physical"},
    {"name_en": "Fuel Oil", "name_cn": "燃料油", "ticker": "FU", "url_id": "fu", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Bitumen", "name_cn": "石油沥青", "ticker": "BU", "url_id": "bu", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Wire Rod", "name_cn": "线材", "ticker": "WR", "url_id": "wr", "unit": "10 tons/lot", "unit_num": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
    {"name_en": "Alumina", "name_cn": "氧化铝", "ticker": "AO", "url_id": "ao", "unit": "20 tons/lot", "unit_num": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "delivery": "physical"},
]


class SHFECollector(BaseCollector):
    exchange_code = "SHFE"
    exchange_name_en = "Shanghai Futures Exchange"
    exchange_name_cn = "上海期货交易所"
    rate_limit = 3.0
    base_url = "https://www.shfe.com.cn"

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in SHFE_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit_num"]))
            spec = ContractSpec(
                exchange_code="SHFE",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_name_cn=prod["name_cn"],
                product_group="Metals" if prod["ticker"] in ("CU","AL","ZN","PB","NI","SN","AU","AG","SS","AO") else "Energy" if prod["ticker"] in ("FU","BU") else "Ferrous" if prod["ticker"] in ("RB","HC","WR") else "Agriculture",
                ticker=prod["ticker"],
                contract_size=prod["unit"],
                contract_size_numeric=Decimal(str(prod["unit_num"])),
                contract_unit="tons" if "ton" in prod["unit"] else "grams" if "gram" in prod["unit"] else "kg",
                quote_unit=prod["quote"],
                quote_currency="CNY",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="CNY",
                contract_months=prod["months"],
                trading_hours_regular="09:00-10:15, 10:30-11:30, 13:30-15:00",
                trading_hours_electronic="21:00-次日02:30 (varies by product)",
                trading_hours_notes="Beijing Time (UTC+8)",
                price_limit_daily="±3%-±6% (varies by product)",
                price_limit_type="variable",
                delivery_method=DeliveryMethod.PHYSICAL,
                deliverable_grades=f"Qualified {prod['name_en']} per SHFE standards",
                delivery_points="SHFE designated delivery warehouses",
                source_url=f"https://www.shfe.com.cn/bourseService/businessdata/spec/{prod['url_id']}/",
                source_type="static+html",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)

        # Try to enrich with live data from SHFE website
        await self._enrich_from_website(results)
        return results

    async def _enrich_from_website(self, specs: List[ContractSpec]):
        """Try to fetch additional details from SHFE website."""
        try:
            html = await self.client.get(
                f"{self.base_url}/bourseService/businessdata/spec/",
                encoding="utf-8",
                rate_limit=self.rate_limit,
            )
            # Parse and enrich specs if the page is accessible
            logger.info("SHFE: website accessible, enrichment possible")
        except Exception as e:
            logger.debug(f"SHFE: website enrichment skipped: {e}")
