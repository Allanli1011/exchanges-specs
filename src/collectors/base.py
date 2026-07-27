from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from src.models.contract_spec import ContractSpec
from src.utils.http_client import HttpClient


class BaseCollector(ABC):
    """Abstract base class for all exchange collectors."""

    exchange_code: str = ""
    exchange_name_en: str = ""
    exchange_name_cn: Optional[str] = None
    rate_limit: float = 2.0  # seconds between requests
    base_url: str = ""

    def __init__(self, http_client: HttpClient, exchange_key: Optional[str] = None):
        self.client = http_client
        self.requested_exchange = exchange_key or self.exchange_code
        self.logger = logging.getLogger(f"collector.{self.requested_exchange}")

    def apply_config(self, exchange_config: Optional[dict]):
        """Apply registry metadata so runtime behavior matches config."""
        if not exchange_config:
            return

        self.rate_limit = exchange_config.get("rate_limit", self.rate_limit)
        self.base_url = exchange_config.get("base_url", self.base_url)
        self.exchange_name_en = exchange_config.get("name_en", self.exchange_name_en)
        self.exchange_name_cn = exchange_config.get("name_cn", self.exchange_name_cn)

    @abstractmethod
    async def collect_all(self) -> List[ContractSpec]:
        """Collect specifications for all futures contracts on this exchange."""
        ...

    async def safe_collect(self) -> List[ContractSpec]:
        """Collect with error isolation — never raises, returns partial results."""
        try:
            results = await self.collect_all()
            for spec in results:
                spec.data_quality = spec.inferred_data_quality()
            self.logger.info(f"{self.requested_exchange}: collected {len(results)} contracts")
            return results
        except Exception as e:
            self.logger.error(f"{self.requested_exchange}: collection failed — {e}", exc_info=True)
            return []
