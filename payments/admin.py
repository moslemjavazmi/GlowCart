from django.contrib import admin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "provider",
        "status",
        "amount",
        "provider_reference",
        "review_reason",
        "created_at",
    )

    list_filter = (
        "status",
        "provider",
        "created_at",
    )

    search_fields = (
        "id",
        "order__order_number",
        "authority",
        "provider_reference",
    )

    readonly_fields = (
        "id",
        "order",
        "provider",
        "status",
        "amount",
        "authority",
        "payment_url",
        "provider_reference",
        "idempotency_key",
        "gateway_response",
        "paid_at",
        "review_reason",
        "callback_authority",
        "callback_status",
        "callback_received_at",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def get_queryset(self, request):

        return (
            super()
            .get_queryset(request)
            .select_related(
                "order",
                "order__user",
            )
        )