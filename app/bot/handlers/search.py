from telegram import Update
from telegram.ext import ContextTypes

from app.db import SessionLocal
from app.models import Gig
from app.services.search import search_gigs_by_keyword


async def search_gigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = context.args[0] if context.args else ""
    if not keyword:
        await update.message.reply_text("Please provide a keyword to search for.")
        return

    db = SessionLocal()
    gigs = search_gigs_by_keyword(db, keyword)
    db.close()

    if not gigs:
        await update.message.reply_text(f"No gigs found for '{keyword}'.")
        return

    message = f"Gigs found for '{keyword}':\n"
    for gig in gigs:
        message += f"- {gig.title}\n"
    await update.message.reply_text(message)
