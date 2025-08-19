#!/usr/bin/env bash
set -euo pipefail

# -------- helpers --------
mask() {
  local s="$1"
  local n=${#s}
  if [ $n -le 10 ]; then printf "%s" "$s"; else printf "%s...%s" "${s:0:6}" "${s: -4}"; fi
}
section() { echo -e "\n\033[1;36m==> $*\033[0m"; }
ok() { echo -e "✅ $*"; }
warn() { echo -e "⚠️  $*"; }
err() { echo -e "❌ $*"; }

# -------- sanity --------
test -f docker-compose.yml || { err "Lancialo nella cartella con docker-compose.yml"; exit 1; }
PROJECT_DIR="$(pwd)"

section "Docker & Compose"
docker -v || true
docker compose version || true
docker compose ps

# -------- env file --------
section ".env (variabili principali, segreti mascherati)"
if [ ! -f .env ]; then
  err ".env mancante"
else
  BOT_TOKEN="$(grep -E '^BOT_TOKEN=' .env | cut -d= -f2- || true)"
  ADMIN_ID="$(grep -E '^ADMIN_USER_ID=' .env | cut -d= -f2- || true)"
  DBN="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || true)"
  DBU="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || true)"
  BTC_MODE="$(grep -E '^BTC_MODE=' .env | cut -d= -f2- || true)"
  BTC_NET="$(grep -E '^BTC_NETWORK=' .env | cut -d= -f2- || true)"
  BTC_XPUB="$(grep -E '^BTC_XPUB=' .env | cut -d= -f2- || true)"
  BTC_XPRV="$(grep -E '^BTC_XPRV=' .env | cut -d= -f2- || true)"
  ESPLORA_URL="$(grep -E '^ESPLORA_URL=' .env | cut -d= -f2- || true)"
  TRON_KEY="$(grep -E '^TRON_PRIVATE_KEY=' .env | cut -d= -f2- || true)"
  TRON_API="$(grep -E '^TRON_API_KEY=' .env | cut -d= -f2- || true)"

  [ -n "${BOT_TOKEN:-}" ] && ok "BOT_TOKEN=$(mask "$BOT_TOKEN")" || warn "BOT_TOKEN assente"
  [ -n "${ADMIN_ID:-}" ] && ok "ADMIN_USER_ID=$ADMIN_ID" || warn "ADMIN_USER_ID assente"
  ok "POSTGRES_DB=${DBN:-}  POSTGRES_USER=${DBU:-}"
  [ -n "${BTC_MODE:-}" ] && ok "BTC_MODE=$BTC_MODE    BTC_NETWORK=${BTC_NET:-}" || warn "BTC non configurato"
  [ -n "${BTC_XPUB:-}" ] && ok "BTC_XPUB=$(mask "$BTC_XPUB")" || true
  [ -n "${BTC_XPRV:-}" ] && warn "BTC_XPRV presente (hot key) -> $(mask "$BTC_XPRV")" || true
  [ -n "${ESPLORA_URL:-}" ] && ok "ESPLORA_URL=$ESPLORA_URL" || true
  [ -n "${TRON_KEY:-}" ] && ok "TRON_PRIVATE_KEY=$(mask "$TRON_KEY")" || true
  [ -n "${TRON_API:-}" ] && ok "TRON_API_KEY=$(mask "$TRON_API")" || true
fi

# -------- app health (localhost) --------
section "API health (localhost:8000)"
set +e
HL=$(curl -sS -m 3 http://localhost:8000/health)
RC=$?
set -e
if [ $RC -eq 0 ]; then ok "Health: $HL"; else err "Health KO su 8000"; fi

# -------- Caddy & dominio --------
section "Caddy & TLS"
DOMAIN_FILE="caddy/Caddyfile"
if [ -f "$DOMAIN_FILE" ]; then
  DOMAIN=$(head -n1 "$DOMAIN_FILE" | awk '{print $1}')
  ok "Dominio: $DOMAIN"
  docker compose logs --tail=30 caddy || true
  set +e
  HDR=$(curl -sSI -m 5 "https://${DOMAIN}/health")
  RC=$?
  set -e
  if [ $RC -eq 0 ]; then
    ok "HTTPS /health risponde:\n$(echo "$HDR" | head -n 5)"
  else
    warn "HTTPS non raggiungibile ora (DNS/LE in corso?)"
  fi
else
  warn "Caddyfile non trovato"
fi

# -------- DB connectivity from app container --------
section "Postgres dal container app"
APP_CONT=$(docker ps -qf "name=escrow-gigs-bot-app-1")
if [ -n "$APP_CONT" ]; then
  set +e
  docker exec "$APP_CONT" python - <<'PY'
import os, sys
from sqlalchemy import create_engine, text
DB=f"postgresql://{os.getenv('POSTGRES_USER','escrow')}:{os.getenv('POSTGRES_PASSWORD','escrowpass')}@{os.getenv('POSTGRES_HOST','db')}:{os.getenv('POSTGRES_PORT','5432')}/{os.getenv('POSTGRES_DB','escrowdb')}"
try:
    eng=create_engine(DB,future=True)
    with eng.connect() as c:
        c.execute(text("select 1"))
    print("DB OK")
except Exception as e:
    print("DB FAIL:", e)
    sys.exit(1)
PY
  RC=$?
  set -e
  [ $RC -eq 0 ] && ok "DB connettività OK" || err "DB connettività FAIL"
else
  warn "Container app non trovato"
fi

# -------- Redis ping --------
section "Redis ping"
REDIS_CONT=$(docker ps -qf "name=escrow-gigs-bot-redis-1")
if [ -n "$REDIS_CONT" ]; then
  set +e
  docker exec "$REDIS_CONT" redis-cli -h localhost ping
  RC=$?
  set -e
  [ $RC -eq 0 ] && ok "Redis OK" || err "Redis FAIL"
else
  warn "Container redis non trovato"
fi

# -------- Telegram getMe (opzionale, non stampa token) --------
section "Telegram bot.getMe"
if [ -n "${BOT_TOKEN:-}" ]; then
  set +e
  OUT=$(curl -sS -m 5 "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
  RC=$?
  set -e
  if [ $RC -eq 0 ] && echo "$OUT" | grep -q '"ok":true'; then
    ok "getMe OK → $(echo "$OUT" | tr -d '\n' | sed 's/.*"username":"\([^"]*\)".*/@\1/' )"
  else
    err "getMe FAIL → $OUT"
  fi
else
  warn "BOT_TOKEN non impostato, skip"
fi

# -------- BTC check: derivazione indirizzo ordine #1 --------
section "BTC on-chain check"
if [ -n "${BTC_XPUB:-}" ] || [ -n "${BTC_XPRV:-}" ]; then
  if [ -f src/app/payment/btc_onchain.py ]; then
    set +e
    docker exec "$APP_CONT" python - <<'PY'
import os
from decimal import Decimal
os.environ['PYTHONUNBUFFERED']='1'
try:
    from app.payment import btc_onchain
    addr, path = btc_onchain.derive_address(1)
    print("BTC derive OK:", addr, "|", path, "| network:", os.getenv("BTC_NETWORK"))
except Exception as e:
    print("BTC derive FAIL:", e)
    raise SystemExit(1)
PY
    RC=$?
    set -e
    [ $RC -eq 0 ] && ok "BTC derivazione indirizzo OK" || err "BTC derivazione FAIL"
  else
    warn "btc_onchain.py non trovato (salta)"
  fi
else
  warn "BTC_XPUB/XPRV assenti → configura prima BTC"
fi

section "FINE"
