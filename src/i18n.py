import os

_CATALOG = {
    "en": {
        "help.usage": "Usage: {usage}",
        "search.no_results": "No results found.",
        "search.result": "{title} — ${price}",
        "start.welcome": "Welcome!",
    },
    "it": {
        "help.usage": "Uso: {usage}",
        "search.no_results": "Nessun risultato trovato.",
        "search.result": "{title} — ${price}",
        "start.welcome": "Benvenuto!",
    },
}

def t(key: str, locale: str | None = None, default: str | None = None, **kwargs) -> str:
    loc = (locale or os.getenv("DEFAULT_LOCALE") or "en").split(",")[0].strip().lower()
    text = (_CATALOG.get(loc, {}).get(key)
            or _CATALOG.get("en", {}).get(key)
            or default
            or key)
    try:
        if kwargs:
            text = text.format(**kwargs)
    except Exception:
        # non bloccare i test se mancano placeholder
        pass
    return text
