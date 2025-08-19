import uuid
from decimal import Decimal
from typing import Any, Dict
from app.services.payments.base import BaseProvider

class MockProvider(BaseProvider):
    def create_checkout(self, user_id: int, amount: Decimal, currency: str) -> Dict[str, Any]:
        ext_ref = f"mock-{uuid.uuid4()}"
        return {"checkout_url": f"https://mock/checkout/{ext_ref}", "ext_ref": ext_ref}

    def verify_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # In tests we trust the payload
        return payload
