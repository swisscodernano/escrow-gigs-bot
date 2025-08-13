import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from app.config import settings
from app.db import SessionLocal
from app.models import User, Gig, Order, Dispute, Feedback
from app.i18n import get_translation
from app.lang_command import cmd_lang

async def ensure_user(user_data):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == str(user_data.id)).first()
    if not user:
        user = User(tg_id=str(user_data.id), username=user_data.username)
        db.add(user)
        db.commit()
    db.close()
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update.effective_user)
    _ = get_translation(user)
    
    keyboard = [
        [InlineKeyboardButton(_("Annunci"), callback_data='gigs')],
        [InlineKeyboardButton(_("I Miei Ordini"), callback_data='orders')],
        [InlineKeyboardButton(_("I Miei Annunci"), callback_data='mygigs')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(_("👋 *Benvenuto nel Gigs Escrow Bot*"), reply_markup=reply_markup)

def main() -> None:
    application = Application.builder().token(settings.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", cmd_lang))
    # Aggiungi qui altri gestori di comandi e callback...
    application.run_polling()

if __name__ == '__main__':
    main()