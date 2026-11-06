
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import User, EmailVerification


MAX_VERIFICATION_ATTEMPTS = 5
VERIFICATION_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_EMAILS_PER_HOUR = 5


class EmailVerificationError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


def create_email_verification(user):
    now = timezone.now()

    with transaction.atomic():

        locked_user = User.objects.select_for_update().get(
            pk=user.pk
        )

        if locked_user.is_email_verified:
            raise EmailVerificationError(
                "Email is already verified."
            )

        latest = (
            EmailVerification.objects
            .filter(user=locked_user)
            .order_by("-created_at")
            .first()
        )

        if latest:
            elapsed = (
                now - latest.created_at
            ).total_seconds()

            if elapsed < RESEND_COOLDOWN_SECONDS:
                raise EmailVerificationError(
                    "Please wait before requesting another code."
                )

        recent_count = EmailVerification.objects.filter(
            user=locked_user,
            created_at__gte=now - timedelta(hours=1),
        ).count()

        if recent_count >= MAX_EMAILS_PER_HOUR:
            raise EmailVerificationError(
                "Too many verification emails. Try again later."
            )

        EmailVerification.objects.filter(
            user=locked_user,
            is_used=False,
        ).update(is_used=True)

        code = f"{secrets.randbelow(1_000_000):06d}"

        verification = EmailVerification.objects.create(
            user=locked_user,
            code_hash=make_password(code),
            expires_at=now + timedelta(
                minutes=VERIFICATION_EXPIRY_MINUTES
            ),
        )

    try:
        send_mail(
            subject="GlowCart email verification",
            message=(
                f"Your verification code is: {code}\n"
                "This code expires in 10 minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[locked_user.email],
            fail_silently=False,
        )

    except Exception as exc:
        raise EmailDeliveryError(
            "Unable to send verification email."
        ) from exc

    return verification


def verify_email_code(user, code):

    with transaction.atomic():

        locked_user = User.objects.select_for_update().get(
            pk=user.pk
        )

        if locked_user.is_email_verified:
            return False

        verification = (
            EmailVerification.objects
            .select_for_update()
            .filter(
                user=locked_user,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if verification is None:
            return False

        now = timezone.now()

        if verification.expires_at <= now:
            verification.is_used = True
            verification.save(update_fields=["is_used"])
            return False

        if verification.attempts >= MAX_VERIFICATION_ATTEMPTS:
            verification.is_used = True
            verification.save(update_fields=["is_used"])
            return False

        if not check_password(code, verification.code_hash):

            verification.attempts += 1

            if verification.attempts >= MAX_VERIFICATION_ATTEMPTS:
                verification.is_used = True

            verification.save(
                update_fields=["attempts", "is_used"]
            )

            return False

        verification.is_used = True
        verification.save(update_fields=["is_used"])

        locked_user.is_email_verified = True
        locked_user.save(
            update_fields=["is_email_verified"]
        )

        EmailVerification.objects.filter(
            user=locked_user,
            is_used=False,
        ).update(is_used=True)

        return True
