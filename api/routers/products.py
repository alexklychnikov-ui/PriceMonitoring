from __future__ import annotations

from decimal import Decimal

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from ai_analysis.recommendation_engine import RecommendationEngine
from api.schemas import PriceHistoryPoint, ProductOut
from db.database import AsyncSessionLocal
from db.models import PriceHistory, Product, Site


router = APIRouter()


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
    page_size: int = 50,
) -> dict:
    price_subq = (
        select(
            PriceHistory.product_id.label("product_id"),
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
            func.max(PriceHistory.scraped_at).label("last_ts"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )
    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Product,
                Site.name.label("site_name"),
                price_subq.c.min_price,
                price_subq.c.max_price,
                price_subq.c.last_ts,
            )
            .join(Site, Site.id == Product.site_id)
            .join(price_subq, price_subq.c.product_id == Product.id, isouter=True)
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
        for product, _, min_price, max_price, last_ts in rows:
            min_v = _to_float(min_price)
            max_v = _to_float(max_price)
            if price_min is not None and (min_v is None or min_v < price_min):
                continue
            if price_max is not None and (min_v is None or min_v > price_max):
                continue
            items.append(
                ProductOut(
                    id=product.id,
                    site_id=product.site_id,
                    name=product.name,
                    brand=product.brand,
                    model=product.model,
                    season=product.season,
                    tire_size=product.tire_size,
                    radius=product.radius,
                    width=product.width,
                    profile=product.profile,
                    diameter=product.diameter,
                    url=product.url,
                    min_price=min_v,
                    max_price=_to_float(max_price),
                    current_price=min_v,
                    updated_at=last_ts,
                ).model_dump()
            )

        reverse = sort_order.lower() == "desc"
        if sort_by == "name":
            items.sort(key=lambda x: x["name"] or "", reverse=reverse)
        else:
            items.sort(key=lambda x: x.get("current_price") or 0, reverse=reverse)

        total = len(items)
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
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductOut(
            id=product.id,
            site_id=product.site_id,
            name=product.name,
            brand=product.brand,
            model=product.model,
            season=product.season,
            tire_size=product.tire_size,
            radius=product.radius,
            width=product.width,
            profile=product.profile,
            diameter=product.diameter,
            url=product.url,
            updated_at=product.updated_at,
        ).model_dump()


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
