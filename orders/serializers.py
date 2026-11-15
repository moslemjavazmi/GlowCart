
from rest_framework import serializers

from orders.models import Address, Order, OrderItem


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address

        fields = [
            "id",
            "title",
            "recipient_name",
            "phone_number",
            "province",
            "city",
            "postal_code",
            "address_line",
            "is_default",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem

        fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        ]

        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "status",
            "subtotal",
            "shipping_cost",
            "discount_amount",
            "total_amount",
            "recipient_name",
            "phone_number",
            "province",
            "city",
            "postal_code",
            "address_line",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields




class CreateOrderSerializer(serializers.Serializer):

    address_id = serializers.UUIDField()

    idempotency_key = serializers.UUIDField(required=True)

    coupon_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
    )

    def validate_address_id(self, value):
        request = self.context.get("request")

        if not request or not Address.objects.filter(
            id=value,
            user=request.user,
        ).exists():
            raise serializers.ValidationError(
                "Address not found."
            )

        return value

    def validate_coupon_code(self, value):
        value = value.strip().upper()
        return value or None
