
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings

from payments.gateways.base import PaymentGateway


class ZarinpalGatewayError(Exception):
    """Base exception for Zarinpal errors."""


class ZarinpalTransportError(ZarinpalGatewayError):
    """The request outcome could not be determined."""


class ZarinpalResponseError(ZarinpalGatewayError):
    """The gateway returned an invalid or unexpected response."""


class ZarinpalRejectedError(ZarinpalGatewayError):
    """The gateway explicitly rejected a payment request."""


class ZarinpalGateway(PaymentGateway):

    def __init__(self):
        self.merchant_id = settings.ZARINPAL_MERCHANT_ID
        self.sandbox = settings.ZARINPAL_SANDBOX
        self.currency = settings.ZARINPAL_CURRENCY

        if not self.merchant_id:
            raise ZarinpalGatewayError(
                "Zarinpal merchant ID is not configured."
            )

        if self.sandbox:
            self.api_base = (
                "https://sandbox.zarinpal.com/pg/v4/payment"
            )
            self.payment_base = (
                "https://sandbox.zarinpal.com/pg/StartPay"
            )
        else:
            self.api_base = (
                "https://payment.zarinpal.com/pg/v4/payment"
            )
            self.payment_base = (
                "https://payment.zarinpal.com/pg/StartPay"
            )

    def _convert_amount(self, amount: Decimal) -> int:
        """
        Database amount is assumed to be in Toman.

        IRT: Toman
        IRR: Rial (10 Toman)
        """

        amount = Decimal(amount)

        if self.currency == "IRT":
            converted = amount
        elif self.currency == "IRR":
            converted = amount * Decimal("10")
        else:
            raise ZarinpalGatewayError(
                "Unsupported Zarinpal currency."
            )

        converted = converted.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )

        if converted <= 0:
            raise ZarinpalGatewayError(
                "Payment amount must be positive."
            )

        return int(converted)

    def _post(self, endpoint: str, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.api_base}/{endpoint}.json",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=(5, 20),
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise ZarinpalTransportError(
                "Could not determine the result of the Zarinpal request."
            ) from exc

        try:
            response_data = response.json()
        except ValueError as exc:
            raise ZarinpalResponseError(
                "Invalid JSON response from Zarinpal."
            ) from exc

        if not isinstance(response_data, dict):
            raise ZarinpalResponseError(
                "Unexpected response structure from Zarinpal."
            )

        return response_data

    def create_payment(
        self,
        *,
        amount: Decimal,
        callback_url: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:

        payload = {
            "merchant_id": self.merchant_id,
            "amount": self._convert_amount(amount),
            "callback_url": callback_url,
            "description": description[:500],
            "currency": self.currency,
            "metadata": metadata or {},
        }

        response_data = self._post("request", payload)

        data = response_data.get("data") or {}
        errors = response_data.get("errors") or {}

        if errors:
            raise ZarinpalRejectedError(
                f"Zarinpal rejected request: "
                f"{errors.get('message', 'Unknown error')}"
            )

        if data.get("code") != 100:
            raise ZarinpalRejectedError(
                f"Zarinpal request rejected with code: "
                f"{data.get('code')}"
            )

        authority = data.get("authority")

        if not authority:
            raise ZarinpalResponseError(
                "Zarinpal did not return an authority."
            )

        return {
            "authority": authority,
            "payment_url": f"{self.payment_base}/{authority}",
            "raw_response": response_data,
        }

    def verify_payment(
        self,
        *,
        authority: str,
        amount: Decimal,
    ) -> dict:

        payload = {
            "merchant_id": self.merchant_id,
            "amount": self._convert_amount(amount),
            "authority": authority,
        }

        response_data = self._post("verify", payload)

        data = response_data.get("data") or {}
        errors = response_data.get("errors") or {}

        # An error response is not automatically proof
        # that the customer was not charged.
        if errors:
            return {
                "success": False,
                "reference": None,
                "definitive_failure": False,
                "raw_response": response_data,
            }

        code = data.get("code")

        # 100: payment verified
        # 101: payment was already verified
        if code in (100, 101):
            reference = data.get("ref_id")

            if reference is None:
                raise ZarinpalResponseError(
                    "Successful verification did not include ref_id."
                )

            return {
                "success": True,
                "reference": str(reference),
                "definitive_failure": False,
                "raw_response": response_data,
            }

        # Until individual negative codes are mapped and
        # confirmed from the gateway documentation, keep
        # the result unresolved.
        return {
            "success": False,
            "reference": None,
            "definitive_failure": False,
            "raw_response": response_data,
        }
