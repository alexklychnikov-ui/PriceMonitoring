from datetime import timedelta

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "scrape-all-sites-hourly-check": {
        "task": "scheduler.tasks.scrape_all_sites",
        "schedule": timedelta(hours=1),
    },
    "send-alerts-every-5-min": {
        "task": "scheduler.tasks.send_pending_alerts",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup-weekly": {
        "task": "scheduler.tasks.cleanup_old_data",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),
    },
    "close-stale-parse-runs": {
        "task": "scheduler.tasks.close_stale_parse_runs",
        "schedule": timedelta(hours=6),
    },
}
