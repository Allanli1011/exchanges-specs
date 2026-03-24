"""Dalian Commodity Exchange (DCE) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)

DCE_PRODUCTS = [
    {"name_en": "Soybean No.1", "name_cn": "黄大豆一号", "ticker": "A", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Soybean No.2", "name_cn": "黄大豆二号", "ticker": "B", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Soybean Meal", "name_cn": "豆粕", "ticker": "M", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,8,9,11,12", "group": "Agriculture"},
    {"name_en": "Soybean Oil", "name_cn": "豆油", "ticker": "Y", "unit": 10, "quote": "CNY/ton", "tick": 2, "months": "1,3,5,7,8,9,11,12", "group": "Agriculture"},
    {"name_en": "Palm Oil", "name_cn": "棕榈油", "ticker": "P", "unit": 10, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Corn", "name_cn": "玉米", "ticker": "C", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Corn Starch", "name_cn": "玉米淀粉", "ticker": "CS", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Egg", "name_cn": "鸡蛋", "ticker": "JD", "unit": 10, "quote": "CNY/500kg", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Polyethylene (LLDPE)", "name_cn": "聚乙烯", "ticker": "L", "unit": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "group": "Chemical"},
    {"name_en": "PVC", "name_cn": "聚氯乙烯", "ticker": "V", "unit": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "group": "Chemical"},
    {"name_en": "Polypropylene", "name_cn": "聚丙烯", "ticker": "PP", "unit": 5, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Ethylene Glycol", "name_cn": "乙二醇", "ticker": "EG", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Styrene", "name_cn": "苯乙烯", "ticker": "EB", "unit": 5, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Iron Ore", "name_cn": "铁矿石", "ticker": "I", "unit": 100, "quote": "CNY/ton", "tick": 0.5, "months": "1-12", "group": "Ferrous"},
    {"name_en": "Coking Coal", "name_cn": "焦煤", "ticker": "JM", "unit": 60, "quote": "CNY/ton", "tick": 0.5, "months": "1-12", "group": "Ferrous"},
    {"name_en": "Coke", "name_cn": "焦炭", "ticker": "J", "unit": 100, "quote": "CNY/ton", "tick": 0.5, "months": "1-12", "group": "Ferrous"},
    {"name_en": "RBD Palm Olein", "name_cn": "棕榈油(国际)", "ticker": "PO", "unit": 10, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Agriculture"},
    {"name_en": "LPG", "name_cn": "液化石油气", "ticker": "PG", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Energy"},
    {"name_en": "Fiberboard", "name_cn": "纤维板", "ticker": "FB", "unit": 10, "quote": "CNY/m³", "tick": 0.5, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Blockboard", "name_cn": "胶合板", "ticker": "BB", "unit": 500, "quote": "CNY/sheet", "tick": 0.05, "months": "1-12", "group": "Agriculture"},
]


class DCECollector(BaseCollector):
    exchange_code = "DCE"
    exchange_name_en = "Dalian Commodity Exchange"
    exchange_name_cn = "大连商品交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in DCE_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit"]))
            spec = ContractSpec(
                exchange_code="DCE",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_name_cn=prod["name_cn"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{prod['unit']} tons/lot" if "ton" in prod["quote"] else f"{prod['unit']}/lot",
                contract_size_numeric=Decimal(str(prod["unit"])),
                quote_unit=prod["quote"],
                quote_currency="CNY",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="CNY",
                contract_months=prod["months"],
                trading_hours_regular="09:00-10:15, 10:30-11:30, 13:30-15:00",
                trading_hours_electronic="21:00-23:00 (varies by product)",
                trading_hours_notes="Beijing Time (UTC+8)",
                price_limit_daily="±4%-±8% (varies by product)",
                price_limit_type="variable",
                delivery_method=DeliveryMethod.PHYSICAL,
                source_url="https://www.dce.com.cn/dalianshangpin/yw/1277396/index.html",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
