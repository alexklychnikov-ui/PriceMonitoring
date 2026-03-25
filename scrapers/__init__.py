from scrapers.avtoshina38 import Avtoshina38Scraper
from scrapers.base import BaseScraper
from scrapers.express_shina import ExpressShinaScraper
from scrapers.kolesa_darom import KolesaDaromScraper
from scrapers.ship_ship import ShipShipScraper
from scrapers.shinapoint import ShinapointScraper
from scrapers.shinservice import ShinserviceScraper
from scrapers.supershina38 import Supershina38Scraper

SCRAPERS_REGISTRY: dict[str, type[BaseScraper]] = {
    "avtoshina38": Avtoshina38Scraper,
    "shinservice": ShinserviceScraper,
    "shinapoint": ShinapointScraper,
    "ship_ship": ShipShipScraper,
    "supershina38": Supershina38Scraper,
    "express_shina": ExpressShinaScraper,
    "kolesa_darom": KolesaDaromScraper,
}

__all__ = ["BaseScraper", "SCRAPERS_REGISTRY"]
