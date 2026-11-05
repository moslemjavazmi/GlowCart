from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.db import IntegrityError, transaction
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


def _build_callback_url(payment_id):
    """
    Add payment_id to the callback URL.

    This allows the callback endpoint to identify the payment
    even if the gateway callback arrives before authority is saved.
    """

    base_url = settings.PAYMENT_CALLBACK_URL

    parts = urlsplit(base_url)

    query_params = dict(
        parse_qsl(parts.query, keep_blank_values=True)
    )

    query_params["payment_id"] = str(payment_id)

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query_params),
        parts.fragment,
    ))


def _mark_payment_failed(payment_id, result):

    with transaction.atomic():

        payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment_id)
        )

        if payment.status in [
            Payment.Status.PENDING,
            Payment.Status.UNKNOWN,
        ]:
            payment.status = Payment.Status.FAILED

            payment.gateway_response = (
                result.get("raw_response") or {}
            )

            payment.save(
                update_fields=[
                    "status",
                    "gateway_response",
                    "updated_at",
                ]
            )

        return payment


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

    gateway = _get_gateway(provider)

    # -----------------------------------------------------
    # STEP 1: Validate order and create Payment
    # -----------------------------------------------------

    try:

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
                        "The previous payment attempt is unresolved. "
                        "Do not create another payment attempt."
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

            payment = Payment.objects.create(
                order=order,
                provider=provider,
                status=Payment.Status.INITIATED,
                amount=amount,
                idempotency_key=idempotency_key,
            )

            payment_id = payment.id
            order_number = order.order_number

    except IntegrityError as exc:

        # A concurrent request may have inserted the same
        # idempotency key or another active payment.

        existing_payment = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing_payment:

            if (
                existing_payment.order_id != order_id
                or existing_payment.provider != provider
            ):
                raise ValidationError({
                    "idempotency_key": (
                        "This key has already been used "
                        "for another payment request."
                    )
                }) from exc

            if (
                existing_payment.status == Payment.Status.PENDING
                and existing_payment.payment_url
            ):
                return _payment_result(
                    existing_payment,
                    reused=True,
                )

            raise PaymentGatewayError(
                "The previous payment attempt is unresolved."
            ) from exc

        raise PaymentGatewayError(
            "Another payment attempt is already active for this order."
        ) from exc

    # -----------------------------------------------------
    # STEP 2: Call Gateway OUTSIDE transaction
    # -----------------------------------------------------

    callback_url = _build_callback_url(payment_id)

    try:

        gateway_result = gateway.create_payment(
            amount=amount,
            callback_url=callback_url,
            description=f"Payment for order {order_number}",
            metadata={
                "order_id": str(order_id),
                "payment_id": str(payment_id),
            },
        )

        authority = gateway_result.get("authority")
        payment_url = gateway_result.get("payment_url")

        if not authority or not payment_url:
            raise ValueError(
                "Invalid gateway response."
            )

    except ZarinpalRejectedError as exc:

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
    # STEP 3: Save Gateway Response
    # -----------------------------------------------------

    early_callback = None

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
            raise PaymentGatewayError(
                "Payment state changed while processing gateway response."
            )

        locked_payment.authority = authority
        locked_payment.payment_url = payment_url
        locked_payment.status = Payment.Status.PENDING

        locked_payment.gateway_response = (
            gateway_result.get("raw_response") or {}
        )

        # Check whether callback arrived before authority was saved.
        if (
            locked_payment.callback_authority
            and locked_payment.callback_authority == authority
        ):
            early_callback = locked_payment.callback_status

        # Clear callback data after matching/processing decision.
        if locked_payment.callback_authority:
            locked_payment.callback_authority = None
            locked_payment.callback_status = None
            locked_payment.callback_received_at = None

        locked_payment.save(
            update_fields=[
                "authority",
                "payment_url",
                "status",
                "gateway_response",
                "callback_authority",
                "callback_status",
                "callback_received_at",
                "updated_at",
            ]
        )

    locked_payment.refresh_from_db()

    # -----------------------------------------------------
    # STEP 4: Process Early Callback
    # -----------------------------------------------------

    if early_callback == "OK":

        try:
            locked_payment = verify_payment(
                locked_payment.id
            )

        except PaymentGatewayError:
            # Verification remains unresolved.
            # The frontend can poll PaymentDetail.
            locked_payment.refresh_from_db()

    elif early_callback and early_callback != "OK":

        with transaction.atomic():

            locked_payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment_id)
            )

            if locked_payment.status == Payment.Status.PENDING:
                locked_payment.status = Payment.Status.CANCELLED

                locked_payment.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

    return _payment_result(
        locked_payment,
        reused=False,
    )


# =========================================================
# Verify Payment
# =========================================================

def verify_payment(payment_id):

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

        raise PaymentGatewayError(
            "Could not determine the payment verification result."
        ) from exc

    if result.get("success") is True:

        return finalize_verified_payment(
            payment.id,
            result,
        )

    if result.get("definitive_failure") is True:

        return _mark_payment_failed(
            payment.id,
            result,
        )

    return Payment.objects.get(id=payment.id)


# =========================================================
# Finalize Verified Payment
# =========================================================

def finalize_verified_payment(payment_id, gateway_result):

    reference = gateway_result.get("reference")

    if not reference:
        raise PaymentGatewayError(
            "Gateway confirmed payment without a transaction reference."
        )

    now = timezone.now()

    with transaction.atomic():

        payment_order_id = (
            Payment.objects
            .only("order_id")
            .get(id=payment_id)
            .order_id
        )

        # Lock order first.
        order = (
            Order.objects
            .select_for_update()
            .get(id=payment_order_id)
        )

        # Lock payment second.
        payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment_id)
        )

        if payment.order_id != order.id:
            raise ValidationError(
                "Payment and order relationship is invalid."
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
        # Validate order state and inventory
        # -------------------------------------------------

        if order.inventory_released_at is not None:
            review_reason = "inventory_already_released"

        elif order.expires_at and order.expires_at <= now:
            review_reason = "order_expired"

        elif order.status == Order.Status.PAID:
            review_reason = "order_already_paid"

        elif order.status != Order.Status.AWAITING_PAYMENT:
            review_reason = "order_not_payable"

        else:
            review_reason = None

        if review_reason:

            payment.status = Payment.Status.REVIEW_REQUIRED
            payment.review_reason = review_reason

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
        # Consume existing reservations without deducting stock again.

        InventoryReservation.objects.filter(
            order=order,
            status=InventoryReservation.Status.ACTIVE,
        ).update(
            status=InventoryReservation.Status.CONSUMED,
            consumed_at=now,
        )

        consume_coupon_reservation(
            order_id=order.id
        )

        return payment