#!/usr/bin/env bash
set -euo pipefail

echo "==> Recupero ultimo backup da S3..."
LATEST_BACKUP=$(aws s3 ls s3://swisscoordinator/ | sort | tail -n 1 | awk {print })
[ -z "$LATEST_BACKUP" ] && { echo "Nessun backup trovato su S3"; exit 1; }

aws s3 cp "s3://swisscoordinator/$LATEST_BACKUP" /tmp/restore.tar.gz

echo "==> Estrazione backup..."
sudo systemctl stop app.service bot.service worker.service
tar xzf /tmp/restore.tar.gz -C /home/ubuntu/escrow-gigs-bot/escrow-gigs-bot

echo "==> Ripristino database..."
export PGPASSWORD=rtQWq-ITqQ5ZFjMCjTNQLX5nKK3o1x31R
psql -h localhost -U postgress -d gigs -f /home/ubuntu/escrow-gigs-bot/escrow-gigs-bot/tmp/escrow_backup/*.sql

echo "==> Riavvio servizi..."
sudo systemctl start app.service bot.service worker.service

echo "==> Ripristino completato da $LATEST_BACKUP"

