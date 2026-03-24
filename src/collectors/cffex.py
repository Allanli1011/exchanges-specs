"""China Financial Futures Exchange (CFFEX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

CFFEX_PRODUCTS = [
    {"name_en": "CSI 300 Index Futures", "name_cn": "沪深300股指期货", "ticker": "IF", "size": 300, "unit": "CNY/point", "tick": 0.2, "months": "current+next+2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "SSE 50 Index Futures", "name_cn": "上证50股指期货", "ticker": "IH", "size": 300, "unit": "CNY/point", "tick": 0.2, "months": "current+next+2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "CSI 500 Index Futures", "name_cn": "中证500股指期货", "ticker": "IC", "size": 200, "unit": "CNY/point", "tick": 0.2, "months": "current+next+2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "CSI 1000 Index Futures", "name_cn": "中证1000股指期货", "ticker": "IM", "size": 200, "unit": "CNY/point", "tick": 0.2, "months": "current+next+2 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "2-Year Treasury Bond Futures", "name_cn": "2年期国债期货", "ticker": "TS", "size": 2000000, "unit": "CNY per 100 face", "tick": 0.005, "months": "Mar,Jun,Sep,Dec", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "5-Year Treasury Bond Futures", "name_cn": "5年期国债期货", "ticker": "TF", "size": 1000000, "unit": "CNY per 100 face", "tick": 0.005, "months": "Mar,Jun,Sep,Dec", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "10-Year Treasury Bond Futures", "name_cn": "10年期国债期货", "ticker": "T", "size": 1000000, "unit": "CNY per 100 face", "tick": 0.005, "months": "Mar,Jun,Sep,Dec", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "30-Year Treasury Bond Futures", "name_cn": "30年期国债期货", "ticker": "TL", "size": 1000000, "unit": "CNY per 100 face", "tick": 0.01, "months": "Mar,Jun,Sep,Dec", "group": "Interest Rate", "delivery": "physical"},
]


class CFFEXCollector(BaseCollector):
    exchange_code = "CFFEX"
    exchange_name_en = "China Financial Futures Exchange"
    exchange_name_cn = "中国金融期货交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in CFFEX_PRODUCTS:
            tick_val = Decimal(str(prod["tick"])) * Decimal(str(prod["size"]))
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL

            spec = ContractSpec(
                exchange_code="CFFEX",
                exchange_name_en=self.exchange_name_en,
                exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"],
                product_name_cn=prod["name_cn"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"CNY {prod['size']} x index" if "Index" in prod["name_en"] else f"CNY {prod['size']:,} face value",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["unit"],
                quote_currency="CNY",
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=tick_val,
                tick_value_currency="CNY",
                contract_months=prod["months"],
                trading_hours_regular="09:30-11:30, 13:00-15:00" if "Index" in prod["name_en"] else "09:15-11:30, 13:00-15:15",
                trading_hours_notes="Beijing Time (UTC+8). No night session.",
                price_limit_daily="±10% (index), ±2% (treasury)" if "Index" in prod["name_en"] else "±2%",
                delivery_method=dm,
                final_settlement_price="Arithmetic average of last 2 hours of trading on last day" if dm == DeliveryMethod.CASH else None,
                source_url="https://www.cffex.com.cn/en_new/sspz/",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
