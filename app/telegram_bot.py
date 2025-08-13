import asyncio
from decimal import Decimal
from app.config import settings
from app.db import SessionLocal
from app.models import User, Gig, Order, Dispute, Feedback
from app.payment.ledger import new_deposit_address
from app.payment.tron_stub import validate_deposit_tx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Defaults, Application, CommandHandler, ContextTypes, CallbackQueryHandler

def db_session():
    return SessionLocal()

async def ensure_user(tg_user) -> User:
    db = db_session()
    u = db.query(User).filter(User.tg_id==str(tg_user.id)).first()
    if not u:
        u = User(tg_id=str(tg_user.id), username=tg_user.username or "")
        db.add(u); db.commit(); db.refresh(u)
    else:
        if u.username != (tg_user.username or ""):
            u.username = tg_user.username or ""
            db.commit()
    db.close()
    return u

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    keyboard = [
        [InlineKeyboardButton("📋 Annunci", callback_data="listings")],
        [InlineKeyboardButton("📦 I Miei Ordini", callback_data="orders")],
        [InlineKeyboardButton("🧾 I Miei Annunci", callback_data="mygigs")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 *Benvenuto nel Gigs Escrow Bot*", reply_markup=reply_markup)

async def cmd_newgig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update.effective_user)
    args = (update.message.text or "").split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text("Uso: /newgig Titolo | prezzo_usd | descrizione")
        return
    payload = args[1]
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Formato: Titolo | prezzo_usd | descrizione")
        return
    title = parts[0][:140]
    try:
        price = Decimal(parts[1])
    except:
        await update.message.reply_text("Prezzo non valido.")
        return
    descr = parts[2] if len(parts) > 2 else ""

    db = db_session()
    seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
    g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price, currency=settings.PRIMARY_ASSET)
    db.add(g); db.commit(); db.refresh(g); db.close()
    await update.message.reply_text(f"✅ Annuncio #{g.id} creato: *{title}* — ${price} ({settings.PRIMARY_ASSET})")

async def cmd_newgigbtc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update.effective_user)
    args = (update.message.text or "").split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text("Uso: /newgigbtc Titolo | prezzo_btc | descrizione")
        return
    payload = args[1]
    parts = [p.strip() for p in payload.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Formato: Titolo | prezzo_btc | descrizione")
        return
    title = parts[0][:140]
    try:
        price_btc = Decimal(parts[1])
    except:
        await update.message.reply_text("Prezzo BTC non valido.")
        return
    descr = parts[2] if len(parts) > 2 else ""

    db = db_session()
    seller = db.query(User).filter(User.tg_id==str(user.tg_id)).first()
    g = Gig(seller_id=seller.id, title=title, description=descr, price_usd=price_btc, currency="BTC-ONCHAIN")
    db.add(g); db.commit(); db.refresh(g); db.close()
    await update.message.reply_text(f"✅ Annuncio BTC #{g.id} creato: *{title}* — {price_btc} BTC")

async def cmd_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = db_session()
    gigs = db.query(Gig).filter(Gig.active==True).order_by(Gig.id.desc()).limit(10).all()
    db.close()
    if not gigs:
        await update.message.reply_text("Nessun annuncio al momento. /newgig")
        return
    
    await update.message.reply_text("📋 *Annunci Recenti:*")
    for g in gigs:
        keyboard = [[InlineKeyboardButton("🛒 Compra", callback_data=f"buy:{g.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"#{g.id} — *{g.title}*\n"
            f"_{g.description or 'Nessuna descrizione'}_ \n"
            f"Prezzo: *{g.price_usd} {g.currency}*",
            reply_markup=reply_markup
        )

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
        ok = await btc_onchain.validate_deposit(o.deposit_address, txid, Decimal(o.expected_amount))
    if not ok:
        db.close()
        await update.message.reply_text("⚠️ Deposito non valido.")
        return
    o.txid = txid; o.status = "FUNDS_HELD"
    db.commit(); db.refresh(o)

    # Notifica al venditore
    try:
        seller_tg_id = o.seller.tg_id
        await context.bot.send_message(
            chat_id=seller_tg_id,
            text=f"💰 Deposito confermato per l'ordine #{o.id}. I fondi sono in garanzia. Puoi procedere."
        )
    except Exception as e:
        print(f"Errore nell'invio notifica al venditore {o.seller_id}: {e}")

    db.close()
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
    db.commit(); db.refresh(o)

    # Notifica al venditore
    try:
        seller_tg_id = o.seller.tg_id
        buyer_username = o.buyer.username or 'utente'
        await context.bot.send_message(
            chat_id=seller_tg_id,
            text=f"✅ Fondi rilasciati da @{buyer_username} per l'ordine #{o.id}. Il pagamento è in elaborazione."
        )
    except Exception as e:
        print(f"Errore nell'invio notifica al venditore {o.seller_id}: {e}")

    db.close()
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
    
    await update.message.reply_text("📦 *I tuoi ordini recenti:*")
    for o in orders:
        keyboard = [[InlineKeyboardButton("📄 Dettagli", callback_data=f"order:{o.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Ordine #{o.id} | *{o.gig.title}*\n"
            f"Stato: *{o.status}* | Importo: *{o.expected_amount} {o.gig.currency}*",
            reply_markup=reply_markup
        )

async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split(" ", 3)
    if len(args) < 3:
        await update.message.reply_text("Uso: /feedback <order_id> <punteggio 1-5> [commento]")
        return
    try:
        oid = int(args[1])
        score = int(args[2])
        if not 1 <= score <= 5: raise ValueError()
    except:
        await update.message.reply_text("ID ordine o punteggio non validi.")
        return
    comment = args[3].strip() if len(args) > 3 else ""

    u = await ensure_user(update.effective_user)
    db = db_session()
    user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
    order = db.query(Order).filter(Order.id==oid).first()

    if not order or (order.buyer_id != user_obj.id and order.seller_id != user_obj.id):
        await update.message.reply_text("Ordine non trovato.")
        db.close(); return
    
    if order.status != "RELEASED":
        await update.message.reply_text("Puoi lasciare un feedback solo per ordini completati.")
        db.close(); return

    if user_obj.id == order.buyer_id:
        reviewer_id, reviewee_id = order.buyer_id, order.seller_id
    else:
        reviewer_id, reviewee_id = order.seller_id, order.buyer_id

    existing_feedback = db.query(Feedback).filter(Feedback.order_id == oid, Feedback.reviewer_id == reviewer_id).first()
    if existing_feedback:
        await update.message.reply_text("Hai già lasciato un feedback per questo ordine.")
        db.close(); return

    fb = Feedback(order_id=oid, reviewer_id=reviewer_id, reviewee_id=reviewee_id, score=score, comment=comment)
    db.add(fb); db.commit()
    
    try:
        other_user = db.query(User).filter(User.id==reviewee_id).first()
        await context.bot.send_message(chat_id=other_user.tg_id, text=f"Hai ricevuto un nuovo feedback per l'ordine #{oid}: {score}/5")
    except Exception as e:
        print(f"Errore nell'invio notifica feedback: {e}")

    db.close()
    await update.message.reply_text("✅ Grazie per il tuo feedback!")

from sqlalchemy.orm import aliased
from sqlalchemy import func

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = (update.message.text or "").split()
    db = db_session()
    
    target_username = args[1].lstrip('@') if len(args) > 1 else update.effective_user.username
    if not target_username:
        await update.message.reply_text("Specifica un username o assicurati di averne uno impostato su Telegram.")
        db.close()
        return

    user = db.query(User).filter(User.username == target_username).first()
    if not user:
        await update.message.reply_text(f"Utente @{target_username} non trovato.")
        db.close()
        return

    # Calcola statistiche feedback
    feedbacks = db.query(Feedback).filter(Feedback.reviewee_id == user.id).all()
    
    if not feedbacks:
        avg_score = "N/A"
        feedback_count = 0
    else:
        total_score = sum(f.score for f in feedbacks)
        feedback_count = len(feedbacks)
        avg_score = f"{total_score / feedback_count:.1f}/5"

    # Statistiche vendite e acquisti
    sales_count = db.query(Order).filter(Order.seller_id == user.id, Order.status == "RELEASED").count()
    purchases_count = db.query(Order).filter(Order.buyer_id == user.id, Order.status == "RELEASED").count()

    profile_text = [
        f"👤 *Profilo di @{user.username}*",
        f"⭐ *Reputazione:* {avg_score} ({feedback_count} recensioni)",
        f"🛒 *Acquisti completati:* {purchases_count}",
        f"💰 *Vendite completate:* {sales_count}",
    ]

    # Ultimi commenti
    latest_feedbacks = db.query(Feedback).filter(Feedback.reviewee_id == user.id).order_by(Feedback.created_at.desc()).limit(3).all()
    if latest_feedbacks:
        profile_text.append("\n*Ultimi commenti:*")
        for fb in latest_feedbacks:
            reviewer = fb.reviewer.username or "Utente"
            profile_text.append(f'🗣️ @{reviewer}: "{fb.comment}" ({fb.score}/5)')

    db.close()
    await update.message.reply_text("\n".join(profile_text))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    action, value = query.data.split(":")
    
    if action == "buy":
        gig_id = int(value)
        buyer = await ensure_user(query.from_user)
        db = db_session()
        g = db.query(Gig).filter(Gig.id==gig_id, Gig.active==True).first()
        if not g:
            db.close()
            await query.edit_message_text("Annuncio non più disponibile.")
            return
        
        buyer_obj = db.query(User).filter(User.tg_id==str(buyer.tg_id)).first()
        o = Order(gig_id=g.id, buyer_id=buyer_obj.id, seller_id=g.seller_id,
                  status="AWAIT_DEPOSIT", expected_amount=g.price_usd, escrow_fee_pct=8.00)
        db.add(o); db.commit(); db.refresh(o)
        dep = new_deposit_address(o.id, g.currency)
        o.deposit_address = dep.address
        db.commit(); db.refresh(o)
        
        try:
            seller_tg_id = o.seller.tg_id
            await context.bot.send_message(
                chat_id=seller_tg_id,
                text=f"🔔 Nuovo ordine ricevuto per l'annuncio #{g.id} da @{buyer.username or 'utente'}. In attesa di deposito."
            )
        except Exception as e:
            print(f"Errore nell'invio notifica al venditore {o.seller_id}: {e}")

        db.close()
        await query.edit_message_text(
            "🛡️ Ordine creato. Deposita *{amt}* in {asset} all\'indirizzo:\n`{addr}`\n\n"
            "Dopo il pagamento: /confirm_tx {oid} <txid>"
            .format(amt=g.price_usd, asset=g.currency, addr=o.deposit_address, oid=o.id)
        )
    
    elif action == "order":
        oid = int(value)
        u = await ensure_user(query.from_user)
        db = db_session()
        user_obj = db.query(User).filter(User.tg_id==str(u.tg_id)).first()
        order = db.query(Order).filter(Order.id==oid).first()
        
        if not order or (order.buyer_id != user_obj.id and order.seller_id != user_obj.id):
            db.close()
            await query.edit_message_text("Ordine non trovato o non hai i permessi per vederlo.")
            return

        gig = order.gig
        buyer = order.buyer
        seller = order.seller
        
        details = [
            f"📦 *Dettagli Ordine #{order.id}*",
            f"🏷️ *Annuncio:* {gig.title}",
            f"💲 *Importo:* {order.expected_amount} {gig.currency}",
            f"👤 *Venditore:* @{seller.username}",
            f"👤 *Acquirente:* @{buyer.username}",
            f"🚦 *Stato:* {order.status}",
        ]
        if order.deposit_address:
            details.append(f"🏦 *Indirizzo Deposito:* `{order.deposit_address}`")
        if order.txid:
            details.append(f"🔗 *TXID:* `{order.txid}`")

        keyboard = []
        # Aggiungi pulsanti contestuali
        if order.status == "FUNDS_HELD" and user_obj.id == order.buyer_id:
            keyboard.append([InlineKeyboardButton("✅ Rilascia Fondi", callback_data=f"release:{order.id}")])
        if order.status == "RELEASED":
             keyboard.append([InlineKeyboardButton("⭐ Lascia Feedback", callback_data=f"feedback:{order.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        db.close()
        await query.edit_message_text("\n".join(details), reply_markup=reply_markup)


async def run_bot_background():
    print("--- Avvio del Bot ---")
    print(f"--- TOKEN LETTO: {settings.BOT_TOKEN} ---")
    app = Application.builder().token(settings.BOT_TOKEN).defaults(Defaults(parse_mode=None)).build()
    
    # Gestori Comandi
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("newgig", cmd_newgig))
    app.add_handler(CommandHandler("newgigbtc", cmd_newgigbtc))
    app.add_handler(CommandHandler("listings", cmd_listings))
    app.add_handler(CommandHandler("mygigs", cmd_mygigs))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("confirm_tx", cmd_confirm_tx))
    app.add_handler(CommandHandler("release", cmd_release))
    app.add_handler(CommandHandler("dispute", cmd_dispute))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("profile", cmd_profile))
    
    # Gestore Pulsanti
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Inizializzazione...")
    await app.initialize()
    print("Avvio...")
    await app.start()
    print("Avvio Polling...")
    await app.updater.start_polling()
    print("--- ✅ Bot avviato con successo e in ascolto ---")

    while True:
        try:
            await asyncio.sleep(3600)
            print("Il bot è ancora in esecuzione...")
        except Exception as e:
            print(f"Errore nel loop principale: {e}")
