from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import Bot
from telegram.helpers import escape_markdown

from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, Product
from notifications.message_templates import PRICE_DROP_TEMPLATE, PRICE_RISE_TEMPLATE, WEEKLY_DIGEST_TEMPLATE, render_template


logger = logging.getLogger("notifications.alert_sender")


class AlertSender:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    async def _already_sent_recently(self, product_id: int, alert_type: str) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                Alert.__table__.select().where(
                    Alert.product_id == product_id,
                    Alert.alert_type == alert_type,
                    Alert.sent_at.is_not(None),
                    Alert.sent_at >= cutoff,
                )
            )
            return rows.first() is not None

    async def send_price_drop_alert(
        self, alert: Alert, product: Product, chat_id: str, *, use_product_dedup: bool = True
    ) -> bool:
        if use_product_dedup and await self._already_sent_recently(product.id, "price_drop"):
            return False
        old_price = float(alert.old_value or 0)
        new_price = float(alert.new_value or 0)
        change_pct = round(((old_price - new_price) / old_price) * 100, 2) if old_price else 0.0
        message = render_template(
            PRICE_DROP_TEMPLATE,
            site_name=str(product.site_id),
            product_name=escape_markdown(product.name, version=2),
            size=f"{product.tire_size or ''} {product.radius or ''}".strip(),
            old_price=old_price,
            new_price=new_price,
            change_pct=change_pct,
            savings=max(old_price - new_price, 0),
            product_url=product.url,
        )
        await self.bot.send_message(chat_id=chat_id, text=message)
        logger.info("message_sent chat_id=%s type=price_drop", chat_id)
        return True

    async def send_price_rise_alert(
        self, alert: Alert, product: Product, chat_id: str, *, use_product_dedup: bool = True
    ) -> bool:
        if use_product_dedup and await self._already_sent_recently(product.id, "price_rise"):
            return False
        old_price = float(alert.old_value or 0)
        new_price = float(alert.new_value or 0)
        change_pct = round(((new_price - old_price) / old_price) * 100, 2) if old_price else 0.0
        message = render_template(
            PRICE_RISE_TEMPLATE,
            site_name=str(product.site_id),
            product_name=escape_markdown(product.name, version=2),
            size=f"{product.tire_size or ''} {product.radius or ''}".strip(),
            old_price=old_price,
            new_price=new_price,
            change_pct=change_pct,
        )
        await self.bot.send_message(chat_id=chat_id, text=message)
        logger.info("message_sent chat_id=%s type=price_rise", chat_id)
        return True

    async def send_new_low_alert(self, alert: Alert, product: Product, chat_id: str) -> bool:
        return await self.send_price_drop_alert(alert, product, chat_id)

    async def send_weekly_digest(self, chat_id: str, report: str) -> bool:
        message = render_template(
            WEEKLY_DIGEST_TEMPLATE,
            week_range=datetime.now(timezone.utc).strftime("%d.%m - %d.%m"),
            total_changes=0,
            avg_change=0.0,
            top_deals_count=0,
            top_deals=[],
            ai_recommendation=report,
        )
        await self.bot.send_message(chat_id=chat_id, text=message)
        logger.info("message_sent chat_id=%s type=weekly_digest", chat_id)
        return True

    async def send_parse_error_notification(self, site_name: str, error: str) -> bool:
        message = f"⚠️ Ошибка парсинга {escape_markdown(site_name, version=2)}: {escape_markdown(error, version=2)}"
        await self.bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=message)
        logger.info("message_sent chat_id=%s type=parse_error", settings.TELEGRAM_CHAT_ID)
        return True

    async def send_to_channel(self, message: str) -> bool:
        await self.bot.send_message(chat_id=settings.TELEGRAM_CHANNEL_ID, text=message)
        logger.info("message_sent chat_id=%s type=channel", settings.TELEGRAM_CHANNEL_ID)
        return True
