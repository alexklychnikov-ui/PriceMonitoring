from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select

from db.database import AsyncSessionLocal
from db.models import PriceHistory, Product, Site


class PriceAnalyzer:
    async def get_price_history_df(
        self,
        product_id: int | None = None,
        brand: str | None = None,
        days: int = 30,
    ) -> pd.DataFrame:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                PriceHistory.scraped_at,
                Site.name.label("site_name"),
                Product.id.label("product_id"),
                Product.brand,
                Product.model,
                Product.tire_size.label("size"),
                Product.radius,
                Product.name.label("product_name"),
                Product.url,
                PriceHistory.price,
                PriceHistory.old_price,
            )
            .join(Product, Product.id == PriceHistory.product_id)
            .join(Site, Site.id == Product.site_id)
            .where(PriceHistory.scraped_at >= cutoff, Site.is_active.is_(True))
            .order_by(PriceHistory.scraped_at.asc())
        )
        if product_id is not None:
            stmt = stmt.where(Product.id == product_id)
        if brand:
            stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))

        async with AsyncSessionLocal() as session:
            rows = (await session.execute(stmt)).all()

        if not rows:
            return pd.DataFrame(
                columns=["scraped_at", "site_name", "product_id", "brand", "model", "size", "radius", "product_name", "url", "price", "old_price"]
            )
        df = pd.DataFrame(rows)
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
        df["price"] = pd.to_numeric(df["price"])
        df["old_price"] = pd.to_numeric(df["old_price"], errors="coerce")
        return df

    def calculate_trends(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {
                "min_price": 0.0,
                "max_price": 0.0,
                "avg_price": 0.0,
                "current_price": 0.0,
                "price_change_7d_pct": 0.0,
                "price_change_30d_pct": 0.0,
                "volatility": 0.0,
                "trend_direction": "stable",
                "cheapest_site": "",
                "price_spread": 0.0,
            }

        sorted_df = df.sort_values("scraped_at")
        prices = sorted_df["price"].astype(float)
        current_price = float(prices.iloc[-1])
        min_price = float(prices.min())
        max_price = float(prices.max())
        avg_price = float(prices.mean())
        volatility = float(prices.std(ddof=0) / avg_price) if avg_price else 0.0

        now = sorted_df["scraped_at"].max()
        price_7d_df = sorted_df[sorted_df["scraped_at"] <= (now - pd.Timedelta(days=7))]
        price_30d_df = sorted_df[sorted_df["scraped_at"] <= (now - pd.Timedelta(days=30))]
        base_7d = float(price_7d_df["price"].iloc[-1]) if not price_7d_df.empty else float(prices.iloc[0])
        base_30d = float(price_30d_df["price"].iloc[-1]) if not price_30d_df.empty else float(prices.iloc[0])

        def _change_pct(current: float, base: float) -> float:
            if not base:
                return 0.0
            return round((current - base) / base * 100, 2)

        change_7d = _change_pct(current_price, base_7d)
        change_30d = _change_pct(current_price, base_30d)

        if change_7d > 3:
            trend = "rising"
        elif change_7d < -3:
            trend = "falling"
        else:
            trend = "stable"

        latest = sorted_df.sort_values("scraped_at").groupby("site_name", as_index=False).tail(1)
        cheapest_row = latest.sort_values("price").iloc[0]
        cheapest_site = str(cheapest_row["site_name"])
        min_current = float(latest["price"].min())
        max_current = float(latest["price"].max())
        spread = round(((max_current - min_current) / min_current * 100), 2) if min_current else 0.0

        return {
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "avg_price": round(avg_price, 2),
            "current_price": round(current_price, 2),
            "price_change_7d_pct": change_7d,
            "price_change_30d_pct": change_30d,
            "volatility": round(volatility, 4),
            "trend_direction": trend,
            "cheapest_site": cheapest_site,
            "price_spread": spread,
        }

    def find_price_anomalies(self, df: pd.DataFrame) -> list[dict]:
        if df.empty:
            return []
        anomalies: list[dict] = []
        sorted_df = df.sort_values(["product_id", "scraped_at"]).copy()
        sorted_df["prev_price"] = sorted_df.groupby("product_id")["price"].shift(1)
        sorted_df["day_change_pct"] = ((sorted_df["price"] - sorted_df["prev_price"]) / sorted_df["prev_price"]) * 100
        stats_mean = float(sorted_df["price"].mean())
        stats_std = float(sorted_df["price"].std(ddof=0))
        if stats_std:
            sorted_df["zscore"] = (sorted_df["price"] - stats_mean) / stats_std
        else:
            sorted_df["zscore"] = 0.0

        for _, row in sorted_df.iterrows():
            if pd.isna(row["day_change_pct"]):
                continue
            reasons: list[str] = []
            day_change = float(row["day_change_pct"])
            if day_change <= -20:
                reasons.append("drop_gt_20pct_1d")
            if day_change >= 30:
                reasons.append("rise_gt_30pct_1d")
            if float(row["price"]) <= stats_mean * 0.7:
                reasons.append("below_market_avg_30pct")
            if abs(float(row["zscore"])) >= 2.5:
                reasons.append("zscore_outlier")
            if reasons:
                anomalies.append(
                    {
                        "scraped_at": row["scraped_at"].isoformat(),
                        "site_name": row["site_name"],
                        "product_id": int(row["product_id"]),
                        "price": float(row["price"]),
                        "day_change_pct": round(day_change, 2),
                        "reasons": reasons,
                    }
                )
        return anomalies

    async def compare_sites(self, brand: str, model: str, size: str) -> pd.DataFrame:
        df = await self.get_price_history_df(brand=brand, days=30)
        if df.empty:
            return pd.DataFrame(columns=["site_name", "current_price", "last_updated", "url"])

        filtered = df[
            (df["brand"].str.lower() == brand.lower())
            & (df["model"].str.lower() == model.lower())
            & (df["size"].str.lower() == size.lower())
        ]
        if filtered.empty:
            return pd.DataFrame(columns=["site_name", "current_price", "last_updated", "url"])

        latest_rows = filtered.sort_values("scraped_at").groupby("site_name", as_index=False).tail(1)
        result = latest_rows[["site_name", "price", "scraped_at", "url"]].copy()
        result.columns = ["site_name", "current_price", "last_updated", "url"]
        result["current_price"] = pd.to_numeric(result["current_price"]).round(2)
        return result.sort_values("current_price").reset_index(drop=True)
