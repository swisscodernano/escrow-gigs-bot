#!/usr/bin/env bash
set -e
if [ ! -f ".env" ]; then
  echo "[!] cp .env.example .env e compila BOT_TOKEN/ADMIN_USER_ID"
  exit 1
fi
docker compose build
docker compose up -d
echo "[✓] Avviato: http://localhost:8000/health"
