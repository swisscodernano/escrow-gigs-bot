from decimal import Decimal
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.wallet import apply_deposit
from app.services.payments import get_provider

router = APIRouter()


@router.post("/webhook/payments")
async def payments_webhook(payload: Dict[str, Any], db: Session = Depends(get_db)):
    provider = get_provider()
    data = provider.verify_webhook(payload)
    if data.get("status") == "succeeded":
        amount = Decimal(str(data.get("amount", "0")))
        user_id = int(data.get("user_id"))
        apply_deposit(db, user_id, amount, data.get("ext_ref", ""))
    return {"ok": True}
