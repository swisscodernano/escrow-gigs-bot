import gettext
import os
import logging

from app.models import User

LANGUAGES = ["en", "it", "es", "fr", "ru", "de"]
DEFAULT_LOCALE = "en"

# Use an absolute path for the locale directory
localedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")
logging.basicConfig(level=logging.INFO)
logging.info(f"Translator localedir: {localedir}")


def get_translation(user: User):
    lang = user.lang if user.lang in LANGUAGES else DEFAULT_LOCALE
    logging.info(f"User lang: {lang}")
    try:
        t = gettext.translation("messages", localedir=localedir, languages=[lang], fallback=True)
        logging.info("Translation loaded successfully")
        return t.gettext
    except Exception as e:
        logging.error(f"Error loading translation: {e}")
        return lambda s: s
