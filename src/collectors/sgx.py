"""Singapore Exchange (SGX) collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

SGX_PRODUCTS = [
    {"name_en": "Nikkei 225 Index Futures", "ticker": "NK", "size": 500, "quote": "JPY/point", "tick": 5, "tick_val": 2500, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "FTSE China A50 Index Futures", "ticker": "CN", "size": 1, "quote": "USD/point", "tick": 2.5, "tick_val": 2.5, "months": "2 serial + 4 quarterly", "group": "Equity Index", "delivery": "cash", "ccy": "USD"},
    {"name_en": "MSCI Singapore Index Futures", "ticker": "QZ", "size": 200, "quote": "SGD/point", "tick": 0.01, "tick_val": 2, "months": "2 serial + 4 quarterly", "group": "Equity Index", "delivery": "cash", "ccy": "SGD"},
    {"name_en": "Nifty 50 Index Futures", "ticker": "IN", "size": 2, "quote": "USD/point", "tick": 0.5, "tick_val": 1, "months": "2 serial + 4 quarterly", "group": "Equity Index", "delivery": "cash", "ccy": "USD"},
    {"name_en": "MSCI Taiwan Index Futures", "ticker": "TW", "size": 100, "quote": "USD/point", "tick": 0.1, "tick_val": 10, "months": "2 serial + 4 quarterly", "group": "Equity Index", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Iron Ore Futures (62% Fe)", "ticker": "FEF", "size": 100, "quote": "USD/dmt", "tick": 0.01, "tick_val": 1, "months": "monthly, 6 years", "group": "Ferrous", "delivery": "cash", "ccy": "USD"},
    {"name_en": "TSI Iron Ore CFR China (58% Fe)", "ticker": "FEM", "size": 100, "quote": "USD/dmt", "tick": 0.01, "tick_val": 1, "months": "monthly", "group": "Ferrous", "delivery": "cash", "ccy": "USD"},
    {"name_en": "Rubber RSS3", "ticker": "RT", "size": 5000, "quote": "USD cents/kg", "tick": 0.1, "tick_val": 5, "months": "1-12", "group": "Agriculture", "delivery": "physical", "ccy": "USD"},
    {"name_en": "Rubber TSR20", "ticker": "RU", "size": 5000, "quote": "USD cents/kg", "tick": 0.1, "tick_val": 5, "months": "1-12", "group": "Agriculture", "delivery": "physical", "ccy": "USD"},
]


class SGXCollector(BaseCollector):
    exchange_code = "SGX"
    exchange_name_en = "Singapore Exchange"
    exchange_name_cn = "新加坡交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in SGX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="SGX", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"{prod['ccy']} {prod['size']} x index" if "Index" in prod["name_en"] else f"{prod['size']:,} units",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency=prod["ccy"],
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=prod["ccy"],
                contract_months=prod["months"],
                trading_hours_electronic="08:30-18:15 SGT (T session), 18:30-05:15 SGT (T+1)",
                trading_hours_notes="Singapore Time (SGT, UTC+8)",
                delivery_method=dm,
                source_url="https://www.sgx.com/derivatives/products/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
