from telegram.ext import Application, ApplicationBuilder

from app.bot.handlers import (lang_command_handler, lang_menu_callback_handler,
                              lang_set_callback_handler,
                              not_implemented_handler, start_handler)
from app.core.config import settings


def create_bot_app() -> Application:
    """
    Creates and configures the Telegram bot application.
    """
    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # Register handlers
    application.add_handler(start_handler)
    application.add_handler(lang_command_handler)
    application.add_handler(lang_menu_callback_handler)
    application.add_handler(lang_set_callback_handler)
    application.add_handler(not_implemented_handler)

    return application


bot_app = create_bot_app()
