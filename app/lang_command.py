from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from app.db_utils import db_session_decorator
from app.models import User
from app.translator import LANGUAGES, get_translation


@db_session_decorator
async def cmd_lang(
    update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session = None
):
    user = db.query(User).filter(User.tg_id == str(update.effective_user.id)).first()
    _ = get_translation(user)

    args = (update.message.text or "").split()
    if len(args) < 2 or args[1] not in LANGUAGES:
        await update.message.reply_text(
            _("Usage: /lang <{languages}>").format(languages="|".join(LANGUAGES))
        )
        return

    if user:
        user.lang = args[1]
        db.commit()
        _ = get_translation(user)
        await update.message.reply_text(
            _("Language set to: {lang}").format(lang=user.lang)
        )
