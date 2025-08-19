#!/usr/bin/env bash
set -euo pipefail

echo "==> Recupero ultimo backup da S3..."
LATEST_BACKUP=$(aws s3 ls s3://swisscoordinator/ | sort | tail -n 1 | awk '{print $4}')
[ -z "$LATEST_BACKUP" ] && { echo "Nessun backup trovato su S3"; exit 1; }

aws s3 cp "s3://swisscoordinator/$LATEST_BACKUP" /tmp/restore.tar.gz

echo "==> Estrazione backup..."
docker compose down
tar xzf /tmp/restore.tar.gz -C .
docker compose up -d

echo "==> Ripristino completato da $LATEST_BACKUP"
