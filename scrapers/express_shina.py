from __future__ import annotations

import asyncio
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


class ExpressShinaScraper(BaseScraper):
    site_name = "express_shina"
    base_url = "https://irkutsk.express-shina.ru"
    catalog_url = "https://irkutsk.express-shina.ru/search/legkovyie-shinyi"
    max_pages = 30
    winter_catalog_url = "https://irkutsk.express-shina.ru/search/legkovyie-shinyi?_Sezon=%D0%B7%D0%B8%D0%BC%D0%B0"
    summer_catalog_url = "https://irkutsk.express-shina.ru/search/legkovyie-shinyi?_Sezon=%D0%BB%D0%B5%D1%82%D0%BE"

    def _get_parse_cfg(self) -> dict:
        cfg = getattr(self, "parse_config", None)
        if isinstance(cfg, dict):
            return cfg
        return {
            "winter": True,
            "winter_studded": True,
            "winter_non_studded": True,
            "summer": True,
        }

    def _all_checks_enabled(self) -> bool:
        cfg = self._get_parse_cfg()
        return bool(cfg.get("winter") and cfg.get("winter_studded") and cfg.get("winter_non_studded") and cfg.get("summer"))

    @staticmethod
    def _detect_spike(card_text: str, product_name: str) -> bool | None:
        match = re.search(r"Наличие\s+шипов:\s*(Да|Нет)", card_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().lower() == "да"
        lowered = product_name.lower()
        if "нешип" in lowered:
            return False
        if "шип" in lowered:
            return True
        return None

    async def parse_products(self, html: str) -> list[ProductDTO]:
        soup = BeautifulSoup(html, "lxml")
        products: list[ProductDTO] = []
        for card in soup.select("div.b-offer"):
            title_el = card.select_one(".b-offer-main__title")
            price_el = card.select_one(".b-offer-pay__price span")
            if not title_el or not price_el:
                continue
            name = title_el.get_text(" ", strip=True)
            tire = parse_tire_size(name)
            if tire is None:
                continue
            price = clean_price(price_el.get_text(" ", strip=True))
            if price is None:
                continue
            old_el = card.select_one(".b-offer-pay__old-price, .old-price")
            old_price = clean_price(old_el.get_text(" ", strip=True)) if old_el else None
            link_el = card.select_one("a")
            href = link_el.get("href", "") if link_el else ""
            url = urljoin(self.base_url, href)
            brand, model = split_brand_model(name)
            card_text = card.get_text(" ", strip=True)
            spike = self._detect_spike(card_text, name)
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
                    spike=spike,
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
        return [f"{base_url}&num={page}" if "?" in base_url else f"{base_url}?num={page}" for page in range(2, self.max_pages + 1)]

    async def run(self) -> list[ProductDTO]:
        cfg = self._get_parse_cfg()
        all_enabled = self._all_checks_enabled()
        source_urls: list[str] = []
        if all_enabled:
            source_urls = [self.catalog_url]
        else:
            if cfg.get("winter"):
                source_urls.append(self.winter_catalog_url)
            if cfg.get("summer"):
                source_urls.append(self.summer_catalog_url)

        products: list[ProductDTO] = []
        async with await self.create_session() as session:
            for source_url in source_urls:
                first_html = await self.fetch_page(source_url, session)
                first_batch = await self.parse_products(first_html)
                if not all_enabled and source_url == self.winter_catalog_url:
                    if cfg.get("winter_studded") and not cfg.get("winter_non_studded"):
                        first_batch = [dto for dto in first_batch if dto.spike is True]
                    elif cfg.get("winter_non_studded") and not cfg.get("winter_studded"):
                        first_batch = [dto for dto in first_batch if dto.spike is False]
                    elif not cfg.get("winter_studded") and not cfg.get("winter_non_studded"):
                        first_batch = []
                products.extend(first_batch)

                if all_enabled:
                    extra_urls = await self.get_pagination_urls(first_html, source_url)
                    for page_url in extra_urls:
                        html = await self.fetch_page(page_url, session)
                        batch = await self.parse_products(html)
                        if not batch:
                            break
                        products.extend(batch)
                else:
                    # In filtered mode do not use max_pages limit; stop on first empty page.
                    for page in range(2, 101):
                        page_url = f"{source_url}&num={page}" if "?" in source_url else f"{source_url}?num={page}"
                        html = await self.fetch_page(page_url, session)
                        batch = await self.parse_products(html)
                        if not batch:
                            break
                        if source_url == self.winter_catalog_url:
                            if cfg.get("winter_studded") and not cfg.get("winter_non_studded"):
                                batch = [dto for dto in batch if dto.spike is True]
                            elif cfg.get("winter_non_studded") and not cfg.get("winter_studded"):
                                batch = [dto for dto in batch if dto.spike is False]
                            elif not cfg.get("winter_studded") and not cfg.get("winter_non_studded"):
                                batch = []
                        products.extend(batch)

        unique: dict[str, ProductDTO] = {}
        for dto in products:
            unique[dto.external_id] = dto
        return list(unique.values())


if __name__ == "__main__":
    result = asyncio.run(ExpressShinaScraper().run())
    print(f"Parsed {len(result)} products from {ExpressShinaScraper.site_name}")
