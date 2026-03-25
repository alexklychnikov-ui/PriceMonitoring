# Этап 6: Система уведомлений — Мета-промпт для Cursor

## Контекст проекта

Система мониторинга цен на шины в Иркутске. Этапы 1-5 выполнены.
Есть: таблица `alerts` в БД, Celery-задача `send_pending_alerts()`, FastAPI endpoint для правил алертов.
Задача: реализовать Telegram-бота и полную систему уведомлений.
Стек: **python-telegram-bot 20.x** (async), **Jinja2** (шаблоны сообщений).

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст систему уведомлений.

### Структура файлов

```
notifications/
├── __init__.py
├── telegram_bot.py         # инициализация бота и handlers
├── alert_sender.py         # отправка алертов
├── message_templates.py    # Jinja2 шаблоны сообщений
├── alert_rules.py          # движок правил алертов
└── history.py              # история изменений цен
```

### `notifications/telegram_bot.py`

Реализовать Telegram-бота с командами:

**`/start`** — приветствие, список доступных команд

**`/price <бренд> <модель> <размер>`**
Размер принимается в формате `tire_size R radius`: например `205/60 R16` или `205/60R16`.
Поиск в БД идёт по полям `tire_size` и `radius` (не по `width/profile/diameter`).
```
Пример: /price Yokohama IG55 205/60R16
Ответ:
🔍 Yokohama Ice Guard IG55 • 205/60 • R16

📊 Цены прямо сейчас:
✅ supershina38.ru      — 7 890 ₽  ← ЛУЧШАЯ
   avtoshina38.ru       — 8 200 ₽
   shinservice.ru       — 8 450 ₽
   kolesa-darom.ru      — 8 600 ₽
   shinapoint.ru        — 8 750 ₽
   ship-ship.ru         — 8 900 ₽
   express-shina.ru     — 9 100 ₽

📈 Тренд: снижение -3.2% за последние 7 дней
💡 Рекомендация: хорошее время для покупки
```

**`/watch <бренд> <модель> <размер> [порог%]`**
- Подписать пользователя на алерты по конкретному товару
- `порог%` — при каком изменении цены уведомлять (по умолчанию 5%)
- Сохранить в новую таблицу `user_subscriptions(chat_id, product_id, threshold_pct, created_at)`

**`/unwatch <бренд> <модель> <размер>`** — отписаться

**`/watchlist`** — список активных подписок пользователя

**`/deals [бюджет] [сезон]`**
```
Пример: /deals 8000 winter
Ответ: топ-5 лучших предложений в рамках бюджета
```

**`/report`** — получить AI-сводку за последние 7 дней

**`/status`** — статус системы (когда последний парсинг, сколько сайтов активно)

### `notifications/alert_rules.py`

```python
class AlertRule(BaseModel):
    rule_type: str          # "price_drop" | "price_rise" | "new_low" | "back_in_stock"
    threshold_pct: float    # минимальное изменение для триггера (%)
    brand: str | None       # фильтр по бренду (None = все)
    season: str | None      # фильтр по сезону
    site_name: str | None   # фильтр по сайту
    chat_id: str            # Telegram chat_id

class AlertEngine:
    async def check_and_create_alerts(
        self,
        product: Product,
        old_price: float,
        new_price: float,
        site_name: str
    ) -> list[Alert]:
        """
        Проверяет все правила алертов.
        Создаёт записи в таблице alerts для совпавших правил.
        Возвращает список созданных алертов.
        """

    async def get_global_rules(self) -> list[AlertRule]:
        """Правила из таблицы alert_rules (для всех пользователей)"""

    async def get_user_subscriptions(self, product_id: int) -> list[AlertRule]:
        """Персональные подписки из user_subscriptions"""
```

### `notifications/alert_sender.py`

```python
class AlertSender:
    async def send_price_drop_alert(self, alert: Alert, product: Product): ...
    async def send_price_rise_alert(self, alert: Alert, product: Product): ...
    async def send_new_low_alert(self, alert: Alert, product: Product): ...
    async def send_weekly_digest(self, chat_id: str, report: str): ...
    async def send_parse_error_notification(self, site_name: str, error: str): ...

    async def send_to_channel(self, message: str):
        """Отправить в основной канал мониторинга (TELEGRAM_CHANNEL_ID)"""
```

### `notifications/message_templates.py`

Jinja2-шаблоны для сообщений:

```python
PRICE_DROP_TEMPLATE = """
🟢 *Снижение цены!*

🏪 Магазин: {{ site_name }}
🔖 Товар: {{ product_name }}
📐 Размер: {{ size }}

💰 Было: ~~{{ old_price|format_rub }}~~
💰 Стало: *{{ new_price|format_rub }}*
📉 Снижение: -{{ change_pct }}%
💵 Экономия: {{ savings|format_rub }}

🔗 [Перейти к товару]({{ product_url }})
"""

PRICE_RISE_TEMPLATE = """
🔴 *Рост цены*

🏪 {{ site_name }} | {{ product_name }} ({{ size }})
📈 {{ old_price|format_rub }} → {{ new_price|format_rub }} (+{{ change_pct }}%)
"""

WEEKLY_DIGEST_TEMPLATE = """
📊 *Еженедельный отчёт по рынку шин Иркутска*
📅 {{ week_range }}

📌 *Ключевые цифры:*
• Отслежено изменений: {{ total_changes }}
• Средняя динамика: {{ avg_change }}%
• Лучшие скидки недели: {{ top_deals_count }} позиций

🏆 *Топ снижений:*
{% for deal in top_deals %}
{{ loop.index }}. {{ deal.name }} — {{ deal.new_price|format_rub }} (-{{ deal.change_pct }}%)
{% endfor %}

💡 {{ ai_recommendation }}
"""
```

### `notifications/history.py`

```python
class PriceHistoryFormatter:
    def format_history_chart_url(self, product_id: int, days: int = 30) -> str:
        """Генерировать ссылку на inline-chart через QuickChart API:
        GET https://quickchart.io/chart?c={chart_json}
        Возвращать URL для отправки как photo в Telegram
        """

    def format_history_text(self, history: list[PriceRecord]) -> str:
        """ASCII-представление истории цен для Telegram:
        Дек 20: 8500₽ ████████████████
        Дек 21: 8200₽ ████████████████
        Дек 22: 7890₽ ███████████████
        """
```

### Добавить таблицу `user_subscriptions` в миграцию

```sql
CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(50) NOT NULL,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    threshold_pct FLOAT DEFAULT 5.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chat_id, product_id)
);
CREATE INDEX idx_subscriptions_product ON user_subscriptions(product_id, is_active);
```

### Запуск бота

В `scheduler/tasks.py` добавить:
```python
@app.task
def start_telegram_bot():
    """Запустить polling бота в отдельном процессе"""
    from notifications.telegram_bot import run_bot
    asyncio.run(run_bot())
```

В `docker-compose.yml` добавить сервис `telegram_bot`:
```yaml
telegram_bot:
  build: .
  command: python -m notifications.telegram_bot
  depends_on: [db, redis]
  restart: unless-stopped
```

### Антифлуд

- Не отправлять одинаковые алерты чаще чем раз в 1 час (проверять по `alerts.triggered_at`)
- Группировать несколько алертов по одному товару в одно сообщение
- Rate limiting для команд бота: не более 5 запросов в минуту от одного пользователя

## Требования к генерируемому Cursor-промпту

- Использовать `python-telegram-bot` v20 async API (не старый синхронный)
- `CommandHandler`, `MessageHandler`, `ConversationHandler` для диалогов
- Inline keyboard для интерактивных кнопок (например, подтверждение подписки)
- Все сообщения — Markdown V2 формат, экранировать спецсимволы через `escape_markdown()`
- Добавить `tests/test_notifications.py` с моком Telegram API
- Логировать все отправленные сообщения: chat_id, тип алерта, время
