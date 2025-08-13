#!/bin/bash
set -euo pipefail

APP_SERVICE=app
APP_PATH=/app/app

read -rsp "Inserisci TELEGRAM_TOKEN: " TOKEN; echo
if [ -z "${TOKEN}" ]; then
  echo "Token vuoto: abort."; exit 1
fi

# Scrivi/aggiorna .env
touch .env
sed -i '/^TELEGRAM_TOKEN=/d' .env
echo "TELEGRAM_TOKEN=${TOKEN}" >> .env

# Override YAML pulito (carica .env dentro 'app')
cat > docker-compose.override.yml <<'YAML'
services:
  app:
    env_file:
      - .env
YAML

echo "==> Applico configurazione e riavvio solo l'app..."
docker compose up -d --force-recreate app
docker compose restart "${APP_SERVICE}"

echo "==> Log (CTRL+C per uscire) — cerca 'Telegram bot avviato' oppure errori."
docker compose logs -f --tail=200 "${APP_SERVICE}"
