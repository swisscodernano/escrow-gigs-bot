import gettext
import os
from typing import Callable, Dict, Optional, Union

# The absolute path to the directory containing language folders (e.g., 'en', 'it')
localedir = os.path.abspath(os.path.dirname(__file__))

# A cache for translation objects
translations: Dict[
    str, Union[gettext.GNUTranslations, gettext.NullTranslations]
] = {}


def get_translation_for_lang(
    lang: str,
) -> Union[gettext.GNUTranslations, gettext.NullTranslations]:
    """
    Get a translation object for a specific language.
    Caches the result to avoid reloading from disk.
    """
    if lang not in translations:
        try:
            translations[lang] = gettext.translation(
                "messages", localedir=localedir, languages=[lang]
            )
        except FileNotFoundError:
            # Fallback to a NullTranslations object if the .mo file is missing
            if "en" not in translations:
                translations["en"] = gettext.translation(
                    "messages", localedir=localedir, languages=["en"], fallback=True
                )
            return translations["en"]
    return translations[lang]


def get_translator(lang: Optional[str]) -> Callable[[str], str]:
    """
    Returns a translator function for the given language.
    Defaults to English if the language is not supported or not found.
    """
    lang = lang or "en"
    translation_obj = get_translation_for_lang(lang)
    return translation_obj.gettext
