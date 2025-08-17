#!/usr/bin/env bash
set -euo pipefail

echo "==> Riavvio di tutti i servizi..."
sudo systemctl restart app.service bot.service worker.service

echo "==> Stato servizi:"
sudo systemctl status app.service bot.service worker.service

