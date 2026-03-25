from __future__ import annotations

import json
import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd

from ai_analysis.price_analyzer import PriceAnalyzer
from ai_analysis.recommendation_engine import RecommendationEngine


class _FakeCache:
    def __init__(self):
        self.storage = {}

    async def get_json(self, key: str):
        return self.storage.get(key)

    async def set_json(self, key: str, payload: dict, ttl_seconds: int):
        self.storage[key] = payload

    async def close(self):
        return None


def _sample_df() -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    return pd.DataFrame(
        [
            {
                "scraped_at": now - timedelta(days=8),
                "site_name": "site_a",
                "product_id": 1,
                "brand": "Yokohama",
                "model": "IG55",
                "size": "205/60",
                "radius": "R16",
                "product_name": "Yokohama IG55 205/60R16",
                "url": "https://x/a",
                "price": 7000.0,
                "old_price": 7200.0,
            },
            {
                "scraped_at": now - timedelta(days=1),
                "site_name": "site_b",
                "product_id": 1,
                "brand": "Yokohama",
                "model": "IG55",
                "size": "205/60",
                "radius": "R16",
                "product_name": "Yokohama IG55 205/60R16",
                "url": "https://x/b",
                "price": 6300.0,
                "old_price": 7000.0,
            },
            {
                "scraped_at": now,
                "site_name": "site_a",
                "product_id": 1,
                "brand": "Yokohama",
                "model": "IG55",
                "size": "205/60",
                "radius": "R16",
                "product_name": "Yokohama IG55 205/60R16",
                "url": "https://x/a",
                "price": 6200.0,
                "old_price": 6300.0,
            },
        ]
    )


def test_price_analyzer_trends_and_anomalies():
    analyzer = PriceAnalyzer()
    df = _sample_df()
    trends = analyzer.calculate_trends(df)
    anomalies = analyzer.find_price_anomalies(df)

    assert trends["current_price"] == 6200.0
    assert trends["cheapest_site"] in {"site_a", "site_b"}
    assert trends["trend_direction"] in {"falling", "stable", "rising"}
    assert isinstance(anomalies, list)


def test_recommendation_engine_buy_recommendation_with_mock(monkeypatch):
    engine = RecommendationEngine(llm_provider="openai")
    engine.cache = _FakeCache()

    async def _fake_compare_sites(*args, **kwargs):
        return pd.DataFrame(
            [
                {"site_name": "site_a", "current_price": 6200.0, "last_updated": "2026-01-01", "url": "https://x/a"},
                {"site_name": "site_b", "current_price": 6400.0, "last_updated": "2026-01-01", "url": "https://x/b"},
            ]
        )

    async def _fake_invoke(prompt: str, fallback_text: str):
        return (
            json.dumps(
                {"optimal_price": 6190, "margin_price": 6500, "reasoning": "mock"},
                ensure_ascii=False,
            ),
            42,
        )

    monkeypatch.setattr(engine.analyzer, "compare_sites", _fake_compare_sites)
    monkeypatch.setattr(engine, "_invoke_llm", _fake_invoke)

    payload = json.loads(asyncio.run(engine.get_buy_recommendation("Yokohama", "IG55", "205/60")))
    assert payload["optimal_price"] == 6190
    assert payload["margin_price"] == 6500
