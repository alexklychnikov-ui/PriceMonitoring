# Этап 3: Планировщик задач — Мета-промпт для Cursor

## Контекст проекта

Система мониторинга цен на шины в Иркутске. Этапы 1-2 выполнены.
Есть: модели БД, 7 парсеров с `BaseScraper`, `ProductDTO`, `SCRAPERS_REGISTRY`.
Стек планировщика: **Celery 5.x** + **Redis** (брокер + бэкенд), **Celery Beat** (cron), **Flower** (UI).

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст систему очередей и планировщика.

### Структура файлов

```
scheduler/
├── celery_app.py       # инициализация Celery
├── tasks.py            # все Celery-задачи
├── beat_schedule.py    # расписание запусков
└── monitoring.py       # health-check и метрики
```

### `scheduler/celery_app.py`

```python
from celery import Celery
from config import settings

app = Celery(
    "price_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["scheduler.tasks"]
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Irkutsk",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # подтверждать после выполнения
    worker_prefetch_multiplier=1,  # не брать следующую задачу до завершения текущей
    task_routes={
        "scheduler.tasks.scrape_site": {"queue": "scraping"},
        "scheduler.tasks.analyze_prices": {"queue": "analysis"},
        "scheduler.tasks.send_alerts": {"queue": "notifications"},
    }
)
```

### `scheduler/tasks.py`

Реализовать следующие задачи:

**`scrape_site(site_name: str)`**
- Получить scraper из `SCRAPERS_REGISTRY[site_name]`
- Обновить `parse_runs.status = "running"`, `started_at = now()`
- Запустить `asyncio.run(scraper.run())`
- Для каждого ProductDTO вызвать `db_writer.upsert_product()`
- Обновить `parse_runs.status = "success"`, `finished_at`, `products_found`
- При исключении: `status = "failed"`, записать `errors_count`, логировать
- Retry: `max_retries=3`, `countdown=60` (через 60 сек при ошибке)
- Таймаут задачи: `time_limit=1800` (30 минут)

**`scrape_all_sites()`**
- Запустить `scrape_site.delay(name)` для всех активных сайтов из БД
- Использовать `group()` для параллельного запуска
- Возвращать `GroupResult` для отслеживания прогресса

**`analyze_prices()`**
- Вызывается после успешного парсинга через `link()` или `chord()`
- Запустить AI-анализ (заглушка на этом этапе, будет реализован в Этапе 4)
- Сохранить результат анализа в Redis с TTL 24 часа

**`send_pending_alerts()`**
- Выбрать из БД алерты где `sent_at IS NULL`
- Вызвать `notifications.telegram.send_alert(alert)` для каждого
- Обновить `alerts.sent_at = now()`
- Запускать каждые 5 минут

**`cleanup_old_data()`**
- Удалить записи `price_history` старше 90 дней
- Удалить завершённые `parse_runs` старше 30 дней
- Запускать раз в неделю

### `scheduler/beat_schedule.py`

```python
CELERYBEAT_SCHEDULE = {
    "scrape-all-every-6-hours": {
        "task": "scheduler.tasks.scrape_all_sites",
        "schedule": crontab(minute=0, hour="*/6"),  # каждые 6 часов
    },
    "send-alerts-every-5-min": {
        "task": "scheduler.tasks.send_pending_alerts",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup-weekly": {
        "task": "scheduler.tasks.cleanup_old_data",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),  # понедельник 03:00
    },
}
```

### `scheduler/monitoring.py`

```python
async def get_system_status() -> dict:
    """Возвращает статус всех компонентов:
    - Redis: ping latency
    - DB: connection pool stats
    - Celery workers: active, reserved, scheduled tasks
    - Last parse run per site: status, time, products_found
    - Pending alerts count
    """

async def get_parse_stats(hours: int = 24) -> dict:
    """Статистика парсинга за последние N часов:
    - Успешных/неудачных запусков по сайтам
    - Среднее время парсинга
    - Количество найденных товаров
    - Количество изменений цен
    """
```

### Логирование

Настроить `logging/config.py`:
- Формат: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- Уровни: DEBUG для парсеров, INFO для задач, WARNING для алертов
- Handlers: `StreamHandler` (stdout) + `RotatingFileHandler` (`logs/app.log`, max 10MB, 5 backup)
- Отдельный logger для каждого парсера: `logging.getLogger(f"scraper.{site_name}")`

### `Makefile` для запуска

```makefile
worker:
    celery -A scheduler.celery_app worker -Q scraping,analysis,notifications --loglevel=info

beat:
    celery -A scheduler.celery_app beat --loglevel=info

flower:
    celery -A scheduler.celery_app flower --port=5555

scrape-now:
    celery -A scheduler.celery_app call scheduler.tasks.scrape_all_sites

run-all:
    docker-compose up -d db redis
    make worker &
    make beat &
    make flower
```

## Требования к генерируемому Cursor-промпту

- Все задачи должны быть идемпотентными (повторный запуск не ломает данные)
- Добавить `@app.task(bind=True)` для задач с retry, чтобы иметь доступ к `self.retry()`
- Включить health-check endpoint: простой Flask/FastAPI маршрут `/health` который проверяет Redis и DB
- Добавить `tests/test_tasks.py` с моком для `asyncio.run` и проверкой что задачи корректно обновляют `parse_runs`
- Все временные зоны — `Asia/Irkutsk` (UTC+8)
