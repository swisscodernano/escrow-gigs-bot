import asyncio
import os
import logging
from app.telegram_bot import (
    cmd_start,
    cmd_help,
    cmd_newgig,
    cmd_mygigs,
    cmd_buy,
    cmd_release,
    # Assuming a cmd_cancel might exist or be needed
)
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler

# Use the logger configured in telegram_bot
log = logging.getLogger(__name__)

async def run_bot_background():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        log.warning("TELEGRAM_TOKEN not set: bot NOT started.")
        return

    log.info("Building bot application...")
    app = ApplicationBuilder().token(token).build()

    # Define commands and their handlers directly
    commands = {
        "start": ("👋 Start the bot", cmd_start),
        "help": ("❓ Show help", cmd_help),
        "newgig": ("➕ Create a new gig", cmd_newgig),
        "mygigs": ("🧾 See your gigs", cmd_mygigs),
        "buy": ("🛒 Buy a gig", cmd_buy),
        "release": ("🔓 Release funds", cmd_release),
    }

    bot_commands = [BotCommand(cmd, desc) for cmd, (desc, _) in commands.items()]
    for cmd, (_, handler) in commands.items():
        app.add_handler(CommandHandler(cmd, handler))
    
    log.info(f"Added {len(commands)} command handlers.")

    await app.initialize()
    await app.start()
    
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.bot.set_my_commands(bot_commands)
        log.info("Bot commands set.")
        
        await app.updater.start_polling()
        log.info("Telegram bot is running and polling for updates.")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        log.info("Bot operation was cancelled.")
    except Exception as e:
        log.critical(f"A critical error occurred in the bot's main loop: {e}", exc_info=True)
    finally:
        log.info("Shutting down bot...")
        try:
            if app.updater and app.updater.is_running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            log.info("Telegram bot stopped cleanly.")

if __name__ == "__main__":
    asyncio.run(run_bot_background())