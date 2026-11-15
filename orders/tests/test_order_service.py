
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from orders.models import (
    Order,
    OrderItem,
    InventoryReservation,
)
from orders.services.order_service import create_order

from .factories import create_checkout_context


class CreateOrderServiceTests(TestCase):

    def setUp(self):
        self.context = create_checkout_context(
            quantity=2,
            price=Decimal("250000.00"),
            stock=10,
        )

    def create_order(self, **kwargs):
        return create_order(
            user=self.context["user"],
            address_id=self.context["address"].id,
            idempotency_key=uuid4(),
            **kwargs,
        )

    def test_create_order_successfully(self):
        order, created = self.create_order()

        self.assertTrue(created)
        self.assertEqual(order.status, Order.Status.AWAITING_PAYMENT)

        self.assertEqual(
            order.subtotal,
            Decimal("500000.00"),
        )

        self.assertEqual(
            order.total_amount,
            Decimal("500000.00"),
        )

        self.assertEqual(order.items.count(), 1)

        item = order.items.get()

        self.assertEqual(item.quantity, 2)
        self.assertEqual(
            item.unit_price,
            Decimal("250000.00"),
        )
        self.assertEqual(
            item.line_total,
            Decimal("500000.00"),
        )

    def test_order_stores_product_snapshots(self):
        product = self.context["product"]
        variant = self.context["variant"]

        order, _ = self.create_order()

        item = order.items.get()

        self.assertEqual(item.product_name, product.name)
        self.assertEqual(item.variant_name, variant.name)
        self.assertEqual(item.sku, variant.sku)

        # Changing the original product must not change
        # the historical order item.
        product.name = "Updated Product Name"
        product.save(update_fields=["name"])

        item.refresh_from_db()

        self.assertNotEqual(
            item.product_name,
            product.name,
        )

    def test_order_stores_address_snapshot(self):
        address = self.context["address"]

        order, _ = self.create_order()

        self.assertEqual(
            order.recipient_name,
            address.recipient_name,
        )
        self.assertEqual(order.city, address.city)
        self.assertEqual(
            order.address_line,
            address.address_line,
        )

        address.address_line = "New address"
        address.save(update_fields=["address_line"])

        order.refresh_from_db()

        self.assertNotEqual(
            order.address_line,
            address.address_line,
        )

    def test_order_reduces_product_stock(self):
        variant = self.context["variant"]

        order, _ = self.create_order()

        variant.refresh_from_db()

        self.assertEqual(variant.stock, 8)

        reservation = InventoryReservation.objects.get(
            order=order,
            variant=variant,
        )

        self.assertEqual(reservation.quantity, 2)
        self.assertEqual(
            reservation.status,
            InventoryReservation.Status.ACTIVE,
        )

    def test_order_clears_cart_after_success(self):
        self.create_order()

        self.assertFalse(
            self.context["cart"].items.exists()
        )

    def test_empty_cart_cannot_create_order(self):
        self.context["cart"].items.all().delete()

        with self.assertRaises(ValidationError):
            self.create_order()

    def test_insufficient_stock_cannot_create_order(self):
        variant = self.context["variant"]
        variant.stock = 1
        variant.save(update_fields=["stock"])

        with self.assertRaises(ValidationError):
            self.create_order()

        variant.refresh_from_db()

        self.assertEqual(variant.stock, 1)

        self.assertFalse(Order.objects.exists())

    def test_inactive_product_cannot_be_ordered(self):
        product = self.context["product"]
        product.is_active = False
        product.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.create_order()

        self.assertFalse(Order.objects.exists())

    def test_inactive_variant_cannot_be_ordered(self):
        variant = self.context["variant"]
        variant.is_active = False
        variant.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.create_order()

        self.assertFalse(Order.objects.exists())

    def test_order_creation_is_atomic(self):
        """
        A failed checkout must not partially reserve stock,
        create an order, or delete cart items.
        """
        variant = self.context["variant"]
        variant.stock = 1
        variant.save(update_fields=["stock"])

        with self.assertRaises(ValidationError):
            self.create_order()

        self.assertFalse(Order.objects.exists())
        self.assertTrue(self.context["cart"].items.exists())

        variant.refresh_from_db()
        self.assertEqual(variant.stock, 1)

        self.assertFalse(
            InventoryReservation.objects.exists()
        )
