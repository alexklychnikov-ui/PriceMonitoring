# Price Monitor

Система мониторинга цен на шины: сбор данных с магазинов, хранение истории цен, API + веб-интерфейс, Telegram-бот и алерты.

## Руководство пользователя

Для работы без технических деталей используйте отдельное руководство: `UserGuide.md`, либо `Руководство пользователя Price Monitor.docx`

## Что делает проект

- Парсит товары с сайтов шинных магазинов.
- Хранит каталог товаров и историю цен в PostgreSQL.
- Отслеживает изменения цен (рост/падение) и формирует алерты.
- Отправляет уведомления в Telegram (канал и подписки пользователей).
- Показывает аналитику в веб-интерфейсе и Grafana.
- Даёт API для каталога, настроек, аналитики и подписок.

## Стек

- Backend/API: `FastAPI`, `SQLAlchemy (async)`, `Celery`, `Redis`
- Парсинг: `aiohttp`, `BeautifulSoup`, `lxml`
- БД: `PostgreSQL`
- Frontend: `React + TypeScript + Vite` (папка `frontend/`)
- Notifications: `python-telegram-bot`
- Monitoring: `Flower`, `Grafana` (Prometheus подготовлен, но не задействован в текущем контуре)
- AI/LLM (опционально): `OpenAI-compatible API` (через ProxyAPI) или `Ollama`

## Структура проекта

- `api/` — FastAPI роуты (`/api/products`, `/api/settings`, `/api/analytics`, `/api/sites`)
- `scheduler/` — Celery задачи и расписание
- `scrapers/` — парсеры площадок + запись в БД
- `notifications/` — Telegram-бот и отправка алертов
- `db/` — ORM модели и SQL-схема
- `frontend/` — веб-интерфейс
- `deploy/` — production compose, nginx, monitoring
- `ai_analysis/` — AI-аналитика и рекомендации

## Требования

- Docker + Docker Compose
- (для локального frontend dev) Node.js 18+
- (опционально, без Docker) Python 3.11+

## Быстрый старт (локально, Docker)

1) Скопируйте пример env:

```bash
cp .env.example .env
```

2) Заполните минимум в `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `PROXY_API_KEY` (если нужен AI-блок; иначе будет fallback без LLM)

3) Запустите сервисы локального compose:

```bash
docker compose up -d
```

4) Проверка:

- API: `http://localhost:8000/`
- Swagger (Basic Auth): `http://localhost:8000/docs`
- Flower: `http://localhost:5555`

## Production запуск

Используется файл `deploy/docker-compose.prod.yml`.

1) Подготовьте `.env` в корне проекта (используется через `env_file: ../.env`).

Минимально важные переменные:

- `DB_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FLOWER_USER`, `FLOWER_PASSWORD`
- `GRAFANA_PASSWORD`
- `DOMAIN_NAME`
- `CORS_ORIGINS`

2) Сборка и запуск:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build
```

3) Проверка статуса:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env ps
```

## Frontend

### Локальная разработка

```bash
cd frontend
npm install
npm run dev
```

### Прод-сборка

```bash
cd frontend
npm install
npm run build
```

Сборка попадает в `frontend/dist` и в production отдаётся через `nginx` из `deploy/docker-compose.prod.yml`.

## Переменные окружения

Смотрите `.env.example`. Основные группы:

- **DB/Redis**: `DATABASE_URL`, `REDIS_URL`, `DB_PASSWORD`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_BOT_USERNAME`
- **Alerts/Parsing**: `PARSE_INTERVAL_HOURS`, `PRICE_ALERT_THRESHOLD_PCT`, `PRUNE_PRODUCTS_INACTIVE_DAYS`
- **LLM**: `LLM_PROVIDER`, `PROXY_API_KEY`, `PROXY_BASE_URL`, `OPENAI_MODEL`, `OLLAMA_*`
- **Web/API**: `DOMAIN_NAME`, `PUBLIC_SITE_URL`, `CORS_ORIGINS`, `SUBSCRIPTION_WEB_KEY`
- **Monitoring**: `FLOWER_USER`, `FLOWER_PASSWORD`, `GRAFANA_PASSWORD`

## Основные API точки

- `GET /api/products` — каталог товаров
- `GET /api/products/{id}` — карточка товара
- `GET /api/analytics/overview` — ключевые метрики
- `GET /api/settings/runtime` / `PUT /api/settings/runtime` — runtime-настройки
- `GET /api/settings/sites` / `PUT /api/settings/sites` — настройки сайтов
- `POST /api/settings/scrape-now` — ручной запуск парсинга
- `GET /api/settings/parsing-status` — статус последнего/следующего запуска

Документация API: `/docs` (защищена Basic Auth, логин/пароль берутся из `FLOWER_USER` / `FLOWER_PASSWORD`).

## Telegram-бот

- Запускается как сервис `telegram_bot`.
- Поддерживает меню, поиск цен, подписки, отчёты и статус системы.
- Для подписок с web-интерфейса используются API `/api/products/{id}/subscription`.

## Мониторинг

- Flower: очередь Celery и задачи
- Grafana: дашборды проекта (в `deploy/monitoring/grafana/dashboards`)
- Prometheus: сервис присутствует в `deploy/docker-compose.prod.yml`, но в текущем состоянии не используется полноценно (нет `/metrics` у API и не подключен Redis exporter)

## Полезные команды

Логи API:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env logs -f api
```

Логи воркера:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env logs -f worker
```

Логи Telegram-бота:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env logs -f telegram_bot
```

Перезапуск ключевых сервисов:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file .env up -d --build api worker beat telegram_bot nginx
```

## Типовые проблемы

- **`/docs` возвращает 401** — это ожидаемо, нужен Basic Auth (`FLOWER_USER` / `FLOWER_PASSWORD`).
- **AI-блок не работает, в логах 401** — проверьте `PROXY_API_KEY` (не должен быть заглушкой).
- **Нет данных в Telegram/аналитике** — проверьте активность сайтов в `Settings` и логи `worker`.
- **Webhook/подписки с фронта не проходят** — проверьте `CORS_ORIGINS`, `PUBLIC_SITE_URL`, `DOMAIN_NAME`.

## Безопасность

- Не коммитьте `.env` и реальные ключи.
- Для web-подписок можно включить `SUBSCRIPTION_WEB_KEY` и передавать `X-Subscription-Key`.
- Для внешнего доступа обязательно держите reverse proxy + HTTPS.
