
import logging

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from payments.models import Payment
from payments.serializers import InitializePaymentSerializer
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from urllib.parse import urlencode
from payments.services.payment_service import initialize_payment, verify_payment


logger = logging.getLogger(__name__)

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


class PaymentDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):

        payment = Payment.objects.filter(
            id=payment_id,
            order__user=request.user,
        ).first()

        if not payment:
            raise NotFound("Payment not found.")

        return Response({
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "status": payment.status,
            "amount": str(payment.amount),
            "provider": payment.provider,
            "provider_reference": payment.provider_reference,
            "paid_at": payment.paid_at,
            "created_at": payment.created_at,
        })


class ZarinpalCallbackView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def _redirect_result(self, *, payment, result):
        query = urlencode({
            "status": result,
            "payment_id": str(payment.id),
            "order_number": payment.order.order_number,
        })

        return HttpResponseRedirect(
            f"{settings.FRONTEND_PAYMENT_RESULT_URL}?{query}"
        )

    def get(self, request):

        authority = request.query_params.get("Authority")
        gateway_status = request.query_params.get("Status")

        if not authority:
            return Response(
                {"detail": "Authority is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = (
            Payment.objects
            .select_related("order")
            .filter(
                provider=Payment.Provider.ZARINPAL,
                authority=authority,
            )
            .first()
        )

        if not payment:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # اگر قبلاً پرداخت تأیید شده، Callback تکراری
        # نباید وضعیت آن را تغییر دهد.
        if payment.status == Payment.Status.SUCCESS:
            return self._redirect_result(
                payment=payment,
                result="success",
            )

        if payment.status != Payment.Status.PENDING:
            return self._redirect_result(
                payment=payment,
                result="not_pending",
            )

        # کاربر پرداخت را لغو کرده یا درگاه وضعیت NOK داده است.
        if gateway_status != "OK":

            with transaction.atomic():

                locked_payment = Payment.objects.select_for_update().get(
                    id=payment.id
                )

                if locked_payment.status == Payment.Status.PENDING:
                    locked_payment.status = Payment.Status.CANCELLED
                    locked_payment.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

            return self._redirect_result(
                payment=payment,
                result="cancelled",
            )

        # Status=OK فقط باعث شروع Verify می‌شود.
        # تأیید نهایی داخل verify_payment انجام می‌شود.
        try:
            verified_payment = verify_payment(
                payment_id=payment.id,
            )

        except Exception:
            logger.exception(
                "Zarinpal verification failed for payment %s",
                payment.id,
            )

            # در خطای شبکه، پرداخت را به‌صورت قطعی Failed نمی‌کنیم.
            # وضعیت Pending می‌ماند تا بعداً دوباره بررسی شود.
            return self._redirect_result(
                payment=payment,
                result="verification_pending",
            )

        if verified_payment.status == Payment.Status.SUCCESS:
            return self._redirect_result(
                payment=verified_payment,
                result="success",
            )

        return self._redirect_result(
            payment=verified_payment,
            result="failed",
        )