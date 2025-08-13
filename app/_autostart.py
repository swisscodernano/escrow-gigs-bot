from dotenv import load_dotenv
load_dotenv()
import os, asyncio, logging, importlib, inspect
from typing import List, Optional, Dict
from telegram import BotCommand, ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from i18n import t

log = logging.getLogger(__name__)

# ---------- UI (English via i18n)
_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton(t("start.buttons.newgig")),  KeyboardButton(t("start.buttons.mygigs"))],
        [KeyboardButton(t("start.buttons.buy")),     KeyboardButton(t("start.buttons.release"))],
        [KeyboardButton(t("start.buttons.help")),    KeyboardButton(t("start.buttons.cancel"))],
    ],
    resize_keyboard=True,
    input_field_placeholder=t("start.placeholder"),
)

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not m: return
    await m.reply_text(t("start.welcome"), reply_markup=_KB)

async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not m: return
    await m.reply_text(t("help.text"))

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
            log.exception("Unable to import handler %s from telegram_bot: %s", name, e)
            _RESOLVE_ERROR_LOGGED.add(name)
        _CACHE[name] = None
        return None

async def _call(handler, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if handler is None:
        m = update.effective_message
        if m: await m.reply_text(t("misc.unavailable"), reply_markup=_KB)
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
        return await m.reply_text(t("usage.newgig"), reply_markup=_KB)
    return await _call(_resolve("cmd_newgig"), update, context)

async def _mygigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _call(_resolve("cmd_mygigs"), update, context)

async def _buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _call(_resolve("cmd_buy"), update, context)

async def _release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not context.args:
        return await m.reply_text(t("usage.release"), reply_markup=_KB)
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

    # Global command menu
    cmds: List[BotCommand] = [
        BotCommand("start",   t("commands.start")),
        BotCommand("help",    t("commands.help")),
        BotCommand("newgig",  t("commands.newgig")),
        BotCommand("mygigs",  t("commands.mygigs")),
        BotCommand("buy",     t("commands.buy")),
        BotCommand("release", t("commands.release")),
        BotCommand("cancel",  t("commands.cancel")),
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
