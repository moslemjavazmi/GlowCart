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
    """The gateway returned an invalid response."""


class ZarinpalRejectedError(ZarinpalGatewayError):
    """The gateway explicitly rejected the request."""


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

    # -----------------------------------------------------
    # Amount conversion
    # -----------------------------------------------------

    def _convert_amount(self, amount: Decimal) -> int:

        """
        Database amount is assumed to be in Toman.

        IRT = Toman
        IRR = Rial
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

    # -----------------------------------------------------
    # HTTP request
    # -----------------------------------------------------


    def _post(
        self,
        endpoint: str,
        payload: dict,
        *,
        reject_client_errors: bool = False,
    ) -> dict:
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
        except requests.RequestException as exc:
            raise ZarinpalTransportError(
                f"Zarinpal connection error: "
                f"{type(exc).__name__}: {str(exc)[:500]}"
            ) from exc

        try:
            response_data = response.json()
        except ValueError as exc:
            raise ZarinpalResponseError(
                f"Invalid JSON response from Zarinpal. "
                f"HTTP status: {response.status_code}"
            ) from exc

        if not isinstance(response_data, dict):
            raise ZarinpalResponseError(
                "Unexpected response structure from Zarinpal."
            )

        if 400 <= response.status_code < 500:
            errors = response_data.get("errors")

            if isinstance(errors, dict):
                if reject_client_errors:
                    raise ZarinpalRejectedError(
                        f"Zarinpal rejected request: "
                        f"{errors.get('message', 'Unknown error')} "
                        f"(code: {errors.get('code', 'unknown')})"
                    )

                # Verify errors are not automatically treated as
                # definitive payment failures.
                return response_data

            raise ZarinpalResponseError(
                f"Zarinpal client error. "
                f"HTTP status: {response.status_code}"
            )

        if response.status_code >= 500:
            raise ZarinpalTransportError(
                f"Zarinpal server error. "
                f"HTTP status: {response.status_code}"
            )

        return response_data
    # -----------------------------------------------------
    # Create payment
    # -----------------------------------------------------

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

        response_data = self._post(
            "request",
            payload,
        )

        data = response_data.get("data")
        errors = response_data.get("errors")

        if errors:

            if not isinstance(errors, dict):
                raise ZarinpalResponseError(
                    "Invalid error structure from Zarinpal."
                )

            raise ZarinpalRejectedError(
                f"Zarinpal rejected request: "
                f"{errors.get('message', 'Unknown error')}"
            )

        if not isinstance(data, dict):
            raise ZarinpalResponseError(
                "Invalid data structure in Zarinpal response."
            )

        try:
            code = int(data.get("code"))

        except (TypeError, ValueError) as exc:
            raise ZarinpalResponseError(
                "Invalid Zarinpal response code."
            ) from exc

        if code != 100:

            # فقط کدهای خطای شناخته‌شده و قطعی
            # باید به عنوان Rejected شناخته شوند.

            if code < 0:
                raise ZarinpalRejectedError(
                    f"Zarinpal request rejected with code: {code}"
                )

            # کد ناشناخته را نباید رد قطعی فرض کنیم.
            raise ZarinpalResponseError(
                f"Unknown Zarinpal request code: {code}"
            )

        authority = data.get("authority")

        if not authority:
            raise ZarinpalResponseError(
                "Zarinpal did not return an authority."
            )

        return {
            "authority": str(authority),
            "payment_url": f"{self.payment_base}/{authority}",
            "raw_response": response_data,
        }

    # -----------------------------------------------------
    # Verify payment
    # -----------------------------------------------------

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

        response_data = self._post(
            "verify",
            payload,
        )

        data = response_data.get("data")
        errors = response_data.get("errors")

        if errors:

            return {
                "success": False,
                "reference": None,
                "definitive_failure": False,
                "raw_response": response_data,
            }

        if not isinstance(data, dict):
            raise ZarinpalResponseError(
                "Invalid verification response structure."
            )

        try:
            code = int(data.get("code"))

        except (TypeError, ValueError) as exc:
            raise ZarinpalResponseError(
                "Invalid Zarinpal verification code."
            ) from exc

        # 100: payment verified
        # 101: payment already verified

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

        # Unknown codes remain unresolved.
        # Do not mark a payment as failed unless the response
        # is explicitly mapped to a definitive failure code.

        return {
            "success": False,
            "reference": None,
            "definitive_failure": False,
            "raw_response": response_data,
        }