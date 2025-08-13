from i18n import t

def test_start_welcome():
    assert t("start.welcome") == "Welcome to Escrow Gigs Bot 👋\nChoose an action:"

def test_usage_release():
    assert t("usage.release") == "Use: /release <order_id>"
