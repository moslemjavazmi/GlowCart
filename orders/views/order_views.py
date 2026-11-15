
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from orders.serializers import (
    OrderSerializer,
    CreateOrderSerializer,
)
from orders.services.order_service import create_order
from orders.services.cancellation_service import cancel_order


class CreateOrderView(generics.GenericAPIView):
    serializer_class = CreateOrderSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order, created = create_order(
            user=request.user,
            address_id=serializer.validated_data["address_id"],
            coupon_code=serializer.validated_data.get("coupon_code"),
            idempotency_key=serializer.validated_data["idempotency_key"],
        )

        return Response(
            OrderSerializer(order).data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = "id"

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items")
        )


class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = cancel_order(
            order_id=order_id,
            user=request.user,
        )

        return Response(
            {
                "message": "Order cancelled successfully.",
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status,
                    "inventory_released": (
                        order.inventory_released_at is not None
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )
