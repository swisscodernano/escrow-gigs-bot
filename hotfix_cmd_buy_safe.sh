#!/bin/bash
set -euo pipefail
APP=app
APP_PATH=/app/app
FILE=telegram_bot.py
TS=$(date +%Y%m%d-%H%M%S)

echo "==> Trovo ultimo backup valido..."
LAST_BAK=$(ls -t _backups/telegram_bot.py.*.bak 2>/dev/null | head -n1 || true)
if [ -z "${LAST_BAK}" ]; then
  echo "Nessun backup trovato: procedo con file attuale dal container."
  docker compose cp "${APP}:${APP_PATH}/${FILE}" "./${FILE}.work"
else
  echo "Uso backup: ${LAST_BAK}"
  cp "${LAST_BAK}" "./${FILE}.work"
fi

echo "==> Applico patch non intrusiva (helper + replace format)..."
python3 - "$FILE.work" <<'PY'
import re, sys, io, os

p=sys.argv[1]
s=open(p,'r',encoding='utf-8').read()

# 1) Aggiungi helper se manca
if "_HOTFIX_CMD_BUY_VALUES" not in s:
    helper = '''

# ===== HOTFIX: detached values helper =====
def _hotfix_values(g, o):  # _HOTFIX_CMD_BUY_VALUES
    try:
        try:
            from app.db import SessionLocal
        except Exception:
            from db import SessionLocal
        with SessionLocal() as _s:
            g2 = _s.merge(g, load=True)
            o2 = _s.merge(o, load=True)
            return {
                "amt": getattr(g2, "price_usd", None),
                "asset": getattr(g2, "currency", None),
                "addr": getattr(o2, "deposit_address", None),
                "oid": getattr(o2, "id", None),
            }
    except Exception:
        # Fallback: usa gli oggetti originali (se ancora validi)
        return {
            "amt": getattr(g, "price_usd", None),
            "asset": getattr(g, "currency", None),
            "addr": getattr(o, "deposit_address", None),
            "oid": getattr(o, "id", None),
        }
# ===== END HOTFIX =====
'''
    # append in fondo al file
    if not s.endswith("\n"):
        s += "\n"
    s += helper

# 2) Rimpiazza la format(...) specifica con format(**_hotfix_values(g,o))
pattern = r"""\.format\(\s*amt\s*=\s*g\.price_usd\s*,\s*asset\s*=\s*g\.currency\s*,\s*addr\s*=\s*o\.deposit_address\s*,\s*oid\s*=\s*o\.id\s*\)"""
s2 = re.sub(pattern, r".format(**_hotfix_values(g,o))", s)

open(p,'w',encoding='utf-8').write(s2)
PY

echo "==> Copio nel container e riavvio..."
docker compose cp "./${FILE}.work" "${APP}:${APP_PATH}/${FILE}"
docker compose restart "${APP}"

echo "==> Log (CTRL+C per uscire)"
docker compose logs -f --tail=200 "${APP}"
