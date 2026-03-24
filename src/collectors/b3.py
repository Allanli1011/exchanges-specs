"""B3 - Brasil Bolsa Balcão collector."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

B3_PRODUCTS = [
    {"name_en": "Ibovespa Index Futures", "ticker": "IND", "size": 1, "quote": "BRL/point", "tick": 5, "tick_val": 5, "months": "even months", "group": "Equity Index", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "Mini Ibovespa Futures", "ticker": "WIN", "size": 0.2, "quote": "BRL/point", "tick": 5, "tick_val": 1, "months": "even months", "group": "Equity Index", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "US Dollar Futures", "ticker": "DOL", "size": 50000, "quote": "BRL/1000 USD", "tick": 0.5, "tick_val": 25, "months": "all months", "group": "FX", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "Mini US Dollar Futures", "ticker": "WDO", "size": 10000, "quote": "BRL/1000 USD", "tick": 0.5, "tick_val": 5, "months": "all months", "group": "FX", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "DI1 Interest Rate Futures", "ticker": "DI1", "size": 100000, "quote": "BRL (100000 at maturity)", "tick": 0.005, "tick_val": 0.5, "months": "all months (Jan mainly)", "group": "Interest Rate", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "Arabica Coffee Futures", "ticker": "ICF", "size": 100, "quote": "USD/60kg bag", "tick": 0.05, "tick_val": 5, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical", "ccy": "USD"},
    {"name_en": "Corn Futures (B3)", "ticker": "CCM", "size": 450, "quote": "BRL/60kg bag", "tick": 0.01, "tick_val": 4.5, "months": "1,3,5,7,8,9,11", "group": "Agriculture", "delivery": "physical", "ccy": "BRL"},
    {"name_en": "Live Cattle Futures (B3)", "ticker": "BGI", "size": 330, "quote": "BRL/arroba", "tick": 0.05, "tick_val": 16.5, "months": "all months", "group": "Agriculture", "delivery": "cash", "ccy": "BRL"},
    {"name_en": "Gold Futures (B3)", "ticker": "OZ1", "size": 250, "quote": "BRL/gram", "tick": 0.01, "tick_val": 2.5, "months": "even months", "group": "Metals", "delivery": "physical", "ccy": "BRL"},
    {"name_en": "Soybean Futures (B3)", "ticker": "SFI", "size": 450, "quote": "USD/60kg bag", "tick": 0.01, "tick_val": 4.5, "months": "H,K,N,U,X", "group": "Agriculture", "delivery": "physical", "ccy": "USD"},
]


class B3Collector(BaseCollector):
    exchange_code = "B3"
    exchange_name_en = "B3 - Brasil Bolsa Balcão"
    exchange_name_cn = "巴西证券期货交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()
        for prod in B3_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            spec = ContractSpec(
                exchange_code="B3", exchange_name_en=self.exchange_name_en, exchange_name_cn=self.exchange_name_cn,
                product_name_en=prod["name_en"], product_group=prod["group"], ticker=prod["ticker"],
                contract_size=f"{prod['ccy']} {prod['size']:,}",
                contract_size_numeric=Decimal(str(prod["size"])),
                quote_unit=prod["quote"], quote_currency=prod["ccy"],
                tick_size=str(prod["tick"]), tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])), tick_value_currency=prod["ccy"],
                contract_months=prod["months"],
                trading_hours_regular="09:00-18:00 BRT (varies)",
                trading_hours_notes="Brasilia Time (BRT, UTC-3)",
                delivery_method=dm,
                source_url="https://www.b3.com.br/en_us/products-and-services/trading/listed-derivatives/",
                source_type="static", last_updated=now_str, data_quality="complete",
            )
            results.append(spec)
        return results
