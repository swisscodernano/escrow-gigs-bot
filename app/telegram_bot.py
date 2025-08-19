import asyncio
from decimal import Decimal
from urllib.parse import quote, unquote
from sqlalchemy import or_
from app.config import settings
from app.db import SessionLocal
from app.models import User, Gig, Order, Dispute
from app.payment.ledger import new_deposit_address
from app.payment.tron_stub import validate_deposit_tx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Defaults,
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Conversation states
TITLE, DESCRIPTION, PRICE, CATEGORY, CONFIRMATION = range(5)

# Predefined categories
PAGE_SIZE = 5
CATEGORIES = [
    "Graphic Design",
    "Translation",
    "Web Development",
    "Writing",
    "Other",
]


def db_session():
    return SessionLocal()


async def ensure_user(tg_user) -> User:
    db = db_session()
    u = db.query(User).filter(User.tg_id == str(tg_user.id)).first()
    if not u:
        u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
        db.add(u)
        db.commit()
        db.refresh(u)
    else:
        if u.username != (tg_user.username or ""):
            u.username = tg_user.username or ""
            db.commit()
    db.close()
    return u


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    await update.message.reply_text(
        "👋 Benvenuto nel *Gigs Escrow Bot*\n"
        "/newgig | /listings | /mygigs | /buy <id> | /confirm_tx <id> <txid> | /release <id> | /dispute <id> <motivo> | /orders | /categories | /search <keyword>"
    )


async def newgig_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the gig's title."""
    await update.message.reply_text("Let's create a new gig. What is the title?")
    return TITLE


async def title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the title and asks for the description."""
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Great. Now, what is the description?")
    return DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the description and asks for the price."""
    context.user_data["description"] = update.message.text
    await update.message.reply_text("Got it. What is the price in USD?")
    return PRICE


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the price and asks for the category."""
    try:
        context.user_data["price"] = Decimal(update.message.text)
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid price. Please enter a number.")
        return PRICE

    keyboard = [
        [InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Almost there. Please choose a category:", reply_markup=reply_markup
    )
    return CATEGORY


async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the category and asks for confirmation."""
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data

    gig_details = (
        f"Title: {context.user_data['title']}\n"
        f"Description: {context.user_data['description']}\n"
        f"Price: ${context.user_data['price']}\n"
        f"Category: {context.user_data['category']}"
    )

    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data="confirm"),
            InlineKeyboardButton("Cancel", callback_data="cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"Please confirm your gig details:\n\n{gig_details}",
        reply_markup=reply_markup,
    )
    return CONFIRMATION


async def save_gig(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the gig to the database."""
    query = update.callback_query
    await query.answer()
    user = await ensure_user(update.effective_user)

    db = db_session()
    seller = db.query(User).filter(User.tg_id == str(user.tg_id)).first()
    g = Gig(
        seller_id=seller.id,
        title=context.user_data["title"],
        description=context.user_data["description"],
        price_usd=context.user_data["price"],
        category=context.user_data["category"],
        currency=settings.PRIMARY_ASSET,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    db.close()

    await query.edit_message_text(
        text=f"✅ Gig #{g.id} created: *{g.title}* — ${g.price_usd} ({g.currency})"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text="Gig creation canceled.")
    else:
        await update.message.reply_text("Gig creation canceled.")

    context.user_data.clear()
    return ConversationHandler.END


async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the list of categories as inline buttons."""
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"category_{quote(cat)}_page_1")]
        for cat in CATEGORIES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please choose a category:", reply_markup=reply_markup
    )


async def category_gigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a paginated list of all active gigs within a category."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    category_name = unquote(parts[1])
    page = int(parts[3])

    db = db_session()

    gigs_query = db.query(Gig).filter(
        Gig.active == True, Gig.category == category_name
    )
    total_gigs = gigs_query.count()
    total_pages = (total_gigs + PAGE_SIZE - 1) // PAGE_SIZE

    gigs = (
        gigs_query.order_by(Gig.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    db.close()

    if not gigs:
        await query.edit_message_text("No gigs found in this category.")
        return

    lines = [f"📋 *Gigs in {category_name} (Page {page}/{total_pages}):*"]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
    lines.append("\nBuy: /buy <id>")

    keyboard = []
    row = []
    if page > 1:
        row.append(
            InlineKeyboardButton(
                "⬅️ Prev", callback_data=f"category_{quote(category_name)}_page_{page-1}"
            )
        )
    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                "Next ➡️", callback_data=f"category_{quote(category_name)}_page_{page+1}"
            )
        )
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("\n".join(lines), reply_markup=reply_markup)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches for gigs by keyword."""
    args = (update.message.text or "").split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /search <keyword>")
        return
    keyword = args[1]
    page = 1

    db = db_session()
    gigs_query = db.query(Gig).filter(
        Gig.active == True,
        or_(
            Gig.title.ilike(f"%{keyword}%"),
            Gig.description.ilike(f"%{keyword}%"),
        ),
    )
    total_gigs = gigs_query.count()
    total_pages = (total_gigs + PAGE_SIZE - 1) // PAGE_SIZE

    gigs = (
        gigs_query.order_by(Gig.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    db.close()

    if not gigs:
        await update.message.reply_text("No gigs found matching your search.")
        return

    lines = [f"📋 *Search results for '{keyword}' (Page {page}/{total_pages}):*"]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
    lines.append("\nBuy: /buy <id>")

    keyboard = []
    row = []
    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                "Next ➡️", callback_data=f"search_{quote(keyword)}_page_{page+1}"
            )
        )
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("\n".join(lines), reply_markup=reply_markup)


async def search_gigs_paginated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a paginated list of search results."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    keyword = unquote(parts[1])
    page = int(parts[3])

    db = db_session()
    gigs_query = db.query(Gig).filter(
        Gig.active == True,
        or_(
            Gig.title.ilike(f"%{keyword}%"),
            Gig.description.ilike(f"%{keyword}%"),
        ),
    )
    total_gigs = gigs_query.count()
    total_pages = (total_gigs + PAGE_SIZE - 1) // PAGE_SIZE

    gigs = (
        gigs_query.order_by(Gig.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    db.close()

    if not gigs:
        await query.edit_message_text("No gigs found matching your search.")
        return

    lines = [f"📋 *Search results for '{keyword}' (Page {page}/{total_pages}):*"]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
    lines.append("\nBuy: /buy <id>")

    keyboard = []
    row = []
    if page > 1:
        row.append(
            InlineKeyboardButton(
                "⬅️ Prev", callback_data=f"search_{quote(keyword)}_page_{page-1}"
            )
        )
    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                "Next ➡️", callback_data=f"search_{quote(keyword)}_page_{page+1}"
            )
        )
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("\n".join(lines), reply_markup=reply_markup)


async def cmd_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = db_session()
    gigs = db.query(Gig).filter(Gig.active==True).order_by(Gig.id.desc()).limit(20).all()
    db.close()
    if not gigs:
        await update.message.reply_text("Nessun annuncio al momento. /newgig")
        return
    lines = ["📋 *Annunci:*"]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
    lines.append("\nCompra: /buy <id>")
    await update.message.reply_text("\n".join(lines))

async def cmd_mygigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = await ensure_user(update.effective_user)
    db = db_session()
    seller = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    gigs = db.query(Gig).filter(Gig.seller_id==seller.id).order_by(Gig.id.desc()).all()
    db.close()
    if not gigs:
        await update.message.reply_text("Non hai annunci. /newgig")
        return
    lines = ["🧾 *I tuoi annunci:*"]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency} — {'ON' if g.active else 'OFF'}")
    await update.message.reply_text("\n".join(lines))

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split()
    if len(args) < 2:
        await update.message.reply_text("Uso: /buy <gig_id>")
        return
    try:
        gig_id = int(args[1])
    except:
        await update.message.reply_text("ID non valido.")
        return
    buyer = await ensure_user(update.effective_user)
    db = db_session()
    g = db.query(Gig).filter(Gig.id==gig_id, Gig.active==True).first()
    if not g:
        db.close()
        await update.message.reply_text("Annuncio non trovato o inattivo.")
        return
    buyer_obj = db.query(User).filter(User.tg_id==str(buyer.tg_id)).first()
    o = Order(gig_id=g.id, buyer_id=buyer_obj.id, seller_id=g.seller_id,
              status="AWAIT_DEPOSIT", expected_amount=g.price_usd, escrow_fee_pct=8.00)
    db.add(o); db.commit(); db.refresh(o)
    dep = new_deposit_address(o.id, g.currency)
    o.deposit_address = dep.address
    db.commit(); db.refresh(o); db.close()
    await update.message.reply_text(
        "🛡️ Ordine creato. Deposita *{amt}* in {asset} all'indirizzo:\n`{addr}`\n\n"
        "Dopo il pagamento: /confirm_tx {oid} <txid>"
        .format(amt=g.price_usd, asset=g.currency, addr=o.deposit_address, oid=o.id))

async def cmd_confirm_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split()
    if len(args) < 3:
        await update.message.reply_text("Uso: /confirm_tx <order_id> <txid>")
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text("order_id non valido.")
        return
    txid = args[2].strip()
    db = db_session()
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        db.close()
        await update.message.reply_text("Ordine non trovato.")
        return
    ok = False
    if o.gig.currency.startswith("USDT-TRON"):
        ok = await validate_deposit_tx(txid, Decimal(o.expected_amount))
    elif o.gig.currency.startswith("BTC-ONCHAIN"):
        from app.payment import btc_onchain
        ok = await btc_onchain.validate_deposit(o.deposit_address, Decimal(o.expected_amount))
    if not ok:
        db.close()
        await update.message.reply_text("⚠️ Deposito non valido.")
        return
    o.txid = txid; o.status = "FUNDS_HELD"
    db.commit(); db.refresh(o); db.close()
    await update.message.reply_text("✅ Deposito confermato. Fondi in garanzia. Usa /release {oid} quando ok.".format(oid=oid))

async def cmd_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split()
    if len(args) < 2:
        await update.message.reply_text("Uso: /release <order_id>")
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text("order_id non valido.")
        return
    db = db_session()
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        db.close()
        await update.message.reply_text("Ordine non trovato.")
        return
    if o.status != "FUNDS_HELD":
        db.close()
        await update.message.reply_text("Ordine non in garanzia.")
        return
    o.status = "RELEASED"
    db.commit(); db.refresh(o); db.close()
    await update.message.reply_text("🔓 Rilascio segnato. (Invio on-chain da worker/admin)")

async def cmd_dispute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split(" ", 2)
    if len(args) < 3:
        await update.message.reply_text("Uso: /dispute <order_id> <motivo>")
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text("order_id non valido.")
        return
    reason = args[2].strip()
    u = await ensure_user(update.effective_user)
    db = db_session()
    user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        db.close()
        await update.message.reply_text("Ordine non trovato.")
        return
    d = Dispute(order_id=o.id, opened_by=user_obj.id, reason=reason, status="OPEN")
    db.add(d); db.commit(); db.close()
    await update.message.reply_text("🧑‍⚖️ Disputa aperta. Verifica in corso.")
    if settings.ADMIN_USER_ID:
        try:
            await context.bot.send_message(chat_id=settings.ADMIN_USER_ID, text=f"⚖️ Disputa ordine {oid}: {reason}")
        except Exception:
            pass

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = await ensure_user(update.effective_user)
    db = db_session()
    user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    orders = db.query(Order).filter((Order.buyer_id==user_obj.id)|(Order.seller_id==user_obj.id)).order_by(Order.id.desc()).limit(10).all()
    db.close()
    if not orders:
        await update.message.reply_text("Nessun ordine.")
        return
    lines = ["📦 *Ordini:*"]
    for o in orders:
        lines.append(f"#{o.id} — {o.status} — ${o.expected_amount} — {o.deposit_address or '-'}")
    await update.message.reply_text("\n".join(lines))

async def run_bot_background():
    app = Application.builder().token(settings.BOT_TOKEN).defaults(Defaults(parse_mode=None)).build()
    app.add_handler(CommandHandler("start", cmd_start))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newgig", newgig_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            CATEGORY: [CallbackQueryHandler(category)],
            CONFIRMATION: [
                CallbackQueryHandler(save_gig, pattern="^confirm$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("categories", cmd_categories))
    app.add_handler(CallbackQueryHandler(category_gigs, pattern="^category_.*_page_"))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CallbackQueryHandler(search_gigs_paginated, pattern="^search_.*_page_"))
    app.add_handler(CommandHandler("listings", cmd_listings))
    app.add_handler(CommandHandler("mygigs", cmd_mygigs))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("confirm_tx", cmd_confirm_tx))
    app.add_handler(CommandHandler("release", cmd_release))
    app.add_handler(CommandHandler("dispute", cmd_dispute))
    app.add_handler(CommandHandler("orders", cmd_orders))

    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
