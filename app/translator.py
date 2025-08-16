import gettext

from app.models import User

LANGUAGES = ["en", "it", "es", "fr", "ru", "de"]
DEFAULT_LOCALE = "en"


def get_translation(user: User):
    lang = user.lang if user.lang in LANGUAGES else DEFAULT_LOCALE
    return gettext.translation(
        "messages", localedir="app/i18n", languages=[lang]
    ).gettext
