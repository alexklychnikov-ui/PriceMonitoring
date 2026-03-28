from __future__ import annotations

import asyncio
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from aiohttp import ClientResponseError

from scrapers.base import BaseScraper
from scrapers.schemas import ProductDTO
from scrapers.utils import build_external_id, clean_price, detect_season, parse_tire_size, split_brand_model


def _dedupe_catalog_by_url_path(products: list[ProductDTO]) -> list[ProductDTO]:
    """One card per catalog URL path; keep highest price to drop outlier lows from duplicate cards."""
    best: dict[str, ProductDTO] = {}
    for dto in products:
        path = urlparse(dto.url).path.rstrip("/")
        key = path if path else dto.external_id
        cur = best.get(key)
        if cur is None or dto.price > cur.price:
            best[key] = dto
    return list(best.values())


class KolesaDaromScraper(BaseScraper):
    site_name = "kolesa_darom"
    base_url = "https://irkutsk.kolesa-darom.ru"
    catalog_url = "https://irkutsk.kolesa-darom.ru/catalog/avto/shiny/"
    max_pages = 30
    winter_studded_url = "https://irkutsk.kolesa-darom.ru/catalog/avto/shiny/shipovannie/zima/"
    winter_non_studded_url = "https://irkutsk.kolesa-darom.ru/catalog/avto/shiny/bezshipov/zima/"
    summer_url = "https://irkutsk.kolesa-darom.ru/catalog/avto/shiny/leto/"

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
            lowered_name = name.lower()
            spike: bool | None = None
            if "нешип" in lowered_name or "липуч" in lowered_name:
                spike = False
            elif "шип" in lowered_name:
                spike = True
            card_text = card.get_text(" ", strip=True)
            products.append(
                ProductDTO(
                    external_id=build_external_id(self.site_name, name, url),
                    name=name,
                    brand=brand,
                    model=model,
                    season=detect_season(name, card_text),
                    spike=spike,
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
        nav_base = base_url.rstrip("/") + "/nav"
        return [f"{nav_base}/page-{page}/" for page in range(2, self.max_pages + 1)]

    async def run(self) -> list[ProductDTO]:
        cfg = self._get_parse_cfg()
        all_enabled = self._all_checks_enabled()
        source_urls: list[tuple[str, str | None, bool | None]] = []

        if all_enabled:
            source_urls = [(self.catalog_url, None, None)]
        else:
            if cfg.get("winter"):
                if cfg.get("winter_studded"):
                    source_urls.append((self.winter_studded_url, "winter", True))
                if cfg.get("winter_non_studded"):
                    source_urls.append((self.winter_non_studded_url, "winter", False))
            if cfg.get("summer"):
                source_urls.append((self.summer_url, "summer", False))

        products: list[ProductDTO] = []
        async with await self.create_session() as session:
            for source_url, forced_season, forced_spike in source_urls:
                first_html = await self.fetch_page(source_url, session)
                first_batch = await self.parse_products(first_html)
                for dto in first_batch:
                    if forced_season is not None:
                        dto.season = forced_season
                    if forced_spike is not None:
                        dto.spike = forced_spike
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
                    nav_base = source_url.rstrip("/") + "/nav"
                    for page in range(2, 101):
                        page_url = f"{nav_base}/page-{page}/"
                        try:
                            html = await self.fetch_page(page_url, session)
                        except ClientResponseError as error:
                            if error.status in {404, 410}:
                                break
                            raise
                        batch = await self.parse_products(html)
                        if not batch:
                            break
                        for dto in batch:
                            if forced_season is not None:
                                dto.season = forced_season
                            if forced_spike is not None:
                                dto.spike = forced_spike
                        products.extend(batch)

        unique: dict[str, ProductDTO] = {}
        for dto in products:
            unique[dto.external_id] = dto
        return _dedupe_catalog_by_url_path(list(unique.values()))


if __name__ == "__main__":
    result = asyncio.run(KolesaDaromScraper().run())
    print(f"Parsed {len(result)} products from {KolesaDaromScraper.site_name}")
