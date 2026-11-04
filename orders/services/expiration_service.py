
from django.utils import timezone

from orders.models import Order
from orders.services.inventory_service import release_order_inventory


def expire_pending_orders():
    """
    Find expired orders and release their inventory
    when payment state allows it.
    """

    now = timezone.now()

    expired_order_ids = list(
        Order.objects.filter(
            status=Order.Status.AWAITING_PAYMENT,
            expires_at__isnull=False,
            expires_at__lte=now,
            inventory_released_at__isnull=True,
        ).values_list("id", flat=True)
    )

    released_count = 0
    skipped_count = 0

    for order_id in expired_order_ids:
        released = release_order_inventory(order_id)

        if released:
            released_count += 1
        else:
            skipped_count += 1

    return {
        "checked": len(expired_order_ids),
        "released": released_count,
        "skipped": skipped_count,
    }
