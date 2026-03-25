from celery.schedules import crontab

from config import settings


CELERYBEAT_SCHEDULE = {
    "scrape-express-shina-daily-02-00": {
        "task": "scheduler.tasks.scrape_site",
        "schedule": crontab(minute=0, hour=10),
        "args": ("express_shina",),
    },
    "scrape-kolesa-darom-daily-02-00": {
        "task": "scheduler.tasks.scrape_site",
        "schedule": crontab(minute=0, hour=10),
        "args": ("kolesa_darom",),
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
