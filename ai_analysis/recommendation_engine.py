from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI
from sqlalchemy import func, select

from ai_analysis.cache import AnalysisCache
from ai_analysis.price_analyzer import PriceAnalyzer
from ai_analysis.prompts import MARKET_OVERVIEW_PROMPT, PRICE_TREND_ANALYSIS_PROMPT, PRICING_RECOMMENDATION_PROMPT
from ai_analysis.reports import format_sites_comparison, safe_json_loads
from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, ParseRun, PriceHistory, Product, Site


logger = logging.getLogger(__name__)


@dataclass
class PriceAnalysisResult:
    product_id: int
    product_name: str
    trend_stats: dict[str, Any]
    anomalies: list[dict[str, Any]]
    ai_summary: str
    tokens_used: int
    created_at: str


class RecommendationEngine:
    def __init__(self, llm_provider: str | None = None):
        self.llm_provider = (llm_provider or settings.LLM_PROVIDER).lower()
        self.analyzer = PriceAnalyzer()
        self.cache = AnalysisCache()

    def _get_llm(self):
        if self.llm_provider == "openai":
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.PROXY_API_KEY,
                base_url=settings.PROXY_BASE_URL,
                temperature=0.2,
            )
        return Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    async def _invoke_llm(self, prompt: str, fallback_text: str) -> tuple[str, int]:
        llm = self._get_llm()
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = getattr(response, "content", "") or str(response)
            token_usage = 0
            usage_meta = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {})
            if isinstance(usage_meta, dict):
                token_usage = int(usage_meta.get("total_tokens", 0) or usage_meta.get("token_usage", {}).get("total_tokens", 0) or 0)
            logger.info("LLM call provider=%s tokens_used=%s", self.llm_provider, token_usage)
            return content, token_usage
        except Exception as error:
            logger.warning("LLM fallback provider=%s error=%s", self.llm_provider, type(error).__name__)
            return fallback_text, 0

    async def analyze_product_price(self, product_id: int) -> PriceAnalysisResult:
        cache_key = f"ai:analyze_product:{product_id}"
        cached = await self.cache.get_json(cache_key)
        if cached:
            return PriceAnalysisResult(**cached)

        df = await self.analyzer.get_price_history_df(product_id=product_id, days=30)
        if df.empty:
            result = PriceAnalysisResult(
                product_id=product_id,
                product_name="unknown",
                trend_stats={},
                anomalies=[],
                ai_summary="Недостаточно данных для анализа.",
                tokens_used=0,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await self.cache.set_json(cache_key, asdict(result), ttl_seconds=3600)
            return result

        trend_stats = self.analyzer.calculate_trends(df)
        anomalies = self.analyzer.find_price_anomalies(df)
        first = df.iloc[-1]
        compare_df = await self.analyzer.compare_sites(
            brand=str(first["brand"]),
            model=str(first["model"]),
            size=str(first["size"]),
        )
        prompt = PRICE_TREND_ANALYSIS_PROMPT.format(
            product_name=str(first["product_name"]),
            brand=str(first["brand"]),
            model=str(first["model"]),
            radius=str(first["radius"]),
            days=30,
            current_price=trend_stats.get("current_price", 0),
            min_price=trend_stats.get("min_price", 0),
            min_site=trend_stats.get("cheapest_site", ""),
            max_price=trend_stats.get("max_price", 0),
            max_site="market",
            change_7d=trend_stats.get("price_change_7d_pct", 0),
            change_30d=trend_stats.get("price_change_30d_pct", 0),
            volatility=trend_stats.get("volatility", 0),
            trend_direction=trend_stats.get("trend_direction", "stable"),
            price_spread=trend_stats.get("price_spread", 0),
            sites_comparison=format_sites_comparison(compare_df),
        )
        fallback = "Цены выглядят стабильными. Рекомендуется сверить минимум по площадкам и проверить наличие акции."
        summary, tokens = await self._invoke_llm(prompt, fallback)

        result = PriceAnalysisResult(
            product_id=product_id,
            product_name=str(first["product_name"]),
            trend_stats=trend_stats,
            anomalies=anomalies,
            ai_summary=summary,
            tokens_used=tokens,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await self.cache.set_json(cache_key, asdict(result), ttl_seconds=3600)
        return result

    async def generate_weekly_report(self) -> str:
        cache_key = "ai:weekly_report"
        cached = await self.cache.get_json(cache_key)
        if cached and "report" in cached:
            return str(cached["report"])

        week = datetime.now(timezone.utc).strftime("%Y-%W")
        async with AsyncSessionLocal() as session:
            sites_count = int(await session.scalar(select(func.count(Site.id))) or 0)
            products_count = int(await session.scalar(select(func.count(Product.id))) or 0)
            since = datetime.now(timezone.utc) - timedelta(days=7)
            price_changes = int(
                await session.scalar(
                    select(func.count(Alert.id)).where(
                        Alert.alert_type.in_(["price_drop", "price_rise", "price_changed"]),
                        Alert.triggered_at >= since,
                    )
                )
                or 0
            )
        prompt = MARKET_OVERVIEW_PROMPT.format(
            sites_count=sites_count,
            products_count=products_count,
            price_changes_count=price_changes,
            avg_decrease=0.0,
            avg_increase=0.0,
            top_discounts="Нет данных",
            top_increases="Нет данных",
            week=week,
        )
        fallback = f"## Обзор рынка шин Иркутск — {week}\n### Ключевые тренды\nДанных пока недостаточно.\n### Лучшие предложения недели\nНет данных.\n### На что обратить внимание\nПродолжайте накопление истории."
        report, tokens = await self._invoke_llm(prompt, fallback)
        logger.info("Weekly report tokens_used=%s", tokens)
        await self.cache.set_json(cache_key, {"report": report}, ttl_seconds=86400)
        return report

    async def get_buy_recommendation(self, brand: str, model: str, size: str) -> str:
        cache_key = f"ai:buy_reco:{brand}:{model}:{size}"
        cached = await self.cache.get_json(cache_key)
        if cached and "recommendation" in cached:
            return str(cached["recommendation"])

        compare_df = await self.analyzer.compare_sites(brand=brand, model=model, size=size)
        if compare_df.empty:
            fallback = {"optimal_price": None, "margin_price": None, "reasoning": "Недостаточно данных по конкурентам."}
            payload = json.dumps(fallback, ensure_ascii=False)
            await self.cache.set_json(cache_key, {"recommendation": payload}, ttl_seconds=7200)
            return payload

        competitor_prices = "\n".join(
            f"{row['site_name']}: {row['current_price']} ₽" for _, row in compare_df.iterrows()
        )
        our_price = float(compare_df.iloc[0]["current_price"])
        prompt = PRICING_RECOMMENDATION_PROMPT.format(
            product_name=f"{brand} {model} {size}",
            competitor_prices=competitor_prices,
            our_price=our_price,
            our_rank=1,
            total_sites=len(compare_df),
        )
        fallback_json = json.dumps(
            {
                "optimal_price": round(our_price * 0.99, 2),
                "margin_price": round(our_price * 1.03, 2),
                "reasoning": "Выбрано на базе минимальной текущей рыночной цены.",
            },
            ensure_ascii=False,
        )
        content, tokens = await self._invoke_llm(prompt, fallback_json)
        logger.info("Buy recommendation tokens_used=%s", tokens)
        parsed = safe_json_loads(content)
        payload = json.dumps(parsed, ensure_ascii=False)
        await self.cache.set_json(cache_key, {"recommendation": payload}, ttl_seconds=7200)
        return payload

    async def close(self) -> None:
        await self.cache.close()
