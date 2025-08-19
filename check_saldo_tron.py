#!/usr/bin/env python3
import os, sys, requests

ADDR = os.getenv("TRON_USDT_ADDR") or (sys.argv[1] if len(sys.argv) > 1 else None)
KEY  = os.getenv("TRONGRID_API_KEY")
USDT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # contratto USDT TRC20

if not ADDR or not KEY:
    print("Setta TRON_USDT_ADDR e TRONGRID_API_KEY nel .env o passa l'indirizzo come argomento.")
    sys.exit(1)

h = {"TRON-PRO-API-KEY": KEY}
r = requests.get(f"https://api.trongrid.io/v1/accounts/{ADDR}", headers=h, timeout=20)
r.raise_for_status()
j = r.json()

if not j.get("data"):
    print("Account non attivato o non trovato su TronGrid (nessuna transazione).")
    sys.exit(0)

acct = j["data"][0]
trx_sun = int(acct.get("balance", 0))
print(f"TRX: {trx_sun/1_000_000:.6f}")

usdt_list = acct.get("trc20") or []
usdt_raw = "0"
decimals = 6
for t in usdt_list:
    ca = t.get("contract_address") or (t.get("token_info") or {}).get("address")
    if ca == USDT:
        usdt_raw = str(t.get("balance") or "0")
        decimals = int((t.get("token_info") or {}).get("decimals") or t.get("decimals") or 6)
        break

usdt = (int(usdt_raw) / (10 ** decimals)) if usdt_raw.isdigit() else 0.0
print(f"USDT: {usdt:.6f}")
