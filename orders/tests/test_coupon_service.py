
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from orders.models import Order
from orders.services.order_service import create_order

from promotions.models import Coupon, CouponReservation
from promotions.services.coupon_service import (
    calculate_coupon_discount,
    apply_coupon_to_order,
    remove_coupon_from_order,
    consume_coupon_reservation,
    release_coupon_reservation,
)

from .factories import (
    create_checkout_context,
    create_coupon,
    create_user,
)


class CouponServiceTests(TestCase):

    def setUp(self):
        self.context = create_checkout_context(
            quantity=2,
            price=Decimal("250000.00"),
            stock=10,
        )

    def create_order(self, coupon_code=None):
        return create_order(
            user=self.context["user"],
            address_id=self.context["address"].id,
            coupon_code=coupon_code,
            idempotency_key=uuid4(),
        )[0]

    def test_percentage_discount_calculation(self):
        coupon = create_coupon(
            discount_type=Coupon.DiscountType.PERCENTAGE,
            value=10,
        )

        discount = calculate_coupon_discount(
            coupon,
            Decimal("500000.00"),
        )

        self.assertEqual(discount, Decimal("50000.00"))

    def test_percentage_discount_respects_max_discount(self):
        coupon = create_coupon(
            value=20,
            max_discount=Decimal("30000.00"),
        )

        discount = calculate_coupon_discount(
            coupon,
            Decimal("500000.00"),
        )

        self.assertEqual(discount, Decimal("30000.00"))

    def test_fixed_discount_calculation(self):
        coupon = create_coupon(
            discount_type=Coupon.DiscountType.FIXED,
            value=Decimal("40000.00"),
        )

        discount = calculate_coupon_discount(
            coupon,
            Decimal("500000.00"),
        )

        self.assertEqual(discount, Decimal("40000.00"))

    def test_discount_never_exceeds_order_amount(self):
        coupon = create_coupon(
            discount_type=Coupon.DiscountType.FIXED,
            value=Decimal("900000.00"),
        )

        discount = calculate_coupon_discount(
            coupon,
            Decimal("500000.00"),
        )

        self.assertEqual(discount, Decimal("500000.00"))

    def test_zero_eligible_amount_is_rejected(self):
        coupon = create_coupon()

        with self.assertRaises(ValidationError):
            calculate_coupon_discount(
                coupon,
                Decimal("0.00"),
            )

    def test_create_order_with_coupon(self):
        coupon = create_coupon(value=10)

        order = self.create_order(coupon.code)

        self.assertEqual(
            order.discount_amount,
            Decimal("50000.00"),
        )
        self.assertEqual(
            order.total_amount,
            Decimal("450000.00"),
        )

        reservation = CouponReservation.objects.get(order=order)

        self.assertEqual(
            reservation.status,
            CouponReservation.Status.ACTIVE,
        )

    def test_invalid_coupon_rolls_back_order(self):
        with self.assertRaises(ValidationError):
            self.create_order("INVALID-CODE")

        self.assertFalse(Order.objects.exists())

        self.assertTrue(
            self.context["cart"].items.exists()
        )

        self.context["variant"].refresh_from_db()

        self.assertEqual(
            self.context["variant"].stock,
            10,
        )

    def test_inactive_coupon_is_rejected(self):
        coupon = create_coupon(is_active=False)

        with self.assertRaises(ValidationError):
            self.create_order(coupon.code)

        self.assertFalse(Order.objects.exists())

    def test_expired_coupon_is_rejected(self):
        from datetime import timedelta

        coupon = create_coupon(
            starts_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            self.create_order(coupon.code)

        self.assertFalse(Order.objects.exists())

    def test_coupon_minimum_amount_is_enforced(self):
        coupon = create_coupon(
            value=10,
            min_order_amount=Decimal("600000.00"),
        )

        with self.assertRaises(ValidationError):
            self.create_order(coupon.code)

        self.assertFalse(Order.objects.exists())

    def test_coupon_usage_limit_is_enforced(self):
        coupon = create_coupon(
            value=10,
            usage_limit=1,
        )

        first_order = self.create_order(coupon.code)

        second_context = create_checkout_context(
            stock=10,
        )

        with self.assertRaises(ValidationError):
            create_order(
                user=second_context["user"],
                address_id=second_context["address"].id,
                coupon_code=coupon.code,
                idempotency_key=uuid4(),
            )

        self.assertEqual(Order.objects.count(), 1)

    def test_coupon_per_user_usage_limit_is_enforced(self):
        coupon = create_coupon(
            value=10,
            usage_limit_per_user=1,
        )

        self.create_order(coupon.code)

        # A second order by the same user.
        from .factories import add_cart_item

        add_cart_item(
            self.context["cart"],
            self.context["variant"],
            quantity=1,
        )

        with self.assertRaises(ValidationError):
            self.create_order(coupon.code)

        self.assertEqual(Order.objects.count(), 1)

    def test_consume_coupon_reservation(self):
        coupon = create_coupon(value=10)
        order = self.create_order(coupon.code)

        result = consume_coupon_reservation(order_id=order.id)

        reservation = CouponReservation.objects.get(order=order)

        self.assertTrue(result)
        self.assertEqual(
            reservation.status,
            CouponReservation.Status.CONSUMED,
        )
        self.assertIsNotNone(reservation.consumed_at)

    def test_release_coupon_reservation(self):
        coupon = create_coupon(value=10)
        order = self.create_order(coupon.code)

        result = release_coupon_reservation(order_id=order.id)

        reservation = CouponReservation.objects.get(order=order)

        self.assertTrue(result)
        self.assertEqual(
            reservation.status,
            CouponReservation.Status.RELEASED,
        )
        self.assertIsNotNone(reservation.released_at)

    def test_remove_coupon_restores_order_total(self):
        coupon = create_coupon(value=10)
        order = self.create_order(coupon.code)

        updated_order = remove_coupon_from_order(
            user=self.context["user"],
            order_id=order.id,
        )

        reservation = CouponReservation.objects.get(order=order)

        self.assertEqual(
            updated_order.discount_amount,
            Decimal("0.00"),
        )
        self.assertEqual(
            updated_order.total_amount,
            updated_order.subtotal + updated_order.shipping_cost,
        )
        self.assertEqual(
            reservation.status,
            CouponReservation.Status.RELEASED,
        )

    def test_apply_coupon_to_existing_order(self):
        order = self.create_order()

        coupon = create_coupon(value=10)

        updated_order = apply_coupon_to_order(
            code=coupon.code,
            user=self.context["user"],
            order_id=order.id,
        )

        self.assertEqual(
            updated_order.discount_amount,
            Decimal("50000.00"),
        )
        self.assertEqual(
            updated_order.total_amount,
            Decimal("450000.00"),
        )

    def test_coupon_cannot_be_applied_to_another_users_order(self):
        order = self.create_order()
        another_user = create_user()
        coupon = create_coupon(value=10)

        with self.assertRaises(ValidationError):
            apply_coupon_to_order(
                code=coupon.code,
                user=another_user,
                order_id=order.id,
            )
