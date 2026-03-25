from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Alert, PriceHistory, Product
from scrapers.schemas import ProductDTO


async def upsert_product(session: AsyncSession, dto: ProductDTO, site_id: int) -> Product:
    stmt = select(Product).where(Product.site_id == site_id, Product.external_id == dto.external_id)
    product = await session.scalar(stmt)

    if product is None:
        product = Product(
            site_id=site_id,
            external_id=dto.external_id,
            name=dto.name,
            brand=dto.brand,
            model=dto.model,
            season=dto.season,
            tire_size=dto.tire_size,
            radius=dto.radius,
            width=dto.width,
            profile=dto.profile,
            diameter=dto.diameter,
            url=dto.url,
        )
        session.add(product)
        await session.flush()
    else:
        product.name = dto.name
        product.brand = dto.brand
        product.model = dto.model
        product.season = dto.season
        product.tire_size = dto.tire_size
        product.radius = dto.radius
        product.width = dto.width
        product.profile = dto.profile
        product.diameter = dto.diameter
        product.url = dto.url

    latest_price_stmt = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product.id)
        .order_by(PriceHistory.scraped_at.desc())
        .limit(1)
    )
    latest_price = await session.scalar(latest_price_stmt)

    history = PriceHistory(
        product_id=product.id,
        price=Decimal(str(dto.price)),
        old_price=Decimal(str(dto.old_price)) if dto.old_price is not None else None,
        discount_pct=Decimal(str(dto.discount_pct)) if dto.discount_pct is not None else None,
        in_stock=dto.in_stock,
        scraped_at=datetime.now(timezone.utc),
    )
    session.add(history)

    if latest_price is not None and float(latest_price.price) != dto.price:
        alert = Alert(
            product_id=product.id,
            alert_type="price_changed",
            old_value=str(latest_price.price),
            new_value=str(dto.price),
            triggered_at=datetime.now(timezone.utc),
        )
        session.add(alert)

    await session.flush()
    return product
