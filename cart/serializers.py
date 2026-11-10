from rest_framework import serializers

from cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.IntegerField(
        source="variant.id",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True,
    )

    variant_name = serializers.CharField(
        source="variant.name",
        read_only=True,
    )

    sku = serializers.CharField(
        source="variant.sku",
        read_only=True,
    )

    available_stock = serializers.IntegerField(
        source="variant.stock",
        read_only=True,
    )

    product_image = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant_id",
            "product_name",
            "variant_name",
            "sku",
            "available_stock",
            "product_image",
            "unit_price",
            "quantity",
            "line_total",
        ]

    def get_product_image(self, obj):
        images = obj.variant.product.images.all()

        image = next(
            (item for item in images if item.is_primary),
            None,
        )

        if image is None:
            image = images[0] if images else None

        if image is None or not image.image:
            return None

        request = self.context.get("request")
        image_url = image.image.url

        if request:
            return request.build_absolute_uri(image_url)

        return image_url

    def get_unit_price(self, obj):
        return str(obj.variant.price)

    def get_line_total(self, obj):
        return str(obj.variant.price * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    total_items = serializers.IntegerField(read_only=True)

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "subtotal",
            "created_at",
            "updated_at",
        ]

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class AddCartItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)