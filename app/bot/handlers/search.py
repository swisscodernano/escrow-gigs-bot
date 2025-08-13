from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from db import SessionLocal
from services.search import search_gigs

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    query = " ".join(context.args) if context.args else ""
    if not query:
        await m.reply_text("Use: /search <query>")
        return
    db = SessionLocal()
    results = search_gigs(db, query, limit=10)
    db.close()
    if not results:
        await m.reply_text("No gigs found.")
        return
    for r in results:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("View", url=f"https://t.me/share/url?url=/buy%20{r['id']}")]]
        )
        await m.reply_text(f"{r['title']} — ${r['price_usd']}\n{r['excerpt']}", reply_markup=kb)

async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query
    if not q:
        return
    db = SessionLocal()
    results = search_gigs(db, q, limit=20)
    db.close()
    articles = []
    for r in results:
        articles.append(
            InlineQueryResultArticle(
                id=str(r["id"]),
                title=f"{r['title']} — ${r['price_usd']}",
                description=r["excerpt"],
                input_message_content=InputTextMessageContent(f"/buy {r['id']}")
            )
        )
    await update.inline_query.answer(articles, cache_time=0)
