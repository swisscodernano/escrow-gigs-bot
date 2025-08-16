# Telegram Gigs Escrow Bot (MVP)

**One-click:**
```bash
cp .env.example .env
# Edit .env -> BOT_TOKEN, ADMIN_USER_ID
./deploy.sh
Code Quality
This project uses black, isort, flake8, and mypy to ensure code quality.

To install the development dependencies, run:

pip install -r requirements-dev.txt
To run the tools, use the following commands:

# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with flake8
flake8 src/ tests/

# Run static type checking with mypy
mypy src/
Comandi bot: /newgig, /listings, /mygigs, /buy

Nota: depositi/transfer on-chain sono stub in MVP. Per produzione attiva gli adapter reali (TRON/TON/BTC).