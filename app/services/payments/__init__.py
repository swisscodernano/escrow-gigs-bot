from functools import lru_cache
from config import settings
from app.mock import MockProvider
from app.base import BaseProvider

@lru_cache()
def get_provider() -> BaseProvider:
    provider = settings.PAYMENTS_PROVIDER.lower()
    if provider == "mock":
        return MockProvider()
    raise ValueError(f"unknown payments provider: {provider}")
