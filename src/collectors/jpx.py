"""Japan Exchange Group (JPX) collector — OSE + TOCOM."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

JPX_PRODUCTS = [
    {"name_en": "Nikkei 225 Futures", "ticker": "NK225", "sub": "OSE", "size": 1000, "quote": "JPY/point", "tick": 10, "tick_val": 10000, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "Nikkei 225 Mini Futures", "ticker": "NK225M", "sub": "OSE", "size": 100, "quote": "JPY/point", "tick": 5, "tick_val": 500, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "Nikkei 225 Micro Futures", "ticker": "NK225MC", "sub": "OSE", "size": 10, "quote": "JPY/point", "tick": 5, "tick_val": 50, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "TOPIX Futures", "ticker": "TOPIX", "sub": "OSE", "size": 10000, "quote": "JPY/point", "tick": 0.5, "tick_val": 5000, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "Mini TOPIX Futures", "ticker": "TOPIXM", "sub": "OSE", "size": 1000, "quote": "JPY/point", "tick": 0.25, "tick_val": 250, "months": "H,M,U,Z + 2 serial", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "JPX-Nikkei 400 Futures", "ticker": "JN400", "sub": "OSE", "size": 100, "quote": "JPY/point", "tick": 5, "tick_val": 500, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "10-Year JGB Futures", "ticker": "JGB", "sub": "OSE", "size": 100000000, "quote": "JPY per 100 face", "tick": 0.01, "tick_val": 10000, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Gold Standard Futures", "ticker": "JAU", "sub": "TOCOM", "size": 1000, "quote": "JPY/gram", "tick": 1, "tick_val": 1000, "months": "even months", "group": "Metals", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Gold Mini Futures", "ticker": "JAUM", "sub": "TOCOM", "size": 100, "quote": "JPY/gram", "tick": 1, "tick_val": 100, "months": "even months", "group": "Metals", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "Silver Futures", "ticker": "JAG", "sub": "TOCOM", "size": 10000, "quote": "JPY/10g", "tick": 0.1, "tick_val": 1000, "months": "even months", "group": "Metals", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Platinum Standard Futures", "ticker": "JPL", "sub": "TOCOM", "size": 500, "quote": "JPY/gram", "tick": 1, "tick_val": 500, "months": "even months", "group": "Metals", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Palladium Futures", "ticker": "JPA", "sub": "TOCOM", "size": 500, "quote": "JPY/gram", "tick": 1, "tick_val": 500, "months": "even months", "group": "Metals", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Rubber (RSS3) Futures", "ticker": "JRU", "sub": "TOCOM", "size": 5000, "quote": "JPY/kg", "tick": 0.1, "tick_val": 500, "months": "1-12", "group": "Agriculture", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Dubai Crude Oil Futures", "ticker": "JCO", "sub": "TOCOM", "size": 50, "quote": "JPY/kiloliter", "tick": 10, "tick_val": 500, "months": "1-12 (6 consecutive)", "group": "Energy", "delivery": "cash", "ccy": "JPY"},
    {"name_en": "Gasoline Futures", "ticker": "JGA", "sub": "TOCOM", "size": 50, "quote": "JPY/kiloliter", "tick": 10, "tick_val": 500, "months": "1-12 (6 consecutive)", "group": "Energy", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Kerosene Futures", "ticker": "JKE", "sub": "TOCOM", "size": 50, "quote": "JPY/kiloliter", "tick": 10, "tick_val": 500, "months": "1-12 (6 consecutive)", "group": "Energy", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Corn Futures (TOCOM)", "ticker": "JCN", "sub": "TOCOM", "size": 50, "quote": "JPY/tonne", "tick": 10, "tick_val": 500, "months": "1,3,5,7,9,11", "group": "Agriculture", "delivery": "physical", "ccy": "JPY"},
    {"name_en": "Soybean Futures (TOCOM)", "ticker": "JSO", "sub": "TOCOM", "size": 25, "quote": "JPY/tonne", "tick": 10, "tick_val": 250, "months": "1-12", "group": "Agriculture", "delivery": "physical", "ccy": "JPY"},
]


class JPXCollector(BaseCollector):
    exchange_code = "JPX"
    exchange_name_en = "Japan Exchange Group"
    exchange_name_cn = "日本交易所集团"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in JPX_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="JPX", exchange_sub=prod["sub"],
                exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"JPY {prod['size']:,} x index" if "Index" in prod["group"] else f"{prod['size']:,} units",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency=prod["ccy"],
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=prod["ccy"],
                contract_months=prod["months"],
                trading_hours_electronic="08:45-15:15, 16:30-06:00 JST",
                trading_hours_notes="Japan Standard Time (JST, UTC+9)",
                delivery_method=dm,
                source_url="https://www.jpx.co.jp/english/derivatives/products/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
