
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orders.models import Address
from orders.serializers import AddressSerializer

from orders.services.address_service import (
    create_address,
    update_address,
    delete_address,
    set_default_address,
)


class AddressViewSet(viewsets.ModelViewSet):

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.instance = create_address(
            user=self.request.user,
            validated_data=serializer.validated_data,
        )


    def perform_update(self, serializer):
        serializer.instance = update_address(
            address=self.get_object(),
            validated_data=serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_address(address=instance)

    @action(
        detail=True,
        methods=["post"],
        url_path="set-default",
    )
    def set_default(self, request, pk=None):
        address = self.get_object()

        address = set_default_address(
            address=address,
            user=request.user,
        )

        return Response(
            AddressSerializer(address).data
        )
