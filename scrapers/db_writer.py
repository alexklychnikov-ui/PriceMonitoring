from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Alert, PriceHistory, Product
from config import settings
from scrapers.schemas import ProductDTO


async def upsert_product(session: AsyncSession, dto: ProductDTO, site_id: int) -> Product:
    stmt = select(Product).where(Product.site_id == site_id, Product.external_id == dto.external_id)
    product = await session.scalar(stmt)
    is_duplicate = False

    if product is None:
        # If external_id is new, try to merge duplicates by a stable key within a site.
        # MVP key requested: (site_id, name, tire_size, diameter) without price.
        dup_stmt = select(Product).where(
            Product.site_id == site_id,
            Product.name == dto.name,
            Product.tire_size == dto.tire_size,
            Product.diameter == dto.diameter,
        )
        duplicate = await session.scalar(dup_stmt)
        if duplicate is not None:
            product = duplicate
            is_duplicate = True
        else:
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

    new_price = Decimal(str(dto.price))
    should_write_price = True
    if is_duplicate and latest_price is not None:
        # For duplicates: only accept a new price if it is lower than the DB price.
        should_write_price = new_price < latest_price.price

    if not should_write_price:
        await session.flush()
        return product

    history = PriceHistory(
        product_id=product.id,
        price=new_price,
        old_price=Decimal(str(dto.old_price)) if dto.old_price is not None else None,
        discount_pct=Decimal(str(dto.discount_pct)) if dto.discount_pct is not None else None,
        in_stock=dto.in_stock,
        scraped_at=datetime.now(timezone.utc),
    )
    session.add(history)

    if latest_price is not None and latest_price.price != new_price:
        threshold_pct = Decimal(str(settings.PRICE_ALERT_THRESHOLD_PCT))
        if latest_price.price != 0:
            change_pct = (abs(new_price - latest_price.price) / latest_price.price) * Decimal("100")
        else:
            change_pct = threshold_pct

        if change_pct >= threshold_pct:
            alert_type = "price_drop" if new_price < latest_price.price else "price_rise"
            alert = Alert(
                product_id=product.id,
                alert_type=alert_type,
                old_value=str(latest_price.price),
                new_value=str(new_price),
                triggered_at=datetime.now(timezone.utc),
            )
            session.add(alert)

    await session.flush()
    return product
