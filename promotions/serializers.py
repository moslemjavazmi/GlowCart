
from rest_framework import serializers


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
    )
