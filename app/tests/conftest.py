import os
import sys

import pytest

# Add the project root to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


@pytest.fixture(autouse=True, scope="session")
def _env():
    os.environ.setdefault("TELEGRAM_TOKEN", "")
    os.environ.setdefault("DEFAULT_LOCALE", "en")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    yield
