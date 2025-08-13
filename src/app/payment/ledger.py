from dataclasses import dataclass
@dataclass
class DepositInfo:
    address: str
    memo: str | None = None
def new_deposit_address(order_id: int, asset: str) -> DepositInfo:
    if asset.startswith("USDT-TRON"):
        return DepositInfo(address="TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", memo=None)
    if asset.startswith("BTC-ONCHAIN"):
        from payment import btc_onchain
        addr, _ = btc_onchain.derive_address(order_id)
        return DepositInfo(address=addr, memo=None)
    return DepositInfo(address="GENERIC_DEMO_ADDRESS", memo=None)
