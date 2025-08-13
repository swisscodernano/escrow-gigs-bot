#!/bin/bash
set -euo pipefail
APP_SERVICE=app
APP_PATH=/app/app
BOT_FILE=telegram_bot.py
TS=$(date +%Y%m%d-%H%M%S)

echo "==> Backup dal container"
mkdir -p _backups
docker compose cp "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}" "_backups/${BOT_FILE}.${TS}.bak"

echo "==> Estrazione locale"
docker compose cp "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}" "./${BOT_FILE}.work"

echo "==> Patch: inserisco merge(g/o) prima del .format(amt=g.price_usd..."
python3 - "$BOT_FILE.work" <<'PY'
import sys, re
p=sys.argv[1]
s=open(p,'r',encoding='utf-8').read()

# Inseriamo il blocco solo una volta, immediatamente prima dell'uso noto del format
needle = ".format(amt=g.price_usd, asset=g.currency, addr=o.deposit_address, oid=o.id)"
if needle in s and "## HOTFIX_MERGE_GO" not in s:
    ins = """\
    ## HOTFIX_MERGE_GO: ensure g/o are attached to a session
    try:
        try:
            from app.db import SessionLocal
        except Exception:
            from db import SessionLocal
        with SessionLocal() as _sfix:
            g = _sfix.merge(g, load=True)
            o = _sfix.merge(o, load=True)
    except Exception:
        pass
"""
    s = s.replace(needle, needle)  # keep marker present
    # Trova la riga che contiene il needle e inserisce il blocco subito PRIMA
    out=[]
    for line in s.splitlines(True):
        if needle in line and "HOTFIX_MERGE_GO" not in "".join(out):
            out.append(ins)
        out.append(line)
    s="".join(out)

open(p,'w',encoding='utf-8').write(s)
PY

echo "==> Copio nel container"
docker compose cp "./${BOT_FILE}.work" "${APP_SERVICE}:${APP_PATH}/${BOT_FILE}"

echo "==> Restart app"
docker compose restart app

echo "==> Log (CTRL+C per uscire)"
docker compose logs -f --tail=200 app
