
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from payments.models import Payment

from orders.models import (
    Order,
    InventoryReservation,
    ProductVariant,
)

from promotions.services.coupon_service import (
    release_coupon_reservation,
)


@transaction.atomic
def release_order_inventory(order_id):

    # -----------------------------------------------------
    # STEP 1: Lock order
    # -----------------------------------------------------

    order = (
        Order.objects
        .select_for_update()
        .filter(id=order_id)
        .first()
    )

    if not order:
        return False

    if order.status != Order.Status.AWAITING_PAYMENT:
        return False

    if order.inventory_released_at is not None:
        return False

    now = timezone.now()

    if order.expires_at and order.expires_at > now:
        return False

    # -----------------------------------------------------
    # STEP 2: Check uncertain payments
    # -----------------------------------------------------


    protected_payment_statuses = [
            Payment.Status.INITIATED,
            Payment.Status.PENDING,
            Payment.Status.UNKNOWN,
            Payment.Status.REVIEW_REQUIRED,
            Payment.Status.SUCCESS,
        ]

    has_protected_payment = Payment.objects.filter(
        order=order,
        status__in=protected_payment_statuses,
    ).exists()

    if has_protected_payment:
        return False

    # -----------------------------------------------------
    # STEP 3: Lock active reservations
    # -----------------------------------------------------

    reservations = list(
        InventoryReservation.objects
        .select_for_update()
        .filter(
            order=order,
            status=InventoryReservation.Status.ACTIVE,
        )
    )

    # -----------------------------------------------------
    # STEP 4: Restore inventory
    # -----------------------------------------------------

    for reservation in reservations:

        variant = (
            ProductVariant.objects
            .select_for_update()
            .get(id=reservation.variant_id)
        )

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

    # -----------------------------------------------------
    # STEP 5: Release coupon reservation
    # -----------------------------------------------------

    release_coupon_reservation(order_id=order.id)

    # -----------------------------------------------------
    # STEP 6: Expire order
    # -----------------------------------------------------

    order.status = Order.Status.EXPIRED
    order.inventory_released_at = now

    order.save(
        update_fields=[
            "status",
            "inventory_released_at",
            "updated_at",
        ]
    )

    return True
