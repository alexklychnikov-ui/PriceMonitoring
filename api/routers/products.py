from __future__ import annotations

from decimal import Decimal

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import desc, func, or_, select

from ai_analysis.recommendation_engine import RecommendationEngine
from api.schemas import PriceHistoryPoint, ProductOut
from config import settings
from db.database import AsyncSessionLocal
from db.models import PriceHistory, Product, Site, UserSubscription


def _latest_price_subquery():
    rn = func.row_number().over(
        partition_by=PriceHistory.product_id,
        order_by=desc(PriceHistory.scraped_at),
    ).label("rn")
    inner = (
        select(
            PriceHistory.product_id.label("product_id"),
            PriceHistory.price.label("last_price"),
            PriceHistory.in_stock.label("last_in_stock"),
            PriceHistory.scraped_at.label("last_ts"),
            rn,
        )
    ).subquery()
    return (
        select(
            inner.c.product_id,
            inner.c.last_price,
            inner.c.last_in_stock,
            inner.c.last_ts,
        ).where(inner.c.rn == 1)
    ).subquery()


router = APIRouter()

_ANY_PRICE_THRESHOLD = Decimal("0")


def _subscription_target_chat_id() -> str:
    cid = (settings.TELEGRAM_CHAT_ID or "").strip()
    if not cid:
        raise HTTPException(status_code=503, detail="TELEGRAM_CHAT_ID is not configured")
    return cid


def _require_subscription_web_key(request: Request) -> None:
    expected = (settings.SUBSCRIPTION_WEB_KEY or "").strip()
    if not expected:
        return
    got = (request.headers.get("X-Subscription-Key") or "").strip()
    if got != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Subscription-Key")


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


@router.get("")
async def get_products(
    brand: str | None = None,
    season: str | None = None,
    width: int | None = None,
    profile: int | None = None,
    diameter: int | None = None,
    site_name: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    sort_by: str = "price",
    tire_size: str | None = None,
    radius: str | None = None,
    sort_order: str = "asc",
    page: int = 1,
    page_size: int | None = None,
    include_unavailable: bool = Query(False, description="Показать позиции с последним снимком in_stock=false"),
) -> dict:
    agg_subq = (
        select(
            PriceHistory.product_id.label("product_id"),
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )
    latest_sq = _latest_price_subquery()
    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Product,
                Site.name.label("site_name"),
                agg_subq.c.min_price,
                agg_subq.c.max_price,
                latest_sq.c.last_price,
                latest_sq.c.last_in_stock,
                latest_sq.c.last_ts,
            )
            .join(Site, Site.id == Product.site_id)
            .outerjoin(agg_subq, agg_subq.c.product_id == Product.id)
            .outerjoin(latest_sq, latest_sq.c.product_id == Product.id)
        )
        if not include_unavailable:
            stmt = stmt.where(
                or_(
                    latest_sq.c.last_in_stock.is_(True),
                    latest_sq.c.product_id.is_(None),
                )
            )
        if brand:
            stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))
        if season:
            stmt = stmt.where(Product.season == season)
        if width is not None:
            stmt = stmt.where(Product.width == width)
        if profile is not None:
            stmt = stmt.where(Product.profile == profile)
        if diameter is not None:
            stmt = stmt.where(Product.diameter == diameter)
        if tire_size:
            stmt = stmt.where(Product.tire_size == tire_size)
        if radius:
            stmt = stmt.where(Product.radius == radius)
        if site_name:
            stmt = stmt.where(Site.name == site_name)

        rows = (await session.execute(stmt)).all()
        items: list[dict] = []
        for product, site_name_val, min_price, max_price, last_price, last_in_stock, last_ts in rows:
            min_v = _to_float(min_price)
            max_v = _to_float(max_price)
            spot = _to_float(last_price)
            current = spot if spot is not None else min_v
            if price_min is not None and (current is None or current < price_min):
                continue
            if price_max is not None and (current is None or current > price_max):
                continue
            items.append(
                ProductOut(
                    id=product.id,
                    site_id=product.site_id,
                    site_name=site_name_val,
                    name=product.name,
                    brand=product.brand,
                    model=product.model,
                    season=product.season,
                    spike=product.spike,
                    tire_size=product.tire_size,
                    radius=product.radius,
                    width=product.width,
                    profile=product.profile,
                    diameter=product.diameter,
                    url=product.url,
                    min_price=min_v,
                    max_price=max_v,
                    current_price=current,
                    updated_at=last_ts,
                    in_stock=last_in_stock,
                ).model_dump()
            )

        reverse = sort_order.lower() == "desc"

        def _sort_key(row: dict) -> str | float:
            if sort_by == "name":
                return (row.get("name") or "").lower()
            if sort_by == "brand":
                return (row.get("brand") or "").lower()
            if sort_by == "model":
                return (row.get("model") or "").lower()
            if sort_by == "season":
                return (row.get("season") or "").lower()
            if sort_by == "tire_size":
                return (row.get("tire_size") or "").lower()
            if sort_by == "radius":
                return (row.get("radius") or "").lower()
            if sort_by == "site_name":
                return (row.get("site_name") or "").lower()
            if sort_by == "price":
                return float(row.get("current_price") or 0)
            return float(row.get("current_price") or 0)

        items.sort(key=_sort_key, reverse=reverse)

        total = len(items)
        if page_size is None or page_size <= 0:
            return {"items": items, "total": total, "page": 1, "page_size": total}

        start = max(page - 1, 0) * page_size
        end = start + page_size
        return {"items": items[start:end], "total": total, "page": page, "page_size": page_size}


@router.get("/search")
async def search_products(q: str = Query(..., min_length=2), limit: int = 20) -> list[dict]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product)
            .where(
                Product.name.ilike(f"%{q}%")
                | Product.brand.ilike(f"%{q}%")
                | Product.model.ilike(f"%{q}%")
            )
            .limit(limit)
        )
        rows = list(await session.scalars(stmt))
        return [{"id": p.id, "name": p.name, "brand": p.brand, "model": p.model} for p in rows]


@router.get("/{product_id}")
async def get_product(product_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product, Site.name)
            .join(Site, Site.id == Product.site_id)
            .where(Product.id == product_id)
        )
        row = (await session.execute(stmt)).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        product, site_name_val = row
        last_in_stock = await session.scalar(
            select(PriceHistory.in_stock)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(1)
        )
        return ProductOut(
            id=product.id,
            site_id=product.site_id,
            site_name=site_name_val,
            name=product.name,
            brand=product.brand,
            model=product.model,
            season=product.season,
            spike=product.spike,
            tire_size=product.tire_size,
            radius=product.radius,
            width=product.width,
            profile=product.profile,
            diameter=product.diameter,
            url=product.url,
            updated_at=product.updated_at,
            in_stock=last_in_stock,
        ).model_dump()


@router.get("/{product_id}/subscription")
async def get_product_subscription(product_id: int, request: Request) -> dict:
    _require_subscription_web_key(request)
    chat_id = _subscription_target_chat_id()
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        row = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.product_id == product_id,
                UserSubscription.chat_id == chat_id,
                UserSubscription.is_active.is_(True),
            )
        )
        return {"subscribed": row is not None}


@router.post("/{product_id}/subscription")
async def subscribe_to_product(product_id: int, request: Request) -> dict:
    _require_subscription_web_key(request)
    chat_id = _subscription_target_chat_id()
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        existing = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.chat_id == chat_id,
                UserSubscription.product_id == product_id,
            )
        )
        if existing:
            existing.threshold_pct = _ANY_PRICE_THRESHOLD
            existing.is_active = True
        else:
            session.add(
                UserSubscription(
                    chat_id=chat_id,
                    product_id=product_id,
                    threshold_pct=_ANY_PRICE_THRESHOLD,
                    is_active=True,
                )
            )
        await session.commit()
    return {"ok": True, "subscribed": True}


@router.delete("/{product_id}/subscription")
async def unsubscribe_from_product(product_id: int, request: Request) -> dict:
    _require_subscription_web_key(request)
    chat_id = _subscription_target_chat_id()
    async with AsyncSessionLocal() as session:
        row = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.chat_id == chat_id,
                UserSubscription.product_id == product_id,
            )
        )
        if row is not None:
            await session.delete(row)
        await session.commit()
    return {"ok": True, "subscribed": False}


@router.get("/{product_id}/history")
async def get_product_history(product_id: int, days: int = 30) -> list[PriceHistoryPoint]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    async with AsyncSessionLocal() as session:
        stmt = (
            select(PriceHistory.scraped_at, PriceHistory.price, PriceHistory.old_price, Site.name)
            .join(Product, Product.id == PriceHistory.product_id)
            .join(Site, Site.id == Product.site_id)
            .where(Product.id == product_id, PriceHistory.scraped_at >= cutoff)
            .order_by(PriceHistory.scraped_at.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [
            PriceHistoryPoint(
                scraped_at=row[0],
                price=float(row[1]),
                old_price=float(row[2]) if row[2] is not None else None,
                site_name=row[3],
            )
            for row in rows
        ]


@router.get("/{product_id}/compare")
async def compare_product_prices(product_id: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
    engine = RecommendationEngine()
    try:
        df = await engine.analyzer.compare_sites(
            brand=product.brand or "",
            model=product.model or "",
            size=product.tire_size or "",
        )
        return df.to_dict(orient="records")
    finally:
        await engine.close()


@router.get("/{product_id}/ai-analysis")
async def get_product_ai_analysis(product_id: int) -> dict:
    engine = RecommendationEngine()
    try:
        result = await engine.analyze_product_price(product_id)
        return result.__dict__
    finally:
        await engine.close()
