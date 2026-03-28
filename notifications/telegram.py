from __future__ import annotations

import logging

from sqlalchemy import select

from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, UserSubscription
from notifications.alert_sender import AlertSender


logger = logging.getLogger("alerts.telegram")


def _subscriber_accepts_change(threshold_pct: float, change_pct_abs: float, old_v: float, new_v: float) -> bool:
    if abs(new_v - old_v) < 1e-9:
        return False
    if threshold_pct <= 0:
        return True
    return change_pct_abs >= threshold_pct


async def send_alert(alert: Alert, *, send_to_main: bool = True) -> bool:
    sender = AlertSender()
    product = alert.product
    if product is None:
        logger.warning("Alert %s skipped: product relation not loaded", alert.id)
        return False

    old_v = float(alert.old_value or 0)
    new_v = float(alert.new_value or 0)
    change_pct_abs = abs((new_v - old_v) / old_v * 100) if old_v > 1e-9 else 0.0
    is_drop = new_v < old_v
    is_rise = new_v > old_v

    async with AsyncSessionLocal() as session:
        subs = list(
            await session.scalars(
                select(UserSubscription).where(
                    UserSubscription.product_id == product.id,
                    UserSubscription.is_active.is_(True),
                )
            )
        )

    if not subs and not send_to_main:
        return True

    any_sent = False
    for sub in subs:
        thr = float(sub.threshold_pct)
        if not _subscriber_accepts_change(thr, change_pct_abs, old_v, new_v):
            continue
        if alert.alert_type in {"price_drop", "new_low"}:
            if not is_drop:
                continue
            ok = await sender.send_price_drop_alert(alert, product, sub.chat_id, use_product_dedup=False)
            any_sent = any_sent or ok
        elif alert.alert_type == "price_rise":
            if not is_rise:
                continue
            ok = await sender.send_price_rise_alert(alert, product, sub.chat_id, use_product_dedup=False)
            any_sent = any_sent or ok
        elif alert.alert_type == "price_changed":
            if is_drop:
                ok = await sender.send_price_drop_alert(alert, product, sub.chat_id, use_product_dedup=False)
            elif is_rise:
                ok = await sender.send_price_rise_alert(alert, product, sub.chat_id, use_product_dedup=False)
            else:
                ok = False
            any_sent = any_sent or ok

    if not send_to_main:
        return any_sent

    if alert.alert_type in {"price_drop", "new_low"}:
        ok = await sender.send_price_drop_alert(alert, product, settings.TELEGRAM_CHAT_ID)
        return any_sent or ok
    if alert.alert_type in {"price_rise"}:
        ok = await sender.send_price_rise_alert(alert, product, settings.TELEGRAM_CHAT_ID)
        return any_sent or ok
    if alert.alert_type == "price_changed":
        if new_v < old_v:
            ok = await sender.send_price_drop_alert(alert, product, settings.TELEGRAM_CHAT_ID)
        elif new_v > old_v:
            ok = await sender.send_price_rise_alert(alert, product, settings.TELEGRAM_CHAT_ID)
        else:
            ok = await sender.send_to_channel(f"Alert price_changed: {product.name}")
        return any_sent or ok
    ok = await sender.send_to_channel(f"Alert {alert.alert_type}: {product.name}")
    return any_sent or ok
