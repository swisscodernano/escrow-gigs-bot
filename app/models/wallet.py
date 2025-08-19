from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db_core import Base


class Wallet(Base):
    __tablename__ = "wallets"
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    ext_ref: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# --- Helpers ---


def get_or_create_wallet(db, user_id: int, currency: str = "USD") -> Wallet:
    w = db.get(Wallet, user_id)
    if not w:
        w = Wallet(user_id=user_id, balance=Decimal("0"), currency=currency)
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def apply_deposit(db, user_id: int, amount: Decimal, ext_ref: str = "") -> Transaction:
    w = get_or_create_wallet(db, user_id)
    w.balance = Decimal(w.balance) + amount
    tx = Transaction(
        user_id=user_id,
        type="deposit",
        amount=amount,
        status="succeeded",
        ext_ref=ext_ref,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(w)
    return tx


def place_hold(db, user_id: int, amount: Decimal, ext_ref: str = "") -> Transaction:
    w = get_or_create_wallet(db, user_id)
    if Decimal(w.balance) < amount:
        raise ValueError("insufficient funds")
    w.balance = Decimal(w.balance) - amount
    tx = Transaction(
        user_id=user_id, type="hold", amount=amount, status="succeeded", ext_ref=ext_ref
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(w)
    return tx


def release_hold(db, hold_tx_id: int, as_refund: bool = False) -> Transaction:
    hold = db.get(Transaction, hold_tx_id)
    if not hold or hold.type != "hold":
        raise ValueError("invalid hold")
    if as_refund:
        w = get_or_create_wallet(db, hold.user_id)
        w.balance = Decimal(w.balance) + Decimal(hold.amount)
        tx_type = "refund"
    else:
        tx_type = "payout"
    tx = Transaction(
        user_id=hold.user_id,
        type=tx_type,
        amount=hold.amount,
        status="succeeded",
        ext_ref=hold.ext_ref,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    if as_refund:
        db.refresh(w)
    return tx
