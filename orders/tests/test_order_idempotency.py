
from uuid import uuid4

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from orders.models import Order
from orders.services.order_service import create_order

from .factories import (
    create_checkout_context,
    create_address,
)
from .factories import add_cart_item


class OrderIdempotencyTests(TestCase):

    def setUp(self):
        self.context = create_checkout_context()
        self.idempotency_key = uuid4()

    def checkout(self, context, key, **kwargs):
        return create_order(
            user=context["user"],
            address_id=context["address"].id,
            idempotency_key=key,
            **kwargs,
        )

    def test_same_key_returns_existing_order(self):
        first_order, first_created = self.checkout(
            self.context,
            self.idempotency_key,
        )

        second_order, second_created = self.checkout(
            self.context,
            self.idempotency_key,
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(first_order.id, second_order.id)
        self.assertEqual(Order.objects.count(), 1)

    def test_same_key_does_not_reserve_stock_twice(self):
        variant = self.context["variant"]

        self.checkout(
            self.context,
            self.idempotency_key,
        )

        self.checkout(
            self.context,
            self.idempotency_key,
        )

        variant.refresh_from_db()

        self.assertEqual(
            variant.stock,
            18,
        )

    def test_same_key_with_different_address_is_rejected(self):
        first_order, _ = self.checkout(
            self.context,
            self.idempotency_key,
        )

        another_address = create_address(
            self.context["user"],
            is_default=False,
        )

        with self.assertRaises(ValidationError):
            create_order(
                user=self.context["user"],
                address_id=another_address.id,
                idempotency_key=self.idempotency_key,
            )

        self.assertEqual(Order.objects.count(), 1)

        first_order.refresh_from_db()

    def test_same_key_cannot_be_used_by_another_user(self):
        from .factories import create_user

        another_user = create_user()

        another_context = create_checkout_context(
            user=another_user,
        )

        self.checkout(
            self.context,
            self.idempotency_key,
        )

        with self.assertRaises(ValidationError):
            self.checkout(
                another_context,
                self.idempotency_key,
            )

        self.assertEqual(Order.objects.count(), 1)

    def test_different_keys_create_different_orders(self):

        first_order, first_created = self.checkout(
            self.context,
            uuid4(),
        )

        add_cart_item(
            self.context["cart"],
            self.context["variant"],
            quantity=1,
        )

        second_order, second_created = self.checkout(
            self.context,
            uuid4(),
        )

        self.assertTrue(first_created)
        self.assertTrue(second_created)
        self.assertNotEqual(first_order.id, second_order.id)
        self.assertEqual(Order.objects.count(), 2)