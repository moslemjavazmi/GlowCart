import logging
from uuid import UUID
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order

from payments.models import Payment
from payments.serializers import InitializePaymentSerializer

from payments.services.payment_service import (
    initialize_payment,
    verify_payment,
)


logger = logging.getLogger(__name__)


FINAL_PAYMENT_STATUSES = [
    Payment.Status.SUCCESS,
    Payment.Status.FAILED,
    Payment.Status.CANCELLED,
    Payment.Status.REVIEW_REQUIRED,
]


# =========================================================
# Initialize Payment
# =========================================================

class InitializePaymentView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = InitializePaymentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        result = initialize_payment(
            user=request.user,
            order_id=serializer.validated_data["order_id"],
            provider=serializer.validated_data["provider"],
            idempotency_key=serializer.validated_data["idempotency_key"],
        )

        payment = result["payment"]

        response_status = (
            status.HTTP_202_ACCEPTED
            if payment.status in [
                Payment.Status.INITIATED,
                Payment.Status.UNKNOWN,
            ]
            else status.HTTP_200_OK
        )

        return Response(
            {
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id),
                "status": payment.status,
                "amount": str(payment.amount),
                "payment_url": result["payment_url"],
                "reused": result["reused"],
            },
            status=response_status,
        )


# =========================================================
# Payment Detail
# =========================================================

class PaymentDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):

        payment = (
            Payment.objects
            .select_related("order")
            .filter(
                id=payment_id,
                order__user=request.user,
            )
            .first()
        )

        if payment is None:
            raise NotFound("Payment not found.")

        return Response(
            {
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id),
                "order_number": payment.order.order_number,
                "status": payment.status,
                "amount": str(payment.amount),
                "provider": payment.provider,
                "provider_reference": payment.provider_reference,
                "review_reason": payment.review_reason,
                "payment_url": (
                    payment.payment_url
                    if payment.status == Payment.Status.PENDING
                    else None
                ),
                "paid_at": payment.paid_at,
                "created_at": payment.created_at,
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# Zarinpal Callback
# =========================================================

class ZarinpalCallbackView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    # -----------------------------------------------------
    # Redirect to frontend
    # -----------------------------------------------------

    def _redirect_result(self, *, payment, result):

        frontend_url = settings.FRONTEND_PAYMENT_RESULT_URL

        parts = urlsplit(frontend_url)

        query_params = dict(
            parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
        )

        query_params.update({
            "status": result,
            "payment_id": str(payment.id),
            "order_number": payment.order.order_number,
        })

        redirect_url = urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_params),
            parts.fragment,
        ))

        return HttpResponseRedirect(redirect_url)

    # -----------------------------------------------------
    # Find payment
    # -----------------------------------------------------

    def _get_payment(self, request, authority):

        payment_id = request.query_params.get("payment_id")

        if payment_id:

            try:
                payment_id = UUID(payment_id)

            except (ValueError, TypeError):
                return None

            return (
                Payment.objects
                .select_related("order")
                .filter(
                    id=payment_id,
                    provider=Payment.Provider.ZARINPAL,
                )
                .first()
            )

        # Backward compatibility for callbacks
        # without payment_id.

        return (
            Payment.objects
            .select_related("order")
            .filter(
                provider=Payment.Provider.ZARINPAL,
                authority=authority,
            )
            .first()
        )

    # -----------------------------------------------------
    # Lock Order and Payment
    # -----------------------------------------------------

    def _lock_payment(self, payment_id):

        order_id = (
            Payment.objects
            .only("order_id")
            .get(id=payment_id)
            .order_id
        )

        order = (
            Order.objects
            .select_for_update()
            .get(id=order_id)
        )

        payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment_id)
        )

        return order, payment

    # -----------------------------------------------------
    # GET Callback
    # -----------------------------------------------------

    def get(self, request):

        authority = request.query_params.get("Authority")
        gateway_status = request.query_params.get("Status")

        # -------------------------------------------------
        # Validate callback parameters
        # -------------------------------------------------

        if not authority:
            return Response(
                {"detail": "Authority is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not gateway_status:
            return Response(
                {"detail": "Status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authority = authority.strip()

        if not authority or len(authority) > 255:
            return Response(
                {"detail": "Authority is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        gateway_status = gateway_status.upper()

        if not authority:
            return Response(
                {"detail": "Authority is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if gateway_status not in ["OK", "NOK"]:
            return Response(
                {"detail": "Invalid gateway status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Find payment
        # -------------------------------------------------

        payment = self._get_payment(
            request,
            authority,
        )

        if payment is None:

            logger.warning(
                "Zarinpal callback payment not found. Authority: %s",
                authority,
            )

            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # Lock payment and order
        # -------------------------------------------------

        with transaction.atomic():

            order, locked_payment = self._lock_payment(
                payment.id
            )

            # -------------------------------------------------
            # Authority validation
            # -------------------------------------------------

            if locked_payment.authority:

                if locked_payment.authority != authority:

                    logger.warning(
                        "Zarinpal authority mismatch for payment %s",
                        locked_payment.id,
                    )

                    return Response(
                        {"detail": "Payment authority mismatch."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # -------------------------------------------------
            # Early callback
            # -------------------------------------------------

            else:

                if locked_payment.status in [
                    Payment.Status.INITIATED,
                    Payment.Status.UNKNOWN,
                ]:

                    locked_payment.callback_authority = authority
                    locked_payment.callback_status = gateway_status
                    locked_payment.callback_received_at = timezone.now()

                    locked_payment.save(
                        update_fields=[
                            "callback_authority",
                            "callback_status",
                            "callback_received_at",
                            "updated_at",
                        ]
                    )

                else:

                    logger.warning(
                        "Callback received without payment authority. "
                        "Payment: %s, status: %s",
                        locked_payment.id,
                        locked_payment.status,
                    )

        # -------------------------------------------------
        # Reload payment
        # -------------------------------------------------

        payment = (
            Payment.objects
            .select_related("order")
            .get(id=payment.id)
        )

        # -------------------------------------------------
        # Check final states
        # -------------------------------------------------

        if payment.status in FINAL_PAYMENT_STATUSES:

            return self._redirect_result(
                payment=payment,
                result=(
                    "review_required"
                    if payment.status == Payment.Status.REVIEW_REQUIRED
                    else (
                        "success"
                        if payment.status == Payment.Status.SUCCESS
                        else payment.status
                    )
                ),
            )

        # -------------------------------------------------
        # Early callback
        # -------------------------------------------------

        if not payment.authority:

            return self._redirect_result(
                payment=payment,
                result="verification_pending",
            )

        # -------------------------------------------------
        # Authority validation again
        # -------------------------------------------------

        if payment.authority != authority:

            return Response(
                {"detail": "Payment authority mismatch."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Verify with gateway
        # -------------------------------------------------

        try:

            verified_payment = verify_payment(
                payment_id=payment.id,
            )

        except Exception:

            logger.exception(
                "Zarinpal verification failed for payment %s",
                payment.id,
            )

            payment = (
                Payment.objects
                .select_related("order")
                .get(id=payment.id)
            )

            return self._redirect_result(
                payment=payment,
                result="verification_pending",
            )

        # -------------------------------------------------
        # Reload final payment
        # -------------------------------------------------

        payment = (
            Payment.objects
            .select_related("order")
            .get(id=verified_payment.id)
        )

        # -------------------------------------------------
        # Determine frontend result
        # -------------------------------------------------

        if payment.status == Payment.Status.SUCCESS:
            result = "success"

        elif payment.status == Payment.Status.REVIEW_REQUIRED:
            result = "review_required"

        elif payment.status == Payment.Status.FAILED:
            result = "failed"

        elif payment.status == Payment.Status.CANCELLED:
            result = "cancelled"

        else:
            result = "verification_pending"

        return self._redirect_result(
            payment=payment,
            result=result,
        )