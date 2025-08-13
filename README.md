# Telegram Gigs Escrow Bot (MVP)

**One-click:**
```bash
cp .env.example .env
# Edit .env -> BOT_TOKEN, ADMIN_USER_ID
./deploy.sh
```
Comandi bot: /newgig, /listings, /mygigs, /buy <id>, /confirm_tx <id> <txid>, /release <id>, /dispute <id> <motivo>, /orders

**Nota:** depositi/transfer on-chain sono **stub** in MVP. Per produzione attiva gli adapter reali (TRON/TON/BTC).
