from fastapi.testclient import TestClient
from app import app
from db import Base, engine, SessionLocal
from models import User
from models.wallet import get_or_create_wallet


def setup_function(fn):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_webhook_deposit():
    db = SessionLocal()
    u = User(tg_id="1")
    db.add(u); db.commit(); db.refresh(u)
    db.close()

    client = TestClient(app)
    payload = {"user_id": u.id, "amount": "5.00", "status": "succeeded", "ext_ref": "abc"}
    r = client.post("/webhook/payments", json=payload)
    assert r.status_code == 200

    db = SessionLocal()
    w = get_or_create_wallet(db, u.id)
    assert float(w.balance) == 5.0
    db.close()
