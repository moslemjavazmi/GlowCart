from django.db import transaction
from django.utils import timezone

from orders.models import (
    Order,
    InventoryReservation,
)


@transaction.atomic
def release_order_inventory(order_id):
    order = (
        Order.objects
        .select_for_update()
        .get(id=order_id)
    )

    # سفارش پرداخت‌شده یا سفارش منقضی‌شده را دوباره آزاد نکن
    if order.status != Order.Status.AWAITING_PAYMENT:
        return False

    if order.inventory_released_at is not None:
        return False

    reservations = list(
        InventoryReservation.objects
        .select_for_update()
        .filter(
            order=order,
            status=InventoryReservation.Status.ACTIVE,
        )
        .select_related("variant")
    )

    for reservation in reservations:
        variant = reservation.variant

        variant.stock += reservation.quantity
        variant.save(update_fields=["stock"])

        reservation.status = InventoryReservation.Status.RELEASED
        reservation.released_at = timezone.now()
        reservation.save(
            update_fields=["status", "released_at"]
        )

    now = timezone.now()

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