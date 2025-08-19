import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from app.models import User, Gig, Order
from app.telegram_bot import cmd_release, db_session

@pytest.mark.asyncio
async def test_cmd_release_increments_reputation():
    # 1. Setup
    db = db_session()
    seller = User(tg_id="seller_tg_id", username="seller")
    buyer = User(tg_id="buyer_tg_id", username="buyer")
    db.add_all([seller, buyer])
    db.commit()

    gig = Gig(seller_id=seller.id, title="Test Gig", price_usd=Decimal("10.00"), currency="USDT-TRON")
    db.add(gig)
    db.commit()

    order = Order(gig_id=gig.id, buyer_id=buyer.id, seller_id=seller.id, status="FUNDS_HELD", expected_amount=Decimal("10.00"))
    db.add(order)
    db.commit()

    # 2. Mock Telegram objects
    update = AsyncMock()
    update.message = AsyncMock()
    update.message.text = f"/release {order.id}"
    context = MagicMock()

    # 3. Call the command
    await cmd_release(update, context)

    # 4. Assertions
    db.refresh(seller)
    assert seller.positive_feedback == 1

    # 5. Teardown
    db.delete(order)
    db.delete(gig)
    db.delete(seller)
    db.delete(buyer)
    db.commit()
    db.close()
