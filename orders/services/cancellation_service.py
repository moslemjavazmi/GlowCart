
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from orders.models import Order, InventoryReservation
from catalog.models import ProductVariant
from payments.models import Payment
from promotions.services.coupon_service import (
    release_coupon_reservation,
)


PROTECTED_PAYMENT_STATUSES = [
    Payment.Status.INITIATED,
    Payment.Status.PENDING,
    Payment.Status.UNKNOWN,
    Payment.Status.REVIEW_REQUIRED,
    Payment.Status.SUCCESS,
]


@transaction.atomic
def cancel_order(*, order_id, user):
    """
    Cancel an unpaid order and safely release its reservations.

    Lock order:
    Order -> Payment -> InventoryReservation -> ProductVariant
    -> CouponReservation
    """

    # 1. Lock and validate the order.
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

    if order.status == Order.Status.CANCELLED:
        return order

    if order.status != Order.Status.AWAITING_PAYMENT:
        raise ValidationError({
            "order": "This order cannot be cancelled."
        })

    if order.inventory_released_at is not None:
        raise ValidationError({
            "order": "Order inventory has already been released."
        })

    # 2. Lock payments and prevent cancellation
    # while a payment result is unresolved.
    payments = list(
        Payment.objects
        .select_for_update()
        .filter(order=order)
        .order_by("id")
    )

    if any(
        payment.status in PROTECTED_PAYMENT_STATUSES
        for payment in payments
    ):
        raise ValidationError({
            "payment": (
                "This order has a payment that is pending, "
                "successful, or requires reconciliation. "
                "The order cannot be cancelled yet."
            )
        })

    now = timezone.now()

    # 3. Lock active inventory reservations.
    reservations = list(
        InventoryReservation.objects
        .select_for_update()
        .filter(
            order=order,
            status=InventoryReservation.Status.ACTIVE,
        )
        .order_by("variant_id")
    )

    # 4. Lock all affected variants in deterministic order.
    variant_ids = sorted({
        reservation.variant_id
        for reservation in reservations
    })

    variants = {
        variant.id: variant
        for variant in (
            ProductVariant.objects
            .select_for_update()
            .filter(id__in=variant_ids)
            .order_by("id")
        )
    }

    # 5. Restore inventory and release reservations.
    for reservation in reservations:
        variant = variants.get(reservation.variant_id)

        if variant is None:
            raise ValidationError({
                "inventory": (
                    "A reserved product variant no longer exists."
                )
            })

        ProductVariant.objects.filter(
            id=variant.id
        ).update(
            stock=F("stock") + reservation.quantity
        )

        reservation.status = InventoryReservation.Status.RELEASED
        reservation.released_at = now

        reservation.save(
            update_fields=[
                "status",
                "released_at",
            ]
        )

    # 6. Release coupon reservation.
    release_coupon_reservation(order_id=order.id)

    # 7. Cancel the order.
    order.status = Order.Status.CANCELLED
    order.inventory_released_at = now

    order.save(
        update_fields=[
            "status",
            "inventory_released_at",
            "updated_at",
        ]
    )

    return order
