import asyncio
from decimal import Decimal
from app.config import settings
from app.models import User, Gig, Order, Dispute
from app.payment.ledger import new_deposit_address
from app.payment.tron_stub import validate_deposit_tx
from sqlalchemy.orm import Session
import logging
import os
from telegram import BotCommand

from telegram import Update
from telegram.ext import Defaults, Application, CommandHandler, ContextTypes, ApplicationBuilder

from app.db_utils import db_session_decorator
from app.translator import get_translation
from app.lang_command import cmd_lang

async def ensure_user(tg_user, db: Session) -> User:
    u = db.query(User).filter(User.tg_id==str(tg_user.id)).first()
    if not u:
        u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
        db.add(u)
        db.flush()
        db.refresh(u)
    else:
        if u.username != (tg_user.username or ""):
            u.username = tg_user.username or ""
    return u

@db_session_decorator
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    await update.message.reply_text(
        _("👋 Welcome to the *Gigs Escrow Bot*\n" 
          "/newgig (USDT) | /newgigbtc (BTC) | /listings | /mygigs | /buy <id> | /confirm_tx <id> <txid> | /release <id> | /dispute <id> <reason> | /orders | /lang <en|it>"))

@db_session_decorator
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    await update.message.reply_text(
        _("Available commands:\n" 
          "/start - Start the bot\n" 
          "/newgig <Title> | <price_usd> | <description> - Create a new gig in USDT\n" 
          "/newgigbtc <Title> | <price_btc> | <description> - Create a new gig in BTC\n" 
          "/listings - Show active gigs\n" 
          "/mygigs - Show your gigs\n" 
          "/buy <id> - Buy a gig\n" 
          "/confirm_tx <id> <txid> - Confirm a transaction\n" 
          "/release <id> - Release funds to the seller\n" 
          "/dispute <id> <reason> - Open a dispute\n" 
          "/orders - Show your orders\n" 
          "/lang <en|it> - Set your language"))

@db_session_decorator
async def cmd_newgig(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text(_("Usage: /newgig Title | price_usd | description"))
        return
    payload = args[1]
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) < 2:
        await update.message.reply_text(_("Format: Title | price_usd | description"))
        return
    title = parts[0][:140]
    try:
        price = Decimal(parts[1])
    except:
        await update.message.reply_text(_("Invalid price."))
        return
    descr = parts[2] if len(parts) > 2 else ""

    seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
    g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price, currency=settings.PRIMARY_ASSET)
    db.add(g)
    db.flush()
    db.refresh(g)
    await update.message.reply_text(_("✅ Gig #{gig_id} created: *{title}* — ${price} ({currency})").format(gig_id=g.id, title=title, price=price, currency=settings.PRIMARY_ASSET))

@db_session_decorator
async def cmd_newgigbtc(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text(_("Usage: /newgigbtc Title | price_btc | description"))
        return
    payload = args[1]
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) < 2:
        await update.message.reply_text(_("Format: Title | price_btc | description"))
        return
    title = parts[0][:140]
    try:
        price_btc = Decimal(parts[1])
    except:
        await update.message.reply_text(_("Invalid BTC price."))
        return
    descr = parts[2] if len(parts) > 2 else ""

    seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
    g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price_btc, currency="BTC-ONCHAIN")
    db.add(g)
    db.flush()
    db.refresh(g)
    await update.message.reply_text(_("✅ BTC Gig #{gig_id} created: *{title}* — {price_btc} BTC").format(gig_id=g.id, title=title, price_btc=price_btc))

@db_session_decorator
async def cmd_listings(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    gigs = db.query(Gig).filter(Gig.active==True).order_by(Gig.id.desc()).limit(20).all()
    if not gigs:
        await update.message.reply_text(_("No gigs at the moment. /newgig"))
        return
    lines = [_("📋 *Gigs:*")]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
    lines.append(_("\nTo buy: /buy <id>"))
    await update.message.reply_text("\n".join(lines))

@db_session_decorator
async def cmd_mygigs(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    u = await ensure_user(update.effective_user, db)
    _ = get_translation(u)
    seller = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    gigs = db.query(Gig).filter(Gig.seller_id==seller.id).order_by(Gig.id.desc()).all()
    if not gigs:
        await update.message.reply_text(_("You have no gigs. /newgig"))
        return
    lines = [_("🧾 *Your gigs:*")]
    for g in gigs:
        lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency} — {_('ON') if g.active else _('OFF')}")
    await update.message.reply_text("\n".join(lines))

@db_session_decorator
async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split()
    if len(args) < 2:
        await update.message.reply_text(_("Usage: /buy <gig_id>"))
        return
    try:
        gig_id = int(args[1])
    except:
        await update.message.reply_text(_("Invalid ID."))
        return
    buyer = await ensure_user(update.effective_user, db)
    g = db.query(Gig).filter(Gig.id==gig_id, Gig.active==True).first()
    if not g:
        await update.message.reply_text(_("Gig not found or inactive."))
        return
    buyer_obj = db.query(User).filter(User.tg_id==str(buyer.tg_id)).first()
    o = Order(gig_id=g.id, buyer_id=buyer_obj.id, seller_id=g.seller_id,
              status="AWAIT_DEPOSIT", expected_amount=g.price_usd, escrow_fee_pct=8.00)
    db.add(o)
    db.flush()
    db.refresh(o)
    dep = new_deposit_address(o.id, g.currency)
    o.deposit_address = dep.address
    db.flush()
    db.refresh(o)
    await update.message.reply_text(
        _("🛡️ Order created. Deposit *{amt}* in {asset} to the address:\n`{addr}`\n\n" 
          "After payment: /confirm_tx {oid} <txid>")
        .format(amt=g.price_usd, asset=g.currency, addr=o.deposit_address, oid=o.id))

@db_session_decorator
async def cmd_confirm_tx(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split()
    if len(args) < 3:
        await update.message.reply_text(_("Usage: /confirm_tx <order_id> <txid>"))
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text(_("Invalid order_id."))
        return
    txid = args[2].strip()
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        await update.message.reply_text(_("Order not found."))
        return
    ok = False
    if o.gig.currency.startswith("USDT-TRON"):
        ok = await validate_deposit_tx(txid, Decimal(o.expected_amount))
    elif o.gig.currency.startswith("BTC-ONCHAIN"):
        from app.payment import btc_onchain
        ok = await btc_onchain.validate_deposit(o.deposit_address, Decimal(o.expected_amount))
    if not ok:
        await update.message.reply_text(_("⚠️ Invalid deposit."))
        return
    o.txid = txid; o.status = "FUNDS_HELD"
    db.flush()
    db.refresh(o)
    await update.message.reply_text(_("✅ Deposit confirmed. Funds are in escrow. Use /release {oid} when ready.").format(oid=oid))

@db_session_decorator
async def cmd_release(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split()
    if len(args) < 2:
        await update.message.reply_text(_("Usage: /release <order_id>"))
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text(_("Invalid order_id."))
        return
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        await update.message.reply_text(_("Order not found."))
        return
    if o.status != "FUNDS_HELD":
        await update.message.reply_text(_("Order not in escrow."))
        return
    o.status = "RELEASED"
    db.flush()
    db.refresh(o)
    await update.message.reply_text(_("🔓 Release marked. (On-chain transfer by worker/admin)"))

@db_session_decorator
async def cmd_dispute(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    args = (update.message.text or "").split(" ", 2)
    if len(args) < 3:
        await update.message.reply_text(_("Usage: /dispute <order_id> <reason>"))
        return
    try:
        oid = int(args[1])
    except:
        await update.message.reply_text(_("Invalid order_id."))
        return
    reason = args[2].strip()
    u = await ensure_user(update.effective_user, db)
    user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    o = db.query(Order).filter(Order.id==oid).first()
    if not o:
        await update.message.reply_text(_("Order not found."))
        return
    d = Dispute(order_id=o.id, opened_by=user_obj.id, reason=reason, status="OPEN")
    db.add(d)
    await update.message.reply_text(_("🧑‍⚖️ Dispute opened. Under review."))
    if settings.ADMIN_USER_ID:
        try:
            await context.bot.send_message(chat_id=settings.ADMIN_USER_ID, text=_("⚖️ Dispute for order {oid}: {reason}").format(oid=oid, reason=reason))
        except Exception:
            pass

@db_session_decorator
async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None):
    user = await ensure_user(update.effective_user, db)
    _ = get_translation(user)
    user_obj = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
    orders = db.query(Order).filter((Order.buyer_id==user_obj.id)|(Order.seller_id==user_obj.id)).order_by(Order.id.desc()).limit(10).all()
    if not orders:
        await update.message.reply_text(_("No orders."))
        return
    lines = [_("📦 *Orders:*")]
    for o in orders:
        lines.append(f"#{o.id} — {o.status} — ${o.expected_amount} — {o.deposit_address or '-'}")
    await update.message.reply_text("\n".join(lines))

async def run_bot_background():
    log = logging.getLogger(__name__)
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        log.warning("TELEGRAM_TOKEN not set: bot NOT started.")
        return

    log.info("Building bot application...")
    app = ApplicationBuilder().token(token).build()

    # Define commands and their handlers directly
    commands = {
        "start": ("👋 Start the bot", cmd_start),
        "help": ("❓ Show help", cmd_help),
        "newgig": ("➕ Create a new gig", cmd_newgig),
        "mygigs": ("🧾 See your gigs", cmd_mygigs),
        "buy": ("🛒 Buy a gig", cmd_buy),
        "release": ("🔓 Release funds", cmd_release),
        "lang": ("🌐 Change language", cmd_lang),
    }

    bot_commands = [BotCommand(cmd, desc) for cmd, (desc, _) in commands.items()]
    for cmd, (_, handler) in commands.items():
        app.add_handler(CommandHandler(cmd, handler))
    
    log.info(f"Added {len(commands)} command handlers.")

    await app.initialize()
    await app.start()
    
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.bot.set_my_commands(bot_commands)
        log.info("Bot commands set.")
        
        await app.updater.start_polling()
        log.info("Telegram bot is running and polling for updates.")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        log.info("Bot operation was cancelled.")
    except Exception as e:
        log.critical(f"A critical error occurred in the bot's main loop: {e}", exc_info=True)
    finally:
        log.info("Shutting down bot...")
        try:
            if app.updater and app.updater.is_running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            log.info("Telegram bot stopped cleanly.")
        except Exception as e:
            log.error(f"Error during bot shutdown: {e}", exc_info=True)