from django.db import transaction
from django.utils import timezone

from payments.models import Payment
from payments.gateways.factory import get_payment_gateway
from payments.gateways.zarinpal import ZarinpalGatewayError

from payments.services.payment_service import (
    finalize_verified_payment,
)


def reconcile_payment(payment_id):

    payment = (
        Payment.objects
        .select_related("order")
        .get(id=payment_id)
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

    if payment.status == Payment.Status.INITIATED:
        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "manual_review_required",
            "reason": "missing_confirmation_from_gateway",
        }

    if payment.status not in [
        Payment.Status.PENDING,
        Payment.Status.UNKNOWN,
    ]:
        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "unsupported_status",
        }

    if not payment.authority:
        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "manual_review_required",
            "reason": "missing_authority",
        }

    # -----------------------------------------------------
    # STEP 2: Verify with gateway
    # -----------------------------------------------------

    try:

        gateway = get_payment_gateway(payment.provider)

        result = gateway.verify_payment(
            authority=payment.authority,
            amount=payment.amount,
        )

    except ZarinpalGatewayError as exc:

        payment.refresh_from_db(
            fields=["status"]
        )

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "gateway_error",
            "error": str(exc)[:500],
        }

    except Exception as exc:

        payment.refresh_from_db(
            fields=["status"]
        )

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "result": "unexpected_error",
            "error": str(exc)[:500],
        }

    # -----------------------------------------------------
    # STEP 3: Successful payment
    # -----------------------------------------------------

    if result.get("success") is True:

        finalized_payment = finalize_verified_payment(
            payment.id,
            result,
        )

        return {
            "payment_id": str(payment.id),
            "status": finalized_payment.status,
            "result": "verified",
        }

    # -----------------------------------------------------
    # STEP 4: Definitive failure
    # -----------------------------------------------------

    if result.get("definitive_failure") is True:

        with transaction.atomic():

            locked_payment = (
                Payment.objects
                .select_for_update()
                .get(id=payment.id)
            )

            if locked_payment.status in [
                Payment.Status.PENDING,
                Payment.Status.UNKNOWN,
            ]:

                locked_payment.status = Payment.Status.FAILED

                locked_payment.gateway_response = (
                    result.get("raw_response") or {}
                )

                locked_payment.save(
                    update_fields=[
                        "status",
                        "gateway_response",
                        "updated_at",
                    ]
                )

        return {
            "payment_id": str(payment.id),
            "status": locked_payment.status,
            "result": (
                "definitive_failure"
                if locked_payment.status == Payment.Status.FAILED
                else "state_changed"
            ),
        }

    # -----------------------------------------------------
    # STEP 5: Ambiguous result
    # -----------------------------------------------------

    current_payment = Payment.objects.get(
        id=payment.id
    )

    return {
        "payment_id": str(payment.id),
        "status": current_payment.status,
        "result": "still_unresolved",
    }


def reconcile_unresolved_payments(limit=100):

    if not isinstance(limit, int) or limit < 1:
        raise ValueError(
            "limit must be a positive integer."
        )

    payment_ids = list(
        Payment.objects.filter(
            status__in=[
                Payment.Status.PENDING,
                Payment.Status.UNKNOWN,
            ]
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