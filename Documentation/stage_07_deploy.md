# Этап 7: Деплой и оптимизация — Мета-промпт для Cursor

## Контекст проекта

Система мониторинга цен на шины в Иркутске. Этапы 1-6 выполнены.
Целевой сервер: Ubuntu 22.04, Docker + Docker Compose, Nginx, домен (или IP).
Задача: продакшн-деплой с мониторингом, оптимизацией и автообновлением.
Сервер для подключения: 193.168.196.12
Домен : alexklyvibe.ru
Подключение: ssh alexklyvibe (настроен ключ SSH)

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст полную инфраструктуру деплоя.

### Структура файлов деплоя

```
deploy/
├── docker-compose.prod.yml   # продакшн compose
├── nginx/
│   ├── nginx.conf
│   └── conf.d/app.conf       # конфиг виртуального хоста
├── scripts/
│   ├── deploy.sh             # скрипт деплоя
│   ├── backup.sh             # бэкап БД
│   └── healthcheck.sh        # проверка всех сервисов
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/price_monitor.json
└── .github/
    └── workflows/
        └── deploy.yml        # CI/CD pipeline
```

### `deploy/docker-compose.prod.yml`

```yaml
version: "3.9"
services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/backup.sh:/backup.sh
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: price_monitor
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped

  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
    depends_on: {db: {condition: service_healthy}, redis: {condition: service_started}}
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@db/price_monitor
      REDIS_URL: redis://redis:6379
    restart: unless-stopped
    labels:
      - "com.centurylinklabs.watchtower.enable=true"  # автообновление образа

  worker:
    build: .
    command: celery -A scheduler.celery_app worker -Q scraping,analysis,notifications -c 2
    depends_on: [db, redis]
    restart: unless-stopped

  beat:
    build: .
    command: celery -A scheduler.celery_app beat --loglevel=info
    depends_on: [db, redis]
    restart: unless-stopped

  telegram_bot:
    build: .
    command: python -m notifications.telegram_bot
    depends_on: [db, redis]
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - certbot_data:/etc/letsencrypt
      - frontend_build:/usr/share/nginx/html
    depends_on: [api]
    restart: unless-stopped

  flower:
    build: .
    command: celery -A scheduler.celery_app flower --port=5555 --basic-auth=${FLOWER_USER}:${FLOWER_PASSWORD}
    depends_on: [redis]
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  certbot_data:
  frontend_build:
```

### `deploy/nginx/conf.d/app.conf`

```nginx
upstream api_backend {
    server api:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name ${DOMAIN_NAME};

    # Перенаправление на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN_NAME};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

    # Frontend (React build)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        gzip_static on;
        expires 1d;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
        proxy_cache_valid 200 1m;  # кэшировать ответы API на 1 минуту
    }

    # Flower (закрыт от публики, только через туннель или IP whitelist)
    location /flower/ {
        proxy_pass http://flower:5555/;
        allow 127.0.0.1;
        deny all;
    }

    # Rate limiting для API
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    location /api/products {
        limit_req zone=api burst=10;
        proxy_pass http://api_backend;
    }
}
```

### `deploy/scripts/deploy.sh`

```bash
#!/bin/bash
set -e

echo "🚀 Запуск деплоя..."

# 1. Собрать frontend
echo "📦 Сборка frontend..."
cd frontend && npm ci && npm run build
docker cp ./dist/. price_monitor_nginx_1:/usr/share/nginx/html/
cd ..

# 2. Собрать и обновить Docker образы
echo "🐳 Обновление Docker образов..."
docker-compose -f deploy/docker-compose.prod.yml build --no-cache app

# 3. Применить миграции БД
echo "🗃️ Применение миграций..."
docker-compose -f deploy/docker-compose.prod.yml run --rm api alembic upgrade head

# 4. Перезапустить сервисы без downtime
echo "🔄 Перезапуск сервисов..."
docker-compose -f deploy/docker-compose.prod.yml up -d --no-deps --build api worker beat telegram_bot

# 5. Health check
echo "✅ Проверка работоспособности..."
sleep 10
bash deploy/scripts/healthcheck.sh

echo "🎉 Деплой успешно завершён!"
```

### `deploy/scripts/backup.sh`

```bash
#!/bin/bash
# Запускать через cron: 0 2 * * * /backup.sh
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="price_monitor_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR
pg_dump -U postgres price_monitor | gzip > "${BACKUP_DIR}/${FILENAME}"

# Удалить бэкапы старше 7 дней
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Бэкап создан: ${FILENAME}"
```

### `deploy/scripts/healthcheck.sh`

```bash
#!/bin/bash
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$response" = "$expected" ]; then
        echo "✅ $name: OK"
    else
        echo "❌ $name: FAILED (HTTP $response)"
        exit 1
    fi
}

check_service "API Health"     "http://localhost:8000/health"  "200"
check_service "Frontend"       "http://localhost:80"           "200"
check_service "Prometheus"     "http://localhost:9090/-/ready" "200"

# Проверить Celery workers
workers=$(docker exec price_monitor_worker_1 celery -A scheduler.celery_app inspect ping 2>&1)
if echo "$workers" | grep -q "pong"; then
    echo "✅ Celery workers: OK"
else
    echo "❌ Celery workers: нет ответа"
    exit 1
fi
```

### `.github/workflows/deploy.yml` — CI/CD

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/price_monitor
            git pull origin main
            bash deploy/scripts/deploy.sh
```

### `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: "fastapi"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: "/metrics"    # добавить prometheus-fastapi-instrumentator

  - job_name: "celery"
    static_configs:
      - targets: ["worker:9540"]  # celery-prometheus-exporter

  - job_name: "postgres"
    static_configs:
      - targets: ["db-exporter:9187"]  # postgres_exporter

  - job_name: "redis"
    static_configs:
      - targets: ["redis-exporter:9121"]  # redis_exporter
```

### Grafana Dashboard (ключевые панели)

В `monitoring/grafana/dashboards/price_monitor.json` создать дашборд с панелями:
1. **Parse runs per hour** — bar chart, успешных vs неудачных
2. **Products monitored** — gauge, общее число товаров
3. **Price changes detected** — time series, за последние 24ч
4. **API response time** — histogram p50/p95/p99
5. **Celery queue depth** — gauge по очередям (scraping, analysis, notifications)
6. **Redis memory usage** — time series
7. **Active alerts** — single stat с цветовой индикацией

### Оптимизация производительности

Добавить в `db/models.py` и `alembic` миграцию для индексов:
```sql
-- Частые запросы при фильтрации
CREATE INDEX CONCURRENTLY idx_products_brand_season ON products(brand, season);
CREATE INDEX CONCURRENTLY idx_products_size ON products(width, profile, diameter);
-- Для графиков истории
CREATE INDEX CONCURRENTLY idx_price_history_product_time ON price_history(product_id, scraped_at DESC);
-- Для алертов
CREATE INDEX CONCURRENTLY idx_alerts_unsent ON alerts(sent_at) WHERE sent_at IS NULL;
```

Добавить в `api/main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

## Требования к генерируемому Cursor-промпту

- Все секреты через переменные окружения, никогда не хардкодить
- Предоставить `.env.prod.example` со всеми необходимыми переменными
- Инструкция первоначальной установки: `git clone → cp .env.prod.example .env.prod → nano .env.prod → bash deploy/scripts/deploy.sh`
- SSL через Let's Encrypt (certbot) — добавить команду получения сертификата
- Добавить `WATCHTOWER` сервис для автоматического обновления Docker образов
- `crontab` на сервере для запуска `backup.sh` каждую ночь в 02:00
