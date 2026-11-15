
from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from orders.models import (
    Order,
    InventoryReservation,
)
from orders.services.order_service import create_order
from orders.services.cancellation_service import cancel_order
from orders.services.inventory_service import release_order_inventory

from payments.models import Payment
from promotions.models import CouponReservation

from .factories import (
    create_checkout_context,
    create_coupon,
)


class OrderCancellationTests(TestCase):

    def setUp(self):
        self.context = create_checkout_context(
            quantity=3,
            stock=10,
        )

        self.order, _ = create_order(
            user=self.context["user"],
            address_id=self.context["address"].id,
            idempotency_key=uuid4(),
        )

    def create_payment(self, status):
        return Payment.objects.create(
            order=self.order,
            provider=Payment.Provider.ZARINPAL,
            status=status,
            amount=self.order.total_amount,
        )

    def test_cancel_order_restores_inventory(self):
        variant = self.context["variant"]

        self.assertEqual(variant.stock, 10)

        order = cancel_order(
            order_id=self.order.id,
            user=self.context["user"],
        )

        variant.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(variant.stock, 10)
        self.assertIsNotNone(order.inventory_released_at)

        reservation = InventoryReservation.objects.get(
            order=order,
            variant=variant,
        )

        self.assertEqual(
            reservation.status,
            InventoryReservation.Status.RELEASED,
        )

    def test_cancel_order_is_idempotent(self):
        variant = self.context["variant"]

        first = cancel_order(
            order_id=self.order.id,
            user=self.context["user"],
        )

        second = cancel_order(
            order_id=self.order.id,
            user=self.context["user"],
        )

        initial_stock = variant.stock

        self.assertEqual(first.id, second.id)
        self.assertEqual(variant.stock, initial_stock)

    def test_another_user_cannot_cancel_order(self):
        from .factories import create_user

        another_user = create_user()

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=another_user,
            )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.AWAITING_PAYMENT,
        )

    def test_paid_order_cannot_be_cancelled(self):
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

    def test_pending_payment_prevents_cancellation(self):
        self.create_payment(Payment.Status.PENDING)

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

    def test_unknown_payment_prevents_cancellation(self):
        self.create_payment(Payment.Status.UNKNOWN)

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

    def test_review_required_payment_prevents_cancellation(self):
        self.create_payment(Payment.Status.REVIEW_REQUIRED)

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

    def test_successful_payment_prevents_cancellation(self):
        self.create_payment(Payment.Status.SUCCESS)

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

    def test_failed_payment_allows_cancellation(self):
        self.create_payment(Payment.Status.FAILED)

        order = cancel_order(
            order_id=self.order.id,
            user=self.context["user"],
        )

        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_expired_order_cannot_be_cancelled_after_inventory_release(self):
        self.order.expires_at = timezone.now() - timedelta(minutes=1)
        self.order.save(update_fields=["expires_at"])

        release_order_inventory(self.order.id)

        with self.assertRaises(ValidationError):
            cancel_order(
                order_id=self.order.id,
                user=self.context["user"],
            )

        self.order.refresh_from_db()

        self.assertEqual(self.order.status, Order.Status.EXPIRED)

    def test_cancellation_releases_coupon_reservation(self):
        # Create a separate checkout with a coupon.
        coupon_context = create_checkout_context(
            quantity=2,
            stock=10,
        )
        coupon = create_coupon(value=10)

        order, _ = create_order(
            user=coupon_context["user"],
            address_id=coupon_context["address"].id,
            coupon_code=coupon.code,
            idempotency_key=uuid4(),
        )

        reservation = CouponReservation.objects.get(order=order)

        self.assertEqual(
            reservation.status,
            CouponReservation.Status.ACTIVE,
        )

        cancel_order(
            order_id=order.id,
            user=coupon_context["user"],
        )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            CouponReservation.Status.RELEASED,
        )
        self.assertIsNotNone(reservation.released_at)
