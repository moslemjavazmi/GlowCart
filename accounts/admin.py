from django.contrib import admin

from accounts.models import EmailVerification


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "expires_at",
        "is_used",
        "created_at",
    )

    list_filter = ("is_used", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("code_hash", "created_at")