"""Zhengzhou Commodity Exchange (CZCE) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

logger = logging.getLogger(__name__)

CZCE_PRODUCTS = [
    {"name_en": "White Sugar", "name_cn": "白糖", "ticker": "SR", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Cotton No.1", "name_cn": "棉花", "ticker": "CF", "unit": 5, "quote": "CNY/ton", "tick": 5, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Cotton Yarn", "name_cn": "棉纱", "ticker": "CY", "unit": 5, "quote": "CNY/ton", "tick": 5, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Rapeseed Oil", "name_cn": "菜籽油", "ticker": "OI", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Rapeseed Meal", "name_cn": "菜籽粕", "ticker": "RM", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Rapeseed", "name_cn": "油菜籽", "ticker": "RS", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "7,8,9,11", "group": "Agriculture"},
    {"name_en": "Strong Gluten Wheat", "name_cn": "强麦", "ticker": "WH", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Rice (Early Indica)", "name_cn": "早籼稻", "ticker": "RI", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,9,11", "group": "Agriculture"},
    {"name_en": "Rice (Late Indica)", "name_cn": "晚籼稻", "ticker": "LR", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "Japonica Rice", "name_cn": "粳稻", "ticker": "JR", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Agriculture"},
    {"name_en": "PTA", "name_cn": "PTA", "ticker": "TA", "unit": 5, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Chemical"},
    {"name_en": "Methanol", "name_cn": "甲醇", "ticker": "MA", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Flat Glass", "name_cn": "玻璃", "ticker": "FG", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Building Materials"},
    {"name_en": "Thermal Coal", "name_cn": "动力煤", "ticker": "ZC", "unit": 100, "quote": "CNY/ton", "tick": 0.2, "months": "1-12", "group": "Energy"},
    {"name_en": "Ferrosilicon", "name_cn": "硅铁", "ticker": "SF", "unit": 5, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Ferrous"},
    {"name_en": "Silicon Manganese", "name_cn": "锰硅", "ticker": "SM", "unit": 5, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Ferrous"},
    {"name_en": "Apple", "name_cn": "苹果", "ticker": "AP", "unit": 10, "quote": "CNY/ton", "tick": 1, "months": "1,3,5,7,10,11,12", "group": "Agriculture"},
    {"name_en": "Red Date", "name_cn": "红枣", "ticker": "CJ", "unit": 5, "quote": "CNY/ton", "tick": 5, "months": "1,3,5,7,9,12", "group": "Agriculture"},
    {"name_en": "Urea", "name_cn": "尿素", "ticker": "UR", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Soda Ash", "name_cn": "纯碱", "ticker": "SA", "unit": 20, "quote": "CNY/ton", "tick": 1, "months": "1-12", "group": "Chemical"},
    {"name_en": "Short Fiber", "name_cn": "短纤", "ticker": "PF", "unit": 5, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Chemical"},
    {"name_en": "Peanut Kernel", "name_cn": "花生", "ticker": "PK", "unit": 5, "quote": "CNY/ton", "tick": 2, "months": "1-12", "group": "Agriculture"},
]


class CZCECollector(BaseCollector):
    exchange_code = "CZCE"
    exchange_name_en = "Zhengzhou Commodity Exchange"
    exchange_name_cn = "郑州商品交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in CZCE_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["unit"]))
            spec = ContractSpec(
                exchange_code="CZCE",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_name_cn=prod["name_cn"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{prod['unit']} tons/lot",
                contract_size_numeric=Decimal(str(prod["unit"])),
                quote_unit=prod["quote"],
                quote_currency="CNY",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="CNY",
                contract_months=prod["months"],
                trading_hours_regular="09:00-10:15, 10:30-11:30, 13:30-15:00",
                trading_hours_electronic="21:00-23:30 (varies by product)",
                trading_hours_notes="Beijing Time (UTC+8)",
                price_limit_daily="±4%-±7% (varies by product)",
                price_limit_type="variable",
                delivery_method=DeliveryMethod.PHYSICAL,
                source_url="https://www.czce.com.cn/cn/jysj/jscs/H770303index_1.htm",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
