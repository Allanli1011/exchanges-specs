"""Taiwan Futures Exchange (TAIFEX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

TAIFEX_PRODUCTS = [
    {"name_en": "TAIEX Futures", "name_cn": "台指期货", "ticker": "TX", "size": 200, "quote": "TWD/point", "tick": 1, "tick_val": 200, "months": "2 serial + 3 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Mini-TAIEX Futures", "name_cn": "小型台指期货", "ticker": "MTX", "size": 50, "quote": "TWD/point", "tick": 1, "tick_val": 50, "months": "2 serial + 3 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "GreTai 50 Futures", "ticker": "GTF", "size": 100, "quote": "TWD/point", "tick": 0.05, "tick_val": 5, "months": "3 serial + 1 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "TPEX 200 Futures", "ticker": "TE", "size": 100, "quote": "TWD/point", "tick": 0.05, "tick_val": 5, "months": "2 serial + 1 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "Taiwan 50 Futures", "ticker": "T5F", "size": 100, "quote": "TWD/point", "tick": 0.05, "tick_val": 5, "months": "2 serial + 3 quarterly", "group": "Equity Index", "delivery": "cash"},
    {"name_en": "10-Year Government Bond Futures", "ticker": "GBF", "size": 5000000, "quote": "TWD per 100 face", "tick": 0.005, "tick_val": 250, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical"},
    {"name_en": "Gold Futures", "ticker": "GDF", "size": 10, "quote": "TWD/gram", "tick": 0.1, "tick_val": 1, "months": "even months", "group": "Metals", "delivery": "physical"},
    {"name_en": "USD/TWD Futures", "ticker": "UDF", "size": 50000, "quote": "TWD/USD", "tick": 0.001, "tick_val": 50, "months": "6 serial", "group": "FX", "delivery": "cash"},
]


class TAIFEXCollector(BaseCollector):
    exchange_code = "TAIFEX"
    exchange_name_en = "Taiwan Futures Exchange"
    exchange_name_cn = "台湾期货交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in TAIFEX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="TAIFEX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_name_cn=prod.get("name_cn"),
                product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"TWD {prod['size']:,} x index" if "Index" in prod["group"] else f"{prod['size']:,}",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency="TWD",
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency="TWD",
                contract_months=prod["months"],
                trading_hours_regular="08:45-13:45 TST",
                trading_hours_electronic="15:00-05:00 TST (After-Hours)",
                trading_hours_notes="Taiwan Standard Time (TST, UTC+8)",
                delivery_method=dm,
                source_url="https://www.taifex.com.tw/enl/eProducts/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
