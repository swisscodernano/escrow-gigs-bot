#!/bin/bash
set -euo pipefail

APP_SERVICE=app
APP_PATH=/app/app
BOT_FILE=telegram_bot.py

echo "==> Check docker compose..."
docker compose version >/dev/null

TS=$(date +%Y%m%d-%H%M%S)
mkdir -p _backups

echo "==> Backup telegram_bot.py dal container (se esiste)..."
if CID=$(docker compose ps -q "${APP_SERVICE}"); then
  [ -n "$CID" ] && docker compose cp "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}" "_backups/${BOT_FILE}.${TS}.bak" || true
fi

echo "==> Assicuro .env base..."
touch .env
grep -q '^PRIMARY_ASSET=' .env && sed -i 's/^PRIMARY_ASSET=.*/PRIMARY_ASSET=USDT-TRON/' .env || echo 'PRIMARY_ASSET=USDT-TRON' >> .env
grep -q '^ASSETS_ENABLED=' .env && sed -i 's/^ASSETS_ENABLED=.*/ASSETS_ENABLED=USDT-TRON/' .env || echo 'ASSETS_ENABLED=USDT-TRON' >> .env
# Non imposto TELEGRAM_TOKEN qui: lo leggo se già presente, altrimenti il bot non parte ma l'app RESTa up.

echo "==> docker-compose.override.yml per caricare .env..."
cat > docker-compose.override.yml <<'YAML'
services:
  app:
    env_file:
      - .env
YAML

echo "==> Scrivo nuovo telegram_bot.py (async run_bot_background + /help)..."
cat > _patched_${BOT_FILE} <<'PY'
import os
import logging
import asyncio
import threading

# Rileva python-telegram-bot v20+ o v13
try:
    from telegram.ext import ApplicationBuilder, CommandHandler  # v20+
    PTB20 = True
except Exception:
    PTB20 = False
    from telegram.ext import Updater, CommandHandler  # v13

logging.basicConfig(level=logging.INFO)
_started = False

def cmd_help(update, context):
    update.message.reply_text("""\
Escrow Gigs Bot — Help

Comandi disponibili:
/start   - Avvia il bot
/help    - Mostra questo messaggio
/newgig  - Crea un nuovo annuncio
/mygigs  - Vedi i tuoi annunci
/release - Rilascia fondi in escrow
/cancel  - Annulla transazione
""")

# Per retrocompatibilità se altrove registri handler passando il dispatcher
def register_help_handler(dp):
    dp.add_handler(CommandHandler("help", cmd_help))

async def run_bot_background():
    """
    Avvia il bot Telegram in background. Coroutine idempotente.
    Se TELEGRAM_TOKEN manca, logga e ritorna senza far fallire l'app.
    """
    global _started
    if _started:
        return

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        logging.warning("TELEGRAM_TOKEN non impostato: bot NON avviato (l'app resta up).")
        return

    try:
        if PTB20:
            # v20: usiamo run_polling in thread per non bloccare l'event loop
            app = ApplicationBuilder().token(token).build()
            app.add_handler(CommandHandler("help", cmd_help))
            await asyncio.to_thread(app.run_polling)
            _started = True
            logging.info("Telegram bot avviato (ptb v20+).")
        else:
            # v13: start_polling rientra, idle blocca: eseguo entrambi in thread
            def _runner():
                updater = Updater(token=token, use_context=True)
                dp = updater.dispatcher
                dp.add_handler(CommandHandler("help", cmd_help))
                updater.start_polling()
                updater.idle()
            # Mantengo la coroutine viva finché il thread gira
            await asyncio.to_thread(_runner)
            _started = True
            logging.info("Telegram bot avviato (ptb v13).")
    except Exception as e:
        logging.exception("Errore avvio Telegram bot: %s", e)
        # Non rilancio: non impedisco l'avvio dell'app FastAPI
        return
PY

echo "==> Ricreo stack per applicare env..."
docker compose up -d --force-recreate

echo "==> Copio file patchato nel container..."
docker compose cp "_patched_${BOT_FILE}" "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}"

echo "==> Restart app..."
docker compose restart "${APP_SERVICE}"

echo '==> Log (CTRL+C per uscire). Se vedi "non impostato", aggiungi TELEGRAM_TOKEN in .env e riavvia.'
docker compose logs -f --tail=200 "${APP_SERVICE}"
