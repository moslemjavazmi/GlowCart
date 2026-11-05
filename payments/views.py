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

from payments.models import Payment
from payments.serializers import InitializePaymentSerializer
from payments.services.payment_service import (
    initialize_payment,
    verify_payment,
)

logger = logging.getLogger(__name__)


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

        return Response(
            {
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id),
                "status": payment.status,
                "amount": str(payment.amount),
                "payment_url": result["payment_url"],
                "reused": result["reused"],
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# Payment Detail
# =========================================================

class PaymentDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):

        payment = (
            Payment.objects
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
                "status": payment.status,
                "amount": str(payment.amount),
                "provider": payment.provider,
                "provider_reference": payment.provider_reference,
                "review_reason": payment.review_reason,
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

        # New callback URLs contain payment_id.
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

        # Backward compatibility for old callback URLs.
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
    # GET Callback
    # -----------------------------------------------------

    def get(self, request):

        authority = request.query_params.get("Authority")
        gateway_status = request.query_params.get("Status")

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

        gateway_status = gateway_status.upper()

        # Accept only documented callback status values.
        if gateway_status not in ["OK", "NOK"]:
            return Response(
                {"detail": "Invalid gateway status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        # Already finalized
        # -------------------------------------------------

        if payment.status == Payment.Status.SUCCESS:
            return self._redirect_result(
                payment=payment,
                result="success",
            )

        if payment.status == Payment.Status.REVIEW_REQUIRED:
            return self._redirect_result(
                payment=payment,
                result="review_required",
            )

        if payment.status in [
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ]:
            return self._redirect_result(
                payment=payment,
                result=payment.status,
            )

        # -------------------------------------------------
        # Lock payment
        # -------------------------------------------------

        with transaction.atomic():

            locked_payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment.id)
            )

            # Another callback may have finalized payment.
            if locked_payment.status in [
                Payment.Status.SUCCESS,
                Payment.Status.REVIEW_REQUIRED,
                Payment.Status.FAILED,
                Payment.Status.CANCELLED,
            ]:
                pass

            # -------------------------------------------------
            # Early callback
            # -------------------------------------------------

            elif not locked_payment.authority:

                # Authority is not saved yet.
                # Store callback temporarily.
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

            # -------------------------------------------------
            # Authority mismatch
            # -------------------------------------------------

            elif locked_payment.authority != authority:

                logger.warning(
                    "Zarinpal callback authority mismatch for payment %s",
                    locked_payment.id,
                )

            # If authority matches, continue after transaction.

        # Reload payment and order.
        payment = (
            Payment.objects
            .select_related("order")
            .get(id=payment.id)
        )

        # -------------------------------------------------
        # Check final states again
        # -------------------------------------------------

        if payment.status == Payment.Status.SUCCESS:
            return self._redirect_result(
                payment=payment,
                result="success",
            )

        if payment.status == Payment.Status.REVIEW_REQUIRED:
            return self._redirect_result(
                payment=payment,
                result="review_required",
            )

        if payment.status in [
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ]:
            return self._redirect_result(
                payment=payment,
                result=payment.status,
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
        # Authority validation
        # -------------------------------------------------

        if payment.authority != authority:
            return self._redirect_result(
                payment=payment,
                result="verification_pending",
            )

        # -------------------------------------------------
        # Non-success callback
        # -------------------------------------------------

        if gateway_status == "NOK":

            with transaction.atomic():

                locked_payment = (
                    Payment.objects
                    .select_for_update()
                    .get(id=payment.id)
                )

                # Only cancel a pending payment.
                # UNKNOWN remains unresolved because a callback
                # alone is not sufficient to prove no charge occurred.

                if locked_payment.status == Payment.Status.PENDING:

                    locked_payment.status = Payment.Status.CANCELLED

                    locked_payment.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

            payment = (
                Payment.objects
                .select_related("order")
                .get(id=payment.id)
            )

            return self._redirect_result(
                payment=payment,
                result=payment.status,
            )

        # -------------------------------------------------
        # Verify payment with Zarinpal
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

        elif payment.status in [
            Payment.Status.PENDING,
            Payment.Status.UNKNOWN,
            Payment.Status.INITIATED,
        ]:
            result = "verification_pending"

        else:
            result = payment.status

        return self._redirect_result(
            payment=payment,
            result=result,
        )