
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from cart.models import Cart, CartItem

from orders.models import (
    Order,
    OrderItem,
    Address,
    InventoryReservation,
)

from promotions.services.coupon_service import reserve_coupon


def generate_order_number():
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:12].upper()

    return f"GC-{date_part}-{random_part}"


@transaction.atomic
def create_order(*, user, address_id, coupon_code=None):
    """
    Create an order from the user's cart.

    All operations are atomic:
    - Address validation
    - Cart locking
    - Product variant locking
    - Stock validation
    - Order creation
    - Coupon reservation
    - Inventory reservation
    - Cart clearing
    """

    # -----------------------------------------------------
    # STEP 1: Validate address ownership
    # -----------------------------------------------------

    address = Address.objects.filter(
        id=address_id,
        user=user,
    ).first()

    if not address:
        raise ValidationError({
            "address_id": "Address not found."
        })

    # -----------------------------------------------------
    # STEP 2: Lock cart
    # -----------------------------------------------------

    cart = (
        Cart.objects
        .select_for_update()
        .filter(user=user)
        .first()
    )

    if not cart:
        raise ValidationError({
            "cart": "Your cart is empty."
        })

    # -----------------------------------------------------
    # STEP 3: Retrieve cart items
    # -----------------------------------------------------

    cart_items = list(
        CartItem.objects
        .filter(cart=cart)
        .select_related(
            "variant",
            "variant__product",
        )
        .order_by("variant_id")
    )

    if not cart_items:
        raise ValidationError({
            "cart": "Your cart is empty."
        })

    # -----------------------------------------------------
    # STEP 4: Lock variants in deterministic order
    # -----------------------------------------------------

    variant_ids = [
        item.variant_id
        for item in cart_items
    ]

    locked_variants = {
        variant.id: variant
        for variant in (
            ProductVariant.objects
            .select_for_update()
            .filter(id__in=variant_ids)
            .select_related("product")
            .order_by("id")
        )
    }

    # -----------------------------------------------------
    # STEP 5: Validate products and calculate subtotal
    # -----------------------------------------------------

    subtotal = Decimal("0.00")
    order_items_data = []

    for cart_item in cart_items:

        variant = locked_variants.get(
            cart_item.variant_id
        )

        if not variant:
            raise ValidationError({
                "cart": "A product variant no longer exists."
            })

        if (
            not variant.is_active
            or not variant.product.is_active
        ):
            raise ValidationError({
                "cart": (
                    f"{variant.name} is no longer available."
                )
            })

        if cart_item.quantity < 1:
            raise ValidationError({
                "cart": "Invalid cart item quantity."
            })

        if cart_item.quantity > variant.stock:
            raise ValidationError({
                "cart": (
                    f"Insufficient stock for {variant.name}. "
                    f"Available: {variant.stock}"
                )
            })

        unit_price = variant.price
        line_total = unit_price * cart_item.quantity

        subtotal += line_total

        order_items_data.append({
            "variant": variant,
            "product_name": variant.product.name,
            "variant_name": variant.name,
            "sku": variant.sku,
            "unit_price": unit_price,
            "quantity": cart_item.quantity,
            "line_total": line_total,
        })

    # -----------------------------------------------------
    # STEP 6: Calculate initial totals
    # -----------------------------------------------------

    shipping_cost = Decimal("0.00")
    discount_amount = Decimal("0.00")

    total_amount = (
        subtotal
        + shipping_cost
        - discount_amount
    )

    expires_at = (
        timezone.now() + timedelta(minutes=20)
    )

    # -----------------------------------------------------
    # STEP 7: Create order
    # -----------------------------------------------------

    order = Order.objects.create(
        order_number=generate_order_number(),
        user=user,
        address=address,
        status=Order.Status.AWAITING_PAYMENT,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount_amount=discount_amount,
        total_amount=total_amount,
        expires_at=expires_at,

        # Address snapshot
        recipient_name=address.recipient_name,
        phone_number=address.phone_number,
        province=address.province,
        city=address.city,
        postal_code=address.postal_code,
        address_line=address.address_line,
    )

    # -----------------------------------------------------
    # STEP 8: Create order items
    # -----------------------------------------------------

    order_items = [
        OrderItem(
            order=order,
            **item_data,
        )
        for item_data in order_items_data
    ]

    OrderItem.objects.bulk_create(order_items)

    # -----------------------------------------------------
    # STEP 9: Reserve coupon if supplied
    # -----------------------------------------------------

    if coupon_code and coupon_code.strip():

        coupon_reservation = reserve_coupon(
            code=coupon_code,
            user=user,
            order_id=order.id,
            discountable_amount=subtotal,
        )

        discount_amount = (
            coupon_reservation.discount_amount
        )

        total_amount = (
            subtotal
            + shipping_cost
            - discount_amount
        )

        if total_amount <= Decimal("0.00"):
            raise ValidationError({
                "coupon": (
                    "The discount cannot make the order total "
                    "zero or negative."
                )
            })

        order.discount_amount = discount_amount
        order.total_amount = total_amount

        order.save(
            update_fields=[
                "discount_amount",
                "total_amount",
                "updated_at",
            ]
        )

    # -----------------------------------------------------
    # STEP 10: Validate final amount
    # -----------------------------------------------------

    if order.total_amount <= Decimal("0.00"):
        raise ValidationError({
            "total_amount": "Invalid order total."
        })

    # -----------------------------------------------------
    # STEP 11: Deduct stock and create reservations
    # -----------------------------------------------------

    reservations = []

    for item_data in order_items_data:

        variant = item_data["variant"]
        quantity = item_data["quantity"]

        variant.stock -= quantity

        variant.save(
            update_fields=["stock"]
        )

        reservations.append(
            InventoryReservation(
                order=order,
                variant=variant,
                quantity=quantity,
                expires_at=expires_at,
                status=InventoryReservation.Status.ACTIVE,
            )
        )

    InventoryReservation.objects.bulk_create(
        reservations
    )

    # -----------------------------------------------------
    # STEP 12: Clear cart
    # -----------------------------------------------------

    CartItem.objects.filter(
        cart=cart
    ).delete()

    return order
