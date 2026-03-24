import asyncio
import hashlib
import logging
import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.cache import HttpCache

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}


class HttpClient:
    """Async HTTP client with retry, rate limiting, and caching."""

    def __init__(
        self,
        cache: Optional[HttpCache] = None,
        rate_limit: float = 2.0,
        timeout: float = 30.0,
        max_concurrent: int = 5,
    ):
        self.cache = cache
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request_time: dict[str, float] = {}  # per-domain rate limiting
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                verify=False,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc

    async def _rate_limit_wait(self, domain: str, rate_limit: float):
        now = time.monotonic()
        last = self._last_request_time.get(domain, 0)
        wait_time = rate_limit - (now - last)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_request_time[domain] = time.monotonic()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def get(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        rate_limit: Optional[float] = None,
        use_cache: bool = True,
        encoding: Optional[str] = None,
    ) -> str:
        """GET request with caching, rate limiting, and retry."""
        cache_key = self._cache_key(url, params)

        if use_cache and self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {url}")
                return cached

        domain = self._get_domain(url)
        rl = rate_limit if rate_limit is not None else self.rate_limit

        async with self._semaphore:
            await self._rate_limit_wait(domain, rl)
            client = await self._get_client()
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            if encoding:
                response.encoding = encoding
            text = response.text

        if use_cache and self.cache:
            await self.cache.set(cache_key, text)

        return text

    async def get_json(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        rate_limit: Optional[float] = None,
        use_cache: bool = True,
    ) -> dict:
        """GET request returning parsed JSON."""
        cache_key = self._cache_key(url, params) + ":json"

        if use_cache and self.cache:
            import json
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return json.loads(cached)

        domain = self._get_domain(url)
        rl = rate_limit if rate_limit is not None else self.rate_limit

        async with self._semaphore:
            await self._rate_limit_wait(domain, rl)
            client = await self._get_client()
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        if use_cache and self.cache:
            import json
            await self.cache.set(cache_key, json.dumps(data, ensure_ascii=False))

        return data

    def _cache_key(self, url: str, params: Optional[dict] = None) -> str:
        key = url
        if params:
            key += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.md5(key.encode()).hexdigest()
