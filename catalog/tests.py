from decimal import Decimal

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Brand,
    Category,
    Product,
    ProductVariant,
)


class ProductAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Face",
            slug="face",
        )

        cls.brand = Brand.objects.create(
            name="Example Beauty",
            slug="example-beauty",
        )

        cls.foundation = Product.objects.create(
            name="Matte Foundation",
            slug="matte-foundation",
            description="Long lasting foundation",
            category=cls.category,
            brand=cls.brand,
            is_active=True,
        )

        cls.lipstick = Product.objects.create(
            name="Red Lipstick",
            slug="red-lipstick",
            description="Matte red lipstick",
            category=cls.category,
            brand=cls.brand,
            is_active=True,
        )

        cls.inactive_product = Product.objects.create(
            name="Hidden Product",
            slug="hidden-product",
            category=cls.category,
            brand=cls.brand,
            is_active=False,
        )

        ProductVariant.objects.create(
            product=cls.foundation,
            sku="FOUNDATION-LIGHT",
            name="Light",
            price=Decimal("250.00"),
            stock=10,
            is_active=True,
        )

        ProductVariant.objects.create(
            product=cls.foundation,
            sku="FOUNDATION-MEDIUM",
            name="Medium",
            price=Decimal("350.00"),
            stock=0,
            is_active=True,
        )

        ProductVariant.objects.create(
            product=cls.lipstick,
            sku="LIPSTICK-RED",
            name="Red",
            price=Decimal("150.00"),
            stock=0,
            is_active=True,
        )

    def test_product_list_returns_active_products(self):
        response = self.client.get(
            reverse("product-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

    def test_product_detail_returns_product(self):
        response = self.client.get(
            reverse(
                "product-detail",
                kwargs={"slug": "matte-foundation"},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["slug"],
            "matte-foundation",
        )

        self.assertEqual(
            len(response.data["variants"]),
            2,
        )

    def test_product_search(self):
        response = self.client.get(
            reverse("product-list"),
            {"search": "foundation"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_category(self):
        response = self.client.get(
            reverse("product-list"),
            {"category": "face"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_filter_in_stock_true(self):
        response = self.client.get(
            reverse("product-list"),
            {"in_stock": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_in_stock_false(self):
        response = self.client.get(
            reverse("product-list"),
            {"in_stock": "false"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_min_price(self):
        response = self.client.get(
            reverse("product-list"),
            {"min_price": "200"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_ordering_by_name(self):
        response = self.client.get(
            reverse("product-list"),
            {"ordering": "name"},
        )

        self.assertEqual(response.status_code, 200)

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            names,
            sorted(names),
        )

    def test_invalid_price_returns_bad_request(self):
        response = self.client.get(
            reverse("product-list"),
            {"min_price": "not-a-number"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )