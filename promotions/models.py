
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

from orders.models import Order


class Coupon(models.Model):

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )

    # For percentage: 10 means 10%
    # For fixed: amount in the same currency as Order.total_amount
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    max_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    usage_limit_per_user = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(value__gt=0),
                name="coupon_value_positive",
            ),
            models.CheckConstraint(
                condition=Q(min_order_amount__gte=0),
                name="coupon_min_order_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discount_type="percentage", value__lte=100)
                    | Q(discount_type="fixed")
                ),
                name="coupon_percentage_max_100",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("starts_at")),
                name="coupon_expiry_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(max_discount__isnull=True)
                    | Q(max_discount__gte=0)
                ),
                name="coupon_max_discount_non_negative",
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class CouponReservation(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONSUMED = "consumed", "Consumed"
        RELEASED = "released", "Released"

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="coupon_reservation",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_reservations",
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    expires_at = models.DateTimeField()

    consumed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["coupon", "status"],
            ),
            models.Index(
                fields=["user", "status"],
            ),
            models.Index(
                fields=["status", "expires_at"],
            ),
        ]

    def __str__(self):
        return f"{self.coupon.code} - {self.order.order_number}"
