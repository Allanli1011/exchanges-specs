"""Korea Exchange (KRX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

KRX_PRODUCTS = [
    {"name_en": "KOSPI 200 Futures", "name_cn": "韩国KOSPI200指数期货", "ticker": "K200", "size": 250000, "quote": "KRW/point", "tick": 0.05, "tick_val": 12500, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Mini KOSPI 200 Futures", "ticker": "K200M", "size": 50000, "quote": "KRW/point", "tick": 0.05, "tick_val": 2500, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "KOSDAQ 150 Futures", "ticker": "KQ150", "size": 10000, "quote": "KRW/point", "tick": 0.1, "tick_val": 1000, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "KRX 300 Futures", "ticker": "KRX300", "size": 10000, "quote": "KRW/point", "tick": 0.05, "tick_val": 500, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "3-Year KTB Futures", "ticker": "KTB3", "size": 100000000, "quote": "KRW per 100", "tick": 0.01, "tick_val": 10000, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "10-Year KTB Futures", "ticker": "KTB10", "size": 100000000, "quote": "KRW per 100", "tick": 0.01, "tick_val": 10000, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "cash"},
    {"name_en": "USD/KRW Futures", "ticker": "USDKRW", "size": 10000, "quote": "KRW/USD", "tick": 0.1, "tick_val": 1000, "months": "12 consecutive", "group": "FX", "delivery": "cash"},
    {"name_en": "Gold Futures", "ticker": "KAU", "size": 1000, "quote": "KRW/gram", "tick": 10, "tick_val": 10000, "months": "even months", "group": "Metals", "delivery": "physical"},
    {"name_en": "Lean Hog Futures", "ticker": "LHG", "size": 1000, "quote": "KRW/kg", "tick": 5, "tick_val": 5000, "months": "1-12", "group": "Agriculture", "delivery": "cash"},
    {"name_en": "V-KOSPI 200 Futures", "ticker": "VKSP", "size": 250000, "quote": "KRW/point", "tick": 0.05, "tick_val": 12500, "months": "nearest 3", "group": "Volatility", "delivery": "cash"},
]


class KRXCollector(BaseCollector):
    exchange_code = "KRX"
    exchange_name_en = "Korea Exchange"
    exchange_name_cn = "韩国交易所"
    rate_limit = 3.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in KRX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="KRX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_name_cn=prod.get("name_cn"),
                product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"KRW {prod['size']:,} x index" if "Index" in prod["group"] or "Volatility" in prod["group"] else f"{prod['size']:,} units",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency="KRW",
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency="KRW",
                contract_months=prod["months"],
                trading_hours_regular="09:00-15:45 KST",
                trading_hours_notes="Korea Standard Time (KST, UTC+9)",
                delivery_method=dm,
                source_url="https://global.krx.co.kr/contents/GLB/05/0501/0501010000/GLB0501010000.jsp",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
