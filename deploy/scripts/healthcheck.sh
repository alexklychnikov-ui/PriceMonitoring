#!/usr/bin/env bash
set -euo pipefail

check() {
  local name="$1"
  local url="$2"
  local expected="$3"

  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
  if [ "$code" = "$expected" ]; then
    echo "OK: $name"
  else
    echo "FAIL: $name (HTTP $code, expected $expected)"
    exit 1
  fi
}

check "API root" "http://localhost:8000/" "200"
check "Analytics overview" "http://localhost:8000/api/analytics/overview" "200"
check "Prometheus ready" "http://localhost:9090/-/ready" "200"

if docker compose -f deploy/docker-compose.prod.yml ps | grep -q "worker.*Up"; then
  echo "OK: worker container is up"
else
  echo "FAIL: worker container is not up"
  exit 1
fi

echo "Healthcheck passed"
