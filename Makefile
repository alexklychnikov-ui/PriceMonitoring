worker:
	celery -A scheduler.celery_app worker -Q scraping,analysis,notifications,maintenance --loglevel=info

beat:
	celery -A scheduler.celery_app beat --loglevel=info

flower:
	celery -A scheduler.celery_app flower --port=5555

scrape-now:
	celery -A scheduler.celery_app call scheduler.tasks.scrape_all_sites

run-all:
	docker compose up -d db redis
	celery -A scheduler.celery_app worker -Q scraping,analysis,notifications,maintenance --loglevel=info &
	celery -A scheduler.celery_app beat --loglevel=info &
	celery -A scheduler.celery_app flower --port=5555
