# Этап 1: Анализ и проектирование — Мета-промпт для Cursor

## Контекст проекта

Ты помогаешь разрабатывать систему мониторинга цен конкурентов на автомобильные шины в Иркутске.
Стек: Python 3.11+, PostgreSQL, SQLAlchemy ORM, Alembic (миграции), Docker Compose.

## Целевые сайты для парсинга

| Сайт | URL каталога | Защита | Пагинация |
|------|-------------|--------|-----------|
| avtoshina38.ru | `/catalog/tires/yokohama/` | JS-challenge (cookie) | AJAX "Показать ещё" |
| shinservice.ru | `/catalog/tyres/` | Нет | `?page=N` |
| kolesa-darom.ru | `/catalog/` | Нет | URL-параметры |
| shinapoint.ru | `/catalog/tires/search/{brand}/` | Нет (Bitrix) | `?PAGEN_1=N` |
| ship-ship.ru | `/tyres/` | Нет | `?PAGEN_1=N` |
| supershina38.ru | `/tires/brand/{brand}/{model}` | Нет | Иерархичная навигация |
| express-shina.ru | `/search/legkovyie-shinyi` | Нет | `?num=N` |

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который выполнит следующее:

1. **Создаст `docs/target_sites_analysis.md`** — детальный анализ каждого из 7 сайтов:
   - URL точки входа для парсинга
   - CSS-селекторы для: карточки товара, заголовка, цены, старой цены (зачёркнутой), бренда, сезона, размера
   - Метод пагинации (URL-параметр или AJAX) с примером URL
   - Наличие защиты и способ её обхода
   - Пример 3 реальных товаров с ценами (из собранных данных ниже)

2. **Создаст `db/schema.sql`** — схему БД PostgreSQL со следующими таблицами:
   ```sql
   -- sites: id, name, base_url, catalog_url, is_active, created_at
   -- products: id, site_id, external_id, name, brand, model, season,
   --            tire_size VARCHAR(10),   -- например '175/65'
   --            radius VARCHAR(5),       -- например 'R14'
   --            width INT, profile INT, diameter INT,  -- числовые значения для фильтрации
   --            url, created_at, updated_at
   -- price_history: id, product_id, price, old_price, discount_pct, in_stock, scraped_at
   -- parse_runs: id, site_id, status (pending/running/success/failed), started_at, finished_at, products_found, errors_count
   -- alerts: id, product_id, alert_type, old_value, new_value, triggered_at, sent_at
   ```
   Все таблицы должны иметь правильные индексы: `(product_id, scraped_at)` для `price_history`, `(site_id, external_id)` уникальный для `products`.

3. **Создаст `db/models.py`** — SQLAlchemy модели, соответствующие схеме выше. Использовать `DeclarativeBase`, `mapped_column`, `Mapped` (стиль SQLAlchemy 2.0). Включить `__repr__` для каждой модели.

4. **Создаст `db/database.py`** — конфигурация подключения: `create_async_engine`, `AsyncSession`, `get_session` как async generator для dependency injection.

5. **Создаст `alembic.ini` и `alembic/env.py`** — настроенные для async работы с моделями из `db/models.py`.

6. **Создаст `config.py`** — Pydantic `BaseSettings` с полями:
   - `DATABASE_URL: str`
   - `REDIS_URL: str`
   - `TELEGRAM_BOT_TOKEN: str`
   - `TELEGRAM_CHAT_ID: str`
   - `PROXY_LIST: list[str]` (для ротации прокси при парсинге)
   - `PARSE_INTERVAL_HOURS: int = 6`
   - `PRICE_ALERT_THRESHOLD_PCT: float = 5.0`
   - `PROXY_API_KEY: str`                        # ключ для ProxyAPI (OpenAI-совместимый)
   - `PROXY_BASE_URL: str = "https://openai.api.proxyapi.ru/v1"`
   - `OPENAI_MODEL: str = "gpt-4o-mini"`
   Читать из `.env`, включить `.env.example` со всеми ключами.

7. **Создаст `docker-compose.yml`** с сервисами: `db` (postgres:15), `redis` (redis:7-alpine), `app` (наш Python сервис), `flower` (мониторинг Celery). Volumes для данных postgres.

## Реальные данные для заполнения `docs/target_sites_analysis.md`

### avtoshina38.ru (Иркутск)
- Защита: кастомный JS-challenge, клик по кнопке "I'm not a robot", устанавливает сессионную cookie
- Структура: таблица `<tr>`, цена в `td:nth-child(4)`, название в `td:nth-child(3) a`
- Примеры: Yokohama IG55 175/65R14 — 5 599 ₽; Yokohama IG55 195/65R15 — 6 400 ₽; Yokohama IG55 215/65R16 — 8 899 ₽
- Разбор названия: "Yokohama IG55 175/65R14" → brand="Yokohama", model="IG55", tire_size="175/65", radius="R14", width=175, profile=65, diameter=14

### shinservice.ru
- Защита: нет
- Структура: `.product-card`, цена `.product-card__price`, заголовок `.product-card__title`
- Пагинация: `?page=N`
- Примеры: Nokian Autograph Eco 3 — 5 450 ₽; Cordiant Winter Drive — 6 300 ₽; Formula Ice Fr — 13 050 ₽

### kolesa-darom.ru
- Крупный федеральный магазин с иркутским складом, широкий ассортимент
- Ценовой диапазон: от ~3 000 ₽ до 50 000+ ₽

### shinapoint.ru (Bitrix CMS)
- Защита: нет
- Структура: `.catalog_item.main_item_wrapper`, цена `.price_matrix_wrapper .price_value`, заголовок `.item-title .item_title_span`
- Пагинация: `?PAGEN_1=N`
- Примеры: Pirelli Ice Zero Friction 3 265/65R17 — 17 840 ₽; Pirelli Ice Zero Friction 3 225/45R18 — 22 450 ₽

### ship-ship.ru
- Защита: нет
- Структура: `.product-card`, цена `.product-card__price-value`, пагинация `?PAGEN_1=N`
- Примеры: Ovation VI-786 155/65R13 — 2 451 ₽; LingLong 155/70R13 — 2 458 ₽

### supershina38.ru
- Защита: нет
- Структура: `table tr`, иерархия brand → model → размеры, цена `td:nth-child(4)`
- Примеры: Aplus A609 205/60R16 — 3 590 ₽; Aplus A701 175/65R14 — 2 800 ₽

### express-shina.ru
- Защита: нет
- Структура: `div.b-offer`, цена `.b-offer-pay__price span`, заголовок `.b-offer-main__title`
- Пагинация: `?num=N`
- Примеры: Кама Евро 519 185/60R14 — 3 085 ₽; Nexen WH62 195/55R15 — 4 990 ₽; Matador MP-30 205/60R16 — 6 035 ₽

## Требования к генерируемому Cursor-промпту

Промпт должен:
- Начинаться с описания архитектуры всего проекта (одним абзацем)
- Содержать явные инструкции Cursor создавать файлы поочерёдно, проверяя импорты
- Указывать на использование async везде, где возможно (asyncpg, aiohttp)
- Требовать комментарии на русском языке в коде
- Содержать инструкцию запустить `alembic revision --autogenerate -m "init"` после создания моделей
