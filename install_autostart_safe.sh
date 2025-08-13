#!/bin/bash
set -euo pipefail

APP=app
APP_PATH=/app/app
FILE=_autostart.py
TS=$(date +%Y%m%d-%H%M%S)

echo "==> Writing $FILE on host..."
cat > "$FILE" <<'PY'
import os, asyncio, logging, importlib, inspect
from typing import List, Optional, Dict
from telegram import BotCommand, ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

log = logging.getLogger(__name__)

# ---------- UI (English)
_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton("/newgig"),  KeyboardButton("/mygigs")],
        [KeyboardButton("/buy"),     KeyboardButton("/release")],
        [KeyboardButton("/help"),    KeyboardButton("/cancel")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose an action…",
)

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not m: return
    await m.reply_text("Welcome to Escrow Gigs Bot 👋\nChoose an action:", reply_markup=_KB)

async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not m: return
    await m.reply_text(
        "Commands:\n"
        "/newgig – Create a gig\n"
        "/mygigs – My gigs\n"
        "/buy – Buy / Deposit\n"
        "/release – Release escrow\n"
        "/cancel – Cancel\n"
        "/help – Help"
    )

# ---------- Lazy resolver for legacy handlers in app.telegram_bot
_CACHE: Dict[str, Optional[object]] = {}
_RESOLVE_ERROR_LOGGED = set()

def _resolve(name: str) -> Optional[object]:
    if name in _CACHE:
        return _CACHE[name]
    try:
        mod = importlib.import_module("app.telegram_bot")
        fn = getattr(mod, name, None)
        _CACHE[name] = fn
        return fn
    except Exception as e:
        if name not in _RESOLVE_ERROR_LOGGED:
            log.exception("Unable to import handler %s from app.telegram_bot: %s", name, e)
            _RESOLVE_ERROR_LOGGED.add(name)
        _CACHE[name] = None
        return None

async def _call(handler, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if handler is None:
        m = update.effective_message
        if m: await m.reply_text("This command is temporarily unavailable.", reply_markup=_KB)
        return
    res = handler(update, context)
    if inspect.isawaitable(res):
        await res

# ---------- Proxies with usage overlays
async def _newgig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    text = (m.text or "") if m else ""
    has_pipes = "|" in text
    if not has_pipes and len(context.args) < 3:
        return await m.reply_text("Use: /newgig <title> | <price_usd> | <description>", reply_markup=_KB)
    return await _call(_resolve("cmd_newgig"), update, context)

async def _mygigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _call(_resolve("cmd_mygigs"), update, context)

async def _buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _call(_resolve("cmd_buy"), update, context)

async def _release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not context.args:
        return await m.reply_text("Use: /release <order_id>", reply_markup=_KB)
    return await _call(_resolve("cmd_release"), update, context)

async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _call(_resolve("cmd_cancel"), update, context)

# ---------- Runner compatible with FastAPI lifespan
async def run_bot_background():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        log.warning("TELEGRAM_TOKEN not set: bot NOT started.")
        return

    app = ApplicationBuilder().token(token).build()

    # Global command menu (EN)
    cmds: List[BotCommand] = [
        BotCommand("start",   "Open the main menu"),
        BotCommand("help",    "How it works & commands"),
        BotCommand("newgig",  "Create a gig"),
        BotCommand("mygigs",  "Your gigs"),
        BotCommand("buy",     "Buy / Deposit"),
        BotCommand("release", "Release escrow"),
        BotCommand("cancel",  "Cancel"),
    ]

    # Our improved start/help
    app.add_handler(CommandHandler("start",   _start))
    app.add_handler(CommandHandler("help",    _help))

    # Proxied legacy commands
    app.add_handler(CommandHandler("newgig",  _newgig))
    app.add_handler(CommandHandler("mygigs",  _mygigs))
    app.add_handler(CommandHandler("buy",     _buy))
    app.add_handler(CommandHandler("release", _release))
    app.add_handler(CommandHandler("cancel",  _cancel))

    await app.initialize()
    await app.start()
    try:
        # Make sure we’re polling and not on webhook; drop stale updates
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.bot.set_my_commands(cmds)

        # PTB v20 polling
        await app.updater.start_polling()
        log.info("Telegram bot is running.")
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            await app.updater.stop()
        except Exception:
            pass
        await app.stop()
        await app.shutdown()
        log.info("Telegram bot stopped cleanly.")
PY

echo "==> Copying into container..."
docker compose cp "$FILE" "$APP:$APP_PATH/$FILE"

echo "==> Ensure FastAPI imports _autostart.run_bot_background"
docker compose exec -T "$APP" sh -lc \
  'sed -i "s#from app\\.telegram_bot import run_bot_background#from app._autostart import run_bot_background#" /app/app/app.py'

echo "==> Syntax check..."
docker compose exec -T "$APP" python - <<'PY'
import py_compile
py_compile.compile("/app/app/_autostart.py", doraise=True)
print("OK syntax.")
PY

echo "==> Restarting app..."
docker compose restart "$APP" >/dev/null
sleep 1
docker compose logs --tail=120 "$APP"
echo
echo "Done. Test /start, then /newgig, /mygigs, /release."
