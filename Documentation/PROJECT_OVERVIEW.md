# Система мониторинга цен конкурентов на шины — Иркутск
## Архитектурный обзор и навигация по промптам

---

## Цель проекта

Автоматизированная система парсинга цен с 7 сайтов, продающих автомобильные шины в Иркутске.
Отслеживает изменения цен, анализирует тренды с помощью AI, отправляет уведомления через Telegram.

---

## Целевые сайты конкурентов

| # | Сайт | URL | Ценовой диапазон | Особенности |
|---|------|-----|-----------------|-------------|
| 1 | **Авто-Шина 38** | [avtoshina38.ru/catalog/tires/](https://avtoshina38.ru/catalog/tires/) | 2 500–80 000 ₽ | JS-challenge защита, AJAX пагинация |
| 2 | **ШинСервис** | [irkutsk.shinservice.ru/catalog/tyres/](https://irkutsk.shinservice.ru/catalog/tyres/) | 2 550–62 400 ₽ | 4448 товаров, ?page=N |
| 3 | **Колёса Даром** | [irkutsk.kolesa-darom.ru](https://irkutsk.kolesa-darom.ru) | 3 000–50 000 ₽ | Федеральный магазин, рассрочка |
| 4 | **ШинаПоинт** | [shinapoint.ru](https://shinapoint.ru) | 3 500–27 000 ₽ | Bitrix CMS, ?PAGEN_1=N |
| 5 | **Шип-Шип** | [irkutsk.ship-ship.ru/tyres/](https://irkutsk.ship-ship.ru/tyres/) | 2 451–40 000 ₽ | ?PAGEN_1=N, стандартная структура |
| 6 | **СуперШина** | [supershina38.ru/tires](https://supershina38.ru/tires) | 2 800–25 000 ₽ | Иерархия бренд→модель→размеры |
| 7 | **Express-Шина** | [irkutsk.express-shina.ru](https://irkutsk.express-shina.ru) | 3 085–15 000 ₽ | ?num=N, div.b-offer карточки |

### Примеры реальных цен (март 2026)

| Товар | Сайт | Цена |
|-------|------|------|
| Yokohama IG55 175/65R14 | avtoshina38.ru | 5 599 ₽ |
| Yokohama IG55 195/65R15 | avtoshina38.ru | 6 400 ₽ |
| Yokohama IG55 215/65R16 | avtoshina38.ru | 8 899 ₽ |
| Nokian Autograph Eco 3 | shinservice.ru | 5 450 ₽ |
| Cordiant Winter Drive | shinservice.ru | 6 300 ₽ |
| Pirelli Ice Zero Friction 3 265/65R17 | shinapoint.ru | 17 840 ₽ |
| Pirelli Ice Zero Friction 3 225/45R18 | shinapoint.ru | 22 450 ₽ |
| Aplus A609 205/60R16 | supershina38.ru | 3 590 ₽ |
| Nexen WH62 195/55R15 | express-shina.ru | 4 990 ₽ |
| Matador MP-30 205/60R16 | express-shina.ru | 6 035 ₽ |
| Ovation VI-786 155/65R13 | ship-ship.ru | 2 451 ₽ |
| LingLong Green-Max 155/70R13 | ship-ship.ru | 2 458 ₽ |

---

## Технологический стек

```
Backend:        Python 3.11+, FastAPI, SQLAlchemy 2.0 async
База данных:    PostgreSQL 15 + Redis 7
Парсеры:        aiohttp + BeautifulSoup4 + Playwright (для JS-сайтов)
Очереди:        Celery 5 + Celery Beat (cron)
AI-анализ:      LangChain 0.2 + ProxyAPI (gpt-4o-mini) / Ollama llama3.2
Frontend:       React 18 + Vite + Recharts + TanStack Table + Tailwind CSS
Уведомления:    python-telegram-bot 20 (async)
Деплой:         Docker Compose + Nginx + Prometheus + Grafana
CI/CD:          GitHub Actions → SSH deploy
```

---

## Структура файлов промптов

```
prompts/
├── PROJECT_OVERVIEW.md              ← этот файл
├── stage_01_analysis_and_design.md  ← Проектирование (БД, конфиг, Docker)
├── stage_02_parsers.md              ← Парсеры для 7 сайтов
├── stage_03_scheduler.md            ← Celery, очереди, планировщик
├── stage_04_ai_analysis.md          ← LangChain, анализ цен, рекомендации
├── stage_05_frontend_dashboard.md   ← FastAPI API + React дашборд
├── stage_06_notifications.md        ← Telegram-бот, алерты
└── stage_07_deploy.md               ← Продакшн деплой, мониторинг, CI/CD
```

---

## Как использовать промпты в Cursor

### Шаг 1 — Подготовка проекта
```bash
mkdir price-monitor && cd price-monitor
git init
code .  # или cursor .
```

### Шаг 2 — Применение промптов

Каждый файл `stage_NN_*.md` — это **мета-промпт**: его нужно вставить в Cursor Chat с инструкцией:

```
Прочитай этот план и создай промпт для Cursor AI Composer,
который реализует описанный функционал. Промпт должен содержать
конкретные инструкции по созданию файлов, их структуре и содержимому.
```

Затем полученный промпт вставить в **Cursor Composer** (Cmd+I / Ctrl+I) с режимом `Agent`.

### Шаг 3 — Порядок выполнения

```
Этап 1 → Этап 2 → Этап 3 ──→ Этап 4
                              ↓
                           Этап 5 → Этап 6 → Этап 7
```

Этапы 4, 5, 6 можно разрабатывать параллельно после завершения этапа 3.

---

## Схема базы данных (краткая)

```
sites ─────────────── products ────── price_history
  id, name,              id, site_id,      id, product_id,
  base_url,              name, brand,      price, old_price,
  is_active              model, season,    discount_pct,
                         tire_size,        in_stock,
                         radius,           scraped_at
                         width, profile,
                         diameter, url

parse_runs                alerts           user_subscriptions
  id, site_id,             id, product_id,   id, chat_id,
  status,                  alert_type,       product_id,
  started_at,              old_value,        threshold_pct,
  products_found,          new_value,        is_active
  errors_count             sent_at
```

**Логика разбора размера шины (единая для всех парсеров):**
```
Текст: "Yokohama IG55 175/65R14 86T"
       ↓ parse_tire_size(name) — scrapers/utils.py
tire_size = "175/65"   ← VARCHAR(10), читаемый вид, фильтр в UI
radius    = "R14"      ← VARCHAR(5),  фильтр в UI и поиск в Telegram
width     = 175        ← INT, для ORDER BY и точных SQL-запросов
profile   = 65         ← INT
diameter  = 14         ← INT
Индекс: (tire_size, radius) — основной фильтр цены
Индекс: (brand, tire_size, radius) — сравнение цен по сайтам
```

---

## Ключевые архитектурные решения

| Решение | Обоснование |
|---------|-------------|
| async везде (asyncpg, aiohttp) | Парсинг 7 сайтов параллельно без блокировок |
| Celery + Redis | Надёжные очереди, retry при ошибках, cron |
| price_history отдельная таблица | Неограниченная история без UPDATE на products |
| Playwright только для avtoshina38 | JS-challenge только у одного сайта, остальные — aiohttp |
| LLM кэш в Redis (TTL 1-2ч) | Экономия API-токенов на повторных запросах |
| Grafana + Prometheus | Visibility: знаем когда парсер упал без просмотра логов |

---

## Переменные окружения (.env)

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/price_monitor
REDIS_URL=redis://localhost:6379

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_CHANNEL_ID=@your_channel

# LLM провайдер: "openai" = ProxyAPI, "ollama" = локальная модель
LLM_PROVIDER=openai
PROXY_API_KEY=your_proxyapi_key        # вместо OPENAI_API_KEY
PROXY_BASE_URL=https://openai.api.proxyapi.ru/v1
OPENAI_MODEL=gpt-4o-mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Прокси для парсинга (не путать с ProxyAPI!)
PROXY_LIST=http://127.0.0.1:12334
PARSE_INTERVAL_HOURS=6
PRICE_ALERT_THRESHOLD_PCT=5.0

FLOWER_USER=admin
FLOWER_PASSWORD=secure_password
GRAFANA_PASSWORD=secure_password
DOMAIN_NAME=monitor.yourdomain.ru
```

---

## Execution Log (Agent)

### v0.1 — 2026-03-21 19:50:55 +08:00 — Шаг 1 / Этап 1
- Prompt: "общая информация для выполнения проекта @Documentation/PROJECT_OVERVIEW.md Делаем только первых три шага. После каждого шага тестируем всё что можно, пишем отчет и ждем от меня подтверждения для продолжения"
- Сделано:
  - Создана базовая инфраструктура этапа 1: `db/schema.sql`, `db/models.py`, `db/database.py`, `config.py`, `.env.example`, `docker-compose.yml`, `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`
  - Создан анализ целевых сайтов: `docs/target_sites_analysis.md`
  - Уточнены индексы и ограничения в SQL/ORM под фильтрацию по шинам и историю цен
  - Для запуска окружения установлены базовые Python-зависимости в `venv`: SQLAlchemy, asyncpg, Alembic, Pydantic, pydantic-settings
- Тестирование:
  - `python -m compileall db alembic config.py` — OK
  - `python -c "from config import settings; from db.models import Base; from db.database import engine"` — OK (через `venv`)
  - `docker compose config` — OK
  - `docker compose up -d db redis` — FAIL (сетевой TLS timeout при pull образов Docker Hub)
- Статус: Шаг 1 выполнен, ожидание подтверждения перед шагом 2.

### v0.2 — 2026-03-21 20:02:12 +08:00 — Шаг 2 / Этап 2
- Prompt: "там все ключи актуальные. которые можно использовать для тестов Выполняем второй этап"
- Сделано:
  - Создана модульная система парсеров: `scrapers/base.py`, `scrapers/utils.py`, `scrapers/proxy_manager.py`, `scrapers/schemas.py`
  - Реализованы 7 парсеров: `avtoshina38`, `shinservice`, `shinapoint`, `ship_ship`, `supershina38`, `express_shina`, `kolesa_darom`
  - Добавлен `SCRAPERS_REGISTRY` в `scrapers/__init__.py`
  - Реализован `scrapers/db_writer.py` с upsert в `products`, записью в `price_history` и созданием `alerts` при смене цены
  - Добавлены тесты и HTML-фикстуры: `tests/test_parsers.py`, `tests/fixtures/*.html`
  - Добавлен `requirements.txt` под этап 2
- Тестирование:
  - `python -m compileall scrapers tests` — OK
  - `python -m pytest tests/test_parsers.py -q` — OK (9 passed)
  - `python -c "import scrapers; from scrapers import SCRAPERS_REGISTRY; ..."` — OK
- Статус: Шаг 2 выполнен, ожидание подтверждения перед шагом 3.

### v0.3 — 2026-03-21 20:08:58 +08:00 — Шаг 3 / Этап 3
- Prompt: "Отлично! продолжаем, делаем третий этап"
- Сделано:
  - Реализован планировщик и очереди: `scheduler/celery_app.py`, `scheduler/tasks.py`, `scheduler/beat_schedule.py`, `scheduler/monitoring.py`, `scheduler/__init__.py`
  - Добавлен health-check endpoint `/health` в `scheduler/monitoring.py` (FastAPI app `health_app`)
  - Добавлено логирование: `logging/config.py` (stdout + rotating file `logs/app.log`)
  - Добавлен модуль уведомлений: `notifications/telegram.py`, `notifications/__init__.py`
  - Добавлен `Makefile` для запуска worker/beat/flower/scrape-now
  - Расширен `requirements.txt` для этапа 3 (`celery`, `redis`, `fastapi`, `uvicorn`)
  - Добавлены тесты задач: `tests/test_tasks.py` (mock/fake сценарии для `scrape_site` и обновления `parse_runs`)
- Тестирование:
  - `python -m compileall scheduler notifications tests/test_tasks.py` — OK
  - `python -m pytest tests/test_tasks.py -q` — OK (3 passed)
  - `python -m pytest tests/test_parsers.py -q` — OK (9 passed, регрессия)
  - `python -c "from scheduler.celery_app import app; from scheduler.monitoring import health_app; ..."` — OK
- Статус: Шаг 3 выполнен.

### v0.4 — 2026-03-21 20:39:04 +08:00 — Шаг 4 / Этап 4
- Prompt: "хоршо, я доверяю тебе. Делаем четвертый этап. Финально всё тестируем и закончим на сегодня"
- Сделано:
  - Добавлен AI-модуль: `ai_analysis/price_analyzer.py`, `ai_analysis/recommendation_engine.py`, `ai_analysis/prompts.py`, `ai_analysis/tools.py`, `ai_analysis/reports.py`, `ai_analysis/cache.py`, `ai_analysis/__init__.py`
  - Добавлен `PriceAnalyzer` для трендов, аномалий и сравнения цен по сайтам
  - Добавлен `RecommendationEngine` с поддержкой `openai` (через ProxyAPI) и `ollama`, Redis TTL-кэшем и fallback-ответами без LLM
  - Добавлено логирование использованных токенов в AI-вызовах
  - Дополнен `scheduler/tasks.py` задачей `analyze_prices_task` и связкой `chord()` после `scrape_all_sites`
  - Усилен `scheduler/monitoring.py`: `/health` больше не падает при недоступных Redis/DB/Celery, возвращает статус `ok=false`
  - Обновлены зависимости в `requirements.txt` под этап 4
  - Добавлены тесты AI: `tests/test_ai_analysis.py` (с моками LLM и кэша)
- Тестирование:
  - `python -m compileall ai_analysis scheduler tests` — OK
  - `python -m pytest tests/test_ai_analysis.py -q` — OK (2 passed)
  - `python -m pytest tests/test_parsers.py -q` — OK (9 passed)
  - `python -m pytest tests/test_tasks.py -q` — OK (3 passed)
  - `python -m pytest -q` — OK (14 passed)
  - `python -c "import asyncio; from scheduler.monitoring import get_system_status; ..."` — OK (возвращает dict даже без сервисов)
- Статус: Шаг 4 выполнен, проект готов к паузе на сегодня.

### v0.5-v0.6 — 2026-03-25 09:56:59 +08:00 — Шаг 5-6 / Этапы 5-6
- Prompt: "отлично, продолжим выполнение этапов 5 и 6 @Documentation/PROJECT_OVERVIEW.md:102"
- Сделано (Этап 5):
  - Поднят FastAPI API: `api/main.py`, `api/schemas.py`, `api/routers/{products,sites,analytics,settings}.py`
  - Реализованы ключевые эндпоинты каталога/аналитики/настроек, включая `/api/products/{id}/ai-analysis`
  - Добавлен фронтенд-каркас Vite+React+TS: `frontend/*` (страницы Dashboard/Products/ProductDetail/Analytics/Settings, hooks, client, типы, proxy в `vite.config.ts`)
  - Добавлен `frontend/README.md` с запуском
- Сделано (Этап 6):
  - Расширена схема и ORM: таблицы `user_subscriptions`, `alert_rules` (`db/schema.sql`, `db/models.py`, `db/__init__.py`)
  - Реализованы модули уведомлений: `notifications/{telegram_bot,alert_sender,message_templates,alert_rules,history}.py`
  - Добавлена интеграция в scheduler: `start_telegram_bot` task, обновлен `send_pending_alerts`, маршрутизация в `scheduler/celery_app.py`
  - Обновлен `docker-compose.yml`: сервис `telegram_bot`, `app` запускает `uvicorn api.main:app`
  - Обновлены зависимости в `requirements.txt` (`python-telegram-bot`, `jinja2`)
- Тестирование:
  - `python -m compileall api notifications frontend/src db scheduler tests` — OK
  - `python -m pytest -q` — OK (17 passed)
  - `python -c "from api.main import app; import notifications.telegram_bot as bot; ..."` — OK
  - `python -m pip install python-telegram-bot jinja2` — OK
- Статус: Шаги 5 и 6 выполнены, финальный прогон тестов успешен.

### v0.7 — 2026-03-25 10:09:08 +08:00 — Pre-deploy интеграционный прогон
- Prompt: "давай перед деплоем сделаем максимальные тесты всех этапов в их взаимодействии"
- Сделано:
  - Прогнан полный тестовый контур Python по всем этапам
  - Проверены импорты/синтаксис модулей API/AI/Scrapers/Scheduler/Notifications
  - Прогнан frontend production build
  - Проверена валидность `docker-compose.yml`
  - Выполнен smoke запрос к API (`/`) и попытка интеграции эндпоинтов, требующих БД
- Результаты:
  - `python -m pytest -q` — OK (17 passed)
  - `python -m compileall api ai_analysis scrapers scheduler notifications` — OK
  - `frontend: npm install && npm run build` — OK (vite build successful)
  - `docker compose config` — OK
  - `GET /` (FastAPI TestClient) — OK (200)
  - Эндпоинты с БД (`/api/analytics/overview`) — FAIL из-за `asyncpg.exceptions.ConnectionDoesNotExistError` на локальном подключении
  - `docker compose up -d app telegram_bot` — FAIL по сети (Docker Hub EOF при pull `python:3.11-slim`)
- Статус: функциональный код протестирован максимально в текущем окружении; блокеры перед деплоем зафиксированы (сеть Docker Hub + локальная asyncpg-коннективность).

### v0.8 — 2026-03-25 10:22:30 +08:00 — Fix блокеров pre-deploy
- Prompt: "можешь сам починить эти блокеры?"
- Сделано:
  - Повторный pull `python:3.11-slim` — успешно (снят сетевой блокер Docker Hub)
  - Обновлен `docker-compose.yml`:
    - `app` и `telegram_bot` используют внутренние адреса `db/redis`
    - команды запуска дополнены установкой зависимостей (`pip install -r requirements.txt`) перед стартом
  - Обновлен `db/database.py` для Windows-runtime устойчивости (SelectorEventLoopPolicy + `connect_args={"ssl": False}`)
  - Инициализирована схема в контейнерной БД из `db/schema.sql`
  - Подняты сервисы `app` и `telegram_bot` в Docker
  - Проверены runtime-запросы к API по HTTP с хоста
- Тестирование/валидация:
  - `docker compose config` — OK
  - `docker compose up -d app telegram_bot` — OK
  - `docker compose ps` — `db`, `redis`, `app`, `telegram_bot` в статусе Up/healthy
  - `GET http://127.0.0.1:8000/` — 200
  - `GET http://127.0.0.1:8000/api/analytics/overview` — 200 (`{"products_count":0,...}`)
- Статус: критичные блокеры перед деплоем устранены, контейнерная связка API+DB+Redis+TelegramBot стартует и отвечает.

### v0.9 — 2026-03-25 10:31:39 +08:00 — Разделение этапа 7 на 2 плана
- Prompt: "Прочитай @Documentation/stage_07_deploy.md и если есть необходимость раздели это на два промпта..."
- Сделано:
  - Сформирован отдельный промпт-план для локальной Windows части деплоя:
    - `Documentation/stage_07_deployWindows.md`
  - Сформирован отдельный промпт-план только для серверной Ubuntu части деплоя:
    - `Documentation/stage_07_deployServer.md`
  - Содержимое разделено по зонам ответственности: подготовка/CI/CD/секреты на Windows и инфраструктурный rollout/SSL/backup/monitoring на сервере.
- Статус: этап 7 декомпозирован на два конечных плана деплоя.

### v1.0 — 2026-03-25 10:44:23 +08:00 — Подготовка Windows-части этапа 7 к push
- Prompt: "выполняем @Documentation/stage_07_deployWindows.md для пуша используй https://github.com/alexklychnikov-ui/PriceMonitoring.git"
- Сделано:
  - Прогнаны локальные проверки готовности:
    - `venv\Scripts\python -m pytest -q` (17 passed)
    - `frontend: npm ci && npm run build` (OK)
    - `docker compose config` (OK)
  - Добавлена структура production-деплоя в репозиторий:
    - `deploy/docker-compose.prod.yml`
    - `deploy/nginx/nginx.conf`
    - `deploy/nginx/conf.d/app.conf`
    - `deploy/scripts/{deploy.sh,backup.sh,healthcheck.sh}`
    - `deploy/monitoring/prometheus.yml`
    - `deploy/monitoring/grafana/dashboards/price_monitor.json`
    - `deploy/.env.prod.example`
  - Добавлен CI/CD workflow:
    - `.github/workflows/deploy.yml`
  - Добавлены базовые файлы для релизной публикации:
    - `.gitignore` (исключение секретов/локальных артефактов)
    - `Dockerfile` (базовая сборка production образа)
- Статус: Windows-часть этапа 7 подготовлена к git init, коммиту и push в remote.
