import gettext
from models import User

LANGUAGES = ['en', 'it']
DEFAULT_LOCALE = 'en'

def get_translation(user: User):
    lang = user.lang if user.lang in LANGUAGES else DEFAULT_LOCALE
    return gettext.translation('messages', localedir='app/i18n', languages=[lang]).gettext
