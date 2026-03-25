from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any

import aiohttp

from config import settings
from scrapers.proxy_manager import ProxyManager
from scrapers.schemas import ProductDTO
from scrapers.utils import get_random_ua


logger = logging.getLogger(__name__)


class BaseScraper(abc.ABC):
    site_name: str = ""
    base_url: str = ""
    catalog_url: str = ""
    max_pages: int = 20

    def __init__(self, proxy_manager: ProxyManager | None = None):
        self.proxy_manager = proxy_manager or ProxyManager(settings.PROXY_LIST)
        self._timeout = aiohttp.ClientTimeout(total=30)

    async def create_session(self) -> aiohttp.ClientSession:
        headers = {"User-Agent": await get_random_ua()}
        return aiohttp.ClientSession(timeout=self._timeout, headers=headers)

    async def fetch_page(self, url: str, session: aiohttp.ClientSession, **request_kwargs: Any) -> str:
        last_error: Exception | None = None
        delay = 1
        for attempt in range(1, 4):
            proxy = await self.proxy_manager.get_proxy()
            try:
                async with session.get(url, proxy=proxy or None, **request_kwargs) as response:
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        wait_for = int(retry_after) if retry_after and retry_after.isdigit() else 60
                        await asyncio.sleep(wait_for)
                        continue
                    if response.status == 403:
                        await self.proxy_manager.mark_failed(proxy)
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    response.raise_for_status()
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                last_error = error
                logger.warning(
                    "Fetch failed site=%s url=%s attempt=%s error=%s",
                    self.site_name,
                    url,
                    attempt,
                    type(error).__name__,
                )
                await asyncio.sleep(delay)
                delay *= 2
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Cannot fetch {url}")

    @abc.abstractmethod
    async def parse_products(self, html: str) -> list[ProductDTO]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_pagination_urls(self, html: str, base_url: str) -> list[str]:
        raise NotImplementedError

    async def run(self) -> list[ProductDTO]:
        async with await self.create_session() as session:
            first_html = await self.fetch_page(self.catalog_url, session)
            products = await self.parse_products(first_html)
            extra_urls = await self.get_pagination_urls(first_html, self.catalog_url)
            for url in extra_urls[: self.max_pages]:
                html = await self.fetch_page(url, session)
                batch = await self.parse_products(html)
                if not batch:
                    break
                products.extend(batch)
        unique: dict[str, ProductDTO] = {}
        for dto in products:
            unique[dto.external_id] = dto
        return list(unique.values())
