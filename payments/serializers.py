
from rest_framework import serializers

from payments.models import Payment


class InitializePaymentSerializer(serializers.Serializer):

    order_id = serializers.UUIDField()

    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices,
    )

    idempotency_key = serializers.UUIDField()