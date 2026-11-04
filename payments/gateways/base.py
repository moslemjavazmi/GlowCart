
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class PaymentGateway(ABC):

    @abstractmethod
    def create_payment(
        self,
        *,
        amount: Decimal,
        callback_url: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Expected:
        {
            "authority": "...",
            "payment_url": "...",
            "raw_response": {}
        }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        *,
        authority: str,
        amount: Decimal,
    ) -> dict:
        """
        Expected:
        {
            "success": bool,
            "reference": str | None,
            "definitive_failure": bool,
            "raw_response": {}
        }
        """
        raise NotImplementedError
