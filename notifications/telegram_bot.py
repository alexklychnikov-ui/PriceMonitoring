from __future__ import annotations

import asyncio
import html
import json
import time
from collections import defaultdict, deque
from datetime import timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ChatAction, ParseMode
from sqlalchemy import and_, func, or_, select

from ai_analysis.recommendation_engine import RecommendationEngine
from config import settings
from db.database import AsyncSessionLocal
from db.models import ParseRun, PriceHistory, Product, Site, UserSubscription


_RATE_LIMIT_WINDOW_SEC = 60
_RATE_LIMIT_MAX_REQUESTS = 5
_rate_limits: dict[int, deque[float]] = defaultdict(deque)
_PRICE_WIZARD_STEP_KEY = "price_wizard_step"
_PRICE_WIZARD_BRAND_KEY = "price_wizard_brand"
_PRICE_WIZARD_MODEL_KEY = "price_wizard_model"
_PRICE_WIZARD_DIAMETER_KEY = "price_wizard_diameter"
_PRICE_WIZARD_STEP_BRAND = "brand"
_PRICE_WIZARD_STEP_MODEL = "model"
_PRICE_WIZARD_STEP_SIZE = "size"
_PRICE_WIZARD_STEP_SIZE_FILTER = "size_filter"
_WATCH_WIZARD_STEP_KEY = "watch_wizard_step"
_WATCH_WIZARD_BRAND_KEY = "watch_wizard_brand"
_WATCH_WIZARD_MODEL_KEY = "watch_wizard_model"
_WATCH_WIZARD_SIZE_KEY = "watch_wizard_size"
_WATCH_WIZARD_STEP_BRAND = "brand"
_WATCH_WIZARD_STEP_MODEL = "model"
_WATCH_WIZARD_STEP_SIZE = "size"
_WATCH_WIZARD_STEP_THRESHOLD = "threshold"

_REPLY_MENU_BUTTON_TEXT = "Меню"


def _persistent_bottom_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(_REPLY_MENU_BUTTON_TEXT)]],
        resize_keyboard=True,
        is_persistent=True,
    )


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


def _parse_diameter(raw: str) -> str:
    value = raw.replace(" ", "").upper()
    if not value:
        return ""
    if value.startswith("R"):
        value = value[1:]
    digits = "".join(ch for ch in value if ch.isdigit())
    return f"R{digits}" if digits else ""


async def _find_products(brand: str, model: str, size: str) -> list[Product]:
    tire_size, radius = _parse_size(size)
    model_like = f"%{model}%"
    conditions = [
        Product.brand.ilike(f"%{brand}%"),
        or_(Product.model.ilike(model_like), Product.name.ilike(model_like)),
        Product.tire_size == tire_size,
        Site.is_active.is_(True),
    ]
    if radius:
        conditions.append(Product.radius == radius)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product)
            .join(Site, Site.id == Product.site_id)
            .where(and_(*conditions))
            .order_by(Product.id.asc())
        )
        return list(await session.scalars(stmt))


async def _find_products_by_diameter(brand: str, model: str, diameter: str) -> list[Product]:
    radius = _parse_diameter(diameter)
    if not radius:
        return []
    model_like = f"%{model}%"
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product)
            .join(Site, Site.id == Product.site_id)
            .where(
                and_(
                    Product.brand.ilike(f"%{brand}%"),
                    or_(Product.model.ilike(model_like), Product.name.ilike(model_like)),
                    Product.radius == radius,
                    Site.is_active.is_(True),
                )
            )
            .order_by(Product.id.asc())
        )
        return list(await session.scalars(stmt))


async def _find_similar_products(brand: str, model: str, size: str, limit: int = 5) -> list[Product]:
    tire_size, radius = _parse_size(size)
    tokens = [t.strip() for t in model.split() if t.strip()]

    conditions = [
        Product.brand.ilike(f"%{brand}%"),
        Product.tire_size == tire_size,
        Site.is_active.is_(True),
    ]
    if radius:
        conditions.append(Product.radius == radius)

    if tokens:
        token_conditions = [Product.model.ilike(f"%{t}%") for t in tokens] + [Product.name.ilike(f"%{t}%") for t in tokens]
        conditions.append(and_(*token_conditions[:3]))

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Product)
            .join(Site, Site.id == Product.site_id)
            .where(and_(*conditions))
            .order_by(Product.id.desc())
            .limit(limit * 3)
        )
        rows = list(await session.scalars(stmt))

    result: list[Product] = []
    seen: set[str] = set()
    for p in rows:
        key = f"{(p.model or '').strip().lower()}|{(p.tire_size or '').strip()}|{(p.radius or '').strip()}"
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
        if len(result) >= limit:
            break
    return result


def _public_site_base() -> str:
    base = (settings.PUBLIC_SITE_URL or "").strip().rstrip("/")
    if base:
        return base
    domain = (settings.DOMAIN_NAME or "").strip().rstrip("/")
    if domain:
        return f"https://{domain}"
    return ""


def _main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Узнать цену", callback_data="menu:price"),
                InlineKeyboardButton("Мои подписки", callback_data="menu:watchlist"),
            ],
            [
                InlineKeyboardButton("Лучшие предложения", callback_data="menu:deals"),
                InlineKeyboardButton("Недельный отчет", callback_data="menu:report"),
            ],
            [
                InlineKeyboardButton("Статус системы", callback_data="menu:status"),
            ],
        ]
    )


async def _send_main_menu(
    update: Update,
    title: str = "Выбери действие:",
    text: str | None = None,
) -> None:
    message_text = text or title
    if update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=_main_menu_markup())
        return
    if update.message:
        await update.message.reply_text(message_text, reply_markup=_main_menu_markup())


async def _reply_text(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
        return
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def _notify_processing(update: Update, text: str = "Обрабатываю запрос, подожди немного...") -> None:
    if update.effective_chat and update.get_bot():
        await update.get_bot().send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await _reply_text(update, text)


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


def _clear_price_wizard(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(_PRICE_WIZARD_STEP_KEY, None)
    context.user_data.pop(_PRICE_WIZARD_BRAND_KEY, None)
    context.user_data.pop(_PRICE_WIZARD_MODEL_KEY, None)
    context.user_data.pop(_PRICE_WIZARD_DIAMETER_KEY, None)


def _clear_watch_wizard(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(_WATCH_WIZARD_STEP_KEY, None)
    context.user_data.pop(_WATCH_WIZARD_BRAND_KEY, None)
    context.user_data.pop(_WATCH_WIZARD_MODEL_KEY, None)
    context.user_data.pop(_WATCH_WIZARD_SIZE_KEY, None)


def _clear_all_wizards(context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_price_wizard(context)
    _clear_watch_wizard(context)


async def _start_price_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_watch_wizard(context)
    context.user_data[_PRICE_WIZARD_STEP_KEY] = _PRICE_WIZARD_STEP_BRAND
    await _reply_text(
        update,
        "Ок, проверим цену по шагам.\nШаг 1/3: введи бренд (например: Yokohama).\nДля отмены напиши: отмена",
    )


async def _start_watch_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_price_wizard(context)
    context.user_data[_WATCH_WIZARD_STEP_KEY] = _WATCH_WIZARD_STEP_BRAND
    await _reply_text(
        update,
        "Ок, настроим подписку по шагам.\nШаг 1/4: введи бренд (например: Yokohama).\nДля отмены напиши: отмена",
    )


async def _send_price_result(
    update: Update,
    brand: str,
    model: str,
    size: str,
) -> None:
    await _notify_processing(update, "Ищу цены по запросу, это может занять до 10-20 секунд...")
    products = await _find_products(brand, model, size)
    if not products:
        suggestions = await _find_similar_products(brand, model, size, limit=5)
        if not suggestions:
            await _reply_text(update, "Товар не найден.")
            return
        lines = ["Точное совпадение не найдено. Похожие варианты:", ""]
        for p in suggestions:
            lines.append(f"• {p.brand or '-'} {p.model or '-'} {p.tire_size or '-'} {p.radius or ''}".strip())
        await _reply_text(update, "\n".join(lines))
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
        await _reply_text(update, "Нет актуальных цен.")
        return

    rows.sort(key=lambda x: x[1])
    top_rows = rows[:10]
    lines = [f"🔍 {brand} {model} • {products[0].tire_size} • {products[0].radius}", "", "📊 Цены прямо сейчас (первые 10):"]
    for idx, (site_name, price, product) in enumerate(top_rows):
        marker = " ← ЛУЧШАЯ" if idx == 0 else ""
        lines.append(f"{'✅' if idx == 0 else '•'} {site_name:18} — {_format_rub(price)}{marker}")
        if product.url:
            lines.append(f"  🔗 {product.url}")

    engine = RecommendationEngine()
    try:
        recommendation = await engine.get_buy_recommendation(brand, model, products[0].tire_size or "")
    finally:
        await engine.close()
    ai_hint = _format_price_ai_hint(recommendation)
    if ai_hint:
        lines.extend(["", f"💡 {ai_hint}"])
    await _reply_text(update, "\n".join(lines))


async def _send_price_result_by_diameter(
    update: Update,
    brand: str,
    model: str,
    diameter: str,
    size_filter: str = "",
) -> None:
    await _notify_processing(update, "Ищу цены по диаметру, это может занять до 10-20 секунд...")
    products = await _find_products_by_diameter(brand, model, diameter)
    if size_filter:
        needle = size_filter.strip().lower()
        products = [p for p in products if needle in (p.tire_size or "").lower()]
    if not products:
        await _reply_text(update, "Товар по заданному диаметру не найден.")
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
        await _reply_text(update, "Нет актуальных цен.")
        return

    rows.sort(key=lambda x: x[1])
    top_rows = rows[:10]
    normalized_diameter = _parse_diameter(diameter)
    header = f"🔍 {brand} {model} • {normalized_diameter}"
    if size_filter:
        header += f" • фильтр размера: {size_filter}"
    lines = [header, "", "📊 Варианты по диаметру (первые 10):"]
    for idx, (site_name, price, product) in enumerate(top_rows):
        marker = " ← ЛУЧШАЯ" if idx == 0 else ""
        lines.append(
            f"{'✅' if idx == 0 else '•'} {product.tire_size or '-'} {product.radius or ''} — {_format_rub(price)} ({site_name}){marker}"
        )
        if product.url:
            lines.append(f"  🔗 {product.url}")
    await _reply_text(update, "\n".join(lines))


def _parse_deals_season(season: str) -> str | None:
    season_map = {
        "winter": "Зима",
        "summer": "Лето",
        "зима": "Зима",
        "лето": "Лето",
        "всесезон": "Всесезон",
        "allseason": "Всесезон",
    }
    key = (season or "").strip().lower()
    if key in ("", "any", "все", "all"):
        return None
    return season_map.get(key)


async def _lowest_listed_price_instock() -> float | None:
    async with AsyncSessionLocal() as session:
        latest_subq = (
            select(
                PriceHistory.product_id.label("product_id"),
                func.max(PriceHistory.scraped_at).label("max_scraped_at"),
            )
            .group_by(PriceHistory.product_id)
            .subquery()
        )
        stmt = (
            select(func.min(PriceHistory.price))
            .select_from(Product)
            .join(Site, Site.id == Product.site_id)
            .join(latest_subq, latest_subq.c.product_id == Product.id)
            .join(
                PriceHistory,
                and_(
                    PriceHistory.product_id == latest_subq.c.product_id,
                    PriceHistory.scraped_at == latest_subq.c.max_scraped_at,
                ),
            )
            .where(Site.is_active.is_(True), PriceHistory.in_stock.is_(True))
        )
        v = await session.scalar(stmt)
        return float(v) if v is not None else None


async def _best_deals_from_db(budget: float, season: str, limit: int = 5) -> list[str]:
    season_value = _parse_deals_season(season)
    pool = max(limit * 40, 100)

    async with AsyncSessionLocal() as session:
        latest_subq = (
            select(
                PriceHistory.product_id.label("product_id"),
                func.max(PriceHistory.scraped_at).label("max_scraped_at"),
            )
            .group_by(PriceHistory.product_id)
            .subquery()
        )

        conditions = [
            Site.is_active.is_(True),
            PriceHistory.in_stock.is_(True),
            PriceHistory.price <= Decimal(str(budget)),
        ]
        if season_value:
            conditions.append(or_(Product.season == season_value, Product.season.is_(None)))

        stmt = (
            select(Product, Site.name, PriceHistory.price)
            .join(Site, Site.id == Product.site_id)
            .join(latest_subq, latest_subq.c.product_id == Product.id)
            .join(
                PriceHistory,
                and_(
                    PriceHistory.product_id == latest_subq.c.product_id,
                    PriceHistory.scraped_at == latest_subq.c.max_scraped_at,
                ),
            )
            .where(and_(*conditions))
            .order_by(PriceHistory.price.asc())
            .limit(pool)
        )
        rows = list((await session.execute(stmt)).all())

    lines: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for product, site_name, price in rows:
        key = ((product.brand or "").strip().lower(), (product.model or "").strip().lower(), (product.tire_size or "").strip())
        if key in seen:
            continue
        seen.add(key)
        title = f"{product.brand or '-'} {product.model or '-'} {product.tire_size or '-'} {product.radius or ''}".strip()
        lines.append(f"• {title} — {_format_rub(float(price))} ({site_name})")
        if len(lines) >= limit:
            break
    return lines


def _format_price_ai_hint(raw_text: str) -> str:
    txt = (raw_text or "").strip()
    if not txt:
        return ""
    try:
        payload = json.loads(txt)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""

    optimal = payload.get("optimal_price")
    margin = payload.get("margin_price")
    reason = str(payload.get("reasoning") or "").strip()
    if optimal is None and margin is None:
        return ""

    parts: list[str] = []
    if optimal is not None:
        parts.append(f"оптимально: {_format_rub(float(optimal))}")
    if margin is not None:
        parts.append(f"с маржой: {_format_rub(float(margin))}")
    if reason:
        parts.append(reason)
    return "; ".join(parts)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None:
        return
    _clear_all_wizards(context)
    welcome = (
        "Привет! Я AI-ассистент Price Monitor.\n\n"
        "Что я умею:\n"
        "• сравнивать цены по шинам в реальном времени;\n"
        "• подписка на товар — на сайте в карточке товара (список — «Мои подписки»);\n"
        "• показывать лучшие предложения и краткий отчет;\n"
        "• отдавать статус системы парсинга.\n\n"
        "Ниже закреплена кнопка «Меню» — то же самое, что /start. Ещё можно: /menu или написать «меню»."
    )
    if update.message:
        await update.message.reply_text(welcome, reply_markup=_persistent_bottom_menu_keyboard())
        await update.message.reply_text("Выбери действие:", reply_markup=_main_menu_markup())
        return
    await _send_main_menu(update, text=welcome)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_all_wizards(context)
    await _send_main_menu(update)


async def menu_text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_cmd(update, context)


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
    await _send_price_result(update, brand, model, size)


async def price_wizard_text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get(_PRICE_WIZARD_STEP_KEY)
    if not step or not update.message:
        return

    text = (update.message.text or "").strip()
    text_lower = text.lower()
    if text_lower in {"отмена", "cancel"}:
        _clear_price_wizard(context)
        await _reply_text(update, "Ок, отменил ввод. Открыть меню снова:", reply_markup=_main_menu_markup())
        return

    if step == _PRICE_WIZARD_STEP_BRAND:
        context.user_data[_PRICE_WIZARD_BRAND_KEY] = text
        context.user_data[_PRICE_WIZARD_STEP_KEY] = _PRICE_WIZARD_STEP_MODEL
        await _reply_text(update, "Шаг 2/3: введи модель (например: IG55).")
        return

    if step == _PRICE_WIZARD_STEP_MODEL:
        context.user_data[_PRICE_WIZARD_MODEL_KEY] = text
        context.user_data[_PRICE_WIZARD_STEP_KEY] = _PRICE_WIZARD_STEP_SIZE
        await _reply_text(update, "Шаг 3/4: введи диаметр (например: R17 или 17).")
        return

    if step == _PRICE_WIZARD_STEP_SIZE:
        context.user_data[_PRICE_WIZARD_DIAMETER_KEY] = text.replace(" ", "")
        context.user_data[_PRICE_WIZARD_STEP_KEY] = _PRICE_WIZARD_STEP_SIZE_FILTER
        await _reply_text(
            update,
            "Шаг 4/4: введи размер или его часть для фильтра (например: 255, 65, 255/65). "
            "Если фильтр не нужен, введи: -",
        )
        return

    brand = str(context.user_data.get(_PRICE_WIZARD_BRAND_KEY, "")).strip()
    model = str(context.user_data.get(_PRICE_WIZARD_MODEL_KEY, "")).strip()
    diameter = str(context.user_data.get(_PRICE_WIZARD_DIAMETER_KEY, "")).strip()
    size_filter = "" if text_lower in {"-", "пропустить", "skip"} else text.replace(" ", "")
    _clear_price_wizard(context)
    await _send_price_result_by_diameter(update, brand, model, diameter, size_filter=size_filter)
    await _reply_text(update, "Готово. Открыть меню снова:", reply_markup=_main_menu_markup())


async def _create_watch_subscription(
    update: Update,
    chat_id: int,
    brand: str,
    model: str,
    size: str,
    threshold: float,
) -> None:
    products = await _find_products(brand, model, size)
    if not products:
        await _reply_text(update, "Товар не найден.")
        return
    product = products[0]
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(UserSubscription).where(
                UserSubscription.chat_id == str(chat_id),
                UserSubscription.product_id == product.id,
            )
        )
        if existing:
            existing.threshold_pct = Decimal(str(threshold))
            existing.is_active = True
        else:
            session.add(
                UserSubscription(
                    chat_id=str(chat_id),
                    product_id=product.id,
                    threshold_pct=Decimal(str(threshold)),
                    is_active=True,
                )
            )
        await session.commit()
    await _reply_text(update, f"Подписка создана: {product.name} ({threshold}%)")


async def watch_wizard_text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get(_WATCH_WIZARD_STEP_KEY)
    if not step or not update.message:
        return

    chat = update.effective_chat
    if chat is None:
        return

    text = (update.message.text or "").strip()
    text_lower = text.lower()
    if text_lower in {"отмена", "cancel"}:
        _clear_watch_wizard(context)
        await _reply_text(update, "Ок, отменил ввод. Открыть меню снова:", reply_markup=_main_menu_markup())
        return

    if step == _WATCH_WIZARD_STEP_BRAND:
        context.user_data[_WATCH_WIZARD_BRAND_KEY] = text
        context.user_data[_WATCH_WIZARD_STEP_KEY] = _WATCH_WIZARD_STEP_MODEL
        await _reply_text(update, "Шаг 2/4: введи модель (например: IG55).")
        return

    if step == _WATCH_WIZARD_STEP_MODEL:
        context.user_data[_WATCH_WIZARD_MODEL_KEY] = text
        context.user_data[_WATCH_WIZARD_STEP_KEY] = _WATCH_WIZARD_STEP_SIZE
        await _reply_text(update, "Шаг 3/4: введи размер (например: 205/60R16).")
        return

    if step == _WATCH_WIZARD_STEP_SIZE:
        context.user_data[_WATCH_WIZARD_SIZE_KEY] = text.replace(" ", "")
        context.user_data[_WATCH_WIZARD_STEP_KEY] = _WATCH_WIZARD_STEP_THRESHOLD
        await _reply_text(
            update,
            "Шаг 4/4: введи порог изменения в % (например: 5). Для значения по умолчанию введи: -",
        )
        return

    threshold = 5.0
    if text_lower not in {"-", "default", "по умолчанию"}:
        try:
            threshold = float(text.replace(",", "."))
        except ValueError:
            await _reply_text(update, "Порог должен быть числом. Введи, например: 5 (или '-' для значения по умолчанию).")
            return

    brand = str(context.user_data.get(_WATCH_WIZARD_BRAND_KEY, "")).strip()
    model = str(context.user_data.get(_WATCH_WIZARD_MODEL_KEY, "")).strip()
    size = str(context.user_data.get(_WATCH_WIZARD_SIZE_KEY, "")).strip()
    _clear_watch_wizard(context)
    await _notify_processing(update, "Создаю подписку, подожди пару секунд...")
    await _create_watch_subscription(update, chat.id, brand, model, size, threshold)
    await _reply_text(update, "Готово. Открыть меню снова:", reply_markup=_main_menu_markup())


async def wizard_text_router_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(_PRICE_WIZARD_STEP_KEY):
        await price_wizard_text_cmd(update, context)
        return
    if context.user_data.get(_WATCH_WIZARD_STEP_KEY):
        await watch_wizard_text_cmd(update, context)
        return


async def watch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /watch <бренд> <модель> <размер> [порог%]")
        return
    size, threshold = _extract_size_and_threshold(context.args[2:])
    await _create_watch_subscription(update, chat.id, context.args[0], context.args[1], size, threshold)


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
            await _reply_text(update, "Подписок нет.")
            return
        base = _public_site_base()
        names: list[str] = []
        for row in rows:
            product = await session.get(Product, row.product_id)
            if not product:
                continue
            if base:
                url = f"{base}/products/{product.id}"
                names.append(f"• <a href=\"{html.escape(url)}\">{html.escape(product.name)}</a>")
            else:
                names.append(f"• {product.name} (id {product.id})")
        body = "Ваши подписки (открывай ссылку — на сайте можно отключить):\n" + "\n".join(names)
        if update.message:
            await update.message.reply_text(body, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(body, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def deals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _notify_processing(update, "Ищу в каталоге парсинга (цена в наличии, последний снимок)...")
    args = context.args or []
    budget = float(args[0]) if args else 15000.0
    season = args[1] if len(args) > 1 else "winter"

    limit = 8
    db_lines = await _best_deals_from_db(budget=budget, season=season, limit=limit)
    season_note = ""
    if not db_lines:
        db_lines = await _best_deals_from_db(budget=budget, season="any", limit=limit)
        if db_lines:
            season_note = "По выбранному сезону в бюджет ничего не попало — ниже любые сезоны.\n\n"

    if db_lines:
        header = f"{season_note}До {_format_rub(budget)} ({season}), в наличии, дешевле первыми:"
        await _reply_text(update, "\n".join([header, *db_lines]))
        return

    lo = await _lowest_listed_price_instock()
    if lo is not None:
        suggest = int(max(lo * 1.15, budget * 1.2))
        await _reply_text(
            update,
            f"В наличии нет позиций до {_format_rub(budget)} (с учётом сезона «{season}» и дублей по модели).\n"
            f"Минимальная цена в базе сейчас: {_format_rub(lo)}.\n"
            f"Попробуй, например: `/deals {suggest}` или `/deals {suggest} summer`",
        )
        return

    await _reply_text(
        update,
        "В базе нет актуальных цен «в наличии» — проверь парсинг сайтов в настройках или подожди следующего обхода.",
    )


async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _notify_processing(update, "Генерирую недельный отчет, это может занять до 30 секунд...")
    engine = RecommendationEngine()
    try:
        report = await engine.generate_weekly_report(force_refresh=True)
    except Exception:
        await _reply_text(update, "Не удалось собрать отчет сейчас. Попробуй позже.")
        return
    finally:
        await engine.close()
    await _reply_text(update, report[:3500])


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        active_sites = int(await session.scalar(select(func.count(Site.id)).where(Site.is_active.is_(True))) or 0)
        last_run = await session.scalar(select(ParseRun).order_by(ParseRun.started_at.desc()).limit(1))
    status = last_run.status if last_run else "n/a"
    ts = "n/a"
    if last_run and last_run.started_at:
        dt = last_run.started_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_irk = dt.astimezone(ZoneInfo("Asia/Irkutsk"))
        ts = dt_irk.strftime("%Y-%m-%d %H:%M:%S")
    await _reply_text(update, f"Активных сайтов: {active_sites}\nПоследний парсинг: {status} ({ts}, Иркутск)")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    action = (query.data or "").replace("menu:", "", 1)

    if action == "price":
        await _start_price_wizard(update, context)
        return
    if action == "watch":
        await _start_watch_wizard(update, context)
        return
    if action == "watchlist":
        await watchlist_cmd(update, context)
        if query.message:
            await query.message.reply_text("Открыть меню снова:", reply_markup=_main_menu_markup())
        return
    if action == "deals":
        await deals_cmd(update, context)
        if query.message:
            await query.message.reply_text("Открыть меню снова:", reply_markup=_main_menu_markup())
        return
    if action == "report":
        await report_cmd(update, context)
        if query.message:
            await query.message.reply_text("Открыть меню снова:", reply_markup=_main_menu_markup())
        return
    if action == "status":
        await status_cmd(update, context)
        if query.message:
            await query.message.reply_text("Открыть меню снова:", reply_markup=_main_menu_markup())
        return

    await _send_main_menu(update)


async def run_bot() -> None:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("watch", watch_cmd))
    app.add_handler(CommandHandler("unwatch", unwatch_cmd))
    app.add_handler(CommandHandler("watchlist", watchlist_cmd))
    app.add_handler(CommandHandler("deals", deals_cmd))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^(меню|menu|📋\s*меню)$"), menu_text_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), wizard_text_router_cmd))
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
