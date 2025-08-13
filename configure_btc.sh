#!/usr/bin/env bash
set -euo pipefail

read -rp "Rete BTC (mainnet/testnet) [testnet]: " NET
NET=${NET:-testnet}
if [[ "$NET" != "mainnet" && "$NET" != "testnet" ]]; then echo "Valore non valido"; exit 1; fi

read -rp "XPUB ($NET, BIP84 bech32): " XPUB
if [[ -z "$XPUB" ]]; then echo "XPUB obbligatorio (consiglio XPUB watch-only)"; exit 1; fi

if [[ "$NET" == "mainnet" ]]; then
  ESPLORA="https://blockstream.info/api"
else
  ESPLORA="https://blockstream.info/testnet/api"
fi

# Scrive su .env (mantiene XPRV vuoto per sicurezza)
grep -q '^BTC_MODE=' .env && sed -i 's|^BTC_MODE=.*|BTC_MODE=ONCHAIN|' .env || echo 'BTC_MODE=ONCHAIN' >> .env
grep -q '^BTC_NETWORK=' .env && sed -i "s|^BTC_NETWORK=.*|BTC_NETWORK=$NET|" .env || echo "BTC_NETWORK=$NET" >> .env
grep -q '^ESPLORA_URL=' .env && sed -i "s|^ESPLORA_URL=.*|ESPLORA_URL=$ESPLORA|" .env || echo "ESPLORA_URL=$ESPLORA" >> .env
grep -q '^BTC_XPUB=' .env && sed -i "s|^BTC_XPUB=.*|BTC_XPUB=$XPUB|" .env || echo "BTC_XPUB=$XPUB" >> .env
grep -q '^BTC_XPRV=' .env && sed -i "s|^BTC_XPRV=.*|BTC_XPRV=|" .env || echo "BTC_XPRV=" >> .env

echo "→ Rebuild & up…"
docker compose up -d --build

echo "→ Derivo indirizzo per order #1…"
APP_CONT=$(docker ps -qf "name=escrow-gigs-bot-app-1")
docker exec "$APP_CONT" python - <<'PY'
import os
from app.payment import btc_onchain
addr, path = btc_onchain.derive_address(1)
print(f"BTC derive OK: {addr} | {path} | network={os.getenv('BTC_NETWORK')}")
PY

echo "→ Health:"
curl -s https://escrow.swisscoordinator.app/health || true
echo
echo "✅ BTC configurato (watch-only)."
echo "Prova nel bot: /newgigbtc Logo premium | 0.001 | 48h → /listings → /buy <id>"
echo "Paga all’indirizzo mostrato, poi /confirm_tx <order_id> <txid>"
