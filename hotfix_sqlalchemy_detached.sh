#!/bin/bash
set -euo pipefail
TS=$(date +%Y%m%d-%H%M%S)
B="_backups/sqlalchemy_$TS"
mkdir -p "$B"

# Patcha tutti i file .py che usano sessionmaker(...): aggiunge expire_on_commit=False se manca
mapfile -t FILES < <(grep -RIl --include='*.py' 'sessionmaker(' . || true)
for f in "${FILES[@]}"; do
  cp "$f" "$B"/
  python3 - "$f" <<'PY'
import sys, re, io
p=sys.argv[1]
s=open(p,'r',encoding='utf-8').read()
def repl(m):
    inside=m.group(1)
    if 'expire_on_commit' in inside:
        return m.group(0)
    return 'sessionmaker(expire_on_commit=False, '+inside
s2=re.sub(r'sessionmaker\(\s*([^)]*)', repl, s, flags=re.MULTILINE)
if s2!=s:
    open(p,'w',encoding='utf-8').write(s2)
PY
done

echo "==> Restart app"
docker compose restart app
echo "==> Logs (CTRL+C per uscire)"
docker compose logs -f --tail=200 app
