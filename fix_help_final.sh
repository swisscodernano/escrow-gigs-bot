#!/bin/bash
set -e

echo "==> Identifico container..."
CID=$(docker compose ps -q app)

echo "==> Copio telegram_bot.py dal container..."
docker compose cp app:/app/app/telegram_bot.py telegram_bot.py.bak

echo "==> Applico patch..."
cat > telegram_bot.py <<'PY'
import os
from telegram.ext import CommandHandler

def cmd_help(update, context):
    update.message.reply_text("""\
Escrow Gigs Bot — Help

Comandi disponibili:
/start - Avvia il bot
/help - Mostra questo messaggio
/newgig - Crea un nuovo annuncio
/mygigs - Vedi i tuoi annunci
/release - Rilascia fondi in escrow
/cancel - Annulla transazione
""")

# Registrazione handler
def register_help_handler(dp):
    dp.add_handler(CommandHandler("help", cmd_help))
PY

echo "==> Copio file patchato nel container..."
docker compose cp telegram_bot.py app:/app/app/telegram_bot.py

echo "==> Riavvio container app..."
docker compose restart app

echo "==> Pulizia file temporanei..."
rm -f telegram_bot.py

echo "==> FATTO. Controlla i log:"
docker compose logs -f app
