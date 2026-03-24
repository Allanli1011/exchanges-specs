"""CME Group collector — covers CME, CBOT, NYMEX, COMEX.
Uses static product catalog as base, enriched via API when accessible."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Optional
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)

EXCHANGE_INFO = {
    "CME": ("CME", "Chicago Mercantile Exchange", "芝加哥商业交易所"),
    "CBOT": ("CBOT", "Chicago Board of Trade", "芝加哥期货交易所"),
    "NYMEX": ("NYMEX", "New York Mercantile Exchange", "纽约商业交易所"),
    "COMEX": ("COMEX", "Commodity Exchange", "纽约商品交易所"),
}

# Comprehensive CME Group product catalog
CME_PRODUCTS = [
    # === CBOT Grains & Oilseeds ===
    {"exch": "CBOT", "name": "Soybean Futures", "ticker": "ZS", "globex": "ZS", "size": "5,000 bushels", "size_num": 5000, "unit": "bushels", "quote": "USD cents/bushel", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "F,H,K,N,Q,U,X", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "price_limit": "Variable, $0.70-$1.60/bu expanded", "pos_limit": "27,300 (spot)"},
    {"exch": "CBOT", "name": "Corn Futures", "ticker": "ZC", "globex": "ZC", "size": "5,000 bushels", "size_num": 5000, "unit": "bushels", "quote": "USD cents/bushel", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "price_limit": "Variable, $0.25-$0.40/bu expanded", "pos_limit": "57,800 (spot)"},
    {"exch": "CBOT", "name": "Chicago SRW Wheat Futures", "ticker": "ZW", "globex": "ZW", "size": "5,000 bushels", "size_num": 5000, "unit": "bushels", "quote": "USD cents/bushel", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "price_limit": "Variable", "pos_limit": "19,300 (spot)"},
    {"exch": "CBOT", "name": "Soybean Meal Futures", "ticker": "ZM", "globex": "ZM", "size": "100 short tons", "size_num": 100, "unit": "short tons", "quote": "USD/short ton", "ccy": "USD", "tick": 0.1, "tick_val": 10, "months": "F,H,K,N,Q,U,V,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "pos_limit": "16,900 (spot)"},
    {"exch": "CBOT", "name": "Soybean Oil Futures", "ticker": "ZL", "globex": "ZL", "size": "60,000 lbs", "size_num": 60000, "unit": "lbs", "quote": "USD cents/lb", "ccy": "USD", "tick": 0.01, "tick_val": 6, "months": "F,H,K,N,Q,U,V,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "pos_limit": "17,400 (spot)"},
    {"exch": "CBOT", "name": "Oats Futures", "ticker": "ZO", "globex": "ZO", "size": "5,000 bushels", "size_num": 5000, "unit": "bushels", "quote": "USD cents/bushel", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical",
     "pos_limit": "2,000 (spot)"},
    {"exch": "CBOT", "name": "KC HRW Wheat Futures", "ticker": "KE", "globex": "KE", "size": "5,000 bushels", "size_num": 5000, "unit": "bushels", "quote": "USD cents/bushel", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "H,K,N,U,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks"},
    {"exch": "CBOT", "name": "Rough Rice Futures", "ticker": "ZR", "globex": "ZR", "size": "2,000 hundredweight", "size_num": 2000, "unit": "cwt", "quote": "USD cents/cwt", "ccy": "USD", "tick": 0.5, "tick_val": 10, "months": "F,H,K,N,U,X", "group": "Agriculture", "delivery": "physical"},

    # === CBOT Treasury ===
    {"exch": "CBOT", "name": "2-Year T-Note Futures", "ticker": "ZT", "globex": "ZT", "size": "$200,000 face value", "size_num": 200000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.0078125, "tick_val": 15.625, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},
    {"exch": "CBOT", "name": "5-Year T-Note Futures", "ticker": "ZF", "globex": "ZF", "size": "$100,000 face value", "size_num": 100000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.0078125, "tick_val": 7.8125, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},
    {"exch": "CBOT", "name": "10-Year T-Note Futures", "ticker": "ZN", "globex": "ZN", "size": "$100,000 face value", "size_num": 100000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.015625, "tick_val": 15.625, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},
    {"exch": "CBOT", "name": "U.S. Treasury Bond Futures", "ticker": "ZB", "globex": "ZB", "size": "$100,000 face value", "size_num": 100000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.03125, "tick_val": 31.25, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},
    {"exch": "CBOT", "name": "Ultra 10-Year T-Note Futures", "ticker": "TN", "globex": "TN", "size": "$100,000 face value", "size_num": 100000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.015625, "tick_val": 15.625, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},
    {"exch": "CBOT", "name": "Ultra T-Bond Futures", "ticker": "UB", "globex": "UB", "size": "$100,000 face value", "size_num": 100000, "unit": "USD", "quote": "points and fractions of 32nds", "ccy": "USD", "tick": 0.03125, "tick_val": 31.25, "months": "H,M,U,Z", "group": "Interest Rate", "delivery": "physical",
     "tas": True, "tas_range": "+/- 2 ticks"},

    # === CME Equity Index ===
    {"exch": "CME", "name": "E-mini S&P 500 Futures", "ticker": "ES", "globex": "ES", "size": "$50 x S&P 500 Index", "size_num": 50, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks", "price_limit": "7%, 13%, 20% circuit breakers"},
    {"exch": "CME", "name": "Micro E-mini S&P 500 Futures", "ticker": "MES", "globex": "MES", "size": "$5 x S&P 500 Index", "size_num": 5, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 0.25, "tick_val": 1.25, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash"},
    {"exch": "CME", "name": "E-mini NASDAQ-100 Futures", "ticker": "NQ", "globex": "NQ", "size": "$20 x NASDAQ-100 Index", "size_num": 20, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 0.25, "tick_val": 5, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks", "price_limit": "7%, 13%, 20% circuit breakers"},
    {"exch": "CME", "name": "Micro E-mini NASDAQ-100 Futures", "ticker": "MNQ", "globex": "MNQ", "size": "$2 x NASDAQ-100 Index", "size_num": 2, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 0.25, "tick_val": 0.5, "months": "H,M,U,Z + 3 serial", "group": "Equity Index", "delivery": "cash"},
    {"exch": "CME", "name": "E-mini Dow ($5) Futures", "ticker": "YM", "globex": "YM", "size": "$5 x DJIA", "size_num": 5, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "CME", "name": "Micro E-mini Dow Futures", "ticker": "MYM", "globex": "MYM", "size": "$0.50 x DJIA", "size_num": 0.5, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 1, "tick_val": 0.5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},
    {"exch": "CME", "name": "E-mini Russell 2000 Futures", "ticker": "RTY", "globex": "RTY", "size": "$50 x Russell 2000 Index", "size_num": 50, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 0.1, "tick_val": 5, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "CME", "name": "Nikkei/USD Futures", "ticker": "NKD", "globex": "NKD", "size": "$5 x Nikkei 225", "size_num": 5, "unit": "index points", "quote": "USD/index point", "ccy": "USD", "tick": 5, "tick_val": 25, "months": "H,M,U,Z", "group": "Equity Index", "delivery": "cash"},

    # === CME FX ===
    {"exch": "CME", "name": "Euro FX Futures", "ticker": "6E", "globex": "6E", "size": "125,000 euros", "size_num": 125000, "unit": "EUR", "quote": "USD/EUR", "ccy": "USD", "tick": 0.00005, "tick_val": 6.25, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "Japanese Yen Futures", "ticker": "6J", "globex": "6J", "size": "12,500,000 yen", "size_num": 12500000, "unit": "JPY", "quote": "USD/JPY (inverse)", "ccy": "USD", "tick": 0.0000005, "tick_val": 6.25, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "British Pound Futures", "ticker": "6B", "globex": "6B", "size": "62,500 pounds", "size_num": 62500, "unit": "GBP", "quote": "USD/GBP", "ccy": "USD", "tick": 0.0001, "tick_val": 6.25, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "Australian Dollar Futures", "ticker": "6A", "globex": "6A", "size": "100,000 AUD", "size_num": 100000, "unit": "AUD", "quote": "USD/AUD", "ccy": "USD", "tick": 0.0001, "tick_val": 10, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "Canadian Dollar Futures", "ticker": "6C", "globex": "6C", "size": "100,000 CAD", "size_num": 100000, "unit": "CAD", "quote": "USD/CAD", "ccy": "USD", "tick": 0.00005, "tick_val": 5, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "Swiss Franc Futures", "ticker": "6S", "globex": "6S", "size": "125,000 CHF", "size_num": 125000, "unit": "CHF", "quote": "USD/CHF", "ccy": "USD", "tick": 0.0001, "tick_val": 12.5, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},
    {"exch": "CME", "name": "Mexican Peso Futures", "ticker": "6M", "globex": "6M", "size": "500,000 MXN", "size_num": 500000, "unit": "MXN", "quote": "USD/MXN", "ccy": "USD", "tick": 0.00001, "tick_val": 5, "months": "H,M,U,Z + 2 serial", "group": "FX", "delivery": "physical"},

    # === CME Livestock ===
    {"exch": "CME", "name": "Live Cattle Futures", "ticker": "LE", "globex": "LE", "size": "40,000 lbs", "size_num": 40000, "unit": "lbs", "quote": "USD cents/lb", "ccy": "USD", "tick": 0.025, "tick_val": 10, "months": "G,J,M,Q,V,Z", "group": "Agriculture", "delivery": "physical",
     "tas": True, "tas_range": "+/- 4 ticks", "pos_limit": "6,300 (spot)"},
    {"exch": "CME", "name": "Feeder Cattle Futures", "ticker": "GF", "globex": "GF", "size": "50,000 lbs", "size_num": 50000, "unit": "lbs", "quote": "USD cents/lb", "ccy": "USD", "tick": 0.025, "tick_val": 12.5, "months": "F,H,J,K,Q,U,V,X", "group": "Agriculture", "delivery": "cash",
     "tas": True, "tas_range": "+/- 4 ticks", "pos_limit": "1,950 (spot)"},
    {"exch": "CME", "name": "Lean Hog Futures", "ticker": "HE", "globex": "HE", "size": "40,000 lbs", "size_num": 40000, "unit": "lbs", "quote": "USD cents/lb", "ccy": "USD", "tick": 0.025, "tick_val": 10, "months": "G,J,K,M,N,Q,V,Z", "group": "Agriculture", "delivery": "cash",
     "tas": True, "tas_range": "+/- 4 ticks", "pos_limit": "6,000 (spot)"},

    # === NYMEX Energy ===
    {"exch": "NYMEX", "name": "WTI Crude Oil Futures", "ticker": "CL", "globex": "CL", "size": "1,000 barrels", "size_num": 1000, "unit": "barrels", "quote": "USD/barrel", "ccy": "USD", "tick": 0.01, "tick_val": 10, "months": "1-12 (monthly, 9+ years)", "group": "Energy", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks", "price_limit": "Variable, $5-$15/bbl expanded"},
    {"exch": "NYMEX", "name": "Henry Hub Natural Gas Futures", "ticker": "NG", "globex": "NG", "size": "10,000 MMBtu", "size_num": 10000, "unit": "MMBtu", "quote": "USD/MMBtu", "ccy": "USD", "tick": 0.001, "tick_val": 10, "months": "1-12 (monthly, 12+ years)", "group": "Energy", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "NYMEX", "name": "RBOB Gasoline Futures", "ticker": "RB", "globex": "RB", "size": "42,000 gallons", "size_num": 42000, "unit": "gallons", "quote": "USD/gallon", "ccy": "USD", "tick": 0.0001, "tick_val": 4.2, "months": "1-12", "group": "Energy", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "NYMEX", "name": "NY Harbor ULSD Futures", "ticker": "HO", "globex": "HO", "size": "42,000 gallons", "size_num": 42000, "unit": "gallons", "quote": "USD/gallon", "ccy": "USD", "tick": 0.0001, "tick_val": 4.2, "months": "1-12", "group": "Energy", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "NYMEX", "name": "Micro WTI Crude Oil Futures", "ticker": "MCL", "globex": "MCL", "size": "100 barrels", "size_num": 100, "unit": "barrels", "quote": "USD/barrel", "ccy": "USD", "tick": 0.01, "tick_val": 1, "months": "1-12", "group": "Energy", "delivery": "cash"},
    {"exch": "NYMEX", "name": "E-mini Natural Gas Futures", "ticker": "QG", "globex": "QG", "size": "2,500 MMBtu", "size_num": 2500, "unit": "MMBtu", "quote": "USD/MMBtu", "ccy": "USD", "tick": 0.005, "tick_val": 12.5, "months": "1-12", "group": "Energy", "delivery": "cash"},
    {"exch": "NYMEX", "name": "Platinum Futures", "ticker": "PL", "globex": "PL", "size": "50 troy oz", "size_num": 50, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.1, "tick_val": 5, "months": "F,J,N,V", "group": "Metals", "delivery": "physical"},
    {"exch": "NYMEX", "name": "Palladium Futures", "ticker": "PA", "globex": "PA", "size": "100 troy oz", "size_num": 100, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.05, "tick_val": 5, "months": "H,M,U,Z", "group": "Metals", "delivery": "physical"},

    # === COMEX Metals ===
    {"exch": "COMEX", "name": "Gold Futures", "ticker": "GC", "globex": "GC", "size": "100 troy oz", "size_num": 100, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.1, "tick_val": 10, "months": "G,J,M,Q,V,Z + serial", "group": "Metals", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "COMEX", "name": "Micro Gold Futures", "ticker": "MGC", "globex": "MGC", "size": "10 troy oz", "size_num": 10, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.1, "tick_val": 1, "months": "G,J,M,Q,V,Z", "group": "Metals", "delivery": "physical"},
    {"exch": "COMEX", "name": "Silver Futures", "ticker": "SI", "globex": "SI", "size": "5,000 troy oz", "size_num": 5000, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.005, "tick_val": 25, "months": "H,K,N,U,Z + serial", "group": "Metals", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "COMEX", "name": "Micro Silver Futures", "ticker": "SIL", "globex": "SIL", "size": "1,000 troy oz", "size_num": 1000, "unit": "troy oz", "quote": "USD/troy oz", "ccy": "USD", "tick": 0.005, "tick_val": 5, "months": "H,K,N,U,Z", "group": "Metals", "delivery": "physical"},
    {"exch": "COMEX", "name": "Copper Futures", "ticker": "HG", "globex": "HG", "size": "25,000 lbs", "size_num": 25000, "unit": "lbs", "quote": "USD cents/lb", "ccy": "USD", "tick": 0.0005, "tick_val": 12.5, "months": "H,K,N,U,Z + serial", "group": "Metals", "delivery": "physical",
     "tas": True, "tas_range": "+/- 0 ticks"},

    # === CME Interest Rate ===
    {"exch": "CME", "name": "3-Month SOFR Futures", "ticker": "SR3", "globex": "SR3", "size": "$2,500 per index point", "size_num": 2500, "unit": "USD", "quote": "100 minus rate", "ccy": "USD", "tick": 0.0025, "tick_val": 6.25, "months": "H,M,U,Z + 5 serial (out to 10 years)", "group": "Interest Rate", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks"},
    {"exch": "CME", "name": "1-Month SOFR Futures", "ticker": "SR1", "globex": "SR1", "size": "$4,167 per index point", "size_num": 4167, "unit": "USD", "quote": "100 minus rate", "ccy": "USD", "tick": 0.005, "tick_val": 20.835, "months": "6 serial", "group": "Interest Rate", "delivery": "cash"},
    {"exch": "CME", "name": "Eurodollar Futures", "ticker": "GE", "globex": "GE", "size": "$2,500 per index point", "size_num": 2500, "unit": "USD", "quote": "100 minus rate", "ccy": "USD", "tick": 0.005, "tick_val": 12.5, "months": "H,M,U,Z + 4 serial", "group": "Interest Rate", "delivery": "cash",
     "tas": True, "tas_range": "+/- 0 ticks"},

    # === CME Cryptocurrency ===
    {"exch": "CME", "name": "Bitcoin Futures", "ticker": "BTC", "globex": "BTC", "size": "5 bitcoin", "size_num": 5, "unit": "BTC", "quote": "USD/bitcoin", "ccy": "USD", "tick": 5, "tick_val": 25, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Micro Bitcoin Futures", "ticker": "MBT", "globex": "MBT", "size": "0.1 bitcoin", "size_num": 0.1, "unit": "BTC", "quote": "USD/bitcoin", "ccy": "USD", "tick": 5, "tick_val": 0.5, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Ether Futures", "ticker": "ETH", "globex": "ETH", "size": "50 ether", "size_num": 50, "unit": "ETH", "quote": "USD/ether", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Micro Ether Futures", "ticker": "MET", "globex": "MET", "size": "0.1 ether", "size_num": 0.1, "unit": "ETH", "quote": "USD/ether", "ccy": "USD", "tick": 0.05, "tick_val": 0.005, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
]


class CMEGroupCollector(BaseCollector):
    exchange_code = "CME"
    exchange_name_en = "CME Group"
    exchange_name_cn = "芝加哥商业交易所集团"
    rate_limit = 2.0
    base_url = "https://www.cmegroup.com"

    def __init__(self, http_client: HttpClient):
        super().__init__(http_client)

    async def collect_all(self) -> List[ContractSpec]:
        results = []
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in CME_PRODUCTS:
            exch_code = prod["exch"]
            info = EXCHANGE_INFO.get(exch_code, ("CME", "CME Group", "CME集团"))
            sub, name_en, name_cn = info

            dm = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL

            spec = ContractSpec(
                exchange_code="CME",
                exchange_sub=sub,
                exchange_name_en=name_en,
                exchange_name_cn=name_cn,
                product_name_en=prod["name"],
                product_group=prod["group"],
                ticker=prod["ticker"],
                bloomberg_code=None,
                contract_size=prod["size"],
                contract_size_numeric=Decimal(str(prod["size_num"])),
                contract_unit=prod["unit"],
                quote_unit=prod["quote"],
                quote_currency=prod["ccy"],
                tick_size=str(prod["tick"]),
                tick_size_numeric=Decimal(str(prod["tick"])),
                tick_value=Decimal(str(prod["tick_val"])),
                tick_value_currency=prod["ccy"],
                contract_months=prod["months"],
                trading_hours_electronic="17:00-16:00 CT (Sun-Fri)",
                trading_hours_notes="Central Time (CT, UTC-6/-5). CME Globex.",
                delivery_method=dm,
                # TAS
                tas_eligible=prod.get("tas", None),
                tas_tick_range=prod.get("tas_range"),
                # Risk
                price_limit_daily=prod.get("price_limit"),
                position_limit_spot=prod.get("pos_limit"),
                # Metadata
                source_url=f"https://www.cmegroup.com/markets/{prod['group'].lower().replace(' ', '-')}/{prod['name'].lower().replace(' ', '-').replace('/', '-')}.contractSpecs.html",
                source_type="static",
                last_updated=now_str,
                data_quality="complete",
            )
            results.append(spec)

        logger.info(f"CME Group: {len(results)} products from static catalog")
        return results
