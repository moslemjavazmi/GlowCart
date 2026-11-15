
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Address

from .factories import create_user, create_address


class AddressAPITests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.base_url = "/api/orders/addresses/"

    def address_payload(self, **overrides):
        data = {
            "title": "Home",
            "recipient_name": "Test Recipient",
            "phone_number": "09123456789",
            "province": "Tehran",
            "city": "Tehran",
            "postal_code": "1234567890",
            "address_line": "Test address",
            "is_default": False,
        }
        data.update(overrides)
        return data

    def test_unauthenticated_user_cannot_list_addresses(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 401)

    def test_user_can_create_address(self):
        response = self.client.post(
            self.base_url,
            self.address_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        address = Address.objects.get(user=self.user)

        self.assertTrue(address.is_default)

    def test_first_address_becomes_default_automatically(self):
        response = self.client.post(
            self.base_url,
            self.address_payload(is_default=False),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        address = Address.objects.get(user=self.user)

        self.assertTrue(address.is_default)

    def test_user_can_create_second_non_default_address(self):
        create_address(self.user, is_default=True)

        response = self.client.post(
            self.base_url,
            self.address_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        addresses = Address.objects.filter(user=self.user)

        self.assertEqual(addresses.count(), 2)
        self.assertEqual(
            addresses.filter(is_default=True).count(),
            1,
        )

    def test_user_can_list_only_own_addresses(self):
        create_address(self.user)

        another_user = create_user()
        create_address(another_user)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_user_cannot_retrieve_another_users_address(self):
        another_user = create_user()
        another_address = create_address(another_user)

        response = self.client.get(
            f"{self.base_url}{another_address.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_can_update_own_address(self):
        address = create_address(self.user)

        response = self.client.patch(
            f"{self.base_url}{address.id}/",
            {
                "city": "Shiraz",
                "address_line": "Updated address",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        address.refresh_from_db()

        self.assertEqual(address.city, "Shiraz")
        self.assertEqual(
            address.address_line,
            "Updated address",
        )

    def test_user_cannot_update_another_users_address(self):
        another_user = create_user()
        address = create_address(another_user)

        response = self.client.patch(
            f"{self.base_url}{address.id}/",
            {"city": "Shiraz"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_user_can_set_default_address(self):
        first = create_address(self.user, is_default=True)
        second = create_address(self.user, is_default=False)

        response = self.client.post(
            f"{self.base_url}{second.id}/set-default/"
        )

        self.assertEqual(response.status_code, 200)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_user_can_delete_non_default_address(self):
        create_address(self.user, is_default=True)
        second = create_address(self.user, is_default=False)

        response = self.client.delete(
            f"{self.base_url}{second.id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Address.objects.filter(id=second.id).exists()
        )

    def test_deleting_default_address_selects_new_default(self):
        first = create_address(self.user, is_default=True)
        second = create_address(self.user, is_default=False)

        response = self.client.delete(
            f"{self.base_url}{first.id}/"
        )

        self.assertEqual(response.status_code, 204)

        second.refresh_from_db()

        self.assertTrue(second.is_default)
