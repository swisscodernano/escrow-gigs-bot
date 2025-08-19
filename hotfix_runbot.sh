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

echo "==> docker-compose.override.yml minimale per caricare .env..."
cat > docker-compose.override.yml <<'YAML'
services:
  app:
    env_file:
      - .env
YAML

echo "==> Scrivo nuovo telegram_bot.py (help + run_bot_background)..."
cat > _patched_${BOT_FILE} <<'PY'
import os
import logging
import threading

# Compat import: v20 (ApplicationBuilder) o v13 (Updater)
try:
    from telegram.ext import ApplicationBuilder, CommandHandler  # v20+
    PTB20 = True
except Exception:  # pragma: no cover
    PTB20 = False
    from telegram.ext import Updater, CommandHandler  # v13

logging.basicConfig(level=logging.INFO)
_started = False
_thread = None

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

# Compat con codice esistente che registra handler passando il dispatcher
def register_help_handler(dp):
    dp.add_handler(CommandHandler("help", cmd_help))

def _start_v20(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("help", cmd_help))
    # run_polling è bloccante: lo avviamo in thread separato
    def _runner():
        try:
            app.run_polling()
        except Exception as e:
            logging.exception("Telegram bot v20 stopped: %s", e)
    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t

def _start_v13(token: str):
    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("help", cmd_help))
    updater.start_polling()
    # In v13 start_polling rientra subito: teniamo un thread sentinella
    def _sentinel():
        try:
            updater.idle()
        except Exception as e:
            logging.exception("Telegram bot v13 stopped: %s", e)
    t = threading.Thread(target=_sentinel, daemon=True)
    t.start()
    return t

def run_bot_background():
    """
    Avvia il bot Telegram in background. Safe/idempotente.
    Ritorna una stringa di stato.
    """
    global _started, _thread
    if _started:
        return "already_started"

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        logging.warning("TELEGRAM_TOKEN non impostato: bot NON avviato")
        return "no_token"

    try:
        if PTB20:
            _thread = _start_v20(token)
            _started = True
            logging.info("Telegram bot avviato (ptb v20+).")
            return "started_v20"
        else:
            _thread = _start_v13(token)
            _started = True
            logging.info("Telegram bot avviato (ptb v13).")
            return "started_v13"
    except Exception as e:
        logging.exception("Errore avvio Telegram bot: %s", e)
        return f"error:{e}"
PY

echo "==> Ricreo stack per applicare env..."
docker compose up -d --force-recreate

echo "==> Copio file patchato nel container..."
docker compose cp "_patched_${BOT_FILE}" "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}"

echo "==> Restart app..."
docker compose restart "${APP_SERVICE}"

echo "==> Pulizia..."
rm -f "_patched_${BOT_FILE}"

echo "==> Log (CTRL+C per uscire)..."
docker compose logs -f --tail=200 "${APP_SERVICE}"
