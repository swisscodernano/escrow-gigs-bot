# Minimal test env; make sure the Telegram bot doesn't start during tests
import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def _env():
    os.environ.setdefault("TELEGRAM_TOKEN", "")
    os.environ.setdefault("DEFAULT_LOCALE", "en")
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/app")
    yield
