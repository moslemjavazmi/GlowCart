from django.utils import timezone

from orders.models import Order
from orders.services.inventory_service import release_order_inventory


def expire_pending_orders():
    now = timezone.now()

    expired_order_ids = list(
        Order.objects.filter(
            status=Order.Status.AWAITING_PAYMENT,
            expires_at__lte=now,
            inventory_released_at__isnull=True,
        ).values_list("id", flat=True)
    )

    results = {
        "checked": len(expired_order_ids),
        "expired": 0,
    }

    for order_id in expired_order_ids:
        released = release_order_inventory(order_id)

        if released:
            results["expired"] += 1

    return results