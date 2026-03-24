"""
Global Futures Contract Specification Collector
Usage:
    python -m src.main --exchanges all
    python -m src.main --exchanges CME SHFE EUREX
    python -m src.main --exchanges all --no-cache
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Type

import yaml
from tqdm import tqdm

from src.models.contract_spec import ContractSpec
from src.collectors.base import BaseCollector
from src.utils.http_client import HttpClient
from src.utils.cache import HttpCache
from src.exporters.excel_exporter import export_to_excel

# Collector registry — import and register all collectors here
from src.collectors.cme_group import CMEGroupCollector
from src.collectors.shfe import SHFECollector
from src.collectors.dce import DCECollector
from src.collectors.czce import CZCECollector
from src.collectors.cffex import CFFEXCollector
from src.collectors.ine import INECollector
from src.collectors.gfex import GFEXCollector
from src.collectors.lme import LMECollector
from src.collectors.sgx import SGXCollector
from src.collectors.hkex import HKEXCollector
from src.collectors.jpx import JPXCollector
from src.collectors.eurex import EurexCollector
from src.collectors.ice import ICECollector
from src.collectors.krx import KRXCollector
from src.collectors.taifex import TAIFEXCollector
from src.collectors.bmd import BMDCollector
from src.collectors.asx import ASXCollector
from src.collectors.cboe import CBOECollector
from src.collectors.b3 import B3Collector
from src.collectors.moex import MOEXCollector
from src.collectors.nse import NSECollector

COLLECTOR_MAP: Dict[str, Type[BaseCollector]] = {
    "CME": CMEGroupCollector,
    "SHFE": SHFECollector,
    "DCE": DCECollector,
    "CZCE": CZCECollector,
    "CFFEX": CFFEXCollector,
    "INE": INECollector,
    "GFEX": GFEXCollector,
    "LME": LMECollector,
    "SGX": SGXCollector,
    "HKEX": HKEXCollector,
    "JPX": JPXCollector,
    "EUREX": EurexCollector,
    "ICE_US": ICECollector,
    "ICE_EU": ICECollector,
    "KRX": KRXCollector,
    "TAIFEX": TAIFEXCollector,
    "BMD": BMDCollector,
    "ASX": ASXCollector,
    "CBOE": CBOECollector,
    "B3": B3Collector,
    "MOEX": MOEXCollector,
    "NSE": NSECollector,
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_exchange_config() -> dict:
    config_path = os.path.join(PROJECT_ROOT, "config", "exchanges.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["exchanges"]


async def collect_exchange(
    exchange_key: str,
    collector_cls: Type[BaseCollector],
    http_client: HttpClient,
) -> List[ContractSpec]:
    collector = collector_cls(http_client)
    return await collector.safe_collect()


async def run(args):
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    config = load_exchange_config()

    # Determine which exchanges to collect
    if "all" in args.exchanges:
        exchange_keys = list(COLLECTOR_MAP.keys())
    else:
        exchange_keys = [e.upper() for e in args.exchanges]
        invalid = [e for e in exchange_keys if e not in COLLECTOR_MAP]
        if invalid:
            logger.error(f"Unknown exchanges: {invalid}. Available: {list(COLLECTOR_MAP.keys())}")
            sys.exit(1)

    # Initialize HTTP client and cache
    cache = None if args.no_cache else HttpCache(
        cache_dir=os.path.join(PROJECT_ROOT, "data", "cache"),
        ttl=args.cache_ttl,
    )
    http_client = HttpClient(cache=cache, rate_limit=2.0, max_concurrent=args.parallel)

    logger.info(f"Collecting from {len(exchange_keys)} exchanges: {exchange_keys}")

    # Collect from all exchanges concurrently (bounded by semaphore)
    all_contracts: List[ContractSpec] = []
    tasks = []
    for key in exchange_keys:
        collector_cls = COLLECTOR_MAP[key]
        tasks.append(collect_exchange(key, collector_cls, http_client))

    pbar = tqdm(total=len(tasks), desc="Exchanges", unit="exch")
    for coro in asyncio.as_completed(tasks):
        contracts = await coro
        all_contracts.extend(contracts)
        pbar.update(1)
    pbar.close()

    logger.info(f"Total contracts collected: {len(all_contracts)}")

    # Export to Excel
    output_dir = os.path.join(PROJECT_ROOT, "data", "output")
    filepath = export_to_excel(all_contracts, output_dir=output_dir)
    logger.info(f"Excel output saved to: {filepath}")

    # Cleanup
    await http_client.close()
    if cache:
        await cache.close()

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Global Futures Contract Spec Collector")
    parser.add_argument(
        "--exchanges", nargs="+", default=["all"],
        help="Exchanges to collect (e.g., CME SHFE EUREX) or 'all'",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable HTTP response cache")
    parser.add_argument("--cache-ttl", type=int, default=86400, help="Cache TTL in seconds (default: 24h)")
    parser.add_argument("--parallel", type=int, default=5, help="Max concurrent exchange collections")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
