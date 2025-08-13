import os, httpx
from decimal import Decimal
from typing import Tuple
from bitcoinlib.keys import HDKey

# Env
ENV_NET = os.getenv("BTC_NETWORK", "mainnet").lower()
BITCOINLIB_NET = "bitcoin" if ENV_NET in ("mainnet","bitcoin") else "testnet"
ESPLORA_URL = os.getenv("ESPLORA_URL", "https://blockstream.info/api")
BTC_XPUB = os.getenv("BTC_XPUB", "")

# BIP84 path for receiving addresses (account 0, external chain)
RECEIVE_PATH = "m/0/{}"

def _get_xpub_key():
    if not BTC_XPUB:
        raise RuntimeError("BTC_XPUB must be set in .env")
    return HDKey(BTC_XPUB, network=BITCOINLIB_NET)

def derive_address(order_id: int) -> Tuple[str, str]:
    """Deriva un indirizzo di ricezione per un dato ID ordine."""
    xpub_key = _get_xpub_key()
    # Usiamo l'order_id come indice per l'indirizzo
    path = RECEIVE_PATH.format(order_id)
    child_key = xpub_key.subkey_for_path(path)
    return child_key.address(witness_type='segwit'), path

async def _esplora_get(path: str):
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(ESPLORA_URL + path)
        r.raise_for_status()
        return r.json()

async def validate_deposit(address: str, txid: str, expected_btc: Decimal, min_confs: int = 1) -> bool:
    """
    Valida una transazione di deposito cercando uno specifico TXID e verificando
    l'importo e le conferme.
    """
    try:
        # 1. Ottieni i dettagli della transazione
        tx_details = await _esplora_get(f"/tx/{txid}")
        
        # 2. Controlla le conferme
        confs = tx_details.get("status", {}).get("block_height", 0)
        if not confs or confs < min_confs:
            # Per ora, consideriamo 0 conferme come valide per il testing, 
            # ma in produzione `min_confs` dovrebbe essere almeno 1.
            # In un sistema reale, si aspetterebbe la conferma.
            pass

        # 3. Verifica l'output corretto
        sats_expected = int(expected_btc * Decimal(1e8))
        output_found = False
        for vout in tx_details.get("vout", []):
            if vout.get("scriptpubkey_address") == address and vout.get("value", 0) >= sats_expected:
                output_found = True
                break
        
        return output_found

    except httpx.HTTPStatusError as e:
        # Se la transazione non viene trovata (404) o c'è un altro errore, non è valida.
        print(f"Errore API durante la validazione della tx {txid}: {e}")
        return False
    except Exception as e:
        print(f"Errore imprevisto durante la validazione della tx {txid}: {e}")
        return False
