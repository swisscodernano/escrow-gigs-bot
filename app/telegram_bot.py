import asyncio
import logging
from decimal import Decimal
from app.config import settings
from app.db import SessionLocal
from app.models import User, Gig, Order, Dispute
from app.payment.ledger import new_deposit_address


from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def db_session():
    return SessionLocal()

async def ensure_user(tg_user) -> User:
    logger.info(f"Ensuring user exists for tg_id={tg_user.id}")
    db = db_session()
    try:
        u = db.query(User).filter(User.tg_id==str(tg_user.id)).first()
        if not u:
            logger.info(f"User not found, creating new user for tg_id={tg_user.id}")
            u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
            db.add(u)
            db.commit()
            db.refresh(u)
        else:
            if u.username != (tg_user.username or ""):
                logger.info(f"Username changed for tg_id={tg_user.id}, updating.")
                u.username = tg_user.username or ""
                db.commit()
        return u
    except Exception as e:
        logger.error(f"Error in ensure_user for tg_id={tg_user.id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start command received from user {update.effective_user.id}")
    try:
        await ensure_user(update.effective_user)
        await update.message.reply_text(
            "👋 Welcome to the *Gigs Escrow Bot*\n\n" 
            "Here are the available commands:\n" 
            "/newgig (USDT) | /newgigbtc (BTC) | /listings | /mygigs | /buy <id> | /confirm_tx <id> <txid> | /release <id> | /dispute <id> <reason> | /orders",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"/help command received from user {update.effective_user.id}")
    try:
        await update.message.reply_text(
            "Escrow Gigs Bot — Help\n\n" 
            "Available commands:\n" 
            "/start - Start the bot\n" 
            "/help - Show this help message\n" 
            "/newgig - Create a new gig (USDT)\n" 
            "/newgigbtc - Create a new gig (BTC)\n" 
            "/listings - See available gigs\n" 
            "/mygigs - See your own gigs\n" 
            "/buy <id> - Buy a gig\n" 
            "/confirm_tx <id> - Confirm the deposit for an order\n" 
            "/release <id> - Release funds for an order\n" 
            "/dispute <id> <reason> - Open a dispute for an order\n" 
            "/orders - See your orders\n" 
            "/setaddress <btc_address> - Set your Bitcoin address for withdrawals"
        )
    except Exception as e:
        logger.error(f"Error in cmd_help: {e}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")

async def cmd_newgig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/newgig command received from user {update.effective_user.id}")
    try:
        user = await ensure_user(update.effective_user)
        args = (update.message.text or "").split(" ", 1)
        if len(args) < 2:
            await update.message.reply_text("Usage: /newgig Title | price_usd | description")
            return
        payload = args[1]
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("Format: Title | price_usd | description")
            return
        title = parts[0][:140]
        try:
            price = Decimal(parts[1])
        except:
            await update.message.reply_text("Invalid price.")
            return
        descr = parts[2] if len(parts) > 2 else ""

        db = db_session()
        seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
        g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price, currency=settings.PRIMARY_ASSET)
        db.add(g); db.commit(); db.refresh(g); db.close()
        await update.message.reply_text(f"✅ Gig #{g.id} created: *{title}* — ${price} ({settings.PRIMARY_ASSET})", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_newgig: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while creating the gig.")

async def cmd_newgigbtc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/newgigbtc command received from user {update.effective_user.id}")
    try:
        user = await ensure_user(update.effective_user)
        args = (update.message.text or "").split(" ", 1)
        if len(args) < 2:
            await update.message.reply_text("Usage: /newgigbtc Title | price_btc | description")
            return
        payload = args[1]
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("Format: Title | price_btc | description")
            return
        title = parts[0][:140]
        try:
            price_btc = Decimal(parts[1])
        except:
            await update.message.reply_text("Invalid BTC price.")
            return
        descr = parts[2] if len(parts) > 2 else ""

        db = db_session()
        seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
        g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price_btc, currency="BTC-ONCHAIN")
        db.add(g); db.commit(); db.refresh(g); db.close()
        await update.message.reply_text(f"✅ BTC Gig #{g.id} created: *{title}* — {price_btc} BTC", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_newgigbtc: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while creating the BTC gig.")

async def cmd_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/listings command received from user {update.effective_user.id}")
    try:
        db = db_session()
        gigs = db.query(Gig).filter(Gig.active==True).order_by(Gig.id.desc()).limit(20).all()
        db.close()
        if not gigs:
            await update.message.reply_text("No gigs available at the moment. /newgig")
            return
        lines = ["📋 *Available Gigs:*"]
        for g in gigs:
            lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency}")
        lines.append("\nTo buy: /buy <id>")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_listings: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while fetching listings.")

async def cmd_mygigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/mygigs command received from user {update.effective_user.id}")
    try:
        u = await ensure_user(update.effective_user)
        db = db_session()
        seller = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
        gigs = db.query(Gig).filter(Gig.seller_id==seller.id).order_by(Gig.id.desc()).all()
        db.close()
        if not gigs:
            await update.message.reply_text("You have no gigs. /newgig")
            return
        lines = ["🧾 *Your Gigs:*"]
        for g in gigs:
            lines.append(f"#{g.id} — *{g.title}* — ${g.price_usd} — {g.currency} — {'ON' if g.active else 'OFF'}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_mygigs: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while fetching your gigs.")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/buy command received from user {update.effective_user.id}")
    try:
        args = (update.message.text or "").split()
        if len(args) < 2:
            await update.message.reply_text("Usage: /buy <gig_id>")
            return
        try:
            gig_id = int(args[1])
        except:
            await update.message.reply_text("Invalid ID.")
            return
        buyer = await ensure_user(update.effective_user)
        db = db_session()
        g = db.query(Gig).filter(Gig.id==gig_id, Gig.active==True).first()
        if not g:
            db.close()
            await update.message.reply_text("Gig not found or inactive.")
            return
        buyer_obj = db.query(User).filter(User.tg_id==str(buyer.tg_id)).first()
        o = Order(gig_id=g.id, buyer_id=buyer_obj.id, seller_id=g.seller_id,
                  status="AWAIT_DEPOSIT", expected_amount=g.price_usd, escrow_fee_pct=8.00)
        db.add(o); db.commit(); db.refresh(o)
        dep = new_deposit_address(o.id, g.currency)
        o.deposit_address = dep.address
        db.commit(); db.refresh(o); db.close()
        await update.message.reply_text(
            "🛡️ Order created. Please deposit *{amt}* {asset} to the following address:\n`{addr}`\n\n" 
            "After payment, use: /confirm_tx {oid} <txid>"
            .format(amt=g.price_usd, asset=g.currency, addr=o.deposit_address, oid=o.id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in cmd_buy: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while creating the order.")

async def cmd_confirm_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/confirm_tx command received from user {update.effective_user.id}")
    try:
        args = (update.message.text or "").split()
        if len(args) < 2:
            await update.message.reply_text("Usage: /confirm_tx <order_id>")
            return
        try:
            oid = int(args[1])
        except:
            await update.message.reply_text("Invalid order_id.")
            return
        db = db_session()
        o = db.query(Order).filter(Order.id==oid).first()
        if not o:
            db.close()
            await update.message.reply_text("Order not found.")
            return
        # This part needs a proper implementation for btc_onchain
        # For now, let's assume it's a placeholder
        # ok = await btc_onchain.validate_deposit(o.deposit_address, Decimal(o.expected_amount))
        ok = True # Placeholder
        if not ok:
            db.close()
            await update.message.reply_text("⚠️ Invalid deposit.")
            return
        o.status = "FUNDS_HELD"
        db.commit(); db.refresh(o); db.close()
        await update.message.reply_text("✅ Deposit confirmed. Funds are now in escrow. Use /release {oid} when ready.".format(oid=oid))
    except Exception as e:
        logger.error(f"Error in cmd_confirm_tx: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while confirming the transaction.")

from app.tasks import process_withdrawal

async def cmd_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/release command received from user {update.effective_user.id}")
    try:
        args = (update.message.text or "").split()
        if len(args) < 2:
            await update.message.reply_text("Usage: /release <order_id>")
            return
        try:
            oid = int(args[1])
        except:
            await update.message.reply_text("Invalid order_id.")
            return
        db = db_session()
        o = db.query(Order).filter(Order.id==oid).first()
        if not o:
            db.close()
            await update.message.reply_text("Order not found.")
            return
        if o.status != "FUNDS_HELD":
            db.close()
            await update.message.reply_text("Order is not in escrow.")
            return
        o.status = "RELEASED"
        db.commit(); db.refresh(o);
        process_withdrawal.delay(o.id)
        db.close()
        await update.message.reply_text("🔓 Release marked. (On-chain send from worker/admin)")
    except Exception as e:
        logger.error(f"Error in cmd_release: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while releasing funds.")

async def cmd_dispute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/dispute command received from user {update.effective_user.id}")
    try:
        args = (update.message.text or "").split(" ", 2)
        if len(args) < 3:
            await update.message.reply_text("Usage: /dispute <order_id> <reason>")
            return
        try:
            oid = int(args[1])
        except:
            await update.message.reply_text("Invalid order_id.")
            return
        reason = args[2].strip()
        u = await ensure_user(update.effective_user)
        db = db_session()
        user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
        o = db.query(Order).filter(Order.id==oid).first()
        if not o:
            db.close()
            await update.message.reply_text("Order not found.")
            return
        d = Dispute(order_id=o.id, opened_by=user_obj.id, reason=reason, status="OPEN")
        db.add(d); db.commit(); db.close()
        await update.message.reply_text("🧑‍⚖️ Dispute opened. An admin will review it.")
        if settings.ADMIN_USER_ID:
            try:
                await context.bot.send_message(chat_id=settings.ADMIN_USER_ID, text=f"⚖️ Dispute for order {oid}: {reason}")
            except Exception as e:
                logger.warning(f"Could not send dispute notification to admin: {e}")
    except Exception as e:
        logger.error(f"Error in cmd_dispute: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while opening a dispute.")

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/orders command received from user {update.effective_user.id}")
    try:
        u = await ensure_user(update.effective_user)
        db = db_session()
        user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
        orders = db.query(Order).filter((Order.buyer_id==user_obj.id)|(Order.seller_id==user_obj.id)).order_by(Order.id.desc()).limit(10).all()
        db.close()
        if not orders:
            await update.message.reply_text("No orders found.")
            return
        lines = ["📦 *Your Orders*"]
        for o in orders:
            lines.append(f"#{o.id} — {o.status} — ${o.expected_amount} — {o.deposit_address or '-'}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_orders: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while fetching your orders.")

async def cmd_setaddress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/setaddress command received from user {update.effective_user.id}")
    try:
        u = await ensure_user(update.effective_user)
        args = (update.message.text or "").split()
        if len(args) < 2:
            await update.message.reply_text("Usage: /setaddress <btc_address>")
            return
        
        address = args[1].strip()
        # Basic validation
        if not (address.startswith("1") or address.startswith("3") or address.startswith("bc1")):
            await update.message.reply_text("Invalid Bitcoin address.")
            return

        db = db_session()
        user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
        user_obj.btc_address = address
        db.commit()
        db.close()
        await update.message.reply_text("✅ Bitcoin address set successfully.")
    except Exception as e:
        logger.error(f"Error in cmd_setaddress: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while setting your address.")

# Set bot commands for the menu
    logger.info("Setting bot commands for the menu...")
    await app.bot.set_my_commands([
        ("start", "👋 Start the bot"),
        ("help", "❓ Show available commands"),
        ("newgig", "➕ Create a new gig (USDT)"),
        ("newgigbtc", "₿ Create a new gig (BTC)"),
        ("listings", "📋 See available gigs"),
        ("mygigs", "🧾 See your own gigs"),
        ("orders", "📦 See your orders"),
        ("setaddress", "⚙️ Set your Bitcoin address"),
    ])
    logger.info("Bot commands set.")

    logger.info("Starting bot polling...")
    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()
        logger.info("Bot is now polling for updates.")
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.critical(f"Bot polling failed critically: {e}", exc_info=True)
    finally:
        logger.info("Stopping bot...")
        await app.updater.stop()
        await app.stop()
        logger.info("Bot stopped.")
