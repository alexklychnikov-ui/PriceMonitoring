from celery.schedules import crontab

from config import settings


CELERYBEAT_SCHEDULE = {
    "scrape-all-every-6-hours": {
        "task": "scheduler.tasks.scrape_all_sites",
        "schedule": crontab(minute=0, hour=f"*/{max(settings.PARSE_INTERVAL_HOURS, 1)}"),
    },
    "send-alerts-every-5-min": {
        "task": "scheduler.tasks.send_pending_alerts",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup-weekly": {
        "task": "scheduler.tasks.cleanup_old_data",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),
    },
}
