"""Shanghai Futures Exchange (SHFE) collector."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Iterable, List

from src.collectors.base import BaseCollector
from src.models.contract_spec import ContractSpec, DeliveryMethod

SHFE_PRODUCT_CONFIG_URL = "https://www.shfe.com.cn/data/config/product_config.dat"
SHFE_CURRENT_TRADING_DAY_URL = "https://www.shfe.com.cn/data/config/currentTradingday.dat"
SHFE_CONTRACT_BASE_INFO_URL = "https://www.shfe.com.cn/data/busiparamdata/future/ContractBaseInfo{date}.dat"
SHFE_TRADE_ARGUMENT_URL = "https://www.shfe.com.cn/data/busiparamdata/future/ContractDailyTradeArgument{date}.dat"
SHFE_DELIVERY_URL = "https://www.shfe.com.cn/data/busiparamdata/future/Delivery{date}.dat"

STATIC_SHFE_FALLBACK_PRODUCTS = [
    {"ticker": "CU", "name_en": "Copper", "group": "Metal", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "10", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "AL", "name_en": "Aluminum", "group": "Metal", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "ZN", "name_en": "Zinc", "group": "Metal", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "PB", "name_en": "Lead", "group": "Metal", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "NI", "name_en": "Nickel", "group": "Metal", "size": "1", "unit_en": "ton", "unit_ens": "tons", "tick": "10", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "SN", "name_en": "Tin", "group": "Metal", "size": "1", "unit_en": "ton", "unit_ens": "tons", "tick": "10", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "AO", "name_en": "Aluminium Oxide", "group": "Metal", "size": "20", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "AD", "name_en": "Cast Aluminum Alloy", "group": "Metal", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "AU", "name_en": "Gold", "group": "Metal", "size": "1000", "unit_en": "gram", "unit_ens": "grams", "tick": "0.02", "hours": "21:00:00|02:30:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "AG", "name_en": "Silver", "group": "Metal", "size": "15", "unit_en": "kilogram", "unit_ens": "kilograms", "tick": "1", "hours": "21:00:00|02:30:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "RB", "name_en": "Steel Rebar", "group": "Metal", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "WR", "name_en": "Steel Wire Rod", "group": "Metal", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "HC", "name_en": "Hot Rolled Coil", "group": "Metal", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "SS", "name_en": "Stainless Steel", "group": "Metal", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|01:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "FU", "name_en": "Fuel Oil", "group": "Chemical", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "BU", "name_en": "Bitumen", "group": "Chemical", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "1", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "BR", "name_en": "Butadiene Rubber", "group": "Chemical", "size": "5", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "RU", "name_en": "Natural Rubber", "group": "Chemical", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "5", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "SP", "name_en": "Woodpulp", "group": "Chemical", "size": "10", "unit_en": "ton", "unit_ens": "tons", "tick": "2", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
    {"ticker": "OP", "name_en": "Offset Paper", "group": "Chemical", "size": "40", "unit_en": "ton", "unit_ens": "tons", "tick": "2", "hours": "21:00:00|23:00:00,09:00:00|10:15:00,10:30:00|11:30:00,13:30:00|15:00:00"},
]


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _format_percent(value: Decimal) -> str:
    return f"{_format_decimal(value * Decimal('100'))}%"


def _percent_band(values: Iterable[object]) -> str | None:
    normalized = sorted({
        decimal
        for value in values
        if (decimal := _decimal_or_none(value)) is not None
    })
    if not normalized:
        return None
    if len(normalized) == 1:
        return _format_percent(normalized[0])
    return f"{_format_percent(normalized[0])}-{_format_percent(normalized[-1])}"


def _format_date(value: str | None) -> str | None:
    if not value or len(value) != 8 or not value.isdigit():
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _format_month_label(value: str | None) -> str | None:
    date_label = _format_date(value)
    return date_label[:7] if date_label else None


def _instrument_prefix(instrument_id: str | None) -> str | None:
    if not instrument_id:
        return None
    match = re.match(r"[A-Za-z]+", instrument_id)
    return match.group(0).lower() if match else None


def parse_shfe_market_timestamp(raw_value: str | None) -> tuple[str | None, str | None]:
    if not raw_value:
        return None, None

    regular_sessions: list[str] = []
    electronic_sessions: list[str] = []

    for chunk in raw_value.split(","):
        if "|" not in chunk:
            continue
        start_raw, end_raw = (part.strip() for part in chunk.split("|", 1))
        start = start_raw[:5]
        end = end_raw[:5]
        session = f"{start}-{end}"

        if start >= "18:00" or end < start:
            electronic_sessions.append(session)
        else:
            regular_sessions.append(session)

    regular = ", ".join(regular_sessions) or None
    electronic = ", ".join(electronic_sessions) or None
    return regular, electronic


def summarize_shfe_contract_months(contract_rows: list[dict]) -> tuple[str | None, str | None]:
    if not contract_rows:
        return None, None

    seen_months: set[str] = set()
    ordered_months: list[str] = []
    seen_instruments: set[str] = set()

    for row in sorted(contract_rows, key=lambda item: item.get("EXPIREDATE", "")):
        instrument_id = row.get("INSTRUMENTID")
        if instrument_id:
            seen_instruments.add(instrument_id)

        month_label = _format_month_label(row.get("EXPIREDATE"))
        if month_label and month_label not in seen_months:
            seen_months.add(month_label)
            ordered_months.append(month_label)

    contract_months = ", ".join(ordered_months) or None
    listed_contracts = str(len(seen_instruments)) if seen_instruments else None
    return contract_months, listed_contracts


def extract_shfe_product_rows(payload: dict) -> list[dict]:
    products: list[dict] = []
    for key, value in payload.items():
        if not isinstance(value, dict):
            continue
        if not key.endswith("_f"):
            continue
        if value.get("exchangeid") != "shfe":
            continue
        products.append({"config_key": key, **value})

    def sort_key(item: dict) -> tuple[int, str]:
        product_sort = item.get("product_sort")
        try:
            return int(str(product_sort)), item.get("productgroupid", "")
        except (TypeError, ValueError):
            return 999999, item.get("productgroupid", "")

    return sorted(products, key=sort_key)


def _group_contract_rows(contract_rows: list[dict], allowed_codes: set[str]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in contract_rows:
        commodity_code = str(row.get("COMMODITYID", "")).lower()
        if commodity_code in allowed_codes:
            grouped[commodity_code].append(row)
    return grouped


def _group_instrument_rows(rows: list[dict], allowed_codes: set[str]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        commodity_code = _instrument_prefix(row.get("INSTRUMENTID"))
        if commodity_code in allowed_codes:
            grouped[commodity_code].append(row)
    return grouped


def _delivery_points(product: dict) -> str:
    has_factory = bool(product.get("weekly_factory_type"))
    has_warehouse = bool(product.get("weekly_warehouse_type") or product.get("stock_depot_name_en"))

    if has_factory and has_warehouse:
        return "SHFE designated warehouses and factory warehouses"
    if has_factory:
        return "SHFE designated factory warehouses"
    if has_warehouse:
        return "SHFE designated delivery warehouses"
    return "SHFE delivery locations per exchange notice"


def _price_limit_summary(trade_rows: list[dict]) -> tuple[str | None, str | None]:
    upper_band = _percent_band(row.get("UPPER_VALUE") for row in trade_rows)
    lower_band = _percent_band(row.get("LOWER_VALUE") for row in trade_rows)

    if not upper_band and not lower_band:
        return None, None

    if upper_band and upper_band == lower_band:
        return f"{upper_band} up/down", "fixed"

    parts = []
    if upper_band:
        parts.append(f"up {upper_band}")
    if lower_band:
        parts.append(f"down {lower_band}")
    return ", ".join(parts), "variable"


def _margin_fields(trade_rows: list[dict], delivery_rows: list[dict]) -> tuple[str | None, str | None]:
    speculative_margin = _percent_band(
        [row.get("SPEC_LONGMARGINRATIO") for row in trade_rows] +
        [row.get("SPEC_SHORTMARGINRATIO") for row in trade_rows]
    )
    hedge_margin = _percent_band(
        [row.get("HDEGE_LONGMARGINRATIO") for row in trade_rows] +
        [row.get("HDEGE_SHORTMARGINRATIO") for row in trade_rows]
    )
    delivery_margin = _percent_band(
        [row.get("LONGMARGINRATIO") for row in delivery_rows] +
        [row.get("SHORTMARGINRATIO") for row in delivery_rows]
    )

    notes: list[str] = []
    if hedge_margin:
        notes.append(f"Hedge margin observed at {hedge_margin}.")
    if delivery_margin:
        notes.append(f"Delivery-period margin observed at {delivery_margin}.")

    return speculative_margin, " ".join(notes) or None


def _contract_size_label(size: Decimal, unit_singular: str, unit_plural: str) -> str:
    unit_label = unit_singular if size == Decimal("1") else unit_plural
    return f"{_format_decimal(size)} {unit_label}/lot"


def _quote_unit(unit_singular: str) -> str:
    normalized_unit = unit_singular.lower()
    return f"CNY/{normalized_unit}"


class SHFECollector(BaseCollector):
    exchange_code = "SHFE"
    exchange_name_en = "Shanghai Futures Exchange"
    exchange_name_cn = "Shanghai Futures Exchange"
    rate_limit = 3.0
    base_url = "https://www.shfe.com.cn"

    async def collect_all(self) -> List[ContractSpec]:
        now_str = datetime.now(timezone.utc).isoformat()

        try:
            products = await self._fetch_product_catalog()
        except Exception as exc:
            self.logger.warning(f"SHFE product_config unavailable, using static fallback: {exc}")
            return self._build_static_fallback(now_str, f"Official SHFE product_config.dat unavailable during this run: {exc}")

        snapshot_date, contract_rows, trade_rows, delivery_rows, snapshot_warning = await self._fetch_snapshot_payloads()
        return self._build_specs(
            products=products,
            contract_rows=contract_rows,
            trade_rows=trade_rows,
            delivery_rows=delivery_rows,
            snapshot_date=snapshot_date,
            snapshot_warning=snapshot_warning,
            now_str=now_str,
        )

    async def _fetch_product_catalog(self) -> list[dict]:
        payload = await self.client.get_json(
            SHFE_PRODUCT_CONFIG_URL,
            rate_limit=self.rate_limit,
            headers={"Referer": f"{self.base_url}/eng/"},
        )
        return extract_shfe_product_rows(payload)

    async def _fetch_snapshot_payloads(self) -> tuple[str | None, list[dict], list[dict], list[dict], str | None]:
        snapshot_warning = None

        try:
            trading_day_payload = await self.client.get_json(
                SHFE_CURRENT_TRADING_DAY_URL,
                rate_limit=self.rate_limit,
                headers={"Referer": f"{self.base_url}/eng/"},
            )
        except Exception as exc:
            self.logger.warning(f"SHFE currentTradingday feed unavailable: {exc}")
            trading_day_payload = {}
            snapshot_warning = f"SHFE currentTradingday feed unavailable during this run: {exc}."

        candidate_dates = []
        for key in ("lastTradingday", "currentTradingday"):
            value = trading_day_payload.get(key)
            if value and value not in candidate_dates:
                candidate_dates.append(value)

        today_label = datetime.now().strftime("%Y%m%d")
        if today_label not in candidate_dates:
            candidate_dates.append(today_label)

        failures: list[str] = []
        for snapshot_date in candidate_dates:
            try:
                contract_payload = await self.client.get_json(
                    SHFE_CONTRACT_BASE_INFO_URL.format(date=snapshot_date),
                    rate_limit=self.rate_limit,
                    headers={"Referer": f"{self.base_url}/eng/"},
                )
                trade_payload = await self.client.get_json(
                    SHFE_TRADE_ARGUMENT_URL.format(date=snapshot_date),
                    rate_limit=self.rate_limit,
                    headers={"Referer": f"{self.base_url}/eng/"},
                )
                delivery_payload = await self.client.get_json(
                    SHFE_DELIVERY_URL.format(date=snapshot_date),
                    rate_limit=self.rate_limit,
                    headers={"Referer": f"{self.base_url}/eng/"},
                )
                return (
                    snapshot_date,
                    contract_payload.get("ContractBaseInfo", []),
                    trade_payload.get("ContractDailyTradeArgument", []),
                    delivery_payload.get("Delivery", []),
                    snapshot_warning,
                )
            except Exception as exc:
                failures.append(f"{snapshot_date}: {exc}")

        combined_warning = " ".join(part for part in [snapshot_warning, "Date-specific SHFE snapshot unavailable."] if part)
        if failures:
            combined_warning = f"{combined_warning} Tried {'; '.join(failures)}".strip()
        return None, [], [], [], combined_warning or None

    def _build_specs(
        self,
        products: list[dict],
        contract_rows: list[dict],
        trade_rows: list[dict],
        delivery_rows: list[dict],
        snapshot_date: str | None,
        snapshot_warning: str | None,
        now_str: str,
    ) -> list[ContractSpec]:
        commodity_codes = {product.get("productgroupid", "").lower() for product in products}
        contract_map = _group_contract_rows(contract_rows, commodity_codes)
        trade_map = _group_instrument_rows(trade_rows, commodity_codes)
        delivery_map = _group_instrument_rows(delivery_rows, commodity_codes)
        source_url = SHFE_CONTRACT_BASE_INFO_URL.format(date=snapshot_date) if snapshot_date else SHFE_PRODUCT_CONFIG_URL

        results: list[ContractSpec] = []
        for product in products:
            commodity_code = str(product.get("productgroupid", "")).lower()
            product_contract_rows = contract_map.get(commodity_code, [])
            product_trade_rows = trade_map.get(commodity_code, [])
            product_delivery_rows = delivery_map.get(commodity_code, [])

            contract_size_numeric = _decimal_or_none(product.get("contract_number")) or Decimal("0")
            tick_size_numeric = _decimal_or_none(product.get("product_tick"))
            regular_hours, electronic_hours = parse_shfe_market_timestamp(product.get("market_timestamp"))
            contract_months, listed_contracts = summarize_shfe_contract_months(product_contract_rows)
            price_limit_daily, price_limit_type = _price_limit_summary(product_trade_rows)
            initial_margin, margin_notes = _margin_fields(product_trade_rows, product_delivery_rows)

            note_parts: list[str] = []
            if snapshot_warning:
                note_parts.append(snapshot_warning)
            if snapshot_date and product_contract_rows:
                note_parts.append(
                    f"Observed {len(product_contract_rows)} active SHFE contracts in snapshot {snapshot_date}; "
                    "contract months reflect currently listed expiries."
                )
            elif snapshot_date:
                note_parts.append(
                    f"Product is present in SHFE product_config.dat but had no active contracts in snapshot {snapshot_date}."
                )
            else:
                note_parts.append("Built from SHFE product_config.dat only; dated contract snapshot was unavailable.")

            results.append(
                ContractSpec(
                    exchange_code="SHFE",
                    exchange_name_en=self.exchange_name_en,
                    exchange_name_cn=self.exchange_name_cn,
                    product_name_en=product.get("product_name_en") or product.get("productname") or commodity_code.upper(),
                    product_name_cn=product.get("product_name_cn") or product.get("productname"),
                    product_group=product.get("product_type_en"),
                    ticker=commodity_code.upper(),
                    contract_size=_contract_size_label(
                        contract_size_numeric,
                        product.get("unit_en", "unit"),
                        product.get("unit_ens", product.get("unit_en", "units")),
                    ),
                    contract_size_numeric=contract_size_numeric,
                    contract_unit=product.get("unit_en"),
                    quote_unit=_quote_unit(product.get("unit_en", "unit")),
                    quote_currency="CNY",
                    tick_size=_format_decimal(tick_size_numeric) if tick_size_numeric is not None else "",
                    tick_size_numeric=tick_size_numeric,
                    tick_value=(contract_size_numeric * tick_size_numeric) if tick_size_numeric is not None else None,
                    tick_value_currency="CNY" if tick_size_numeric is not None else None,
                    contract_months=contract_months or "See SHFE dated contract snapshot",
                    listed_contracts=listed_contracts,
                    trading_hours_regular=regular_hours,
                    trading_hours_electronic=electronic_hours,
                    trading_hours_notes="Beijing Time (UTC+8). Sessions sourced from SHFE product_config.dat.",
                    price_limit_daily=price_limit_daily,
                    price_limit_type=price_limit_type,
                    initial_margin=initial_margin,
                    margin_notes=margin_notes,
                    delivery_method=DeliveryMethod.PHYSICAL,
                    delivery_points=_delivery_points(product),
                    source_url=source_url,
                    source_type="api",
                    last_updated=now_str,
                    notes=" ".join(note_parts),
                )
            )

        return results

    def _build_static_fallback(self, now_str: str, warning_note: str) -> list[ContractSpec]:
        results: list[ContractSpec] = []
        for product in STATIC_SHFE_FALLBACK_PRODUCTS:
            contract_size_numeric = Decimal(product["size"])
            tick_size_numeric = Decimal(product["tick"])
            regular_hours, electronic_hours = parse_shfe_market_timestamp(product["hours"])
            results.append(
                ContractSpec(
                    exchange_code="SHFE",
                    exchange_name_en=self.exchange_name_en,
                    exchange_name_cn=self.exchange_name_cn,
                    product_name_en=product["name_en"],
                    product_group=product["group"],
                    ticker=product["ticker"],
                    contract_size=_contract_size_label(
                        contract_size_numeric,
                        product["unit_en"],
                        product["unit_ens"],
                    ),
                    contract_size_numeric=contract_size_numeric,
                    contract_unit=product["unit_en"],
                    quote_unit=_quote_unit(product["unit_en"]),
                    quote_currency="CNY",
                    tick_size=_format_decimal(tick_size_numeric),
                    tick_size_numeric=tick_size_numeric,
                    tick_value=contract_size_numeric * tick_size_numeric,
                    tick_value_currency="CNY",
                    contract_months="Static fallback; live SHFE snapshot unavailable",
                    trading_hours_regular=regular_hours,
                    trading_hours_electronic=electronic_hours,
                    trading_hours_notes="Beijing Time (UTC+8). Static fallback metadata.",
                    delivery_method=DeliveryMethod.PHYSICAL,
                    delivery_points="SHFE delivery locations per exchange notice",
                    source_url=SHFE_PRODUCT_CONFIG_URL,
                    source_type="static",
                    last_updated=now_str,
                    notes=f"{warning_note} Static fallback metadata only; active contract discovery was unavailable.",
                )
            )
        return results
