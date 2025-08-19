from telegram import Update
from telegram.ext import ContextTypes
from db import SessionLocal
from models import User
from translator import LANGUAGES

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split()
    if len(args) < 2 or args[1] not in LANGUAGES:
        await update.message.reply_text(f"Uso: /lang <{'|'.join(LANGUAGES)}>")
        return
    
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    if user:
        user.lang = args[1]
        db.commit()
        await update.message.reply_text(f"Lingua impostata su: {user.lang}")
    db.close()
