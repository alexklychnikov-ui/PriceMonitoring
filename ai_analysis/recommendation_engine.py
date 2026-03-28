from __future__ import annotations

import json
import logging
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

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

_IRKUTSK_TZ = ZoneInfo("Asia/Irkutsk")

_INVALID_OPENAI_KEYS = frozenset(
    {
        "",
        "replace_me",
        "change_me",
        "your_proxyapi_key",
        "xxx",
    }
)


def _openai_api_key_invalid(key: str) -> bool:
    return (key or "").strip().lower() in _INVALID_OPENAI_KEYS


def _format_report_period_label() -> str:
    now = datetime.now(_IRKUTSK_TZ)
    end_d = now.date()
    start_d = end_d - timedelta(days=7)
    return f"{start_d.strftime('%d.%m.%Y')}—{end_d.strftime('%d.%m.%Y')} (Иркутск, 7 дн.)"


def _pct_change(old_s: str | None, new_s: str | None) -> float | None:
    try:
        old_p = Decimal(str(old_s))
        new_p = Decimal(str(new_s))
    except (ArithmeticError, TypeError, ValueError):
        return None
    if old_p <= 0:
        return None
    return float((new_p - old_p) / old_p * Decimal("100"))


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
        if self.llm_provider == "openai" and _openai_api_key_invalid(settings.PROXY_API_KEY):
            logger.warning("LLM skipped: PROXY_API_KEY empty or placeholder")
            note = (
                "\n\n### LLM\n"
                "Сейчас `PROXY_API_KEY` пустой или заглушка (`REPLACE_ME` / `change_me`).\n"
                "1) Ключ: https://proxyapi.ru\n"
                "2) В `deploy/.env` замени строку `PROXY_API_KEY=...` (compose подставляет её в контейнеры).\n"
                "3) Дублируй то же значение в корневом `price_monitor/.env`, если запускаешь без Docker.\n"
                "4) `docker compose -f deploy/docker-compose.prod.yml up -d telegram_bot worker api`\n"
                "Сеть до proxyapi.ru из контейнера есть; 401 от API = неверный ключ."
            )
            return fallback_text + note, 0
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

    async def _weekly_moves_from_alerts(self, session, since: datetime) -> tuple[float, float, str, str]:
        rows = (
            await session.execute(
                select(Alert, Product.id, Product.name, Site.name)
                .join(Product, Product.id == Alert.product_id)
                .join(Site, Site.id == Product.site_id)
                .where(
                    Site.is_active.is_(True),
                    Alert.triggered_at >= since,
                    Alert.alert_type.in_(["price_drop", "price_rise"]),
                )
                .order_by(Alert.triggered_at.desc())
                .limit(800)
            )
        ).all()

        Row = tuple[float, int, str, str, str, str]

        best_drop: dict[int, Row] = {}
        best_rise: dict[int, Row] = {}
        for alert, product_id, pname, sname in rows:
            pct = _pct_change(alert.old_value, alert.new_value)
            if pct is None:
                continue
            name = (pname or "")[:80]
            site = (sname or "")[:32]
            old_v = str(alert.old_value or "")
            new_v = str(alert.new_value or "")
            row: Row = (pct, int(product_id), name, site, old_v, new_v)
            if alert.alert_type == "price_drop":
                if pct >= 0:
                    continue
                cur = best_drop.get(int(product_id))
                if cur is None or pct < cur[0]:
                    best_drop[int(product_id)] = row
            else:
                if pct <= 0:
                    continue
                cur = best_rise.get(int(product_id))
                if cur is None or pct > cur[0]:
                    best_rise[int(product_id)] = row

        for pid in list(best_drop.keys() & best_rise.keys()):
            d_pct = best_drop[pid][0]
            r_pct = best_rise[pid][0]
            if abs(r_pct) >= abs(d_pct):
                del best_drop[pid]
            else:
                del best_rise[pid]

        drops = sorted(best_drop.values(), key=lambda x: x[0])
        rises = sorted(best_rise.values(), key=lambda x: x[0], reverse=True)
        top_d, top_r = drops[:5], rises[:5]

        def _lines(items: list[Row]) -> str:
            return "\n".join(f"- {n} ({s}): {o}→{nv} ₽ ({p:+.2f}%)" for p, _pid, n, s, o, nv in items)

        avg_dec = float(statistics.mean(abs(x[0]) for x in drops)) if drops else 0.0
        avg_inc = float(statistics.mean(x[0] for x in rises)) if rises else 0.0
        disc = _lines(top_d) if top_d else "Нет снижений выше порога алертов за период."
        inc_str = _lines(top_r) if top_r else "Нет повышений выше порога алертов за период."
        return avg_dec, avg_inc, disc, inc_str

    async def generate_weekly_report(self, force_refresh: bool = False) -> str:
        cache_key = "ai:weekly_report"
        if not force_refresh:
            cached = await self.cache.get_json(cache_key)
            if cached and "report" in cached:
                return str(cached["report"])

        week = _format_report_period_label()
        async with AsyncSessionLocal() as session:
            sites_count = int(await session.scalar(select(func.count(Site.id)).where(Site.is_active.is_(True))) or 0)
            products_count = int(
                await session.scalar(
                    select(func.count(Product.id)).join(Site, Site.id == Product.site_id).where(Site.is_active.is_(True))
                )
                or 0
            )
            since = datetime.now(timezone.utc) - timedelta(days=7)
            price_changes = int(
                await session.scalar(
                    select(func.count(Alert.id)).where(
                        Alert.product_id.in_(
                            select(Product.id).join(Site, Site.id == Product.site_id).where(Site.is_active.is_(True))
                        ),
                        Alert.alert_type.in_(["price_drop", "price_rise", "price_changed"]),
                        Alert.triggered_at >= since,
                    )
                )
                or 0
            )
            avg_decrease, avg_increase, top_discounts, top_increases = await self._weekly_moves_from_alerts(session, since)

        prompt = MARKET_OVERVIEW_PROMPT.format(
            sites_count=sites_count,
            products_count=products_count,
            price_changes_count=price_changes,
            avg_decrease=round(avg_decrease, 2),
            avg_increase=round(avg_increase, 2),
            top_discounts=top_discounts,
            top_increases=top_increases,
            week=week,
        )
        fallback = (
            f"## Обзор рынка шин Иркутск — {week}\n"
            f"### Сводка\n"
            f"- Сайтов: {sites_count}, товаров в мониторинге: {products_count}\n"
            f"- Алертов об изменении цены за 7 дн.: {price_changes}\n"
            f"- Средняя величина снижения (по алертам): {round(avg_decrease, 2)}%\n"
            f"- Средняя величина повышения (по алертам): {round(avg_increase, 2)}%\n"
            f"### Крупнейшие снижения\n{top_discounts}\n"
            f"### Крупнейшие повышения\n{top_increases}\n"
            f"### Примечание\n"
            f"Ниже — данные из БД; связный текст отчёта даёт LLM при успешном ответе API."
        )
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
