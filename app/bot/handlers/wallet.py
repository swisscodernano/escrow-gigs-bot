from db import SessionLocal
from models import User
from models.wallet import Transaction, get_or_create_wallet


async def wallet(update, context):
    tg = update.effective_user
    db = SessionLocal()
    u = db.query(User).filter(User.tg_id == str(tg.id)).first()
    if not u:
        u = User(tg_id=str(tg.id), username=tg.username or "")
        db.add(u)
        db.commit()
        db.refresh(u)
    w = get_or_create_wallet(db, u.id)
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == u.id)
        .order_by(Transaction.id.desc())
        .limit(10)
        .all()
    )
    lines = [
        f"💰 Balance: {w.balance} {w.currency}",
        "Add funds with /deposit <amount>",
        "History:",
    ]
    for t in txs:
        lines.append(f"{t.type} {t.amount} {t.status}")
    await update.effective_message.reply_text("\n".join(lines))
    db.close()
