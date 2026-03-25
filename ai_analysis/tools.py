from __future__ import annotations

import json

from langchain_core.tools import tool

from ai_analysis.price_analyzer import PriceAnalyzer
from ai_analysis.recommendation_engine import RecommendationEngine


@tool
async def get_price_for_tire(brand: str, model: str, size: str) -> str:
    analyzer = PriceAnalyzer()
    df = await analyzer.compare_sites(brand=brand, model=model, size=size)
    if df.empty:
        return "Нет данных по этой шине."
    payload = df.to_dict(orient="records")
    return json.dumps(payload, ensure_ascii=False)


@tool
async def get_price_history(brand: str, model: str, size: str, days: int = 30) -> str:
    analyzer = PriceAnalyzer()
    df = await analyzer.get_price_history_df(brand=brand, days=days)
    filtered = df[
        (df["brand"].str.lower() == brand.lower())
        & (df["model"].str.lower() == model.lower())
        & (df["size"].str.lower() == size.lower())
    ]
    if filtered.empty:
        return "История цен не найдена."
    return filtered.to_json(orient="records", force_ascii=False, date_format="iso")


@tool
async def get_market_overview() -> str:
    engine = RecommendationEngine()
    try:
        return await engine.generate_weekly_report()
    finally:
        await engine.close()


@tool
async def find_best_deals(season: str = "winter", budget: float = 10000) -> str:
    analyzer = PriceAnalyzer()
    df = await analyzer.get_price_history_df(days=7)
    if df.empty:
        return "Нет данных по рынку."
    latest = df.sort_values("scraped_at").groupby("product_id", as_index=False).tail(1)
    filtered = latest[(latest["price"] <= budget) & (latest["product_name"].str.lower().str.contains(season.lower(), na=False))]
    if filtered.empty:
        return "Под заданные параметры предложений не найдено."
    deals = filtered.sort_values("price")[["product_name", "site_name", "price", "url"]].head(20)
    return deals.to_json(orient="records", force_ascii=False)
