# Промпт 1: План деплоя со стороны Windows (локальная машина)

Ты помогаешь подготовить и выполнить локальную часть продакшн-деплоя проекта PriceMonitoring.
Нужно сделать только то, что выполняется на Windows, а не на сервере.

## Цель
- Подготовить проект к продакшн-деплою.
- Собрать и проверить артефакты.
- Подготовить секреты и CI/CD.
- Передать серверу готовый репозиторий и инструкции.

## Шаги (Windows)

1) **Актуализация репозитория**
- Перейти в корень проекта.
- Проверить, что рабочее дерево чистое.
- Обновить `main`, убедиться, что все изменения этапов 1-6 и pre-deploy фиксы сохранены.

2) **Локальные проверки перед релизом**
- Прогнать Python тесты:
  - `python -m pytest -q`
- Прогнать сборку frontend:
  - `cd frontend && npm install && npm run build`
- Проверить конфиг compose:
  - `docker compose config`
- Проверить API smoke локально (если контейнеры подняты):
  - `GET /`
  - `GET /api/analytics/overview`

3) **Подготовка production-конфигов в репозитории**
- Создать/обновить:
  - `deploy/docker-compose.prod.yml`
  - `deploy/nginx/nginx.conf`
  - `deploy/nginx/conf.d/app.conf`
  - `deploy/scripts/deploy.sh`
  - `deploy/scripts/backup.sh`
  - `deploy/scripts/healthcheck.sh`
  - `deploy/monitoring/prometheus.yml`
  - `deploy/monitoring/grafana/dashboards/price_monitor.json`
- Добавить `deploy/.env.prod.example` (без реальных секретов).

4) **Секреты и переменные (локально не хардкодить)**
- Подготовить значения для:
  - `DB_PASSWORD`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `TELEGRAM_CHANNEL_ID`
  - `PROXY_API_KEY`
  - `FLOWER_USER`, `FLOWER_PASSWORD`
  - `GRAFANA_PASSWORD`
  - `DOMAIN_NAME`
- Проверить, что в git нет утечки реальных ключей.

5) **CI/CD настройка из Windows**
- Добавить workflow:
  - `.github/workflows/deploy.yml`
- В GitHub Secrets завести:
  - `SERVER_HOST`
  - `SERVER_USER`
  - `SSH_PRIVATE_KEY`
  - (при необходимости) дополнительные prod секреты

6) **Подготовка SSH доступа к серверу**
- Проверить вход:
  - `ssh alexklyvibe@193.168.196.12`
- Проверить, что деплой-пользователь имеет права на `/opt/price_monitor`.

7) **Релизный push**
- Запушить `main` с файлами деплоя.
- Убедиться, что workflow стартует автоматически при push в `main`.

## Готовность к переходу на сервер (Definition of Ready)
- Python тесты зеленые.
- Frontend build успешен.
- `docker compose config` валиден.
- Все `deploy/*` файлы есть.
- `deploy/.env.prod.example` заполнен корректно.
- GitHub Actions deploy workflow и secrets настроены.
