import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import EmailVerification


def create_email_verification(user):
    # Invalidate previous unused codes
    EmailVerification.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)

    code = f"{secrets.randbelow(1_000_000):06d}"

    verification = EmailVerification.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    send_mail(
        subject="GlowCart email verification",
        message=(
            f"Your verification code is: {code}\n"
            "This code expires in 10 minutes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return verification


def verify_email_code(user, code):
    from django.contrib.auth.hashers import check_password

    verification = (
        EmailVerification.objects
        .filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )

    if verification is None:
        return False

    if not check_password(code, verification.code_hash):
        return False

    verification.is_used = True
    verification.save(update_fields=["is_used"])

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])

    return True