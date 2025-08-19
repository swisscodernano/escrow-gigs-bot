#!/bin/bash
set -euo pipefail
APP=app
APP_PATH=/app/app
FILE=telegram_bot.py
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p _backups

echo "==> Scarico e salvo backup"
docker compose cp "$APP:$APP_PATH/$FILE" "./$FILE.work"
cp "./$FILE.work" "_backups/$FILE.$TS.bak"

echo "==> Rimuovo eventuali patch vecchie"
sed -i '/^# === AUTOPATCH BEGIN ===$/,/^# === AUTOPATCH END ===$/d' "$FILE.work" || true

echo "==> Aggiungo autopatch (handlers + keyboard + menu + run_bot_background async)"
{
  echo '# === AUTOPATCH BEGIN ==='
  echo 'import asyncio, inspect, os, logging'
  echo 'from typing import List'
  echo 'try:'
  echo '    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand'
  echo '    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes'
  echo '    PTB20 = True'
  echo 'except Exception:'
  echo '    PTB20 = False'
  echo ''
  echo 'async def __egb_default_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):'
  echo '    kb = [['
  echo '        KeyboardButton("/newgig"), KeyboardButton("/mygigs")],'
  echo '        [KeyboardButton("/buy"), KeyboardButton("/release")],'
  echo '        [KeyboardButton("/help"), KeyboardButton("/cancel")]'
  echo '    ]'
  echo '    await update.message.reply_text('
  echo '        "Benvenuto su Escrow Gigs Bot 👋\\nScegli un\'azione:",'
  echo '        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))'
  echo ''
  echo 'def __egb_wrap(f):'
  echo '    if f is None: return None'
  echo '    if inspect.iscoroutinefunction(f): return f'
  echo '    async def _w(u, c):'
  echo '        return f(u, c)'
  echo '    return _w'
  echo ''
  echo 'async def run_bot_background():'
  echo '    """Avvia il bot in polling (PTB v20) senza bloccare FastAPI."""'
  echo '    token = os.getenv("TELEGRAM_TOKEN", "").strip()'
  echo '    if not token:'
  echo '        logging.warning("TELEGRAM_TOKEN non impostato: bot NON avviato (app up)."); return'
  echo '    if not PTB20:'
  echo '        logging.error("python-telegram-bot v20 richiesto. Blocca le versioni a >=20,<21."); return'
  echo '    app = ApplicationBuilder().token(token).build()'
  echo '    # Registra handlers se presenti nel modulo'
  echo '    cmds: List[BotCommand] = []'
  echo '    start_func = globals().get("cmd_start") or __egb_default_start'
  echo '    app.add_handler(CommandHandler("start", __egb_wrap(start_func))); cmds.append(BotCommand("start","Apri menu"))'
  echo '    if globals().get("cmd_help"):'
  echo '        app.add_handler(CommandHandler("help", __egb_wrap(globals()["cmd_help"]))); cmds.append(BotCommand("help","Aiuto"))'
  echo '    if globals().get("cmd_buy"):'
  echo '        app.add_handler(CommandHandler("buy", __egb_wrap(globals()["cmd_buy"]))); cmds.append(BotCommand("buy","Acquista/Deposita"))'
  echo '    if globals().get("cmd_newgig"):'
  echo '        app.add_handler(CommandHandler("newgig", __egb_wrap(globals()["cmd_newgig"]))); cmds.append(BotCommand("newgig","Crea annuncio"))'
  echo '    if globals().get("cmd_mygigs"):'
  echo '        app.add_handler(CommandHandler("mygigs", __egb_wrap(globals()["cmd_mygigs"]))); cmds.append(BotCommand("mygigs","I miei annunci"))'
  echo '    if globals().get("cmd_release"):'
  echo '        app.add_handler(CommandHandler("release", __egb_wrap(globals()["cmd_release"]))); cmds.append(BotCommand("release","Rilascia escrow"))'
  echo '    if globals().get("cmd_cancel"):'
  echo '        app.add_handler(CommandHandler("cancel", __egb_wrap(globals()["cmd_cancel"]))); cmds.append(BotCommand("cancel","Annulla"))'
  echo ''
  echo '    await app.initialize(); await app.start()'
  echo '    await app.bot.delete_webhook(drop_pending_updates=True)'
  echo '    if cmds:'
  echo '        try: await app.bot.set_my_commands(cmds)'
  echo '        except Exception: pass'
  echo '    try:'
  echo '        await app.updater.start_polling()'
  echo '        while True:'
  echo '            await asyncio.sleep(3600)'
  echo '    except asyncio.CancelledError:'
  echo '        pass'
  echo '    finally:'
  echo '        try: await app.updater.stop()'
  echo '        except Exception: pass'
  echo '        await app.stop(); await app.shutdown()'
  echo '# === AUTOPATCH END ==='
} >> "$FILE.work"

echo "==> Copio nel container e riavvio"
docker compose cp "./$FILE.work" "$APP:$APP_PATH/$FILE"
docker compose restart "$APP"

echo "==> Pronto. Apri la chat e invia /start (vedrai i bottoni). Controllo log:"
docker compose logs -f --tail=200 "$APP"
