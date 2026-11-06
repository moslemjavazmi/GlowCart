
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Q
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


# =========================================================
# MONEY
# =========================================================

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


# =========================================================
# ORDER VALIDATION
# =========================================================

def get_editable_order(*, user, order_id):
    """
    Retrieve and lock an order that can still be modified.
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
            "order": "This order cannot be modified."
        })

    if order.inventory_released_at is not None:
        raise ValidationError({
            "order": "Inventory has already been released."
        })

    if order.expires_at and order.expires_at <= timezone.now():
        raise ValidationError({
            "order": "This order has expired."
        })

    return order


# =========================================================
# COUPON VALIDATION
# =========================================================

def validate_coupon(
    coupon,
    *,
    user,
    amount,
    exclude_reservation_id=None,
):
    """
    Validate coupon availability and usage limits.

    The Coupon row must already be locked by the caller.
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

    # Count active and consumed reservations.
    usage_queryset = CouponReservation.objects.filter(
        coupon=coupon,
    ).filter(
        Q(status=CouponReservation.Status.CONSUMED)
        | Q(
            status=CouponReservation.Status.ACTIVE,
            expires_at__gt=now,
        )
    )
    user_usage_queryset = usage_queryset.filter(
        user=user,
    )

    # Exclude the current reservation when revalidating
    # an already reserved coupon for the same order.
    if exclude_reservation_id is not None:

        usage_queryset = usage_queryset.exclude(
            id=exclude_reservation_id
        )

        user_usage_queryset = user_usage_queryset.exclude(
            id=exclude_reservation_id
        )

    usage_count = usage_queryset.count()

    if (
        coupon.usage_limit is not None
        and usage_count >= coupon.usage_limit
    ):
        raise ValidationError({
            "coupon": "This coupon has reached its usage limit."
        })

    user_usage_count = user_usage_queryset.count()

    if (
        coupon.usage_limit_per_user is not None
        and user_usage_count >= coupon.usage_limit_per_user
    ):
        raise ValidationError({
            "coupon": (
                "You have already used this coupon "
                "the maximum number of times."
            )
        })

    return calculate_coupon_discount(
        coupon,
        amount,
    )


# =========================================================
# RESERVE COUPON
# =========================================================

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

    Locking the Coupon row serializes concurrent reservations
    for the same coupon.
    """

    order = get_editable_order(
        user=user,
        order_id=order_id,
    )

    if not order.expires_at:
        raise ValidationError({
            "order": "Order expiration time is required."
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

    # Lock existing reservation if present.
    existing = (
        CouponReservation.objects
        .select_for_update()
        .filter(order=order)
        .first()
    )

    if existing:

        if existing.status == CouponReservation.Status.CONSUMED:
            raise ValidationError({
                "coupon": (
                    "A coupon has already been consumed "
                    "for this order."
                )
            })

        if (
            existing.status == CouponReservation.Status.ACTIVE
            and existing.coupon_id != coupon.id
        ):
            raise ValidationError({
                "coupon": (
                    "This order already has an active coupon. "
                    "Remove it before applying another coupon."
                )
            })

    discount = validate_coupon(
        coupon,
        user=user,
        amount=discountable_amount,
        exclude_reservation_id=(
            existing.id if existing else None
        ),
    )

    reservation_expiry = order.expires_at

    # Reactivate or update an existing reservation.
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

    # Create a new reservation.
    return CouponReservation.objects.create(
        coupon=coupon,
        order=order,
        user=user,
        discount_amount=discount,
        status=CouponReservation.Status.ACTIVE,
        expires_at=reservation_expiry,
    )


# =========================================================
# CONSUME COUPON
# =========================================================

@transaction.atomic
def consume_coupon_reservation(*, order_id):
    """
    Consume an active coupon reservation
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


# =========================================================
# RELEASE COUPON
# =========================================================

@transaction.atomic
def release_coupon_reservation(*, order_id):
    """
    Release an active coupon reservation
    when an order expires or is cancelled.
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


# =========================================================
# APPLY COUPON TO ORDER
# =========================================================

@transaction.atomic
def apply_coupon_to_order(*, code, user, order_id):
    """
    Apply a coupon to an existing editable order.
    """

    order = get_editable_order(
        user=user,
        order_id=order_id,
    )

    # Coupon discount is calculated against subtotal,
    # excluding shipping cost.
    reservation = reserve_coupon(
        code=code,
        user=user,
        order_id=order.id,
        discountable_amount=order.subtotal,
    )

    discount_amount = reservation.discount_amount

    total_amount = (
        order.subtotal
        + order.shipping_cost
        - discount_amount
    )

    if total_amount <= Decimal("0.00"):
        raise ValidationError({
            "coupon": "Invalid final order amount."
        })

    order.discount_amount = discount_amount
    order.total_amount = total_amount

    order.save(
        update_fields=[
            "discount_amount",
            "total_amount",
            "updated_at",
        ]
    )

    return order


# =========================================================
# REMOVE COUPON FROM ORDER
# =========================================================

@transaction.atomic
def remove_coupon_from_order(*, user, order_id):
    """
    Remove an active coupon and restore the original total.
    """

    order = get_editable_order(
        user=user,
        order_id=order_id,
    )

    reservation = (
        CouponReservation.objects
        .select_for_update()
        .filter(
            order=order,
            status=CouponReservation.Status.ACTIVE,
        )
        .first()
    )

    if reservation:

        reservation.status = CouponReservation.Status.RELEASED
        reservation.released_at = timezone.now()

        reservation.save(
            update_fields=[
                "status",
                "released_at",
            ]
        )

    order.discount_amount = Decimal("0.00")

    order.total_amount = (
        order.subtotal + order.shipping_cost
    )

    order.save(
        update_fields=[
            "discount_amount",
            "total_amount",
            "updated_at",
        ]
    )

    return order
