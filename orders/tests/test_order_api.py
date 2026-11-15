
from uuid import uuid4

from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Order

from .factories import (
    create_user,
    create_checkout_context,
)


class OrderAPITests(TestCase):

    def setUp(self):
        self.context = create_checkout_context()
        self.user = self.context["user"]

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_user_cannot_create_order(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(self.context["address"].id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_create_order(self):
        response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(self.context["address"].id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)

        self.assertEqual(
            response.data["status"],
            Order.Status.AWAITING_PAYMENT,
        )

    def test_create_order_requires_valid_address_uuid(self):
        response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": "invalid-uuid",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_user_cannot_create_order_with_another_users_address(self):
        another_user = create_user()

        from .factories import create_address

        another_address = create_address(another_user)

        response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(another_address.id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_user_can_list_only_own_orders(self):
        own_order_response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(self.context["address"].id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(own_order_response.status_code, 201)

        another_context = create_checkout_context()

        from orders.services.order_service import create_order

        create_order(
            user=another_context["user"],
            address_id=another_context["address"].id,
            idempotency_key=uuid4(),
        )

        response = self.client.get("/api/orders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_user_cannot_retrieve_another_users_order(self):
        another_context = create_checkout_context()

        from orders.services.order_service import create_order

        another_order, _ = create_order(
            user=another_context["user"],
            address_id=another_context["address"].id,
            idempotency_key=uuid4(),
        )

        response = self.client.get(
            f"/api/orders/{another_order.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_can_retrieve_own_order(self):
        response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(self.context["address"].id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        order_id = response.data["id"]

        detail_response = self.client.get(
            f"/api/orders/{order_id}/"
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["id"], order_id)

    def test_user_cannot_cancel_another_users_order(self):
        another_context = create_checkout_context()

        from orders.services.order_service import create_order

        another_order, _ = create_order(
            user=another_context["user"],
            address_id=another_context["address"].id,
            idempotency_key=uuid4(),
        )

        response = self.client.post(
            f"/api/orders/{another_order.id}/cancel/"
        )

        self.assertEqual(response.status_code, 400)

    def test_user_can_cancel_own_order(self):
        create_response = self.client.post(
            "/api/orders/create/",
            {
                "address_id": str(self.context["address"].id),
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        order_id = create_response.data["id"]

        response = self.client.post(
            f"/api/orders/{order_id}/cancel/"
        )

        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(id=order_id)

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )
