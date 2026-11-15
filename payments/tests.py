
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone

from orders.models import Address, Order
from payments.models import Payment
from payments.gateways.zarinpal import (
    ZarinpalGateway,
    ZarinpalRejectedError,
    ZarinpalTransportError,
)
from payments.services.payment_service import (
    PaymentGatewayError,
    initialize_payment,
    verify_payment,
)
from urllib.parse import parse_qs, urlsplit
from rest_framework.test import APIClient

from datetime import timedelta

# =========================================================
# Zarinpal Gateway Tests
# =========================================================

@override_settings(
    ZARINPAL_MERCHANT_ID="00000000-0000-0000-0000-000000000000",
    ZARINPAL_SANDBOX=True,
    ZARINPAL_CURRENCY="IRT",
)
class ZarinpalGatewayTests(SimpleTestCase):

    def setUp(self):
        self.gateway = ZarinpalGateway()

    @patch("payments.gateways.zarinpal.requests.post")
    def test_create_payment_rejects_explicit_4xx_error(self, mock_post):
        response = MagicMock()
        response.status_code = 422
        response.json.return_value = {
            "data": {},
            "errors": {
                "code": -9,
                "message": "Invalid merchant ID",
            },
        }
        mock_post.return_value = response

        with self.assertRaises(ZarinpalRejectedError):
            self.gateway.create_payment(
                amount=1000,
                callback_url="https://example.com/callback",
                description="Test payment",
            )

    @patch("payments.gateways.zarinpal.requests.post")
    def test_verify_4xx_error_remains_unresolved(self, mock_post):
        response = MagicMock()
        response.status_code = 422
        response.json.return_value = {
            "data": {},
            "errors": {
                "code": -9,
                "message": "Verification error",
            },
        }
        mock_post.return_value = response

        result = self.gateway.verify_payment(
            authority="S00000000000000000000000000000057nr2",
            amount=1000,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["definitive_failure"])
        self.assertIsNone(result["reference"])

    @patch("payments.gateways.zarinpal.requests.post")
    def test_create_payment_returns_authority(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "code": 100,
                "authority": "S00000000000000000000000000000057nr2",
            },
            "errors": [],
        }
        mock_post.return_value = response

        result = self.gateway.create_payment(
            amount=1000,
            callback_url="https://example.com/callback",
            description="Test payment",
        )

        self.assertEqual(
            result["authority"],
            "S00000000000000000000000000000057nr2",
        )
        self.assertIn("StartPay", result["payment_url"])

    @patch("payments.gateways.zarinpal.requests.post")
    def test_verify_success_returns_reference(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "code": 100,
                "ref_id": 123456789,
            },
            "errors": [],
        }
        mock_post.return_value = response

        result = self.gateway.verify_payment(
            authority="S00000000000000000000000000000057nr2",
            amount=1000,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["reference"], "123456789")
        self.assertFalse(result["definitive_failure"])

    @patch("payments.gateways.zarinpal.requests.post")
    def test_network_error_raises_transport_error(self, mock_post):
        import requests

        mock_post.side_effect = requests.Timeout("Gateway timeout")

        with self.assertRaises(ZarinpalTransportError):
            self.gateway.create_payment(
                amount=1000,
                callback_url="https://example.com/callback",
                description="Test payment",
            )


# =========================================================
# Payment Service Tests
# =========================================================

@override_settings(
    PAYMENT_CALLBACK_URL="https://example.com/payments/callback/",
)
class PaymentServiceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="payment-test@example.com",
            password="TestPassword123!",
        )

        self.address = Address.objects.create(
            user=self.user,
            title="Home",
            recipient_name="Test User",
            phone_number="09120000000",
            province="Tehran",
            city="Tehran",
            postal_code="1234567890",
            address_line="Test address",
            is_default=True,
        )

        self.order = Order.objects.create(
            order_number="GC-TEST-0001",
            user=self.user,
            address=self.address,
            recipient_name="Test User",
            phone_number="09120000000",
            province="Tehran",
            city="Tehran",
            postal_code="1234567890",
            address_line="Test address",
            status=Order.Status.AWAITING_PAYMENT,
            subtotal=Decimal("100000.00"),
            shipping_cost=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("100000.00"),
            expires_at=None,
        )

        self.idempotency_key = uuid.uuid4()

        self.gateway = MagicMock()

    def initialize(self, idempotency_key=None):
        return initialize_payment(
            user=self.user,
            order_id=self.order.id,
            provider=Payment.Provider.ZARINPAL,
            idempotency_key=idempotency_key or self.idempotency_key,
        )

    @patch("payments.services.payment_service.get_payment_gateway")
    def test_timeout_returns_unknown_payment_with_payment_id(
        self,
        mock_get_gateway,
    ):
        self.gateway.create_payment.side_effect = TimeoutError(
            "Gateway timeout"
        )
        mock_get_gateway.return_value = self.gateway

        result = self.initialize()

        payment = result["payment"]

        self.assertEqual(payment.status, Payment.Status.UNKNOWN)
        self.assertIsNotNone(payment.id)
        self.assertIsNone(result["payment_url"])
        self.assertFalse(result["reused"])

        self.assertEqual(Payment.objects.count(), 1)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.UNKNOWN)
        self.assertIn(
            "outcome is unknown",
            payment.gateway_response["message"],
        )

    @patch("payments.services.payment_service.get_payment_gateway")
    def test_explicit_gateway_rejection_marks_payment_failed(
        self,
        mock_get_gateway,
    ):
        self.gateway.create_payment.side_effect = ZarinpalRejectedError(
            "Invalid payment request"
        )
        mock_get_gateway.return_value = self.gateway

        result = self.initialize()

        payment = result["payment"]

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIsNone(result["payment_url"])
        self.assertFalse(result["reused"])
        self.assertEqual(Payment.objects.count(), 1)

    @patch("payments.services.payment_service.consume_coupon_reservation")
    @patch("payments.services.payment_service.get_payment_gateway")
    def test_early_callback_authority_is_adopted_and_verified(
        self,
        mock_get_gateway,
        mock_consume_coupon,
    ):
        authority = "S00000000000000000000000000000057nr2"

        def create_payment_with_early_callback(**kwargs):
            payment = Payment.objects.get(order=self.order)

            payment.callback_authority = authority
            payment.callback_status = "OK"
            payment.callback_received_at = timezone.now()
            payment.save(
                update_fields=[
                    "callback_authority",
                    "callback_status",
                    "callback_received_at",
                    "updated_at",
                ]
            )

            raise TimeoutError("Gateway response timed out")

        self.gateway.create_payment.side_effect = (
            create_payment_with_early_callback
        )

        self.gateway.verify_payment.return_value = {
            "success": True,
            "definitive_failure": False,
            "reference": "123456789",
            "raw_response": {"code": 100},
        }

        mock_get_gateway.return_value = self.gateway

        result = self.initialize()
        payment = result["payment"]

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.authority, authority)
        self.assertEqual(payment.provider_reference, "123456789")
        self.assertIsNotNone(payment.paid_at)

        self.assertIsNone(payment.callback_authority)
        self.assertIsNone(payment.callback_status)
        self.assertIsNone(payment.callback_received_at)

        self.assertEqual(self.order.status, Order.Status.PAID)

        self.gateway.verify_payment.assert_called_once()
        mock_consume_coupon.assert_called_once_with(
            order_id=self.order.id
        )

    @patch("payments.services.payment_service.consume_coupon_reservation")
    @patch("payments.services.payment_service.get_payment_gateway")
    def test_verify_success_finalizes_payment_and_order(
        self,
        mock_get_gateway,
        mock_consume_coupon,
    ):
        payment = Payment.objects.create(
            order=self.order,
            provider=Payment.Provider.ZARINPAL,
            status=Payment.Status.PENDING,
            amount=self.order.total_amount,
            authority="S00000000000000000000000000000057nr2",
            payment_url="https://example.com/pay",
        )

        self.gateway.verify_payment.return_value = {
            "success": True,
            "definitive_failure": False,
            "reference": "987654321",
            "raw_response": {"code": 100},
        }
        mock_get_gateway.return_value = self.gateway

        result = verify_payment(payment.id)

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(result.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.provider_reference, "987654321")
        self.assertIsNotNone(payment.paid_at)

        self.assertEqual(self.order.status, Order.Status.PAID)
        mock_consume_coupon.assert_called_once_with(
            order_id=self.order.id
        )

    @patch("payments.services.payment_service.get_payment_gateway")
    def test_active_payment_prevents_second_payment(
        self,
        mock_get_gateway,
    ):
        Payment.objects.create(
            order=self.order,
            provider=Payment.Provider.ZARINPAL,
            status=Payment.Status.PENDING,
            amount=self.order.total_amount,
            authority="EXISTING-AUTHORITY",
            payment_url="https://example.com/pay",
        )

        mock_get_gateway.return_value = self.gateway

        with self.assertRaises(PaymentGatewayError):
            self.initialize(idempotency_key=uuid.uuid4())

        self.assertEqual(Payment.objects.count(), 1)
        self.gateway.create_payment.assert_not_called()

    @patch("payments.services.payment_service.get_payment_gateway")
    def test_same_idempotency_key_reuses_existing_payment(
        self,
        mock_get_gateway,
    ):
        existing_payment = Payment.objects.create(
            order=self.order,
            provider=Payment.Provider.ZARINPAL,
            status=Payment.Status.PENDING,
            amount=self.order.total_amount,
            authority="EXISTING-AUTHORITY",
            payment_url="https://example.com/pay",
            idempotency_key=self.idempotency_key,
        )

        mock_get_gateway.return_value = self.gateway

        result = self.initialize()

        self.assertEqual(result["payment"].id, existing_payment.id)
        self.assertTrue(result["reused"])
        self.assertEqual(
            result["payment_url"],
            existing_payment.payment_url,
        )

        self.assertEqual(Payment.objects.count(), 1)
        self.gateway.create_payment.assert_not_called()




class ReconciliationServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="reconciliation-test@example.com",
            password="TestPassword123!",
        )

        self.address = Address.objects.create(
            user=self.user,
            title="Home",
            recipient_name="Test User",
            phone_number="09120000000",
            province="Tehran",
            city="Tehran",
            postal_code="1234567890",
            address_line="Test address",
        )

        self.order = Order.objects.create(
            user=self.user,
            address=self.address,
            order_number="GC-RECON-0001",
            status=Order.Status.AWAITING_PAYMENT,
            subtotal=Decimal("100000"),
            shipping_cost=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("100000"),
            expires_at=None,
        )

    def create_payment(self, **kwargs):
        defaults = {
            "order": self.order,
            "provider": Payment.Provider.ZARINPAL,
            "status": Payment.Status.PENDING,
            "amount": Decimal("100000"),
            "authority": "A000000000000000000000000000000001",
        }
        defaults.update(kwargs)
        return Payment.objects.create(**defaults)

    @patch("payments.services.reconciliation_service.get_payment_gateway")
    def test_missing_authority_moves_payment_to_review_required(
        self,
        mock_get_gateway,
    ):
        from payments.services.reconciliation_service import (
            reconcile_payment,
        )

        payment = self.create_payment(
            status=Payment.Status.UNKNOWN,
            authority=None,
        )

        result = reconcile_payment(payment.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.REVIEW_REQUIRED,
        )
        self.assertEqual(result["result"], "manual_review_required")
        self.assertEqual(result["reason"], "missing_authority")
        mock_get_gateway.assert_not_called()

    @patch("payments.services.reconciliation_service.get_payment_gateway")
    def test_stale_initiated_payment_moves_to_review_required(
        self,
        mock_get_gateway,
    ):
        from payments.services.reconciliation_service import (
            reconcile_payment,
        )

        payment = self.create_payment(
            status=Payment.Status.INITIATED,
            authority=None,
        )

        Payment.objects.filter(pk=payment.pk).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        with patch(
            "payments.services.reconciliation_service.INITIATED_STALE_AFTER",
            timedelta(minutes=5),
        ):
            result = reconcile_payment(payment.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.REVIEW_REQUIRED,
        )
        self.assertEqual(result["result"], "manual_review_required")
        self.assertEqual(
            result["reason"],
            "stale_initiated_payment",
        )
        mock_get_gateway.assert_not_called()

    @patch("payments.services.reconciliation_service.get_payment_gateway")
    def test_ambiguous_gateway_response_keeps_payment_unresolved(
        self,
        mock_get_gateway,
    ):
        from payments.services.reconciliation_service import (
            reconcile_payment,
        )

        payment = self.create_payment()

        gateway = MagicMock()
        gateway.verify_payment.return_value = {
            "success": False,
            "reference": None,
            "definitive_failure": False,
            "raw_response": {"message": "Verification is inconclusive"},
        }
        mock_get_gateway.return_value = gateway

        result = reconcile_payment(payment.id)

        payment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(result["result"], "still_unresolved")
        gateway.verify_payment.assert_called_once_with(
            authority=payment.authority,
            amount=payment.amount,
        )

    @patch("payments.services.reconciliation_service.get_payment_gateway")
    def test_definitive_gateway_failure_marks_payment_failed(
        self,
        mock_get_gateway,
    ):
        from payments.services.reconciliation_service import (
            reconcile_payment,
        )

        payment = self.create_payment()

        gateway = MagicMock()
        gateway.verify_payment.return_value = {
            "success": False,
            "reference": None,
            "definitive_failure": True,
            "raw_response": {"code": -21},
        }
        mock_get_gateway.return_value = gateway

        result = reconcile_payment(payment.id)

        payment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(result["result"], "definitive_failure")

    @patch("payments.services.reconciliation_service.get_payment_gateway")
    def test_early_callback_authority_is_adopted_before_verification(
        self,
        mock_get_gateway,
    ):
        from payments.services.reconciliation_service import (
            reconcile_payment,
        )

        callback_authority = (
            "S00000000000000000000000000000057nr2"
        )

        payment = self.create_payment(
            status=Payment.Status.INITIATED,
            authority=None,
            callback_authority=callback_authority,
            callback_status="OK",
            callback_received_at=timezone.now(),
        )

        gateway = MagicMock()
        gateway.verify_payment.return_value = {
            "success": False,
            "reference": None,
            "definitive_failure": False,
            "raw_response": {"message": "Still unresolved"},
        }
        mock_get_gateway.return_value = gateway

        result = reconcile_payment(payment.id)

        payment.refresh_from_db()

        self.assertEqual(payment.authority, callback_authority)
        self.assertEqual(payment.status, Payment.Status.UNKNOWN)
        self.assertIsNone(payment.callback_authority)
        self.assertIsNone(payment.callback_status)
        self.assertIsNone(payment.callback_received_at)
        self.assertEqual(result["result"], "still_unresolved")

        gateway.verify_payment.assert_called_once_with(
            authority=callback_authority,
            amount=payment.amount,
        )

    def test_reconcile_unresolved_payments_rejects_invalid_limit(self):
        from payments.services.reconciliation_service import (
            reconcile_unresolved_payments,
        )

        for invalid_limit in (0, -1, True, 1.5, "10", None):
            with self.subTest(limit=invalid_limit):
                with self.assertRaises(ValueError):
                    reconcile_unresolved_payments(
                        limit=invalid_limit
                    )



@override_settings(
    FRONTEND_PAYMENT_RESULT_URL="http://localhost:3000/payment/result/"
)
class ZarinpalCallbackViewTests(TestCase):
    CALLBACK_URL = "/api/payments/callback/zarinpal/"

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="callback-test@example.com",
            password="TestPassword123!",
        )

        self.address = Address.objects.create(
            user=self.user,
            title="Home",
            recipient_name="Test User",
            phone_number="09120000000",
            province="Tehran",
            city="Tehran",
            postal_code="1234567890",
            address_line="Test address",
        )

        self.order = Order.objects.create(
            user=self.user,
            address=self.address,
            order_number="GC-CALLBACK-0001",
            status=Order.Status.AWAITING_PAYMENT,
            subtotal=Decimal("100000"),
            shipping_cost=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("100000"),
            expires_at=None,
        )

        self.client = APIClient()

        self.authority = "A000000000000000000000000000000001"

    def create_payment(self, **kwargs):
        defaults = {
            "order": self.order,
            "provider": Payment.Provider.ZARINPAL,
            "status": Payment.Status.PENDING,
            "amount": Decimal("100000"),
            "authority": self.authority,
        }
        defaults.update(kwargs)

        return Payment.objects.create(**defaults)

    def get_redirect_params(self, response):
        self.assertEqual(response.status_code, 302)

        parsed_url = urlsplit(response.url)
        return parse_qs(parsed_url.query)

    def test_callback_requires_authority(self):
        response = self.client.get(
            self.CALLBACK_URL,
            {"Status": "OK"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Authority is required.",
        )

    def test_callback_rejects_invalid_gateway_status(self):
        response = self.client.get(
            self.CALLBACK_URL,
            {
                "Authority": self.authority,
                "Status": "INVALID",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Invalid gateway status.",
        )

    def test_callback_returns_404_for_unknown_payment(self):
        response = self.client.get(
            self.CALLBACK_URL,
            {
                "Authority": self.authority,
                "Status": "OK",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"],
            "Payment not found.",
        )

    def test_callback_rejects_authority_mismatch(self):
        payment = self.create_payment()

        response = self.client.get(
            self.CALLBACK_URL,
            {
                "payment_id": str(payment.id),
                "Authority": "DIFFERENT_AUTHORITY",
                "Status": "OK",
            },
        )

        payment.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Payment authority mismatch.",
        )
        self.assertEqual(payment.authority, self.authority)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_early_callback_stores_authority_and_redirects(self):
        payment = self.create_payment(
            status=Payment.Status.INITIATED,
            authority=None,
        )

        response = self.client.get(
            self.CALLBACK_URL,
            {
                "payment_id": str(payment.id),
                "Authority": self.authority,
                "Status": "OK",
            },
        )

        payment.refresh_from_db()

        params = self.get_redirect_params(response)

        self.assertEqual(
            payment.callback_authority,
            self.authority,
        )
        self.assertEqual(payment.callback_status, "OK")
        self.assertIsNotNone(payment.callback_received_at)

        self.assertEqual(
            params["status"],
            ["verification_pending"],
        )
        self.assertEqual(
            params["payment_id"],
            [str(payment.id)],
        )
        self.assertEqual(
            params["order_number"],
            [self.order.order_number],
        )

    @patch("payments.views.verify_payment")
    def test_callback_verifies_payment_and_redirects_success(
        self,
        mock_verify_payment,
    ):
        payment = self.create_payment()

        def fake_verify_payment(payment_id):
            current_payment = Payment.objects.get(id=payment_id)
            current_payment.status = Payment.Status.SUCCESS
            current_payment.provider_reference = "123456789"
            current_payment.paid_at = timezone.now()
            current_payment.save(
                update_fields=[
                    "status",
                    "provider_reference",
                    "paid_at",
                    "updated_at",
                ]
            )
            return current_payment

        mock_verify_payment.side_effect = fake_verify_payment

        response = self.client.get(
            self.CALLBACK_URL,
            {
                "payment_id": str(payment.id),
                "Authority": self.authority,
                "Status": "OK",
            },
        )

        payment.refresh_from_db()
        params = self.get_redirect_params(response)

        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(
            payment.provider_reference,
            "123456789",
        )

        self.assertEqual(params["status"], ["success"])
        self.assertEqual(
            params["payment_id"],
            [str(payment.id)],
        )

        mock_verify_payment.assert_called_once_with(
            payment_id=payment.id,
        )

    @patch("payments.views.verify_payment")
    def test_duplicate_callback_does_not_verify_final_payment(
        self,
        mock_verify_payment,
    ):
        payment = self.create_payment(
            status=Payment.Status.SUCCESS,
            provider_reference="123456789",
            paid_at=timezone.now(),
        )

        response = self.client.get(
            self.CALLBACK_URL,
            {
                "payment_id": str(payment.id),
                "Authority": self.authority,
                "Status": "OK",
            },
        )

        params = self.get_redirect_params(response)

        self.assertEqual(params["status"], ["success"])
        self.assertEqual(
            params["payment_id"],
            [str(payment.id)],
        )
        mock_verify_payment.assert_not_called()
