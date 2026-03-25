from __future__ import annotations

import asyncio
from dataclasses import dataclass

import scheduler.tasks as task_module
from scrapers.schemas import ProductDTO


@dataclass
class _Store:
    site: object | None = None
    run: object | None = None
    run_id: int = 1


class _FakeSession:
    def __init__(self, store: _Store):
        self.store = store

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, obj):
        if obj.__class__.__name__ == "Site":
            obj.id = 1
            self.store.site = obj
        if obj.__class__.__name__ == "ParseRun":
            obj.id = self.store.run_id
            self.store.run = obj

    async def scalar(self, stmt):
        text = str(stmt)
        if "FROM sites" in text:
            return self.store.site
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def get(self, model, pk):
        if model.__name__ == "ParseRun":
            return self.store.run
        return None


class _FakeScraperSuccess:
    base_url = "https://example.com"
    catalog_url = "https://example.com/catalog"

    async def run(self):
        return [
            ProductDTO(
                external_id="ext-1",
                name="Yokohama IG55 175/65R14",
                brand="Yokohama",
                model="IG55",
                season="winter",
                tire_size="175/65",
                radius="R14",
                width=175,
                profile=65,
                diameter=14,
                price=5599.0,
                old_price=6200.0,
                discount_pct=9.69,
                in_stock=True,
                url="https://example.com/p1",
                site_name="test_site",
            )
        ]


class _FakeScraperFail(_FakeScraperSuccess):
    async def run(self):
        raise RuntimeError("scrape failed")


def test__run_scrape_site_updates_parse_run_success(monkeypatch):
    store = _Store()

    monkeypatch.setattr(task_module, "AsyncSessionLocal", lambda: _FakeSession(store))
    monkeypatch.setitem(task_module.SCRAPERS_REGISTRY, "test_site", _FakeScraperSuccess)

    async def _fake_upsert(*args, **kwargs):
        return None

    monkeypatch.setattr(task_module, "upsert_product", _fake_upsert)

    result = asyncio.run(task_module._run_scrape_site("test_site"))

    assert result["status"] == "success"
    assert store.run is not None
    assert store.run.status == "success"
    assert store.run.products_found == 1


def test__run_scrape_site_updates_parse_run_failed(monkeypatch):
    store = _Store()

    monkeypatch.setattr(task_module, "AsyncSessionLocal", lambda: _FakeSession(store))
    monkeypatch.setitem(task_module.SCRAPERS_REGISTRY, "test_site_fail", _FakeScraperFail)

    async def _fake_upsert(*args, **kwargs):
        return None

    monkeypatch.setattr(task_module, "upsert_product", _fake_upsert)

    try:
        asyncio.run(task_module._run_scrape_site("test_site_fail"))
    except RuntimeError:
        pass

    assert store.run is not None
    assert store.run.status == "failed"
    assert store.run.errors_count == 1


def test_scrape_site_task_uses_asyncio_run(monkeypatch):
    payload = {"site_name": "x", "status": "success", "products_found": 0}

    def _fake_run(coro):
        coro.close()
        return payload

    monkeypatch.setattr(task_module.asyncio, "run", _fake_run)
    result = task_module.scrape_site.run("shinservice")
    assert result == payload
