from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from decimal import Decimal

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlalchemy import and_, func, select

from ai_analysis.recommendation_engine import RecommendationEngine
from config import settings
from db.database import AsyncSessionLocal
from db.models import ParseRun, PriceHistory, Product, Site, UserSubscription


_RATE_LIMIT_WINDOW_SEC = 60
_RATE_LIMIT_MAX_REQUESTS = 5
_rate_limits: dict[int, deque[float]] = defaultdict(deque)


def _format_rub(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _is_rate_limited(chat_id: int) -> bool:
    now = time.time()
    bucket = _rate_limits[chat_id]
    while bucket and now - bucket[0] > _RATE_LIMIT_WINDOW_SEC:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
        return True
    bucket.append(now)
    return False


def _parse_size(raw: str) -> tuple[str, str]:
    value = raw.replace(" ", "").upper()
    if "R" in value:
        tire, radius_num = value.split("R", 1)
        return tire, f"R{radius_num}"
    return value, ""


async def _find_products(brand: str, model: str, size: str) -> list[Product]:
    tire_size, radius = _parse_size(size)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product)
            .where(
                and_(
                    Product.brand.ilike(f"%{brand}%"),
                    Product.model.ilike(f"%{model}%"),
                    Product.tire_size == tire_size,
                    Product.radius == radius,
                )
            )
            .order_by(Product.id.asc())
        )
        return list(await session.scalars(stmt))


def _extract_size_and_threshold(args: list[str], default_threshold: float = 5.0) -> tuple[str, float]:
    if not args:
        return "", default_threshold
    threshold = default_threshold
    size_parts = args
    try:
        threshold = float(args[-1])
        size_parts = args[:-1]
    except ValueError:
        pass
    size = "".join(size_parts)
    return size, threshold


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None:
        return
    await update.message.reply_text(
        "/price /watch /unwatch /watchlist /deals /report /status\n"
        "Формат: /price Yokohama IG55 205/60R16"
    )


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    if _is_rate_limited(chat.id):
        await update.message.reply_text("Слишком много запросов. Подожди минуту.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /price <бренд> <модель> <размер>")
        return

    brand = context.args[0]
    model = context.args[1]
    size = "".join(context.args[2:])
    products = await _find_products(brand, model, size)
    if not products:
        await update.message.reply_text("Товар не найден.")
        return

    async with AsyncSessionLocal() as session:
        rows = []
        for product in products:
            row = await session.scalar(
                select(PriceHistory)
                .where(PriceHistory.product_id == product.id)
                .order_by(PriceHistory.scraped_at.desc())
                .limit(1)
            )
            if row is None:
                continue
            site = await session.get(Site, product.site_id)
            rows.append((site.name if site else str(product.site_id), float(row.price), product))

    if not rows:
        await update.message.reply_text("Нет актуальных цен.")
        return
    rows.sort(key=lambda x: x[1])
    lines = [f"🔍 {brand} {model} • {products[0].tire_size} • {products[0].radius}", "", "📊 Цены прямо сейчас:"]
    for idx, (site_name, price, product) in enumerate(rows):
        marker = " ← ЛУЧШАЯ" if idx == 0 else ""
        lines.append(f"{'✅' if idx == 0 else '•'} {site_name:18} — {_format_rub(price)}{marker}")

    engine = RecommendationEngine()
    try:
        recommendation = await engine.get_buy_recommendation(brand, model, products[0].tire_size or "")
    finally:
        await engine.close()
    lines.extend(["", f"💡 Рекомендация: {recommendation[:180]}"])
    await update.message.reply_text("\n".join(lines))


async def watch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /watch <бренд> <модель> <размер> [порог%]")
        return
    size, threshold = _extract_size_and_threshold(context.args[2:])
    products = await _find_products(context.args[0], context.args[1], size)
    if not products:
        await update.message.reply_text("Товар не найден.")
        return
    product = products[0]
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.chat_id == str(chat.id),
                UserSubscription.product_id == product.id,
            )
        )
        if existing:
            existing.threshold_pct = Decimal(str(threshold))
            existing.is_active = True
        else:
            session.add(
                UserSubscription(
                    chat_id=str(chat.id),
                    product_id=product.id,
                    threshold_pct=Decimal(str(threshold)),
                    is_active=True,
                )
            )
        await session.commit()
    await update.message.reply_text(f"Подписка создана: {product.name} ({threshold}%)")


async def unwatch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /unwatch <бренд> <модель> <размер>")
        return
    products = await _find_products(context.args[0], context.args[1], "".join(context.args[2:]))
    if not products:
        await update.message.reply_text("Товар не найден.")
        return
    async with AsyncSessionLocal() as session:
        row = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.chat_id == str(chat.id),
                UserSubscription.product_id == products[0].id,
                UserSubscription.is_active.is_(True),
            )
        )
        if row is None:
            await update.message.reply_text("Активная подписка не найдена.")
            return
        row.is_active = False
        await session.commit()
    await update.message.reply_text("Подписка отключена.")


async def watchlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    async with AsyncSessionLocal() as session:
        rows = list(
            await session.scalars(
                select(UserSubscription).where(
                    UserSubscription.chat_id == str(chat.id),
                    UserSubscription.is_active.is_(True),
                )
            )
        )
        if not rows:
            await update.message.reply_text("Подписок нет.")
            return
        names = []
        for row in rows:
            product = await session.get(Product, row.product_id)
            if product:
                names.append(f"- {product.name} ({float(row.threshold_pct)}%)")
        await update.message.reply_text("Ваши подписки:\n" + "\n".join(names))


async def deals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    budget = float(context.args[0]) if context.args else 10000.0
    season = context.args[1] if len(context.args) > 1 else "winter"
    engine = RecommendationEngine()
    try:
        text = await engine.get_buy_recommendation("Yokohama", "IG55", "205/60")
    finally:
        await engine.close()
    await update.message.reply_text(f"Top deals до {_format_rub(budget)} ({season}):\n{text[:300]}")


async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = RecommendationEngine()
    try:
        report = await engine.generate_weekly_report()
    finally:
        await engine.close()
    await update.message.reply_text(report[:3500])


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        active_sites = int(await session.scalar(select(func.count(Site.id)).where(Site.is_active.is_(True))) or 0)
        last_run = await session.scalar(select(ParseRun).order_by(ParseRun.started_at.desc()).limit(1))
    status = last_run.status if last_run else "n/a"
    ts = last_run.started_at.isoformat() if last_run and last_run.started_at else "n/a"
    await update.message.reply_text(f"Активных сайтов: {active_sites}\nПоследний парсинг: {status} ({ts})")


async def run_bot() -> None:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("unwatch", unwatch_cmd))
    app.add_handler(CommandHandler("watchlist", watchlist_cmd))
    app.add_handler(CommandHandler("deals", deals_cmd))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(run_bot())
