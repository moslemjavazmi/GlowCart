
from rest_framework import serializers


class ApplyCouponSerializer(serializers.Serializer):

    code = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
        allow_blank=False,
    )

    def validate_code(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError(
                "Coupon code cannot be empty."
            )

        return value
