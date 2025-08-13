import os

_CATALOG = {
    "en": {
        "help.usage": "Usage: {usage}",
        "help.text": (
            "Commands:\n"
            "/newgig — Create a gig\n"
            "/mygigs — Your gigs\n"
            "/search — Find gigs\n"
            "/wallet — Balance & deposits\n"
            "/buy <gig_id> — Start an order\n"
            "/release <order_id> — Release escrow\n"
            "/help — How it works"
        ),
        "search.no_results": "No results found.",
        "search.result": "{title} — ${price}",
        "start.welcome": "Welcome to Escrow Gigs Bot 👋\nChoose an action:",
        "usage.release": "Use: /release <order_id>",
    },
    "it": {
        "help.usage": "Uso: {usage}",
        "help.text": (
            "Comandi:\n"
            "/newgig — Crea un annuncio\n"
            "/mygigs — I tuoi annunci\n"
            "/search — Cerca annunci\n"
            "/wallet — Saldo e depositi\n"
            "/buy <gig_id> — Avvia un ordine\n"
            "/release <order_id> — Rilascia l'escrow\n"
            "/help — Come funziona"
        ),
        "search.no_results": "Nessun risultato trovato.",
        "search.result": "{title} — ${price}",
        "start.welcome": "Benvenuto!",
        "usage.release": "Usa: /release <order_id>",
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
        pass
    return text
