#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/backups/postgres"
DATE="$(date +%Y%m%d_%H%M%S)"
FILE_NAME="price_monitor_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"
pg_dump -U postgres price_monitor | gzip > "${BACKUP_DIR}/${FILE_NAME}"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
echo "Backup created: ${BACKUP_DIR}/${FILE_NAME}"
