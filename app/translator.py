import gettext
import os

from app.models import User

LANGUAGES = ["en", "it", "es", "fr", "ru", "de"]
DEFAULT_LOCALE = "en"

# Use an absolute path for the locale directory
localedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")


def get_translation(user: User):
    lang = user.lang if user.lang in LANGUAGES else DEFAULT_LOCALE
    t = gettext.translation("messages", localedir=localedir, languages=[lang], fallback=True)
    return t.gettext
