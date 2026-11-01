
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import (
    ValidationError,
    APIException,
)
from django.conf import settings

from orders.models import Order
from payments.models import Payment
from payments.gateways.factory import get_payment_gateway


class PaymentGatewayError(APIException):
    status_code = 502
    default_detail = "Payment gateway is temporarily unavailable."
    default_code = "payment_gateway_error"


def initialize_payment(
    *,
    user,
    order_id,
    provider,
    idempotency_key,
):
    # مرحله اول:
    # بررسی سفارش و ثبت Payment اولیه در دیتابیس

    with transaction.atomic():

        order = (
            Order.objects
            .select_for_update()
            .filter(
                id=order_id,
                user=user,
            )
            .first()
        )

        if not order:
            raise ValidationError({
                "order_id": "Order not found."
            })

        if order.status != Order.Status.AWAITING_PAYMENT:
            raise ValidationError({
                "order": "This order is not awaiting payment."
            })

        amount = order.total_amount

        if amount <= Decimal("0.00"):
            raise ValidationError({
                "amount": "Order amount must be greater than zero."
            })

        # بررسی Idempotency
        existing_payment = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing_payment:

            if (
                existing_payment.order_id != order.id
                or existing_payment.provider != provider
            ):
                raise ValidationError({
                    "idempotency_key": (
                        "This key has already been used "
                        "for another payment request."
                    )
                })

            if (
                existing_payment.status == Payment.Status.PENDING
                and existing_payment.payment_url
            ):
                return {
                    "payment": existing_payment,
                    "payment_url": existing_payment.payment_url,
                    "reused": True,
                }

            if existing_payment.status == Payment.Status.INITIATED:
                raise ValidationError({
                    "payment": (
                        "This payment request is still being processed. "
                        "Please retry shortly."
                    )
                })

            raise ValidationError({
                "idempotency_key": (
                    "This payment attempt has already finished. "
                    "Use a new key for a new attempt."
                )
            })

        # جلوگیری از ایجاد چند پرداخت فعال برای یک سفارش
        active_payment = Payment.objects.filter(
            order=order,
            status__in=[
                Payment.Status.INITIATED,
                Payment.Status.PENDING,
            ],
        ).first()

        if active_payment:
            raise ValidationError({
                "payment": (
                    "An active payment already exists for this order."
                )
            })

        payment = Payment.objects.create(
            order=order,
            provider=provider,
            status=Payment.Status.INITIATED,
            amount=amount,
            idempotency_key=idempotency_key,
        )

    # مرحله دوم:
    # ارتباط با درگاه خارج از transaction دیتابیس

    try:
        gateway = get_payment_gateway(provider)

        gateway_result = gateway.create_payment(
            amount=amount,
            callback_url=settings.PAYMENT_CALLBACK_URL,
            description=f"Payment for order {order.order_number}",
            metadata={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        )

        authority = gateway_result["authority"]
        payment_url = gateway_result["payment_url"]

        if not authority or not payment_url:
            raise ValueError("Invalid gateway response.")

    except Exception as exc:

        Payment.objects.filter(
            id=payment.id,
            status=Payment.Status.INITIATED,
        ).update(
            status=Payment.Status.FAILED,
            gateway_response={
                "error": str(exc)[:500],
            },
            updated_at=timezone.now(),
        )

        raise PaymentGatewayError()

    # مرحله سوم:
    # ذخیره اطلاعات دریافتی از درگاه

    updated = Payment.objects.filter(
        id=payment.id,
        status=Payment.Status.INITIATED,
    ).update(
        authority=authority,
        payment_url=payment_url,
        status=Payment.Status.PENDING,
        gateway_response=gateway_result.get("raw_response") or {},
        updated_at=timezone.now(),
    )

    if not updated:
        raise PaymentGatewayError(
            "Payment state could not be updated."
        )

    payment.refresh_from_db()

    return {
        "payment": payment,
        "payment_url": payment_url,
        "reused": False,
    }



def verify_payment(*, payment_id):
    payment = Payment.objects.select_related("order").filter(
        id=payment_id
    ).first()

    if not payment:
        raise PaymentGatewayError("Payment not found.")

    # Callback ممکن است چند بار ارسال شود.
    # اگر قبلاً موفق شده، دوباره Verify نمی‌کنیم.
    if payment.status == Payment.Status.SUCCESS:
        return payment

    if payment.status != Payment.Status.PENDING:
        raise PaymentGatewayError(
            "Payment is not in a verifiable state."
        )

    if not payment.authority:
        raise PaymentGatewayError(
            "Payment authority is missing."
        )

    gateway = get_payment_gateway(payment.provider)

    # تماس با سرور درگاه خارج از transaction
    result = gateway.verify_payment(
        authority=payment.authority,
        amount=payment.amount,
    )

    if not result.get("success"):
        with transaction.atomic():
            locked_payment = Payment.objects.select_for_update().get(
                id=payment.id
            )

            if locked_payment.status == Payment.Status.SUCCESS:
                return locked_payment

            if locked_payment.status == Payment.Status.PENDING:
                locked_payment.status = Payment.Status.FAILED
                locked_payment.gateway_response = (
                    result.get("raw_response") or {}
                )
                locked_payment.save(
                    update_fields=[
                        "status",
                        "gateway_response",
                        "updated_at",
                    ]
                )

        return locked_payment

    reference = result.get("reference")

    if not reference:
        raise PaymentGatewayError(
            "Gateway verification returned no reference."
        )

    # ثبت نتیجه موفق به شکل اتمیک
    with transaction.atomic():

        locked_payment = Payment.objects.select_for_update().get(
            id=payment.id
        )

        locked_order = Order.objects.select_for_update().get(
            id=locked_payment.order_id
        )

        # محافظت در برابر Callback تکراری
        if locked_payment.status == Payment.Status.SUCCESS:
            return locked_payment

        if locked_payment.status != Payment.Status.PENDING:
            raise PaymentGatewayError(
                "Payment state changed during verification."
            )

        # اگر سفارش قبلاً پرداخت شده باشد، نباید دوباره
        # وضعیت آن را تغییر دهیم.
        if locked_order.status == Order.Status.PAID:
            raise PaymentGatewayError(
                "Order has already been paid by another payment."
            )

        if locked_order.status != Order.Status.AWAITING_PAYMENT:
            raise PaymentGatewayError(
                "Order is not awaiting payment."
            )

        if locked_payment.amount != locked_order.total_amount:
            raise PaymentGatewayError(
                "Payment amount does not match order amount."
            )

        locked_payment.status = Payment.Status.SUCCESS
        locked_payment.provider_reference = str(reference)
        locked_payment.gateway_response = (
            result.get("raw_response") or {}
        )
        locked_payment.paid_at = timezone.now()

        locked_payment.save(
            update_fields=[
                "status",
                "provider_reference",
                "gateway_response",
                "paid_at",
                "updated_at",
            ]
        )

        locked_order.status = Order.Status.PAID
        locked_order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return locked_payment