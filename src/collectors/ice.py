"""ICE Futures collector — covers ICE US and ICE Europe."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

logger = logging.getLogger(__name__)

ICE_US_PRODUCTS = [
    {"name_en": "Cotton No. 2", "ticker": "CT", "unit": 50000, "unit_desc": "lbs", "quote": "USD cents/lb", "tick": 0.01, "tick_val": 5, "months": "H,K,N,V,Z", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_US"},
    {"name_en": "Coffee C", "ticker": "KC", "unit": 37500, "unit_desc": "lbs", "quote": "USD cents/lb", "tick": 0.05, "tick_val": 18.75, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_US"},
    {"name_en": "Sugar No. 11", "ticker": "SB", "unit": 112000, "unit_desc": "lbs", "quote": "USD cents/lb", "tick": 0.01, "tick_val": 11.2, "months": "H,K,N,V", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_US"},
    {"name_en": "Cocoa", "ticker": "CC", "unit": 10, "unit_desc": "metric tonnes", "quote": "USD/tonne", "tick": 1, "tick_val": 10, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_US"},
    {"name_en": "Orange Juice", "ticker": "OJ", "unit": 15000, "unit_desc": "lbs", "quote": "USD cents/lb", "tick": 0.05, "tick_val": 7.5, "months": "F,H,K,N,U,X", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_US"},
    {"name_en": "MSCI Emerging Markets", "ticker": "MME", "unit": 50, "unit_desc": "index", "quote": "USD/point", "tick": 0.1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "exchange": "ICE_US"},
    {"name_en": "US Dollar Index", "ticker": "DX", "unit": 1000, "unit_desc": "index", "quote": "USD", "tick": 0.005, "tick_val": 5, "months": "H,M,U,Z", "group": "FX", "delivery": "cash", "exchange": "ICE_US"},
    {"name_en": "Russell 2000 Mini", "ticker": "QR", "unit": 50, "unit_desc": "index", "quote": "USD/point", "tick": 0.1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "exchange": "ICE_US"},
]

ICE_EU_PRODUCTS = [
    {"name_en": "Brent Crude Oil", "ticker": "B", "unit": 1000, "unit_desc": "barrels", "quote": "USD/barrel", "tick": 0.01, "tick_val": 10, "months": "1-12 (monthly, 6+ years)", "group": "Energy", "delivery": "cash", "exchange": "ICE_EU"},
    {"name_en": "WTI Crude Oil (ICE)", "ticker": "T", "unit": 1000, "unit_desc": "barrels", "quote": "USD/barrel", "tick": 0.01, "tick_val": 10, "months": "1-12", "group": "Energy", "delivery": "cash", "exchange": "ICE_EU"},
    {"name_en": "Low Sulphur Gasoil", "ticker": "G", "unit": 100, "unit_desc": "metric tonnes", "quote": "USD/tonne", "tick": 0.25, "tick_val": 25, "months": "1-12", "group": "Energy", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "UK Natural Gas (NBP)", "ticker": "M", "unit": 1000, "unit_desc": "therms/day", "quote": "pence/therm", "tick": 0.01, "tick_val": 10, "months": "1-12", "group": "Energy", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "Dutch TTF Gas", "ticker": "TFM", "unit": 1, "unit_desc": "MW/day", "quote": "EUR/MWh", "tick": 0.001, "tick_val": 0.001, "months": "1-12", "group": "Energy", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "EUA Futures (Carbon)", "ticker": "ECF", "unit": 1000, "unit_desc": "EUA allowances", "quote": "EUR/tonne CO2", "tick": 0.01, "tick_val": 10, "months": "H,M,U,Z", "group": "Emissions", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "Robusta Coffee", "ticker": "RC", "unit": 10, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 1, "tick_val": 10, "months": "F,H,K,N,U,X", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "White Sugar", "ticker": "SW", "unit": 50, "unit_desc": "tonnes", "quote": "USD/tonne", "tick": 0.1, "tick_val": 5, "months": "H,K,Q,V,Z", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "London Cocoa", "ticker": "C", "unit": 10, "unit_desc": "tonnes", "quote": "GBP/tonne", "tick": 1, "tick_val": 10, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical", "exchange": "ICE_EU"},
    {"name_en": "FTSE 100 Index Futures", "ticker": "Z", "unit": 10, "unit_desc": "index", "quote": "GBP/point", "tick": 0.5, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash", "exchange": "ICE_EU"},
]


class ICECollector(BaseCollector):
    exchange_code = "ICE"
    exchange_name_en = "Intercontinental Exchange"
    exchange_name_cn = "洲际交易所"
    rate_limit = 2.0

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in ICE_US_PRODUCTS + ICE_EU_PRODUCTS:
            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL
            exch = prod["exchange"]
            ccy = "GBP" if "GBP" in prod["quote"] else "EUR" if "EUR" in prod["quote"] else "USD"

            spec = ContractSpec(
                exchange_code=exch,
                exchange_sub=exch,
                exchange_name_en="ICE Futures US" if exch == "ICE_US" else "ICE Futures Europe",
                exchange_name_cn="洲际交易所(美国)" if exch == "ICE_US" else "洲际交易所(欧洲)",
                product_name_en=prod["name_en"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                contract_size=f"{prod['unit']:,} {prod['unit_desc']}",
                contract_size_numeric=Decimal(str(prod["unit"])),
                contract_unit=prod["unit_desc"],
                quote_unit=prod["quote"],
                quote_currency=ccy,
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])),
                tick_value_currency=ccy,
                contract_months=prod["months"],
                trading_hours_electronic="20:00-18:00 ET (ICE US) / 01:00-19:00 London (ICE EU)",
                delivery_method=dm,
                source_url=f"https://www.theice.com/products/",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)
        return results
