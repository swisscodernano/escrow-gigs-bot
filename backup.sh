#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/tmp/escrow_backup"
DATE=$(date +%F_%H-%M-%S)
DB_BACKUP_FILE="$BACKUP_DIR/escrow_db_$DATE.sql"
APP_BACKUP_FILE="$BACKUP_DIR/escrow_app_$DATE.tar.gz"
PROJECT_DIR="/home/ubuntu/escrow-gigs-bot/escrow-gigs-bot"
S3_BUCKET="s3://swisscoordinator"

mkdir -p "$BACKUP_DIR"

echo "==> Creazione backup del database..."
export PGPASSWORD=rtQWq-ITqQ5ZFjMCjTNQLX5nKK3o1x31R
pg_dump -h localhost -U postgress -d gigs --no-owner --no-privileges > "$DB_BACKUP_FILE"

echo "==> Creazione backup dellapplicazione..."
tar czf "$APP_BACKUP_FILE" -C "$PROJECT_DIR" --exclude=venv --exclude=__pycache__ --exclude=*.log .

echo "==> Upload su S3..."
aws s3 cp "$APP_BACKUP_FILE" "$S3_BUCKET/"

echo "==> Pulizia file temporanei..."
rm "$DB_BACKUP_FILE"
rm "$APP_BACKUP_FILE"

echo "==> Backup completato e caricato su S3: $APP_BACKUP_FILE"

