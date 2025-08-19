#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/tmp/escrow_backup"
DATE=$(date +%F_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/escrow_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "==> Creazione backup di codice e dati..."
docker compose stop app
tar czf "$BACKUP_FILE" \
  --exclude='__pycache__' \
  --exclude='*.log' \
  .

echo "==> Avvio app..."
docker compose start app

echo "==> Upload su S3..."
aws s3 cp "$BACKUP_FILE" s3://swisscoordinator/

echo "==> Backup completato: $BACKUP_FILE"
