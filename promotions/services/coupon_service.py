
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from promotions.models import Coupon, CouponReservation
from orders.models import Order


MONEY_PLACES = Decimal("0.01")

ACTIVE_OR_CONSUMED = [
    CouponReservation.Status.ACTIVE,
    CouponReservation.Status.CONSUMED,
]


def calculate_coupon_discount(coupon, amount):
    """
    Calculate the discount without exceeding the eligible amount.
    """

    amount = Decimal(amount).quantize(MONEY_PLACES)

    if amount <= Decimal("0.00"):
        raise ValidationError({
            "amount": "The eligible amount must be greater than zero."
        })

    if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
        discount = (
            amount * coupon.value / Decimal("100")
        )

        if coupon.max_discount is not None:
            discount = min(discount, coupon.max_discount)

    elif coupon.discount_type == Coupon.DiscountType.FIXED:
        discount = coupon.value

    else:
        raise ValidationError({
            "coupon": "Unsupported discount type."
        })

    discount = min(discount, amount)

    return discount.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def validate_coupon(coupon, *, user, amount):
    """
    Validate time, status, minimum order amount and usage limits.

    This function assumes the Coupon row is already locked
    when used inside the reservation transaction.
    """

    now = timezone.now()

    if not coupon.is_active:
        raise ValidationError({
            "coupon": "This coupon is not active."
        })

    if now < coupon.starts_at:
        raise ValidationError({
            "coupon": "This coupon is not available yet."
        })

    if now >= coupon.expires_at:
        raise ValidationError({
            "coupon": "This coupon has expired."
        })

    amount = Decimal(amount).quantize(MONEY_PLACES)

    if amount < coupon.min_order_amount:
        raise ValidationError({
            "coupon": (
                f"Minimum eligible order amount is "
                f"{coupon.min_order_amount}."
            )
        })

    # Count consumed reservations and currently active reservations.
    usage_count = CouponReservation.objects.filter(
        coupon=coupon,
        status__in=ACTIVE_OR_CONSUMED,
    ).count()

    if (
        coupon.usage_limit is not None
        and usage_count >= coupon.usage_limit
    ):
        raise ValidationError({
            "coupon": "This coupon has reached its usage limit."
        })

    user_usage_count = CouponReservation.objects.filter(
        coupon=coupon,
        user=user,
        status__in=ACTIVE_OR_CONSUMED,
    ).count()

    if (
        coupon.usage_limit_per_user is not None
        and user_usage_count >= coupon.usage_limit_per_user
    ):
        raise ValidationError({
            "coupon": "You have already used this coupon the maximum number of times."
        })

    return calculate_coupon_discount(coupon, amount)


@transaction.atomic
def reserve_coupon(
    *,
    code,
    user,
    order_id,
    discountable_amount,
):
    """
    Validate a coupon and reserve one usage for an order.

    The coupon row is locked to serialize concurrent reservations
    for the same coupon.
    """

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
            "order": "Order not found."
        })

    if order.status != Order.Status.AWAITING_PAYMENT:
        raise ValidationError({
            "order": "This order is not awaiting payment."
        })

    if order.inventory_released_at is not None:
        raise ValidationError({
            "order": "Inventory for this order has already been released."
        })

    if order.expires_at and order.expires_at <= timezone.now():
        raise ValidationError({
            "order": "This order has expired."
        })

    normalized_code = code.strip().upper()

    coupon = (
        Coupon.objects
        .select_for_update()
        .filter(code=normalized_code)
        .first()
    )

    if not coupon:
        raise ValidationError({
            "code": "Invalid coupon code."
        })

    # An order can have only one coupon reservation.
    existing = (
        CouponReservation.objects
        .filter(order=order)
        .first()
    )

    if existing:
        if existing.status == CouponReservation.Status.ACTIVE:
            if existing.coupon_id == coupon.id:
                return existing

            raise ValidationError({
                "coupon": "This order already has an active coupon."
            })

        if existing.status == CouponReservation.Status.CONSUMED:
            raise ValidationError({
                "coupon": "A coupon has already been consumed for this order."
            })

        # A released reservation can be reused for the same order.
        # The old reservation is reactivated after fresh validation.

    discount = validate_coupon(
        coupon,
        user=user,
        amount=discountable_amount,
    )

    reservation_expiry = order.expires_at

    if reservation_expiry is None:
        raise ValidationError({
            "order": "Order expiration time is required."
        })

    if existing:
        existing.coupon = coupon
        existing.user = user
        existing.discount_amount = discount
        existing.status = CouponReservation.Status.ACTIVE
        existing.expires_at = reservation_expiry
        existing.consumed_at = None
        existing.released_at = None

        existing.save(
            update_fields=[
                "coupon",
                "user",
                "discount_amount",
                "status",
                "expires_at",
                "consumed_at",
                "released_at",
            ]
        )

        return existing

    return CouponReservation.objects.create(
        coupon=coupon,
        order=order,
        user=user,
        discount_amount=discount,
        status=CouponReservation.Status.ACTIVE,
        expires_at=reservation_expiry,
    )


@transaction.atomic
def consume_coupon_reservation(*, order_id):
    """
    Mark the active coupon reservation as consumed
    after successful payment.
    """

    reservation = (
        CouponReservation.objects
        .select_for_update()
        .filter(
            order_id=order_id,
            status=CouponReservation.Status.ACTIVE,
        )
        .first()
    )

    if not reservation:
        return False

    reservation.status = CouponReservation.Status.CONSUMED
    reservation.consumed_at = timezone.now()

    reservation.save(
        update_fields=[
            "status",
            "consumed_at",
        ]
    )

    return True


@transaction.atomic
def release_coupon_reservation(*, order_id):
    """
    Release an active coupon reservation when an order
    is cancelled or expires.
    """

    reservation = (
        CouponReservation.objects
        .select_for_update()
        .filter(
            order_id=order_id,
            status=CouponReservation.Status.ACTIVE,
        )
        .first()
    )

    if not reservation:
        return False

    reservation.status = CouponReservation.Status.RELEASED
    reservation.released_at = timezone.now()

    reservation.save(
        update_fields=[
            "status",
            "released_at",
        ]
    )

    return True
