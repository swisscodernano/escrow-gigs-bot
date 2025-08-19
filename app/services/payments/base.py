from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict


class BaseProvider(ABC):
    @abstractmethod
    def create_checkout(
        self, user_id: int, amount: Decimal, currency: str
    ) -> Dict[str, Any]:
        """Start a checkout session and return provider-specific data."""

    @abstractmethod
    def verify_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate webhook payload and return normalized data."""
