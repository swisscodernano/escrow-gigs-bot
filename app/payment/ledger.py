
from app.payment import btc_onchain

def new_deposit_address(order_id: int, currency: str):
    if currency == "BTC-ONCHAIN":
        return btc_onchain.new_deposit_address(order_id)
    else:
        raise ValueError(f"Unsupported currency: {currency}")
