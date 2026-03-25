from __future__ import annotations

import asyncio

from notifications.alert_sender import AlertSender
from notifications.message_templates import PRICE_DROP_TEMPLATE, render_template
from notifications.telegram_bot import _is_rate_limited


class _FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id: str, text: str, parse_mode=None):
        self.messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})
        return True


def test_template_render_price_drop():
    text = render_template(
        PRICE_DROP_TEMPLATE,
        site_name="site",
        product_name="Yokohama IG55",
        size="205/60 R16",
        old_price=9000,
        new_price=8000,
        change_pct=11.1,
        savings=1000,
        product_url="https://example.com",
    )
    assert "Снижение цены" in text
    assert "205/60 R16" in text


def test_rate_limit_basic():
    chat_id = 111
    for _ in range(5):
        assert _is_rate_limited(chat_id) is False
    assert _is_rate_limited(chat_id) is True


def test_alert_sender_channel(monkeypatch):
    sender = AlertSender()
    fake = _FakeBot()
    sender.bot = fake
    asyncio.run(sender.send_to_channel("hello"))
    assert len(fake.messages) == 1
