#!/usr/bin/env bash
set -euo pipefail

echo "==> Riavvio di tutti i servizi..."
docker compose down
docker compose up -d

echo "==> Stato servizi:"
docker compose ps
