import asyncio
from datetime import datetime
from decimal import Decimal

import pytest

from src.collectors.base import BaseCollector
from src.collectors.cme_group import (
    CMEGroupCollector,
    _derive_cme_delivery_method,
    _prefer_static_if_generic,
    parse_cme_minimum_price_fluctuation,
    parse_cme_trading_hours,
)
from src.collectors.ice import ICECollector
from src.collectors.nse import parse_nse_lot_sizes
from src.collectors.shfe import (
    extract_shfe_product_rows,
    parse_shfe_market_timestamp,
    summarize_shfe_contract_months,
)
from src.main import build_output_filename, deduplicate_contracts, validate_registry
from src.models.contract_spec import ContractSpec, DeliveryMethod
from src.utils.http_client import HttpClient


def make_spec(**overrides) -> ContractSpec:
    data = {
        "exchange_code": "TEST",
        "exchange_name_en": "Test Exchange",
        "product_name_en": "Test Product",
        "ticker": "TP",
        "contract_size": "1 lot",
        "quote_unit": "USD/unit",
        "quote_currency": "USD",
        "tick_size": "0.01",
        "contract_months": "H,M,U,Z",
        "source_type": "static",
    }
    data.update(overrides)
    return ContractSpec(**data)


class DummyCollector(BaseCollector):
    exchange_code = "DUMMY"

    async def collect_all(self) -> list[ContractSpec]:
        return [
            make_spec(
                exchange_code="DUMMY",
                exchange_name_en="Dummy Exchange",
                product_name_en="Sparse Contract",
                ticker="DC",
                data_quality="complete",
                source_type="static",
            )
        ]


def test_ice_collector_respects_requested_exchange():
    async def run() -> list[ContractSpec]:
        client = HttpClient(cache=None)
        try:
            return await ICECollector(client, exchange_key="ICE_US").safe_collect()
        finally:
            await client.close()

    specs = asyncio.run(run())
    assert specs
    assert {spec.exchange_code for spec in specs} == {"ICE_US"}
    assert len(specs) == 8


def test_deduplicate_contracts_keeps_first_record():
    first = make_spec(exchange_code="ICE_US", exchange_sub="ICE_US", ticker="DX", product_name_en="US Dollar Index")
    duplicate = make_spec(exchange_code="ICE_US", exchange_sub="ICE_US", ticker="DX", product_name_en="US Dollar Index")
    unique = make_spec(exchange_code="ICE_EU", exchange_sub="ICE_EU", ticker="B", product_name_en="Brent Crude Oil")

    unique_contracts, duplicates = deduplicate_contracts([first, duplicate, unique])

    assert len(unique_contracts) == 2
    assert unique_contracts[0] is first
    assert duplicates == [("ICE_US", "ICE_US", "DX", "US Dollar Index")]


def test_build_output_filename_is_scope_aware_and_timestamped():
    filename = build_output_filename(
        ["ICE_US", "ICE_EU"],
        generated_at=datetime(2026, 3, 24, 13, 30, 45),
    )

    assert filename == "Global_Futures_Specs_ICE_US-ICE_EU_2026-03-24_13-30-45.xlsx"


def test_safe_collect_rewrites_misleading_complete_quality():
    specs = asyncio.run(DummyCollector(HttpClient(cache=None)).safe_collect())

    assert len(specs) == 1
    assert specs[0].data_quality == "manual_review"


def test_inferred_data_quality_allows_complete_for_high_coverage_live_sources():
    spec = make_spec(
        exchange_code="LIVE",
        exchange_name_en="Live Exchange",
        product_name_en="Rich Contract",
        ticker="LC",
        product_name_cn="丰富合约",
        product_group="Energy",
        bloomberg_code="LC1",
        contract_size_numeric=Decimal("1000"),
        contract_unit="barrels",
        tick_size_numeric=Decimal("0.01"),
        tick_value=Decimal("10"),
        tick_value_currency="USD",
        contract_months_codes="F,G,H,J,K,M,N,Q,U,V,X,Z",
        listed_contracts="72 monthly",
        trading_hours_regular="09:00-14:30",
        trading_hours_electronic="18:00-17:00",
        trading_hours_notes="UTC",
        settlement_method="VWAP",
        tas_eligible=True,
        tas_tick_range="+/- 10 ticks",
        price_limit_daily="7%",
        price_limit_type="circuit_breaker",
        initial_margin="10000",
        maintenance_margin="8000",
        margin_currency="USD",
        position_limit_spot="1000",
        position_limit_single="2000",
        position_limit_all="5000",
        large_trader_reporting="250",
        delivery_method=DeliveryMethod.CASH,
        last_trading_day="Business day before month end",
        first_notice_day="N/A",
        last_delivery_day="N/A",
        first_delivery_day="N/A",
        delivery_period="Cash settled",
        deliverable_grades="N/A",
        delivery_points="N/A",
        final_settlement_price="Official settlement",
        settlement_procedure="Exchange rulebook",
        source_type="api",
    )

    assert spec.inferred_data_quality() == "complete"


def test_apply_config_updates_runtime_metadata():
    collector = DummyCollector(HttpClient(cache=None))

    collector.apply_config({
        "name_en": "Configured Exchange",
        "name_cn": "配置交易所",
        "base_url": "https://example.com",
        "rate_limit": 9.5,
    })

    assert collector.exchange_name_en == "Configured Exchange"
    assert collector.exchange_name_cn == "配置交易所"
    assert collector.base_url == "https://example.com"
    assert collector.rate_limit == 9.5


def test_validate_registry_detects_mismatch():
    with pytest.raises(RuntimeError):
        validate_registry({"ICE_US": {}})


def test_parse_nse_lot_sizes_handles_index_and_stock_sections():
    csv_text = """UNDERLYING,SYMBOL,MAR-26,APR-26,MAY-26\nNIFTY 50,NIFTY,65,65,65\nDerivatives on Individual Securities,Symbol,MAR-26,APR-26,MAY-26\nABB INDIA LIMITED,ABB,125,125,125\n"""

    rows = parse_nse_lot_sizes(csv_text)

    assert rows == [
        {
            "section": "index",
            "underlying": "NIFTY 50",
            "symbol": "NIFTY",
            "lot_size": 65,
            "expiries": ["MAR-26", "APR-26", "MAY-26"],
        },
        {
            "section": "stock",
            "underlying": "ABB INDIA LIMITED",
            "symbol": "ABB",
            "lot_size": 125,
            "expiries": ["MAR-26", "APR-26", "MAY-26"],
        },
    ]


def test_parse_shfe_market_timestamp_splits_regular_and_electronic_sessions():
    regular, electronic = parse_shfe_market_timestamp(
        "21:00:00|02:30:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"
    )

    assert regular == "09:00-10:15, 10:30-11:30, 13:30-15:00"
    assert electronic == "21:00-02:30"


def test_extract_shfe_product_rows_filters_out_ine_products():
    payload = {
        "cu_f": {
            "exchangeid": "shfe",
            "productgroupid": "cu",
            "product_name_en": "Copper",
            "product_sort": "10",
        },
        "sc_f": {
            "exchangeid": "ine",
            "productgroupid": "sc",
            "product_name_en": "Crude Oil",
            "product_sort": "20",
        },
        "cu_o": {
            "exchangeid": "shfe",
            "productgroupid": "cu",
            "product_name_en": "Copper Option",
            "product_sort": "11",
        },
    }

    rows = extract_shfe_product_rows(payload)

    assert rows == [
        {
            "config_key": "cu_f",
            "exchangeid": "shfe",
            "productgroupid": "cu",
            "product_name_en": "Copper",
            "product_sort": "10",
        }
    ]


def test_summarize_shfe_contract_months_uses_ordered_expiries():
    contract_months, listed_contracts = summarize_shfe_contract_months([
        {"INSTRUMENTID": "au2702", "EXPIREDATE": "20270212"},
        {"INSTRUMENTID": "au2604", "EXPIREDATE": "20260415"},
        {"INSTRUMENTID": "au2612", "EXPIREDATE": "20261215"},
    ])

    assert contract_months == "2026-04, 2026-12, 2027-02"
    assert listed_contracts == "3"


def test_parse_cme_minimum_price_fluctuation_prefers_globex_and_extracts_tick_values():
    text, tick_size, tick_value, alternate_note = parse_cme_minimum_price_fluctuation({
        "ticks": [
            {"type": "Open Outcry:", "mintk": "0.10 = $10.00 per contract"},
            {"type": "CME Globex:", "mintk": "0.25 = $12.50 per contract"},
        ]
    })

    assert text == "0.25 = $12.50 per contract"
    assert tick_size == Decimal("0.25")
    assert tick_value == Decimal("12.50")
    assert alternate_note == "Open Outcry: 0.10 = $10.00 per contract"


def test_parse_cme_trading_hours_splits_globex_and_floor_sessions():
    electronic, regular, notes = parse_cme_trading_hours({
        "vandhr": [
            {"venue": "CME Globex:", "hours": "Sun-Fri 17:00-16:00"},
            {"venue": "Open Outcry:", "hours": "Mon-Fri 08:30-13:20"},
            {"venue": "CME ClearPort:", "hours": "Sun-Fri 17:00-16:00"},
        ]
    })

    assert electronic == "Sun-Fri 17:00-16:00"
    assert regular == "Mon-Fri 08:30-13:20"
    assert notes == "Central Time (CT, UTC-6/-5). CME ClearPort: Sun-Fri 17:00-16:00"


def test_cme_delivery_method_prefers_official_settlement_method():
    assert _derive_cme_delivery_method("Financially Settled", "physical") == DeliveryMethod.CASH
    assert _derive_cme_delivery_method("Deliverable", "cash") == DeliveryMethod.PHYSICAL


def test_cme_generic_limits_keep_specific_static_values():
    assert _prefer_static_if_generic(
        "27,300 (spot)",
        "Position Limits",
        {"position limits"},
    ) == "27,300 (spot)"
    assert _prefer_static_if_generic(
        "27,300 (spot)",
        "Spot month limit: 30,000",
        {"position limits"},
    ) == "Spot month limit: 30,000"


def test_cme_collector_falls_back_to_static_when_active_products_api_fails(monkeypatch):
    async def run() -> list[ContractSpec]:
        client = HttpClient(cache=None)
        collector = CMEGroupCollector(client)

        async def boom():
            raise RuntimeError("upstream unavailable")

        monkeypatch.setattr(collector, "_fetch_active_products", boom)
        try:
            return await collector.collect_all()
        finally:
            await client.close()

    specs = asyncio.run(run())

    assert len(specs) == 51
    assert all(spec.source_type == "static" for spec in specs)
    assert all("Official CME APIs were unavailable during this run" in (spec.notes or "") for spec in specs)
