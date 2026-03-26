from __future__ import annotations

import asyncio
from pathlib import Path

from scrapers.avtoshina38 import Avtoshina38Scraper
from scrapers.express_shina import ExpressShinaScraper
from scrapers.kolesa_darom import KolesaDaromScraper
from scrapers.ship_ship import ShipShipScraper
from scrapers.shinapoint import ShinapointScraper
from scrapers.shinservice import ShinserviceScraper
from scrapers.supershina38 import Supershina38Scraper
from scrapers.utils import clean_price, parse_tire_size, split_brand_model


FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _run_parse(scraper, fixture_name: str):
    html = _read_fixture(fixture_name)
    return asyncio.run(scraper.parse_products(html))


def test_parse_tire_size_formats():
    a = parse_tire_size("Yokohama IG55 175/65R14 86T")
    b = parse_tire_size("Nokian 205/60 R16")
    c = parse_tire_size("Pirelli 225/45r18")
    assert a is not None and a.tire_size == "175/65" and a.radius == "R14"
    assert b is not None and b.width == 205 and b.profile == 60 and b.diameter == 16
    assert c is not None and c.radius == "R18"


def test_clean_price_edges():
    assert clean_price("5 599.81 ₽") == 5599.81
    assert clean_price("6 300 ₽") == 6300.0
    assert clean_price("17,840 ₽") == 17840.0
    assert clean_price("") is None
    assert clean_price("N/A") is None


def test_split_brand_model_with_shina_prefix():
    brand, model = split_brand_model("Легковая шина Н.Камск Кама Евро 519 185/60 R14 82T")
    assert brand == "Кама"
    assert model.startswith("Евро 519")


def test_split_brand_model_regular_brand():
    brand, model = split_brand_model("Легковая шина Pirelli Scorpion Ice Zero 2 225/55 R19")
    assert brand == "Pirelli"
    assert model.startswith("Scorpion Ice Zero 2")


def test_avtoshina_parse_products():
    items = _run_parse(Avtoshina38Scraper(), "avtoshina38.html")
    assert len(items) == 1
    assert items[0].site_name == "avtoshina38"


def test_shinservice_parse_products():
    items = _run_parse(ShinserviceScraper(), "shinservice.html")
    assert len(items) == 1
    assert items[0].site_name == "shinservice"


def test_shinapoint_parse_products():
    items = _run_parse(ShinapointScraper(), "shinapoint.html")
    assert len(items) == 1
    assert items[0].site_name == "shinapoint"


def test_ship_ship_parse_products():
    items = _run_parse(ShipShipScraper(), "ship_ship.html")
    assert len(items) == 1
    assert items[0].site_name == "ship_ship"


def test_supershina_parse_products():
    items = _run_parse(Supershina38Scraper(), "supershina38.html")
    assert len(items) == 1
    assert items[0].site_name == "supershina38"


def test_express_parse_products():
    items = _run_parse(ExpressShinaScraper(), "express_shina.html")
    assert len(items) == 1
    assert items[0].site_name == "express_shina"


def test_kolesa_darom_parse_products():
    items = _run_parse(KolesaDaromScraper(), "kolesa_darom.html")
    assert len(items) == 1
    assert items[0].site_name == "kolesa_darom"
