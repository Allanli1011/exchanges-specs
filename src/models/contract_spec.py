from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from decimal import Decimal


class DeliveryMethod(str, Enum):
    PHYSICAL = "physical"
    CASH = "cash"
    BOTH = "both"


class ContractSpec(BaseModel):
    """Unified schema for a single futures contract specification."""

    # === BASIC SPECS ===
    exchange_code: str = Field(description="Exchange code: CME, SHFE, EUREX, etc.")
    exchange_sub: Optional[str] = Field(default=None, description="Sub-exchange: CBOT, NYMEX, COMEX, TOCOM")
    exchange_name_en: str = Field(description="Exchange full name in English")
    exchange_name_cn: Optional[str] = Field(default=None, description="Exchange full name in Chinese")
    product_name_en: str = Field(description="Product name in English")
    product_name_cn: Optional[str] = Field(default=None, description="Product name in Chinese")
    product_group: Optional[str] = Field(default=None, description="Category: Equity Index, Energy, Metals, etc.")
    ticker: str = Field(description="Exchange ticker symbol")
    bloomberg_code: Optional[str] = Field(default=None, description="Bloomberg ticker")
    contract_size: str = Field(description="Contract size description")
    contract_size_numeric: Optional[Decimal] = Field(default=None, description="Numeric multiplier")
    contract_unit: Optional[str] = Field(default=None, description="Unit: barrels, metric tons, USD")
    quote_unit: str = Field(description="Quote unit: USD per barrel, index points")
    quote_currency: str = Field(description="Currency: USD, CNY, EUR, JPY")
    tick_size: str = Field(description="Minimum tick size description")
    tick_size_numeric: Optional[Decimal] = Field(default=None, description="Numeric tick size")
    tick_value: Optional[Decimal] = Field(default=None, description="Monetary value of one tick")
    tick_value_currency: Optional[str] = Field(default=None, description="Tick value currency")
    contract_months: str = Field(description="Available contract months")
    contract_months_codes: Optional[str] = Field(default=None, description="Month codes: H,M,U,Z")
    listed_contracts: Optional[str] = Field(default=None, description="Number of listed contracts")
    trading_hours_regular: Optional[str] = Field(default=None, description="Regular trading hours")
    trading_hours_electronic: Optional[str] = Field(default=None, description="Electronic trading hours")
    trading_hours_notes: Optional[str] = Field(default=None, description="Timezone and special sessions")
    settlement_method: Optional[str] = Field(default=None, description="Daily settlement method")

    # === TAS / TAM RULES ===
    tas_eligible: Optional[bool] = Field(default=None, description="TAS trading available")
    tas_tick_range: Optional[str] = Field(default=None, description="TAS allowed tick range")
    tas_tick_range_numeric: Optional[int] = Field(default=None, description="TAS tick range number")
    tas_eligible_months: Optional[str] = Field(default=None, description="TAS eligible contract months")
    tas_trading_hours: Optional[str] = Field(default=None, description="TAS trading window")
    tam_eligible: Optional[bool] = Field(default=None, description="TAM eligible")
    tam_rules: Optional[str] = Field(default=None, description="TAM rules")
    btic_eligible: Optional[bool] = Field(default=None, description="BTIC eligible")
    btic_rules: Optional[str] = Field(default=None, description="BTIC rules")
    block_trade_minimum: Optional[str] = Field(default=None, description="Block trade minimum")
    efp_eligible: Optional[bool] = Field(default=None, description="EFP eligible")

    # === RISK CONTROLS ===
    price_limit_daily: Optional[str] = Field(default=None, description="Daily price limit")
    price_limit_type: Optional[str] = Field(default=None, description="Limit type: circuit breaker, variable")
    initial_margin: Optional[str] = Field(default=None, description="Initial margin")
    maintenance_margin: Optional[str] = Field(default=None, description="Maintenance margin")
    margin_currency: Optional[str] = Field(default=None, description="Margin currency")
    margin_notes: Optional[str] = Field(default=None, description="Margin notes")
    position_limit_spot: Optional[str] = Field(default=None, description="Spot month position limit")
    position_limit_single: Optional[str] = Field(default=None, description="Single month position limit")
    position_limit_all: Optional[str] = Field(default=None, description="All months position limit")
    position_limit_notes: Optional[str] = Field(default=None, description="Position limit notes")
    large_trader_reporting: Optional[str] = Field(default=None, description="Reportable position level")
    position_accountability_level: Optional[str] = Field(default=None, description="Accountability level")

    # === DELIVERY ===
    delivery_method: Optional[DeliveryMethod] = Field(default=None, description="Physical/Cash/Both")
    last_trading_day: Optional[str] = Field(default=None, description="Last trading day rule")
    first_notice_day: Optional[str] = Field(default=None, description="First notice day")
    last_delivery_day: Optional[str] = Field(default=None, description="Last delivery day")
    first_delivery_day: Optional[str] = Field(default=None, description="First delivery day")
    delivery_period: Optional[str] = Field(default=None, description="Delivery period")
    deliverable_grades: Optional[str] = Field(default=None, description="Deliverable grades/quality")
    delivery_points: Optional[str] = Field(default=None, description="Delivery locations")
    final_settlement_price: Optional[str] = Field(default=None, description="Final settlement calculation")
    settlement_procedure: Optional[str] = Field(default=None, description="Settlement procedure")

    # === METADATA ===
    source_url: Optional[str] = Field(default=None, description="Data source URL")
    source_type: Optional[str] = Field(default=None, description="Source type: api, html, pdf")
    last_updated: Optional[str] = Field(default=None, description="ISO datetime of data collection")
    data_quality: Optional[str] = Field(default=None, description="complete, partial, manual_review")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    def completeness_score(self) -> float:
        """Calculate data completeness as percentage of non-None fields."""
        fields = type(self).model_fields
        total = len(fields) - 5  # exclude metadata fields
        filled = sum(
            1 for k, v in self.model_dump().items()
            if v is not None and k not in ("source_url", "source_type", "last_updated", "data_quality", "notes")
        )
        return round(filled / total * 100, 1) if total > 0 else 0.0

    def inferred_data_quality(self) -> str:
        """Infer a realistic data quality label from coverage and source type."""
        score = self.completeness_score()
        source_parts = {
            part.strip().lower()
            for part in (self.source_type or "").split("+")
            if part.strip()
        }
        has_live_source = bool(source_parts & {"api", "html", "pdf"})

        if score >= 75 and has_live_source and "static" not in source_parts:
            return "complete"
        if score >= 40 or has_live_source:
            return "partial"
        return "manual_review"
