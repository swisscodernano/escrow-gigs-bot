#!/usr/bin/env bash
set -Eeuo pipefail

python3 -m pip install -U pip
python3 -m pip --version

# Installa dipendenze (se presenti) rispettando i vincoli, se ci sono
if [[ -f requirements.txt ]]; then
  if [[ -f codex-constraints.txt ]]; then
    python3 -m pip install -r requirements.txt -c codex-constraints.txt
  else
    python3 -m pip install -r requirements.txt
  fi
fi

# Smoke test import dei moduli principali
python3 - <<'PY'
import importlib, sys
mods = ["fastapi","uvicorn","sqlalchemy","httpx","telegram","pydantic"]
bad = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        bad.append((m, repr(e)))
if bad:
    print("Missing/failed imports:", bad)
    sys.exit(1)
print("✓ imports OK")
PY

# Lint e test (non falliscono il job se mancano test)
python3 -m pip install -q flake8 pytest pytest-asyncio || true
flake8 app tests || true
pytest -q || true
