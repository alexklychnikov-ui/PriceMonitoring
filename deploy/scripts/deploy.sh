#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Frontend build"
cd frontend
npm ci
npm run build
cd ..

echo "[2/5] Pull latest and build images"
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod pull || true
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod build

echo "[3/5] Start infra"
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d db redis

echo "[4/5] Apply migrations"
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod run --rm api alembic upgrade head

echo "[5/5] Start app services"
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d api worker beat telegram_bot flower nginx prometheus grafana watchtower

echo "Deployment complete"
