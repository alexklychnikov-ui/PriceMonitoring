# Промпт 2: План деплоя на Ubuntu сервере (только серверная часть)

Ты выполняешь только серверные действия для продакшн-деплоя PriceMonitoring.
Сервер: `193.168.196.12`, пользователь: `alexklyvibe`, ОС: Ubuntu 22.04.

## Цель
- Развернуть продакшн окружение через Docker Compose.
- Поднять API, worker, beat, telegram bot, nginx, monitoring.
- Включить SSL, backup, healthcheck и автодеплой.

## Шаги (Server only)

1) **Первичная подготовка Ubuntu**
- Обновить систему:
  - `sudo apt update && sudo apt upgrade -y`
- Установить:
  - `git`, `curl`, `ca-certificates`, `gnupg`, `docker`, `docker compose plugin`
- Включить Docker:
  - `sudo systemctl enable --now docker`

2) **Развернуть код проекта**
- Создать директорию:
  - `/opt/price_monitor`
- Клонировать репозиторий:
  - `git clone <repo_url> /opt/price_monitor`
- Перейти в `/opt/price_monitor`.

3) **Подготовить production env**
- Создать `.env.prod` из `deploy/.env.prod.example`.
- Заполнить реальными значениями:
  - БД, Telegram, ProxyAPI, домен, пароли Flower/Grafana.
- Убедиться, что в `deploy/docker-compose.prod.yml` сервисы читают `.env.prod`.

4) **SSL и Nginx**
- Настроить `deploy/nginx/conf.d/app.conf` на домен `alexklyvibe.ru`.
- Получить SSL сертификат Let's Encrypt (certbot).
- Проверить, что Nginx видит:
  - `fullchain.pem`
  - `privkey.pem`

5) **Первый запуск сервисов**
- Запуск:
  - `docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d --build`
- Проверка:
  - `docker compose -f deploy/docker-compose.prod.yml ps`
  - все сервисы должны быть `Up`/`healthy`.

6) **Миграции и инициализация**
- Применить миграции:
  - `docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod run --rm api alembic upgrade head`
- Проверить таблицы (`products`, `price_history`, `alerts`, `user_subscriptions`, `alert_rules`).

7) **Проверки после запуска**
- Выполнить `deploy/scripts/healthcheck.sh`.
- Проверить вручную:
  - `https://alexklyvibe.ru` (frontend)
  - `https://alexklyvibe.ru/docs` (FastAPI docs)
  - `/api/analytics/overview` (ожидается 200)
- Проверить Celery:
  - inspect ping / очереди / beat schedule.
- Проверить Telegram bot:
  - команда `/start`.

8) **Мониторинг и наблюдаемость**
- Поднять Prometheus + Grafana.
- В Grafana подключить дашборд `price_monitor.json`.
- Проверить панели: API latency, queue depth, active alerts, parse runs.

9) **Резервное копирование**
- Настроить cron:
  - `0 2 * * * /opt/price_monitor/deploy/scripts/backup.sh`
- Проверить создание `.sql.gz` и ротацию (удаление старше 7 дней).

10) **Автообновление и эксплуатация**
- Включить Watchtower (если включен в prod compose).
- Проверить лог-файлы и restart policy.
- Задокументировать rollback:
  - предыдущий git commit + `docker compose up -d` с прошлой версией.

## Definition of Done (Server)
- Все prod контейнеры подняты и healthy.
- HTTPS работает, сертификат валиден.
- API/Frontend/Telegram bot доступны.
- Celery worker/beat выполняют задачи.
- Мониторинг и backup настроены.
- CI/CD deploy из `main` проходит без ручных хотфиксов.
