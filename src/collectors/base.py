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

    def __init__(self, http_client: HttpClient):
        self.client = http_client
        self.logger = logging.getLogger(f"collector.{self.exchange_code}")

    @abstractmethod
    async def collect_all(self) -> List[ContractSpec]:
        """Collect specifications for all futures contracts on this exchange."""
        ...

    async def safe_collect(self) -> List[ContractSpec]:
        """Collect with error isolation — never raises, returns partial results."""
        try:
            results = await self.collect_all()
            self.logger.info(f"{self.exchange_code}: collected {len(results)} contracts")
            return results
        except Exception as e:
            self.logger.error(f"{self.exchange_code}: collection failed — {e}", exc_info=True)
            return []
