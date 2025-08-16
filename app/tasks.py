import os

from bip_utils import (
    Bip39SeedGenerator,
    Bip44,
    Bip44Changes,
    Bip44Coins,
)
from celery import Celery

from app.config import settings
from app.db import SessionLocal
from app.models import Order, User

celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


def get_wallet_from_mnemonic(mnemonic: str):
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    return bip44_mst_ctx


def get_blockcypher_token():
    token = os.environ.get("BLOCKCYPHER_TOKEN")
    if not token:
        raise ValueError("BLOCKCYPHER_TOKEN environment variable not set")
    return token


@celery_app.task
def process_withdrawal(order_id: int):
    db = SessionLocal()
    order = db.query(Order).get(order_id)
    if not order or order.status != "RELEASED":
        print(f"[WORKER] Order {order_id} invalid or not ready for withdrawal.")
        db.close()
        return

    print(f"[WORKER] Starting withdrawal for order #{order_id}...")

    seller = db.query(User).get(order.seller_id)
    if not seller.btc_address:
        print(f"[WORKER] Seller BTC address not set for order {order_id}.")
        db.close()
        return

    try:
        # Retrieve mnemonic from environment variable (for demonstration, in real app use secure storage)
        mnemonic = os.environ.get("BTC_WALLET_PASSPHRASE")
        if not mnemonic:
            raise ValueError("BTC_WALLET_PASSPHRASE environment variable not set")

        wallet_ctx = get_wallet_from_mnemonic(mnemonic)

        # For simplicity, we'll assume the first external address of the first account as the source
        # In a real app, you'd manage UTXOs and select appropriate inputs
        source_address_ctx = (
            wallet_ctx.Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(0)
        )
        source_address = source_address_ctx.PublicKey().ToAddress()

        # This is a simplified transaction creation. In a real scenario, you'd need to:
        # 1. Fetch UTXOs for source_address
        # 2. Calculate fees dynamically
        # 3. Build a raw transaction
        # 4. Sign the transaction
        # 5. Broadcast the signed transaction

        # For now, we'll simulate a successful transaction broadcast
        print(
            f"[WORKER] Simulating transaction from {source_address} to {seller.btc_address} for {order.expected_amount} BTC."
        )

        # Simulate broadcasting a transaction
        get_blockcypher_token()
        # This is a placeholder for actual transaction broadcasting logic
        # In a real scenario, you would build and sign a raw transaction and then push it.
        # Example: https://www.blockcypher.com/dev/bitcoin/#push-transaction-endpoint
        # For now, we'll just check if the token is valid and simulate success.

        # Simulate a successful broadcast
        tx_hash = "simulated_tx_" + str(order.id)  # Placeholder transaction ID

        order.txid = tx_hash
        order.status = "COMPLETED"
        db.commit()
        print(
            f"[WORKER] Withdrawal for order #{order.id} completed successfully (simulated). Transaction ID: {tx_hash}"
        )

    except Exception as e:
        print(f"[WORKER] Error during withdrawal for order {order.id}: {e}")
        # Optionally, update order status to indicate withdrawal failure
        # order.status = "WITHDRAWAL_FAILED"
        # db.commit()
    finally:
        db.close()
