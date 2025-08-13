from decimal import Decimal
from app.db import Base, engine, SessionLocal
from app.models import User
from app.models.wallet import get_or_create_wallet, apply_deposit, place_hold, release_hold


def setup_function(fn):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_wallet_deposit_hold_release():
    db = SessionLocal()
    u = User(tg_id="1")
    db.add(u); db.commit(); db.refresh(u)

    apply_deposit(db, u.id, Decimal("10.00"))
    w = get_or_create_wallet(db, u.id)
    assert float(w.balance) == 10.0

    hold = place_hold(db, u.id, Decimal("4.00"))
    w = get_or_create_wallet(db, u.id)
    assert float(w.balance) == 6.0

    release_hold(db, hold.id, as_refund=True)
    w = get_or_create_wallet(db, u.id)
    assert float(w.balance) == 10.0

    hold2 = place_hold(db, u.id, Decimal("3.00"))
    release_hold(db, hold2.id, as_refund=False)
    w = get_or_create_wallet(db, u.id)
    assert float(w.balance) == 7.0
    db.close()
