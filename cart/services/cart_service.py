
import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404

from catalog.models import ProductVariant
from cart.models import Cart, CartItem


@transaction.atomic
def get_or_create_cart(*, user=None, guest_token=None):
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=user,
            defaults={"guest_token": None},
        )
        return cart

    if guest_token:
        cart = Cart.objects.filter(
            guest_token=guest_token,
            user__isnull=True,
        ).first()

        if cart:
            return cart

    return Cart.objects.create(
        guest_token=uuid.uuid4(),
    )


@transaction.atomic
def add_item(*, cart, variant_id, quantity=1):
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    variant = get_object_or_404(
        ProductVariant.objects.select_for_update(),
        id=variant_id,
        is_active=True,
        product__is_active=True,
    )

    item = (
        CartItem.objects.select_for_update()
        .filter(cart=cart, variant=variant)
        .first()
    )

    new_quantity = quantity + (item.quantity if item else 0)

    if variant.stock < new_quantity:
        raise ValueError(
            f"Only {variant.stock} items are available."
        )

    if item:
        item.quantity = new_quantity
        item.save(update_fields=["quantity", "updated_at"])
    else:
        item = CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=quantity,
        )

    return item


@transaction.atomic
def update_item_quantity(*, cart, item_id, quantity):
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    item = get_object_or_404(
        CartItem.objects.select_for_update().select_related("variant"),
        id=item_id,
        cart=cart,
    )

    if item.variant.stock < quantity:
        raise ValueError(
            f"Only {item.variant.stock} items are available."
        )

    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])

    return item


@transaction.atomic
def remove_item(*, cart, item_id):
    item = get_object_or_404(
        CartItem.objects.select_for_update(),
        id=item_id,
        cart=cart,
    )
    item.delete()


@transaction.atomic
def clear_cart(*, cart):
    cart.items.all().delete()


@transaction.atomic
def merge_guest_cart(*, user, guest_token):
    guest_cart = (
        Cart.objects.select_for_update()
        .filter(
            guest_token=guest_token,
            user__isnull=True,
        )
        .first()
    )

    if guest_cart is None:
        return Cart.objects.get_or_create(user=user)[0]

    user_cart = (
        Cart.objects.select_for_update()
        .filter(user=user)
        .first()
    )

    if user_cart is None:
        guest_cart.user = user
        guest_cart.guest_token = None
        guest_cart.save(
            update_fields=["user", "guest_token", "updated_at"]
        )
        return guest_cart

    guest_items = (
        guest_cart.items
        .select_related("variant", "variant__product")
        .all()
    )

    for guest_item in guest_items:
        variant = guest_item.variant

        if not variant.is_active or not variant.product.is_active:
            continue

        user_item = (
            CartItem.objects.select_for_update()
            .filter(
                cart=user_cart,
                variant=variant,
            )
            .first()
        )

        existing_quantity = (
            user_item.quantity if user_item else 0
        )

        available_quantity = max(variant.stock, 0)

        final_quantity = min(
            existing_quantity + guest_item.quantity,
            available_quantity,
        )

        # اگر موجودی کافی نیست، آیتم مهمان را به سبد کاربر اضافه نکن.
        # آیتم قبلی کاربر را نیز حذف نکن.
        if final_quantity <= existing_quantity:
            continue

        if user_item:
            user_item.quantity = final_quantity
            user_item.save(
                update_fields=["quantity", "updated_at"]
            )
        else:
            CartItem.objects.create(
                cart=user_cart,
                variant=variant,
                quantity=final_quantity,
            )

    guest_cart.delete()

    return user_cart
