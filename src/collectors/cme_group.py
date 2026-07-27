"""CME Group collector — covers CME, CBOT, NYMEX, COMEX.
Uses static product catalog as base, enriched via API when accessible."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import unescape
import re
from typing import Any, List, Optional
import logging

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)

CME_PRODUCTS_PAGE_URL = "https://www.cmegroup.com/markets/products.html"
CME_ACTIVE_PRODUCTS_URL = "https://www.cmegroup.com/CmeWS/md/Product/V2/ActiveProducts"
CME_CONTRACT_SPECS_URL = "https://www.cmegroup.com/CmeWS/mvc/ContractSpecs/List/productId/{product_id}"
CME_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}
CME_API_HEADERS = {
    **CME_BROWSER_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cmegroup.com",
    "Referer": CME_PRODUCTS_PAGE_URL,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}
GENERIC_PRICE_LIMIT_LABELS = {
    "price limits",
    "price limit guide",
}
GENERIC_POSITION_LIMIT_LABELS = {
    "position limits",
    "cme position limits",
    "cbot position limits",
    "nymex position limits",
    "comex position limits",
}

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
    # === CME Cryptocurrency ===
    {"exch": "CME", "name": "Bitcoin Futures", "ticker": "BTC", "globex": "BTC", "size": "5 bitcoin", "size_num": 5, "unit": "BTC", "quote": "USD/bitcoin", "ccy": "USD", "tick": 5, "tick_val": 25, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Micro Bitcoin Futures", "ticker": "MBT", "globex": "MBT", "size": "0.1 bitcoin", "size_num": 0.1, "unit": "BTC", "quote": "USD/bitcoin", "ccy": "USD", "tick": 5, "tick_val": 0.5, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Ether Futures", "ticker": "ETH", "globex": "ETH", "size": "50 ether", "size_num": 50, "unit": "ETH", "quote": "USD/ether", "ccy": "USD", "tick": 0.25, "tick_val": 12.5, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
    {"exch": "CME", "name": "Micro Ether Futures", "ticker": "MET", "globex": "MET", "size": "0.1 ether", "size_num": 0.1, "unit": "ETH", "quote": "USD/ether", "ccy": "USD", "tick": 0.05, "tick_val": 0.005, "months": "6 serial + 2 quarterly", "group": "Cryptocurrency", "delivery": "cash"},
]


def clean_cme_spec_text(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None

    text = str(value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"(?i)<li\s*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip() or None


def _decimal_or_none(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _pick_preferred_entry(entries: list[dict], label_key: str, preferred_labels: list[str]) -> Optional[dict]:
    if not entries:
        return None

    for preferred in preferred_labels:
        for entry in entries:
            label = (clean_cme_spec_text(entry.get(label_key)) or "").lower()
            if label.startswith(preferred.lower()):
                return entry
    return entries[0]


def parse_cme_minimum_price_fluctuation(value: Any) -> tuple[Optional[str], Optional[Decimal], Optional[Decimal], Optional[str]]:
    if isinstance(value, dict) and isinstance(value.get("ticks"), list):
        entries = value["ticks"]
        selected = _pick_preferred_entry(entries, "type", ["CME Globex:", "Default:"])
        selected_text = clean_cme_spec_text((selected or {}).get("mintk"))

        tick_size_numeric = None
        tick_value = None
        if selected_text:
            numeric_match = re.search(r"(?<!\$)(\d+(?:,\d{3})*(?:\.\d+)?)", selected_text)
            currency_match = re.search(r"=\s*\$([0-9][0-9,]*(?:\.\d+)?)", selected_text)
            if numeric_match:
                tick_size_numeric = _decimal_or_none(numeric_match.group(1))
            if currency_match:
                tick_value = _decimal_or_none(currency_match.group(1))

        alternate_entries = []
        for entry in entries:
            if entry is selected:
                continue
            venue = clean_cme_spec_text(entry.get("type"))
            tick_text = clean_cme_spec_text(entry.get("mintk"))
            if venue and tick_text:
                alternate_entries.append(f"{venue} {tick_text}")
        alternate_note = " | ".join(alternate_entries) or None
        return selected_text, tick_size_numeric, tick_value, alternate_note

    text = clean_cme_spec_text(value)
    return text, None, None, None


def parse_cme_trading_hours(value: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not isinstance(value, dict) or not isinstance(value.get("vandhr"), list):
        return None, None, "Central Time (CT, UTC-6/-5)."

    entries = value["vandhr"]
    globex = _pick_preferred_entry(entries, "venue", ["CME Globex:"])
    regular = _pick_preferred_entry(entries, "venue", ["Open Outcry:", "Floor:"])

    electronic_hours = clean_cme_spec_text((globex or {}).get("hours"))
    regular_hours = clean_cme_spec_text((regular or {}).get("hours"))

    note_parts = ["Central Time (CT, UTC-6/-5)."]
    for entry in entries:
        venue = clean_cme_spec_text(entry.get("venue"))
        hours = clean_cme_spec_text(entry.get("hours"))
        if not venue or not hours:
            continue
        if entry is globex or entry is regular:
            continue
        note_parts.append(f"{venue} {hours}")

    return electronic_hours, regular_hours, " ".join(note_parts)


def _stringify_cme_named_entries(value: Any, container_key: str, text_key: str, label_key: str) -> Optional[str]:
    if not isinstance(value, dict) or not isinstance(value.get(container_key), list):
        return clean_cme_spec_text(value)

    parts: list[str] = []
    for entry in value[container_key]:
        label = clean_cme_spec_text(entry.get(label_key))
        text = clean_cme_spec_text(entry.get(text_key))
        if not text:
            continue
        if label and label.lower() != "default:":
            parts.append(f"{label} {text}")
        else:
            parts.append(text)
    return " | ".join(parts) or None


def _stringify_cme_product_codes(value: Any) -> tuple[Optional[str], dict[str, str]]:
    if not isinstance(value, dict):
        return clean_cme_spec_text(value), {}

    code_map = {
        str(key): clean_cme_spec_text(code)
        for key, code in value.items()
        if clean_cme_spec_text(code)
    }
    ordered_keys = [
        "CmeGlobex",
        "ClearPort",
        "OpenOutCry",
        "ClearingCode",
        "TAS",
        "TAM",
        "BTIC",
        "TACO",
        "TMAC",
        "tickerCall",
        "tickerPut",
    ]
    parts = [f"{key}: {code_map[key]}" for key in ordered_keys if key in code_map]
    for key, code in code_map.items():
        if key not in ordered_keys:
            parts.append(f"{key}: {code}")
    return "; ".join(parts) or None, code_map


def _derive_cme_delivery_method(settlement_method: Optional[str], static_delivery: str) -> DeliveryMethod:
    settlement = (settlement_method or "").lower()
    if "financial" in settlement or "cash" in settlement:
        return DeliveryMethod.CASH
    if "deliverable" in settlement or "physical" in settlement:
        return DeliveryMethod.PHYSICAL
    return DeliveryMethod.CASH if static_delivery == "cash" else DeliveryMethod.PHYSICAL


def _extract_cme_tas_tick_range(*texts: Optional[str]) -> Optional[str]:
    for text in texts:
        if not text:
            continue
        match = re.search(r"TAS:\s*(Zero or \+/-\s*\d+\s*ticks?)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"TAS:\s*(\+/-\s*\d+\s*ticks?)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _prefer_static_if_generic(static_value: Optional[str], official_value: Optional[str], generic_labels: set[str]) -> Optional[str]:
    if official_value and official_value.strip().lower() not in generic_labels:
        return official_value
    return static_value or official_value


def _build_static_cme_spec(prod: dict, now_str: str, note_prefix: Optional[str] = None) -> ContractSpec:
    exch_code = prod["exch"]
    sub, name_en, name_cn = EXCHANGE_INFO.get(exch_code, ("CME", "CME Group", "CME Group"))
    delivery_method = DeliveryMethod.CASH if prod["delivery"] == "cash" else DeliveryMethod.PHYSICAL

    notes = "Static CME fallback metadata."
    if note_prefix:
        notes = f"{note_prefix} {notes}".strip()

    return ContractSpec(
        exchange_code="CME",
        exchange_sub=sub,
        exchange_name_en=name_en,
        exchange_name_cn=name_cn,
        product_name_en=prod["name"],
        product_group=prod["group"],
        ticker=prod["ticker"],
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
        trading_hours_notes="Central Time (CT, UTC-6/-5). Static fallback metadata.",
        delivery_method=delivery_method,
        tas_eligible=prod.get("tas"),
        tas_tick_range=prod.get("tas_range"),
        price_limit_daily=prod.get("price_limit"),
        position_limit_spot=prod.get("pos_limit"),
        source_url=CME_PRODUCTS_PAGE_URL,
        source_type="static",
        last_updated=now_str,
        notes=notes,
    )


class CMEGroupCollector(BaseCollector):
    exchange_code = "CME"
    exchange_name_en = "CME Group"
    exchange_name_cn = "芝加哥商业交易所集团"
    rate_limit = 2.0
    base_url = "https://www.cmegroup.com"

    def __init__(self, http_client: HttpClient, exchange_key: Optional[str] = None):
        super().__init__(http_client, exchange_key=exchange_key)
        self._cme_session_ready = False

    async def collect_all(self) -> List[ContractSpec]:
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            active_lookup = await self._fetch_active_products()
        except Exception as exc:
            logger.warning(f"CME Group API unavailable, using static fallback: {exc}")
            return [
                _build_static_cme_spec(
                    prod,
                    now_str,
                    note_prefix=f"Official CME APIs were unavailable during this run: {exc}.",
                )
                for prod in CME_PRODUCTS
            ]

        results: list[ContractSpec] = []
        for prod in CME_PRODUCTS:
            try:
                results.append(await self._build_enriched_spec(prod, active_lookup, now_str))
            except Exception as exc:
                logger.warning(f"CME fallback for {prod['ticker']} due to API error: {exc}")
                results.append(
                    _build_static_cme_spec(
                        prod,
                        now_str,
                        note_prefix=f"Official CME contract specs API unavailable for {prod['ticker']}: {exc}.",
                    )
                )

        logger.info(f"CME Group: {len(results)} curated futures enriched from official APIs")
        return results

    async def _prime_cme_session(self):
        if self._cme_session_ready:
            return

        await self.client.get(
            CME_PRODUCTS_PAGE_URL,
            headers=CME_BROWSER_HEADERS,
            rate_limit=self.rate_limit,
            use_cache=False,
        )
        self._cme_session_ready = True

    async def _get_cme_json(self, url: str) -> dict:
        await self._prime_cme_session()
        try:
            return await self.client.get_json(
                url,
                headers=CME_API_HEADERS,
                rate_limit=self.rate_limit,
            )
        except Exception:
            self._cme_session_ready = False
            await self._prime_cme_session()
            return await self.client.get_json(
                url,
                headers=CME_API_HEADERS,
                rate_limit=self.rate_limit,
            )

    async def _fetch_active_products(self) -> dict[str, dict]:
        payload = await self._get_cme_json(CME_ACTIVE_PRODUCTS_URL)
        rows = payload.get("p", [])
        return {
            row["productCode"]: row
            for row in rows
            if isinstance(row, dict) and row.get("productCode")
        }

    async def _fetch_contract_specs(self, product_id: str) -> dict:
        return await self._get_cme_json(CME_CONTRACT_SPECS_URL.format(product_id=product_id))

    async def _build_enriched_spec(self, prod: dict, active_lookup: dict[str, dict], now_str: str) -> ContractSpec:
        active_product = active_lookup.get(prod["ticker"])
        if not active_product:
            raise RuntimeError(f"No active CME product match for ticker {prod['ticker']}")

        spec_payload = await self._fetch_contract_specs(active_product["productId"])
        exch_code = prod["exch"]
        sub, name_en, name_cn = EXCHANGE_INFO.get(exch_code, ("CME", "CME Group", "CME Group"))

        official_product_name = (
            clean_cme_spec_text(spec_payload.get("ProductName"))
            or active_product.get("name")
            or prod["name"]
        )
        minimum_price_text, tick_size_numeric, tick_value, tick_note = parse_cme_minimum_price_fluctuation(
            spec_payload.get("MinimumPriceFluctuation")
        )
        trading_hours_electronic, trading_hours_regular, trading_hours_notes = parse_cme_trading_hours(
            spec_payload.get("TradingHours")
        )
        listed_contracts = _stringify_cme_named_entries(
            spec_payload.get("ListedContracts"),
            "contractMonthsList",
            "contrMonth",
            "type",
        )
        last_trading_day = _stringify_cme_named_entries(
            spec_payload.get("TerminationOfTrading"),
            "terminationOfTrading",
            "termsOfTrading",
            "type",
        )
        _, product_codes = _stringify_cme_product_codes(spec_payload.get("ProductCode"))
        settlement_method = clean_cme_spec_text(spec_payload.get("SettlementMethod"))
        delivery_method = _derive_cme_delivery_method(settlement_method, prod["delivery"])
        trade_rules = clean_cme_spec_text(spec_payload.get("TradeAtMarkerOrTradeAtSettlementRules"))

        tas_eligible = bool(prod.get("tas")) or "TAS" in product_codes or (
            trade_rules and "trading at settlement" in trade_rules.lower()
        )
        tam_eligible = "TAM" in product_codes or "TMAC" in product_codes or "TACO" in product_codes or (
            trade_rules and "trading at marker" in trade_rules.lower()
        )
        btic_eligible = "BTIC" in product_codes or (
            trade_rules and "btic" in trade_rules.lower()
        )

        price_limit_daily = _prefer_static_if_generic(
            prod.get("price_limit"),
            clean_cme_spec_text(spec_payload.get("PriceLimitOrCircuit")),
            GENERIC_PRICE_LIMIT_LABELS,
        )
        position_limit_spot = _prefer_static_if_generic(
            prod.get("pos_limit"),
            clean_cme_spec_text(spec_payload.get("PositionLimits")),
            GENERIC_POSITION_LIMIT_LABELS,
        )

        source_page = active_product.get("uri2") or active_product.get("uri")
        source_url = f"{self.base_url}{source_page}" if source_page else CME_PRODUCTS_PAGE_URL

        notes = [f"Contract specs sourced from official CME API for productId {active_product['productId']}."]
        if tick_note:
            notes.append(f"Alternate venue tick increments: {tick_note}")

        return ContractSpec(
            exchange_code="CME",
            exchange_sub=sub,
            exchange_name_en=name_en,
            exchange_name_cn=name_cn,
            product_name_en=official_product_name,
            product_group=prod["group"],
            ticker=prod["ticker"],
            contract_size=clean_cme_spec_text(spec_payload.get("ContractUnit")) or prod["size"],
            contract_size_numeric=Decimal(str(prod["size_num"])),
            contract_unit=prod["unit"],
            quote_unit=clean_cme_spec_text(spec_payload.get("PriceQuotation")) or prod["quote"],
            quote_currency=prod["ccy"],
            tick_size=minimum_price_text or str(prod["tick"]),
            tick_size_numeric=tick_size_numeric or Decimal(str(prod["tick"])),
            tick_value=tick_value or Decimal(str(prod["tick_val"])),
            tick_value_currency=prod["ccy"],
            contract_months=prod["months"],
            listed_contracts=listed_contracts,
            trading_hours_regular=trading_hours_regular,
            trading_hours_electronic=trading_hours_electronic or "17:00-16:00 CT (Sun-Fri)",
            trading_hours_notes=trading_hours_notes,
            settlement_method=settlement_method,
            tas_eligible=tas_eligible,
            tas_tick_range=prod.get("tas_range") or _extract_cme_tas_tick_range(trade_rules, minimum_price_text),
            tam_eligible=tam_eligible,
            tam_rules=trade_rules if tam_eligible else None,
            btic_eligible=btic_eligible,
            btic_rules=trade_rules if btic_eligible else None,
            block_trade_minimum=clean_cme_spec_text(spec_payload.get("BlockMinimum")),
            price_limit_daily=price_limit_daily,
            price_limit_type=(
                "circuit_breaker"
                if price_limit_daily and "circuit" in price_limit_daily.lower()
                else "variable" if price_limit_daily else None
            ),
            position_limit_spot=position_limit_spot,
            position_limit_notes=clean_cme_spec_text(spec_payload.get("PositionLimits")),
            delivery_method=delivery_method,
            last_trading_day=last_trading_day,
            last_delivery_day=clean_cme_spec_text(spec_payload.get("LastDeliveryDate")),
            delivery_period=clean_cme_spec_text(spec_payload.get("DeliveryPeriod")),
            deliverable_grades=clean_cme_spec_text(spec_payload.get("GradeAndQuality")),
            delivery_points=clean_cme_spec_text(spec_payload.get("DeliveryProcedure")),
            final_settlement_price=clean_cme_spec_text(spec_payload.get("SettlementAtExpiration")),
            settlement_procedure=clean_cme_spec_text(spec_payload.get("SettlementProcedures")),
            source_url=source_url,
            source_type="api+static",
            last_updated=now_str,
            notes=" ".join(notes),
        )
