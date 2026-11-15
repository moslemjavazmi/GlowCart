
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from orders.models import (
    Order,
    InventoryReservation,
)
from orders.services.order_service import create_order
from orders.services.inventory_service import release_order_inventory

from .factories import create_checkout_context


class InventoryReleaseTests(TestCase):

    def setUp(self):
        self.context = create_checkout_context(
            quantity=3,
            stock=10,
        )

        self.order, _ = create_order(
            user=self.context["user"],
            address_id=self.context["address"].id,
            idempotency_key=__import__("uuid").uuid4(),
        )

    def expire_order(self):
        self.order.expires_at = (
            timezone.now() - timedelta(minutes=1)
        )
        self.order.save(update_fields=["expires_at"])

    def test_expired_order_releases_inventory(self):
        variant = self.context["variant"]
        self.expire_order()

        result = release_order_inventory(self.order.id)

        self.assertTrue(result)

        variant.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(variant.stock, 10)
        self.assertEqual(
            self.order.status,
            Order.Status.EXPIRED,
        )
        self.assertIsNotNone(
            self.order.inventory_released_at
        )

        reservation = InventoryReservation.objects.get(
            order=self.order,
            variant=variant,
        )

        self.assertEqual(
            reservation.status,
            InventoryReservation.Status.RELEASED,
        )
        self.assertIsNotNone(reservation.released_at)

    def test_inventory_cannot_be_released_twice(self):
        variant = self.context["variant"]
        self.expire_order()

        first_result = release_order_inventory(
            self.order.id
        )
        second_result = release_order_inventory(
            self.order.id
        )

        variant.refresh_from_db()

        self.assertTrue(first_result)
        self.assertFalse(second_result)

        # Stock must not be restored twice.
        self.assertEqual(variant.stock, 10)

    def test_unexpired_order_does_not_release_inventory(self):
        variant = self.context["variant"]

        result = release_order_inventory(self.order.id)

        variant.refresh_from_db()
        self.order.refresh_from_db()

        self.assertFalse(result)
        self.assertEqual(variant.stock, 7)
        self.assertEqual(
            self.order.status,
            Order.Status.AWAITING_PAYMENT,
        )

    def test_already_released_order_does_not_release_again(self):
        variant = self.context["variant"]
        self.expire_order()

        release_order_inventory(self.order.id)

        result = release_order_inventory(self.order.id)

        variant.refresh_from_db()

        self.assertFalse(result)
        self.assertEqual(variant.stock, 10)

    def test_nonexistent_order_returns_false(self):
        import uuid

        result = release_order_inventory(uuid.uuid4())

        self.assertFalse(result)
