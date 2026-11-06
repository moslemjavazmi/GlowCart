
from django.contrib import admin

from .models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "parent",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    autocomplete_fields = (
        "parent",
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0

    fields = (
        "sku",
        "name",
        "price",
        "stock",
        "is_active",
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

    fields = (
        "image",
        "alt_text",
        "is_primary",
        "sort_order",
    )

    ordering = (
        "sort_order",
        "id",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "brand",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "category",
        "brand",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
        "description",
        "brand__name",
        "category__name",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    autocomplete_fields = (
        "category",
        "brand",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = (
        ProductVariantInline,
        ProductImageInline,
    )

    ordering = (
        "-created_at",
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product",
        "name",
        "price",
        "stock",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "sku",
        "name",
        "product__name",
    )

    autocomplete_fields = (
        "product",
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "alt_text",
        "is_primary",
        "sort_order",
    )

    list_filter = (
        "is_primary",
    )

    search_fields = (
        "product__name",
        "alt_text",
    )

    autocomplete_fields = (
        "product",
    )

    ordering = (
        "product",
        "sort_order",
    )
