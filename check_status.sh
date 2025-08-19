#!/usr/bin/env bash
set -euo pipefail

section(){ echo -e "\n\033[1;36m==> $*\033[0m"; }
ok(){ echo "✅ $*"; }
warn(){ echo "⚠️  $*"; }
err(){ echo "❌ $*"; }

section "Docker"
docker compose ps

section "App health (via Caddy HTTPS) /health"
curl -sS -I https://escrow.swisscoordinator.app/health || true

section "App logs (ultimi 60 righe)"
docker compose logs --tail=60 app || true

section "DB & Redis quick ping"
docker compose exec -T app sh -lc 'python - <<PY
import os, sys
from sqlalchemy import create_engine, text
import redis
url = os.getenv("DATABASE_URL","postgresql+psycopg2://escrow@db:5432/escrowdb")
try:
    e=create_engine(url); 
    with e.connect() as c: c.execute(text("SELECT 1"))
    print("DB OK")
except Exception as ex: 
    print("DB FAIL:", ex)
try:
    r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), db=0)
    r.ping()
    print("Redis OK")
except Exception as ex:
    print("Redis FAIL:", ex)
PY' || true

section "Telegram bot.getMe"
docker compose exec -T app sh -lc 'python - <<PY
import os, asyncio
from telegram import Bot
tok=os.getenv("BOT_TOKEN")
async def run():
    try:
        u=await Bot(tok).get_me()
        print("BOT OK -> @"+u.username)
    except Exception as e:
        print("BOT FAIL:", e)
asyncio.run(run())
PY' || true

section "Wallets audit (env & capacità)"
docker compose exec -T app sh -lc 'python - <<PY
import os
def mask(s): 
    return s if not s or len(s)<=10 else s[:6]+"..."+s[-4:]
env = {k:os.getenv(k,"") for k in [
  "BTC_MODE","BTC_NETWORK","ESPLORA_URL","BTC_XPUB","BTC_XPRV",
  "TRON_USDT_ADDR","TRON_USDT_PRIV","TRONGRID_API_KEY",
  "USD_WALLET_ID","USD_API_KEY"
]}
print("Environment:")
for k,v in env.items(): 
    print(f"  {k}=", mask(v) if v else "(unset)")
# Prova derivazione BTC (solo se XPUB/XPRV)
if env["BTC_XPUB"] or env["BTC_XPRV"]:
    try:
        from app.payment import btc_onchain
        addr, path = btc_onchain.derive_address(1)
        print("BTC derive OK:", addr, path)
    except Exception as e:
        print("BTC derive FAIL:", e)
else:
    print("BTC derive SKIP: no XPUB/XPRV")
PY' || true

section "Patch sanity"
docker compose exec -T app sh -lc '
grep -R "expire_on_commit=False" /app/app || echo "MANCANTE: expire_on_commit=False"
grep -n "reply_text(" /app/app/telegram_bot.py | head -n1 | sed "s/.*/OK: reply_text trovato/"
grep -n "send_message(" /app/app/telegram_bot.py | head -n1 | sed "s/.*/OK: send_message trovato/"
' || true

echo
ok "Check completato."

echo
echo "==> TRON balances (TRX & USDT TRC20)"
ADDR=$(grep -E '^TRON_USDT_ADDR=' .env | cut -d= -f2-)
KEY=$(grep -E '^TRONGRID_API_KEY=' .env | cut -d= -f2-)
if [ -n "$ADDR" ] && [ -n "$KEY" ]; then
  if [ -x ./check_saldo_tron.py ]; then
    TRONGRID_API_KEY="$KEY" ./check_saldo_tron.py "$ADDR" | sed 's/^/  /'
  else
    echo "  check_saldo_tron.py non trovato (usa: python3 -m pip install requests; vedi repo)"
  fi
else
  echo "  TRONGRID_API_KEY o TRON_USDT_ADDR non impostati nel .env"
fi
