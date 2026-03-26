from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import func, select

from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, PriceHistory, Product, Site


router = APIRouter()
PRICE_ALERT_TYPES = ("price_drop", "price_rise", "price_changed", "new_low")


def _safe_to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


@router.get("/overview")
async def get_overview() -> dict:
    async with AsyncSessionLocal() as session:
        products_count = int(
            await session.scalar(
                select(func.count(Product.id)).join(Site, Site.id == Product.site_id).where(Site.is_active.is_(True))
            )
            or 0
        )
        active_sites = int(await session.scalar(select(func.count(Site.id)).where(Site.is_active.is_(True))) or 0)
        changes_24h = int(
            await session.scalar(
                select(func.count(Alert.id))
                .join(Product, Product.id == Alert.product_id)
                .join(Site, Site.id == Product.site_id)
                .where(
                    Alert.alert_type.in_(PRICE_ALERT_TYPES),
                    Alert.triggered_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                    Site.is_active.is_(True),
                )
            )
            or 0
        )
        unread_alerts = int(
            await session.scalar(
                select(func.count(Alert.id))
                .join(Product, Product.id == Alert.product_id)
                .join(Site, Site.id == Product.site_id)
                .where(
                    Alert.sent_at.is_(None),
                    Alert.alert_type.in_(PRICE_ALERT_TYPES),
                    Site.is_active.is_(True),
                )
            )
            or 0
        )
    return {
        "products_count": products_count,
        "active_sites": active_sites,
        "changes_24h": changes_24h,
        "unread_alerts": unread_alerts,
    }


@router.get("/price-changes")
async def get_price_changes(days: int = 30) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Alert.id, Alert.product_id, Alert.old_value, Alert.new_value, Alert.triggered_at, Product.name, Site.name)
            .join(Product, Product.id == Alert.product_id)
            .join(Site, Site.id == Product.site_id)
            .where(
                Alert.alert_type.in_(PRICE_ALERT_TYPES),
                Alert.triggered_at >= cutoff,
                Site.is_active.is_(True),
            )
            .order_by(Alert.triggered_at.desc())
            .limit(200)
        )
        rows = (await session.execute(stmt)).all()
        payload = []
        for row in rows:
            old_v = _safe_to_float(row[2])
            new_v = _safe_to_float(row[3])
            change_pct = 0.0
            if old_v is not None and new_v is not None and old_v != 0:
                change_pct = round((new_v - old_v) / old_v * 100, 2)
            payload.append(
                {
                    "alert_id": row[0],
                    "product_id": row[1],
                    "old_price": old_v,
                    "new_price": new_v,
                    "change_pct": change_pct,
                    "triggered_at": row[4],
                    "product_name": row[5],
                    "site_name": row[6],
                }
            )
        return payload


@router.get("/best-deals")
async def get_best_deals(limit: int = 5) -> list[dict]:
    async with AsyncSessionLocal() as session:
        latest_price_subq = (
            select(
                PriceHistory.product_id.label("product_id"),
                func.max(PriceHistory.scraped_at).label("last_scraped_at"),
            )
            .group_by(PriceHistory.product_id)
            .subquery()
        )
        stmt = (
            select(Product.id, Product.name, Product.url, PriceHistory.price, PriceHistory.old_price, Site.name)
            .join(latest_price_subq, latest_price_subq.c.product_id == Product.id)
            .join(
                PriceHistory,
                (PriceHistory.product_id == latest_price_subq.c.product_id)
                & (PriceHistory.scraped_at == latest_price_subq.c.last_scraped_at),
            )
            .join(Site, Site.id == Product.site_id)
            .where(PriceHistory.old_price.is_not(None), PriceHistory.old_price > PriceHistory.price, Site.is_active.is_(True))
            .order_by((PriceHistory.old_price - PriceHistory.price).desc())
            .limit(max(limit * 3, 10))
        )
        rows = (await session.execute(stmt)).all()
        unique_payload: list[dict] = []
        seen_product_ids: set[int] = set()
        for row in rows:
            product_id = int(row[0])
            if product_id in seen_product_ids:
                continue
            seen_product_ids.add(product_id)
            unique_payload.append(
                {
                    "product_id": product_id,
                    "name": row[1],
                    "url": row[2],
                    "price": float(row[3]),
                    "old_price": float(row[4]) if row[4] is not None else None,
                    "discount_pct": round((float(row[4]) - float(row[3])) / float(row[4]) * 100, 2) if row[4] else 0.0,
                    "site_name": row[5],
                }
            )
            if len(unique_payload) >= limit:
                break
        return unique_payload


@router.get("/weekly-report")
async def get_weekly_report() -> dict:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await redis.get("ai:weekly_report")
        return {"report": raw or ""}
    finally:
        await redis.aclose()


@router.get("/site-stats")
async def get_site_stats() -> list[dict]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Site.name, func.count(Product.id), func.min(PriceHistory.price), func.max(PriceHistory.price))
            .join(Product, Product.site_id == Site.id, isouter=True)
            .join(PriceHistory, PriceHistory.product_id == Product.id, isouter=True)
            .where(Site.is_active.is_(True))
            .group_by(Site.name)
            .order_by(Site.name.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "site_name": row[0],
                "products_count": int(row[1] or 0),
                "min_price": float(row[2]) if row[2] is not None else None,
                "max_price": float(row[3]) if row[3] is not None else None,
            }
            for row in rows
        ]
