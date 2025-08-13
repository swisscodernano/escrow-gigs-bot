import os, httpx
from decimal import Decimal
from typing import Tuple
from bitcoinlib.keys import HDKey

# Env
ENV_NET = os.getenv("BTC_NETWORK", "mainnet").lower()
BITCOINLIB_NET = "bitcoin" if ENV_NET in ("mainnet","bitcoin") else "testnet"
ESPLORA_URL = os.getenv("ESPLORA_URL", "https://blockstream.info/api")
BTC_XPRV = os.getenv("BTC_XPRV", "")
BTC_XPUB = os.getenv("BTC_XPUB", "")

# BIP84 path
ACCOUNT_PATH = "m/84h/0h/0h" if BITCOINLIB_NET == "bitcoin" else "m/84h/1h/0h"
RECEIVE_PATH = ACCOUNT_PATH + "/0/{}"

def _hdkey():
    if BTC_XPRV: return HDKey(BTC_XPRV, network=BITCOINLIB_NET)
    if BTC_XPUB: return HDKey(BTC_XPUB, network=BITCOINLIB_NET)
    raise RuntimeError("BTC_XPRV or BTC_XPUB must be set")

def derive_address(order_id: int) -> Tuple[str, str]:
    k = _hdkey()
    child = k.subkey_for_path(RECEIVE_PATH.format(order_id))
    return child.address(witness_type='segwit'), RECEIVE_PATH.format(order_id)

async def _esplora_get(path: str):
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(ESPLORA_URL + path)
        r.raise_for_status()
        return r.json()

async def validate_deposit(address: str, expected_btc: Decimal, min_confs: int = 1) -> bool:
    d = await _esplora_get(f"/address/{address}")
    funded = int(d.get("chain_stats", {}).get("funded_txo_sum", 0))
    spent  = int(d.get("chain_stats", {}).get("spent_txo_sum", 0))
    need = int((expected_btc * Decimal(1e8)).to_integral_value())
    return (funded - spent) >= need
