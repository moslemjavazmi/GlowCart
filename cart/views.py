from uuid import UUID

from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from rest_framework.permissions import IsAuthenticated
from cart.services.cart_service import merge_guest_cart
from cart.models import Cart, CartItem
from cart.serializers import (
    CartSerializer,
    AddCartItemSerializer,
    UpdateCartItemSerializer,
)
from cart.services.cart_service import (
    get_or_create_cart,
    add_item,
    update_item_quantity,
    remove_item,
    clear_cart,
)


def get_request_cart(request):
    if request.user.is_authenticated:
        return get_or_create_cart(user=request.user), None

    raw_token = request.headers.get("X-Guest-Cart-Token")

    if raw_token:
        try:
            guest_token = UUID(raw_token)
        except (ValueError, TypeError):
            return None, Response(
                {"error": "Invalid guest cart token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = Cart.objects.filter(
            guest_token=guest_token,
            user__isnull=True,
        ).first()

        if cart:
            return cart, None

    # اگر مهمان توکن نداشته باشد، سبد جدید ساخته می‌شود.
    cart = get_or_create_cart()
    return cart, None


def cart_response(cart, *, status_code=status.HTTP_200_OK):
    cart = (
        Cart.objects
        .prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related(
                    "variant",
                    "variant__product",
                ),
            )
        )
        .get(pk=cart.pk)
    )

    data = CartSerializer(cart).data

    # مهمان باید این شناسه را برای درخواست‌های بعدی نگه دارد.
    if cart.guest_token:
        data["guest_token"] = str(cart.guest_token)

    return Response(data, status=status_code)


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart, error = get_request_cart(request)

        if error:
            return error

        return cart_response(cart)


class AddCartItemView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart, error = get_request_cart(request)

        if error:
            return error

        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            add_item(
                cart=cart,
                variant_id=serializer.validated_data["variant_id"],
                quantity=serializer.validated_data["quantity"],
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return cart_response(cart, status_code=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, item_id):
        cart, error = get_request_cart(request)

        if error:
            return error

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            update_item_quantity(
                cart=cart,
                item_id=item_id,
                quantity=serializer.validated_data["quantity"],
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return cart_response(cart)


class RemoveCartItemView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, item_id):
        cart, error = get_request_cart(request)

        if error:
            return error

        remove_item(cart=cart, item_id=item_id)

        return cart_response(cart)


class ClearCartView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart, error = get_request_cart(request)

        if error:
            return error

        clear_cart(cart=cart)

        return cart_response(cart)



class MergeGuestCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        guest_token = request.data.get("guest_token")

        if not guest_token:
            return Response(
                {"error": "guest_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            guest_token = UUID(str(guest_token))
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid guest token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = merge_guest_cart(
            user=request.user,
            guest_token=guest_token,
        )

        return cart_response(cart)