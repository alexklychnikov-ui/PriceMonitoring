from celery import Celery

from config import settings
from scheduler.beat_schedule import CELERYBEAT_SCHEDULE


app = Celery(
    "price_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["scheduler.tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Irkutsk",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule=CELERYBEAT_SCHEDULE,
    task_routes={
        "scheduler.tasks.scrape_site": {"queue": "scraping"},
        "scheduler.tasks.scrape_all_sites": {"queue": "scraping"},
        "scheduler.tasks.analyze_prices": {"queue": "analysis"},
        "scheduler.tasks.analyze_prices_task": {"queue": "analysis"},
        "scheduler.tasks.send_pending_alerts": {"queue": "notifications"},
        "scheduler.tasks.start_telegram_bot": {"queue": "notifications"},
        "scheduler.tasks.cleanup_old_data": {"queue": "maintenance"},
    },
)
