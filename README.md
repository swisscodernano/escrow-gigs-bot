# Telegram Gigs Escrow Bot (MVP)

**Setup in 3 passi:**

1.  **Configurazione Iniziale**
    ```bash
    cp .env.example .env
    # Modifica .env e inserisci almeno BOT_TOKEN e ADMIN_USER_ID
    ```

2.  **Creazione del Portafoglio Bitcoin**
    Esegui lo script di setup interattivo per creare il wallet sicuro.
    ```bash
    python setup_wallet.py
    ```
    Lo script ti guiderà nella creazione di un file portafoglio protetto da password.
    - **Salva la seed phrase** in un luogo sicuro e offline.
    - Copia l'output (le variabili `BTC_...`) nel tuo file `.env`.

3.  **Avvio**
    ```bash
    ./deploy.sh
    ```
Comandi bot: /newgig, /listings, /mygigs, /buy <id>, /confirm_tx <id> <txid>, /release <id>, /dispute <id> <motivo>, /orders

**Nota:** depositi/transfer on-chain sono **stub** in MVP. Per produzione attiva gli adapter reali (TRON/TON/BTC).
