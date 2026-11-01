
import uuid

from django.db import models

from orders.models import Order


class Payment(models.Model):

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        UNKNOWN = "unknown", "Unknown"

    class Provider(models.TextChoices):
        ZARINPAL = "zarinpal", "Zarinpal"
        IDPAY = "idpay", "IDPay"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # شناسه‌ای که درگاه برای تراکنش برمی‌گرداند.
    authority = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    payment_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
    )

    # شماره پیگیری نهایی تراکنش درگاه.
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # جلوگیری از ایجاد چند Payment برای یک درخواست تکراری.
    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # اطلاعات فنی پاسخ درگاه؛ بدون اطلاعات حساس کارت.
    gateway_response = models.JSONField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["provider", "authority"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "authority"],
                condition=~models.Q(authority__isnull=True),
                name="unique_provider_authority",
            ),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"
