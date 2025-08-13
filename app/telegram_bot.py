import asyncio
from app.config import settings
from app.db import SessionLocal
from app.models import User

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Defaults, Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import InvalidToken

def db_session():
    return SessionLocal()

async def ensure_user(tg_user) -> User:
    db = db_session()
    u = db.query(User).filter(User.tg_id==str(tg_user.id)).first()
    if not u:
        u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
        db.add(u); db.commit(); db.refresh(u)
    db.close()
    return u

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    keyboard = [
        [InlineKeyboardButton("📋 Annunci", callback_data="listings")],
        [InlineKeyboardButton("📦 I Miei Ordini", callback_data="orders")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 *Benvenuto nel Gigs Escrow Bot*", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"Hai selezionato: {query.data}")

async def run_bot_background():
    print("--- Avvio del Bot Semplificato ---")
    app = Application.builder().token(settings.BOT_TOKEN).defaults(Defaults(parse_mode=None)).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Inizializzazione...")
    try:
        await app.initialize()
    except InvalidToken:
        print("ERRORE: Token non valido.")
        return
        
    print("Avvio Polling...")
    await app.updater.start_polling(drop_pending_updates=True)
    print("--- ✅ Bot avviato con successo ---")

    while True:
        await asyncio.sleep(3600)
