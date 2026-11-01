from django.db.models import Q
from django_filters import rest_framework as filters
from django.db.models import Exists, OuterRef
from .models import Product, ProductVariant


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(
        field_name="category__slug",
        lookup_expr="exact",
    )

    brand = filters.CharFilter(
        field_name="brand__slug",
        lookup_expr="exact",
    )

    min_price = filters.NumberFilter(
        method="filter_min_price",
    )

    max_price = filters.NumberFilter(
        method="filter_max_price",
    )

    in_stock = filters.BooleanFilter(
        method="filter_in_stock",
    )

    class Meta:
        model = Product
        fields = [
            "category",
            "brand",
            "min_price",
            "max_price",
            "in_stock",
        ]

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(
            variants__is_active=True,
            variants__price__gte=value,
        ).distinct()

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(
            variants__is_active=True,
            variants__price__lte=value,
        ).distinct()

    def filter_in_stock(self, queryset, name, value):
        available_variants = ProductVariant.objects.filter(
            product=OuterRef("pk"),
            is_active=True,
            stock__gt=0,
        )

        if value:
            return queryset.filter(
                Exists(available_variants)
            )

        return queryset.filter(
            ~Exists(available_variants)
        )