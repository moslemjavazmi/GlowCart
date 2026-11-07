from django.db.models import Min, Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, filters
from rest_framework.exceptions import ValidationError

from .filters import ProductFilter
from .models import (
    Brand,
    Category,
    Product,
    ProductVariant,
)
from .pagination import ProductPagination
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductSerializer,
)


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description",
        "brand__name",
        "category__name",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True),
                ),
            )
        )

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True),
                ),
            )
        )



class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return (
            Category.objects
            .filter(is_active=True)
            .order_by("name")
        )


class BrandListView(generics.ListAPIView):
    serializer_class = BrandSerializer

    def get_queryset(self):
        return (
            Brand.objects
            .filter(is_active=True)
            .order_by("name")
        )


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description",
        "brand__name",
        "category__name",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
        "min_variant_price",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(
                        is_active=True
                    ),
                ),
            )
            .annotate(
                min_variant_price=Min(
                    "variants__price",
                    filter=Q(variants__is_active=True),
                )
            )
        )


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(
                        is_active=True
                    ),
                ),
            )
        )