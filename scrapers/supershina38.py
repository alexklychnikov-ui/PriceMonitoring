from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


class Supershina38Scraper(BaseScraper):
    site_name = "supershina38"
    base_url = "https://supershina38.ru"
    catalog_url = "https://supershina38.ru/tires/"
    max_pages = 50

    async def parse_products(self, html: str) -> list[ProductDTO]:
        soup = BeautifulSoup(html, "lxml")
        products: list[ProductDTO] = []
        for row in soup.select("table tr"):
            title_el = row.select_one("td:nth-child(2) a, td:nth-child(3) a")
            price_el = row.select_one("td:nth-child(4)")
            if not title_el or not price_el:
                continue
            name = title_el.get_text(" ", strip=True)
            tire = parse_tire_size(name)
            if tire is None:
                continue
            price = clean_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            old_el = row.select_one("td:nth-child(4) del, td:nth-child(4) s")
            old_price = clean_price(old_el.get_text(" ", strip=True)) if old_el else None
            href = title_el.get("href", "")
            url = urljoin(self.base_url, href)
            brand, model = split_brand_model(name)
            discount_pct = None
            if old_price and old_price > 0 and old_price > price:
                discount_pct = round((old_price - price) / old_price * 100, 2)
            row_text = row.get_text(" ", strip=True)
            products.append(
                ProductDTO(
                    external_id=build_external_id(self.site_name, name, url),
                    name=name,
                    brand=brand,
                    model=model,
                    season=detect_season(name, row_text),
                    tire_size=tire.tire_size,
                    radius=tire.radius,
                    width=tire.width,
                    profile=tire.profile,
                    diameter=tire.diameter,
                    price=price,
                    old_price=old_price,
                    discount_pct=discount_pct,
                    in_stock=True,
                    url=url,
                    site_name=self.site_name,
                )
            )
        return products

    async def get_pagination_urls(self, html: str, base_url: str) -> list[str]:
        return []

    async def run(self) -> list[ProductDTO]:
        async with await self.create_session() as session:
            root_html = await self.fetch_page(self.catalog_url, session)
            root_soup = BeautifulSoup(root_html, "lxml")
            link_set: set[str] = set()
            for el in root_soup.select("div.makes_list a, a[href*='/tires/brand/']"):
                href = el.get("href", "")
                if not href:
                    continue
                link_set.add(urljoin(self.base_url, href))
            if not link_set:
                link_set.add(self.catalog_url)

            products: list[ProductDTO] = []
            for link in sorted(link_set):
                html = await self.fetch_page(link, session)
                products.extend(await self.parse_products(html))
        unique: dict[str, ProductDTO] = {}
        for dto in products:
            unique[dto.external_id] = dto
        return list(unique.values())


if __name__ == "__main__":
    result = asyncio.run(Supershina38Scraper().run())
    print(f"Parsed {len(result)} products from {Supershina38Scraper.site_name}")
