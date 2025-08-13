import os
import logging
import asyncio
import threading

# Rileva python-telegram-bot v20+ o v13
try:
    from telegram.ext import ApplicationBuilder, CommandHandler  # v20+
    PTB20 = True
except Exception:
    PTB20 = False
    from telegram.ext import Updater, CommandHandler  # v13

logging.basicConfig(level=logging.INFO)
_started = False

def cmd_help(update, context):
    update.message.reply_text("""\
Escrow Gigs Bot — Help

Comandi disponibili:
/start   - Avvia il bot
/help    - Mostra questo messaggio
/newgig  - Crea un nuovo annuncio
/mygigs  - Vedi i tuoi annunci
/release - Rilascia fondi in escrow
/cancel  - Annulla transazione
""")

# Per retrocompatibilità se altrove registri handler passando il dispatcher
def register_help_handler(dp):
    dp.add_handler(CommandHandler("help", cmd_help))

async def run_bot_background():
    """
    Avvia il bot Telegram in background. Coroutine idempotente.
    Se TELEGRAM_TOKEN manca, logga e ritorna senza far fallire l'app.
    """
    global _started
    if _started:
        return

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        logging.warning("TELEGRAM_TOKEN non impostato: bot NON avviato (l'app resta up).")
        return

    try:
        if PTB20:
            # v20: usiamo run_polling in thread per non bloccare l'event loop
            app = ApplicationBuilder().token(token).build()
            app.add_handler(CommandHandler("help", cmd_help))
            await asyncio.to_thread(app.run_polling)
            _started = True
            logging.info("Telegram bot avviato (ptb v20+).")
        else:
            # v13: start_polling rientra, idle blocca: eseguo entrambi in thread
            def _runner():
                updater = Updater(token=token, use_context=True)
                dp = updater.dispatcher
                dp.add_handler(CommandHandler("help", cmd_help))
                updater.start_polling()
                updater.idle()
            # Mantengo la coroutine viva finché il thread gira
            await asyncio.to_thread(_runner)
            _started = True
            logging.info("Telegram bot avviato (ptb v13).")
    except Exception as e:
        logging.exception("Errore avvio Telegram bot: %s", e)
        # Non rilancio: non impedisco l'avvio dell'app FastAPI
        return
