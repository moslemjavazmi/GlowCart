
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError, APIException

from orders.models import Order, InventoryReservation
from payments.models import Payment
from payments.gateways.factory import get_payment_gateway
from payments.gateways.zarinpal import (
    ZarinpalGatewayError,
    ZarinpalRejectedError,
)

from promotions.services.coupon_service import (
    consume_coupon_reservation,
)

class PaymentGatewayError(APIException):
    status_code = 502
    default_detail = "Payment gateway is temporarily unavailable."
    default_code = "payment_gateway_error"


# =========================================================
# Helpers
# =========================================================

def _get_gateway(provider):
    """
    Instantiate the gateway before creating a Payment record.

    Configuration errors should not leave an INITIATED payment
    in the database.
    """
    try:
        return get_payment_gateway(provider)

    except ZarinpalGatewayError as exc:
        raise PaymentGatewayError(
            "Payment gateway configuration is invalid."
        ) from exc

    except ValueError as exc:
        raise ValidationError({
            "provider": str(exc)
        }) from exc


def _payment_result(payment, *, reused):
    return {
        "payment": payment,
        "payment_url": payment.payment_url,
        "reused": reused,
    }


# =========================================================
# Initialize Payment
# =========================================================

def initialize_payment(
    *,
    user,
    order_id,
    provider,
    idempotency_key,
):
    """
    Create a payment attempt and request a payment URL.

    Important:
    - The database transaction is not held open during HTTP calls.
    - A definite gateway rejection becomes FAILED.
    - An ambiguous gateway outcome becomes UNKNOWN.
    """

    # Instantiate first. This catches local configuration errors
    # before creating a Payment record.
    gateway = _get_gateway(provider)

    # -----------------------------------------------------
    # STEP 1: Validate order and create Payment
    # -----------------------------------------------------

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

        now = timezone.now()

        if order.expires_at and order.expires_at <= now:
            raise ValidationError({
                "order": "This order has expired."
            })

        amount = order.total_amount

        if amount <= Decimal("0.00"):
            raise ValidationError({
                "amount": "Order amount must be greater than zero."
            })

        # -------------------------------------------------
        # Idempotency
        # -------------------------------------------------

        existing_payment = (
            Payment.objects
            .select_for_update()
            .filter(idempotency_key=idempotency_key)
            .first()
        )

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
                return _payment_result(
                    existing_payment,
                    reused=True,
                )

            if existing_payment.status in [
                Payment.Status.INITIATED,
                Payment.Status.UNKNOWN,
            ]:
                raise PaymentGatewayError(
                    "The previous payment attempt is still unresolved. "
                    "Do not create another payment attempt yet."
                )

            raise ValidationError({
                "idempotency_key": (
                    "This payment attempt has already finished. "
                    "Use a new key for a new attempt."
                )
            })

        # -------------------------------------------------
        # Active payment check
        # -------------------------------------------------

        active_payment = (
            Payment.objects
            .select_for_update()
            .filter(
                order=order,
                status__in=[
                    Payment.Status.INITIATED,
                    Payment.Status.PENDING,
                    Payment.Status.UNKNOWN,
                ],
            )
            .first()
        )

        if active_payment:
            raise PaymentGatewayError(
                "This order already has an active payment attempt."
            )

        # -------------------------------------------------
        # Create initial Payment
        # -------------------------------------------------

        payment = Payment.objects.create(
            order=order,
            provider=provider,
            status=Payment.Status.INITIATED,
            amount=amount,
            idempotency_key=idempotency_key,
        )

        payment_id = payment.id
        order_number = order.order_number

    # -----------------------------------------------------
    # STEP 2: Call gateway OUTSIDE database transaction
    # -----------------------------------------------------

    try:
        gateway_result = gateway.create_payment(
            amount=amount,
            callback_url=settings.PAYMENT_CALLBACK_URL,
            description=f"Payment for order {order_number}",
            metadata={
                "order_id": str(order_id),
                "payment_id": str(payment_id),
            },
        )

        authority = gateway_result.get("authority")
        payment_url = gateway_result.get("payment_url")

        if not authority or not payment_url:
            # The gateway may have created a transaction even
            # though its response was incomplete.
            raise ValueError("Invalid gateway response.")

    except ZarinpalRejectedError as exc:
        # The gateway explicitly rejected the request.
        Payment.objects.filter(
            id=payment_id,
            status=Payment.Status.INITIATED,
        ).update(
            status=Payment.Status.FAILED,
            gateway_response={
                "error": str(exc)[:500],
                "message": "Gateway explicitly rejected the request.",
            },
            updated_at=timezone.now(),
        )

        raise PaymentGatewayError(
            "The payment gateway rejected the payment request."
        ) from exc

    except Exception as exc:
        # Network errors, timeouts, malformed responses, and
        # unexpected errors can have an ambiguous outcome.
        Payment.objects.filter(
            id=payment_id,
            status=Payment.Status.INITIATED,
        ).update(
            status=Payment.Status.UNKNOWN,
            gateway_response={
                "error": str(exc)[:500],
                "message": "Gateway request outcome is unknown.",
            },
            updated_at=timezone.now(),
        )

        raise PaymentGatewayError(
            "The payment outcome is unknown. "
            "Do not retry with a new payment attempt yet."
        ) from exc

    # -----------------------------------------------------
    # STEP 3: Save gateway response
    # -----------------------------------------------------

    with transaction.atomic():

        locked_payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment_id)
        )

        if locked_payment.status not in [
            Payment.Status.INITIATED,
            Payment.Status.UNKNOWN,
        ]:
            # Never overwrite a state that another process
            # has already finalized.
            raise PaymentGatewayError(
                "Payment state changed while processing the gateway response."
            )

        locked_payment.authority = authority
        locked_payment.payment_url = payment_url
        locked_payment.status = Payment.Status.PENDING
        locked_payment.gateway_response = (
            gateway_result.get("raw_response") or {}
        )

        locked_payment.save(
            update_fields=[
                "authority",
                "payment_url",
                "status",
                "gateway_response",
                "updated_at",
            ]
        )

    locked_payment.refresh_from_db()

    return _payment_result(
        locked_payment,
        reused=False,
    )


# =========================================================
# Verify Payment
# =========================================================

def verify_payment(payment_id):
    """
    Verify a payment with the gateway.

    Ambiguous verification results do not change the payment
    to FAILED. They remain available for reconciliation.
    """

    payment = (
        Payment.objects
        .select_related("order")
        .get(id=payment_id)
    )

    if payment.status in [
        Payment.Status.SUCCESS,
        Payment.Status.REVIEW_REQUIRED,
    ]:
        return payment

    if payment.status not in [
        Payment.Status.PENDING,
        Payment.Status.UNKNOWN,
    ]:
        raise ValidationError(
            "Payment cannot be verified in its current state."
        )

    if not payment.authority:
        raise ValidationError(
            "Payment authority is missing."
        )

    gateway = _get_gateway(payment.provider)

    try:
        result = gateway.verify_payment(
            authority=payment.authority,
            amount=payment.amount,
        )

    except ZarinpalGatewayError as exc:
        # A communication or response error is not proof
        # that the payment failed.
        raise PaymentGatewayError(
            "Could not determine the payment verification result."
        ) from exc

    if result.get("success") is True:
        return finalize_verified_payment(
            payment.id,
            result,
        )

    if result.get("definitive_failure") is True:

        with transaction.atomic():

            locked_payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment.id)
            )

            # Another callback/reconciliation process may have
            # completed this payment while verification was running.
            if locked_payment.status in [
                Payment.Status.SUCCESS,
                Payment.Status.REVIEW_REQUIRED,
            ]:
                return locked_payment

            if locked_payment.status in [
                Payment.Status.PENDING,
                Payment.Status.UNKNOWN,
            ]:
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

    # An ambiguous result remains unresolved.
    return Payment.objects.get(id=payment.id)


# =========================================================
# Finalize Verified Payment
# =========================================================

def finalize_verified_payment(payment_id, gateway_result):
    """
    Finalize a payment after the gateway confirms success.

    A successful gateway transaction does not automatically
    mean that the related order can still be fulfilled.
    """

    reference = gateway_result.get("reference")

    if not reference:
        raise PaymentGatewayError(
            "Gateway confirmed payment without a transaction reference."
        )

    now = timezone.now()

    with transaction.atomic():

        payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment_id)
        )

        order = (
            Order.objects
            .select_for_update()
            .get(id=payment.order_id)
        )

        # -------------------------------------------------
        # Idempotency
        # -------------------------------------------------

        if payment.status in [
            Payment.Status.SUCCESS,
            Payment.Status.REVIEW_REQUIRED,
        ]:
            return payment

        if payment.status not in [
            Payment.Status.PENDING,
            Payment.Status.UNKNOWN,
        ]:
            raise ValidationError(
                "Payment is not eligible for finalization."
            )

        payment.provider_reference = str(reference)

        # -------------------------------------------------
        # Validate amount
        # -------------------------------------------------

        if payment.amount != order.total_amount:
            payment.status = Payment.Status.REVIEW_REQUIRED
            payment.review_reason = "amount_mismatch"

            payment.save(
                update_fields=[
                    "provider_reference",
                    "status",
                    "review_reason",
                    "updated_at",
                ]
            )

            return payment

        # -------------------------------------------------
        # Another payment may already have paid this order
        # -------------------------------------------------

        if order.status == Order.Status.PAID:
            payment.status = Payment.Status.REVIEW_REQUIRED
            payment.review_reason = "order_already_paid"

            payment.save(
                update_fields=[
                    "provider_reference",
                    "status",
                    "review_reason",
                    "updated_at",
                ]
            )

            return payment

        # -------------------------------------------------
        # Validate order and inventory reservation
        # -------------------------------------------------

        if (
            order.status != Order.Status.AWAITING_PAYMENT
            or order.inventory_released_at is not None
            or (
                order.expires_at is not None
                and order.expires_at <= now
            )
        ):
            payment.status = Payment.Status.REVIEW_REQUIRED

            if order.inventory_released_at is not None:
                payment.review_reason = "inventory_already_released"
            else:
                payment.review_reason = "order_expired"

            payment.save(
                update_fields=[
                    "provider_reference",
                    "status",
                    "review_reason",
                    "updated_at",
                ]
            )

            return payment

        # -------------------------------------------------
        # Complete payment
        # -------------------------------------------------

        payment.status = Payment.Status.SUCCESS
        payment.paid_at = now
        payment.review_reason = ""

        payment.gateway_response = (
            gateway_result.get("raw_response") or {}
        )

        payment.save(
            update_fields=[
                "provider_reference",
                "status",
                "paid_at",
                "review_reason",
                "gateway_response",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Complete order
        # -------------------------------------------------

        order.status = Order.Status.PAID

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # Stock was already deducted when the order was created.
        # Here we only consume the existing reservations.
        InventoryReservation.objects.filter(
            order=order,
            status=InventoryReservation.Status.ACTIVE,
        ).update(
            status=InventoryReservation.Status.CONSUMED,
            consumed_at=now,
        )
        consume_coupon_reservation(order_id=order.id)
        return payment
