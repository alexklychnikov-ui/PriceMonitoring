from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


class ShinserviceScraper(BaseScraper):
    site_name = "shinservice"
    base_url = "https://irkutsk.shinservice.ru"
    catalog_url = "https://irkutsk.shinservice.ru/catalog/tyres/"
    max_pages = 30

    async def parse_products(self, html: str) -> list[ProductDTO]:
        soup = BeautifulSoup(html, "lxml")
        products: list[ProductDTO] = []
        for card in soup.select(".product-card"):
            title_el = card.select_one(".product-card__title")
            price_el = card.select_one(".product-card__price")
            if not title_el or not price_el:
                continue
            name = title_el.get_text(" ", strip=True)
            tire = parse_tire_size(name)
            if tire is None:
                continue
            price = clean_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            old_el = card.select_one(".product-card__old-price")
            old_price = clean_price(old_el.get_text(" ", strip=True)) if old_el else None
            brand, model = split_brand_model(name)
            href = title_el.get("href", "")
            url = urljoin(self.base_url, href)
            discount_pct = None
            if old_price and old_price > 0 and old_price > price:
                discount_pct = round((old_price - price) / old_price * 100, 2)
            products.append(
                ProductDTO(
                    external_id=build_external_id(self.site_name, name, url),
                    name=name,
                    brand=brand,
                    model=model,
                    season=detect_season(name),
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
        return [f"{self.catalog_url}?page={page}" for page in range(2, self.max_pages + 1)]


if __name__ == "__main__":
    result = asyncio.run(ShinserviceScraper().run())
    print(f"Parsed {len(result)} products from {ShinserviceScraper.site_name}")
