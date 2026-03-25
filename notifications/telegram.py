from __future__ import annotations

import logging

from config import settings
from db.models import Alert
from notifications.alert_sender import AlertSender


logger = logging.getLogger("alerts.telegram")


async def send_alert(alert: Alert) -> bool:
    sender = AlertSender()
    product = alert.product
    if product is None:
        logger.warning("Alert %s skipped: product relation not loaded", alert.id)
        return False
    if alert.alert_type in {"price_drop", "new_low", "price_changed"}:
        return await sender.send_price_drop_alert(alert, product, settings.TELEGRAM_CHAT_ID)
    if alert.alert_type in {"price_rise"}:
        return await sender.send_price_rise_alert(alert, product, settings.TELEGRAM_CHAT_ID)
    return await sender.send_to_channel(f"Alert {alert.alert_type}: {product.name}")
