import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from app.config import settings

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello World')

def main() -> None:
    application = Application.builder().token(settings.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == '__main__':
    main()
