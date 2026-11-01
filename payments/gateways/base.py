
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
        ایجاد درخواست پرداخت.

        خروجی استاندارد:
        {
            "authority": "...",
            "payment_url": "..."
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
        استعلام و تأیید پرداخت از سرور درگاه.

        خروجی استاندارد:
        {
            "success": True,
            "reference": "...",
            "raw_response": {}
        }
        """
        raise NotImplementedError
