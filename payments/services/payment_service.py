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


ACTIVE_PAYMENT_STATUSES = [
    Payment.Status.INITIATED,
    Payment.Status.PENDING,
    Payment.Status.UNKNOWN,
    Payment.Status.REVIEW_REQUIRED,
]

VERIFIABLE_PAYMENT_STATUSES = [
    Payment.Status.PENDING,
    Payment.Status.UNKNOWN,
]


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
        "payment_url": (
            payment.payment_url
            if payment.status == Payment.Status.PENDING
            else None
        ),
        "reused": reused,
    }


def _build_callback_url(payment_id):
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


def _lock_order_and_payment(payment_id):
    """
    Always lock Order first and Payment second.

    This order must remain consistent with inventory release
    and payment finalization to reduce deadlock risk.
    """

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

def _adopt_early_callback_authority(payment_id):
    """
    Adopt an authority received through an early callback.

    The authority is not trusted by itself.
    It must still be verified directly with the gateway.
    """

    with transaction.atomic():
        _, payment = _lock_order_and_payment(payment_id)

        if payment.authority:
            return payment

        if (
            payment.status in [
                Payment.Status.INITIATED,
                Payment.Status.UNKNOWN,
            ]
            and payment.callback_authority
        ):
            payment.authority = payment.callback_authority
            payment.status = Payment.Status.UNKNOWN

            payment.callback_authority = None
            payment.callback_status = None
            payment.callback_received_at = None

            payment.save(
                update_fields=[
                    "authority",
                    "status",
                    "callback_authority",
                    "callback_status",
                    "callback_received_at",
                    "updated_at",
                ]
            )

        return payment
def _mark_payment_failed(
    payment_id,
    result,
    *,
    allow_initiated=False,
):
    """
    Mark a payment as failed only when the gateway result
    is definitive.

    INITIATED is accepted only for an explicit gateway rejection
    during payment creation.
    """

    allowed_statuses = list(VERIFIABLE_PAYMENT_STATUSES)

    if allow_initiated:
        allowed_statuses.append(Payment.Status.INITIATED)

    with transaction.atomic():

        _, payment = _lock_order_and_payment(payment_id)

        if payment.status in allowed_statuses:
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


def _mark_payment_unknown(payment_id, error):
    """
    An exception after sending a gateway request does not prove
    that the gateway failed to create the payment.
    """

    with transaction.atomic():

        _, payment = _lock_order_and_payment(payment_id)

        if payment.status == Payment.Status.INITIATED:
            payment.status = Payment.Status.UNKNOWN

            payment.gateway_response = {
                "message": "Gateway request outcome is unknown.",
                "error": str(error)[:500],
            }

            payment.save(
                update_fields=[
                    "status",
                    "gateway_response",
                    "updated_at",
                ]
            )

        return payment


def _mark_payment_review_required(
    payment_id,
    *,
    reason,
    result=None,
):
    """
    Move an unresolved payment to manual review.

    Do not overwrite successful or failed terminal states.
    """

    with transaction.atomic():

        _, payment = _lock_order_and_payment(payment_id)

        if payment.status in ACTIVE_PAYMENT_STATUSES:
            payment.status = Payment.Status.REVIEW_REQUIRED
            payment.review_reason = reason

            if result is not None:
                payment.gateway_response = (
                    result.get("raw_response") or {}
                )

            payment.save(
                update_fields=[
                    "status",
                    "review_reason",
                    "gateway_response",
                    "updated_at",
                ]
            )

        return payment


def _store_verification_result(payment_id, result):
    """
    Save an ambiguous verification response without changing
    the current payment status.
    """

    with transaction.atomic():

        _, payment = _lock_order_and_payment(payment_id)

        if payment.status in VERIFIABLE_PAYMENT_STATUSES:
            payment.gateway_response = (
                result.get("raw_response") or {}
            )

            payment.save(
                update_fields=[
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

            # -------------------------------------------------
            # Idempotency must be checked before order state.
            # -------------------------------------------------

            existing_payment = (
                Payment.objects
                .select_for_update()
                .filter(
                    idempotency_key=idempotency_key
                )
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

                # Return the same payment resource.
                # Never create a second payment for the same key.
                return _payment_result(
                    existing_payment,
                    reused=True,
                )

            # -------------------------------------------------
            # Validate order state
            # -------------------------------------------------

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
            # Active payment check
            # -------------------------------------------------

            active_payment = (
                Payment.objects
                .select_for_update()
                .filter(
                    order=order,
                    status__in=ACTIVE_PAYMENT_STATUSES,
                )
                .first()
            )

            if active_payment:

                if (
                    active_payment.status
                    == Payment.Status.REVIEW_REQUIRED
                ):
                    raise PaymentGatewayError(
                        "The previous payment requires manual review."
                    )

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
                str(existing_payment.order_id) != str(order_id)
                or existing_payment.provider != provider
            ):
                raise ValidationError({
                    "idempotency_key": (
                        "This key has already been used "
                        "for another payment request."
                    )
                }) from exc

            return _payment_result(
                existing_payment,
                reused=True,
            )

        active_payment = Payment.objects.filter(
            order_id=order_id,
            status__in=ACTIVE_PAYMENT_STATUSES,
        ).first()

        if active_payment:
            raise PaymentGatewayError(
                "Another payment attempt is already active for this order."
            ) from exc

        raise PaymentGatewayError(
            "Could not create the payment attempt."
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
                "Gateway response does not contain authority or payment_url."
            )

    except ZarinpalRejectedError as exc:

        failed_payment = _mark_payment_failed(
            payment_id,
            {
                "raw_response": {
                    "error": str(exc)[:500],
                    "message": "Gateway explicitly rejected the request.",
                }
            },
            allow_initiated=True,
        )

        return _payment_result(
            failed_payment,
            reused=False,
        )

    except Exception as exc:

        unknown_payment = _mark_payment_unknown(
            payment_id,
            exc,
        )

        # A callback may have arrived before the gateway
        # request timed out.
        unknown_payment = _adopt_early_callback_authority(
            payment_id
        )

        # If an early callback supplied an authority,
        # verify it instead of leaving it unresolved.
        if unknown_payment.authority:

            try:
                unknown_payment = verify_payment(
                    payment_id
                )

            except PaymentGatewayError:
                unknown_payment.refresh_from_db()

        return _payment_result(
            unknown_payment,
            reused=False,
        )

    # -----------------------------------------------------
    # STEP 3: Save Gateway Response
    # -----------------------------------------------------

    early_callback = None

    try:

        with transaction.atomic():

            # Keep the same lock order as finalization.
            _, locked_payment = _lock_order_and_payment(
                payment_id
            )

            # A reconciliation worker may have moved the payment
            # to REVIEW_REQUIRED while the gateway request was running.
            if locked_payment.status not in [
                Payment.Status.INITIATED,
                Payment.Status.UNKNOWN,
                Payment.Status.REVIEW_REQUIRED,
            ]:
                return _payment_result(
                    locked_payment,
                    reused=False,
                )

            locked_payment.authority = authority
            locked_payment.payment_url = payment_url

            locked_payment.gateway_response = (
                gateway_result.get("raw_response") or {}
            )

            if locked_payment.status in [
                Payment.Status.INITIATED,
                Payment.Status.UNKNOWN,
            ]:
                locked_payment.status = Payment.Status.PENDING

            if (
                locked_payment.callback_authority
                and locked_payment.callback_authority == authority
            ):
                early_callback = locked_payment.callback_status

            # Callback data is advisory. Clear it after inspecting it.
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

    except IntegrityError as exc:

        # For example, the authority may already belong to another
        # payment record. Do not silently mark this payment failed.
        _mark_payment_review_required(
            payment_id,
            reason="gateway_authority_conflict",
        )

        raise PaymentGatewayError(
            "The gateway response requires manual review."
        ) from exc

    locked_payment = Payment.objects.get(id=payment_id)

    # -----------------------------------------------------
    # STEP 4: Process Early Callback
    # -----------------------------------------------------

    if (
        early_callback in ["OK", "NOK"]
        and locked_payment.status == Payment.Status.PENDING
    ):

        try:
            locked_payment = verify_payment(
                locked_payment.id
            )

        except PaymentGatewayError:
            locked_payment.refresh_from_db()

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

    if payment.status not in VERIFIABLE_PAYMENT_STATUSES:
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

    except Exception as exc:

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

    return _store_verification_result(
        payment.id,
        result,
    )


# =========================================================
# Finalize Verified Payment
# =========================================================

def finalize_verified_payment(payment_id, gateway_result):

    reference = gateway_result.get("reference")

    if reference is None or str(reference).strip() == "":
        raise PaymentGatewayError(
            "Gateway confirmed payment without a transaction reference."
        )

    now = timezone.now()

    with transaction.atomic():

        order, payment = _lock_order_and_payment(
            payment_id
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

        if payment.status not in VERIFIABLE_PAYMENT_STATUSES:
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

            payment.gateway_response = (
                gateway_result.get("raw_response") or {}
            )

            payment.save(
                update_fields=[
                    "provider_reference",
                    "status",
                    "review_reason",
                    "gateway_response",
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

            payment.gateway_response = (
                gateway_result.get("raw_response") or {}
            )

            payment.save(
                update_fields=[
                    "provider_reference",
                    "status",
                    "review_reason",
                    "gateway_response",
                    "updated_at",
                ]
            )

            return payment

        # -------------------------------------------------
        # Complete payment
        # -------------------------------------------------

        payment.status = Payment.Status.SUCCESS
        payment.paid_at = now
        payment.review_reason = None

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

        # Stock was deducted when the order was created.
        # Consume reservations without deducting stock again.

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