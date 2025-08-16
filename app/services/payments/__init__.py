from functools import lru_cache

from app.config import settings
from app.services.payments.base import BaseProvider
from app.services.payments.mock import MockProvider


@lru_cache()
def get_provider() -> BaseProvider:
    provider = settings.PAYMENTS_PROVIDER.lower()
    if provider == "mock":
        return MockProvider()
    raise ValueError(f"unknown payments provider: {provider}")
