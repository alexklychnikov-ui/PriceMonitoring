from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Alert, PriceHistory, Product, UserSubscription
from config import settings
from scrapers.schemas import ProductDTO


def _normalize_season(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"winter", "зима"}:
        return "Зима"
    if normalized in {"summer", "лето"}:
        return "Лето"
    if normalized in {"allseason", "all season", "всесезон", "всесезонные", "всесезонная"}:
        return "Всесезон"
    return None


def _norm_name(value: str | None) -> str:
    return " ".join((value or "").split())


def _model_merge_ok(model: str | None) -> bool:
    m = (model or "").strip().lower()
    return bool(m) and m != "unknown"


async def _find_merge_candidate(session: AsyncSession, site_id: int, dto: ProductDTO) -> Product | None:
    season = _normalize_season(dto.season)
    filters = [
        Product.site_id == site_id,
        Product.brand == dto.brand,
        Product.tire_size == dto.tire_size,
        Product.radius == dto.radius,
        Product.diameter == dto.diameter,
        Product.season == season,
    ]
    if dto.spike is None:
        filters.append(Product.spike.is_(None))
    else:
        filters.append(Product.spike == dto.spike)

    candidates = list(await session.scalars(select(Product).where(*filters)))
    norm = _norm_name(dto.name)
    for p in candidates:
        if p.name == dto.name or _norm_name(p.name) == norm:
            return p
    if _model_merge_ok(dto.model):
        for p in candidates:
            if p.model == dto.model:
                return p
    return None


def _apply_dto_to_product(product: Product, dto: ProductDTO) -> None:
    product.external_id = dto.external_id
    product.name = dto.name
    product.brand = dto.brand
    product.model = dto.model
    product.season = _normalize_season(dto.season)
    product.spike = dto.spike
    product.tire_size = dto.tire_size
    product.radius = dto.radius
    product.width = dto.width
    product.profile = dto.profile
    product.diameter = dto.diameter
    product.url = dto.url


async def upsert_product(
    session: AsyncSession,
    dto: ProductDTO,
    site_id: int,
    alert_threshold_pct: Decimal | None = None,
) -> Product:
    stmt = select(Product).where(Product.site_id == site_id, Product.external_id == dto.external_id)
    product = await session.scalar(stmt)

    if product is None:
        merged = await _find_merge_candidate(session, site_id, dto)
        if merged is not None:
            product = merged
        else:
            product = Product(
                site_id=site_id,
                external_id=dto.external_id,
                name=dto.name,
                brand=dto.brand,
                model=dto.model,
                season=_normalize_season(dto.season),
                spike=dto.spike,
                tire_size=dto.tire_size,
                radius=dto.radius,
                width=dto.width,
                profile=dto.profile,
                diameter=dto.diameter,
                url=dto.url,
            )
            session.add(product)
            await session.flush()

    _apply_dto_to_product(product, dto)

    latest_price_stmt = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product.id)
        .order_by(PriceHistory.scraped_at.desc())
        .limit(1)
    )
    latest_price = await session.scalar(latest_price_stmt)

    new_price = Decimal(str(dto.price))

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
        threshold_pct = (
            alert_threshold_pct
            if alert_threshold_pct is not None
            else Decimal(str(settings.PRICE_ALERT_THRESHOLD_PCT))
        )
        if latest_price.price != 0:
            change_pct = (abs(new_price - latest_price.price) / latest_price.price) * Decimal("100")
        else:
            change_pct = threshold_pct

        subscriber_wants_alert = False
        subs = list(
            await session.scalars(
                select(UserSubscription).where(
                    UserSubscription.product_id == product.id,
                    UserSubscription.is_active.is_(True),
                )
            )
        )
        for sub in subs:
            st = Decimal(sub.threshold_pct)
            if st == 0 and change_pct > 0:
                subscriber_wants_alert = True
                break
            if st > 0 and change_pct >= st:
                subscriber_wants_alert = True
                break

        if change_pct >= threshold_pct or subscriber_wants_alert:
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


async def mark_missing_products_out_of_stock(session: AsyncSession, site_id: int, seen_external_ids: set[str]) -> int:
    if not seen_external_ids:
        return 0

    products = list(await session.scalars(select(Product).where(Product.site_id == site_id)))
    marked = 0
    now = datetime.now(timezone.utc)

    for product in products:
        if product.external_id in seen_external_ids:
            continue

        latest_price = await session.scalar(
            select(PriceHistory)
            .where(PriceHistory.product_id == product.id)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(1)
        )
        if latest_price is None:
            continue
        if latest_price.in_stock is False:
            continue

        session.add(
            PriceHistory(
                product_id=product.id,
                price=latest_price.price,
                old_price=latest_price.price,
                discount_pct=None,
                in_stock=False,
                scraped_at=now,
            )
        )
        marked += 1

    await session.flush()
    return marked
