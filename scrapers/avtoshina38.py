from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


logger = logging.getLogger(__name__)


class Avtoshina38Scraper(BaseScraper):
    site_name = "avtoshina38"
    base_url = "https://avtoshina38.ru"
    catalog_url = "https://avtoshina38.ru/catalog/tires/"
    max_pages = 30

    async def _get_session_cookies(self) -> dict[str, str]:
        try:
            from playwright.async_api import async_playwright
        except Exception:
            return {}
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(self.catalog_url, wait_until="networkidle")
                cookies = await page.context.cookies()
                await browser.close()
                return {item["name"]: item["value"] for item in cookies}
        except Exception as error:
            logger.warning("Playwright cookie bootstrap failed: %s", type(error).__name__)
            return {}

    async def parse_products(self, html: str) -> list[ProductDTO]:
        soup = BeautifulSoup(html, "lxml")
        products: list[ProductDTO] = []
        for row in soup.select("table tr"):
            title_el = row.select_one("td:nth-child(3) a")
            price_el = row.select_one("td:nth-child(4)")
            if not title_el or not price_el:
                continue
            name = title_el.get_text(" ", strip=True)
            current_price = clean_price(price_el.get_text(" ", strip=True))
            if current_price is None:
                continue
            old_el = row.select_one("td:nth-child(4) del, td:nth-child(4) s")
            old_price = clean_price(old_el.get_text(" ", strip=True)) if old_el else None
            tire = parse_tire_size(name)
            if tire is None:
                continue
            brand, model = split_brand_model(name)
            relative_url = title_el.get("href", "")
            product_url = urljoin(self.base_url, relative_url)
            discount_pct = None
            if old_price and old_price > 0 and old_price > current_price:
                discount_pct = round((old_price - current_price) / old_price * 100, 2)
            products.append(
                ProductDTO(
                    external_id=build_external_id(self.site_name, name, product_url),
                    name=name,
                    brand=brand,
                    model=model,
                    season=detect_season(name),
                    tire_size=tire.tire_size,
                    radius=tire.radius,
                    width=tire.width,
                    profile=tire.profile,
                    diameter=tire.diameter,
                    price=current_price,
                    old_price=old_price,
                    discount_pct=discount_pct,
                    in_stock=True,
                    url=product_url,
                    site_name=self.site_name,
                )
            )
        return products

    async def get_pagination_urls(self, html: str, base_url: str) -> list[str]:
        return []

    async def run(self) -> list[ProductDTO]:
        async with await self.create_session() as session:
            cookies = await self._get_session_cookies()
            if cookies:
                session.cookie_jar.update_cookies(cookies)
            first_html = await self.fetch_page(self.catalog_url, session)
            products = await self.parse_products(first_html)
            for page in range(2, self.max_pages + 1):
                payload = {"PAGEN_1": str(page)}
                try:
                    async with session.post(self.catalog_url, data=payload) as response:
                        response.raise_for_status()
                        html = await response.text()
                except Exception:
                    break
                batch = await self.parse_products(html)
                if not batch:
                    break
                products.extend(batch)
        unique: dict[str, ProductDTO] = {}
        for dto in products:
            unique[dto.external_id] = dto
        return list(unique.values())


if __name__ == "__main__":
    result = asyncio.run(Avtoshina38Scraper().run())
    print(f"Parsed {len(result)} products from {Avtoshina38Scraper.site_name}")
