from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from app.db.session import SessionLocal
from app.i18n.translator import get_translator
from app.services import user_service


async def start(update: Update, context: CallbackContext) -> None:
    """Sends a welcome message and the main menu."""
    user_data = update.effective_user
    if not user_data:
        return

    db = SessionLocal()
    user = user_service.get_or_create_user(db, str(user_data.id), user_data.username)
    db.close()

    _ = get_translator(user.lang)

    keyboard = [
        [InlineKeyboardButton(_("Create Gig"), callback_data="create_gig")],
        [InlineKeyboardButton(_("My Orders"), callback_data="my_orders")],
        [InlineKeyboardButton(_("Switch Language"), callback_data="lang_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = _("Hello, World!")
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)


async def lang_menu(update: Update, context: CallbackContext) -> None:
    """Shows the language selection menu, usable as a command or callback."""
    user_data = update.effective_user
    if not user_data:
        return

    db = SessionLocal()
    user = user_service.get_or_create_user(db, str(user_data.id), user_data.username)
    db.close()

    _ = get_translator(user.lang)

    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="set_lang_en")],
        [InlineKeyboardButton("Italiano 🇮🇹", callback_data="set_lang_it")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = _("Choose your language:")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def set_language(update: Update, context: CallbackContext) -> None:
    """Sets the user's language and returns to the main menu."""
    query = update.callback_query
    user_data = update.effective_user
    if not query or not user_data or not query.data:
        return

    await query.answer()

    lang_code = query.data.split("_")[-1]

    db = SessionLocal()
    user = user_service.get_or_create_user(db, str(user_data.id), user_data.username)
    user_service.update_user_lang(db, user.id, lang_code)
    db.close()

    _ = get_translator(lang_code)

    keyboard = [
        [InlineKeyboardButton(_("Create Gig"), callback_data="create_gig")],
        [InlineKeyboardButton(_("My Orders"), callback_data="my_orders")],
        [InlineKeyboardButton(_("Switch Language"), callback_data="lang_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=_("Language updated!"), reply_markup=reply_markup
    )


async def not_implemented(update: Update, context: CallbackContext) -> None:
    """Handles features that are not yet implemented."""
    query = update.callback_query
    if not query:
        return

    user_data = update.effective_user
    if not user_data:
        # Fallback for safety, though effective_user should exist for a query
        await query.answer(text="Cannot identify user.", show_alert=True)
        return

    db = SessionLocal()
    user = user_service.get_or_create_user(db, str(user_data.id), user_data.username)
    db.close()
    _ = get_translator(user.lang)

    await query.answer(text=_("This feature is not implemented yet."), show_alert=True)


start_handler = CommandHandler("start", start)
lang_command_handler = CommandHandler("lang", lang_menu)
lang_menu_callback_handler = CallbackQueryHandler(lang_menu, pattern="^lang_menu$")
lang_set_callback_handler = CallbackQueryHandler(set_language, pattern="^set_lang_")
not_implemented_handler = CallbackQueryHandler(
    not_implemented, pattern="^(create_gig|my_orders)$"
)
