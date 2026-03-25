from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


class KolesaDaromScraper(BaseScraper):
    site_name = "kolesa_darom"
    base_url = "https://irkutsk.kolesa-darom.ru"
    catalog_url = "https://irkutsk.kolesa-darom.ru/catalog/avto/shiny/"
    max_pages = 30

    async def parse_products(self, html: str) -> list[ProductDTO]:
        soup = BeautifulSoup(html, "lxml")
        products: list[ProductDTO] = []
        cards = soup.select(".product-card")
        for card in cards:
            title_el = card.select_one(".product-card-properties__title")
            price_el = card.select_one(".product-card__button.kd-btn_primary, .product-card__price")
            link_el = card.select_one("a.product-card-properties__main, a.product-card__image-container")
            if not title_el or not price_el:
                continue
            brand_name = title_el.get_text(" ", strip=True)
            # build tire size from chips: first 3 chips are width, profile, radius
            chips = [li.get_text(strip=True) for li in card.select(".kd-chip-new")]
            size_str = ""
            if len(chips) >= 3:
                size_str = f" {chips[0]}/{chips[1]} {chips[2]}"
            name = brand_name + size_str
            tire = parse_tire_size(name)
            if tire is None:
                continue
            price = clean_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            href = link_el.get("href", "") if link_el else ""
            url = urljoin(self.base_url, href)
            brand, model = split_brand_model(brand_name)
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
                    old_price=None,
                    discount_pct=None,
                    in_stock=True,
                    url=url,
                    site_name=self.site_name,
                )
            )
        return products

    async def get_pagination_urls(self, html: str, base_url: str) -> list[str]:
        # On the website pagination is rendered as:
        # /catalog/avto/shiny/nav/page-{N}/
        nav_base = self.catalog_url.rstrip("/") + "/nav"
        return [f"{nav_base}/page-{page}/" for page in range(2, self.max_pages + 1)]


if __name__ == "__main__":
    result = asyncio.run(KolesaDaromScraper().run())
    print(f"Parsed {len(result)} products from {KolesaDaromScraper.site_name}")
