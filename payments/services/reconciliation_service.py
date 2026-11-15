from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from payments.models import Payment
from payments.gateways.factory import get_payment_gateway

from payments.services.payment_service import (
    finalize_verified_payment,
    _mark_payment_failed,
    _mark_payment_review_required,
    _store_verification_result,
    _adopt_early_callback_authority,
)


INITIATED_STALE_AFTER = timedelta(
    seconds=max(
        1,
        getattr(
            settings,
            "PAYMENT_INITIATED_STALE_AFTER_SECONDS",
            300,
        ),
    )
)


# =========================================================
# Reconcile Single Payment
# =========================================================

def reconcile_payment(payment_id):

    payment = Payment.objects.get(id=payment_id)

# Recover an authority received through an early callback.
    if (
        payment.status in [
            Payment.Status.INITIATED,
            Payment.Status.UNKNOWN,
        ]
        and not payment.authority
        and payment.callback_authority
    ):
        payment = _adopt_early_callback_authority(
            payment.id
        )

    # -----------------------------------------------------
    # STEP 1: Check final states
    # -----------------------------------------------------

    if payment.status in [
        Payment.Status.SUCCESS,
        Payment.Status.FAILED,
        Payment.Status.CANCELLED,
        Payment.Status.REVIEW_REQUIRED,
    ]:
        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "already_final",
        }

    # -----------------------------------------------------
    # STEP 2: Handle stale INITIATED payments
    # -----------------------------------------------------

    if payment.status == Payment.Status.INITIATED:

        stale_before = timezone.now() - INITIATED_STALE_AFTER

        if payment.created_at > stale_before:
            return {
                "payment_id": str(payment.id),
                "status": payment.status,
                "result": "waiting_for_gateway_response",
            }

        reviewed_payment = _mark_payment_review_required(
            payment.id,
            reason="stale_initiated_payment",
        )

        return {
            "payment_id": str(payment.id),
            "status": reviewed_payment.status,
            "result": "manual_review_required",
            "reason": "stale_initiated_payment",
        }

    # -----------------------------------------------------
    # STEP 3: Validate status
    # -----------------------------------------------------

    if payment.status not in [
        Payment.Status.PENDING,
        Payment.Status.UNKNOWN,
    ]:
        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "unsupported_status",
        }

    # -----------------------------------------------------
    # STEP 4: Validate authority
    # -----------------------------------------------------

    if not payment.authority:

        reviewed_payment = _mark_payment_review_required(
            payment.id,
            reason="missing_authority",
        )

        return {
            "payment_id": str(payment.id),
            "status": reviewed_payment.status,
            "result": "manual_review_required",
            "reason": "missing_authority",
        }

    # -----------------------------------------------------
    # STEP 5: Verify with gateway
    # -----------------------------------------------------

    try:

        gateway = get_payment_gateway(
            payment.provider
        )

        result = gateway.verify_payment(
            authority=payment.authority,
            amount=payment.amount,
        )

    except Exception as exc:

        current_payment = Payment.objects.get(
            id=payment.id
        )

        return {
            "payment_id": str(payment.id),
            "status": current_payment.status,
            "result": "gateway_error",
            "error": str(exc)[:500],
        }

    # -----------------------------------------------------
    # STEP 6: Successful payment
    # -----------------------------------------------------

    if result.get("success") is True:

        finalized_payment = finalize_verified_payment(
            payment.id,
            result,
        )

        return {
            "payment_id": str(payment.id),
            "status": finalized_payment.status,
            "result": (
                "verified"
                if finalized_payment.status == Payment.Status.SUCCESS
                else "manual_review_required"
            ),
            "reason": finalized_payment.review_reason,
        }

    # -----------------------------------------------------
    # STEP 7: Definitive failure
    # -----------------------------------------------------

    if result.get("definitive_failure") is True:

        failed_payment = _mark_payment_failed(
            payment.id,
            result,
        )

        return {
            "payment_id": str(payment.id),
            "status": failed_payment.status,
            "result": (
                "definitive_failure"
                if failed_payment.status == Payment.Status.FAILED
                else "state_changed"
            ),
        }

    # -----------------------------------------------------
    # STEP 8: Ambiguous result
    # -----------------------------------------------------

    current_payment = _store_verification_result(
        payment.id,
        result,
    )

    return {
        "payment_id": str(payment.id),
        "status": current_payment.status,
        "result": "still_unresolved",
    }


# =========================================================
# Reconcile Unresolved Payments
# =========================================================

def reconcile_unresolved_payments(limit=100):

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
    ):
        raise ValueError(
            "limit must be a positive integer."
        )

    now = timezone.now()

    stale_before = now - INITIATED_STALE_AFTER

    payment_ids = list(
        Payment.objects.filter(
            Q(
                status__in=[
                    Payment.Status.PENDING,
                    Payment.Status.UNKNOWN,
                ]
            )
            | Q(
                status=Payment.Status.INITIATED,
                created_at__lte=stale_before,
            )
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )

    results = []

    for payment_id in payment_ids:

        try:

            results.append(
                reconcile_payment(payment_id)
            )

        except Payment.DoesNotExist:
            continue

        except Exception as exc:

            results.append({
                "payment_id": str(payment_id),
                "result": "error",
                "error": str(exc)[:500],
            })

    return {
        "checked": len(payment_ids),
        "results": results,
        "checked_at": timezone.now().isoformat(),
    }