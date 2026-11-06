
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from promotions.serializers import ApplyCouponSerializer
from promotions.services.coupon_service import (
    apply_coupon_to_order,
    remove_coupon_from_order,
)


def order_coupon_response(order):
    return {
        "order_id": str(order.id),
        "subtotal": str(order.subtotal),
        "shipping_cost": str(order.shipping_cost),
        "discount_amount": str(order.discount_amount),
        "total_amount": str(order.total_amount),
    }


class ApplyCouponView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        serializer = ApplyCouponSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        order = apply_coupon_to_order(
            code=serializer.validated_data["code"],
            user=request.user,
            order_id=order_id,
        )

        return Response(
            {
                "message": "Coupon applied successfully.",
                "order": order_coupon_response(order),
            },
            status=status.HTTP_200_OK,
        )


class RemoveCouponView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, order_id):

        order = remove_coupon_from_order(
            user=request.user,
            order_id=order_id,
        )

        return Response(
            {
                "message": "Coupon removed successfully.",
                "order": order_coupon_response(order),
            },
            status=status.HTTP_200_OK,
        )
